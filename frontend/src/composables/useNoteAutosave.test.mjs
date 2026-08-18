import assert from 'node:assert/strict'
import test from 'node:test'
import { ref } from 'vue'
import { useNoteAutosave } from './useNoteAutosave.js'

const source = ref({ title: 'Initial', content: '' })
let saveCalls = 0
const autosave = useNoteAutosave({
  snapshot: () => source.value,
  save: async (payload) => {
    saveCalls += 1
    assert.deepEqual(payload, { title: 'Updated', content: '' })
  },
})

autosave.reset(source.value)
source.value = { title: 'Updated', content: '' }
await autosave.saveNow()

assert.equal(saveCalls, 1)
assert.equal(autosave.dirty.value, false)
assert.equal(autosave.status.value, 'saved')

console.log('useNoteAutosave regression test passed')

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

test('cancel makes an in-flight autosave silent and prevents stale failure state', async () => {
  const draft = ref({ title: 'Before', content: '' })
  const request = deferred()
  const instance = useNoteAutosave({
    snapshot: () => draft.value,
    save: () => request.promise,
  })

  instance.reset(draft.value)
  draft.value = { title: 'After', content: '' }
  const savePromise = instance.saveNow()
  instance.cancel()
  request.reject(new Error('stale failure'))

  await assert.doesNotReject(savePromise)
  assert.notEqual(instance.status.value, 'error')
})

test('reset invalidates a prior successful autosave response', async () => {
  const draft = ref({ title: 'First', content: '' })
  const request = deferred()
  const instance = useNoteAutosave({
    snapshot: () => draft.value,
    save: () => request.promise,
  })

  instance.reset(draft.value)
  draft.value = { title: 'Old route', content: '' }
  const savePromise = instance.saveNow()
  draft.value = { title: 'New route', content: '' }
  instance.reset(draft.value)
  request.resolve()

  await savePromise
  assert.equal(instance.status.value, 'idle')
  assert.equal(instance.dirty.value, false)
})

test('real autosave failures remain observable and retryable', async () => {
  const draft = ref({ title: 'Initial', content: '' })
  let attempts = 0
  const instance = useNoteAutosave({
    snapshot: () => draft.value,
    save: async () => {
      attempts += 1
      throw new Error('real failure')
    },
  })

  instance.reset(draft.value)
  draft.value = { title: 'Changed', content: '' }
  await assert.rejects(instance.saveNow(), /real failure/)
  assert.equal(instance.status.value, 'error')
  assert.equal(attempts, 1)
})
