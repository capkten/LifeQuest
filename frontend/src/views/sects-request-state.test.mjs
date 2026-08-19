import assert from 'node:assert/strict'
import test from 'node:test'
import { createSequencedRequest } from './sects-request-state.js'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

test('a later sect request wins when real promises resolve out of order', async () => {
  const events = []
  const requests = createSequencedRequest({
    onStart: () => events.push('loading'),
    onSuccess: (value) => events.push(`success:${value}`),
    onError: (error) => events.push(`error:${error.message}`),
    onFinish: () => events.push('finished'),
  })
  const first = deferred()
  const second = deferred()

  const firstRun = requests(() => first.promise)
  const secondRun = requests(() => second.promise)
  second.resolve('latest')
  first.resolve('stale')
  await Promise.all([firstRun, secondRun])

  assert.deepEqual(events, ['loading', 'loading', 'success:latest', 'finished'])
})

test('stale sect errors do not clear the latest loading state or overwrite its result', async () => {
  const state = { loading: false, error: null, value: null }
  const requests = createSequencedRequest({
    onStart: () => {
      state.loading = true
      state.error = null
    },
    onSuccess: (value) => {
      state.value = value
    },
    onError: (error) => {
      state.error = error
    },
    onFinish: () => {
      state.loading = false
    },
  })
  const first = deferred()
  const second = deferred()

  const firstRun = requests(() => first.promise)
  const secondRun = requests(() => second.promise)
  first.reject(new Error('stale failure'))
  await firstRun
  assert.equal(state.loading, true)
  assert.equal(state.error, null)

  second.reject(new Error('latest failure'))
  await secondRun
  assert.equal(state.loading, false)
  assert.equal(state.error?.message, 'latest failure')
})

test('cancelled requests do not surface stale failures', async () => {
  const events = []
  const requests = createSequencedRequest({
    onStart: () => events.push('loading'),
    onSuccess: (value) => events.push(`success:${value}`),
    onError: (error) => events.push(`error:${error.message}`),
    onFinish: () => events.push('finished'),
  })
  const pending = deferred()
  const run = requests(() => pending.promise)

  requests.cancel()
  pending.reject(new Error('cancelled failure'))
  await run

  assert.deepEqual(events, ['loading'])
})
