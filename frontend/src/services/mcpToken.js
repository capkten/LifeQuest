import api from './api'

export const mcpTokenService = {
  async listTokens() {
    const response = await api.get('/auth/mcp-tokens', { skipErrorToast: true })
    return response.data
  },

  async createToken(data) {
    const response = await api.post('/auth/mcp-tokens', data)
    return response.data
  },

  async revokeToken(tokenId) {
    const response = await api.delete(`/auth/mcp-tokens/${tokenId}`)
    return response.data
  }
}
