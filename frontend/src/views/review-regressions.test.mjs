import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (name) => readFile(new URL(`./${name}`, import.meta.url), 'utf8')
const serviceSource = (name) => readFile(new URL(`../services/${name}`, import.meta.url), 'utf8')

test('review service requests the selected weekly review boundary', async () => {
  const service = await serviceSource('review.js')

  assert.match(service, /getWeeklyReview\s*\(/)
  assert.match(service, /\/review\/weekly/)
  assert.match(service, /week_start/)
})

test('weekly review page keeps retryable states and exposes execution links', async () => {
  const page = await source('WeeklyReview.vue')

  assert.match(page, /reviewService\.getWeeklyReview\(/)
  assert.match(page, /unfinished_high_priority/)
  assert.match(page, /projects_without_next_action/)
  assert.match(page, /suggestions/)
  assert.match(page, /note|notes|笔记/s)
  assert.match(page, /loading/)
  assert.match(page, /error/)
  assert.match(page, /重试/)
  assert.match(page, /@click="loadReview(?:\(\))?"/)
})

test('weekly review keeps occurrence context when opening a recurring task', async () => {
  const page = await source('WeeklyReview.vue')
  const todos = await source('Todos.vue')

  assert.match(page, /occurrence_date=.*item\.occurrence_date/)
  assert.match(todos, /route\.query\.occurrence_date/)
  assert.match(todos, /completeTask\(task\.id,/)
})

test('weekly review uses the layout main landmark and locks refresh requests', async () => {
  const page = await source('WeeklyReview.vue')

  assert.doesNotMatch(page, /<main\s+v-if="review"/)
  assert.match(page, /if \(loading\.value && review\.value\) return/)
  assert.match(page, /loading\.value = true/)
})

test('weekly review keeps streak changes in a horizontal summary row', async () => {
  const page = await source('WeeklyReview.vue')

  assert.match(page, /\.review-list-item > div\s*\{[\s\S]*justify-content:\s*space-between/)
  assert.match(page, /\.review-item-main,\s*\.suggestion-copy\s*\{[\s\S]*flex-direction:\s*column/)
  assert.doesNotMatch(page, /\.review-list-item > div,\s*\.review-item-main,\s*\.suggestion-copy\s*\{[^}]*flex-direction:\s*column/)
})

test('weekly review is reachable from the authenticated shell', async () => {
  const router = await readFile(new URL('../router/index.js', import.meta.url), 'utf8')
  const sidebar = await source('../components/layout/Sidebar.vue')
  const layout = await source('../components/layout/AppLayout.vue')

  assert.match(router, /path: 'review'/)
  assert.match(router, /WeeklyReview/)
  assert.match(sidebar, /to="\/review"/)
  assert.match(sidebar, /周复盘/)
  assert.match(layout, /WeeklyReview\s*:\s*['"]周复盘['"]/)
})
