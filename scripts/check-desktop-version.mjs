import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)))
const version = readFileSync(resolve(repositoryRoot, 'VERSION'), 'utf8').trim()
const packageJson = JSON.parse(readFileSync(resolve(repositoryRoot, 'desktop/package.json'), 'utf8'))
const packageLock = JSON.parse(readFileSync(resolve(repositoryRoot, 'desktop/package-lock.json'), 'utf8'))
const tauriConfig = JSON.parse(readFileSync(resolve(repositoryRoot, 'desktop/src-tauri/tauri.conf.json'), 'utf8'))
const cargo = readFileSync(resolve(repositoryRoot, 'desktop/src-tauri/Cargo.toml'), 'utf8')
const cargoVersion = cargo.match(/^version\s*=\s*"([^"]+)"\s*$/m)?.[1]

const mismatches = [
  ['desktop/package.json', packageJson.version],
  ['desktop/package-lock.json', packageLock.version],
  ['desktop/package-lock.json packages[""].version', packageLock.packages?.['']?.version],
  ['desktop/src-tauri/tauri.conf.json', tauriConfig.version],
  ['desktop/src-tauri/Cargo.toml', cargoVersion],
].filter(([, value]) => value !== version)

if (mismatches.length > 0) {
  throw new Error(`Desktop version mismatch: ${mismatches.map(([name, value]) => `${name}=${value}`).join(', ')}; VERSION=${version}`)
}

console.log(`Desktop version check passed: ${version}`)
