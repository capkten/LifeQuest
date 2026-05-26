import api from './api'

export const achievementService = {
  async getAchievements() {
    const response = await api.get('/achievements')
    return response.data
  },

  async getUserAchievements() {
    const response = await api.get('/achievements/me')
    return response.data
  }
}
