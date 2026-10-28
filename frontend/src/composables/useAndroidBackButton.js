import { onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'

const OVERLAY_SELECTORS = [
  '[role="dialog"]',
  '.el-overlay',
  '.el-drawer',
  '.dialog-overlay',
  '.modal-overlay',
]

function isVisible(element) {
  if (!element) return false
  const style = window.getComputedStyle(element)
  if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false
  const rect = element.getBoundingClientRect()
  return rect.width > 0 && rect.height > 0
}

/**
 * Returns the topmost visible overlay so the back gesture can close it before
 * navigating. Dispatching on the overlay itself (rather than on document) is
 * what makes both Element Plus dialogs and the hand-rolled `@keydown.esc`
 * dialogs in this codebase react.
 */
function findTopOverlay() {
  const overlays = OVERLAY_SELECTORS
    .flatMap((selector) => [...document.querySelectorAll(selector)])
    .filter(isVisible)
  return overlays.length ? overlays[overlays.length - 1] : null
}

function closeTopOverlay() {
  const overlay = findTopOverlay()
  if (!overlay) return false
  overlay.dispatchEvent(new KeyboardEvent('keydown', {
    key: 'Escape',
    code: 'Escape',
    keyCode: 27,
    which: 27,
    bubbles: true,
    cancelable: true,
  }))
  return true
}

/**
 * Android hardware back: close an open overlay, otherwise walk the history,
 * otherwise leave the app from the home screen. Without this listener the OS
 * exits the whole app from any of the ~30 routes.
 */
export function useAndroidBackButton() {
  if (!Capacitor.isNativePlatform() || Capacitor.getPlatform() !== 'android') return

  const router = useRouter()
  const route = useRoute()
  let listener = null

  onMounted(async () => {
    listener = await App.addListener('backButton', ({ canGoBack }) => {
      if (closeTopOverlay()) return

      if (canGoBack || window.history.state?.back) {
        router.back()
        return
      }

      if (route.name !== 'Home') {
        router.replace({ name: 'Home' })
        return
      }

      App.exitApp()
    })
  })

  onUnmounted(() => {
    listener?.remove()
    listener = null
  })
}
