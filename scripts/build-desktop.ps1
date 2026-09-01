$ErrorActionPreference = 'Stop'

Push-Location (Join-Path $PSScriptRoot '..')
try {
    npm --prefix frontend run check:version
    npm --prefix desktop run check:version
    npm --prefix frontend run build
    npm --prefix desktop run build
}
finally {
    Pop-Location
}
