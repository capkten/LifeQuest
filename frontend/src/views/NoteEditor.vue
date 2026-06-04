<template>
  <div class="note-editor-page">
    <div class="editor-header">
      <div class="header-left">
        <button class="back-btn" @click="goBack" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M19 12H5" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>
        <h1 class="page-title">{{ isEditing ? '编辑笔记' : '新建笔记' }}</h1>
      </div>
      <div class="header-actions">
        <button class="save-btn" @click="saveNote" :disabled="saving">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else class="editor-body">
      <div class="title-input-wrapper">
        <input
          v-model="noteTitle"
          type="text"
          class="title-input"
          placeholder="请输入笔记标题..."
          maxlength="200"
        />
      </div>
      <div class="editor-wrapper">
        <v-md-editor
          v-model="noteContent"
          height="100%"
          placeholder="请输入笔记内容（支持 Markdown）..."
        />
      </div>
    </div>

    <!-- Toast Messages -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show" class="toast" :class="toast.type">
          {{ toast.message }}
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { noteService } from '../services/note'

const route = useRoute()
const router = useRouter()

const noteTitle = ref('')
const noteContent = ref('')
const loading = ref(false)
const saving = ref(false)
const noteId = ref(null)
const folderId = ref(null)

const toast = ref({ show: false, message: '', type: 'success' })

const isEditing = computed(() => !!noteId.value)

let toastTimer = null

function showToast(message, type = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

async function loadNote() {
  if (!noteId.value) return
  loading.value = true
  try {
    const note = await noteService.getNote(noteId.value)
    noteTitle.value = note.name || ''
    noteContent.value = note.content || ''
    if (note.parent_id) {
      folderId.value = note.parent_id
    }
  } catch (e) {
    console.error('Failed to load note:', e)
    showToast('加载笔记失败', 'error')
  } finally {
    loading.value = false
  }
}

async function saveNote() {
  if (!noteTitle.value.trim()) {
    showToast('请输入笔记标题', 'error')
    return
  }

  saving.value = true
  try {
    if (isEditing.value) {
      await noteService.updateNote(noteId.value, {
        title: noteTitle.value.trim(),
        content: noteContent.value
      })
      showToast('保存成功')
    } else {
      const newNote = await noteService.createNote({
        folder_id: folderId.value,
        title: noteTitle.value.trim(),
        content: noteContent.value
      })
      noteId.value = newNote.id
      // Update URL to edit mode without triggering a full reload
      router.replace({ name: 'NoteEditor', params: { id: newNote.id } })
      showToast('创建成功')
    }
  } catch (e) {
    console.error('Failed to save note:', e)
    showToast('保存失败，请重试', 'error')
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/notes')
}

onMounted(() => {
  if (route.name === 'NoteEditor' && route.params.id) {
    noteId.value = route.params.id
    loadNote()
  } else if (route.name === 'NewNote' && route.params.folderId) {
    folderId.value = route.params.folderId
  }
})
</script>

<style scoped>
.note-editor-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  width: 100%;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  background: var(--color-card);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.back-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  color: var(--color-text);
  transition: background 0.2s;
}

.back-btn:hover {
  background: var(--color-bg-secondary);
}

.back-btn svg {
  width: 24px;
  height: 24px;
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.save-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: background 0.2s;
}

.save-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-btn svg {
  width: 18px;
  height: 18px;
}

.editor-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.title-input-wrapper {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.title-input {
  width: 100%;
  padding: var(--spacing-sm) 0;
  border: none;
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--color-text);
  background: transparent;
  outline: none;
}

.title-input::placeholder {
  color: var(--color-text-tertiary);
}

.editor-wrapper {
  flex: 1;
  min-height: 0;
}

.editor-wrapper :deep(.v-md-editor) {
  box-shadow: none;
  border: none;
  border-radius: 0;
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.editor-wrapper :deep(.v-md-editor__toolbar) {
  background-color: var(--color-bg-tertiary);
  border-bottom-color: var(--color-border);
}

.editor-wrapper :deep(.v-md-editor__toolbar-item) {
  color: var(--color-text-secondary);
}

.editor-wrapper :deep(.v-md-editor__toolbar-item:hover) {
  background-color: var(--color-bg-secondary);
}

.editor-wrapper :deep(.v-md-textarea-editor textarea) {
  color: var(--color-text);
  background-color: var(--color-bg-secondary);
}

.editor-wrapper :deep(.v-md-editor__preview-wrapper) {
  border-left-color: var(--color-border);
}

.editor-wrapper :deep(.github-markdown-body) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.editor-wrapper :deep(.github-markdown-body a) {
  color: var(--color-primary);
}

.editor-wrapper :deep(.github-markdown-body code) {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text);
}

.editor-wrapper :deep(.github-markdown-body pre) {
  background-color: var(--color-bg-tertiary);
}

.editor-wrapper :deep(.github-markdown-body pre code) {
  color: var(--color-text);
}

.editor-wrapper :deep(.github-markdown-body blockquote) {
  color: var(--color-text-secondary);
  border-left-color: var(--color-border);
}

.editor-wrapper :deep(.github-markdown-body h1),
.editor-wrapper :deep(.github-markdown-body h2) {
  border-bottom-color: var(--color-border);
}

.editor-wrapper :deep(.github-markdown-body hr) {
  background-color: var(--color-border);
}

.editor-wrapper :deep(.github-markdown-body table th),
.editor-wrapper :deep(.github-markdown-body table td) {
  border-color: var(--color-border);
}

.editor-wrapper :deep(.github-markdown-body table tr) {
  background-color: var(--color-bg-secondary);
  border-top-color: var(--color-border);
}

.editor-wrapper :deep(.github-markdown-body table tr:nth-child(2n)) {
  background-color: var(--color-bg-tertiary);
}

.editor-wrapper :deep(.v-md-editor--editable .v-md-editor__editor-wrapper) {
  border-right-color: var(--color-border);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-3xl) var(--spacing-xl);
  flex: 1;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-lg);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Toast */
.toast {
  position: fixed;
  bottom: var(--spacing-xl);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--spacing-md) var(--spacing-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  z-index: 200;
  box-shadow: var(--shadow-lg);
  pointer-events: none;
}

.toast.success {
  background: #10b981;
  color: white;
}

.toast.error {
  background: #ef4444;
  color: white;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

@media (max-width: 767px) {
  .note-editor-page {
    height: calc(100vh - 64px - 60px);
  }

  .editor-header {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .page-title {
    font-size: var(--font-size-lg);
  }

  .title-input-wrapper {
    padding: var(--spacing-md);
  }

  .title-input {
    font-size: var(--font-size-xl);
  }
}
</style>
