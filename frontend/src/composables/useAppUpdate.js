import { ref } from 'vue'
import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'

const manifestUrl = import.meta.env.VITE_ANDROID_UPDATE_MANIFEST_URL
const update = ref(null)
const checking = ref(false)
const downloading = ref(false)
const updateError = ref('')

function isNewerVersion(remote, current) {
  return Number(remote) > Number(current)
}

async function checkForUpdate() {
  if (Capacitor.getPlatform() !== 'android' || !manifestUrl || checking.value || update.value) return

  checking.value = true
  try {
    const [{ build }, response] = await Promise.all([
      App.getInfo(),
      fetch(manifestUrl, { cache: 'no-store' }),
    ])
    if (!response.ok) return

    const manifest = await response.json()
    if (isNewerVersion(manifest.versionCode, build) && manifest.downloadUrl) {
      update.value = {
        versionName: manifest.versionName || `版本 ${manifest.versionCode}`,
        releaseNotes: manifest.releaseNotes || '包含功能改进和问题修复。',
        downloadUrl: manifest.downloadUrl,
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
  updateError.value = ''
  try {
    await AppUpdater.startDownload({ url: update.value.downloadUrl })
  } catch (error) {
    updateError.value = error?.message || '无法开始下载更新，请稍后重试。'
  } finally {
    downloading.value = false
  }
}

export function useAppUpdate(AppUpdater) {
  return {
    update,
    checking,
    checkForUpdate,
    downloading,
    updateError,
    startUpdate: () => startUpdate(AppUpdater),
    dismissUpdate,
  }
}
