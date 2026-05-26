<template>
  <div class="folder-detail-page">
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.back()" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M19 12H5" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>
        <div>
          <h1 class="page-title">{{ folderName || '文件夹' }}</h1>
        </div>
      </div>
      <button class="create-btn" @click="showCreateNote = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建笔记
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="error" class="error-state">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="fetchData">重试</button>
    </div>

    <div v-else-if="notes.length === 0" class="empty-state">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
      <h3 class="empty-title">暂无笔记</h3>
      <p class="empty-text">点击上方按钮创建第一篇笔记</p>
    </div>

    <div v-else class="notes-list">
      <div
        v-for="note in notes"
        :key="note.id"
        class="note-card"
        tabindex="0"
        role="button"
        @click="openNote(note)"
        @keydown.enter="openNote(note)"
      >
        <div class="note-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
        <div class="note-info">
          <h3 class="note-title">{{ note.title }}</h3>
          <p class="note-meta" v-if="note.updated_at">{{ formatDate(note.updated_at) }}</p>
        </div>
        <button
          class="delete-btn"
          @click.stop="deleteNote(note)"
          aria-label="删除笔记"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Create Note Dialog -->
    <Teleport to="body">
      <div v-if="showCreateNote" class="dialog-overlay" @click.self="showCreateNote = false">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="create-note-title">
          <div class="dialog-header">
            <h3 id="create-note-title" class="dialog-title">新建笔记</h3>
            <button class="dialog-close" @click="showCreateNote = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createNote">
            <div class="form-group">
              <label class="form-label" for="note-title">笔记标题</label>
              <input
                id="note-title"
                v-model="noteForm.title"
                type="text"
                class="form-input"
                placeholder="我的笔记"
                required
                maxlength="200"
              />
            </div>
            <div class="dialog-actions">
              <button type="button" class="cancel-btn" @click="showCreateNote = false">取消</button>
              <button type="submit" class="confirm-btn" :disabled="!noteForm.title">创建</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { noteService } from '../services/note'

const route = useRoute()
const router = useRouter()
const folderId = route.params.id

const folderName = ref('')
const notes = ref([])
const loading = ref(true)
const error = ref(null)
const showCreateNote = ref(false)
const noteForm = ref({ title: '' })

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const notesRes = await noteService.getNotesByFolder(folderId)
    notes.value = notesRes
    // Try to get folder name from the first note or use a default
    if (notesRes.length > 0 && notesRes[0].folder_name) {
      folderName.value = notesRes[0].folder_name
    } else {
      folderName.value = '文件夹'
    }
  } catch (e) {
    error.value = '加载失败，请重试'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function createNote() {
  if (!noteForm.value.title) return
  try {
    const newNote = await noteService.createNote({
      folder_id: folderId,
      title: noteForm.value.title
    })
    showCreateNote.value = false
    noteForm.value = { title: '' }
    // Navigate to the note editor (Task 6)
    router.push(`/notes/editor/${newNote.id}`)
  } catch (e) {
    console.error(e)
  }
}

async function deleteNote(note) {
  if (!confirm(`确定要删除笔记「${note.title}」吗？`)) return
  try {
    await noteService.deleteNote(note.id)
    await fetchData()
  } catch (e) {
    console.error(e)
  }
}

function openNote(note) {
  router.push(`/notes/editor/${note.id}`)
}

onMounted(fetchData)
</script>

<style scoped>
.folder-detail-page {
  padding: var(--spacing-xl);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-xl);
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
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.create-btn {
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

.create-btn:hover {
  background: var(--color-primary-dark);
}

.create-btn svg {
  width: 18px;
  height: 18px;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.note-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.note-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.note-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.note-icon {
  width: 48px;
  height: 48px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.note-icon svg {
  width: 28px;
  height: 28px;
  color: var(--color-primary);
}

.note-info {
  flex: 1;
  min-width: 0;
}

.note-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.note-meta {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all 0.2s;
  opacity: 0;
}

.note-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--color-error);
  background: var(--color-bg-secondary);
}

.delete-btn svg {
  width: 18px;
  height: 18px;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-3xl) var(--spacing-xl);
  text-align: center;
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

.error-state span {
  color: var(--color-error);
  margin-bottom: var(--spacing-lg);
}

.retry-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-lg);
}

.empty-title {
  font-size: var(--font-size-lg);
  color: var(--color-text);
  margin: 0 0 var(--spacing-sm);
}

.empty-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

/* Dialog styles */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: var(--spacing-lg);
}

.dialog {
  background: var(--color-card);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 440px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-xl);
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.dialog-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
  color: var(--color-text-secondary);
}

.dialog-close svg {
  width: 20px;
  height: 20px;
}

.dialog-body {
  padding: var(--spacing-xl);
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: var(--spacing-sm);
}

.form-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.dialog-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding-top: var(--spacing-lg);
}

.cancel-btn,
.confirm-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: var(--color-bg-secondary);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.cancel-btn:hover {
  background: var(--color-border);
}

.confirm-btn {
  background: var(--color-primary);
  color: white;
  border: none;
}

.confirm-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 767px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .create-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
