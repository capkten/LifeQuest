import test from 'node:test'
import assert from 'node:assert/strict'
import { createCaveConnectivity } from './caveConnectivity.js'

test('browser connectivity reads the device state and removes online/offline listeners on disposal', () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  const navigator = { onLine: false }
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: navigator })
  try {
    const target = new EventTarget()
    const connectivity = createCaveConnectivity({ target })
    const changes = []
    const unsubscribe = connectivity.subscribe(online => changes.push(online))
    assert.equal(connectivity.isOnline(), false)
    navigator.onLine = true
    target.dispatchEvent(new Event('online'))
    assert.equal(connectivity.isOnline(), true)
    navigator.onLine = false
    target.dispatchEvent(new Event('offline'))
    assert.deepEqual(changes, [true, false])
    unsubscribe()
    target.dispatchEvent(new Event('online'))
    assert.deepEqual(changes, [true, false])
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'navigator', descriptor)
    else delete globalThis.navigator
  }
})
