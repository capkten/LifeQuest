import api from './api'

export const noteService = {
  /**
   * Get all notebooks for current user
   * @returns {Promise<Array>} List of notebooks
   */
  async getNotebooks() {
    const response = await api.get('/notes/notebooks')
    return response.data
  },

  /**
   * Create a new notebook
   * @param {Object} data - Notebook data (name, description)
   * @returns {Promise<Object>} Created notebook
   */
  async createNotebook(data) {
    const response = await api.post('/notes/notebooks', data)
    return response.data
  }
}
