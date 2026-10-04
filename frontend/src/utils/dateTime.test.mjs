import assert from 'node:assert/strict'
import test from 'node:test'
import {
  chinaDateKey,
  dateKeyFromTimestamp,
  dateKeyFromParts,
  dateKeyParts,
  dateKeyTimestamp,
  formatChinaDate,
  formatChinaDateTime,
  shiftDateKey,
  todayChinaDateKey,
  weekdayForDateKey,
} from './dateTime.js'

test('China date keys ignore the browser runtime timezone', () => {
  const previousTimezone = process.env.TZ
  try {
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
    assert.equal(dateKeyTimestamp('2026-09-12'), Date.UTC(2026, 8, 12))
    assert.equal(dateKeyFromTimestamp(Date.UTC(2026, 8, 12)), '2026-09-12')
    assert.equal(weekdayForDateKey('2026-09-14'), 0)
    assert.equal(formatChinaDate('2026-09-12', { year: 'numeric', month: '2-digit', day: '2-digit' }), '2026/09/12')
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ
    else process.env.TZ = previousTimezone
  }
})

test('China formatters retain the China timezone when callers provide options', () => {
  const options = { timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit', day: '2-digit' }
  assert.equal(formatChinaDate('2026-09-11T16:00:00Z', options), '2026/09/12')
  assert.equal(formatChinaDateTime('2026-09-11T16:00:00Z', options), '2026/09/12 00:00')
})
