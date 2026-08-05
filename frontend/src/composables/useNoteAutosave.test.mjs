import assert from 'node:assert/strict'
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
