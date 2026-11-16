import test from 'node:test'
import assert from 'node:assert/strict'
import { createCaveFeedback } from './caveFeedback.js'

test('Android sound defaults on but stays silent until a user gesture', async () => {
  let opened = 0
  const feedback = createCaveFeedback({ platform: 'android', storage: null, createAudioContext: () => { opened += 1 } })
  assert.equal(feedback.soundEnabled.value, true)
  await feedback.play('start')
  assert.equal(opened, 0)
  feedback.dispose()
})

test('user gestures unlock start, end and completion sounds, and disabling stops playback', async () => {
  const tones = []
  let closed = false
  const context = {
    currentTime: 0, destination: {}, state: 'suspended',
    async resume() { this.state = 'running' },
    async close() { closed = true },
    createOscillator() { return { frequency: { value: 0 }, connect() {}, start() { tones.push(this.frequency.value) }, stop() {} } },
    createGain() { return { gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {} } },
  }
  const feedback = createCaveFeedback({ platform: 'android', storage: null, createAudioContext: () => context })
  await feedback.unlockFromGesture()
  for (const cue of ['start', 'end', 'complete']) await feedback.play(cue)
  assert.deepEqual(tones, [440, 330, 660])
  feedback.setSoundEnabled(false)
  await feedback.play('complete')
  assert.equal(tones.length, 3)
  feedback.dispose()
  assert.equal(closed, true)
})

test('mobile completion offers one light touch independently of sound and can be disabled', async () => {
  const impacts = []
  const feedback = createCaveFeedback({ platform: 'android', storage: null, haptic: async () => impacts.push('light') })
  feedback.setSoundEnabled(false)
  for (const cue of ['start', 'end', 'complete']) await feedback.play(cue)
  assert.deepEqual(impacts, ['light'])
  feedback.setHapticsEnabled(false)
  await feedback.play('complete')
  assert.deepEqual(impacts, ['light'])
})

test('sound and touch preferences survive restart, including disabling Android sound', () => {
  const values = new Map()
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) }
  const web = createCaveFeedback({ storage })
  assert.equal(web.soundEnabled.value, false)
  web.setSoundEnabled(true)
  web.setHapticsEnabled(false)
  assert.equal(createCaveFeedback({ storage }).soundEnabled.value, true)
  assert.equal(createCaveFeedback({ platform: 'android', storage }).hapticsEnabled.value, false)
  web.setSoundEnabled(false)
  assert.equal(createCaveFeedback({ platform: 'android', storage }).soundEnabled.value, false)
})
