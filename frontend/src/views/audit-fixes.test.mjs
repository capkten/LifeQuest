import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { formatDateTimeInput } from '../utils/dateTime.js'
import { ACTION_TYPE_LABELS } from '../locales/zh-CN.js'

test('deadline editing preserves the instant in local datetime inputs', () => {
  const previousTimezone = process.env.TZ
  try {
    for (const timezone of ['Asia/Shanghai', 'UTC', 'America/Los_Angeles']) {
      process.env.TZ = timezone
      const original = '2026-09-11T16:00:00Z'
      const value = formatDateTimeInput(original)
      assert.equal(new Date(value).getTime(), new Date(original).getTime())
      if (timezone === 'Asia/Shanghai') assert.equal(value, '2026-09-12T00:00')
    }
    assert.equal(formatDateTimeInput(null), '')
    assert.equal(formatDateTimeInput('invalid'), '')
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ
    else process.env.TZ = previousTimezone
  }
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
  assert.equal((source.match(/await refreshTaskReward\(updated\)/g) || []).length, 2)
  assert.match(source, /Object\.assign\(task, updated\)/)
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
