import api from './api'

export const cultivationService = {
  async getOverview() {
    const response = await api.get('/cultivation/overview')
    return response.data
  },

  async getWorld() {
    const response = await api.get('/cultivation/world')
    return response.data
  },

  async getSects(params) {
    const filters = params || {}
    const response = await api.get('/cultivation/sects', {
      params: {
        star: filters.star ?? null,
        kind: filters.kind ?? null,
        task_preference: filters.task_preference ?? null,
      },
    })
    return response.data
  },

  async joinSect(sectId) {
    const response = await api.post(`/cultivation/sects/${sectId}/join`)
    return response.data
  },

  async contactSectMessenger(sectId) {
    const response = await api.post(`/cultivation/sects/${sectId}/messenger/contact`)
    return response.data
  },

  async completeSectTrial(sectId) {
    const response = await api.post(`/cultivation/sects/${sectId}/trial/complete`)
    return response.data
  },

  async leaveSect() {
    const response = await api.post('/cultivation/sects/leave')
    return response.data
  },

  async getTechniques() {
    const response = await api.get('/cultivation/techniques')
    return response.data
  },

  async learnTechnique(techniqueKey) {
    const response = await api.post(`/cultivation/techniques/${techniqueKey}/learn`)
    return response.data
  },

  async purchaseSlot(slotType) {
    const response = await api.post('/cultivation/technique-slots/purchase', { slot_type: slotType })
    return response.data
  },

  async updateLoadout(loadout) {
    const response = await api.put('/cultivation/loadout', { loadout })
    return response.data
  },

  async getNpcs() {
    const response = await api.get('/cultivation/npcs')
    return response.data
  },

  async meetNpc({ sect_key, population_index }) {
    const response = await api.post('/cultivation/npcs/meet', { sect_key, population_index })
    return response.data
  },

  async getTribulationPreview(pillCount = 0, config = {}) {
    const response = await api.get('/cultivation/tribulation/preview', { ...config, params: { pill_count: pillCount } })
    return response.data
  },

  async attemptTribulation({ pill_count }) {
    const response = await api.post('/cultivation/tribulation/attempt', { pill_count })
    return response.data
  },
}
