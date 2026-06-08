import { ref, watch, onUnmounted } from 'vue'
import { resolveUrl } from '../services/api'

export function useResolvedImage(pathRef) {
  const src = ref('')

  let currentBlob = null

  async function load(path) {
    if (currentBlob) {
      URL.revokeObjectURL(currentBlob)
      currentBlob = null
    }
    if (!path) {
      src.value = ''
      return
    }
    const fullUrl = resolveUrl(path)
    if (!fullUrl.startsWith('http')) {
      src.value = fullUrl
      return
    }
    try {
      const res = await fetch(fullUrl)
      const blob = await res.blob()
      currentBlob = URL.createObjectURL(blob)
      src.value = currentBlob
    } catch {
      src.value = fullUrl
    }
  }

  watch(() => pathRef.value ?? pathRef, load, { immediate: true })

  onUnmounted(() => {
    if (currentBlob) URL.revokeObjectURL(currentBlob)
  })

  return src
}
