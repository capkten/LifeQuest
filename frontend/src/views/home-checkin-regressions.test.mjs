import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('check-in reports success once and never surfaces a refresh failure as a failed check-in', async () => {
  const home = await source('./Home.vue')
  const handler = home.match(/async function doCheckin\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(handler, 'doCheckin handler must remain available')

  // The handler used to call refreshActionRewards(), which was never defined,
  // so the ReferenceError landed in the catch block and reported the already
  // successful check-in as a failure.
  assert.doesNotMatch(handler, /refreshActionRewards/)

  const requestStart = handler.indexOf('checkinService.checkin()')
  const catchStart = handler.indexOf('} catch')
  const finallyStart = handler.indexOf('} finally')
  const refreshStart = handler.indexOf('Promise.allSettled')

  assert.ok(requestStart >= 0, 'the handler must call the check-in endpoint')
  assert.ok(catchStart > requestStart, 'the request must be wrapped in try/catch')
  assert.ok(finallyStart > catchStart, 'the loading flag must be reset in finally')
  assert.ok(
    refreshStart > finallyStart,
    'reward refreshes must run after the request settles so they cannot fail the check-in',
  )

  const refresh = handler.slice(refreshStart)
  assert.match(refresh, /Promise\.allSettled\(/)
  assert.doesNotMatch(refresh, /\bawait\s+fetchActionCenter\(\)/)
})
