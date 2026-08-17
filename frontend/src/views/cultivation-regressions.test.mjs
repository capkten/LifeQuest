import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const srcDirectory = new URL('../', import.meta.url)

test('cultivation service keeps endpoint paths in one module', async () => {
  const source = await readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8')

  assert.match(source, /\/api\/cultivation\/overview/)
  assert.match(source, /\/api\/cultivation\/tribulation\/preview/)
  assert.doesNotMatch(source, /final_probability|roll/)
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
  assert.match(probability, /defineEmits\(\[[^\]]*'attempt'/)
  assert.match(probability, /aria-live="polite"/)
  assert.match(styles, /cultivation-slot-grid[\s\S]*min-height/)
  assert.match(styles, /prefers-reduced-motion/)
  assert.match([mapNode, npcTimeline].join('\n'), /aria-label/)
})
