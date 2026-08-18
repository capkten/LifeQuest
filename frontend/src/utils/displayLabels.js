import {
  EVENT_SUMMARY_LABELS,
  LOCK_REASON_LABELS,
  NPC_ROLE_LABELS,
  REALM_LABELS,
  RESOURCE_LABELS,
  SECT_KIND_LABELS,
  SLOT_TYPE_LABELS,
  STATUS_LABELS,
  TASK_PREFERENCE_LABELS,
  TECHNIQUE_TYPE_LABELS,
  DIFFICULTY_LABELS,
  FREQUENCY_LABELS,
  ACCOUNT_TYPE_LABELS,
  PERIOD_LABELS,
  SOURCE_LABELS,
  PROJECT_STATUS_LABELS,
  TASK_STATUS_LABELS,
  ITEM_TYPE_LABELS,
  ACTION_TYPE_LABELS,
  EXCHANGE_STATUS_LABELS,
  TRANSACTION_TYPE_LABELS,
} from '../locales/zh-CN.js'

export function labelRealm(value) {
  return labelValue(REALM_LABELS, value, '未知境界')
}

export function labelSectKind(value) {
  return labelValue(SECT_KIND_LABELS, value, '未知宗门类型')
}

export function labelTechniqueType(value) {
  return labelValue(TECHNIQUE_TYPE_LABELS, value, '未知功法类型')
}

export function labelTaskPreference(value) {
  return labelValue(TASK_PREFERENCE_LABELS, value, '未知任务偏好')
}

export function labelStatus(value) {
  return labelValue(STATUS_LABELS, value, '未知状态')
}

export function labelResource(value) {
  return labelValue(RESOURCE_LABELS, value, '未知资源')
}

export function labelSlotType(value) {
  return labelValue(SLOT_TYPE_LABELS, value, '未知格子类型')
}

export function labelNpcRole(value) {
  return labelValue(NPC_ROLE_LABELS, value, '未知身份')
}

export function labelEventSummary(value) {
  return labelValue(EVENT_SUMMARY_LABELS, value, '未知事件')
}

export function labelLockReason(value) {
  return labelValue(LOCK_REASON_LABELS, value, '未知渡劫状态')
}

export function labelDifficulty(value) {
  return labelValue(DIFFICULTY_LABELS, value, '未知难度')
}

export function labelFrequency(value) {
  return labelValue(FREQUENCY_LABELS, value, '未知频率')
}

export function labelAccountType(value) {
  return labelValue(ACCOUNT_TYPE_LABELS, value, '未知账户类型')
}

export function labelPeriod(value) {
  return labelValue(PERIOD_LABELS, value, '未知周期')
}

export function labelSource(value) {
  return labelValue(SOURCE_LABELS, value, '其他')
}

export function labelProjectStatus(value) {
  return labelValue(PROJECT_STATUS_LABELS, value, '未知项目状态')
}

export function labelTaskStatus(value) {
  return labelValue(TASK_STATUS_LABELS, value, '未知任务状态')
}

export function labelItemType(value) {
  return labelValue(ITEM_TYPE_LABELS, value, '未知物品类型')
}

export function labelActionType(value) {
  return labelValue(ACTION_TYPE_LABELS, value, '未知动作')
}

export function labelExchangeStatus(value) {
  return labelValue(EXCHANGE_STATUS_LABELS, value, '未知兑换状态')
}

export function labelTransactionType(value) {
  return labelValue(TRANSACTION_TYPE_LABELS, value, '未知交易类型')
}

export function isTrustedLabel(serverLabel, stableValue) {
  const label = normalizeLabel(serverLabel)
  const stableKey = normalizeLabel(stableValue)
  return Boolean(label && label !== stableKey && /[\u3400-\u9fff]/.test(label))
}

export function labelFromServer(record, labelKey, stableValue, fallback) {
  const serverLabel = record?.[labelKey]
  if (isTrustedLabel(serverLabel, stableValue)) return normalizeLabel(serverLabel)
  return typeof fallback === 'function' ? fallback(stableValue) : fallback
}

function labelValue(labels, value, fallback) {
  return typeof value === 'string' && labels[value] ? labels[value] : fallback
}

function normalizeLabel(value) {
  return typeof value === 'string' ? value.trim() : ''
}
