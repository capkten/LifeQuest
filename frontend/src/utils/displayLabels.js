import {
  EVENT_SUMMARY_LABELS,
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
  return REALM_LABELS[value] || value || '未知境界'
}

export function labelSectKind(value) {
  return SECT_KIND_LABELS[value] || value || '未知宗门类型'
}

export function labelTechniqueType(value) {
  return TECHNIQUE_TYPE_LABELS[value] || value || '未知功法类型'
}

export function labelTaskPreference(value) {
  return TASK_PREFERENCE_LABELS[value] || value || '未知任务偏好'
}

export function labelStatus(value) {
  return STATUS_LABELS[value] || value || '未知状态'
}

export function labelResource(value) {
  return RESOURCE_LABELS[value] || value || '未知资源'
}

export function labelSlotType(value) {
  return SLOT_TYPE_LABELS[value] || value || '未知格子类型'
}

export function labelNpcRole(value) {
  return NPC_ROLE_LABELS[value] || value || '未知身份'
}

export function labelEventSummary(value) {
  return EVENT_SUMMARY_LABELS[value] || value || '未知事件'
}
