import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import {
  chinaDateKey,
  chinaDateTimeInputToUtcIso,
  formatChinaDate,
  formatDateTimeInput,
} from '../utils/dateTime.js'
import { ACTION_TYPE_LABELS } from '../locales/zh-CN.js'

test('deadline editing uses China wall-clock values in every browser timezone', () => {
  const previousTimezone = process.env.TZ
  try {
    for (const timezone of ['Asia/Shanghai', 'UTC', 'America/Los_Angeles']) {
      process.env.TZ = timezone
      const original = '2026-09-11T16:00:00Z'
      const value = formatDateTimeInput(original)
      assert.equal(value, '2026-09-12T00:00')
      assert.equal(chinaDateTimeInputToUtcIso(value), '2026-09-11T16:00:00.000Z')
    }
    assert.equal(formatDateTimeInput(null), '')
    assert.equal(formatDateTimeInput('invalid'), '')
    assert.equal(chinaDateTimeInputToUtcIso('2026-09-12T24:00'), '')
    assert.equal(chinaDateTimeInputToUtcIso('invalid'), '')
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ
    else process.env.TZ = previousTimezone
  }
})

test('Todos deadline input conversion is centralized in China timezone helpers', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')
  assert.match(source, /chinaDateTimeInputToUtcIso/)
  assert.doesNotMatch(source, /new Date\(form\.value\.deadline\)\.toISOString\(\)/)
})

test('Todos switches tabs before loading an edit form', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')
  const body = source.match(/function openEditDialog\(item, type\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(body, 'openEditDialog must remain available')
  const tabSwitch = body.indexOf('activeTab.value = type')
  const formAssignment = body.indexOf('form.value = {')
  assert.ok(tabSwitch >= 0, 'edit dialog must select the item tab')
  assert.ok(formAssignment >= 0, 'edit dialog must populate the edit form')
  assert.ok(tabSwitch < formAssignment, 'the tab watcher must not reset the loaded edit form')
})

test('refund history exposes a localized action', () => {
  assert.equal(ACTION_TYPE_LABELS.refund, '退货')
})

test('finance and calendar views use the shared China date utility', async () => {
  const views = ['Finance.vue', 'FinanceTransactions.vue', 'FinanceDebts.vue', 'Calendar.vue']
  for (const view of views) {
    const source = await readFile(new URL(`./${view}`, import.meta.url), 'utf8')
    assert.match(source, /from ['"]\.\.\/utils\/dateTime['"]/)
    assert.doesNotMatch(source, /new Date\(\)\.toISOString\(\)\.split\('T'\)\[0\]/)
    assert.doesNotMatch(source, /\.(getFullYear|getMonth|getDate)\(/)
    assert.doesNotMatch(source, /(?:function|const|let) shiftDate\b/)
  }
})

test('project completion refreshes server rewards without undoing a successful action on refresh failure', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')
  assert.match(source, /Promise\.allSettled\([\s\S]*authStore\.fetchUser\(\)[\s\S]*cultivationStore\.applySettlement/)
  assert.equal((source.match(/await refreshTaskReward\(updated, task\.id, token\)/g) || []).length, 2)
  assert.match(source, /Object\.assign\(task, updated\)/)
})

test('ProjectDetail renders date-only project metadata in the China timezone', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')
  assert.match(source, /import \{[\s\S]*chinaDateKey[\s\S]*formatChinaDate[\s\S]*\} from ['"]\.\.\/utils\/dateTime['"]\s/)
  assert.match(source, /return formatChinaDate\(d, \{ year: 'numeric', month: 'short', day: 'numeric' \}\)/)
  assert.match(source, /return formatChinaDate\(d, \{ month: 'short', day: 'numeric' \}\)/)
  assert.doesNotMatch(source, /new Date\(d\)\.toLocaleDateString/)

  const previousTimezone = process.env.TZ
  try {
    for (const timezone of ['UTC', 'Asia/Shanghai', 'America/Los_Angeles']) {
      process.env.TZ = timezone
      assert.equal(
        formatChinaDate('2026-09-12', { year: 'numeric', month: '2-digit', day: '2-digit' }),
        '2026/09/12',
      )
    }
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ
    else process.env.TZ = previousTimezone
  }
})

test('ProjectDetail uses China date keys when opening date-only edit fields', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')
  assert.match(source, /import \{[\s\S]*chinaDateKey[\s\S]*formatChinaDate[\s\S]*\} from ['"]\.\.\/utils\/dateTime['"]\s/)
  assert.match(source, /due_date: ms\?\.due_date \? chinaDateKey\(ms\.due_date\) \|\| ''/)
  assert.match(source, /start_date: project\.value\.start_date \? chinaDateKey\(project\.value\.start_date\) \|\| ''/)
  assert.match(source, /end_date: project\.value\.end_date \? chinaDateKey\(project\.value\.end_date\) \|\| ''/)
  assert.doesNotMatch(source, /new Date\([^)]*\)\.toISOString\(\)\.slice\(0, 10\)/)

  const previousTimezone = process.env.TZ
  try {
    for (const timezone of ['UTC', 'Asia/Shanghai', 'America/Los_Angeles']) {
      process.env.TZ = timezone
      assert.equal(chinaDateKey('2026-09-11T16:00:00Z'), '2026-09-12')
    }
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ
    else process.env.TZ = previousTimezone
  }
})

test('todo completion settles server rewards without making refresh failures retryable', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')
  const settlement = source.match(/async function settleCompletion\(updated\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(settlement, 'settleCompletion must remain available')
  assert.match(settlement, /showReward\(updated\)/)
  assert.match(settlement, /Promise\.allSettled\(\[authStore\.fetchUser\(\)/)
  assert.match(settlement, /无需再次提交/)
  for (const handler of ['completeHabit', 'completeTask', 'completeGoal']) {
    const body = source.match(new RegExp(`async function ${handler}\\([^)]*\\) \\{([\\s\\S]*?)\\n\\}`))?.[1]
    assert.ok(body, `${handler} must remain available`)
    assert.doesNotMatch(body, /await authStore\.fetchUser\(\)/)
  }
})

test('habit history ignores stale responses and identifies weekly targets as planned slots', async () => {
  const source = await readFile(new URL('../components/HabitHistoryDialog.vue', import.meta.url), 'utf8')

  assert.match(source, /from ['"]\.\.\/utils\/dateTime['"][\s\S]*chinaDateKey[\s\S]*shiftDateKey[\s\S]*weekdayForDateKey/)
  assert.match(source, /let historyRequestId = 0/)
  assert.match(source, /const requestId = \+\+historyRequestId/)
  assert.match(source, /props\.visible && props\.habit\?\.id === habitId && requestId === historyRequestId/)
  assert.match(source, /计划槽位/)
  assert.match(source, /计划日/)
})

test('habit history keeps business-locked check-ins clickable with their reason', async () => {
  const source = await readFile(new URL('../components/HabitHistoryDialog.vue', import.meta.url), 'utf8')

  assert.match(source, /:disabled="busy"/)
  assert.doesNotMatch(source, /:disabled="busy \|\| !canCompleteToday"/)
  assert.match(source, /:aria-disabled="!canCompleteToday"/)
  assert.match(source, /:title="todayBlockedReason"/)
  assert.match(source, /v-if="!canCompleteToday"[\s\S]*todayBlockedReason/)
  assert.match(source, /if \(!canCompleteToday\.value \|\| busy\.value\) return/)
})

test('habit history clears the previous record before a new habit load', async () => {
  const source = await readFile(new URL('../components/HabitHistoryDialog.vue', import.meta.url), 'utf8')
  const visibleWatcher = source.match(/watch\(\(\) => props\.visible,[\s\S]*?\n\}\)/)?.[0]
  const habitWatcher = source.match(/watch\(\(\) => props\.habit\?\.id,[\s\S]*?\n\}\)/)?.[0]

  assert.ok(visibleWatcher, 'visible watcher must remain available')
  assert.ok(habitWatcher, 'habit watcher must remain available')
  assert.match(visibleWatcher, /history\.value = null/)
  assert.match(habitWatcher, /history\.value = null/)
})

test('ProjectDetail keeps Gantt date-only values on the China calendar', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')
  const ganttSource = source.slice(source.indexOf('// --- Gantt Chart ---'))

  assert.match(source, /chinaDateKey/)
  assert.match(source, /dateKeyTimestamp/)
  assert.match(source, /dateKeyFromTimestamp/)
  assert.match(ganttSource, /function ganttDateTimestamp\(value\)[\s\S]*chinaDateKey\(value\)/)
  assert.match(ganttSource, /function ganttDateToX\(dateStr\)[\s\S]*ganttDateTimestamp\(dateStr\)/)
  assert.doesNotMatch(ganttSource, /new Date\(dateStr\)/)
  assert.doesNotMatch(ganttSource, /\.(getFullYear|getMonth|getDate)\(/)
})

test('ProjectDetail serializes route loads and kanban mutations', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')

  assert.match(source, /const taskPendingIds = reactive\(new Set\(\)\)/)
  assert.match(source, /:draggable="!taskPendingIds\.has\(task\.id\)"/)
  assert.match(source, /if \(taskPendingIds\.has\(task\.id\)\)/)
  assert.match(source, /watch\(\(\) => route\.params\.id/)
  assert.match(source, /fetchData\(nextId\)/)
  assert.match(source, /fetchRequestId|requestId/)
})

test('ProjectDetail retry reloads the current route project', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')

  assert.match(source, /@click="fetchData\(projectId\)"/)
})

test('ProjectDetail can clear milestone dates and keeps milestone saves retryable', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')

  assert.match(source, /due_date: msForm\.value\.due_date \|\| null/)
  assert.match(source, /const milestonePending = ref\(false\)/)
  assert.match(source, /if \(milestonePending\.value\)/)
  assert.match(source, /:disabled="milestonePending"/)
})

test('ProjectDetail defines the task edit dialog handlers it renders', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')

  assert.match(source, /function cancelTaskDialog\(/)
  assert.match(source, /async function saveTask\(/)
  assert.match(source, /projectService\.updateTask\(/)
})

test('cultivation settlement application is idempotent by log identity', async () => {
  const source = await readFile(new URL('../stores/cultivation.js', import.meta.url), 'utf8')

  assert.match(source, /const appliedSettlementIds = new Set\(\)/)
  assert.match(source, /settlement\.log_id/)
  assert.match(source, /appliedSettlementIds\.has\(/)
  assert.match(source, /appliedSettlementIds\.add\(/)
  assert.match(source, /appliedSettlementIds\.clear\(\)/)
})
