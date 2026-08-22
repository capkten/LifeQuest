import { ERROR_MESSAGES } from '../locales/zh-CN.js'
import { labelRealm } from './displayLabels.js'

const STATUS_MESSAGES = Object.freeze({
  400: '请求参数错误',
  403: '没有权限执行此操作',
  404: '资源不存在',
  409: '请求冲突，请检查后重试',
  401: '用户名或密码错误，请检查后重试。',
  422: '请求数据格式错误',
  500: '服务器内部错误，请稍后重试',
})

const CODE_MESSAGES = Object.freeze({
  INSUFFICIENT_SPIRIT_STONES: '灵石不足，请先完成任务获得灵石后再试。',
  REALM_PREREQUISITE: '境界不足，请先提升境界后再试。',
  FINAL_MINOR_STAGE_REQUIRED: '尚未达到当前境界的最终小境界阈值。',
  TRIBULATION_PREREQUISITE: '渡劫前置条件未满足，请先完成渡劫试炼并达到要求。',
  TRIBULATION_COOLDOWN_ACTIVE: '渡劫冷却中，请等待冷却结束后再试。',
  'tribulation already complete': '渡劫已经完成，无需重复尝试。',
  'tribulation cooldown active': '渡劫冷却中，请等待冷却结束后再试。',
  'tribulation requires final minor stage threshold': '尚未达到当前境界的最终小境界阈值。',
  TRIAL_MESSENGER_REQUIRED: '请先联系入门使者，再开始宗门试炼。',
  'sect is locked': '宗门当前处于锁定状态，请先完成解锁条件。',
  'messenger contact required before trial': '请先联系入门使者，再开始宗门试炼。',
  'leave current sect before joining another': '请先退出当前宗门，再加入新的宗门。',
  'messenger contact required before meeting NPC': '请先联系宗门使者，再与 NPC 相遇。',
  'NPC meeting cooldown active': 'NPC 相遇仍在冷却中，请稍后再试。',
  'NPC population capacity reached': 'NPC 人口槽位已满，请选择其他槽位。',
  'Incorrect username or password': '用户名或密码错误，请检查后重试。',
  'Username already exists': '用户名已存在，请换一个用户名。',
  'Email already exists': '邮箱已存在，请换一个邮箱。',
  TRIAL_OBJECTIVE_UNMET: '还有试炼目标未完成，请先完成后再提交。',
  TRIAL_OBJECTIVE_NOT_FOUND: '试炼目标不存在，请刷新后重试。',
  HIDDEN_SECT_LOCKED: '隐藏宗门尚未现身，请先完成显示的解锁条件。',
  WORLD_NODE_PREVIOUS_REQUIRED: '请先完成前置节点，再探索这里。',
  WORLD_NODE_REALM_REQUIRED: '境界不足，暂时无法探索该节点。',
  WORLD_NODE_PROJECT_PHASE_REQUIRED: '项目阶段不足，暂时无法探索该节点。',
  WORLD_NODE_LOCKED: '该地图节点已锁定，请先完成解锁条件。',
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
  if (code === 'TECHNIQUE_REALM_REQUIRED' && parameters.length) {
    const realm = parameters.join(':').replace(/^technique requires\s+/i, '').replace(/\s+realm$/i, '')
    return `境界不足，需要达到${localizeRealm(realm)}后再学习或配置功法。`
  }
  if (code === 'SLOT_REALM_REQUIRED' && parameters.length) {
    const realm = parameters.join(':')
    return `境界不足，需要达到${localizeRealm(realm)}后购买功法格。`
  }
  const direct = translateDetail(code) || CODE_MESSAGES[code]
  if (direct) return direct
  const parameterized = parameters.length ? translateDetail(`${code}:${parameters.join(':')}`) : null
  return parameterized || CODE_MESSAGES[`${code}:${parameters.join(':')}`] || null
}

function localizeRealm(value) {
  const localized = labelRealm(value)
  return localized === '未知境界' && /[\u3400-\u9fff]/.test(value) ? value : localized
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
