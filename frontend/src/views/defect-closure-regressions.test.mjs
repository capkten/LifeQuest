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
