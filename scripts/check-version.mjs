import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)))
const version = readFileSync(resolve(repositoryRoot, 'VERSION'), 'utf8').trim()
const packageJson = JSON.parse(readFileSync(resolve(repositoryRoot, 'frontend/package.json'), 'utf8'))
const packageLock = JSON.parse(readFileSync(resolve(repositoryRoot, 'frontend/package-lock.json'), 'utf8'))

if (!/^\d+\.\d+\.\d+$/.test(version)) {
  throw new Error(`VERSION must contain a semantic version like 1.8.2, got: ${version}`)
}

const resolvedVersions = [
  ['frontend/package.json', packageJson.version],
  ['frontend/package-lock.json', packageLock.version],
  ['frontend/package-lock.json packages[""].version', packageLock.packages?.['']?.version],
]
const mismatches = resolvedVersions.filter(([, value]) => value !== version)
if (mismatches.length > 0) {
  throw new Error(`Version mismatch: ${mismatches.map(([name, value]) => `${name}=${value}`).join(', ')}; VERSION=${version}`)
}

console.log(`Version check passed: ${version}`)
