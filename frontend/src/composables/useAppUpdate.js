import { ref } from 'vue'
import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'

const manifestUrl = import.meta.env.VITE_ANDROID_UPDATE_MANIFEST_URL
const update = ref(null)
const checking = ref(false)

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

export function useAppUpdate() {
  return {
    update,
    checking,
    checkForUpdate,
    dismissUpdate,
  }
}
