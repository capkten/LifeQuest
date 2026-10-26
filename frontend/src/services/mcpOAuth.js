import api from './api'

const options = { skipErrorToast: true }
export const mcpOAuthService = {
  async details(requestId) {
    return (await api.get(`/oauth/requests/${encodeURIComponent(requestId)}`, options)).data
  },
  async consent(requestId, approve) {
    return (await api.post('/oauth/consent', { request_id: requestId, approve }, options)).data
  },
  async listGrants() {
    return (await api.get('/oauth/grants', options)).data
  },
  async revokeGrant(grantId) {
    await api.delete(`/oauth/grants/${encodeURIComponent(grantId)}`, options)
  },
}
