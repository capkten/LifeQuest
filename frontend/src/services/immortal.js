import api from './api'

export const immortalService = {
  async getOverview(config = {}) {
    const response = await api.get('/immortal/overview', config)
    return response.data
  },
  async ascend(requestKey) {
    const response = await api.post('/immortal/ascend', { request_key: requestKey })
    return response.data
  },
  async runActivity(activityId, requestKey) {
    const response = await api.post('/immortal/activities/run', { activity_id: activityId, request_key: requestKey })
    return response.data
  },
  async advanceStage(requestKey) {
    const response = await api.post('/immortal/stage/advance', { request_key: requestKey })
    return response.data
  },
  async commission(officialKey, requestKey) {
    const response = await api.post('/immortal/officials/commission', { official_key: officialKey, request_key: requestKey })
    return response.data
  }
}
