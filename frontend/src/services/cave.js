import api from './api.js'

export const caveService = {
  async getCave() {
    const response = await api.get('/cave/today', { skipErrorToast: true })
    return response.data
  },

  async skipOnboarding(data) {
    const response = await api.post('/cave/onboarding/skip', data, { skipErrorToast: true })
    return response.data
  },

  async completeOnboarding(data) {
    const response = await api.post('/cave/onboarding/complete', data, { skipErrorToast: true })
    return response.data
  },

  async startSession(data) {
    const response = await api.post('/cave/sessions', data, { skipErrorToast: true })
    return response.data
  },

  async getSession(id) {
    const response = await api.get(`/cave/sessions/${id}`, { skipErrorToast: true })
    return response.data
  },

  async settleSession(id, data) {
    const response = await api.post(`/cave/sessions/${id}/settle`, data, { skipErrorToast: true })
    return response.data
  },

  async acknowledgeReturn(id, data) {
    const response = await api.post(`/cave/sessions/${id}/acknowledge`, data, { skipErrorToast: true })
    return response.data
  },

  async createQuickTask(data) {
    const response = await api.post('/todos/workbench/tasks', data, { skipErrorToast: true })
    return response.data
  },

  async getCandidates() {
    const response = await api.get('/todos/tasks', { skipErrorToast: true })
    return response.data
  },

  async reroll(data) {
    const response = await api.post('/cave/signs/reroll', data, { skipErrorToast: true })
    return response.data
  },

  async selectSign(data) {
    const response = await api.post('/cave/signs/select', data, { skipErrorToast: true })
    return response.data
  },

  async getLetters() {
    const response = await api.get('/cave/letters', { skipErrorToast: true })
    return response.data
  },

  async getLetter(id) {
    const response = await api.get(`/cave/letters/${id}`, { skipErrorToast: true })
    return response.data
  },

  async readLetter(id, data) {
    const response = await api.post(`/cave/letters/${id}/read`, data, { skipErrorToast: true })
    return response.data
  },

  async acceptLetter(id, data) {
    const response = await api.post(`/cave/letters/${id}/accept`, data, { skipErrorToast: true })
    return response.data
  },

  async declineLetter(id, data) {
    const response = await api.post(`/cave/letters/${id}/decline`, data, { skipErrorToast: true })
    return response.data
  },

  async claimLetter(id, data) {
    const response = await api.post(`/cave/letters/${id}/claim`, data, { skipErrorToast: true })
    return response.data
  },

  async getGrowth() {
    const response = await api.get('/cave/growth', { skipErrorToast: true })
    return response.data
  },

  async getCodex() {
    const response = await api.get('/cave/codex', { skipErrorToast: true })
    return response.data
  },

  async getCompanions() {
    const response = await api.get('/cave/companions', { skipErrorToast: true })
    return response.data
  },

  async activateCompanion(key, data) {
    const response = await api.post(`/cave/companions/${key}/activate`, data, { skipErrorToast: true })
    return response.data
  },

  async recordEvent(data) {
    const response = await api.post('/cave/events', data, { skipErrorToast: true })
    return response.data
  },
}
