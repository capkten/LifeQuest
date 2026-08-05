import { computed, ref, toValue } from 'vue'

const AUTOSAVE_STATUSES = ['idle', 'dirty', 'saving', 'saved', 'error']

function cloneSnapshot(value) {
  if (value == null) return value
  return JSON.parse(JSON.stringify(value))
}

function snapshotsEqual(left, right) {
  return JSON.stringify(left) === JSON.stringify(right)
}

function resolveSnapshot(source) {
  const value = typeof source === 'function' ? source() : toValue(source)
  return value == null ? null : cloneSnapshot(value)
}

export function useNoteAutosave({ snapshot, save, delay = 900, initialSnapshot = null } = {}) {
  if (typeof save !== 'function') throw new TypeError('useNoteAutosave requires a save function')

  const savedSnapshot = ref(initialSnapshot == null ? null : resolveSnapshot(initialSnapshot))
  const hasBaseline = ref(savedSnapshot.value !== null)
  let timer = null
  let queued = false
  const inFlight = ref(null)
  const status = ref('idle')
  const lastSavedAt = ref(null)

  const dirty = computed(() => {
    const currentSnapshot = resolveSnapshot(snapshot)
    return currentSnapshot !== null && (!hasBaseline.value || !snapshotsEqual(currentSnapshot, savedSnapshot.value))
  })

  function schedule() {
    const currentSnapshot = resolveSnapshot(snapshot)
    if (currentSnapshot === null) return

    if (!hasBaseline.value) {
      savedSnapshot.value = currentSnapshot
      hasBaseline.value = true
      status.value = 'idle'
      return
    }

    if (timer) clearTimeout(timer)
    if (dirty.value) status.value = 'dirty'
    timer = setTimeout(() => {
      timer = null
      saveNow()
    }, Math.max(0, delay))
  }

  function saveNow() {
    if (inFlight.value) {
      queued = true
      return inFlight.value
    }

    if (!dirty.value) {
      if (status.value !== 'saved') status.value = 'idle'
      return Promise.resolve(null)
    }

    const payload = resolveSnapshot(snapshot)
    if (payload === null) return Promise.resolve(null)

    status.value = 'saving'
    const request = Promise.resolve().then(() => save(payload))
    inFlight.value = request

    request
      .then(() => {
        savedSnapshot.value = payload
        hasBaseline.value = true
        lastSavedAt.value = new Date()
        status.value = dirty.value ? 'dirty' : 'saved'
        if (queued || dirty.value) {
          queued = false
          schedule()
        } else {
          queued = false
        }
      })
      .catch(() => {
        status.value = 'error'
        queued = false
      })
      .finally(() => {
        if (inFlight.value === request) inFlight.value = null
      })

    return request
  }

  function reset(nextSnapshot = resolveSnapshot(snapshot), savedAt = null) {
    if (timer) clearTimeout(timer)
    timer = null
    queued = false
    savedSnapshot.value = nextSnapshot == null ? null : resolveSnapshot(nextSnapshot)
    hasBaseline.value = savedSnapshot.value !== null
    lastSavedAt.value = savedAt ? new Date(savedAt) : null
    status.value = 'idle'
  }

  function cancel() {
    if (timer) clearTimeout(timer)
    timer = null
    queued = false
  }

  return {
    dirty,
    status,
    lastSavedAt,
    schedule,
    saveNow,
    cancel,
    reset,
    statuses: AUTOSAVE_STATUSES,
  }
}

export default useNoteAutosave
