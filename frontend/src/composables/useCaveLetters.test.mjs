import test from 'node:test'
import assert from 'node:assert/strict'
import { useCave } from './useCave.js'


test('reading a letter retries its request and updates detail, inbox and home unread state', async () => {
  const original = { id: 'letter-one', status: 'unread', body: '一封未改写的信。' }
  const marked = { ...original, status: 'read', read_at: '2026-09-07T00:00:00Z' }
  const inbox = { letters: [marked], unread_count: 0, accepted_trial: null }
  const requests = []
  const cave = useCave({
    getCave: async () => ({ unread_letters_count: 1 }),
    getLetters: async () => ({ ...inbox, letters: [original], unread_count: 1 }),
    getLetter: async () => original,
    readLetter: async (id, payload) => {
      requests.push([id, payload])
      if (requests.length === 1) throw new Error('lost acknowledgement')
      return inbox
    },
  }, { newRequestId: () => 'read-request' })
  await cave.load()
  await cave.loadLetters()
  assert.deepEqual(await cave.loadLetter('letter-one'), original)
  assert.equal(await cave.readLetter('letter-one'), false)
  assert.ok(cave.letterError.value)
  assert.equal(cave.letter.value.status, 'unread')
  assert.equal(cave.letterPending.value, null)
  assert.equal(cave.pendingAction.value, null)
  assert.deepEqual(await cave.readLetter('letter-one'), inbox)
  assert.deepEqual(requests, [['letter-one', { request_id: 'read-request' }], ['letter-one', { request_id: 'read-request' }]])
  assert.deepEqual(cave.letter.value, marked)
  assert.deepEqual(cave.letters.value, inbox)
  assert.equal(cave.data.value.unread_letters_count, 0)
  assert.equal(cave.letterError.value, '')
  cave.dispose()
})


test('accepting a trial publishes the server weekly choice and does not block session actions', async () => {
  let reply
  const letter = { id: 'one', status: 'read' }
  const selected = { ...letter, status: 'accepted', trial: { status: 'accepted', can_accept: false } }
  const result = { letters: [selected], unread_count: 0, accepted_trial: { letter_id: 'one', week_start: '2026-09-14', status: 'accepted' } }
  const cave = useCave({
    getLetter: async () => letter,
    acceptLetter: () => new Promise(resolve => { reply = resolve }),
  }, { newRequestId: () => 'accept-one' })
  await cave.loadLetter('one')
  const pending = cave.acceptLetter('one')
  assert.deepEqual(cave.letterPending.value, { id: 'one', action: 'accept' })
  assert.equal(cave.pendingAction.value, null)
  reply(result)
  assert.deepEqual(await pending, result)
  assert.deepEqual(cave.letters.value.accepted_trial, result.accepted_trial)
  assert.deepEqual(cave.letter.value, selected)
  assert.equal(cave.letterPending.value, null)
  cave.dispose()
})


test('declining retains server authority and retries the same decision after a lost response', async () => {
  const requests = []
  const result = { letters: [{ id: 'two', status: 'declined', trial: { status: 'declined', can_accept: false } }], unread_count: 0, accepted_trial: null }
  const cave = useCave({
    getLetter: async () => ({ id: 'two', status: 'unread' }),
    declineLetter: async (id, payload) => {
      requests.push([id, payload])
      if (requests.length === 1) throw new Error('response lost')
      return result
    },
  }, { newRequestId: () => 'decline-two' })
  await cave.loadLetter('two')
  assert.equal(await cave.declineLetter('two'), false)
  assert.equal(cave.letter.value.status, 'unread')
  assert.deepEqual(await cave.declineLetter('two'), result)
  assert.deepEqual(requests, [['two', { request_id: 'decline-two' }], ['two', { request_id: 'decline-two' }]])
  assert.equal(cave.letter.value.status, 'declined')
  cave.dispose()
})


test('claiming retains the ready trial until confirmation and reuses its claim request', async () => {
  const requests = []
  const ready = { id: 'story', status: 'accepted', trial: { status: 'ready', current: 1 } }
  const completed = { ...ready, status: 'completed', trial: { status: 'completed', reward: { kind: 'codex', key: 'trial:quiet_night', name: '留一晚灯火', story: '一页山中故事。' } } }
  const result = { letters: [completed], unread_count: 0, accepted_trial: { letter_id: 'story', week_start: '2026-09-07', status: 'completed' } }
  const cave = useCave({
    getLetter: async () => ready,
    claimLetter: async (id, payload) => {
      requests.push([id, payload])
      if (requests.length === 1) throw new Error('lost response')
      return result
    },
  }, { newRequestId: () => 'claim-story' })
  await cave.loadLetter('story')
  assert.equal(await cave.claimLetter('story'), false)
  assert.deepEqual(cave.letter.value, ready)
  assert.deepEqual(await cave.claimLetter('story'), result)
  assert.deepEqual(requests, [['story', { request_id: 'claim-story' }], ['story', { request_id: 'claim-story' }]])
  assert.deepEqual(cave.letter.value.trial.reward, completed.trial.reward)
  cave.dispose()
})


test('late home inbox and detail reads cannot undo a confirmed letter decision', async () => {
  let homeReply, inboxReply, detailReply
  const original = { id: 'one', status: 'unread' }
  const marked = { ...original, status: 'read' }
  const result = { letters: [marked], unread_count: 0, accepted_trial: null }
  const cave = useCave({
    getCave: () => new Promise(resolve => { homeReply = resolve }),
    getLetters: () => new Promise(resolve => { inboxReply = resolve }),
    getLetter: () => new Promise(resolve => { detailReply = resolve }),
    readLetter: async () => result,
  }, { newRequestId: () => 'confirmed-read' })
  const home = cave.load(), inbox = cave.loadLetters(), detail = cave.loadLetter('one')
  await cave.readLetter('one')
  homeReply({ unread_letters_count: 1 })
  inboxReply({ ...result, letters: [original], unread_count: 1 })
  detailReply(original)
  await Promise.all([home, inbox, detail])
  assert.equal(cave.data.value.unread_letters_count, 0)
  assert.deepEqual(cave.letters.value, result)
  assert.deepEqual(cave.letter.value, marked)
  cave.dispose()
})


for (const action of ['reroll', 'selectSign']) {
  test(`a late ${action} snapshot retains newer unread state without cancelling the sign action`, async () => {
    let reply
    const initial = { date: '2026-09-14', unread_letters_count: 2, primary_sign: { id: 'old' }, reroll_used: false }
    const cave = useCave({
      getCave: async () => initial,
      [action]: () => new Promise(resolve => { reply = resolve }),
      readLetter: async () => ({ letters: [{ id: 'one', status: 'read' }], unread_count: 1, accepted_trial: null }),
    }, { newRequestId: () => 'request' })
    await cave.load()
    const pending = cave[action]('fresh')
    await cave.readLetter('one')
    reply({ ...initial, primary_sign: { id: 'fresh' } })
    assert.equal(await pending, true)
    assert.equal(cave.data.value.unread_letters_count, 1)
    assert.equal(cave.primarySign.value.id, 'fresh')
    assert.equal(cave.pendingAction.value, null)
    cave.dispose()
  })
}


test('letters load independently and retain the last inbox if refresh fails', async () => {
  let reply, fail = false
  const inbox = { letters: [], unread_count: 0, accepted_trial: null }
  const cave = useCave({
    getLetters: () => fail ? Promise.reject(new Error('offline')) : new Promise(resolve => { reply = resolve }),
  })
  assert.equal(cave.letters.value, null)
  const pending = cave.loadLetters()
  assert.equal(cave.lettersLoading.value, true)
  assert.equal(cave.loading.value, false)
  reply(inbox)
  assert.deepEqual(await pending, inbox)
  assert.deepEqual(cave.letters.value, inbox)
  fail = true
  assert.equal(await cave.loadLetters(), false)
  assert.deepEqual(cave.letters.value, inbox)
  assert.ok(cave.lettersError.value)
  assert.equal(cave.lettersLoading.value, false)
  assert.equal(cave.loadError.value, '')
  cave.dispose()
})
