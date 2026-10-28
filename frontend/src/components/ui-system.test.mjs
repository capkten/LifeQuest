import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(path, import.meta.url), 'utf8')
const ui = (name) => source(`./ui/${name}`)

test('AppState renders one state surface with role switching and a business action slot', async () => {
  const appState = await ui('AppState.vue')

  assert.match(appState, /defineProps\(\{[\s\S]*state:/)
  assert.match(appState, /state === 'error' \? 'alert' : 'status'/)
  assert.match(appState, /class="app-state"/)
  assert.match(appState, /app-state--\$\{/)
  assert.match(appState, /<slot name="actions"/)
  assert.match(appState, /aria-busy/)
})

test('AppButton keeps one pressable surface with variants, loading and block semantics', async () => {
  const appButton = await ui('AppButton.vue')

  assert.match(appButton, /variant:\s*\{\s*type:\s*String,\s*default:\s*'primary'/)
  assert.match(appButton, /size:\s*\{\s*type:\s*String,\s*default:\s*'md'/)
  assert.match(appButton, /class="app-button"/)
  assert.match(appButton, /app-button--\$\{variant\}/)
  assert.match(appButton, /:disabled="disabled \|\| loading"/)
  assert.match(appButton, /:aria-busy="loading \? 'true' : undefined"/)
  assert.match(appButton, /min-height:\s*var\(--touch-target-min\)/)
})

test('AppCard exposes an optional interactive surface without duplicating page radii', async () => {
  const appCard = await ui('AppCard.vue')

  assert.match(appCard, /interactive:\s*\{\s*type:\s*Boolean,\s*default:\s*false/)
  assert.match(appCard, /class="app-card"/)
  assert.match(appCard, /app-card--interactive/)
  assert.match(appCard, /border-radius:\s*var\(--radius-card\)/)
})

test('AppBadge maps tones onto the shared colour tokens', async () => {
  const appBadge = await ui('AppBadge.vue')

  assert.match(appBadge, /tone:\s*\{\s*type:\s*String,\s*default:\s*'neutral'/)
  assert.match(appBadge, /class="app-badge"/)
  assert.match(appBadge, /app-badge--\$\{tone\}/)
  assert.match(appBadge, /--color-gold/)
})

test('AppField wires the label to its control and keeps hint and error slots accessible', async () => {
  const appField = await ui('AppField.vue')

  assert.match(appField, /:for="fieldId"/)
  assert.match(appField, /:id="fieldId"/)
  assert.match(appField, /aria-describedby/)
  assert.match(appField, /class="app-field"/)
})

test('AppSheet is a body-level dialog that closes on escape and backdrop but not while pending', async () => {
  const appSheet = await ui('AppSheet.vue')

  assert.match(appSheet, /<Teleport to="body">/)
  assert.match(appSheet, /role="dialog"/)
  assert.match(appSheet, /aria-modal="true"/)
  assert.match(appSheet, /@keydown\.esc="requestClose"/)
  assert.match(appSheet, /@click\.self="requestClose"/)
  assert.match(appSheet, /if \((?:props\.)?pending(?:\.value)?\) return/)
  assert.match(appSheet, /emit\('update:modelValue', false\)/)
})

test('AppTabs exposes a real tablist with selected and count semantics', async () => {
  const appTabs = await ui('AppTabs.vue')

  assert.match(appTabs, /role="tablist"/)
  assert.match(appTabs, /role="tab"/)
  assert.match(appTabs, /:aria-selected="item\.key === modelValue"/)
  assert.match(appTabs, /emit\('update:modelValue'/)
})

test('AppList renders dense rows without per-page list scaffolding', async () => {
  const appList = await ui('AppList.vue')

  assert.match(appList, /dense:\s*\{\s*type:\s*Boolean,\s*default:\s*false/)
  assert.match(appList, /class="app-list"/)
  assert.match(appList, /app-list--dense/)
  assert.match(appList, /<slot \/>/)
})

test('shared state surfaces keep a single source of truth in the design layer', async () => {
  const [app, overrides] = await Promise.all([
    source('../App.vue'),
    source('../styles/stitch-overrides.css'),
  ])

  // The 16px form rule already lives in the shared mobile contract.
  assert.match(overrides, /input,\s*\n\s*textarea,\s*\n\s*select \{\s*\n\s*font-size: 16px !important;/)
  assert.doesNotMatch(app, /input:not\(\[type='checkbox'\]\)[\s\S]{0,120}font-size: 16px/)
})

test('Shop renders through the shared kit instead of page-local state markup', async () => {
  const shop = await source('../views/Shop.vue')

  assert.match(shop, /import AppState from '\.\.\/components\/ui\/AppState\.vue'/)
  assert.match(shop, /import AppTabs from '\.\.\/components\/ui\/AppTabs\.vue'/)
  assert.match(shop, /import AppBadge from '\.\.\/components\/ui\/AppBadge\.vue'/)

  assert.match(shop, /<AppState v-if="loading"/)
  assert.match(shop, /<AppState\s+v-else-if="error"/)
  assert.match(shop, /state="error"[\s\S]{0,200}重试/)
  assert.match(shop, /<AppTabs[\s\S]{0,160}:items="categoryTabs"/)
  assert.match(shop, /<AppBadge v-if="item\.category"/)

  // The page-local duplicates are gone rather than shadowing the kit.
  assert.doesNotMatch(shop, /class="(?:loading-state|error-state|empty-state)"/)
  assert.doesNotMatch(shop, /^\.loading-state\s*\{/m)
  assert.doesNotMatch(shop, /^\.empty-state\s*\{/m)
  assert.doesNotMatch(shop, /^\.shop-category\s*\{/m)
})

test('list pages adopt AppState for load failures and keep a retry action', async () => {
  const pages = {
    'Projects.vue': /@click="fetchProjects"/,
    'Backpack.vue': /@click="fetchAll"/,
    'Finance.vue': /@click="fetchDashboard"/,
    'Stats.vue': /@click="fetchAll"/,
  }

  for (const [file, retry] of Object.entries(pages)) {
    const page = await source(`../views/${file}`)
    assert.match(page, /import AppState from/, `${file} must import AppState`)
    assert.match(page, /state="loading"/, `${file} must render the loading state through AppState`)
    assert.match(page, /state="error"/, `${file} must render the error state through AppState`)
    assert.match(page, retry, `${file} must keep its retry handler wired to the error action`)
    assert.match(page, /<AppButton[\s\S]{0,80}重试/, `${file} must retry through the shared button`)
    assert.doesNotMatch(page, /class="(?:loading-state|error-state)"/, `${file} must not keep page-local state markup`)
  }
})

test('Stats no longer reserves the bottom navigation inset twice', async () => {
  const stats = await source('../views/Stats.vue')

  assert.doesNotMatch(stats, /padding-bottom:\s*calc\(var\(--spacing-md\) \+ var\(--bottom-nav-height\)\)/)
})

test('interface icons come from the lucide set instead of emoji glyphs', async () => {
  const files = [
    '../views/Shop.vue',
    '../views/Todos.vue',
    '../components/home/TodayWorkbench.vue',
    '../components/notes/NoteViewer.vue',
    '../components/retreat/CultivationRetreatModal.vue',
    '../components/retreat/EncounterCatalogDrawer.vue',
    '../components/retreat/EncounterScrollDialog.vue',
  ]

  for (const file of files) {
    const content = await source(file)
    assert.doesNotMatch(content, /[\u{1F300}-\u{1FAFF}\u{2728}]/u, `${file} must not render emoji as an icon`)
  }

  const withIcons = ['../views/Shop.vue', '../views/Todos.vue', '../components/home/TodayWorkbench.vue']
  for (const file of withIcons) {
    const content = await source(file)
    assert.match(content, /from 'lucide-vue-next'/, `${file} must take its icons from lucide`)
  }
})
