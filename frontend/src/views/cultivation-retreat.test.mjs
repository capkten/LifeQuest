import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('retreat countdown ring component defines svg ring, progress stroke and breathing glow', async () => {
  const source = await readFile(
    new URL('../components/retreat/RetreatCountdownRing.vue', import.meta.url),
    'utf8'
  )

  // Verify SVG ring markup
  assert.match(source, /<svg/i, 'SVG element missing')
  assert.match(source, /stroke-dasharray/i, 'stroke-dasharray calculation missing')
  assert.match(source, /stroke-dashoffset/i, 'stroke-dashoffset calculation missing')
  assert.match(source, /formatTime|remainingFormatted/i, 'time formatting missing')
  assert.match(source, /breathing|pulse|glow/i, 'breathing/glow animation style missing')
})

test('cultivation retreat modal integrates composable, presets, fullscreen and settlement', async () => {
  const source = await readFile(
    new URL('../components/retreat/CultivationRetreatModal.vue', import.meta.url),
    'utf8'
  )

  // Verify composable integration
  assert.match(source, /useCultivationRetreat/, 'useCultivationRetreat not used')
  assert.match(source, /RetreatCountdownRing/, 'RetreatCountdownRing not embedded')
  assert.match(source, /toggleFullscreen|requestFullscreen/, 'fullscreen toggle missing')
  assert.match(source, /15|25|45|60/, 'duration presets missing')
  assert.match(source, /abortRetreat/, 'abortRetreat missing')
  assert.match(source, /completeRetreat/, 'completeRetreat missing')
  assert.match(source, /markTodoComplete|mark_todo_complete/, 'todo complete linkage option missing')
})
