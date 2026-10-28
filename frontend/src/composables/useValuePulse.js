import { onUnmounted, ref, watch } from 'vue'

function prefersReducedMotion() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Flags a short "value went up" pulse for reward counters such as coins and
 * experience. It only fires on an increase, so page loads and decreases stay
 * quiet, and it stays inert when the user asks for reduced motion.
 */
export function useValuePulse(source, { duration = 600 } = {}) {
  const pulsing = ref(false)
  let timer = null

  watch(source, (next, previous) => {
    if (previous === undefined || previous === null || next === null) return
    if (Number(next) <= Number(previous)) return
    if (prefersReducedMotion()) return

    pulsing.value = true
    clearTimeout(timer)
    timer = setTimeout(() => {
      pulsing.value = false
    }, duration)
  })

  onUnmounted(() => clearTimeout(timer))

  return { pulsing }
}
