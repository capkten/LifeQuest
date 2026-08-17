import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const srcDirectory = new URL('../', import.meta.url)

test('router includes authenticated cultivation routes', async () => {
  const source = await readFile(new URL('../router/index.js', import.meta.url), 'utf8')

  assert.match(source, /path: ['"]cultivation['"]/, 'cultivation route is missing')
  assert.match(source, /path: ['"]tribulations['"]/, 'tribulations route is missing')
})

test('todo page keeps the legacy reward fallback', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')

  assert.match(source, /coins_reward/)
  assert.match(source, /exp_reward/)
  assert.match(source, /cultivation|修为/)
})

test('cultivation service keeps endpoint paths in one module', async () => {
  const source = await readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8')
  const apiSource = await readFile(new URL('../services/api.js', import.meta.url), 'utf8')

  assert.match(source, /import\s+api\s+from\s+['"]\.\/api['"]/)
  assert.match(apiSource, /baseURL:\s*apiBaseUrl/)
  assert.match(source, /['"]\/cultivation\/overview['"]\)/)
  assert.match(source, /['"]\/cultivation\/world['"]\)/)
  assert.match(source, /['"]\/cultivation\/npcs['"]\)/)
  assert.match(source, /['"]\/cultivation\/tribulation\/preview['"]\)/)
  assert.ok(source.includes("'/cultivation/tribulation/attempt'"))
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
  assert.match(resourceSummary, /aria-labelledby="resource-summary-title"/)
  assert.match(rewardToast, /role="status"/)
  assert.match(rewardToast, /<Close\s*\/>/)
  assert.match(probability, /defineEmits\(\[[^\]]*'attempt'/)
  assert.match(probability, /attempting|submitting/)
  assert.match(probability, /:aria-busy="operationBusy"/)
  assert.match(probability, /const operationBusy = computed\(\(\) => props\.loading\s*\|\|\s*props\.attempting\s*\|\|\s*props\.submitting\)/)
  assert.match(probability, /<button[^>]+:disabled="[^"]*loading[^"\n]*operationBusy[^>]*"[^>]+@click="\$emit\('retry'\)"/)
  assert.match(probability, /<button[^>]+:disabled="[^"]*loading[^"]*operationBusy[^>]*"[^>]+@click="\$emit\('attempt'\)"/)
  assert.match(probability, /aria-live="polite"/)
  assert.match(styles, /cultivation-slot-grid[\s\S]*min-height/)
  assert.match(styles, /prefers-reduced-motion/)
  assert.match(slots, /error/)
  assert.match(slots, /No technique slots available/)
  assert.match(slots, /:disabled="[^"]*(busy|loading)/)
  assert.match(mapNode, /locked/)
  assert.match(mapNode, /Locked/)
  assert.match(mapNode, /:disabled="isLocked"/)
  assert.match(npcTimeline, /fixed_core/)
  assert.match(npcTimeline, /recently_met/)
  assert.match(npcTimeline, /events/)
  assert.match(npcTimeline, /Array\.isArray/)
  assert.doesNotMatch(npcTimeline, /props\.npcs\.map/)
  assert.match(npcTimeline, /index\s*\+\s*1/)
  assert.match(npcTimeline, /Cultivation event|NPC record|Relationship record/)
  assert.match([mapNode, npcTimeline].join('\n'), /aria-label/)
})
