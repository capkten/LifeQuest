import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import {
  buildCoinHistoryParams,
  coinHistoryResponse,
  coinTransactionDateKey,
  coinTransactionPresentation,
  createCoinHistoryController,
  createCoinHistoryClient,
} from '../services/coinHistoryContract.js'
import { saveBudgetMutation } from '../services/budgetMutations.js'

test('coin history maps the response envelope and renders both directions by type', () => {
  const income = { type: 'earn', amount: 20 }
  const expense = { type: 'spend', amount: 20 }

  assert.deepEqual(coinHistoryResponse({
    transactions: [income, expense],
    total_earned: 10,
    total_spent: 20,
    count: 21,
  }), {
    transactions: [income, expense],
    total_earned: 10,
    total_spent: 20,
    count: 21,
  })
  assert.deepEqual(coinTransactionPresentation(income), {
    isSpend: false,
    sign: '+',
    amount: 20,
    iconClass: 'tx-icon--income',
    amountClass: 'tx-amount--positive',
  })
  assert.deepEqual(coinTransactionPresentation(expense), {
    isSpend: true,
    sign: '-',
    amount: 20,
    iconClass: 'tx-icon--expense',
    amountClass: 'tx-amount--negative',
  })
})

test('coin history controller runs initial and load-more workflow using filtered count', async () => {
  const calls = []
  let filters = { type: 'income', source: 'task' }
  const responses = [
    {
      transactions: [{ id: 1, type: 'earn', amount: 10 }],
      total_earned: 10,
      total_spent: 0,
      count: 3,
    },
    {
      transactions: [{ id: 2, type: 'earn', amount: 5 }],
      total_earned: 15,
      total_spent: 0,
      count: 3,
    },
    {
      transactions: [{ id: 3, type: 'spend', amount: 4 }],
      total_earned: 15,
      total_spent: 4,
      count: 1,
    },
  ]
  const service = createCoinHistoryClient({
    async get(path, options) {
      calls.push({ path, options })
      return { data: responses.shift() }
    },
  })
  const controller = createCoinHistoryController({
    getHistory: (params) => service.getHistory(params),
    getFilters: () => filters,
    pageSize: 2,
  })

  await controller.fetchHistory()
  assert.deepEqual(calls[0].options.params, {
    coin_type: 'earn',
    source: 'task',
    skip: 0,
    limit: 2,
  })
  assert.deepEqual(controller.state.transactions, [{ id: 1, type: 'earn', amount: 10 }])
  assert.equal(controller.state.historyCount, 3)
  assert.equal(controller.state.hasMore, true)
  assert.deepEqual(coinTransactionPresentation(controller.state.transactions[0]), {
    isSpend: false,
    sign: '+',
    amount: 10,
    iconClass: 'tx-icon--income',
    amountClass: 'tx-amount--positive',
  })

  await controller.loadMore()
  assert.deepEqual(calls[1].options.params, {
    coin_type: 'earn',
    source: 'task',
    skip: 1,
    limit: 2,
  })
  assert.deepEqual(controller.state.transactions, [
    { id: 1, type: 'earn', amount: 10 },
    { id: 2, type: 'earn', amount: 5 },
  ])
  assert.equal(controller.state.hasMore, true)

  filters = { type: 'expense', source: 'shop' }
  await controller.fetchHistory()
  assert.deepEqual(calls[2].options.params, {
    coin_type: 'spend',
    source: 'shop',
    skip: 0,
    limit: 2,
  })
  assert.deepEqual(controller.state.transactions, [{ id: 3, type: 'spend', amount: 4 }])
  assert.equal(controller.state.historyCount, 1)
  assert.equal(controller.state.hasMore, false)
  assert.deepEqual(coinTransactionPresentation(controller.state.transactions[0]), {
    isSpend: true,
    sign: '-',
    amount: 4,
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

test('budget views consume server-computed budget statistics', async () => {
  const [budgetsView, financeView] = await Promise.all([
    readFile(new URL('./FinanceBudgets.vue', import.meta.url), 'utf8'),
    readFile(new URL('./Finance.vue', import.meta.url), 'utf8'),
  ])

  for (const source of [budgetsView, financeView]) {
    assert.match(source, /spent_amount/)
    assert.match(source, /remaining_amount/)
    assert.match(source, /progress/)
    assert.match(source, /category_name/)
    assert.doesNotMatch(source, /\bb\.spent\b/)
  }
  assert.match(budgetsView, /saveBudgetMutation/)
})

test('budget mutation failure preserves the list and a retry applies the response', async () => {
  const existing = { id: 'existing', amount: 100, spent_amount: 20 }
  const created = { id: 'created', amount: 50, spent_amount: 0 }
  const budgets = [existing]
  let attempts = 0

  const first = await saveBudgetMutation({
    budgets,
    form: { category_id: 'food', amount: 50, period: 'monthly' },
    createBudget: async () => {
      attempts += 1
      throw new Error('temporary failure')
    },
    getErrorMessage: error => error.message,
  })

  assert.equal(first.ok, false)
  assert.equal(first.error, 'temporary failure')
  assert.deepEqual(first.budgets, [existing])
  assert.deepEqual(budgets, [existing])

  const second = await saveBudgetMutation({
    budgets: first.budgets,
    form: { category_id: 'food', amount: 50, period: 'monthly' },
    createBudget: async () => {
      attempts += 1
      return created
    },
    getErrorMessage: error => error.message,
  })

  assert.equal(attempts, 2)
  assert.equal(second.ok, true)
  assert.deepEqual(second.budgets, [existing, created])
})

test('debt and recurring finance views use canonical contracts', async () => {
  const [debtsView, financeService, financeView] = await Promise.all([
    readFile(new URL('./FinanceDebts.vue', import.meta.url), 'utf8'),
    readFile(new URL('../services/finance.js', import.meta.url), 'utf8'),
    readFile(new URL('./Finance.vue', import.meta.url), 'utf8'),
  ])

  assert.match(debtsView, /form\.creditor/)
  assert.match(debtsView, /form\.type = 'borrow'/)
  assert.match(debtsView, /form\.type = 'lend'/)
  assert.match(debtsView, /remaining/)
  assert.match(debtsView, /status/)
  assert.match(debtsView, /payments/)
  assert.doesNotMatch(debtsView, /remaining \|\| amount/)
  assert.match(financeService, /updateRecurring/)
  assert.match(financeView, /流水已更新/)
  assert.match(financeView, /记账成功/)
})
