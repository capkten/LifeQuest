import api from './api'

export const titleService = {
  /**
   * Get all available titles
   * @returns {Promise<Array>} List of all titles
   */
  async getAllTitles() {
    const response = await api.get('/titles')
    return response.data
  },

  /**
   * Get titles unlocked by current user
   * @returns {Promise<Array>} List of user's unlocked titles
   */
  async getMyTitles() {
    const response = await api.get('/titles/me')
    return response.data
  },

  /**
   * Activate a title for the current user
   * @param {number} titleId - ID of the title to activate
   * @returns {Promise<Object>} Updated user data
   */
  async activateTitle(titleId) {
    const response = await api.put('/titles/activate', { title_id: titleId })
    return response.data
  }
}
