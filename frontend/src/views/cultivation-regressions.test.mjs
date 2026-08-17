import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const srcDirectory = new URL('../', import.meta.url)

test('cultivation service keeps endpoint paths in one module', async () => {
  const source = await readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8')

  assert.match(source, /['"]\/cultivation\/overview['"]/)
  assert.match(source, /['"]\/cultivation\/tribulation\/preview['"]/)
  assert.doesNotMatch(source, /['"]\/api\/cultivation\//)
  assert.doesNotMatch(source, /final_probability|roll/)
})

test('settlements update visible deltas and obtain an authoritative overview', async () => {
  const source = await readFile(new URL('../stores/cultivation.js', import.meta.url), 'utf8')

  assert.match(source, /settlement\.cultivation/)
  assert.match(source, /settlement\.spirit_stones/)
  assert.match(source, /overview\.value\s*=\s*\{/)
  assert.match(source, /await refresh\(\)/)
  assert.doesNotMatch(source, /nextOverview\s*=\s*settlement\s*\|\|\s*settlement/)
})

test('realm progress derives its percentage from StageProgress thresholds', async () => {
  const source = await readFile(new URL('../components/cultivation/RealmProgress.vue', import.meta.url), 'utf8')

  assert.match(source, /current_threshold/)
  assert.match(source, /next_threshold/)
  assert.match(source, /remaining/)
  assert.doesNotMatch(source, /progress\.percent/)
  assert.match(source, /aria-valuemax="100"/)
})

test('cultivation shared states expose accessible stable contracts', async () => {
  const [statusBar, realmProgress, resourceSummary, rewardToast, probability, slots, mapNode, npcTimeline, styles] = await Promise.all([
    'components/cultivation/CultivationStatusBar.vue',
    'components/cultivation/RealmProgress.vue',
    'components/cultivation/ResourceSummary.vue',
    'components/cultivation/RewardToast.vue',
    'components/cultivation/TribulationProbability.vue',
    'components/cultivation/TechniqueSlotGrid.vue',
    'components/cultivation/MapNode.vue',
    'components/cultivation/NpcTimeline.vue',
    'styles/stitch-overrides.css',
  ].map((path) => readFile(new URL(path, srcDirectory), 'utf8')))

  assert.match(statusBar, /aria-live="polite"/)
  assert.match(realmProgress, /aria-valuenow/)
  assert.match(resourceSummary, /aria-label/)
  assert.match(rewardToast, /role="status"/)
  assert.match(rewardToast, /<Close\s*\/>/)
  assert.match(probability, /defineEmits\(\[[^\]]*'attempt'/)
  assert.match(probability, /attempting|submitting/)
  assert.match(probability, /aria-busy/)
  assert.match(probability, /:disabled="[^"]*operationBusy/)
  assert.match(probability, /aria-live="polite"/)
  assert.match(styles, /cultivation-slot-grid[\s\S]*min-height/)
  assert.match(styles, /prefers-reduced-motion/)
  assert.match(slots, /error/)
  assert.match(slots, /No technique slots available/)
  assert.match(slots, /:disabled="[^"]*(busy|loading)/)
  assert.match(mapNode, /locked/)
  assert.match(mapNode, /Locked/)
  assert.match(mapNode, /:disabled="isLocked"/)
  assert.match(npcTimeline, /index/)
  assert.match(npcTimeline, /event|title|description/)
  assert.match([mapNode, npcTimeline].join('\n'), /aria-label/)
})
