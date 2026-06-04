import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const refreshTokenValue = ref(localStorage.getItem('refreshToken') || null)
  const user = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  function setTokens(accessToken, refreshToken) {
    token.value = accessToken
    refreshTokenValue.value = refreshToken
    localStorage.setItem('token', accessToken)
    localStorage.setItem('refreshToken', refreshToken)
  }

  function clearTokens() {
    token.value = null
    refreshTokenValue.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  async function refreshAccessToken() {
    if (!refreshTokenValue.value) return false
    try {
      const response = await authService.refreshToken(refreshTokenValue.value)
      setTokens(response.access_token, response.refresh_token)
      return true
    } catch {
      clearTokens()
      return false
    }
  }

  async function login(credentials) {
    loading.value = true
    try {
      const response = await authService.login(credentials.username, credentials.password)
      setTokens(response.access_token, response.refresh_token)
      await fetchUser()
      const redirect = router.currentRoute.value.query.redirect || '/'
      router.push(redirect)
    } finally {
      loading.value = false
    }
  }

  async function register(userData) {
    loading.value = true
    try {
      await authService.register(userData)
      router.push({ name: 'Login' })
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    try {
      const userData = await authService.getCurrentUser()
      user.value = userData
    } catch (error) {
      logout()
      throw error
    }
  }

  function logout() {
    token.value = null
    refreshTokenValue.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    router.push({ name: 'Login' })
  }

  return {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout,
    refreshAccessToken,
  }
})
