import api from './api'

export const statsService = {
  async getOverview() {
    const response = await api.get('/stats/overview')
    return response.data
  },

  async getTaskTrends(period) {
    const response = await api.get('/stats/tasks', { params: { period } })
    return response.data
  },

  async getHabitStats(period) {
    const response = await api.get('/stats/habits', { params: { period } })
    return response.data
  },

  async getCoinTrends(period) {
    const response = await api.get('/stats/coins', { params: { period } })
    return response.data
  },

  async getLevelProgress() {
    const response = await api.get('/stats/level')
    return response.data
  },
}
