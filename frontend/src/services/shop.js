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
  async purchaseItem(itemId, quantity = 1, idempotencyKey) {
    const key = idempotencyKey || `purchase-${itemId}-${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`
    const response = await api.post('/shop/exchange', {
      item_id: itemId,
      quantity
    }, {
      headers: { 'Idempotency-Key': key }
    })
    return response.data
  },

  /**
   * Refund an exchange
   * @param {string} exchangeId - Exchange history ID
   * @returns {Promise<Object>} Refunded exchange history record
   */
  async refundExchange(exchangeId) {
    const response = await api.post(`/shop/exchange/${exchangeId}/refund`)
    return response.data
  },

  /**
   * Get exchange history
   * @returns {Promise<Array>} List of exchange history records
   */
  async getExchangeHistory() {
    const response = await api.get('/shop/exchange/history')
    return response.data
  },

  /**
   * Update a shop item
   * @param {string} itemId - Shop item ID
   * @param {Object} data - Fields to update
   * @returns {Promise<Object>} Updated shop item
   */
  async updateItem(itemId, data) {
    const response = await api.put(`/shop/items/${itemId}`, data)
    return response.data
  },

  /**
   * Delete a shop item
   * @param {string} itemId - Shop item ID
   * @returns {Promise<void>}
   */
  async deleteItem(itemId) {
    await api.delete(`/shop/items/${itemId}`)
  }
}
