import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('todo view consumes the server-owned habit state contract', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')

  assert.match(source, /habit\.is_active/)
  assert.match(source, /habit\.paused_today/)
  assert.match(source, /habit\.scheduled_today/)
})

test('calendar and stats render server-owned completion and cumulative experience', async () => {
  const calendar = await readFile(new URL('./Calendar.vue', import.meta.url), 'utf8')
  const stats = await readFile(new URL('./Stats.vue', import.meta.url), 'utf8')

  assert.match(calendar, /event-dot--['"] \+ dot\.status|dot\.status.*event-dot--/)
  assert.match(stats, /overview\.total_exp/)
})

test('goal editing does not settle a reward a second time', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')
  const saveItem = source.match(/async function saveItem\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(saveItem, 'saveItem must remain available')
  assert.doesNotMatch(saveItem, /settleCompletion\(/)
})

test('coin history uses the canonical filtered pagination contract', async () => {
  const service = await readFile(new URL('../services/coin.js', import.meta.url), 'utf8')
  const history = await readFile(new URL('./CoinHistory.vue', import.meta.url), 'utf8')

  assert.match(service, /coins\/history/)
  assert.match(history, /coin_type/)
  assert.match(history, /skip/)
  assert.match(history, /result\.transactions/)
  assert.doesNotMatch(history, /params\.type/)
  assert.doesNotMatch(history, /result\?\.data/)
})

test('coin history derives spending direction from transaction type', async () => {
  const history = await readFile(new URL('./CoinHistory.vue', import.meta.url), 'utf8')

  assert.match(history, /tx\.type === ['"]spend['"]\s*\? ['"]-['"] : ['"]\+['"]/)
  assert.match(history, /tx\.type === ['"]spend['"]\s*\? ['"]tx-icon--expense['"] : ['"]tx-icon--income['"]/)
  assert.doesNotMatch(history, /tx\.amount > 0 \? ['"]\+['"] : ['"]["']/)
})
