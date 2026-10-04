import api from './api'
import { createCoinHistoryClient } from './coinHistoryContract'

const historyClient = createCoinHistoryClient(api)

export const coinService = {
  ...historyClient,
  /**
   * Get coin totals (earned, spent)
   * @returns {Promise<Object>} Total earned and spent amounts
   */
  async getTotals() {
    const response = await api.get('/coins/totals')
    return response.data
  }
}
