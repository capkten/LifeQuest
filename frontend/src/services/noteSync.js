import api from './api'

export function isDesktopRuntime() {
  return Boolean(typeof window !== 'undefined' && (
    window.__TAURI__?.core?.invoke || window.__TAURI_INTERNALS__?.invoke
  ))
}

function serverEndpoint() {
  const configured = import.meta.env.VITE_API_BASE_URL
  if (configured && /^https?:\/\//.test(configured)) return configured.replace(/\/api\/?$/, '')
  return typeof window !== 'undefined' ? window.location.origin : ''
}

function authToken() {
  return typeof localStorage !== 'undefined' ? localStorage.getItem('token') || '' : ''
}

async function invokeDesktop(command, args = {}) {
  const invoke = window.__TAURI__?.core?.invoke || window.__TAURI_INTERNALS__?.invoke
  if (!invoke) {
    const error = new Error('DESKTOP_CLIENT_REQUIRED')
    error.code = 'DESKTOP_CLIENT_REQUIRED'
    throw error
  }
  return invoke(command, args)
}

function rustBinding(binding) {
  return {
    notebook_id: String(binding.notebookId || binding.notebook_id),
    folder: binding.folder,
    device_id: binding.deviceId || binding.device_id,
    cursor: Number(binding.cursor || 0),
  }
}

export const noteSyncService = {
  async getManifest(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}/sync/manifest`, { skipErrorToast: true })
    return response.data
  },

  async getConflicts(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}/sync/conflicts`, { skipErrorToast: true })
    return response.data.conflicts || []
  },

  async selectFolder() {
    return invokeDesktop('select_sync_folder')
  },

  async previewSync(notebookId, folder, deviceId) {
    return invokeDesktop('preview_sync', {
      notebookId: String(notebookId),
      folder,
      deviceId,
      endpoint: serverEndpoint(),
      token: authToken(),
    })
  },

  async startSync(binding) {
    return invokeDesktop('start_sync', {
      binding: rustBinding(binding),
      endpoint: serverEndpoint(),
      token: authToken(),
    })
  },

  async syncNow(binding) {
    return invokeDesktop('sync_now', {
      binding: rustBinding(binding),
      endpoint: serverEndpoint(),
      token: authToken(),
    })
  },

  async pauseSync(binding) {
    return invokeDesktop('pause_sync', { binding: rustBinding(binding), endpoint: serverEndpoint() })
  },

  async resumeSync(binding) {
    return invokeDesktop('resume_sync', {
      binding: rustBinding(binding),
      endpoint: serverEndpoint(),
      token: authToken(),
    })
  },

  async resolveConflict(binding, conflictId, resolution, content, baseRevision) {
    return invokeDesktop('resolve_conflict', {
      binding: rustBinding(binding),
      conflictId: String(conflictId),
      resolution,
      content,
      baseRevision,
      endpoint: serverEndpoint(),
      token: authToken(),
    })
  },

  async listen(eventName, handler) {
    const listen = window.__TAURI__?.event?.listen
    if (!listen) return () => {}
    return listen(eventName, handler)
  },
}
