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

/**
 * 复制文本到剪贴板
 * 优先使用 Clipboard API，如果不支持则使用 execCommand 兜底
 * @param text 要复制的文本
 * @returns Promise<void>
 */
export async function copyToClipboard(text: string): Promise<void> {
  // 优先使用现代 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text)
  }

  // 兜底方案：使用 execCommand
  return new Promise((resolve, reject) => {
    const textArea = document.createElement('textarea')
    textArea.value = text

    // 避免滚动到视图中
    textArea.style.cssText = `
      position: fixed;
      top: -9999px;
      left: -9999px;
      opacity: 0;
      pointer-events: none;
    `

    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    try {
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      if (successful) {
        resolve()
      } else {
        reject(new Error('execCommand copy failed'))
      }
    } catch (err) {
      document.body.removeChild(textArea)
      reject(err)
    }
  })
}
