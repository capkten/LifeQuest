import { onMounted, onUnmounted, ref } from 'vue'
import { App } from '@capacitor/app'
import { Browser } from '@capacitor/browser'
import { Capacitor, CapacitorHttp } from '@capacitor/core'

const manifestUrl = import.meta.env.VITE_ANDROID_UPDATE_MANIFEST_URL
const update = ref(null)
const checking = ref(false)
const downloading = ref(false)
const updateError = ref('')
const downloadProgress = ref(0)
const downloadStatus = ref('idle')

let progressListener = null

function parseVersionCode(value) {
  const code = Number(value)
  return Number.isFinite(code) ? code : 0
}

function isNewerVersion(remote, current) {
  const remoteCode = parseVersionCode(remote)
  return remoteCode > 0 && remoteCode > parseVersionCode(current)
}

/**
 * GitHub release assets redirect to release-assets.githubusercontent.com and do
 * not send CORS headers, so the WebView fetch fails even when the URL is
 * reachable. The native HTTP client bypasses CORS entirely, so it is the
 * fallback that keeps update checks working.
 */
async function fetchManifest(url) {
  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (response.ok) return await response.json()
  } catch (error) {
    // fall through to the native client
  }

  try {
    const response = await CapacitorHttp.get({
      url,
      connectTimeout: 15000,
      readTimeout: 20000,
    })
    if (response.status >= 200 && response.status < 300) {
      return typeof response.data === 'string' ? JSON.parse(response.data) : response.data
    }
  } catch (error) {
    console.warn('App update manifest unavailable:', error)
  }

  return null
}

async function checkForUpdate() {
  if (Capacitor.getPlatform() !== 'android' || !manifestUrl || checking.value || update.value) return

  checking.value = true
  try {
    const [{ build }, manifest] = await Promise.all([
      App.getInfo(),
      fetchManifest(manifestUrl),
    ])
    if (!manifest) return

    if (isNewerVersion(manifest.versionCode, build) && manifest.downloadUrl) {
      update.value = {
        versionName: manifest.versionName || `版本 ${manifest.versionCode}`,
        releaseNotes: manifest.releaseNotes || '包含功能改进和问题修复。',
        downloadUrl: manifest.downloadUrl,
        releaseUrl: manifest.releaseUrl || manifest.downloadUrl,
        forceUpdate: manifest.forceUpdate === true,
      }
    }
  } catch (error) {
    console.warn('App update check failed:', error)
  } finally {
    checking.value = false
  }
}

function dismissUpdate() {
  if (!update.value?.forceUpdate) update.value = null
}

async function startUpdate(AppUpdater) {
  if (!update.value?.downloadUrl || downloading.value) return
  downloading.value = true
  downloadProgress.value = 0
  downloadStatus.value = 'starting'
  updateError.value = ''
  try {
    if (!progressListener) {
      progressListener = await AppUpdater.addListener('downloadProgress', (event = {}) => {
        downloadStatus.value = event.state || 'downloading'
        if (Number.isFinite(Number(event.percent)) && Number(event.percent) >= 0) {
          downloadProgress.value = Math.min(100, Math.round(Number(event.percent)))
        }
        if (downloadStatus.value === 'failed') {
          downloading.value = false
          updateError.value = event.message || '更新下载失败，请打开 GitHub 手动下载。'
        } else if (downloadStatus.value === 'completed') {
          downloading.value = false
          downloadStatus.value = 'installing'
        }
      })
    }
    await AppUpdater.startDownload({ url: update.value.downloadUrl })
  } catch (error) {
    downloading.value = false
    downloadStatus.value = 'failed'
    updateError.value = error?.message || '无法开始下载更新，请稍后重试。'
  }
}

async function openGithubDownload() {
  const url = update.value?.releaseUrl || update.value?.downloadUrl
  if (!url) return
  try {
    await Browser.open({ url })
  } catch (error) {
    updateError.value = error?.message || '无法打开 GitHub 下载页面。'
  }
}

export function useAppUpdate(AppUpdater) {
  let appStateListener = null

  onMounted(async () => {
    await checkForUpdate()
    // Users who launched the app before a release was published would otherwise
    // never see the prompt until the next cold start.
    appStateListener = await App.addListener('appStateChange', ({ isActive }) => {
      if (isActive) checkForUpdate()
    })
  })

  onUnmounted(() => {
    appStateListener?.remove()
    appStateListener = null
  })

  return {
    update,
    checking,
    checkForUpdate,
    downloading,
    downloadProgress,
    downloadStatus,
    updateError,
    startUpdate: () => startUpdate(AppUpdater),
    openGithubDownload,
    dismissUpdate,
  }
}
