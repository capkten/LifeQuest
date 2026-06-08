import api from './api'

export const authService = {
  /**
   * Login user with username and password
   * @param {string} username
   * @param {string} password
   * @returns {Promise<Object>} Response with access_token and refresh_token
   */
  async login(username, password) {
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('password', password)

    const response = await api.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
    return response.data
  },

  /**
   * Refresh access token using refresh token
   * @param {string} refreshToken
   * @returns {Promise<Object>} Response with new access_token and refresh_token
   */
  async refreshToken(refreshToken) {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },

  /**
   * Register new user
   * @param {Object} userData - { username, email, password }
   * @returns {Promise<Object>} Response with user data
   */
  async register(userData) {
    const response = await api.post('/auth/register', userData)
    return response.data
  },

  /**
   * Get current user profile
   * @returns {Promise<Object>} User data
   */
  async getCurrentUser() {
    const response = await api.get('/users/me')
    return response.data
  },

  /**
   * Update current user profile
   * @param {Object} data - { username, email }
   * @returns {Promise<Object>} Updated user data
   */
  async updateProfile(data) {
    const response = await api.put('/users/me', data)
    return response.data
  },

  /**
   * Upload avatar for current user
   * @param {File} file - The avatar image file
   * @returns {Promise<Object>} Response with avatar URL
   */
  async uploadAvatar(file) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/users/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }
}
