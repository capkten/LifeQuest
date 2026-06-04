import api from './api'

export const checkinService = {
  /**
   * Get current check-in status for today
   * @returns {Promise<Object>} Check-in status with streak info
   */
  async getStatus() {
    const response = await api.get('/checkin/status')
    return response.data
  },

  /**
   * Perform daily check-in
   * @returns {Promise<Object>} Check-in result with rewards
   */
  async checkin() {
    const response = await api.post('/checkin')
    return response.data
  }
}
