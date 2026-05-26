import api from './api'

export const shopService = {
  /**
   * Get all shop items
   * @param {Object} params - { skip, limit }
   * @returns {Promise<Array>} List of shop items
   */
  async getItems(params = {}) {
    const response = await api.get('/shop/items', { params })
    return response.data
  },

  /**
   * Create a new shop item
   * @param {Object} data - Shop item data { name, description, icon, category, coin_price, stock }
   * @returns {Promise<Object>} Created shop item
   */
  async createItem(data) {
    const response = await api.post('/shop/items', data)
    return response.data
  },

  /**
   * Purchase a shop item
   * @param {string} itemId - Shop item ID
   * @param {number} quantity - Quantity to purchase (default 1)
   * @returns {Promise<Object>} Exchange history record
   */
  async purchaseItem(itemId, quantity = 1) {
    const response = await api.post('/shop/exchange', {
      item_id: itemId,
      quantity
    })
    return response.data
  },

  /**
   * Get exchange history
   * @returns {Promise<Array>} List of exchange history records
   */
  async getExchangeHistory() {
    const response = await api.get('/shop/exchange/history')
    return response.data
  }
}
