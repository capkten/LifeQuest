import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const read = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('android builds know where the update manifest lives', async () => {
  const env = await read('../../.env.android')
  const example = await read('../../.env.android.example')

  for (const [name, content] of [['.env.android', env], ['.env.android.example', example]]) {
    assert.match(
      content,
      /^VITE_ANDROID_UPDATE_MANIFEST_URL=https:\/\/life\.capkin\.cn\/latest\.json$/m,
      `${name} must point the updater at our own origin`,
    )
  }
})

test('the update check survives a blocked CORS request and re-runs on resume', async () => {
  const source = await read('../composables/useAppUpdate.js')

  // GitHub release assets redirect to a host without CORS headers, so the
  // WebView fetch alone is not enough.
  assert.match(source, /CapacitorHttp/)
  assert.match(source, /async function fetchManifest/)
  assert.match(source, /appStateChange/)
  assert.match(source, /onMounted\(async \(\) => \{[\s\S]*checkForUpdate\(\)/)

  // A malformed manifest version must not silently win the comparison.
  assert.match(source, /function parseVersionCode/)
  assert.match(source, /remoteCode > 0 && remoteCode >/)
})

test('deployment publishes the update manifest and package from our own origin', async () => {
  const script = await read('../../../deploy/update-systemd.sh')
  const workflow = await read('../../../.github/workflows/android-release.yml')

  assert.match(script, /publish_android_update\(\)/)
  assert.match(script, /latest\.json/)
  assert.match(script, /app-release\.apk/)
  assert.match(script, /manifest\['downloadUrl'\] = f'\{origin\}\/app-release\.apk'/)
  // A refresh failure must never fail the deployment.
  assert.match(script, /publish_android_update \|\| echo/)

  assert.match(workflow, /https:\/\/life\.capkin\.cn\/latest\.json/)
})

test('deployment keeps a runner-side fallback when the server cannot reach GitHub', async () => {
  const workflow = await read('../../../.github/workflows/deploy.yml')

  // Two independent paths: the server pulls from GitHub, and when that network
  // path is blocked the runner downloads and pushes the assets over SSH.
  assert.match(workflow, /publish_android_assets\(\)/)
  assert.match(workflow, /scp "\$\{SSH_ARGS\[@\]\}"/)
  assert.match(workflow, /publish_android_assets \|\| echo/)
})
