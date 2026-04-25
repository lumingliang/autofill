import dayjs from 'dayjs'

export function formatDateTime(time?: string | number | Date, format = 'YYYY-MM-DD HH:mm:ss') {
  return dayjs(time).format(format)
}

export function formatDate(date?: string | number | Date, format = 'YYYY-MM-DD') {
  return formatDateTime(date, format)
}

export function isNullOrWhitespace(val: unknown): boolean {
  return val === null || val === undefined || val === ''
}

export function isEmpty(val: unknown): boolean {
  if (Array.isArray(val) || typeof val === 'string') {
    return val.length === 0
  }
  if (val instanceof Map || val instanceof Set) {
    return val.size === 0
  }
  if (typeof val === 'object' && val !== null) {
    return Object.keys(val).length === 0
  }
  return false
}
