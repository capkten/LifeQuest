import { ERROR_MESSAGES } from '../locales/zh-CN.js'

const STATUS_MESSAGES = Object.freeze({
  400: '请求参数错误',
  403: '没有权限执行此操作',
  404: '资源不存在',
  409: '请求冲突，请检查后重试',
  422: '请求数据格式错误',
  500: '服务器内部错误，请稍后重试',
})

function translateDetail(detail) {
  if (typeof detail !== 'string') return null
  if (ERROR_MESSAGES[detail]) return ERROR_MESSAGES[detail]
  if (/[\u3400-\u9fff]/.test(detail)) return detail
  return null
}

export function getErrorMessage(error, fallback = '操作失败，请重试。') {
  const detail = error?.response?.data?.detail
  const detailMessage = typeof detail === 'object' ? detail?.message : detail
  const errorCode = error?.code || error?.message
  const translatedDetail = translateDetail(detailMessage || errorCode)
  if (translatedDetail) return translatedDetail
  if (error?.response?.status && STATUS_MESSAGES[error.response.status]) return STATUS_MESSAGES[error.response.status]
  if (!error?.response && error?.request) return '网络连接失败，请检查网络。'
  return fallback
}
