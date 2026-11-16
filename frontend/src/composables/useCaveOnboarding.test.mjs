import test from 'node:test'
import assert from 'node:assert/strict'
import { useCave } from './useCave.js'

const pending = { status: 'pending', completed_session_id: null }
const skipped = { status: 'skipped', completed_session_id: null }
const completed = { status: 'completed', completed_session_id: 'first-session' }
const today = (onboarding = pending) => ({
  date: '2026-09-12', server_now: '2026-09-12T02:00:00Z', first_session: true,
  onboarding, primary_sign: { id: 'task-one', title: '读一页' }, signs: [{ id: 'task-one', title: '读一页' }],
  fortune: { key: 'quiet' }, active_session: null, summary: { completed_today: 0 },
})
const now = () => Date.parse('2026-09-12T02:00:00Z')

test('switching accounts or disposing invalidates late onboarding replies and pending state', async () => {
  for (const lifecycle of ['switch', 'dispose']) {
    let finish
    const cave = useCave({ getCave: async () => today(),
      completeOnboarding: () => new Promise(resolve => { finish = resolve }),
    }, { now })
    await cave.load()
    const completion = cave.completeOnboarding('first-session')
    assert.equal(cave.onboardingPending.value, 'complete')
    if (lifecycle === 'switch') await cave.setUser('bob')
    else cave.dispose()
    finish(completed)
    assert.equal(await completion, false)
    assert.notEqual(cave.onboarding.value?.status, 'completed')
    if (lifecycle === 'switch') {
      assert.equal(cave.onboardingPending.value, null)
      assert.equal(cave.onboardingError.value, '')
    }
    cave.dispose()
  }
})

test('offline onboarding writes stay pending and never enter the settlement queue', async () => {
  let online = true
  let requests = 0
  const cave = useCave({ getCave: async () => today(),
    skipOnboarding: async () => { requests += 1; return skipped },
    completeOnboarding: async () => { requests += 1; return completed },
  }, { identity: 'alice', now,
    persistence: { load: async () => ({ cache: null, queue: [] }), save: async () => {}, clear: async () => {} },
    connectivity: { isOnline: () => online, subscribe: () => () => {} },
  })
  await cave.load()
  online = false
  assert.equal(await cave.skipOnboarding(), false)
  assert.equal(await cave.completeOnboarding('first-session'), false)
  assert.equal(requests, 0)
  assert.deepEqual(cave.onboarding.value, pending)
  assert.equal(cave.onboardingPending.value, null)
  assert.ok(cave.onboardingError.value)
  assert.deepEqual(cave.pendingSettlements.value, [])
  cave.dispose()
})

test('lost completion replies allow one explicit retry with the original UUID and expose only server confirmation', async () => {
  const requests = []
  let finish
  let nextId = 0
  const cave = useCave({ getCave: async () => today(),
    completeOnboarding: async payload => {
      requests.push(payload)
      if (requests.length === 1) throw new Error('lost completion response')
      return new Promise(resolve => { finish = resolve })
    },
  }, { identity: 'alice', now, newRequestId: () => `complete-${++nextId}`,
    persistence: { load: async () => ({ cache: null, queue: [] }), save: async () => {}, clear: async () => {} },
  })
  await cave.load()
  assert.equal(await cave.completeOnboarding('first-session'), false)
  assert.equal(cave.offline.value, true)
  assert.deepEqual(cave.onboarding.value, pending)
  const retry = cave.completeOnboarding('first-session')
  assert.equal(cave.onboardingPending.value, 'complete')
  assert.equal(await cave.completeOnboarding('first-session'), false)
  assert.equal(await cave.skipOnboarding(), false)
  finish(completed)
  assert.deepEqual(await retry, completed)
  assert.equal(cave.offline.value, false)
  assert.deepEqual(requests, [
    { session_id: 'first-session', request_id: 'complete-1' },
    { session_id: 'first-session', request_id: 'complete-1' },
  ])
  assert.equal(cave.settledSession.value, null)
  assert.deepEqual(cave.pendingSettlements.value, [])
  cave.dispose()
})

test('late home and sign snapshots cannot reopen a confirmed skipped or completed guide', async () => {
  for (const read of ['load', 'reroll', 'selectSign']) {
    for (const result of [skipped, completed]) {
      let finish
      let first = true
      const oldSnapshot = () => new Promise(resolve => { finish = resolve })
      const cave = useCave({
        getCave: () => { if (first) { first = false; return Promise.resolve(today()) }; return oldSnapshot() },
        reroll: oldSnapshot, selectSign: oldSnapshot,
        skipOnboarding: async () => result, completeOnboarding: async () => result,
      }, { now })
      await cave.load()
      const stale = read === 'selectSign' ? cave.selectSign('task-two') : cave[read]()
      await (result.status === 'skipped' ? cave.skipOnboarding() : cave.completeOnboarding('first-session'))
      finish(today())
      await stale
      assert.deepEqual(cave.onboarding.value, result, `${read} preserves ${result.status}`)
      cave.dispose()
    }
  }
})

test('skipping publishes authoritative onboarding status without changing signs or inventing a receipt', async () => {
  let finish
  const cave = useCave({ getCave: async () => today(),
    skipOnboarding: () => new Promise(resolve => { finish = resolve }),
  }, { now })
  await cave.load()
  assert.deepEqual(cave.onboarding.value, pending)
  const skip = cave.skipOnboarding()
  assert.equal(cave.onboardingPending.value, 'skip')
  assert.deepEqual(cave.onboarding.value, pending)
  finish(skipped)
  assert.deepEqual(await skip, skipped)
  assert.deepEqual(cave.onboarding.value, skipped)
  assert.equal(cave.onboardingPending.value, null)
  assert.equal(cave.onboardingError.value, '')
  assert.equal(cave.primarySign.value.id, 'task-one')
  assert.equal(cave.settledSession.value, null)
  assert.deepEqual(cave.pendingSettlements.value, [])
  cave.dispose()
})

test('a lost skip acknowledgement retains the pending guide and retries the same request UUID', async () => {
  const requests = []
  let sequence = 0
  const cave = useCave({
    getCave: async () => today(),
    skipOnboarding: async payload => {
      requests.push(payload)
      if (requests.length === 1) throw new Error('lost acknowledgement')
      return skipped
    },
  }, { now, newRequestId: () => `10000000-0000-4000-8000-00000000000${++sequence}` })
  await cave.load()
  assert.equal(await cave.skipOnboarding(), false)
  assert.deepEqual(cave.onboarding.value, pending)
  assert.ok(cave.onboardingError.value)
  assert.equal(cave.onboardingPending.value, null)
  assert.deepEqual(await cave.skipOnboarding(), skipped)
  assert.deepEqual(requests, [
    { request_id: '10000000-0000-4000-8000-000000000001' },
    { request_id: '10000000-0000-4000-8000-000000000001' },
  ])
  cave.dispose()
})

test('completing onboarding includes the qualifying session and keeps the server result after reload', async () => {
  const persistence = {
    value: { cache: null, queue: [] },
    async load() { return this.value },
    async save(userId, envelope) { this.value = structuredClone(envelope) },
    async clear() {},
  }
  const cave = useCave({
    getCave: async () => today(),
    completeOnboarding: async payload => {
      assert.deepEqual(payload, { session_id: 'first-session', request_id: 'complete-request' })
      return completed
    },
  }, { identity: 'alice', persistence, now, newRequestId: () => 'complete-request' })
  await cave.load()
  assert.deepEqual(await cave.completeOnboarding('first-session'), completed)
  assert.deepEqual(cave.onboarding.value, completed)
  assert.equal(cave.onboardingPending.value, null)
  cave.dispose()
  const restored = useCave({}, { identity: 'alice', persistence, connectivity: { isOnline: () => false, subscribe: () => () => {} }, now })
  await restored.load()
  assert.deepEqual(restored.onboarding.value, completed)
  restored.dispose()
})
