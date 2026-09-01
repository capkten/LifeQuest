import api from './api'

export const actionCenterService = {
  /**
   * Get the server-computed action center for the current China-local day.
   * @param {string} [date] - Optional date in YYYY-MM-DD format.
   * @returns {Promise<Object>} Action center payload.
   */
  async getToday(date) {
    const params = date ? { date } : undefined
    const response = await api.get('/action-center/today', { params })
    return response.data
  },
}
