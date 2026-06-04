import api from './api'

export const coinService = {
  /**
   * Get coin transaction history with optional filters
   * @param {Object} params - Query params (type, source, page, limit)
   * @returns {Promise<Object>} Paginated transaction list
   */
  async getHistory(params) {
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
