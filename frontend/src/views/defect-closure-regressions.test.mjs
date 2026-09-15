import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import {
  buildCoinHistoryParams,
  coinHistoryResponse,
  coinTransactionDateKey,
  coinTransactionPresentation,
  createCoinHistoryClient,
} from '../services/coinHistoryContract.js'

test('coin history maps the response envelope and renders type-driven spending', () => {
  const transaction = { type: 'spend', amount: 20 }

  assert.deepEqual(coinHistoryResponse({
    transactions: [transaction],
    total_earned: 10,
    total_spent: 20,
    count: 21,
  }), {
    transactions: [transaction],
    total_earned: 10,
    total_spent: 20,
    count: 21,
  })
  assert.deepEqual(coinTransactionPresentation(transaction), {
    isSpend: true,
    sign: '-',
    amount: 20,
    iconClass: 'tx-icon--expense',
    amountClass: 'tx-amount--negative',
  })
})

test('coin history service sends canonical filters and returns the response envelope', async () => {
  const calls = []
  const expected = {
    transactions: [{ id: 1, type: 'spend', amount: 20 }],
    total_earned: 10,
    total_spent: 20,
    count: 21,
  }
  const service = createCoinHistoryClient({
    async get(path, options) {
      calls.push({ path, options })
      return { data: expected }
    },
  })

  const result = await service.getHistory({
    type: 'expense',
    source: 'shop',
    start_date: '2026-09-01',
    end_date: '2026-09-15',
    skip: 20,
    limit: 20,
  })

  assert.deepEqual(calls, [{
    path: '/coins/history',
    options: {
      params: {
        coin_type: 'spend',
        source: 'shop',
        start_date: '2026-09-01',
        end_date: '2026-09-15',
        skip: 20,
        limit: 20,
      },
    },
  }])
  assert.deepEqual(result, expected)
})

test('coin history groups timestamps by the China business date', () => {
  const previousTimezone = process.env.TZ
  try {
    for (const timezone of ['UTC', 'Asia/Shanghai', 'America/Los_Angeles']) {
      process.env.TZ = timezone
      assert.equal(coinTransactionDateKey('2026-09-14T16:00:00Z'), '2026-09-15')
    }
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ
    else process.env.TZ = previousTimezone
  }
})

test('todo view consumes the server-owned habit state contract', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')

  assert.match(source, /habit\.is_active/)
  assert.match(source, /habit\.paused_today/)
  assert.match(source, /habit\.scheduled_today/)
})

test('calendar and stats render server-owned completion and cumulative experience', async () => {
  const calendar = await readFile(new URL('./Calendar.vue', import.meta.url), 'utf8')
  const stats = await readFile(new URL('./Stats.vue', import.meta.url), 'utf8')

  assert.match(calendar, /event-dot--['"] \+ dot\.status|dot\.status.*event-dot--/)
  assert.match(stats, /overview\.total_exp/)
})

test('goal editing does not settle a reward a second time', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')
  const saveItem = source.match(/async function saveItem\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(saveItem, 'saveItem must remain available')
  assert.doesNotMatch(saveItem, /settleCompletion\(/)
})

test('coin history source contract remains canonical', async () => {
  assert.deepEqual(buildCoinHistoryParams({
    type: 'expense',
    source: 'shop',
    start_date: '2026-09-01',
    end_date: '2026-09-15',
    skip: 20,
    limit: 20,
  }), {
    coin_type: 'spend',
    source: 'shop',
    start_date: '2026-09-01',
    end_date: '2026-09-15',
    skip: 20,
    limit: 20,
  })
})

test('coin history delegates rendering to the type-driven presentation contract', async () => {
  const history = await readFile(new URL('./CoinHistory.vue', import.meta.url), 'utf8')

  assert.match(history, /coinTransactionPresentation\(tx\)/)
})
