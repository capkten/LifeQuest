import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { chinaDateKey, useDailyWorkbench } from './useDailyWorkbench.js'
import { chinaDateKey as utilityChinaDateKey } from '../utils/dateTime.js'

const copy = value => structuredClone(value)
const task = (id, title = id) => ({ id, title, status: 'pending', deadline: null, completed_at: null })

function board() {
  const tasks = [task('first', '写周报'), task('second', '运动'), task('third', '阅读'), task('fourth', '整理')]
  return {
    date: '2026-09-12', revision: 0, focus_tasks: [tasks[0]],
    task_groups: { today: [], overdue: [], unscheduled: tasks, upcoming: [] },
    summary: { completed_today: 0, open_tasks: 4, today: 0, overdue: 0, unscheduled: 4, focus_completed: 0 }
  }
}

function deferred() {
  let resolve, reject
  const promise = new Promise((accept, fail) => { resolve = accept; reject = fail })
  return { promise, resolve, reject }
}

function harness(overrides = {}, options = {}) {
  const snapshot = board()
  let requests = 0
  const api = {
    getWorkbench: async () => copy(snapshot),
    completeTask: async id => ({ ...task(id), status: 'completed', completed_at: '2026-09-12T02:00:00Z' }),
    createQuickTask: async data => ({ ...task('new', data.title) }),
    saveDailyFocus: async data => ({ ...copy(snapshot), revision: data.revision + 1,
      focus_tasks: data.task_ids.map(id => snapshot.task_groups.unscheduled.find(item => item.id === id)) }),
    ...overrides
  }
  return { api, snapshot, state: useDailyWorkbench(api, { newRequestId: () => `request-${++requests}`, ...options }) }
}

test('China date grouping is independent of the browser timezone', () => {
  assert.equal(chinaDateKey('2026-09-11T15:59:59Z'), '2026-09-11')
  assert.equal(chinaDateKey('2026-09-11T16:00:00Z'), '2026-09-12')
  assert.equal(chinaDateKey('2026-09-12T00:00:00+08:00'), '2026-09-12')
  assert.equal(chinaDateKey(null), null)
  assert.equal(chinaDateKey('invalid'), null)
})

test('workbench re-exports the shared China date implementation', () => {
  assert.equal(chinaDateKey, utilityChinaDateKey)
})

test('failed initial load is not presented as a legitimate empty workbench', async () => {
  const { state } = harness({ getWorkbench: async () => { throw new Error('offline') } })
  assert.equal(await state.load(), false)
  assert.equal(state.data.value, null)
  assert.ok(state.loadError.value)
  assert.equal(state.loading.value, false)
})

test('a server workbench date replaces a stale client date', async () => {
  const { state, api, snapshot } = harness()
  state.data.value = { ...copy(snapshot), date: '2026-09-11' }
  api.getWorkbench = async () => ({ ...copy(snapshot), date: '2026-09-12' })

  assert.equal(await state.load(), true)
  assert.equal(state.data.value.date, '2026-09-12')
})

test('refresh failure preserves existing data and a retry can succeed', async () => {
  const { state, api, snapshot } = harness()
  await state.load()
  const previous = state.data.value
  api.getWorkbench = async () => { throw new Error('offline') }

  assert.equal(await state.load(), false)
  assert.equal(state.data.value, previous)
  assert.ok(state.loadError.value)
  assert.equal(state.loading.value, false)

  api.getWorkbench = async () => ({ ...copy(snapshot), revision: 3 })
  assert.equal(await state.load(), true)
  assert.equal(state.data.value.revision, 3)
  assert.equal(state.loadError.value, '')
})

test('pending completion suppresses duplicate requests and preserves failure context', async () => {
  const response = deferred()
  let calls = 0
  const { state } = harness({ completeTask: () => { calls += 1; return response.promise } })
  await state.load()
  const original = state.data.value.focus_tasks[0]
  const pending = state.completeTask(original)
  assert.equal(await state.completeTask(original), false)
  assert.equal(calls, 1)
  assert.equal(state.pendingAction.value, 'complete:first')
  response.reject(new Error('failed'))
  assert.equal(await pending, false)
  assert.equal(state.data.value.focus_tasks[0].status, 'pending')
  assert.ok(state.actionError.value)
  assert.equal(state.busy.value, false)
})

test('refresh failures do not undo a committed completion or report it as failed', async () => {
  const { state, api } = harness({}, { refreshRewards: () => { throw new Error('refresh failed') } })
  await state.load()
  api.getWorkbench = async () => { throw new Error('offline') }
  assert.equal(await state.completeTask(state.data.value.focus_tasks[0]), true)
  assert.equal(state.data.value.focus_tasks[0].status, 'completed')
  assert.equal(state.data.value.task_groups.unscheduled.some(item => item.id === 'first'), false)
  assert.equal(state.data.value.summary.completed_today, 1)
  assert.equal(state.data.value.summary.focus_completed, 1)
  assert.equal(state.actionError.value, '')
  assert.ok(state.feedback.value.includes('已完成'))
  assert.ok(state.warning.value.includes('无需重复提交'))
})

test('quick-create retry keeps its request ID and draft until acknowledgement', async () => {
  const payloads = []
  const { state, api } = harness({ createQuickTask: async payload => {
    payloads.push(payload)
    if (payloads.length === 1) throw new Error('response lost')
    return task('new', payload.title)
  } })
  await state.load()
  state.draft.value.title = '  新任务  '
  state.draft.value.schedule = 'unscheduled'
  assert.equal(await state.createTask(), false)
  assert.equal(state.draft.value.title, '  新任务  ')
  api.getWorkbench = async () => { throw new Error('offline') }
  assert.equal(await state.createTask(), true)
  assert.equal(payloads[0].request_id, payloads[1].request_id)
  assert.equal(payloads[1].title, '新任务')
  assert.equal(state.draft.value.title, '')
  assert.equal(state.data.value.summary.completed_today, 0)
  assert.ok(Number.isFinite(state.data.value.summary.completed_today))
  assert.equal(state.data.value.task_groups.unscheduled[0].id, 'new')
})

test('changed quick-create content starts a new idempotency request', async () => {
  const payloads = []
  const { state } = harness({ createQuickTask: async payload => {
    payloads.push(payload)
    throw new Error('offline')
  } })
  state.draft.value.title = '原内容'
  await state.createTask()
  state.draft.value.title = '新的内容'
  await state.createTask()
  assert.notEqual(payloads[0].request_id, payloads[1].request_id)
})

test('focus selection limits three tasks, preserves order and allows retry after failure', async () => {
  const { state, api } = harness()
  await state.load()
  state.beginFocus()
  state.toggleFocus('second')
  state.toggleFocus('third')
  state.toggleFocus('fourth')
  assert.deepEqual([...state.focusDraft.value], ['first', 'second', 'third'])
  assert.ok(state.focusError.value)
  state.moveFocus('third', -1)
  assert.deepEqual([...state.focusDraft.value], ['first', 'third', 'second'])
  const originalSave = api.saveDailyFocus
  api.saveDailyFocus = async () => { throw new Error('offline') }
  assert.equal(await state.saveFocus(), false)
  assert.equal(state.editingFocus.value, true)
  assert.deepEqual([...state.focusDraft.value], ['first', 'third', 'second'])
  api.saveDailyFocus = originalSave
  assert.equal(await state.saveFocus(), true)
  assert.equal(state.editingFocus.value, false)
  assert.deepEqual(state.data.value.focus_tasks.map(item => item.id), ['first', 'third', 'second'])
})

test('focus conflict retains the edit base instead of silently overwriting another device', async () => {
  const payloads = []
  const { state, api, snapshot } = harness({ saveDailyFocus: async payload => {
    payloads.push(payload)
    throw { response: { status: 409, data: { detail: '今日重点已在其他页面更新' } } }
  } })
  await state.load()
  state.beginFocus()
  state.toggleFocus('second')
  assert.equal(await state.saveFocus(), false)
  assert.equal(state.editingFocus.value, true)
  assert.ok(state.focusError.value.includes('当前选择已保留'))
  api.getWorkbench = async () => ({ ...copy(snapshot), revision: 2 })
  await state.load()
  assert.equal(state.data.value.revision, 0)
  assert.deepEqual([...state.focusDraft.value], ['first', 'second'])
  await state.saveFocus()
  assert.equal(payloads[1].revision, 0)
  state.cancelFocus()
  await state.load()
  state.beginFocus()
  await state.saveFocus()
  assert.equal(payloads[2].revision, 2)
})

test('refresh does not replace the workbench behind an active focus draft', async () => {
  const { state, api, snapshot } = harness()
  await state.load()
  state.beginFocus()
  state.toggleFocus('second')
  api.getWorkbench = async () => ({ ...copy(snapshot), revision: 2, focus_tasks: [snapshot.task_groups.unscheduled[2]] })

  assert.equal(await state.load(), true)
  assert.equal(state.data.value.revision, 0)
  assert.deepEqual([...state.focusDraft.value], ['first', 'second'])
})

test('focus form cannot close while its save is pending', async () => {
  const response = deferred()
  const { state, snapshot } = harness({ saveDailyFocus: () => response.promise })
  await state.load()
  state.beginFocus()
  const pending = state.saveFocus()
  state.cancelFocus()
  state.toggleFocus('second')
  assert.equal(state.editingFocus.value, true)
  assert.deepEqual([...state.focusDraft.value], ['first'])
  response.resolve({ ...copy(snapshot), revision: 1 })
  await pending
  assert.equal(state.editingFocus.value, false)
})

test('a stale GET cannot reintroduce a task after successful completion', async () => {
  const stale = deferred()
  const { state, api, snapshot } = harness()
  await state.load()
  api.getWorkbench = () => stale.promise
  const earlierLoad = state.load()
  const latest = copy(snapshot)
  latest.focus_tasks[0].status = 'completed'
  latest.task_groups.unscheduled = latest.task_groups.unscheduled.filter(item => item.id !== 'first')
  api.getWorkbench = async () => latest
  await state.completeTask(state.data.value.focus_tasks[0])
  stale.resolve(copy(snapshot))
  assert.equal(await earlierLoad, false)
  assert.equal(state.data.value.focus_tasks[0].status, 'completed')
})

test('leaving the page invalidates pending results and skips refresh callbacks', async () => {
  const response = deferred()
  let refreshes = 0
  let changes = 0
  const { state } = harness({ completeTask: () => response.promise }, {
    refreshRewards: () => { refreshes += 1 },
    onChanged: () => { changes += 1 }
  })
  await state.load()
  const pending = state.completeTask(state.data.value.focus_tasks[0])
  state.dispose()
  response.resolve({ ...task('first'), status: 'completed', completed_at: '2026-09-12T02:00:00Z' })
  assert.equal(await pending, false)
  assert.equal(refreshes, 0)
  assert.equal(changes, 0)
  assert.equal(state.pendingAction.value, 'complete:first')
})

test('workbench appears before game information and keeps mobile controls accessible', async () => {
  const home = await readFile(new URL('../views/Home.vue', import.meta.url), 'utf8')
  const component = await readFile(new URL('../components/home/TodayWorkbench.vue', import.meta.url), 'utf8')
  assert.ok(home.indexOf('<TodayWorkbench') < home.indexOf('<section class="hero-card">'))
  assert.match(home, /@changed="refreshHomeTasks"/)
  assert.match(component, /role="alert"/)
  assert.match(component, /fieldset :disabled="busy"/)
  assert.match(component, /@keydown\.esc\.prevent="closeFocus"/)
  assert.match(component, /min-height:\s*48px/)
  assert.match(component, /font-size:\s*16px/)
})
