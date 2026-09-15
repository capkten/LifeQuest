import { chinaDateKey } from '../utils/dateTime.js'

const UI_TYPE_MAP = {
  income: 'earn',
  expense: 'spend',
}

export function buildCoinHistoryParams({
  type,
  coin_type,
  source,
  start_date,
  end_date,
  skip = 0,
  limit = 50,
} = {}) {
  const params = { skip, limit }
  const coinType = coin_type || UI_TYPE_MAP[type] || type
  if (coinType) params.coin_type = coinType
  if (source) params.source = source
  if (start_date) params.start_date = start_date
  if (end_date) params.end_date = end_date
  return params
}

export function coinHistoryResponse(data) {
  return {
    transactions: Array.isArray(data?.transactions) ? data.transactions : [],
    total_earned: data?.total_earned ?? 0,
    total_spent: data?.total_spent ?? 0,
    count: data?.count ?? 0,
  }
}

export function coinTransactionPresentation(transaction) {
  const isSpend = transaction?.type === 'spend'
  return {
    isSpend,
    sign: isSpend ? '-' : '+',
    amount: Math.abs(Number(transaction?.amount) || 0),
    iconClass: isSpend ? 'tx-icon--expense' : 'tx-icon--income',
    amountClass: isSpend ? 'tx-amount--negative' : 'tx-amount--positive',
  }
}

export function coinTransactionDateKey(value) {
  return chinaDateKey(value) || chinaDateKey()
}

export function createCoinHistoryClient(apiClient) {
  return {
    async getHistory(params) {
      const response = await apiClient.get('/coins/history', {
        params: buildCoinHistoryParams(params),
      })
      return coinHistoryResponse(response.data)
    },
  }
}

export function createCoinHistoryController({
  getHistory,
  getFilters = () => ({}),
  pageSize = 20,
  formatError = (error, fallback) => error?.message || fallback,
} = {}) {
  const state = {
    transactions: [],
    loading: true,
    error: null,
    loadingMore: false,
    loadMoreError: null,
    historyCount: 0,
    hasMore: false,
  }
  let requestSequence = 0
  let filterGeneration = 0

  function historyParams(skip) {
    return buildCoinHistoryParams({
      ...getFilters(),
      skip,
      limit: pageSize,
    })
  }

  async function fetchHistory() {
    const requestId = ++requestSequence
    ++filterGeneration
    state.loading = true
    state.error = null
    state.loadMoreError = null
    state.loadingMore = false
    state.hasMore = false
    state.historyCount = 0
    try {
      const result = await getHistory(historyParams(0))
      if (requestId !== requestSequence) return
      state.transactions = result?.transactions || []
      state.historyCount = result?.count || 0
      state.hasMore = state.transactions.length < state.historyCount
    } catch (error) {
      if (requestId === requestSequence) {
        state.error = formatError(error, '加载金币记录失败，请重试。')
      }
    } finally {
      if (requestId === requestSequence) state.loading = false
    }
  }

  async function loadMore() {
    if (state.loadingMore || !state.hasMore) return
    const requestId = ++requestSequence
    const generation = filterGeneration
    const nextSkip = state.transactions.length
    state.loadingMore = true
    state.loadMoreError = null
    try {
      const result = await getHistory(historyParams(nextSkip))
      if (requestId !== requestSequence || generation !== filterGeneration) return
      const items = result?.transactions || []
      state.transactions.push(...items)
      state.historyCount = result?.count || state.historyCount
      state.hasMore = state.transactions.length < state.historyCount
    } catch (error) {
      if (requestId === requestSequence && generation === filterGeneration) {
        state.loadMoreError = formatError(error, '加载更多金币记录失败，请重试。')
      }
    } finally {
      if (requestId === requestSequence && generation === filterGeneration) {
        state.loadingMore = false
      }
    }
  }

  return { state, fetchHistory, loadMore }
}
