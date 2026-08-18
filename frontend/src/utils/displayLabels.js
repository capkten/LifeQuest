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

function labelValue(labels, value, fallback) {
  return typeof value === 'string' && labels[value] ? labels[value] : fallback
}
