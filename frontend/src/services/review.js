import api from './api'

export const reviewService = {
  async getWeeklyReview(weekStart) {
    const params = weekStart ? { week_start: weekStart } : {}
    const response = await api.get('/review/weekly', { params })
    return response.data
  }
}
