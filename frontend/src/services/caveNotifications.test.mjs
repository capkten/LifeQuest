import test from 'node:test'
import assert from 'node:assert/strict'
import { createCaveNotifications } from './caveNotifications.js'

const ownerId = '11111111-1111-4111-8111-111111111111'
const sessionId = '22222222-2222-4222-8222-222222222222'
const started = Date.parse('2026-11-16T10:00:00Z')
const session = { id: sessionId, user_id: ownerId, status: 'active', started_at: '2026-11-16T10:00:00Z',
  target_duration: 25, todo_title: '写完周报' }

function androidSystem(display = 'granted') {
  const delivered = []
  const scheduled = []
  const removed = []
  return {
    delivered, scheduled, removed,
    android: { showOngoing: async value => delivered.push(value), cancel: async value => removed.push(value.id) },
    localNotifications: {
      checkPermissions: async () => ({ display }), requestPermissions: async () => ({ display }),
      createChannel: async () => {},
      schedule: async value => scheduled.push(...value.notifications),
      cancel: async value => removed.push(...value.notifications.map(item => item.id)),
      removeDeliveredNotifications: async () => {},
    },
  }
}

test('Android startup checks permission without asking the user', async () => {
  const prompts = []
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    localNotifications: {
      checkPermissions: async () => ({ display: 'prompt' }),
      requestPermissions: async () => { prompts.push('display'); return { display: 'granted' } },
    },
  })
  assert.equal(notifications.enabled.value, true)
  assert.deepEqual(prompts, [])
  assert.equal(await notifications.requestFromGesture(), true)
  assert.deepEqual(prompts, ['display'])
  assert.equal(notifications.permission.value, 'granted')
})

test('Android posts a native deadline countdown with the task and schedules completion independently of JS ticks', async () => {
  const system = androidSystem()
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, now: () => started + 60_000, ...system })
  await notifications.syncSession(session, { serverNow: '2026-11-16T10:02:00Z' })
  assert.deepEqual(system.delivered, [{ id: 190008, sessionId, ownerId,
    deadlineMs: started + 24 * 60_000, taskTitle: '写完周报', postedAt: started + 60_000 }])
  assert.equal(system.scheduled[0].id, 190008)
  assert.equal(system.scheduled[0].title, '入定结束，回来收功')
  assert.equal(system.scheduled[0].schedule.at.getTime(), started + 24 * 60_000)
  assert.deepEqual(system.scheduled[0].extra, { sessionId, ownerId, type: 'completion', postedAt: started + 24 * 60_000 })
  assert.equal(system.scheduled[0].ongoing, false)
})

test('denied notification permission leaves session state untouched and explains the in-app fallback', async () => {
  const system = androidSystem('denied')
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, now: () => started, ...system })
  assert.equal(await notifications.syncSession(session), false)
  assert.equal(notifications.permission.value, 'denied')
  assert.match(notifications.notice.value, /迷你条/)
  assert.deepEqual(system.delivered, [])
  assert.deepEqual(system.scheduled, [])
  assert.equal(session.status, 'active')
})

test('turning notifications off cancels the scheduled and visible Android notice and survives restart', async () => {
  const values = new Map()
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) }
  const system = androidSystem()
  const notifications = createCaveNotifications({ platform: 'android', storage,
    getOwnerId: () => ownerId, now: () => started, ...system })
  await notifications.syncSession(session)
  await notifications.setEnabled(false)
  assert.equal(notifications.enabled.value, false)
  assert.ok(system.removed.includes(190008))
  assert.equal(createCaveNotifications({ platform: 'android', storage }).enabled.value, false)
  assert.equal(await notifications.syncSession(session), false)
  assert.equal(system.scheduled.length, 1)
})

test('settling or clearing the current session removes native pending reminders', async () => {
  const system = androidSystem()
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, now: () => started, ...system })
  await notifications.syncSession(session)
  await notifications.syncSession({ ...session, status: 'completed' })
  assert.ok(system.removed.includes(190008))
  assert.equal(system.scheduled.length, 1)
  await notifications.syncSession(null)
  assert.equal(system.scheduled.length, 1)
})

function actionSystem(pending = null) {
  let receiver
  return {
    emit: value => receiver(value),
    android: {
      addListener: async (_event, callback) => { receiver = callback; return { remove: async () => { receiver = null } } },
      getPendingAction: async () => ({ action: pending }),
    },
  }
}

test('an early native finish action validates the server session and only routes back to the session', async () => {
  const actions = []
  const system = actionSystem()
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started + 10 * 60_000, getOwnerId: () => ownerId, ...system,
    api: { getSession: async () => ({ session, server_now: '2026-11-16T10:10:00Z' }) },
  })
  await notifications.listen(value => actions.push(value))
  await system.emit({ action: 'finish', type: 'ongoing', sessionId, ownerId, postedAt: started })
  assert.equal(actions.length, 1)
  assert.equal(actions[0].canComplete, false)
  assert.equal(actions[0].path, `/cave/session/${sessionId}`)
  assert.equal(actions[0].delayMs, 600_000)
})

test('clearing notifications invalidates an action awaiting a server reply', async () => {
  const actions = []
  const system = actionSystem()
  let respond
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, ...system, localNotifications: androidSystem().localNotifications,
    api: { getSession: () => new Promise(resolve => { respond = resolve }) },
  })
  await notifications.listen(value => actions.push(value))
  const pending = system.emit({ action: 'finish', type: 'ongoing', sessionId, ownerId, postedAt: started })
  await notifications.clear()
  respond({ session, server_now: '2026-11-16T10:25:00Z' })
  await pending
  assert.deepEqual(actions, [])
})

test('logout while a native post is in flight cannot leave a later completion alarm behind', async () => {
  const system = androidSystem()
  let release
  let posted
  const posting = new Promise(resolve => { posted = resolve })
  const pending = new Set()
  system.android.showOngoing = async () => { posted(); await new Promise(resolve => { release = resolve }) }
  system.localNotifications.schedule = async ({ notifications }) => notifications.forEach(item => pending.add(item.id))
  system.localNotifications.cancel = async ({ notifications }) => notifications.forEach(item => pending.delete(item.id))
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, now: () => started, ...system })
  const syncing = notifications.syncSession(session)
  await posting
  const clearing = notifications.clear()
  release()
  await Promise.all([syncing, clearing])
  assert.deepEqual([...pending], [])
})

test('disposing removes native listeners and prevents further permission or session work', async () => {
  const system = { ...androidSystem(), ...actionSystem() }
  const actions = []
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, now: () => started, ...system })
  await notifications.listen(value => actions.push(value))
  await notifications.dispose()
  assert.equal(await notifications.requestFromGesture(), false)
  assert.equal(await notifications.syncSession(session), false)
  assert.deepEqual(system.scheduled, [])
  assert.deepEqual(actions, [])
})

test('Windows uses a native toast only while its cancellable runtime deadline timer exists', async () => {
  const timers = new Map()
  const toasts = []
  const desktop = { checkPermissions: async () => ({ display: 'granted' }),
    requestPermissions: async () => ({ display: 'granted' }), show: async value => toasts.push(value) }
  const notifications = createCaveNotifications({ platform: 'windows', storage: null,
    getOwnerId: () => ownerId, now: () => started, desktop,
    setTimeout: (callback, delay) => { timers.set(1, { callback, delay }); return 1 },
    clearTimeout: id => timers.delete(id),
  })
  assert.equal(await notifications.syncSession(session), true)
  assert.equal(timers.get(1).delay, 1_500_000)
  assert.deepEqual(toasts, [])
  await timers.get(1).callback()
  assert.equal(toasts[0].title, '入定结束，回来收功')
  await notifications.syncSession(session)
  await notifications.clear()
  assert.equal(timers.size, 0)
  await notifications.dispose()
})

test('Android exact-alarm denial schedules inexactly with an honest notice and never opens permission settings', async () => {
  const system = androidSystem()
  let settingsOpened = false
  system.localNotifications.checkExactNotificationSetting = async () => ({ exact_alarm: 'denied' })
  system.localNotifications.changeExactNotificationSetting = async () => { settingsOpened = true }
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started, getOwnerId: () => ownerId, ...system })
  assert.equal(await notifications.syncSession(session), true)
  assert.match(notifications.notice.value, /延迟/)
  assert.equal(system.scheduled.length, 1)
  assert.equal(settingsOpened, false)
})

test('a cached session belonging to another account is never posted or scheduled', async () => {
  const system = androidSystem()
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started, getOwnerId: () => '33333333-3333-4333-8333-333333333333', ...system })
  assert.equal(await notifications.syncSession(session), false)
  assert.deepEqual(system.delivered, [])
  assert.deepEqual(system.scheduled, [])
})

test('an already elapsed active session posts completion without restarting a native countdown or scheduling the past', async () => {
  const system = androidSystem()
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started + 26 * 60_000, getOwnerId: () => ownerId, ...system })
  assert.equal(await notifications.syncSession(session), true)
  assert.deepEqual(system.delivered, [])
  assert.equal(system.scheduled[0].title, '入定结束，回来收功')
  assert.equal(system.scheduled[0].schedule, undefined)
})

test('disposing while the native listener is registering still releases that listener', async () => {
  let finishRegistration
  let registering
  let removed = false
  const startedRegistering = new Promise(resolve => { registering = resolve })
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    localNotifications: androidSystem().localNotifications,
    android: {
      addListener: async () => { registering(); return new Promise(resolve => { finishRegistration = resolve }) },
      getPendingAction: async () => ({}), cancel: async () => {},
    },
  })
  const listening = notifications.listen(() => {})
  await startedRegistering
  await notifications.dispose()
  finishRegistration({ remove: async () => { removed = true } })
  await listening
  assert.equal(removed, true)
})

test('a failed completion schedule removes the ongoing notice instead of leaving a dead countdown', async () => {
  const system = androidSystem()
  system.localNotifications.schedule = async () => { throw new Error('OS refused schedule') }
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started, getOwnerId: () => ownerId, ...system })
  assert.equal(await notifications.syncSession(session), false)
  assert.ok(system.removed.includes(190008))
  assert.match(notifications.notice.value, /迷你条/)
})

test('Web keeps the in-app experience without invoking notification system adapters', async () => {
  const system = androidSystem()
  let requested = false
  system.localNotifications.requestPermissions = async () => { requested = true }
  const notifications = createCaveNotifications({ platform: 'web', storage: null,
    now: () => started, getOwnerId: () => ownerId, ...system })
  assert.equal(notifications.isSupported, false)
  assert.equal(notifications.permission.value, 'in-app')
  assert.equal(await notifications.requestFromGesture(), false)
  assert.equal(await notifications.syncSession(session), false)
  assert.equal(requested, false)
  assert.deepEqual(system.scheduled, [])
  await notifications.dispose()
})

test('a cold completion tap validates its owned session and routes to the corresponding return', async () => {
  const actions = []
  const system = actionSystem({ action: 'open', type: 'completion', sessionId, ownerId, postedAt: started + 25 * 60_000 })
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started + 26 * 60_000, getOwnerId: () => ownerId, ...system,
    api: { getSession: async () => ({ session, server_now: '2026-11-16T10:26:00Z' }) },
  })
  await notifications.listen(value => actions.push(value))
  assert.equal(actions.length, 1)
  assert.equal(actions[0].path, `/cave/return/${sessionId}`)
  assert.equal(actions[0].type, 'completion')
  assert.equal(actions[0].delayMs, 60_000)
})

test('completion tapped before the server deadline routes to the live session regardless of the client clock', async () => {
  const actions = []
  const system = actionSystem({ action: 'open', type: 'completion', sessionId, ownerId, postedAt: started })
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started + 2_000_000, getOwnerId: () => ownerId, ...system,
    api: { getSession: async () => ({ session, server_now: '2026-11-16T10:05:00Z' }) },
  })
  await notifications.listen(value => actions.push(value))
  assert.equal(actions[0].path, `/cave/session/${sessionId}`)
  assert.equal(actions[0].canComplete, false)
})

test('an eligible finish tap uses the server eighty-percent boundary', async () => {
  const actions = []
  const system = actionSystem({ action: 'finish', type: 'ongoing', sessionId, ownerId, postedAt: started })
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    now: () => started, getOwnerId: () => ownerId, ...system,
    api: { getSession: async () => ({ session, server_now: '2026-11-16T10:20:00Z' }) },
  })
  await notifications.listen(value => actions.push(value))
  assert.equal(actions[0].canComplete, true)
  assert.equal(actions[0].path, `/cave/return/${sessionId}`)
})

test('foreign and malformed native payloads never reach the authenticated session API', async () => {
  const system = actionSystem()
  const fetched = []
  const actions = []
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => ownerId, ...system, api: { getSession: async id => fetched.push(id) } })
  await notifications.listen(value => actions.push(value))
  await system.emit({ action: 'open', type: 'completion', sessionId, ownerId: 'someone-else' })
  await system.emit({ action: 'open', type: 'completion', sessionId: '../../settings', ownerId })
  await system.emit({ action: 'award', type: 'ongoing', sessionId, ownerId })
  assert.deepEqual(fetched, [])
  assert.deepEqual(actions, [])
})

test('an account change during session validation discards the old notification action', async () => {
  const system = actionSystem()
  const actions = []
  let currentOwner = ownerId
  let respond
  const notifications = createCaveNotifications({ platform: 'android', storage: null,
    getOwnerId: () => currentOwner, ...system,
    api: { getSession: () => new Promise(resolve => { respond = resolve }) } })
  await notifications.listen(value => actions.push(value))
  const pending = system.emit({ action: 'finish', type: 'ongoing', sessionId, ownerId, postedAt: started })
  currentOwner = '33333333-3333-4333-8333-333333333333'
  respond({ session, server_now: '2026-11-16T10:25:00Z' })
  await pending
  assert.deepEqual(actions, [])
})

test('native plugin absence is a resolved in-app fallback rather than an unhandled rejection', async () => {
  const notifications = createCaveNotifications({ platform: 'android', storage: null })
  assert.equal(await notifications.requestFromGesture(), false)
  assert.equal(notifications.permission.value, 'denied')
  await notifications.clear()
  await notifications.dispose()
})
