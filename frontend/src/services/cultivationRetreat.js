import api from './api.js'

export const cultivationRetreatService = {
  async startRetreat({ target_duration = 25, todo_id = null }) {
    const response = await api.post('/cultivation/retreat/start', {
      target_duration,
      todo_id,
    })
    return response.data
  },

  async getActive() {
    const response = await api.get('/cultivation/retreat/active')
    return response.data
  },

  async completeRetreat(retreatId, { mark_todo_complete = false } = {}) {
    const response = await api.post(`/cultivation/retreat/${retreatId}/complete`, {
      mark_todo_complete,
    })
    return response.data
  },

  async abortRetreat(retreatId) {
    const response = await api.post(`/cultivation/retreat/${retreatId}/abort`)
    return response.data
  },

  async getHistory({ limit = 20, offset = 0 } = {}) {
    const response = await api.get('/cultivation/retreat/history', {
      params: { limit, offset },
    })
    return response.data
  },

  async getCatalog() {
    const response = await api.get('/cultivation/retreat/encounters/catalog')
    return response.data
  },
}
