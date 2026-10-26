import test from 'node:test'
import assert from 'node:assert/strict'
import { safeLoginRedirect, createConsentState } from './mcpOAuthState.js'

test('login return path stays local and preserves pending authorization', () => {
  assert.equal(safeLoginRedirect('/oauth/authorize?request_id=opaque'), '/oauth/authorize?request_id=opaque')
  for (const value of ['https://evil.test', '//evil.test', '/\\evil.test', '/%2f%2fevil.test', '/%5cevil.test', 'javascript:alert(1)', ['/', '//evil'], null, '/\n/evil']) {
    assert.equal(safeLoginRedirect(value), '/', String(value))
  }
})
test('consent needs details, submits once and cannot repeat after callback', () => {
  const state = createConsentState()
  assert.equal(state.beginSubmit(), false)
  state.loaded({ client_name: 'ChatGPT' })
  assert.equal(state.beginSubmit(), true)
  assert.equal(state.beginSubmit(), false)
  state.failed('Please retry')
  assert.equal(state.error, 'Please retry')
  assert.equal(state.beginSubmit(), true)
  state.completed()
  assert.equal(state.beginSubmit(), false)
})
test('failed authorization details cannot be approved', () => {
  const state = createConsentState()
  state.failed('Expired')
  assert.equal(state.beginSubmit(), false)
  assert.equal(state.details, null)
})
