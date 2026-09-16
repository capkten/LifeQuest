import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/auth'
import router from '../router'
import { useCultivationStore } from './cultivation'
import { registerAuthCleanup } from '../services/authSession'

let refreshPromise = null
let logoutPromise = null

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const refreshTokenValue = ref(localStorage.getItem('refreshToken') || null)
  const user = ref(null)
  const loading = ref(false)
  const cultivationStore = useCultivationStore()

  function clearAuthState() {
    cultivationStore.clear()
    clearTokens()
    user.value = null
  }

  registerAuthCleanup(logout)

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

  function refreshAccessToken() {
    if (refreshPromise) return refreshPromise
    if (!refreshTokenValue.value) return Promise.resolve(false)

    const refreshTokenAtStart = refreshTokenValue.value
    refreshPromise = authService.refreshToken(refreshTokenAtStart)
      .then((response) => {
        if (refreshTokenValue.value === refreshTokenAtStart) {
          setTokens(response.access_token, response.refresh_token)
        }
        return true
      })
      .catch(() => {
        if (refreshTokenValue.value === refreshTokenAtStart) {
          logout()
        }
        return false
      })
      .finally(() => {
        refreshPromise = null
      })

    return refreshPromise
  }

  async function login(credentials) {
    loading.value = true
    cultivationStore.clear()
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
      if (user.value?.id && user.value.id !== userData.id) {
        cultivationStore.clear()
      }
      user.value = userData
    } catch (error) {
      logout()
      throw error
    }
  }

  function logout() {
    if (logoutPromise) return logoutPromise
    const refreshTokenAtLogout = refreshTokenValue.value
    clearAuthState()
    router.push({ name: 'Login' })

    if (!refreshTokenAtLogout) return Promise.resolve()
    logoutPromise = authService.logout(refreshTokenAtLogout)
      .catch(() => undefined)
      .finally(() => {
        logoutPromise = null
      })
    return logoutPromise
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
