import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const read = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('todo service carries occurrence identity through completion, snooze, and reschedule', async () => {
  const source = await read('../services/todo.js')

  assert.match(source, /completeTask\(taskId, occurrenceDate\)/)
  assert.match(source, /occurrence_date: occurrenceDate/)
  assert.match(source, /snoozeTask\(taskId, data\)/)
  assert.match(source, /\/todos\/tasks\/\$\{taskId\}\/snooze/)
  assert.match(source, /rescheduleTask\(taskId, data\)/)
  assert.match(source, /\/todos\/tasks\/\$\{taskId\}\/schedule/)
})

test('todos expose a retryable postpone action and recurring schedule fields', async () => {
  const source = await read('./Todos.vue')

  assert.match(source, /snoozeTask\(/)
  assert.match(source, /延期|稍后处理/)
  assert.match(source, /snoozeError/)
  assert.match(source, /schedule\.rule_type|scheduleRuleType/)
  assert.match(source, /weekdays|每周重复/)
})

test('calendar task details expose occurrence-aware rescheduling', async () => {
  const source = await read('./Calendar.vue')

  assert.match(source, /rescheduleTask\(/)
  assert.match(source, /occurrence_date/)
  assert.match(source, /calendarRescheduleError/)
  assert.match(source, /重新安排|重排/) 
  assert.match(source, /target_id/)
  assert.match(source, /await fetchEvents\(\)/)
  assert.match(source, /\.detail-item-action/)
})
