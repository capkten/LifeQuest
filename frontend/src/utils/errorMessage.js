import { ERROR_MESSAGES } from '../locales/zh-CN.js'

const STATUS_MESSAGES = Object.freeze({
  400: '请求参数错误',
  403: '没有权限执行此操作',
  404: '资源不存在',
  409: '请求冲突，请检查后重试',
  422: '请求数据格式错误',
  500: '服务器内部错误，请稍后重试',
})

const CODE_MESSAGES = Object.freeze({
  INSUFFICIENT_SPIRIT_STONES: '灵石不足，请先完成任务获得灵石后再试。',
  REALM_PREREQUISITE: '境界不足，请先提升境界后再试。',
  TRIBULATION_PREREQUISITE: '渡劫前置条件未满足，请先完成渡劫试炼并达到要求。',
  TRIBULATION_COOLDOWN_ACTIVE: '渡劫冷却中，请等待冷却结束后再试。',
  'Insufficient coins': '金币不足，请先获得更多金币后再试。',
  'Item is out of stock': '商品已售罄，请选择其他商品。',
  'Already checked in today': '今天已经签到过了。',
})

function translateDetail(detail) {
  if (typeof detail !== 'string') return null
  if (ERROR_MESSAGES[detail]) return ERROR_MESSAGES[detail]
  if (/[\u3400-\u9fff]/.test(detail)) return detail
  return null
}

function detailParts(detail) {
  if (typeof detail !== 'string') return null
  const [code, ...parameters] = detail.split(':')
  return { code, parameters }
}

function translateCode(code, parameters = []) {
  if (!code) return null
  const direct = translateDetail(code) || CODE_MESSAGES[code]
  if (direct) return direct
  const parameterized = parameters.length ? translateDetail(`${code}:${parameters.join(':')}`) : null
  return parameterized || CODE_MESSAGES[`${code}:${parameters.join(':')}`] || null
}

export function getErrorMessage(error, fallback = '操作失败，请重试。') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') {
    const translatedDetail = translateDetail(detail) || translateCode(...Object.values(detailParts(detail)))
    if (translatedDetail) return translatedDetail
  } else if (detail && typeof detail === 'object') {
    const detailMessage = detail.message || detail.detail
    const translatedMessage = translateDetail(detailMessage)
    if (translatedMessage) return translatedMessage
    const parameters = detail.parameters || detail.params || []
    const translatedCode = translateCode(detail.code, Array.isArray(parameters) ? parameters : Object.values(parameters))
    if (translatedCode) return translatedCode
  }
  const errorParts = detailParts(error?.code || error?.message)
  const translatedCode = errorParts && translateCode(errorParts.code, errorParts.parameters)
  if (translatedCode) return translatedCode
  const translatedError = translateDetail(error?.code || error?.message)
  if (translatedError) return translatedError
  if (error?.response?.status && STATUS_MESSAGES[error.response.status]) return STATUS_MESSAGES[error.response.status]
  if (!error?.response && error?.request) return '网络连接失败，请检查网络。'
  return fallback
}
