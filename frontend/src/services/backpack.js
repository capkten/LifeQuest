import api from './api'

export const backpackService = {
  /**
   * Get backpack items, optionally filtered by status
   * @param {Object} params - { status }
   * @returns {Promise<Array>} List of backpack items
   */
  async getItems(params = {}) {
    const response = await api.get('/backpack/items', { params })
    return response.data
  },

  /**
   * Use a backpack item
   * @param {string} itemId - Backpack item ID
   * @param {number} quantity - Quantity to use (default 1)
   * @returns {Promise<Object>} Updated backpack item
   */
  async useItem(itemId, quantity = 1) {
    const response = await api.post(`/backpack/items/${itemId}/use`, null, {
      params: { quantity }
    })
    return response.data
  },

  /**
   * Discard a backpack item
   * @param {string} itemId - Backpack item ID
   * @param {number} quantity - Quantity to discard (default 1)
   * @returns {Promise<Object>} Updated backpack item
   */
  async discardItem(itemId, quantity = 1) {
    const response = await api.post(`/backpack/items/${itemId}/discard`, null, {
      params: { quantity }
    })
    return response.data
  },

  /**
   * Get usage history
   * @returns {Promise<Array>} List of usage history records
   */
  async getHistory() {
    const response = await api.get('/backpack/history')
    return response.data
  }
}
