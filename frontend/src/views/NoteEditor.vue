<template>
  <div class="note-editor-page">
    <header class="editor-header">
      <div class="header-left">
        <button type="button" class="back-btn" aria-label="返回" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M19 12H5" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>
        <div>
          <p class="context-kicker">{{ contextLabel }}</p>
          <h1 class="page-title">{{ isEditing ? '编辑笔记' : '新建笔记' }}</h1>
        </div>
      </div>
      <div class="header-actions">
        <span class="save-status" :class="`save-status--${status}`" role="status" aria-live="polite">
          <span class="save-status-dot" aria-hidden="true"></span>
          {{ statusLabel }}
        </span>
        <button type="button" class="save-btn" :disabled="status === 'saving' || (isEditing && !hydrated)" @click="saveNote">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          {{ status === 'error' ? '重试并查看' : '保存并查看' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading-state" aria-live="polite">
      <div class="loading-spinner"></div>
      <span>正在加载笔记...</span>
    </div>

    <div v-else-if="loadError" class="error-state" role="alert">
      <span>{{ loadError }}</span>
      <button type="button" class="retry-btn" @click="loadRoute">重试</button>
    </div>

    <main v-else-if="hydrated" class="editor-body">
      <section class="editor-meta" aria-label="笔记详情">
        <label class="field field--title" for="note-title">
          <span class="sr-only">标题</span>
          <input id="note-title" v-model="noteTitle" type="text" class="title-input" placeholder="笔记标题" maxlength="200" />
        </label>
        <label class="field" for="note-summary">
          <span class="field-label">摘要</span>
          <textarea id="note-summary" v-model="noteSummary" class="meta-input meta-input--summary" rows="2" maxlength="500" placeholder="为读者写一段简短摘要"></textarea>
        </label>
        <label class="field" for="note-tags">
          <span class="field-label">标签</span>
          <input id="note-tags" v-model="noteTags" type="text" class="meta-input" placeholder="工作、想法、参考" maxlength="500" />
        </label>
        <label class="pin-field" for="note-pinned">
          <input id="note-pinned" v-model="isPinned" type="checkbox" />
          <span>置顶这篇笔记</span>
        </label>
      </section>

      <section class="editor-wrapper" aria-label="Markdown 编辑器">
        <v-md-editor
          v-model="noteContent"
          height="100%"
          placeholder="使用 Markdown 编写内容..."
          :disabled-menus="[]"
          @upload-image="handleUploadImage"
        />
      </section>
    </main>

    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show" class="toast" :class="toast.type" role="alert">{{ toast.message }}</div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { useNoteAutosave } from '../composables/useNoteAutosave'
import { noteService } from '../services/note'
import { getErrorMessage } from '../utils/errorMessage'

const route = useRoute()
const router = useRouter()

const noteTitle = ref('')
const noteContent = ref('')
const noteSummary = ref('')
const noteTags = ref('')
const isPinned = ref(false)
const noteId = ref(null)
const notebookId = ref(null)
const folderId = ref(null)
const loading = ref(false)
const hydrated = ref(false)
const loadError = ref(null)
const suppressRouteWarning = ref(false)
const toast = ref({ show: false, message: '', type: 'success' })

const isEditing = computed(() => !!noteId.value)
const contextLabel = computed(() => {
  if (notebookId.value && folderId.value) return `笔记本 ${notebookId.value} / 文件夹 ${folderId.value}`
  if (notebookId.value) return `笔记本 ${notebookId.value}`
  return '笔记'
})

function snapshot() {
  return {
    title: noteTitle.value.trim(),
    content: noteContent.value,
    summary: noteSummary.value.trim(),
    tags: noteTags.value.trim(),
    is_pinned: isPinned.value,
  }
}

function displayTime(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

const autosave = useNoteAutosave({ snapshot, delay: 900, save: persistNote })
const status = computed(() => autosave.status.value)
const statusLabel = computed(() => {
  if (status.value === 'dirty') return '有未保存的更改'
  if (status.value === 'saving') return '保存中...'
  if (status.value === 'error') return '保存失败 · 点击重试'
  if (status.value === 'saved') return `已保存 ${displayTime(autosave.lastSavedAt.value)}`
  return '所有更改已保存'
})

let toastTimer = null
let loadRequest = 0

function showToast(message, type = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

function showTitleRequiredError() {
  showToast(getErrorMessage(new Error('TITLE_REQUIRED')), 'error')
}

function routeContext() {
  return {
    noteId: route.params.noteId || route.params.id || null,
    notebookId: route.params.notebookId || null,
    folderId: route.query.parent_id || route.query.folder_id || null,
  }
}

async function loadRoute() {
  const requestId = ++loadRequest
  const context = routeContext()
  autosave.cancel()
  hydrated.value = false
  loadError.value = null
  noteId.value = context.noteId
  notebookId.value = context.notebookId
  folderId.value = context.folderId
  noteTitle.value = ''
  noteContent.value = ''
  noteSummary.value = ''
  noteTags.value = ''
  isPinned.value = false

  if (!noteId.value) {
    loading.value = false
    hydrated.value = true
    autosave.reset(snapshot())
    return
  }

  loading.value = true
  try {
    const note = await noteService.getNote(noteId.value)
    if (requestId !== loadRequest) return
    noteTitle.value = note.name || ''
    noteContent.value = note.content || ''
    noteSummary.value = note.summary || ''
    noteTags.value = note.tags || ''
    isPinned.value = !!note.is_pinned
    notebookId.value = note.notebook_id || notebookId.value
    folderId.value = note.parent_id || folderId.value
    autosave.reset(snapshot(), note.updated_at)
    hydrated.value = true
  } catch (error) {
    if (requestId === loadRequest) {
      loadError.value = getErrorMessage(error, '加载笔记失败，请重试。')
      showToast(loadError.value, 'error')
    }
  } finally {
    if (requestId === loadRequest) loading.value = false
  }
}

function scheduleAutosave() {
  if (hydrated.value) autosave.schedule()
}

async function persistNote(payload) {
  if (!payload.title) {
    showTitleRequiredError()
    throw new Error('TITLE_REQUIRED')
  }
  if (noteId.value) return noteService.updateNote(noteId.value, payload)
  if (!notebookId.value) throw new Error('NOTEBOOK_REQUIRED')

  const created = await noteService.createNote(notebookId.value, { ...payload, parent_id: folderId.value })
  noteId.value = created.id
  notebookId.value = created.notebook_id || notebookId.value
  folderId.value = created.parent_id || folderId.value
  suppressRouteWarning.value = true
  try {
    await router.replace({ name: 'NotebookWorkspaceEdit', params: { notebookId: notebookId.value, noteId: noteId.value } })
  } finally {
    suppressRouteWarning.value = false
  }
  return created
}

async function saveNote() {
  if (isEditing.value && !hydrated.value) {
    showToast(loadError.value || '笔记尚未加载完成，请先重试加载。', 'error')
    return
  }
  if (!noteTitle.value.trim()) {
    showTitleRequiredError()
    return
  }
  try {
    await autosave.saveNow()
    if (!autosave.dirty.value && noteId.value && notebookId.value) {
      await router.push({ name: 'NotebookWorkspaceView', params: { notebookId: notebookId.value, noteId: noteId.value } })
    }
  } catch (error) {
    showToast(getErrorMessage(error, '保存失败，请重试。'), 'error')
  }
}

async function handleUploadImage(event, insertCallback, files) {
  const file = files?.[0]
  if (!file) return
  try {
    const url = await noteService.uploadImage(file)
    insertCallback({ url })
  } catch (error) {
    showToast(getErrorMessage(error, '图片上传失败，请重试。'), 'error')
  }
}

function goBack() {
  if (noteId.value && notebookId.value) return router.push({ name: 'NotebookWorkspaceView', params: { notebookId: notebookId.value, noteId: noteId.value } })
  if (notebookId.value) return router.push({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } })
  return router.push({ name: 'Notes' })
}

function handleBeforeUnload(event) {
  if (!autosave.dirty.value || suppressRouteWarning.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave(() => {
  if (suppressRouteWarning.value || !autosave.dirty.value) return true
  return window.confirm('当前笔记有未保存的更改，确定要离开吗？')
})

watch(snapshot, scheduleAutosave, { deep: true })
watch(() => [route.name, route.params.id, route.params.noteId, route.params.notebookId, route.query.parent_id, route.query.folder_id], loadRoute, { immediate: true })

onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
onUnmounted(() => {
  autosave.cancel()
  window.removeEventListener('beforeunload', handleBeforeUnload)
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<style scoped>
.note-editor-page { display: flex; flex-direction: column; width: 100%; height: calc(100vh - 64px); height: calc(100dvh - 64px); min-width: 0; background: var(--color-bg-secondary); }
.editor-header { display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); padding: var(--spacing-md) var(--spacing-xl); border-bottom: 1px solid var(--color-border); flex-shrink: 0; background: var(--color-card); }
.header-left, .header-actions { display: flex; align-items: center; gap: var(--spacing-md); min-width: 0; }
.back-btn { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; padding: 0; border: 0; border-radius: var(--radius-md); color: var(--color-text); background: transparent; cursor: pointer; }
.back-btn:hover, .back-btn:focus-visible { background: var(--color-bg-secondary); outline: 2px solid var(--color-primary); outline-offset: 2px; }
.back-btn svg { width: 24px; height: 24px; }
.context-kicker, .field-label { margin: 0 0 var(--spacing-2xs); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.page-title { margin: 0; color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); }
.save-status { display: inline-flex; align-items: center; gap: var(--spacing-xs); color: var(--color-text-secondary); font-size: var(--font-size-sm); white-space: nowrap; }
.save-status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-success); }
.save-status--dirty .save-status-dot, .save-status--error .save-status-dot { background: var(--color-warning); }
.save-status--saving .save-status-dot { background: var(--color-primary); animation: pulse 1s ease-in-out infinite; }
.save-status--error { color: var(--color-error-dark); }
.save-btn { display: inline-flex; align-items: center; gap: var(--spacing-xs); min-height: 44px; padding: var(--spacing-sm) var(--spacing-lg); border: 0; border-radius: var(--radius-md); color: white; background: var(--color-primary); cursor: pointer; font-size: var(--font-size-sm); font-weight: 700; }
.save-btn:hover:not(:disabled), .save-btn:focus-visible { background: var(--color-primary-dark); outline: 2px solid var(--color-primary-light); outline-offset: 2px; }
.save-btn:disabled { opacity: .6; cursor: not-allowed; }
.save-btn svg { width: 18px; height: 18px; }
.editor-body { display: flex; flex: 1; flex-direction: column; min-height: 0; }
.editor-meta { display: grid; grid-template-columns: minmax(220px, 1.4fr) minmax(220px, 1fr) minmax(180px, .8fr) auto; align-items: end; gap: var(--spacing-md); padding: var(--spacing-lg) var(--spacing-xl); border-bottom: 1px solid var(--color-border); background: var(--color-card); }
.field { display: flex; flex-direction: column; min-width: 0; }
.field--title { align-self: stretch; justify-content: center; }
.title-input, .meta-input { width: 100%; box-sizing: border-box; border: 1px solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); background: var(--color-bg-secondary); outline: none; font: inherit; }
.title-input { padding: var(--spacing-sm) 0; border-width: 0 0 2px; border-radius: 0; font-family: var(--font-family-display); font-size: var(--font-size-2xl); font-weight: 700; }
.meta-input { min-height: 44px; padding: var(--spacing-sm); font-size: var(--font-size-sm); }
.meta-input--summary { resize: vertical; min-height: 60px; }
.title-input:focus, .meta-input:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(14, 165, 233, .12); }
.pin-field { display: inline-flex; align-items: center; gap: var(--spacing-xs); min-height: 44px; color: var(--color-text-secondary); font-size: var(--font-size-sm); white-space: nowrap; cursor: pointer; }
.pin-field input { width: 18px; height: 18px; accent-color: var(--color-primary); }
.editor-wrapper { flex: 1; min-height: 0; }
.editor-wrapper :deep(.v-md-editor) { height: 100%; border: 0; border-radius: 0; box-shadow: none; background: var(--color-bg-secondary); }
.editor-wrapper :deep(.v-md-editor__toolbar) { background: var(--color-bg-tertiary); border-bottom-color: var(--color-border); }
.editor-wrapper :deep(.v-md-textarea-editor textarea), .editor-wrapper :deep(.github-markdown-body) { color: var(--color-text); background: var(--color-bg-secondary); }
.editor-wrapper :deep(.v-md-editor__preview-wrapper), .editor-wrapper :deep(.v-md-editor--editable .v-md-editor__editor-wrapper) { border-color: var(--color-border); }
.loading-state { display: flex; flex: 1; align-items: center; justify-content: center; gap: var(--spacing-md); color: var(--color-text-secondary); }
.loading-spinner { width: 28px; height: 28px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 1s linear infinite; }
.toast { position: fixed; z-index: 200; bottom: var(--spacing-xl); left: 50%; transform: translateX(-50%); padding: var(--spacing-md) var(--spacing-xl); border-radius: var(--radius-md); color: white; box-shadow: var(--shadow-lg); pointer-events: none; }
.toast.success { background: var(--color-success-dark); }
.toast.error { background: var(--color-error-dark); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .loading-spinner, .save-status--saving .save-status-dot { animation: none; } }
@media (max-width: 960px) { .editor-meta { grid-template-columns: 1fr 1fr; } .field--title { grid-column: 1 / -1; } .pin-field { align-self: center; } }
@media (max-width: 767px) { .note-editor-page { height: calc(100vh - var(--bottom-nav-height) - var(--header-height)); height: calc(100dvh - var(--bottom-nav-height) - var(--header-height)); padding-bottom: var(--safe-area-bottom); } .editor-header { align-items: flex-start; padding: var(--spacing-sm) var(--spacing-md); } .header-actions { flex-direction: column; align-items: flex-end; gap: var(--spacing-xs); } .save-status { font-size: var(--font-size-xs); } .editor-meta { grid-template-columns: 1fr; padding: var(--spacing-md); } .field--title { grid-column: auto; } .pin-field { justify-self: start; } }
</style>
