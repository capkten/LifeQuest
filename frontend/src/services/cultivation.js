import api from './api'

export const cultivationService = {
  async getOverview() {
    const response = await api.get('/api/cultivation/overview')
    return response.data
  },

  async getWorld() {
    const response = await api.get('/api/cultivation/world')
    return response.data
  },

  async getSects(params) {
    const response = await api.get('/api/cultivation/sects', { params })
    return response.data
  },

  async joinSect(sectId) {
    const response = await api.post(`/api/cultivation/sects/${sectId}/join`)
    return response.data
  },

  async leaveSect() {
    const response = await api.post('/api/cultivation/sects/leave')
    return response.data
  },

  async getTechniques() {
    const response = await api.get('/api/cultivation/techniques')
    return response.data
  },

  async purchaseSlot(slotType) {
    const response = await api.post('/api/cultivation/technique-slots/purchase', { slot_type: slotType })
    return response.data
  },

  async updateLoadout(loadout) {
    const response = await api.put('/api/cultivation/loadout', { loadout })
    return response.data
  },

  async getNpcs() {
    const response = await api.get('/api/cultivation/npcs')
    return response.data
  },

  async getTribulationPreview() {
    const response = await api.get('/api/cultivation/tribulation/preview')
    return response.data
  },

  async attemptTribulation(payload) {
    const response = await api.post('/api/cultivation/tribulation/attempt', payload)
    return response.data
  },
}
