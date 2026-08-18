import { ERROR_MESSAGES } from '../locales/zh-CN.js'

export function getErrorMessage(error, fallback = '操作失败，请重试。') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'object' && detail?.message) return detail.message
  if (typeof detail === 'string') {
    if (ERROR_MESSAGES[detail]) return ERROR_MESSAGES[detail]
    if (/[\u3400-\u9fff]/.test(detail)) return detail
  }
  if (!error?.response && error?.request) return '网络连接失败，请检查网络。'
  return fallback
}
