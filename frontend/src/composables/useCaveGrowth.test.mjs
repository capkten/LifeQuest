import test from 'node:test'
import assert from 'node:assert/strict'
import { useCave } from './useCave.js'

test('companion activation retries the same request and refreshes visible companion state without blocking sessions', async () => {
  const payloads = []
  let ids = 0
  const original = { active_pet_key: null, pets: [], daily_note: null }
  const selected = { ...original, active_pet_key: 'white_deer' }
  const cave = useCave({
    getCave: async () => ({ date: '2026-09-12', companions: original }),
    getGrowth: async () => ({ companions: original }),
    getCompanions: async () => original,
    activateCompanion: async (key, payload) => {
      payloads.push([key, payload])
      if (payloads.length === 1) throw new Error('response lost')
      return selected
    },
  }, { newRequestId: () => `request-${++ids}` })
  await cave.load()
  await cave.loadGrowth()
  await cave.loadCompanions()
  assert.equal(await cave.activateCompanion('white_deer'), false)
  assert.ok(cave.companionsError.value)
  assert.equal(cave.companionPending.value, null)
  assert.equal(cave.pendingAction.value, null)
  assert.deepEqual(await cave.activateCompanion('white_deer'), selected)
  assert.deepEqual(payloads, [
    ['white_deer', { request_id: 'request-1' }], ['white_deer', { request_id: 'request-1' }],
  ])
  assert.equal(cave.companions.value.active_pet_key, 'white_deer')
  assert.equal(cave.growth.value.companions.active_pet_key, 'white_deer')
  assert.equal(cave.data.value.companions.active_pet_key, 'white_deer')
  assert.equal(cave.companionsError.value, '')
  cave.dispose()
})

test('late home and growth reads cannot undo a newer companion selection', async () => {
  let homeReply, growthReply, companionsReply
  const original = { active_pet_key: null, pets: [] }
  const selected = { active_pet_key: 'spirit_fox', pets: [], daily_note: null }
  const cave = useCave({
    getCave: () => new Promise(resolve => { homeReply = resolve }),
    getGrowth: () => new Promise(resolve => { growthReply = resolve }),
    getCompanions: () => new Promise(resolve => { companionsReply = resolve }),
    activateCompanion: async () => selected,
  }, { newRequestId: () => 'select-fox' })
  const home = cave.load()
  const growth = cave.loadGrowth()
  const companions = cave.loadCompanions()
  await cave.activateCompanion('spirit_fox')
  assert.equal(cave.loading.value, true)
  assert.equal(cave.growthLoading.value, true)
  homeReply({ date: '2026-09-12', companions: original })
  growthReply({ companions: original })
  companionsReply(original)
  await Promise.all([home, growth, companions])
  assert.equal(cave.companions.value.active_pet_key, 'spirit_fox')
  assert.equal(cave.growth.value.companions.active_pet_key, 'spirit_fox')
  assert.equal(cave.data.value.companions.active_pet_key, 'spirit_fox')
  assert.equal(cave.loading.value, false)
  assert.equal(cave.growthLoading.value, false)
  cave.dispose()
})

for (const [name, action, method] of [
  ['growth', 'loadGrowth', 'getGrowth'],
  ['codex', 'loadCodex', 'getCodex'],
  ['companions', 'loadCompanions', 'getCompanions'],
]) {
  test(`${name} loads independently from the home snapshot and keeps data on refresh failure`, async () => {
    let fail = false
    const value = { name }
    const cave = useCave({ [method]: async () => { if (fail) throw new Error('offline'); return value } })
    assert.equal(cave[name].value, null)
    assert.deepEqual(await cave[action](), value)
    assert.deepEqual(cave[name].value, value)
    assert.equal(cave.data.value, null)
    assert.equal(cave.loading.value, false)
    fail = true
    assert.equal(await cave[action](), false)
    assert.deepEqual(cave[name].value, value)
    assert.ok(cave[`${name}Error`].value)
    assert.equal(cave[`${name}Loading`].value, false)
    assert.equal(cave.loadError.value, '')
    cave.dispose()
  })
}
