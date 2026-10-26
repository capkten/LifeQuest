// Login may only return to an application path. Decode before checking so URL
// normalization cannot turn an encoded slash or backslash into another origin.
export function safeLoginRedirect(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return '/'
  let decoded
  try { decoded = decodeURIComponent(value) } catch { return '/' }
  if (!decoded.startsWith('/') || decoded.startsWith('//') || /[\\\u0000-\u0020\u007f]/.test(decoded)) return '/'
  return value
}

export function createConsentState() {
  return {
    details: null,
    submitting: false,
    finished: false,
    error: '',
    loaded(details) { this.details = details; this.error = '' },
    beginSubmit() {
      if (!this.details || this.submitting || this.finished) return false
      this.submitting = true
      this.error = ''
      return true
    },
    failed(message) { this.submitting = false; this.error = message },
    completed() { this.submitting = false; this.finished = true },
  }
}
