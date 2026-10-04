import test from 'node:test'
import assert from 'node:assert/strict'
import { useCultivationRetreat } from './useCultivationRetreat.js'

function createMockApi() {
  let activeSession = null
  let catalog = []

  return {
    getActive: async () => activeSession,
    startRetreat: async ({ target_duration, todo_id }) => {
      activeSession = {
        id: 'session-123',
        target_duration,
        todo_id: todo_id || null,
        status: 'active',
        started_at: new Date(Date.now()).toISOString(),
        exp_gained: 0,
        coins_gained: 0,
      }
      return activeSession
    },
    completeRetreat: async (id, { mark_todo_complete }) => {
      const res = {
        ...activeSession,
        status: 'completed',
        actual_duration: activeSession.target_duration,
        exp_gained: activeSession.target_duration * 10,
        coins_gained: activeSession.target_duration * 5,
        encounter_result: {
          id: 'encounter-1',
          title: '仙人指路',
          rarity: 'rare',
        },
      }
      activeSession = null
      return res
    },
    abortRetreat: async (id) => {
      const res = {
        ...activeSession,
        status: 'aborted',
      }
      activeSession = null
      return res
    },
    getCatalog: async () => catalog,
  }
}

test('useCultivationRetreat initial state is idle', () => {
  const api = createMockApi()
  const retreat = useCultivationRetreat(api, { autoTick: false })

  assert.equal(retreat.activeRetreat.value, null)
  assert.equal(retreat.isFocusing.value, false)
  assert.equal(retreat.remainingSeconds.value, 0)
  assert.equal(retreat.latestEncounter.value, null)
})

test('useCultivationRetreat starts session and updates remaining seconds', async () => {
  const api = createMockApi()
  const retreat = useCultivationRetreat(api, { autoTick: false })

  await retreat.startRetreat({ targetDuration: 25, todoId: 'todo-abc' })

  assert.ok(retreat.activeRetreat.value)
  assert.equal(retreat.activeRetreat.value.target_duration, 25)
  assert.equal(retreat.activeRetreat.value.todo_id, 'todo-abc')
  assert.equal(retreat.isFocusing.value, true)
  assert.equal(retreat.totalSeconds.value, 25 * 60)
  assert.equal(retreat.remainingSeconds.value, 25 * 60)

  // Advance time by 60 seconds
  retreat.tick(Date.now() + 60 * 1000)
  assert.equal(retreat.remainingSeconds.value, 24 * 60)
  assert.ok(retreat.progressRatio.value > 0)
})

test('useCultivationRetreat completes session and captures encounter', async () => {
  const api = createMockApi()
  const retreat = useCultivationRetreat(api, { autoTick: false })

  await retreat.startRetreat({ targetDuration: 25 })
  const result = await retreat.completeRetreat({ markTodoComplete: true })

  assert.equal(result.status, 'completed')
  assert.equal(retreat.activeRetreat.value, null)
  assert.equal(retreat.isFocusing.value, false)
  assert.ok(retreat.latestEncounter.value)
  assert.equal(retreat.latestEncounter.value.title, '仙人指路')
})

test('useCultivationRetreat aborts session cleanly', async () => {
  const api = createMockApi()
  const retreat = useCultivationRetreat(api, { autoTick: false })

  await retreat.startRetreat({ targetDuration: 25 })
  const result = await retreat.abortRetreat()

  assert.equal(result.status, 'aborted')
  assert.equal(retreat.activeRetreat.value, null)
  assert.equal(retreat.isFocusing.value, false)
  assert.equal(retreat.remainingSeconds.value, 0)
})
