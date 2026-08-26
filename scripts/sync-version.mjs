import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)))
const versionFile = resolve(repositoryRoot, 'VERSION')
const frontendPackageFile = resolve(repositoryRoot, 'frontend/package.json')
const frontendLockFile = resolve(repositoryRoot, 'frontend/package-lock.json')

const version = readFileSync(versionFile, 'utf8').trim()
if (!/^\d+\.\d+\.\d+$/.test(version)) {
  throw new Error(`VERSION must contain a semantic version like 1.8.2, got: ${version}`)
}

function updatePackage(filePath, updateRootPackage = false) {
  const packageJson = JSON.parse(readFileSync(filePath, 'utf8'))
  packageJson.version = version
  if (updateRootPackage && packageJson.packages?.['']) {
    packageJson.packages[''].version = version
  }
  writeFileSync(filePath, `${JSON.stringify(packageJson, null, 2)}\n`, 'utf8')
}

updatePackage(frontendPackageFile)
updatePackage(frontendLockFile, true)
console.log(`Synchronized frontend metadata to ${version}`)
