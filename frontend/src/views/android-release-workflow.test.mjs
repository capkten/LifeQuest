import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

const workflowUrl = new URL('../../../.github/workflows/android-release.yml', import.meta.url)

function extractCheckScript(workflow) {
  const checkStart = workflow.indexOf('      - id: check\n')
  const runStart = workflow.indexOf('        run: |\n', checkStart) + '        run: |\n'.length
  const nextJob = workflow.indexOf('\n  release:\n', runStart)

  assert.ok(checkStart >= 0 && runStart >= 0 && nextJob > runStart, 'workflow release check must have a script block')

  return workflow.slice(runStart, nextJob)
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => {
      assert.ok(line.startsWith('          '), 'workflow script lines must retain YAML block indentation')
      return line.slice(10)
    })
    .join('\n')
}

function git(repo, ...args) {
  return execFileSync('git', args, { cwd: repo, encoding: 'utf8' }).trim()
}

function commit(repo, message) {
  git(repo, 'add', '-A')
  git(repo, 'commit', '-m', message)
  return git(repo, 'rev-parse', 'HEAD')
}

test('Android release gate sees app changes earlier in a multi-commit push', async (t) => {
  const repo = mkdtempSync(join(tmpdir(), 'lifequest-android-release-'))
  t.after(() => rmSync(repo, { recursive: true, force: true }))

  git(repo, 'init', '-q')
  git(repo, 'config', 'user.name', 'Release Gate Test')
  git(repo, 'config', 'user.email', 'release-gate@example.invalid')
  mkdirSync(join(repo, 'frontend'), { recursive: true })
  mkdirSync(join(repo, 'docs'), { recursive: true })
  writeFileSync(join(repo, 'VERSION'), '1.14.5\n', 'utf8')
  writeFileSync(join(repo, 'frontend', 'app.js'), 'const version = "1.14.5"\n', 'utf8')
  writeFileSync(join(repo, 'docs', 'release.md'), 'Release notes\n', 'utf8')
  const before = commit(repo, 'baseline')

  writeFileSync(join(repo, 'VERSION'), '1.14.6\n', 'utf8')
  writeFileSync(join(repo, 'frontend', 'app.js'), 'const version = "1.14.6"\n', 'utf8')
  commit(repo, 'prepare app release')
  writeFileSync(join(repo, 'docs', 'release.md'), 'Release notes finalized\n', 'utf8')
  const sha = commit(repo, 'finalize release documentation')

  const workflow = readFileSync(workflowUrl, 'utf8')
  const context = { eventName: 'push', before, sha }
  const script = extractCheckScript(workflow).replaceAll('${{ github.event_name }}', context.eventName)
    .replaceAll('${{ github.event.before }}', context.before)
    .replaceAll('${{ github.sha }}', context.sha)
  const outputPath = join(repo, 'github-output.txt')

  execFileSync('bash', ['-e', '-u', '-o', 'pipefail', '-c', script], {
    cwd: repo,
    env: {
      ...process.env,
      GITHUB_EVENT_NAME: context.eventName,
      GITHUB_SHA: context.sha,
      GITHUB_OUTPUT: outputPath,
      PUSH_BEFORE: context.before,
    },
  })

  assert.equal(readFileSync(outputPath, 'utf8'), 'should_release=true\n')
})
