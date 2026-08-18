import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const viewsDirectory = new URL('./', import.meta.url)

test('notes discovery controls use readable Chinese labels', async () => {
  const source = await readFile(new URL('./Notes.vue', viewsDirectory), 'utf8')

  assert.match(source, /aria-label="\u6392\u5e8f"/)
  assert.match(source, />\u6700\u8fd1\u6253\u5f00<\/option>/)
  assert.match(source, />\u6700\u8fd1\u66f4\u65b0<\/option>/)
  assert.match(source, /aria-label="\u7b14\u8bb0\u672c\u7b5b\u9009"/)
  assert.doesNotMatch(source, /\u93ba\u6391\u7c2d|\u93c8\u5100\u677f\u621a\u5f48\u6d93\u5bee/)
})

test('shop search overrides the desktop flex basis on mobile', async () => {
  const source = await readFile(new URL('./Shop.vue', viewsDirectory), 'utf8')

  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search \{[\s\S]*?flex: 0 0 44px[\s\S]*?height: 44px/)
  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search input \{[\s\S]*?height: 100%/)
})

test('business-locked todo and shop actions stay clickable and explain their lock', async () => {
  const [todos, shop] = await Promise.all([
    readFile(new URL('./Todos.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Shop.vue', viewsDirectory), 'utf8'),
  ])

  assert.match(todos, /function explainBlocked\(/)
  assert.match(todos, /function explainBlocked\(message\)[\s\S]*showError\(message\)/)
  assert.match(todos, /已完成|不可完成/)
  assert.match(todos, /aria-disabled/)
  assert.match(shop, /function explainBlocked\(/)
  assert.match(shop, /金币不足|售罄/)
  assert.match(shop, /aria-disabled/)
})

test('todo habit completion uses the server completed_today field for all lock states', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')

  assert.match(source, /'todo-card--completed': habit\.completed_today/)
  assert.match(source, /'complete-btn--done': habit\.completed_today/)
  assert.match(source, /:aria-disabled="habit\.completed_today"/)
  assert.match(source, /if \(habit\.completed_today\)/)
  assert.doesNotMatch(source, /habit\.is_active/)
})

test('backpack business actions expose a visible blocked-action feedback path', async () => {
  const source = await readFile(new URL('./Backpack.vue', viewsDirectory), 'utf8')

  assert.match(source, /function explainBlocked\(/)
  assert.match(source, /不可使用|不可装备|不可丢弃/)
  assert.match(source, /aria-disabled/)
})

test('cross-item in-flight actions explain the shared lock without submitting', async () => {
  const [todos, shop, backpack, project] = await Promise.all([
    readFile(new URL('./Todos.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Shop.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Backpack.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8'),
  ])

  assert.match(todos, /if \(completingId\.value\) \{\s*explainBlocked\(/)
  assert.match(todos, /if \(completingSubtaskId\.value\) \{\s*explainBlocked\(/)
  assert.match(shop, /if \(purchasingId\.value\) \{\s*explainBlocked\(/)
  assert.match(backpack, /if \(actionId\.value\) \{\s*explainBlocked\(/)
  assert.match(project, /if \(completingTaskId\.value\) \{\s*showError\(/)
})

test('subtask deletion blocks cross-item requests with handler feedback and loading semantics', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')
  const handler = source.match(/async function deleteSubtask\(subtask, taskId\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(handler, 'deleteSubtask handler must remain available for the template contract')
  assert.match(handler, /if \(deletingSubtaskId\.value\) \{\s*explainBlocked\(['"]已有其他子任务正在删除，请等待完成后再试。['"]\);\s*return\s*\}/)
  assert.match(source, /:aria-disabled="Boolean\(deletingSubtaskId\)"/)
  assert.match(source, /v-if="deletingSubtaskId === subtask\.id"[\s\S]*loading-spinner/)
})

test('home daily summary keeps request failures separate from the legitimate empty state', async () => {
  const source = await readFile(new URL('./Home.vue', viewsDirectory), 'utf8')

  assert.match(source, /dailyError/)
  assert.match(source, /v-else-if="dailyError"[\s\S]*重试[\s\S]*fetchDailySummary/)
  assert.match(source, /dailyError\.value\s*=\s*getErrorMessage\(e/)
})
