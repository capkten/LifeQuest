import { computed, onMounted, onUnmounted, ref, toValue, watch } from 'vue'
import { isDesktopRuntime, noteSyncService } from '../services/noteSync'
import { getErrorMessage } from '../utils/errorMessage'

function storageKey(notebookId) {
  return `lifequest.note-sync.${notebookId}`
}

function readBinding(notebookId) {
  try {
    const raw = localStorage.getItem(storageKey(notebookId))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveBinding(notebookId, value) {
  try { localStorage.setItem(storageKey(notebookId), JSON.stringify(value)) } catch { /* storage is optional */ }
}

export function useNoteSync(notebookId) {
  const binding = ref(null)
  const status = ref({ state: 'unbound', cursor: 0, pending_operations: 0, conflicts: 0 })
  const previewData = ref(null)
  const conflicts = ref([])
  const loading = ref(false)
  const error = ref(null)
  const desktop = computed(() => isDesktopRuntime())
  const listeners = []
  let requestId = 0

  function setError(cause) {
    error.value = cause
    status.value = { ...status.value, state: 'error', error: getErrorMessage(cause) }
  }

  async function load() {
    const id = toValue(notebookId)
    if (!id) return
    binding.value = readBinding(id)
    if (binding.value) {
      status.value = { ...status.value, state: binding.value.paused ? 'paused' : 'bound', cursor: binding.value.cursor || 0 }
    }
    try {
      conflicts.value = await noteSyncService.getConflicts(id)
      status.value = { ...status.value, conflicts: conflicts.value.filter(item => item.status === 'open').length }
    } catch (cause) {
      setError(cause)
    }
  }

  async function selectFolder() {
    loading.value = true
    error.value = null
    try {
      const selected = await noteSyncService.selectFolder()
      const id = toValue(notebookId)
      binding.value = {
        notebookId: String(id),
        folder: selected.path,
        deviceId: binding.value?.deviceId || crypto.randomUUID(),
        cursor: binding.value?.cursor || 0,
        paused: false,
      }
      saveBinding(id, binding.value)
      status.value = { ...status.value, state: 'bound', folder: selected.path, cursor: binding.value.cursor }
      previewData.value = null
      return binding.value
    } catch (cause) {
      setError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function previewSync() {
    if (!binding.value) throw new Error('SYNC_FOLDER_REQUIRED')
    loading.value = true
    error.value = null
    status.value = { ...status.value, state: 'previewing' }
    try {
      previewData.value = await noteSyncService.previewSync(
        binding.value.notebookId,
        binding.value.folder,
        binding.value.deviceId,
      )
      status.value = { ...status.value, state: 'preview', cursor: previewData.value.revision }
      return previewData.value
    } catch (cause) {
      setError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function start() {
    if (!binding.value) throw new Error('SYNC_FOLDER_REQUIRED')
    loading.value = true
    error.value = null
    status.value = { ...status.value, state: 'syncing' }
    try {
      const nextStatus = await noteSyncService.startSync(binding.value)
      status.value = { ...status.value, ...nextStatus }
      binding.value = { ...binding.value, cursor: nextStatus.cursor || binding.value.cursor, paused: false }
      saveBinding(binding.value.notebookId, binding.value)
      await load()
      return nextStatus
    } catch (cause) {
      setError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function syncNow() {
    if (!binding.value) throw new Error('SYNC_FOLDER_REQUIRED')
    loading.value = true
    error.value = null
    status.value = { ...status.value, state: 'syncing' }
    try {
      const report = await noteSyncService.syncNow(binding.value)
      status.value = { ...status.value, ...report.status }
      binding.value = { ...binding.value, cursor: report.status.cursor || binding.value.cursor, paused: false }
      saveBinding(binding.value.notebookId, binding.value)
      await refreshConflicts()
      return report
    } catch (cause) {
      setError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function pause() {
    if (!binding.value) return null
    const nextStatus = await noteSyncService.pauseSync(binding.value)
    status.value = { ...status.value, ...nextStatus }
    binding.value = { ...binding.value, paused: true }
    saveBinding(binding.value.notebookId, binding.value)
    return nextStatus
  }

  async function resume() {
    if (!binding.value) return null
    const nextStatus = await noteSyncService.resumeSync(binding.value)
    status.value = { ...status.value, ...nextStatus }
    binding.value = { ...binding.value, cursor: nextStatus.cursor || binding.value.cursor, paused: false }
    saveBinding(binding.value.notebookId, binding.value)
    return nextStatus
  }

  async function refreshConflicts() {
    conflicts.value = await noteSyncService.getConflicts(toValue(notebookId))
    status.value = { ...status.value, conflicts: conflicts.value.filter(item => item.status === 'open').length }
    return conflicts.value
  }

  async function resolveConflict(conflict, resolution, content) {
    if (!binding.value) throw new Error('SYNC_FOLDER_REQUIRED')
    loading.value = true
    error.value = null
    try {
      const report = await noteSyncService.resolveConflict(
        binding.value,
        conflict.id,
        resolution,
        content,
        conflict.remote_revision,
      )
      await refreshConflicts()
      status.value = { ...status.value, ...report.status }
      return report
    } catch (cause) {
      setError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  function listenToEvents() {
    if (!desktop.value) return
    for (const name of ['sync://status', 'sync://progress', 'sync://conflict', 'sync://error']) {
      noteSyncService.listen(name, event => {
        const payload = event?.payload || event
        if (name === 'sync://conflict') refreshConflicts().catch(setError)
        else if (name === 'sync://error') setError(new Error(payload?.error || payload?.message || 'SYNC_ERROR'))
        else status.value = { ...status.value, ...(payload || {}) }
      }).then?.(unlisten => listeners.push(unlisten))
    }
  }

  watch(notebookId, () => { requestId += 1; load() }, { immediate: true })
  onMounted(listenToEvents)
  onUnmounted(() => {
    requestId += 1
    while (listeners.length) {
      const unlisten = listeners.pop()
      try { unlisten?.() } catch { /* listener cleanup is best-effort */ }
    }
  })

  return {
    binding,
    status,
    preview: previewData,
    conflicts,
    loading,
    error,
    isDesktop: desktop,
    load,
    selectFolder,
    previewSync,
    start,
    pause,
    resume,
    syncNow,
    refreshConflicts,
    resolveConflict,
  }
}
