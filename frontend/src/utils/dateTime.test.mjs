import assert from 'node:assert/strict'
import test from 'node:test'
import {
  chinaDateKey,
  dateKeyFromParts,
  dateKeyParts,
  formatChinaDate,
  shiftDateKey,
  todayChinaDateKey,
  weekdayForDateKey,
} from './dateTime.js'

test('China date keys ignore the browser runtime timezone', () => {
  for (const timezone of ['UTC', 'Asia/Shanghai', 'America/Los_Angeles']) {
    process.env.TZ = timezone
    assert.equal(chinaDateKey('2026-09-11T15:59:59Z'), '2026-09-11')
    assert.equal(chinaDateKey('2026-09-11T16:00:00Z'), '2026-09-12')
    assert.equal(chinaDateKey('2026-09-12'), '2026-09-12')
  }
  assert.equal(todayChinaDateKey(new Date('2026-09-11T16:00:00Z')), '2026-09-12')
  assert.equal(shiftDateKey('2026-03-01', -1), '2026-02-28')
  assert.equal(shiftDateKey('2026-12-31', 1), '2027-01-01')
  assert.deepEqual(dateKeyParts('2026-09-12'), { year: 2026, monthIndex: 8, day: 12 })
  assert.equal(dateKeyFromParts(2026, 8, 12), '2026-09-12')
  assert.equal(weekdayForDateKey('2026-09-14'), 0)
  assert.equal(formatChinaDate('2026-09-12', { year: 'numeric', month: '2-digit', day: '2-digit' }), '2026/09/12')
})
