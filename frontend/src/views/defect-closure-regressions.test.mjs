import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import axios from 'axios'
import { ref, toValue } from 'vue'
import {
  buildCoinHistoryParams,
  coinHistoryResponse,
  coinTransactionDateKey,
  coinTransactionPresentation,
  createCoinHistoryController,
  createCoinHistoryClient,
} from '../services/coinHistoryContract.js'
import { saveBudgetMutation } from '../services/budgetMutations.js'
import { createMilestoneReachRequestState } from '../utils/milestoneReachState.js'

const contractApi = {}

function replaceApiMethod(method, implementation) {
  const original = contractApi[method]
  contractApi[method] = implementation
  return () => { contractApi[method] = original }
}

async function loadNamedSource(relativePath, name, dependencies = {}) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8')
  const executable = source
    .replace(/^import[^\n]*\n/gm, '')
    .replace(/^export default[^\n]*\n/gm, '')
    .replace(/\bexport\s+(?=(?:const|function|class)\b)/g, '')
    .replace(/import\.meta\.env\.VITE_API_BASE_URL/g, "'/api'")
  const dependencyNames = Object.keys(dependencies)
  return new Function(...dependencyNames, `${executable}; return ${name}`)(
    ...dependencyNames.map(key => dependencies[key]),
  )
}

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

test('backpack history consumes canonical action types and covers every lifecycle action', async () => {
  const source = await readFile(new URL('./BackpackHistory.vue', import.meta.url), 'utf8')

  assert.match(source, /record\.action_type/)
  for (const action of ['add', 'use', 'equip', 'unequip', 'discard', 'refund']) {
    assert.match(source, new RegExp(action))
  }
})

test('exchange history prefers stored snapshots and uses stable unknown values when absent', async () => {
  const source = await readFile(new URL('./ExchangeHistory.vue', import.meta.url), 'utf8')
  const helperSource = source.match(/function exchangeItemPresentation\(record\) \{[\s\S]*?\n\}/)?.[0]

  assert.ok(helperSource, 'exchangeItemPresentation must remain available')
  assert.match(source, /item_name_snapshot/)
  assert.match(source, /unit_price_snapshot/)
  assert.match(source, /getItemPresentation\(record\)/)

  const exchangeItemPresentation = new Function(
    `${helperSource}; return exchangeItemPresentation`,
  )()

  assert.deepEqual(exchangeItemPresentation({
    item_id: 'archived-item',
    item_name_snapshot: '已归档奖励',
    unit_price_snapshot: 37,
  }, {}), {
    name: '已归档奖励',
    unitPrice: 37,
  })
  assert.deepEqual(exchangeItemPresentation({ item_id: 'legacy-item' }, {
    'legacy-item': { name: '旧商品', coin_price: 12 },
  }), {
    name: '未知商品',
    unitPrice: null,
  })
})

test('unrecoverable exchange history does not present mutable catalog values as a snapshot', async () => {
  const source = await readFile(new URL('./ExchangeHistory.vue', import.meta.url), 'utf8')
  const helperSource = source.match(/function exchangeItemPresentation\(record\) \{[\s\S]*?\n\}/)?.[0]
  assert.ok(helperSource, 'exchangeItemPresentation must remain available')

  const exchangeItemPresentation = new Function(
    `${helperSource}; return exchangeItemPresentation`,
  )()
  assert.deepEqual(exchangeItemPresentation({ item_id: 'legacy-item' }, {
    'legacy-item': { name: 'Catalog value changed later', coin_price: 99 },
  }), {
    name: '未知商品',
    unitPrice: null,
  })
})

test('exchange history refund mutation preserves records and shows the server reason on failure', async () => {
  const source = await readFile(new URL('./ExchangeHistory.vue', import.meta.url), 'utf8')
  const helperSource = source.match(/async function submitRefundMutation\(\{[\s\S]*?\n\}/)?.[0]

  assert.ok(helperSource, 'submitRefundMutation must remain available')
  assert.match(source, /shopService\.refundExchange/)
  assert.match(source, /@click="refundRecord\(record\)"/)
  assert.match(source, /refundErrors/)

  const submitRefundMutation = new Function(
    `${helperSource}; return submitRefundMutation`,
  )()
  const records = [{ id: 'exchange-1', status: 'completed', item_name_snapshot: '奖励' }]
  const originalRecords = structuredClone(records)

  const result = await submitRefundMutation({
    records,
    record: records[0],
    refundExchange: async () => {
      throw new Error('server rejected refund')
    },
    getErrorMessage: () => '请先卸下装备后再退款',
  })

  assert.equal(result.ok, false)
  assert.equal(result.error, '请先卸下装备后再退款')
  assert.strictEqual(result.records, records)
  assert.deepEqual(records, originalRecords)
})

test('exchange history refund mutation replaces the refunded record after success', async () => {
  const source = await readFile(new URL('./ExchangeHistory.vue', import.meta.url), 'utf8')
  const helperSource = source.match(/async function submitRefundMutation\(\{[\s\S]*?\n\}/)?.[0]
  assert.ok(helperSource, 'submitRefundMutation must remain available')

  const submitRefundMutation = new Function(
    `${helperSource}; return submitRefundMutation`,
  )()
  const record = { id: 'exchange-1', status: 'completed' }
  const updated = { id: 'exchange-1', status: 'refunded' }
  const result = await submitRefundMutation({
    records: [record],
    record,
    refundExchange: async (exchangeId) => {
      assert.equal(exchangeId, record.id)
      return updated
    },
    getErrorMessage: () => '退款失败，请重试。',
  })

  assert.equal(result.ok, true)
  assert.deepEqual(result.records, [updated])
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

test('transaction mutation keeps failed edit data and distinguishes edit from create feedback', async () => {
  const source = await readFile(new URL('./Finance.vue', import.meta.url), 'utf8')
  const helperSource = source.match(/async function submitTransactionMutation\(\{[\s\S]*?\n\}\n/)?.[0]
  assert.ok(helperSource, 'submitTransactionMutation must remain available')
  assert.match(source, /const wasEditing = Boolean\(editingTx\.value\)/)
  assert.match(source, /submitTransactionMutation\(/)
  assert.match(source, /return \{ feedback: wasEditing \? '流水已更新' : '记账成功！' \}/)
  assert.match(source, /const result = await submitTransactionMutation\([\s\S]*?\n\s*\}\)\n\s*cancelQuickAdd\(\)\n\s*showSuccess\(result\.feedback\)/)

  const submitTransactionMutation = new Function(
    `${helperSource}; return submitTransactionMutation`,
  )()
  const form = {
    type: 'expense', amount: 42, account_id: 'account-1', to_account_id: '',
    category_id: 'category-1', description: '保留编辑内容', date: '2026-09-15',
  }
  const originalForm = structuredClone(form)
  const editCalls = []
  const editFailure = await submitTransactionMutation({
    wasEditing: true,
    transactionId: 'transaction-1',
    form,
    service: {
      async updateTransaction(id, data) {
        editCalls.push({ id, data })
        throw new Error('保存失败')
      },
    },
  }).then(
    () => null,
    error => error,
  )
  assert.equal(editFailure.message, '保存失败')
  assert.deepEqual(editCalls, [{
    id: 'transaction-1',
    data: {
      type: 'expense', amount: 42, account_id: 'account-1', to_account_id: null,
      category_id: 'category-1', description: '保留编辑内容', date: '2026-09-15',
    },
  }])
  assert.deepEqual(form, originalForm)

  const edited = await submitTransactionMutation({
    wasEditing: true,
    transactionId: 'transaction-1',
    form,
    service: { async updateTransaction() {} },
  })
  const created = await submitTransactionMutation({
    wasEditing: false,
    transactionId: null,
    form,
    service: { async createTransaction() {} },
  })
  assert.equal(edited.feedback, '流水已更新')
  assert.equal(created.feedback, '记账成功！')
})

test('home habit flow consumes server state, completes, pauses, and resumes', async () => {
  const todoService = await loadNamedSource('../services/todo.js', 'todoService', { api: contractApi })
  const [source, todosSource] = await Promise.all([
    readFile(new URL('./Home.vue', import.meta.url), 'utf8'),
    readFile(new URL('./Todos.vue', import.meta.url), 'utf8'),
  ])
  const blockReasonSource = source.match(/function dailyHabitBlockReason\(habit\) \{[\s\S]*?\n\}/)?.[0]
  assert.ok(blockReasonSource, 'Home must keep its server-state lock helper available')
  const dailyHabitBlockReason = new Function(`${blockReasonSource}; return dailyHabitBlockReason`)()
  assert.match(source, /todoService\.getDailySummary\(\)/)
  assert.match(source, /todoService\.completeHabit\(habit\.id\)/)
  assert.match(todosSource, /todoService\.pauseHabit\(habit\.id\)/)
  assert.match(todosSource, /todoService\.resumeHabit\(habit\.id\)/)

  let habit = {
    id: 'habit-1', title: '晨间计划', is_active: true, paused_today: false,
    scheduled_today: true, completed_today: false,
  }
  const calls = []
  const restoreGet = replaceApiMethod('get', async (path) => {
    calls.push({ method: 'GET', path })
    return { data: { habits: [habit], summary: { total_habits: 1, completed_habits: habit.completed_today ? 1 : 0 } } }
  })
  const restorePost = replaceApiMethod('post', async (path) => {
    calls.push({ method: 'POST', path })
    if (path.endsWith('/complete')) habit = { ...habit, completed_today: true }
    if (path.endsWith('/pause')) habit = { ...habit, is_active: false, paused_today: true }
    if (path.endsWith('/resume')) habit = { ...habit, is_active: true, paused_today: false }
    return { data: habit }
  })
  try {
    const initial = await todoService.getDailySummary()
    assert.equal(initial.habits[0].is_active, true)
    assert.equal(initial.habits[0].paused_today, false)
    assert.equal(initial.habits[0].scheduled_today, true)
    assert.equal(dailyHabitBlockReason(initial.habits[0]), '')

    const completed = await todoService.completeHabit(habit.id)
    assert.equal(completed.completed_today, true)
    assert.match(dailyHabitBlockReason(completed), /已经完成/)

    habit = { ...habit, completed_today: false }
    const paused = await todoService.pauseHabit(habit.id)
    assert.equal(paused.is_active, false)
    assert.equal(paused.paused_today, true)
    assert.match(dailyHabitBlockReason(paused), /暂停/)

    const resumed = await todoService.resumeHabit(habit.id)
    assert.equal(resumed.is_active, true)
    assert.equal(resumed.paused_today, false)
    assert.equal(dailyHabitBlockReason(resumed), '')
    assert.deepEqual(calls.map(call => call.path), [
      '/todos/daily',
      '/todos/habits/habit-1/complete',
      '/todos/habits/habit-1/pause',
      '/todos/habits/habit-1/resume',
    ])
  } finally {
    restoreGet()
    restorePost()
  }
})

test('budget and debt forms send canonical DTOs and preserve failed input', async () => {
  const financeService = await loadNamedSource('../services/finance.js', 'financeService', { api: contractApi })
  const budgetForm = { category_id: 'food', amount: 50, period: 'monthly' }
  let budgetRequest
  const budgetFailure = await saveBudgetMutation({
    budgets: [{ id: 'existing', amount: 100 }],
    form: budgetForm,
    createBudget: async (data) => {
      budgetRequest = structuredClone(data)
      throw new Error('temporary budget failure')
    },
    getErrorMessage: error => error.message,
  })
  assert.deepEqual(budgetRequest, budgetForm)
  assert.deepEqual(budgetFailure.budgets, [{ id: 'existing', amount: 100 }])
  assert.deepEqual(budgetForm, { category_id: 'food', amount: 50, period: 'monthly' })

  const debtForm = {
    creditor: '供应商', type: 'borrow', amount: 300, remaining: 300,
    interest_rate: 0, due_date: '', description: '保留表单',
  }
  const calls = []
  const restorePost = replaceApiMethod('post', async (path, data) => {
    calls.push({ path, data })
    return { data: { id: 'debt-1', ...data } }
  })
  try {
    const created = await financeService.createDebt(debtForm)
    assert.deepEqual(created, { id: 'debt-1', ...debtForm })
    assert.deepEqual(calls, [{ path: '/finance/debts', data: debtForm }])
  } finally {
    restorePost()
  }
})

test('finance edit feedback and inactive-account errors remain actionable', async () => {
  const getErrorMessage = await loadNamedSource('../utils/errorMessage.js', 'getErrorMessage', {
    ERROR_MESSAGES: {},
    labelRealm: value => value,
  })
  const source = await readFile(new URL('./Finance.vue', import.meta.url), 'utf8')
  assert.match(source, /流水已更新/)
  assert.match(source, /txError\.value = getErrorMessage\(e\)/)
  assert.equal(getErrorMessage({
    response: {
      status: 409,
      data: {
        detail: { code: 'ACCOUNT_INACTIVE', message: '账户已停用，无法创建新的财务操作。' },
      },
    },
  }), '账户已停用，无法创建新的财务操作。')
})

test('backpack history and unequip use canonical action and lifecycle responses', async () => {
  const backpackService = await loadNamedSource('../services/backpack.js', 'backpackService', { api: contractApi })
  const calls = []
  const restoreGet = replaceApiMethod('get', async (path) => {
    calls.push({ method: 'GET', path })
    return { data: [{ id: 'history-1', action_type: 'unequip', item_id: 'gear-1' }] }
  })
  const restorePost = replaceApiMethod('post', async (path) => {
    calls.push({ method: 'POST', path })
    return { data: { id: 'gear-1', is_equipped: false, status: 'active' } }
  })
  try {
    const history = await backpackService.getHistory()
    const updated = await backpackService.unequipItem('gear-1')
    assert.equal(history[0].action_type, 'unequip')
    assert.deepEqual(updated, { id: 'gear-1', is_equipped: false, status: 'active' })
    assert.deepEqual(calls, [
      { method: 'GET', path: '/backpack/history' },
      { method: 'POST', path: '/backpack/items/gear-1/unequip' },
    ])
  } finally {
    restoreGet()
    restorePost()
  }
})

test('note folder rename and move preserve selection on success and failure', async () => {
  const noteService = await loadNamedSource('../services/note.js', 'noteService', { api: contractApi })
  const useNoteWorkspace = await loadNamedSource('../composables/useNoteWorkspace.js', 'useNoteWorkspace', {
    ref,
    toValue,
    noteService,
  })
  const initialTree = [
    { id: 'folder-1', type: 'folder', name: '旧目录', parent_id: null, children: [
      { id: 'note-1', type: 'note', name: '笔记', parent_id: 'folder-1', children: [] },
    ] },
    { id: 'folder-2', type: 'folder', name: '目标目录', parent_id: null, children: [] },
  ]
  let tree = structuredClone(initialTree)
  let failNextPatch = false
  const restoreGet = replaceApiMethod('get', async (path) => {
    assert.equal(path, '/notes/notebooks/book-1/tree')
    return { data: structuredClone(tree) }
  })
  const restorePatch = replaceApiMethod('patch', async (path, payload) => {
    if (failNextPatch) {
      failNextPatch = false
      throw new Error('note mutation failed')
    }
    if (path === '/notes/nodes/folder-1') tree[0].name = payload.name
    if (path === '/notes/nodes/note-1') {
      tree[0].children = []
      tree[1].children = [{ id: 'note-1', type: 'note', name: '笔记', parent_id: 'folder-2', children: [] }]
    }
    return { data: { id: path.split('/').pop(), ...payload } }
  })
  const workspace = useNoteWorkspace('book-1')
  try {
    await workspace.loadTree()
    workspace.selectNote('note-1')
    await workspace.renameNode('folder-1', '新目录')
    assert.equal(workspace.selectedNoteId.value, 'note-1')
    assert.equal(workspace.tree.value[0].name, '新目录')

    await workspace.moveNode('note-1', 'folder-2')
    assert.equal(workspace.selectedNoteId.value, 'note-1')
    assert.equal(workspace.currentFolderId.value, 'folder-2')
    assert.equal(workspace.tree.value[1].children[0].id, 'note-1')

    const treeBeforeFailure = JSON.parse(JSON.stringify(workspace.tree.value))
    failNextPatch = true
    await assert.rejects(() => workspace.renameNode('folder-1', '失败名称'), /note mutation failed/)
    assert.equal(workspace.selectedNoteId.value, 'note-1')
    assert.deepEqual(workspace.tree.value, treeBeforeFailure)
    assert.match(workspace.error.value.message, /note mutation failed/)
  } finally {
    restoreGet()
    restorePatch()
  }
})

test('project start and milestone reach use service routes, locks, and retry state', async () => {
  const projectService = await loadNamedSource('../services/project.js', 'projectService', { api: contractApi })
  const calls = []
  const restorePost = replaceApiMethod('post', async (path) => {
    calls.push(path)
    if (path === '/projects/project-1/start') return { data: { id: 'project-1', status: 'active' } }
    return { data: { id: 'milestone-1', status: 'reached', reached_at: '2026-09-16T00:00:00Z' } }
  })
  const requestState = createMilestoneReachRequestState()
  try {
    const started = await projectService.startProject('project-1')
    const token = requestState.begin('milestone-1', 'project-1', 4)
    const reached = await projectService.reachMilestone('milestone-1')
    assert.deepEqual(started, { id: 'project-1', status: 'active' })
    assert.equal(reached.status, 'reached')
    assert.equal(requestState.isCurrent(token, 'project-1', 4), true)
    requestState.finish(token)
    assert.equal(requestState.isCurrent(token, 'project-1', 4), false)
    assert.deepEqual(calls, ['/projects/project-1/start', '/projects/milestones/milestone-1/reach'])
  } finally {
    restorePost()
  }

  const [projects, detail] = await Promise.all([
    readFile(new URL('./Projects.vue', import.meta.url), 'utf8'),
    readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8'),
  ])
  assert.match(projects, /startPendingIds\.has\(project\.id\)/)
  assert.match(projects, /项目正在启动，请等待完成后再试。/)
  assert.match(detail, /milestoneReachPendingIds\.has\(milestone\.id\)/)
  assert.match(detail, /重试保存里程碑|请稍后再试/)
})

test('refresh callers share one Promise and reject incomplete refresh without looping', async () => {
  const refreshAuthToken = await loadNamedSource('../services/auth.js', 'refreshAuthToken', {
    api: contractApi,
    axios,
  })
  const source = await readFile(new URL('../services/api.js', import.meta.url), 'utf8')
  assert.match(source, /await\s+refreshAuthToken\(/)
  assert.match(source, /originalRequest\._retry\s*=\s*true/)
  assert.match(source, /return Promise\.reject\(error\)/)
  assert.doesNotMatch(source, /originalRequest\._retry\s*=\s*false/)

  const originalPost = axios.post
  let calls = 0
  let resolveRefresh
  axios.post = () => {
    calls += 1
    return new Promise(resolve => { resolveRefresh = resolve })
  }
  try {
    const first = refreshAuthToken('refresh-1')
    const second = refreshAuthToken('refresh-1')
    assert.strictEqual(first, second)
    resolveRefresh({ data: { access_token: 'access-2', refresh_token: 'refresh-2' } })
    assert.deepEqual(await first, { access_token: 'access-2', refresh_token: 'refresh-2' })
    assert.equal(calls, 1)
  } finally {
    axios.post = originalPost
  }
})
