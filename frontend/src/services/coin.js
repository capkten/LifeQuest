import api from './api'

export const coinService = {
  /**
   * Get coin transaction history with optional filters
   * @param {Object} params - Query params (coin_type, source, start_date, end_date, skip, limit)
   * @returns {Promise<Object>} Paginated transaction list
   */
  async getHistory({ coin_type, source, start_date, end_date, skip = 0, limit = 50 } = {}) {
    const params = { skip, limit }
    for (const [key, value] of Object.entries({ coin_type, source, start_date, end_date })) {
      if (value !== undefined && value !== null && value !== '') params[key] = value
    }
    const response = await api.get('/coins/history', { params })
    return response.data
  },

  /**
   * Get coin totals (earned, spent)
   * @returns {Promise<Object>} Total earned and spent amounts
   */
  async getTotals() {
    const response = await api.get('/coins/totals')
    return response.data
  }
}
