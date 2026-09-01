import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)))
const versionFile = resolve(repositoryRoot, 'VERSION')
const frontendPackageFile = resolve(repositoryRoot, 'frontend/package.json')
const frontendLockFile = resolve(repositoryRoot, 'frontend/package-lock.json')
const desktopPackageFile = resolve(repositoryRoot, 'desktop/package.json')
const desktopLockFile = resolve(repositoryRoot, 'desktop/package-lock.json')
const desktopCargoFile = resolve(repositoryRoot, 'desktop/src-tauri/Cargo.toml')
const desktopConfigFile = resolve(repositoryRoot, 'desktop/src-tauri/tauri.conf.json')

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

try {
  updatePackage(desktopPackageFile)
  updatePackage(desktopLockFile, true)
  const cargo = readFileSync(desktopCargoFile, 'utf8')
  if (!/^version\s*=\s*"\d+\.\d+\.\d+"\s*$/m.test(cargo)) {
    throw new Error('desktop Cargo.toml package version was not found')
  }
  const updatedCargo = cargo.replace(/^(version\s*=\s*")\d+\.\d+\.\d+("\s*$)/m, `$1${version}$2`)
  writeFileSync(desktopCargoFile, updatedCargo, 'utf8')

  const desktopConfig = JSON.parse(readFileSync(desktopConfigFile, 'utf8'))
  desktopConfig.version = version
  writeFileSync(desktopConfigFile, `${JSON.stringify(desktopConfig, null, 2)}\n`, 'utf8')
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}
console.log(`Synchronized frontend metadata to ${version}`)
