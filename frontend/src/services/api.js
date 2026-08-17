import axios from 'axios'
import { ElMessage } from 'element-plus'
import { invalidateAuthSession } from './authSession'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
const serverBaseUrl = apiBaseUrl.replace(/\/api\/?$/, '')

export function resolveUrl(path) {
  if (!path) return ''
  if (typeof path !== 'string') return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return serverBaseUrl + path
}

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Flag to prevent multiple refresh attempts
let isRefreshing = false
let refreshSubscribers = []

function onRefreshed(newToken) {
  refreshSubscribers.forEach(({ resolve }) => resolve(newToken))
  refreshSubscribers = []
}

function onRefreshFailed(error) {
  refreshSubscribers.forEach(({ reject }) => reject(error))
  refreshSubscribers = []
}

// Response interceptor to handle 401 errors with refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refreshToken')

      if (!refreshToken) {
        invalidateAuthSession()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Queue this request until refresh completes
        originalRequest._retry = true
        return new Promise((resolve, reject) => {
          refreshSubscribers.push({ resolve: (newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(api(originalRequest))
          }, reject })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const response = await axios.post(`${apiBaseUrl}/auth/refresh`, { refresh_token: refreshToken })
        const { access_token, refresh_token: newRefreshToken } = response.data

        localStorage.setItem('token', access_token)
        localStorage.setItem('refreshToken', newRefreshToken)

        onRefreshed(access_token)
        isRefreshing = false

        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        onRefreshFailed(refreshError)
        invalidateAuthSession()
        return Promise.reject(refreshError)
      }
    }

    // Unified error display for non-401 errors. Background metadata requests can
    // opt out when their failure must not interrupt the current screen.
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (!error.config?.skipErrorToast && status && status !== 401) {
      const messages = {
        400: detail || '请求参数错误',
        403: '没有权限执行此操作',
        404: detail || '资源不存在',
        422: '请求数据格式错误',
        500: '服务器内部错误，请稍后重试',
      }
      ElMessage.error(messages[status] || `请求失败 (${status})`)
    } else if (!error.config?.skipErrorToast && !error.response) {
      ElMessage.error('网络连接失败，请检查网络')
    }

    return Promise.reject(error)
  }
)

export default api
