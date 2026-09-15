import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('todo view consumes the server-owned habit state contract', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')

  assert.match(source, /habit\.is_active/)
  assert.match(source, /habit\.paused_today/)
  assert.match(source, /habit\.scheduled_today/)
})
