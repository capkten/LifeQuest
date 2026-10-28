import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('shop create dialog is a shared sheet built from fields and buttons', async () => {
  const shop = await source('./Shop.vue')

  assert.match(shop, /import AppSheet from '\.\.\/components\/ui\/AppSheet\.vue'/)
  assert.match(shop, /import AppField from '\.\.\/components\/ui\/AppField\.vue'/)
  assert.match(shop, /<AppSheet[\s\S]{0,240}v-model="showCreateDialog"/)
  assert.match(shop, /<AppField[\s\S]{0,160}label="商品名称"/)
  assert.match(shop, /#control="\{ id, ariaDescribedby \}"/)
  assert.match(shop, /native-type="submit"/)

  // The hand-rolled dialog scaffolding is gone rather than sitting alongside it.
  assert.doesNotMatch(shop, /<label class="form-label" for="item-name">/)
  assert.doesNotMatch(shop, /aria-labelledby="create-dialog-title"/)
})

test('shop item grid renders through the shared list primitive', async () => {
  const shop = await source('./Shop.vue')

  assert.match(shop, /import AppList from '\.\.\/components\/ui\/AppList\.vue'/)
  assert.match(shop, /<AppList v-else class="items-grid">/)
  assert.match(shop, /<li\s+v-for="\(item, index\) in filteredItems"/)
  assert.match(shop, /<\/AppList>/)
})

test('home quick actions use the shared card surface', async () => {
  const home = await source('./Home.vue')

  assert.match(home, /import AppCard from '\.\.\/components\/ui\/AppCard\.vue'/)
  assert.match(home, /<AppCard class="quick-actions-card">/)
})

test('numeric readouts share one tabular figure treatment', async () => {
  const [app, home, stats, profile] = await Promise.all([
    source('../App.vue'),
    source('./Home.vue'),
    source('./Stats.vue'),
    source('./Profile.vue'),
  ])

  assert.match(app, /\.metric-figure\s*\{[^}]*font-variant-numeric:\s*tabular-nums/)
  for (const [file, content] of [['Home.vue', home], ['Stats.vue', stats], ['Profile.vue', profile]]) {
    assert.match(content, /metric-figure/, `${file} must use the shared numeric treatment`)
  }
})

test('achievement titles carry the gold reward semantic', async () => {
  const profile = await source('./Profile.vue')
  const badge = profile.match(/\.profile-title-badge\s*\{[\s\S]*?\n\}/)?.[0] || ''

  assert.ok(badge, 'profile title badge styles must remain available')
  assert.match(badge, /--color-gold/)
})

test('motivation pulse is a shared composable that respects reduced motion', async () => {
  const [pulse, home] = await Promise.all([
    source('../composables/useValuePulse.js'),
    source('./Home.vue'),
  ])

  assert.match(pulse, /export function useValuePulse/)
  assert.match(pulse, /prefers-reduced-motion/)
  assert.match(pulse, /matchMedia/)
  assert.match(home, /useValuePulse/)
})

test('login keeps the card centred on phones and the brand on tablets', async () => {
  const login = await source('./Login.vue')
  const mobileBlock = login.match(/@media \(max-width: 767px\) \{[\s\S]*?\n\}/)?.[0] || ''

  assert.ok(mobileBlock, 'login needs a phone media query')
  assert.match(mobileBlock, /align-items:\s*center/)
  assert.doesNotMatch(mobileBlock, /margin-top:\s*8vh/)
})

test('shop page header no longer repeats its own title', async () => {
  const shop = await source('./Shop.vue')

  assert.doesNotMatch(shop, /<h2 class="page-title">商城<\/h2>/)
  assert.match(shop, /class="shop-header-meta[^"]*"/)
})

const PAGE_ROOTS = [
  'todos-page', 'shop-page', 'projects-page', 'profile-page', 'notes-page',
  'calendar-page', 'finance-page', 'stats-page', 'backpack-page', 'history-page',
  'coin-history-page', 'project-detail-page', 'edit-profile-page', 'file-manager',
]

test('page roots own no gutter and never reserve the bottom navigation twice', async () => {
  const { readdir } = await import('node:fs/promises')
  const files = (await readdir(new URL('.', import.meta.url))).filter((name) => name.endsWith('.vue'))

  for (const file of files) {
    const content = await source(`./${file}`)
    const rootPattern = new RegExp(`\\.(${PAGE_ROOTS.join('|')})\\s*\\{([^}]*)\\}`, 'g')
    for (const rule of content.matchAll(rootPattern)) {
      const body = rule[2]
      assert.doesNotMatch(
        body,
        /\bpadding(-(top|right|bottom|left))?\s*:/,
        `${file}: .${rule[1]} must not declare its own padding (the shell owns the gutter)`,
      )
    }
  }
})

test('high-traffic dialog submit bars stay reachable on phones', async () => {
  for (const file of ['Todos.vue', 'Finance.vue']) {
    const content = await source(`./${file}`)
    const actions = content.match(/\.dialog-actions\s*\{[^}]*position:\s*sticky[^}]*\}/)?.[0] || ''
    assert.ok(actions, `${file} must pin its dialog actions on mobile`)
    assert.match(actions, /bottom:\s*0/)
    assert.match(actions, /--safe-area-bottom/)
  }
})
