import test from 'node:test'
import assert from 'node:assert/strict'
import { createCavePersistence } from './cavePersistence.js'

test('unsupported persistence versions never restore another schema as current cache', async () => {
  const storage = { getItem: () => JSON.stringify({ version: 99, cache: { date: '2026-09-12' }, queue: [{ id: 'unknown' }] }) }
  const persistence = createCavePersistence({ storage })
  assert.deepEqual(await persistence.load('alice'), { version: 1, cache: null, queue: [] })
})

test('persistence rejects unavailable storage instead of promising a durable settlement', async () => {
  const persistence = createCavePersistence({ storage: null })
  await assert.rejects(persistence.save('alice', { cache: null, queue: [{ id: 'session' }] }), /storage/i)
})

test('restricted storage access is unavailable rather than an application import failure', async () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('storage denied') } })
  try {
    const persistence = createCavePersistence()
    assert.deepEqual(await persistence.load('alice'), { version: 1, cache: null, queue: [] })
    await assert.rejects(persistence.save('alice', { cache: null, queue: [] }), /storage/i)
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor)
    else delete globalThis.localStorage
  }
})

test('the storage adapter isolates identities, survives a new adapter, and clears only the chosen user', async () => {
  const values = new Map()
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
  const first = createCavePersistence({ storage })
  await first.save('alice', { cache: { date: '2026-09-12' }, queue: [{ id: 'alice-session' }] })
  await first.save('bob', { cache: { date: '2026-09-13' }, queue: [{ id: 'bob-session' }] })
  const restored = createCavePersistence({ storage })
  assert.equal((await restored.load('alice')).queue[0].id, 'alice-session')
  assert.equal((await restored.load('bob')).cache.date, '2026-09-13')
  await restored.clear('alice')
  assert.deepEqual(await restored.load('alice'), { version: 1, cache: null, queue: [] })
  assert.equal((await restored.load('bob')).queue[0].id, 'bob-session')
})

test('corrupt storage is not interpreted as a cache or settlement intent', async () => {
  const persistence = createCavePersistence({ storage: { getItem: () => '{broken' } })
  assert.deepEqual(await persistence.load('alice'), { version: 1, cache: null, queue: [] })
})
