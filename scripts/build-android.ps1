param(
    [string]$ApiBaseUrl = "",
    [switch]$OpenAndroidStudio,
    [switch]$BuildDebugApk
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$androidDir = Join-Path $frontendDir "android"

function Get-AndroidSdkPath {
    if ($env:ANDROID_HOME -and (Test-Path $env:ANDROID_HOME)) {
        return $env:ANDROID_HOME
    }

    if ($env:ANDROID_SDK_ROOT -and (Test-Path $env:ANDROID_SDK_ROOT)) {
        return $env:ANDROID_SDK_ROOT
    }

    $defaultSdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
    if (Test-Path $defaultSdk) {
        return $defaultSdk
    }

    return $null
}

Push-Location $frontendDir
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..."
        npm install
    }

    if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
        Write-Host "Building Android web assets with default Vite API base URL..."
        npm run build:android
    } else {
        Write-Host "Building Android web assets with API base URL: $ApiBaseUrl"
        $env:VITE_API_BASE_URL = $ApiBaseUrl
        npm run build:android
        Remove-Item Env:VITE_API_BASE_URL -ErrorAction SilentlyContinue
    }

    Write-Host "Syncing web assets to Android project..."
    npx cap sync android

    $sdkPath = Get-AndroidSdkPath
    if ($sdkPath) {
        $escapedSdkPath = $sdkPath.Replace('\', '\\')
        Set-Content -Path (Join-Path $androidDir "local.properties") -Value "sdk.dir=$escapedSdkPath" -Encoding ASCII
        Write-Host "Android SDK detected: $sdkPath"
    } else {
        Write-Warning "Android SDK not found. Install Android Studio / Android SDK before building APK."
    }

    if ($BuildDebugApk) {
        if (-not $sdkPath) {
            throw "Cannot build debug APK because Android SDK was not found."
        }

        Write-Host "Building debug APK..."
        Push-Location $androidDir
        try {
            .\gradlew.bat assembleDebug
        }
        finally {
            Pop-Location
        }

        Write-Host "Debug APK output:"
        Write-Host (Join-Path $androidDir "app\build\outputs\apk\debug\app-debug.apk")
    }

    if ($OpenAndroidStudio) {
        Write-Host "Opening Android Studio project..."
        npx cap open android
    } else {
        Write-Host "Android project synced. Open it later with: npm run cap:open:android"
    }
}
finally {
    Pop-Location
}
