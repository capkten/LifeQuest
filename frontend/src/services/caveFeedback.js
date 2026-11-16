import { ref } from 'vue'

export function createCaveFeedback({ platform = 'web', storage = globalThis.localStorage, createAudioContext = () => new (globalThis.AudioContext || globalThis.webkitAudioContext)(), haptic = async () => { const { Haptics, ImpactStyle } = await import('@capacitor/haptics'); await Haptics.impact({ style: ImpactStyle.Light }) } } = {}) {
  function preference(key, fallback) {
    try { const value = storage?.getItem(`cave:${key}`); return value === null || value === undefined ? fallback : value === 'true' } catch { return fallback }
  }
  const soundEnabled = ref(preference('sound', platform === 'android'))
  const hapticsEnabled = ref(preference('haptics', platform === 'android' || platform === 'ios'))
  function save(key, value) { try { storage?.setItem(`cave:${key}`, String(value)) } catch {} }
  function setSoundEnabled(value) { soundEnabled.value = Boolean(value); save('sound', soundEnabled.value) }
  function setHapticsEnabled(value) { hapticsEnabled.value = Boolean(value); save('haptics', hapticsEnabled.value) }

  let context = null
  let disposed = false
  async function unlockFromGesture() {
    if (disposed || !soundEnabled.value) return
    try {
      context ||= createAudioContext()
      if (context?.state === 'suspended') await context.resume()
    } catch { context = null }
  }
  async function play(cue) {
    if (disposed) return
    if (cue === 'complete' && hapticsEnabled.value && ['android', 'ios'].includes(platform)) {
      try { await haptic() } catch {}
    }
    if (!soundEnabled.value || !context || context.state !== 'running') return
    try {
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.frequency.value = { start: 440, end: 330, complete: 660 }[cue] || 440
      oscillator.connect(gain)
      gain.connect(context.destination)
      gain.gain.setValueAtTime(0.08, context.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.35)
      oscillator.start(context.currentTime)
      oscillator.stop(context.currentTime + 0.36)
    } catch {}
  }
  function dispose() {
    disposed = true
    context?.close()?.catch(() => {})
    context = null
  }

  return { soundEnabled, hapticsEnabled, setSoundEnabled, setHapticsEnabled, unlockFromGesture, play, dispose }
}
