const STORAGE_PREFIX = 'lifequest:cave:v1:'

function storageKey(userId) {
  return `${STORAGE_PREFIX}${encodeURIComponent(String(userId))}`
}

function emptyEnvelope() {
  return { version: 1, cache: null, queue: [] }
}

export function createCavePersistence({ storage } = {}) {
  if (storage === undefined) {
    try { storage = globalThis.localStorage } catch { storage = null }
  }
  return {
    async load(userId) {
      if (!storage || !userId) return emptyEnvelope()
      const raw = storage.getItem(storageKey(userId))
      if (!raw) return emptyEnvelope()
      try {
        const value = JSON.parse(raw)
        if (value?.version !== 1) return emptyEnvelope()
        return {
          version: 1,
          cache: value?.cache || null,
          queue: Array.isArray(value?.queue) ? value.queue : [],
        }
      } catch {
        return emptyEnvelope()
      }
    },

    async save(userId, envelope) {
      if (!storage) throw new Error('Cave storage is unavailable')
      if (!userId) throw new Error('Cave storage requires a user identity')
      storage.setItem(storageKey(userId), JSON.stringify({
        version: 1,
        cache: envelope?.cache || null,
        queue: Array.isArray(envelope?.queue) ? envelope.queue : [],
      }))
    },

    async clear(userId) {
      if (!storage || !userId) return
      storage.removeItem(storageKey(userId))
    },
  }
}

export const defaultCavePersistence = createCavePersistence()
