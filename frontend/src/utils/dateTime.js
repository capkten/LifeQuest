export function formatDateTimeInput(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const values = Object.fromEntries(
    parts.filter(({ type }) => type !== 'literal').map(({ type, value: part }) => [type, part]),
  )
  return `${values.year}-${values.month}-${values.day}T${values.hour}:${values.minute}`
}

const CHINA_TIME_ZONE = 'Asia/Shanghai'
const DATE_KEY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/
const CHINA_DATETIME_INPUT_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/

function validDateKeyParts(year, monthIndex, day) {
  if (!Number.isInteger(year) || !Number.isInteger(monthIndex) || !Number.isInteger(day)) return false
  const date = new Date(Date.UTC(year, monthIndex, day))
  return date.getUTCFullYear() === year && date.getUTCMonth() === monthIndex && date.getUTCDate() === day
}

function pad(value) {
  return String(value).padStart(2, '0')
}

function dateFromValue(value) {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  if (value === null || value === '') return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function isDateKey(value) {
  return typeof value === 'string' && DATE_KEY_PATTERN.test(value) && dateKeyParts(value) !== null
}

function dateForDateKey(dateKey) {
  const parts = dateKeyParts(dateKey)
  return parts ? new Date(Date.UTC(parts.year, parts.monthIndex, parts.day)) : null
}

function chinaDateParts(date) {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: CHINA_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const parts = formatter.formatToParts(date)
  return Object.fromEntries(parts.filter(({ type }) => type !== 'literal').map(({ type, value }) => [type, value]))
}

export function dateKeyParts(dateKey) {
  if (typeof dateKey !== 'string') return null
  const match = DATE_KEY_PATTERN.exec(dateKey)
  if (!match) return null
  const year = Number(match[1])
  const monthIndex = Number(match[2]) - 1
  const day = Number(match[3])
  return validDateKeyParts(year, monthIndex, day) ? { year, monthIndex, day } : null
}

export function dateKeyFromParts(year, monthIndex, day) {
  if (!validDateKeyParts(year, monthIndex, day)) return ''
  return `${String(year).padStart(4, '0')}-${pad(monthIndex + 1)}-${pad(day)}`
}

export function chinaDateTimeInputToUtcIso(value) {
  if (typeof value !== 'string') return ''
  const match = CHINA_DATETIME_INPUT_PATTERN.exec(value)
  if (!match) return ''
  const year = Number(match[1])
  const monthIndex = Number(match[2]) - 1
  const day = Number(match[3])
  const hour = Number(match[4])
  const minute = Number(match[5])
  const second = Number(match[6] || 0)
  if (!validDateKeyParts(year, monthIndex, day) || hour > 23 || minute > 59 || second > 59) return ''
  return new Date(Date.UTC(year, monthIndex, day, hour - 8, minute, second)).toISOString()
}

export function dateKeyTimestamp(dateKey) {
  const parts = dateKeyParts(dateKey)
  return parts ? Date.UTC(parts.year, parts.monthIndex, parts.day) : null
}

export function dateKeyFromTimestamp(timestamp) {
  if (!Number.isFinite(timestamp)) return ''
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  return dateKeyFromParts(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
}

export function chinaDateKey(value = new Date()) {
  if (isDateKey(value)) return value
  const date = dateFromValue(value)
  if (!date) return null
  const parts = chinaDateParts(date)
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function todayChinaDateKey(value = new Date()) {
  return chinaDateKey(value) || ''
}

export function shiftDateKey(dateKey, amount) {
  const parts = dateKeyParts(dateKey)
  if (!parts || !Number.isInteger(amount)) return ''
  const shifted = new Date(Date.UTC(parts.year, parts.monthIndex, parts.day + amount))
  return dateKeyFromParts(shifted.getUTCFullYear(), shifted.getUTCMonth(), shifted.getUTCDate())
}

export function weekdayForDateKey(dateKey) {
  const parts = dateKeyParts(dateKey)
  if (!parts) return null
  return (new Date(Date.UTC(parts.year, parts.monthIndex, parts.day)).getUTCDay() + 6) % 7
}

export function formatChinaDate(value, options = {}) {
  const date = isDateKey(value) ? dateForDateKey(value) : dateFromValue(value)
  if (!date) return ''
  return new Intl.DateTimeFormat('zh-CN', { ...options, timeZone: CHINA_TIME_ZONE }).format(date)
}

export function formatChinaDateTime(value, options = {}) {
  if (isDateKey(value)) return formatChinaDate(value, options)
  const date = dateFromValue(value)
  if (!date) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...options,
    timeZone: CHINA_TIME_ZONE,
  }).format(date)
}
