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
