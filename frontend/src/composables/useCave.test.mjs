import test from 'node:test'
import assert from 'node:assert/strict'
import { useCave } from './useCave.js'

const snapshot = (overrides = {}) => ({
  date: '2026-09-12', server_now: '2026-09-12T02:00:00Z', first_session: false,
  fortune: { key: 'quiet', title: '静处自有回响', text: '先做一件事。', multiplier: 1 },
  primary_sign: { id: 'task-1', title: '写周报', source: '今天到期', deadline: null },
  active_session: null, summary: { completed_today: 0 }, ...overrides,
})

function memoryPersistence(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    values,
    async load(userId) { return values.get(userId) || { cache: null, queue: [] } },
    async save(userId, envelope) { values.set(userId, structuredClone(envelope)) },
    async clear(userId) { values.delete(userId) },
  }
}

function connectivity(initial = true) {
  let online = initial
  const listeners = new Set()
  return {
    isOnline: () => online,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener) },
    setOnline(value) { online = value; listeners.forEach(listener => listener(value)) },
  }
}

test('offline restore uses the user cache and marks it stale without showing old daily signs', async () => {
  const persistence = memoryPersistence({ alice: { cache: {
    date: '2026-09-11', serverOffsetMs: 120000,
    snapshot: snapshot({ date: '2026-09-11', fortune: { key: 'old' }, signs: [{ id: 'old-sign' }], primary_sign: { id: 'old-sign' }, summary: { completed_today: 9 } }),
  }, queue: [] } })
  const network = connectivity(false)
  const cave = useCave({ getCave: async () => { throw new Error('offline') } }, {
    identity: 'alice', persistence, connectivity: network,
    now: () => Date.parse('2026-09-12T02:00:00Z'),
  })
  await cave.setUser('alice')
  assert.equal(await cave.load(), true)
  assert.equal(cave.offline.value, true)
  assert.equal(cave.cacheDate.value, '2026-09-11')
  assert.equal(cave.staleCache.value, true)
  assert.equal(cave.data.value.date, '2026-09-12')
  assert.equal(cave.data.value.fortune, null)
  assert.deepEqual(cave.signs.value, [])
  assert.equal(cave.data.value.summary, null)
  cave.dispose()
})

test('a new offline provider restores a started session and preserves the saved server-clock offset', async () => {
  let instant = Date.parse('2026-09-12T03:00:00Z')
  const persistence = memoryPersistence()
  const network = connectivity(true)
  const session = { id: 'durable-session', status: 'active', target_duration: 25, started_at: '2026-09-12T02:00:00Z', mark_todo_complete: true }
  const first = useCave({ getCave: async () => snapshot(), startSession: async () => session }, {
    identity: 'alice', persistence, connectivity: network, now: () => instant,
  })
  await first.load()
  await first.startSession()
  first.dispose()
  instant += 5 * 60_000
  network.setOnline(false)
  const restored = useCave({}, { identity: 'alice', persistence, connectivity: network, now: () => instant })
  await restored.load()
  assert.equal(restored.offline.value, true)
  assert.equal(restored.activeSession.value.id, 'durable-session')
  assert.equal(restored.remainingSeconds.value, 1200)
  assert.equal(restored.getServerNow(), '2026-09-12T02:05:00.000Z')
  restored.dispose()
})

test('settlement intent is saved before HTTP and a lost reply survives reload with the same fixed payload', async () => {
  const persistence = memoryPersistence()
  const network = connectivity(true)
  const session = { id: 'queued', status: 'active', target_duration: 25, started_at: '2026-09-12T01:30:00Z', mark_todo_complete: true, todo_title: '写周报' }
  const requests = []
  let succeed = false
  const api = {
    getCave: async () => snapshot({ active_session: session }),
    settleSession: async (id, payload) => {
      const saved = await persistence.load('alice')
      assert.equal(saved.queue[0].request_id, payload.request_id)
      requests.push({ id, ...payload })
      if (!succeed) throw new Error('reply lost')
      return { ...session, status: 'completed', qi_gained: 25, exp_gained: 12 }
    },
  }
  const options = { identity: 'alice', persistence, connectivity: network,
    now: () => Date.parse('2026-09-12T02:00:00Z'), newRequestId: () => 'stable-queue-id' }
  const cave = useCave(api, options)
  await cave.load()
  assert.deepEqual(await cave.settleSession(), { status: 'pending_settlement', id: 'queued' })
  assert.equal(cave.settledSession.value, null)
  assert.equal(cave.pendingSettlements.value[0].session.todo_title, '写周报')
  cave.dispose()
  network.setOnline(false)
  const restored = useCave(api, options)
  await restored.load()
  assert.deepEqual(await restored.settleSession({ early: true }), { status: 'pending_settlement', id: 'queued' })
  assert.equal(restored.pendingSettlements.value.length, 1)
  succeed = true
  network.setOnline(true)
  await restored.retryPendingSettlements()
  assert.equal(restored.pendingSettlements.value.length, 0)
  assert.equal(restored.settledSession.value.exp_gained, 12)
  assert.deepEqual(requests, [
    { id: 'queued', early: false, request_id: 'stable-queue-id' },
    { id: 'queued', early: false, request_id: 'stable-queue-id' },
  ])
  restored.dispose()
})

test('offline session links restore only their own cached authoritative session without a request', async () => {
  const session = { id: 'cached-link', status: 'active', target_duration: 25, started_at: '2026-09-12T01:50:00Z', mark_todo_complete: true, todo_title: '读一页' }
  const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0,
    snapshot: snapshot({ active_session: session }), settledSession: null }, queue: [] } })
  const cave = useCave({}, { identity: 'alice', persistence, connectivity: connectivity(false), now: () => Date.parse('2026-09-12T02:00:00Z') })
  assert.equal((await cave.loadSession('cached-link')).id, 'cached-link')
  assert.equal(cave.sessionTask.value.title, '读一页')
  assert.equal(await cave.loadSession('some-other-session'), false)
  assert.equal(cave.remainingSeconds.value, 900)
  cave.dispose()
})

test('offline state rejects online-only writes and never queues task creation', async () => {
  let calls = 0
  const cave = useCave({
    createQuickTask: async () => { calls += 1; return {} },
    startSession: async () => { calls += 1; return {} },
    reroll: async () => { calls += 1; return {} },
    selectSign: async () => { calls += 1; return {} },
  }, { identity: 'alice', persistence: memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0, snapshot: snapshot() }, queue: [] } }),
    connectivity: connectivity(false), now: () => Date.parse('2026-09-12T02:00:00Z') })
  await cave.load()
  cave.draftTitle.value = '离线不创建'
  assert.equal(await cave.createTask(), false)
  assert.equal(await cave.startSession(), false)
  assert.equal(await cave.reroll(), false)
  assert.equal(await cave.selectSign('task-1'), false)
  assert.equal(calls, 0)
  assert.deepEqual(cave.pendingSettlements.value, [])
  assert.equal(cave.draftTitle.value, '离线不创建')
  assert.ok(cave.actionError.value)
  cave.dispose()
})

test('an already-open offline cave hides yesterday at China midnight while retaining session and queue', async () => {
  let instant = Date.parse('2026-09-12T15:59:00Z')
  const session = { id: 'midnight', status: 'active', target_duration: 25, started_at: '2026-09-12T15:50:00Z' }
  const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0,
    snapshot: snapshot({ active_session: session, signs: [{ id: 'yesterday' }] }) }, queue: [] } })
  const cave = useCave({}, { identity: 'alice', persistence, connectivity: connectivity(false), now: () => instant })
  await cave.load()
  await cave.settleSession({ early: true })
  instant += 2 * 60_000
  await cave.tick()
  assert.equal(cave.staleCache.value, true)
  assert.equal(cave.cacheDate.value, '2026-09-12')
  assert.equal(cave.data.value.date, '2026-09-13')
  assert.equal(cave.data.value.fortune, null)
  assert.equal(cave.data.value.summary, null)
  assert.deepEqual(cave.signs.value, [])
  assert.equal(cave.activeSession.value.id, 'midnight')
  assert.equal(cave.pendingSettlements.value[0].session.id, 'midnight')
  cave.dispose()
})

test('account changes erase private panels and invalidate every older in-flight response', async () => {
  const finishes = {}
  const waiting = key => new Promise(resolve => { finishes[key] = resolve })
  const persistence = memoryPersistence()
  const cave = useCave({
    getCave: async () => snapshot(), getCompanions: async () => ({ active: 'alice-deer' }),
    getGrowth: () => waiting('growth'), getCandidates: () => waiting('candidates'),
    startSession: () => waiting('start'), readLetter: () => waiting('letter'),
  }, { identity: 'alice', persistence, connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') })
  await cave.load()
  await cave.loadCompanions()
  const growth = cave.loadGrowth()
  const candidates = cave.loadCandidates()
  const start = cave.startSession()
  const letter = cave.readLetter('alice-letter')
  cave.draftTitle.value = 'private draft'
  await cave.setUser('bob')
  assert.equal(cave.companions.value, null)
  assert.equal(cave.draftTitle.value, '')
  assert.equal(cave.pendingAction.value, null)
  assert.equal(cave.letterPending.value, null)
  assert.equal(cave.data.value, null)
  finishes.growth({ private: 'alice' })
  finishes.candidates([{ id: 'alice-task', status: 'pending' }])
  finishes.start({ id: 'alice-session', status: 'active' })
  finishes.letter({ letters: [{ id: 'alice-letter' }], unread_count: 8 })
  assert.deepEqual(await Promise.all([growth, candidates, start, letter]), [false, false, false, false])
  assert.equal(cave.growth.value, null)
  assert.equal(cave.letters.value, null)
  assert.deepEqual(cave.candidates.value, [])
  assert.equal(cave.activeSession.value, null)
  assert.equal(persistence.values.has('alice'), false)
  assert.equal(persistence.values.has('bob'), false)
  cave.dispose()
})

function fakeClock(start = Date.parse('2026-09-12T02:00:00Z')) {
  let instant = start
  let nextId = 0
  const timers = new Map()
  return {
    now: () => instant,
    scheduler: {
      setTimeout(callback, delay) { const id = ++nextId; timers.set(id, { at: instant + delay, callback }); return id },
      clearTimeout(id) { timers.delete(id) },
    },
    async advance(milliseconds) {
      instant += milliseconds
      for (const [id, timer] of [...timers]) {
        if (timer.at <= instant) { timers.delete(id); await timer.callback() }
      }
      await new Promise(resolve => setImmediate(resolve))
    },
    get timerCount() { return timers.size },
  }
}

test('restored settlements resume exponential backoff even when transport failed but the device stayed online', async () => {
  const clock = fakeClock()
  const persistence = memoryPersistence()
  const network = connectivity()
  const session = { id: 'backoff', status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z', mark_todo_complete: false }
  const requests = []
  let succeed = false
  const api = {
    getCave: async () => snapshot({ active_session: session }),
    settleSession: async (id, payload) => {
      requests.push({ id, ...payload })
      if (!succeed) {
        if (requests.length % 2 === 0) throw { response: { status: 503 } }
        throw new Error('transport failed')
      }
      return { ...session, status: 'completed', qi_gained: 25 }
    },
  }
  const options = { identity: 'alice', persistence, connectivity: network, now: clock.now, scheduler: clock.scheduler, newRequestId: () => 'backoff-id' }
  const first = useCave(api, options)
  await first.load()
  await first.settleSession()
  assert.equal(first.offline.value, true)
  first.dispose()
  assert.equal(clock.timerCount, 0)
  const restored = useCave(api, options)
  await restored.load()
  let calls = 1
  for (const delay of [1000, 2000, 4000, 8000, 16000, 32000, 60000, 60000]) {
    await clock.advance(delay - 1)
    assert.equal(requests.length, calls)
    await clock.advance(1)
    assert.equal(requests.length, ++calls)
  }
  succeed = true
  await clock.advance(60000)
  assert.equal(restored.offline.value, false)
  assert.equal(restored.pendingSettlements.value.length, 0)
  assert.equal(restored.settledSession.value.qi_gained, 25)
  assert.ok(requests.every(item => item.request_id === 'backoff-id' && item.early === false))
  restored.dispose()
})

test('a settlement retry invalidates an older cave read and coalesces repeated recovery requests', async () => {
  const session = { id: 'retry-race', status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z' }
  const queue = [{ id: session.id, session_id: session.id, request_id: 'race-id', early: false,
    session, attempts: 1, status: 'pending', nextAttemptAt: Date.parse('2026-09-12T03:00:00Z') }]
  const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0, snapshot: snapshot({ active_session: session }) }, queue } })
  let finishRead, finishSettlement, calls = 0
  const cave = useCave({
    getCave: () => new Promise(resolve => { finishRead = resolve }),
    settleSession: () => { calls += 1; return new Promise(resolve => { finishSettlement = resolve }) },
  }, { identity: 'alice', persistence, connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') })
  await cave.setUser('alice')
  const read = cave.load()
  await new Promise(resolve => setImmediate(resolve))
  const retry = cave.retryPendingSettlements()
  const duplicate = cave.retryPendingSettlements()
  assert.equal(calls, 1)
  finishSettlement({ ...session, status: 'completed', qi_gained: 25 })
  await Promise.all([retry, duplicate])
  finishRead(snapshot({ active_session: session }))
  assert.equal(await read, false)
  assert.equal(cave.activeSession.value, null)
  assert.equal(cave.settledSession.value.qi_gained, 25)
  assert.equal(cave.pendingAction.value, null)
  cave.dispose()
})

test('confirmed receipts and queue removal persist atomically without refreshing an old daily cache date', async () => {
  const session = { id: 'old-day', status: 'active', target_duration: 25, started_at: '2026-09-11T01:00:00Z' }
  const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-11', serverOffsetMs: 0,
    snapshot: snapshot({ date: '2026-09-11', active_session: session }) }, queue: [] } })
  const savesAfterReceipt = []
  const save = persistence.save
  let confirmed = false
  persistence.save = async (userId, envelope) => {
    if (confirmed) savesAfterReceipt.push(structuredClone(envelope))
    return save(userId, envelope)
  }
  const api = {
    getCave: async () => { throw new Error('transport') },
    settleSession: async () => { confirmed = true; return { ...session, status: 'completed', qi_gained: 25 } },
  }
  const options = { identity: 'alice', persistence, connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') }
  const cave = useCave(api, options)
  await cave.load()
  await cave.settleSession()
  await cave.retryPendingSettlements()
  assert.ok(savesAfterReceipt.length > 0)
  assert.ok(savesAfterReceipt.every(envelope => envelope.queue.length === 0 &&
    envelope.cache.settledSession?.status === 'completed' && !envelope.cache.snapshot.active_session))
  cave.dispose()
  const restored = useCave({}, { ...options, connectivity: connectivity(false) })
  await restored.load()
  assert.equal(restored.staleCache.value, true)
  assert.equal(restored.cacheDate.value, '2026-09-11')
  assert.equal(restored.data.value.fortune, null)
  assert.equal((await restored.loadSession('old-day')).qi_gained, 25)
  restored.dispose()
})

test('an identity attached after construction reconnects queued work and disposal removes that listener', async () => {
  const session = { id: 'late-identity', status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z' }
  const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0,
    snapshot: snapshot({ active_session: session }) }, queue: [] } })
  const network = connectivity(false)
  let calls = 0
  const cave = useCave({
    getCave: async () => snapshot({ active_session: calls ? null : session }),
    settleSession: async () => { calls += 1; return { ...session, status: 'completed', qi_gained: 25 } },
  }, { persistence, connectivity: network, now: () => Date.parse('2026-09-12T02:00:00Z') })
  await cave.setUser('alice')
  await cave.settleSession()
  network.setOnline(true)
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(calls, 1)
  assert.equal(cave.pendingSettlements.value.length, 0)
  assert.equal(cave.settledSession.value.qi_gained, 25)
  cave.dispose()
  network.setOnline(false)
  network.setOnline(true)
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(calls, 1)
})

test('blocked settlements do not auto-loop and explicit recovery reuses the original payload once', async () => {
  const clock = fakeClock()
  const persistence = memoryPersistence()
  const network = connectivity()
  const session = { id: 'blocked', status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z', mark_todo_complete: true }
  const requests = []
  let recover = false
  const cave = useCave({
    getCave: async () => snapshot({ active_session: recover ? null : session }),
    settleSession: async (id, payload) => {
      requests.push({ id, ...payload })
      if (!recover) throw { response: { status: 409, data: { detail: '请校正时间后再试' } } }
      return { ...session, status: 'completed', qi_gained: 25 }
    },
  }, { identity: 'alice', persistence, connectivity: network, now: clock.now, scheduler: clock.scheduler, newRequestId: () => 'blocked-id' })
  await cave.load()
  assert.deepEqual(await cave.settleSession(), { status: 'pending_settlement', id: 'blocked' })
  assert.equal(cave.pendingSettlements.value[0].status, 'blocked')
  assert.equal(cave.pendingSettlements.value[0].error, '请校正时间后再试')
  assert.equal(clock.timerCount, 0)
  await clock.advance(3600000)
  network.setOnline(true)
  await new Promise(resolve => setImmediate(resolve))
  await cave.retryPendingSettlements()
  assert.equal(requests.length, 1)
  recover = true
  await cave.retryPendingSettlements({ includeBlocked: true })
  assert.deepEqual(requests, [
    { id: 'blocked', early: false, request_id: 'blocked-id' },
    { id: 'blocked', early: false, request_id: 'blocked-id' },
  ])
  assert.equal(cave.pendingSettlements.value.length, 0)
  assert.equal(cave.settledSession.value.qi_gained, 25)
  cave.dispose()
})

test('storage failure prevents any settlement HTTP or false durable-pending success', async () => {
  let requests = 0
  const session = { id: 'no-storage', status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z' }
  const cave = useCave({ getCave: async () => snapshot({ active_session: session }),
    settleSession: async () => { requests += 1; return { status: 'completed' } },
  }, { identity: 'alice', connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z'),
    persistence: { load: async () => ({ cache: null, queue: [] }), save: async () => { throw new Error('quota') }, clear: async () => {} } })
  await cave.load()
  assert.equal(await cave.settleSession(), false)
  assert.equal(requests, 0)
  assert.deepEqual(cave.pendingSettlements.value, [])
  assert.equal(cave.activeSession.value.id, 'no-storage')
  assert.equal(cave.settledSession.value, null)
  assert.ok(cave.actionError.value)
  cave.dispose()
})

test('logging out during a retry clears its queue and an old receipt cannot contaminate the next account', async () => {
  const persistence = memoryPersistence()
  const network = connectivity()
  const session = user => ({ id: `${user}-session`, status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z' })
  let user = 'alice', finishAlice
  const cave = useCave({
    getCave: async () => snapshot({ active_session: session(user) }),
    settleSession: (id) => id === 'alice-session'
      ? new Promise(resolve => { finishAlice = resolve }) : Promise.resolve({ ...session('bob'), status: 'completed', qi_gained: 20 }),
  }, { identity: 'alice', persistence, connectivity: network, now: () => Date.parse('2026-09-12T02:00:00Z') })
  await cave.load()
  network.setOnline(false)
  await cave.settleSession()
  network.setOnline(true)
  await new Promise(resolve => setImmediate(resolve))
  const oldRetry = cave.retryPendingSettlements()
  await cave.setUser(null)
  assert.equal(persistence.values.has('alice'), false)
  assert.deepEqual(cave.pendingSettlements.value, [])
  user = 'bob'
  await cave.setUser('bob')
  await cave.load()
  assert.equal((await cave.settleSession()).id, 'bob-session')
  finishAlice({ ...session('alice'), status: 'completed', qi_gained: 99 })
  assert.equal(await oldRetry, false)
  assert.equal(cave.settledSession.value.id, 'bob-session')
  assert.equal(cave.settledSession.value.qi_gained, 20)
  assert.equal(persistence.values.has('alice'), false)
  assert.deepEqual((await persistence.load('bob')).queue, [])
  cave.dispose()
})

test('a confirmed sign choice is the one restored by a later offline provider', async () => {
  const persistence = memoryPersistence()
  const options = { identity: 'alice', persistence, connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') }
  const selected = snapshot({ primary_sign: { id: 'manual', title: '自选的一件事' }, signs: [{ id: 'manual', title: '自选的一件事' }] })
  const cave = useCave({ getCave: async () => snapshot(), selectSign: async () => selected }, options)
  await cave.load()
  await cave.selectSign('manual')
  cave.dispose()
  const restored = useCave({}, { ...options, connectivity: connectivity(false) })
  await restored.load()
  assert.equal(restored.primarySign.value.id, 'manual')
  assert.equal(restored.signs.value[0].title, '自选的一件事')
  restored.dispose()
})

test('authorization failures do not become offline cache successes', async () => {
  for (const status of [401, 403]) {
    const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0, snapshot: snapshot() }, queue: [] } })
    const denied = async () => { throw { response: { status } } }
    const cave = useCave({ getCave: denied, getSession: denied }, { identity: 'alice', persistence,
      connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') })
    assert.equal(await cave.load(), false)
    assert.equal(cave.offline.value, false)
    assert.equal(cave.data.value, null)
    assert.equal(await cave.loadSession('private-session'), false)
    assert.equal(cave.offline.value, false)
    cave.dispose()
  }
})

test('a delayed cache write cannot resurrect logged-out storage or erase a queued settlement', async () => {
  const persistence = memoryPersistence()
  let release
  const delayed = new Promise(resolve => { release = resolve })
  const save = persistence.save
  let firstSave = true, calls = 0
  persistence.save = async (userId, envelope) => {
    if (firstSave) { firstSave = false; await delayed }
    return save(userId, envelope)
  }
  const session = { id: 'delayed-save', status: 'active', target_duration: 25, started_at: '2026-09-12T01:00:00Z' }
  const cave = useCave({ getCave: async () => snapshot({ active_session: session }),
    settleSession: async () => { calls += 1; return { status: 'completed' } },
  }, { identity: 'alice', persistence, connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') })
  const load = cave.load()
  await new Promise(resolve => setImmediate(resolve))
  const settlement = cave.settleSession()
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(calls, 0)
  const changed = cave.setUser('bob')
  release()
  await changed
  assert.equal(await load, false)
  assert.equal(await settlement, false)
  assert.equal(calls, 0)
  assert.equal(persistence.values.has('alice'), false)
  assert.equal(persistence.values.has('bob'), false)
  assert.equal(cave.data.value, null)
  assert.deepEqual(cave.pendingSettlements.value, [])
  cave.dispose()
})

test('session links fall back to their same-user active or terminal cache after transport failure', async () => {
  const active = { id: 'active-cache', status: 'active', target_duration: 25, started_at: '2026-09-12T01:50:00Z' }
  const receipt = { id: 'terminal-cache', status: 'completed', qi_gained: 20 }
  const persistence = memoryPersistence({ alice: { cache: { date: '2026-09-12', serverOffsetMs: 0,
    snapshot: snapshot({ active_session: active }), settledSession: receipt }, queue: [] } })
  const cave = useCave({ getSession: async () => { throw new Error('transport') } }, {
    identity: 'alice', persistence, connectivity: connectivity(), now: () => Date.parse('2026-09-12T02:00:00Z') })
  assert.equal((await cave.loadSession('active-cache')).id, 'active-cache')
  assert.equal(cave.offline.value, true)
  assert.equal((await cave.loadSession('terminal-cache')).qi_gained, 20)
  assert.equal(await cave.loadSession('foreign'), false)
  await cave.setUser('bob')
  assert.equal(await cave.loadSession('terminal-cache'), false)
  cave.dispose()
})

test('first session defaults to fifteen minutes, then morning forty-five and other periods twenty-five', async () => {
  let instant = Date.parse('2026-09-12T05:00:00+08:00')
  let first = true
  const cave = useCave({ getCave: async () => snapshot({ first_session: first }) }, { now: () => instant })
  await cave.load()
  assert.equal(cave.defaultDuration.value, 15)
  assert.equal(cave.selectedDuration.value, 15)
  first = false
  await cave.load()
  assert.equal(cave.defaultDuration.value, 45)
  assert.equal(cave.selectedDuration.value, 45)
  instant = Date.parse('2026-09-12T11:00:00+08:00')
  cave.tick()
  assert.equal(cave.defaultDuration.value, 25)
  assert.equal(cave.selectedDuration.value, 25)
  cave.dispose()
})

test('a failed refresh keeps the last cave and presents an error without becoming an empty state', async () => {
  let fail = false
  const cave = useCave({ getCave: async () => { if (fail) throw new Error('offline'); return snapshot() } })
  await cave.load()
  fail = true
  assert.equal(await cave.load(), false)
  assert.equal(cave.primarySign.value.title, '写周报')
  assert.ok(cave.loadError.value)
  assert.equal(cave.loading.value, false)
  cave.dispose()
})

test('getServerNow advances the adjusted server clock without a refresh or tick and survives session restoration', async () => {
  let instant = Date.parse('2026-09-12T03:00:00Z')
  const session = { id: 'session-clock', status: 'active', target_duration: 25, started_at: '2026-09-12T02:02:00Z' }
  const cave = useCave({
    getCave: async () => snapshot(),
    startSession: async () => session,
    getSession: async () => ({ session, server_now: '2026-09-12T02:04:00Z' }),
  }, { now: () => instant, newRequestId: () => 'clock-request' })
  await cave.load()
  assert.equal(cave.getServerNow(), '2026-09-12T02:00:00.000Z')
  instant += 120_000
  assert.equal(cave.getServerNow(), '2026-09-12T02:02:00.000Z')
  await cave.startSession()
  assert.equal(cave.getServerNow(), '2026-09-12T02:02:00.000Z')
  instant += 60_000
  assert.equal(cave.getServerNow(), '2026-09-12T02:03:00.000Z')
  await cave.loadSession('session-clock')
  assert.equal(cave.getServerNow(), '2026-09-12T02:04:00.000Z')
  instant += 60_000
  assert.equal(cave.getServerNow(), '2026-09-12T02:05:00.000Z')
  cave.dispose()
})


test('starting binds the primary sign and counts down from server time despite browser clock drift', async () => {
  let instant = Date.parse('2026-09-12T03:00:00Z')
  let payload
  const cave = useCave({
    getCave: async () => snapshot(),
    startSession: async value => {
      payload = value
      return { id: 'session-1', todo_id: value.todo_id, status: 'active', target_duration: 15, started_at: '2026-09-12T01:50:00' }
    },
  }, { now: () => instant, newRequestId: () => 'request-1' })
  await cave.load()
  cave.selectedDuration.value = 15
  await cave.startSession()
  assert.deepEqual(payload, { target_duration: 15, todo_id: 'task-1', mark_todo_complete: true, request_id: 'request-1' })
  assert.equal(cave.activeSession.value.id, 'session-1')
  assert.equal(cave.remainingSeconds.value, 300)
  instant += 60_000
  cave.tick()
  assert.equal(cave.remainingSeconds.value, 240)
  instant += 900_000
  cave.tick()
  assert.equal(cave.remainingSeconds.value, 0)
  cave.dispose()
})

test('cave opening records source, scene and existing session once without blocking on telemetry failure', async () => {
  const events = []
  const cave = useCave({
    getCave: async () => snapshot(),
    recordEvent: async event => { events.push(event); throw new Error('telemetry offline') },
  }, { now: () => Date.parse('2026-09-12T05:00:00+08:00'), newRequestId: () => 'open-1' })
  assert.equal(await cave.load({ source: 'bottom_nav' }), true)
  await cave.load()
  assert.deepEqual(events, [{ event: 'cave_open', source: 'bottom_nav', mode: 'morning', has_active_session: false, request_id: 'open-1' }])
  assert.equal(cave.loadError.value, '')
  cave.dispose()
})

test('a start retry reuses its request ID when the acknowledgement was lost', async () => {
  const payloads = []
  let ids = 0
  const cave = useCave({
    getCave: async () => snapshot(),
    startSession: async payload => {
      payloads.push(payload)
      if (payloads.length === 1) throw new Error('response lost')
      return { id: 'already-created', target_duration: 15, started_at: '2026-09-12T02:00:00Z', status: 'active' }
    },
  }, { newRequestId: () => `request-${++ids}` })
  await cave.load()
  assert.equal(await cave.startSession(), false)
  assert.ok(cave.actionError.value)
  await cave.startSession()
  assert.equal(payloads[1].request_id, payloads[0].request_id)
  assert.equal(cave.activeSession.value.id, 'already-created')
  assert.equal(cave.actionError.value, '')
  cave.dispose()
})

test('writing one thing creates a task for today and makes it the cave action', async () => {
  let created = false
  let payload
  const cave = useCave({
    getCave: async () => snapshot({ primary_sign: created ? { id: 'new', title: '散步十分钟' } : null }),
    createQuickTask: async value => { payload = value; created = true; return { id: 'new', title: value.title } },
  }, { newRequestId: () => 'create-1' })
  await cave.load()
  cave.draftTitle.value = '  散步十分钟  '
  assert.equal(await cave.createTask(), true)
  assert.deepEqual(payload, { title: '散步十分钟', schedule: 'today', request_id: 'create-1' })
  assert.equal(cave.primarySign.value.id, 'new')
  assert.equal(cave.draftTitle.value, '')
  cave.dispose()
})

test('a disposed cave ignores a late session response', async () => {
  let finish
  const response = new Promise(resolve => { finish = resolve })
  const cave = useCave({ getCave: async () => snapshot(), startSession: async () => response })
  await cave.load()
  const pending = cave.startSession()
  cave.dispose()
  finish({ id: 'late-session', target_duration: 15, started_at: '2026-09-12T02:00:00Z' })
  assert.equal(await pending, false)
  assert.equal(cave.activeSession.value, null)
})

test('an older cave refresh cannot erase a session that was started while the read was pending', async () => {
  let finish
  let reads = 0
  const response = new Promise(resolve => { finish = resolve })
  const cave = useCave({
    getCave: async () => ++reads === 1 ? snapshot() : response,
    startSession: async () => ({ id: 'new-session', target_duration: 15, started_at: '2026-09-12T02:00:00Z' }),
  })
  await cave.load()
  const pending = cave.load()
  await cave.startSession()
  finish(snapshot())
  await pending
  assert.equal(cave.activeSession.value.id, 'new-session')
  cave.dispose()
})

test('reroll replaces public signs and marks the free daily change as used', async () => {
  const first = { id: 'first', title: '第一件事' }
  const backup = { id: 'backup', title: '备签' }
  const replacement = { id: 'new', title: '换一件事' }
  let payload
  const cave = useCave({
    getCave: async () => snapshot({ primary_sign: first, signs: [first, backup], reroll_used: false }),
    reroll: async value => { payload = value; return snapshot({ primary_sign: replacement, signs: [replacement, backup], reroll_used: true }) },
  }, { newRequestId: () => 'reroll-1' })
  await cave.load()
  assert.equal(await cave.reroll(), true)
  assert.deepEqual(payload, { date: '2026-09-12', request_id: 'reroll-1' })
  assert.deepEqual(cave.signs.value.map(task => task.id), ['new', 'backup'])
  assert.equal(cave.rerollUsed.value, true)
  assert.equal(cave.primarySign.value.id, 'new')
  cave.dispose()
})

test('manual promotion updates the primary and does not spend the daily reroll', async () => {
  const first = { id: 'first', title: '第一件事' }
  const backup = { id: 'backup', title: '备签' }
  let payload
  const cave = useCave({
    getCave: async () => snapshot({ primary_sign: first, signs: [first, backup], reroll_used: false }),
    selectSign: async value => { payload = value; return snapshot({ primary_sign: backup, signs: [backup, first], reroll_used: false }) },
  }, { newRequestId: () => 'select-1' })
  await cave.load()
  assert.equal(await cave.selectSign('backup'), true)
  assert.deepEqual(payload, { date: '2026-09-12', task_id: 'backup', request_id: 'select-1' })
  assert.equal(cave.primarySign.value.id, 'backup')
  assert.equal(cave.rerollUsed.value, false)
  cave.dispose()
})

test('the bucket includes ordinary unscheduled tasks but excludes completed and cancelled tasks', async () => {
  const cave = useCave({ getCandidates: async () => [
    { id: 'ordinary', title: '普通未排期', status: 'pending', deadline: null, priority: 'low', project_id: 'project-1', project_name: '个人' },
    { id: 'active', title: '正在做', status: 'in_progress' },
    { id: 'closed', title: '已完成', status: 'completed' },
    { id: 'cancelled', title: '已取消', status: 'cancelled' },
  ] })
  assert.equal(await cave.loadCandidates(), true)
  assert.deepEqual(cave.candidates.value.map(task => task.id), ['ordinary', 'active'])
  assert.equal(cave.candidates.value[0].project_name, '个人')
  cave.dispose()
})

test('China midnight reloads the daily signs without overwriting a chosen duration', async () => {
  let instant = Date.parse('2026-09-12T23:59:59+08:00')
  const midnight = Date.parse('2026-09-13T00:00:00+08:00')
  const cave = useCave({ getCave: async () => snapshot({
    server_now: new Date(instant).toISOString(), date: instant < midnight ? '2026-09-12' : '2026-09-13',
    reroll_used: instant < midnight, signs: [{ id: instant < midnight ? 'old' : 'new' }],
  }) }, { now: () => instant })
  await cave.load()
  cave.selectedDuration.value = 60
  instant = midnight
  await cave.tick()
  assert.equal(cave.data.value.date, '2026-09-13')
  assert.equal(cave.signs.value[0].id, 'new')
  assert.equal(cave.rerollUsed.value, false)
  assert.equal(cave.selectedDuration.value, 60)
  cave.dispose()
})

test('a background refresh cannot strand an in-flight manual selection', async () => {
  let finish
  const pending = new Promise(resolve => { finish = resolve })
  const cave = useCave({ getCave: async () => snapshot(), selectSign: async () => pending })
  await cave.load()
  const selection = cave.selectSign('chosen')
  await cave.load()
  finish(snapshot({ primary_sign: { id: 'chosen' }, signs: [{ id: 'chosen' }] }))
  assert.equal(await selection, true)
  assert.equal(cave.pendingAction.value, null)
  assert.equal(cave.primarySign.value.id, 'chosen')
  cave.dispose()
})

test('lost reroll acknowledgements retry the same request and retain the previous signs until confirmed', async () => {
  let attempts = 0
  const payloads = []
  const cave = useCave({
    getCave: async () => snapshot({ signs: [{ id: 'original' }], reroll_used: false }),
    reroll: async payload => {
      payloads.push(payload)
      if (++attempts === 1) throw new Error('response lost')
      return snapshot({ signs: [{ id: 'replacement' }], reroll_used: true })
    },
  })
  await cave.load()
  assert.equal(await cave.reroll(), false)
  assert.equal(cave.signs.value[0].id, 'original')
  assert.equal(cave.rerollUsed.value, false)
  assert.equal(cave.pendingAction.value, null)
  assert.equal(await cave.reroll(), true)
  assert.equal(payloads[1].request_id, payloads[0].request_id)
  assert.equal(cave.rerollUsed.value, true)
  cave.dispose()
})

test('preparing a session binds the main sign or a chosen task, allows unbinding, and sends the planned choice', async () => {
  let payload
  const cave = useCave({
    getCave: async () => snapshot(),
    startSession: async value => {
      payload = value
      return { id: 'prepared', status: 'active', target_duration: value.target_duration, started_at: '2026-09-12T02:00:00Z', mark_todo_complete: value.mark_todo_complete }
    },
  }, { newRequestId: () => 'prepared-request' })
  await cave.load()
  assert.equal(cave.settledSession.value, null)
  cave.prepareSession()
  assert.equal(cave.preparingSession.value, true)
  assert.equal(cave.sessionTask.value.id, 'task-1')
  assert.equal(cave.markTodoComplete.value, true)
  cave.prepareSession({ id: 'other', title: '任意未完成任务' })
  assert.equal(cave.sessionTask.value.id, 'other')
  cave.sessionTask.value = null
  cave.markTodoComplete.value = false
  cave.selectedDuration.value = 90
  await cave.startSession()
  assert.deepEqual(payload, { target_duration: 90, todo_id: null, mark_todo_complete: false, request_id: 'prepared-request' })
  assert.equal(cave.preparingSession.value, false)
  assert.equal(cave.activeSession.value.id, 'prepared')
  cave.dispose()
})

test('a direct session link restores server time and enables collection exactly at eighty percent', async () => {
  let instant = Date.parse('2026-09-12T03:00:00Z')
  const session = { id: 'linked', status: 'active', target_duration: 25,
    started_at: '2026-09-12T02:00:00Z', todo_id: 'chosen', todo_title: '选中的事', mark_todo_complete: false }
  const cave = useCave({ getSession: async () => ({ session, server_now: '2026-09-12T02:19:59Z' }) }, { now: () => instant })
  assert.equal(await cave.loadSession('linked'), session)
  assert.equal(cave.activeSession.value.id, 'linked')
  assert.equal(cave.sessionTask.value.title, '选中的事')
  assert.equal(cave.markTodoComplete.value, false)
  assert.equal(cave.remainingSeconds.value, 301)
  assert.equal(cave.canComplete.value, false)
  instant += 1000
  cave.tick()
  assert.equal(cave.canComplete.value, true)
  instant += 60 * 60_000
  cave.tick()
  assert.equal(cave.remainingSeconds.value, 0)
  assert.equal(cave.activeSession.value.id, 'linked')
  assert.equal(cave.settledSession.value, null)
  cave.dispose()
})

test('a lost settlement acknowledgement retains the session and retries the same request before exposing the receipt', async () => {
  const session = { id: 'settling', status: 'active', target_duration: 25, started_at: '2026-09-12T01:30:00Z' }
  const receipt = { ...session, status: 'completed', exp_gained: 6, qi_gained: 25,
    settlement_result: { conversion_rate: 0.25, task_completed: false } }
  const requests = []
  let ids = 0
  const cave = useCave({
    getCave: async () => snapshot({ active_session: session }),
    settleSession: async (id, payload) => {
      requests.push({ id, ...payload })
      if (requests.length === 1) throw new Error('response lost')
      return receipt
    },
  }, { now: () => Date.parse('2026-09-12T02:00:00Z'), newRequestId: () => `settle-${++ids}` })
  await cave.load()
  assert.equal(await cave.settleSession(), false)
  assert.equal(cave.activeSession.value.id, 'settling')
  assert.equal(cave.settledSession.value, null)
  assert.ok(cave.actionError.value)
  assert.equal(cave.pendingAction.value, null)
  assert.equal(await cave.settleSession(), receipt)
  assert.deepEqual(requests, [
    { id: 'settling', early: false, request_id: 'settle-1' },
    { id: 'settling', early: false, request_id: 'settle-1' },
  ])
  assert.equal(cave.activeSession.value, null)
  assert.equal(cave.settledSession.value.status, 'completed')
  assert.deepEqual(cave.pendingReturn.value, { session_id: 'settling', status: 'unviewed', todo_title: null })
  assert.equal(cave.actionError.value, '')
  cave.dispose()
})

test('before eighty percent only explicit early ending can settle and it never changes the saved task choice', async () => {
  const session = { id: 'early', status: 'active', target_duration: 25, started_at: '2026-09-12T01:50:00Z', mark_todo_complete: true }
  const cave = useCave({
    getCave: async () => snapshot({ active_session: session }),
    settleSession: async (id, payload) => ({ ...session, status: payload.early ? 'aborted' : 'completed', qi_gained: 10 }),
  }, { now: () => Date.parse('2026-09-12T02:00:00Z') })
  await cave.load()
  assert.equal(await cave.settleSession(), false)
  assert.equal(cave.activeSession.value.id, 'early')
  const receipt = await cave.settleSession({ early: true })
  assert.equal(receipt.status, 'aborted')
  assert.equal(receipt.mark_todo_complete, true)
  assert.equal(cave.activeSession.value, null)
  cave.dispose()
})

test('discovering an existing active session while preparing reuses it and closes the draft', async () => {
  const existing = { id: 'existing', status: 'active', target_duration: 25, started_at: '2026-09-12T02:00:00Z' }
  const cave = useCave({ getCave: async () => snapshot({ active_session: existing }) })
  cave.prepareSession({ id: 'draft-task', title: '稍后做' })
  await cave.load()
  assert.equal(await cave.startSession(), cave.activeSession.value)
  assert.equal(cave.activeSession.value.id, 'existing')
  assert.equal(cave.preparingSession.value, false)
  cave.dispose()
})

test('starting before cave data arrives keeps the draft and explains that a refresh is needed', async () => {
  const cave = useCave({})
  cave.prepareSession(null)
  assert.equal(await cave.startSession(), false)
  assert.equal(cave.preparingSession.value, true)
  assert.ok(cave.actionError.value)
  cave.dispose()
})

test('opening an older settled receipt preserves a different active session and does not settle again', async () => {
  const running = { id: 'running', status: 'active', target_duration: 25, started_at: '2026-09-12T02:00:00Z' }
  const receipt = { id: 'previous', status: 'completed', exp_gained: 6 }
  const cave = useCave({
    getCave: async () => snapshot({ active_session: running }),
    getSession: async () => ({ session: receipt, server_now: '2026-09-12T02:01:00Z' }),
  })
  await cave.load()
  await cave.loadSession('previous')
  assert.equal(cave.settledSession.value.id, 'previous')
  assert.equal(cave.activeSession.value.id, 'running')
  cave.dispose()
})

test('direct return links restore an unacknowledged marker but not acknowledged or legacy receipts', async () => {
  for (const [acknowledged, summary, expected] of [[false, {}, 'direct'], [true, {}, null], [false, null, null]]) {
    const receipt = { id: 'direct', status: 'completed', return_summary: summary, todo_title: '读一页' }
    const cave = useCave({
      getSession: async () => ({ session: receipt, acknowledged, server_now: '2026-09-12T02:00:00Z' }),
    })
    await cave.loadSession('direct')
    assert.equal(cave.pendingReturn.value?.session_id || null, expected)
    assert.equal(cave.settledSession.value.id, 'direct')
    cave.dispose()
  }
})

test('disposing a provider prevents a late settlement response from changing its visible state', async () => {
  let finish
  const response = new Promise(resolve => { finish = resolve })
  const running = { id: 'running', status: 'active', target_duration: 25, started_at: '2026-09-12T01:30:00Z' }
  const cave = useCave({ getCave: async () => snapshot({ active_session: running }), settleSession: async () => response })
  await cave.load()
  const pending = cave.settleSession()
  cave.dispose()
  finish({ ...running, status: 'completed' })
  assert.equal(await pending, false)
  assert.equal(cave.settledSession.value, null)
  assert.equal(cave.activeSession.value.id, 'running')
})

test('a return marker remains after viewing and failed acknowledgement, then clears only after confirmed acknowledgement', async () => {
  const receipt = { id: 'unviewed', status: 'completed', return_summary: { total_reward: { cultivation: 6 } } }
  const marker = { session_id: 'unviewed', status: 'unviewed', todo_title: null }
  let acknowledged = false
  const requests = []
  const cave = useCave({
    getCave: async () => snapshot({ pending_return: acknowledged ? null : marker }),
    getSession: async () => ({ session: receipt, server_now: '2026-09-12T02:00:00Z', acknowledged }),
    acknowledgeReturn: async (id, payload) => {
      requests.push({ id, ...payload })
      if (requests.length === 1) throw new Error('network lost')
      acknowledged = true
      return { session_id: id, acknowledged: true }
    },
  }, { newRequestId: () => 'ack-request' })
  await cave.load()
  await cave.loadSession('unviewed')
  assert.equal(cave.pendingReturn.value.session_id, 'unviewed')
  assert.equal(await cave.acknowledgeReturn('unviewed'), false)
  assert.equal(cave.pendingReturn.value.session_id, 'unviewed')
  assert.equal(await cave.acknowledgeReturn('unviewed'), true)
  assert.deepEqual(requests, [
    { id: 'unviewed', request_id: 'ack-request' }, { id: 'unviewed', request_id: 'ack-request' },
  ])
  assert.equal(cave.pendingReturn.value, null)
  assert.equal(cave.settledSession.value.id, 'unviewed')
  cave.dispose()
})

test('each explicit return-page opening records a nonblocking view without acknowledging or altering rewards', async () => {
  const events = []
  let ids = 0
  const marker = { session_id: 'viewed', status: 'unviewed', todo_title: null }
  const cave = useCave({
    getCave: async () => snapshot({ pending_return: marker }),
    recordEvent: async event => { events.push(event); throw new Error('telemetry offline') },
  }, { now: () => Date.parse('2026-09-12T02:00:00Z'), newRequestId: () => `view-${++ids}` })
  await cave.load()
  await cave.recordReturnView('viewed')
  await cave.recordReturnView('viewed')
  const views = events.filter(event => event.event === 'return_view')
  assert.deepEqual(views.map(event => [event.session_id, event.source, event.mode, event.has_active_session]), [
    ['viewed', 'return_page', 'morning', false], ['viewed', 'return_page', 'morning', false],
  ])
  assert.notEqual(views[0].request_id, views[1].request_id)
  assert.equal(cave.pendingReturn.value.session_id, 'viewed')
  assert.equal(cave.actionError.value, '')
  assert.equal(cave.settledSession.value, null)
  cave.dispose()
})

test('an active session becomes ready locally at expiry without automatically settling it', async () => {
  let instant = Date.parse('2026-09-12T02:00:00Z')
  const session = { id: 'expires', status: 'active', target_duration: 1, started_at: '2026-09-12T02:00:00Z', todo_title: '读一页' }
  const cave = useCave({ getCave: async () => snapshot({ active_session: session, pending_return: null }) }, { now: () => instant })
  await cave.load()
  assert.equal(cave.pendingReturn.value, null)
  instant += 60_000
  cave.tick()
  assert.deepEqual(cave.pendingReturn.value, { session_id: 'expires', status: 'ready', todo_title: '读一页' })
  assert.equal(cave.activeSession.value.id, 'expires')
  assert.equal(cave.settledSession.value, null)
  cave.dispose()
})

test('cave uses China-time morning, day, dusk and night boundaries', () => {
  let instant = Date.parse('2026-09-12T04:59:00+08:00')
  const cave = useCave({}, { now: () => instant })
  for (const [time, expected] of [
    ['04:59', 'night'], ['05:00', 'morning'], ['10:59', 'morning'], ['11:00', 'day'],
    ['16:59', 'day'], ['17:00', 'dusk'], ['20:59', 'dusk'], ['21:00', 'night'],
  ]) {
    instant = Date.parse(`2026-09-12T${time}:00+08:00`)
    cave.tick()
    assert.equal(cave.mode.value, expected, time)
  }
  cave.dispose()
})
