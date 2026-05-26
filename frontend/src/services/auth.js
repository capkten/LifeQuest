import api from './api'

export const authService = {
  /**
   * Login user with username and password
   * @param {string} username
   * @param {string} password
   * @returns {Promise<Object>} Response with access_token
   */
  async login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
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
  }
}
