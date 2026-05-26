import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  /**
   * Login user
   * @param {Object} credentials - { username, password }
   */
  async function login(credentials) {
    loading.value = true
    try {
      const response = await authService.login(credentials.username, credentials.password)
      token.value = response.access_token
      localStorage.setItem('token', response.access_token)

      // Fetch user data after login
      await fetchUser()

      // Redirect to intended route or home
      const redirect = router.currentRoute.value.query.redirect || '/'
      router.push(redirect)
    } finally {
      loading.value = false
    }
  }

  /**
   * Register new user
   * @param {Object} userData - { username, email, password }
   */
  async function register(userData) {
    loading.value = true
    try {
      await authService.register(userData)
      // Redirect to login page after successful registration
      router.push({ name: 'Login' })
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch current user data
   */
  async function fetchUser() {
    try {
      const userData = await authService.getCurrentUser()
      user.value = userData
    } catch (error) {
      // If fetching user fails, clear auth state
      logout()
      throw error
    }
  }

  /**
   * Logout user
   */
  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    router.push({ name: 'Login' })
  }

  return {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout
  }
})
