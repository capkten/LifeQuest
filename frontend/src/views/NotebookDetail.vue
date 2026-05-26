<template>
  <div class="notebook-detail-page">
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.push('/notes')" aria-label="返回笔记列表">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M19 12H5" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>
        <div>
          <h1 class="page-title">{{ notebook?.name || '笔记本' }}</h1>
          <p class="page-description">{{ notebook?.description || '' }}</p>
        </div>
      </div>
      <button class="create-btn" @click="showCreateFolder = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建文件夹
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

    <div v-else-if="folders.length === 0" class="empty-state">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
      <h3 class="empty-title">暂无文件夹</h3>
      <p class="empty-text">点击上方按钮创建第一个文件夹</p>
    </div>

    <div v-else class="folders-grid">
      <div
        v-for="folder in folders"
        :key="folder.id"
        class="folder-card"
        tabindex="0"
        role="button"
        @click="openFolder(folder)"
        @keydown.enter="openFolder(folder)"
      >
        <div class="folder-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div class="folder-info">
          <h3 class="folder-name">{{ folder.name }}</h3>
          <p class="folder-count">{{ folder.note_count || 0 }} 篇笔记</p>
        </div>
      </div>
    </div>

    <!-- Create Folder Dialog -->
    <Teleport to="body">
      <div v-if="showCreateFolder" class="dialog-overlay" @click.self="showCreateFolder = false">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="create-folder-title">
          <div class="dialog-header">
            <h3 id="create-folder-title" class="dialog-title">新建文件夹</h3>
            <button class="dialog-close" @click="showCreateFolder = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createFolder">
            <div class="form-group">
              <label class="form-label" for="folder-name">文件夹名称</label>
              <input
                id="folder-name"
                v-model="folderForm.name"
                type="text"
                class="form-input"
                placeholder="我的文件夹"
                required
                maxlength="100"
              />
            </div>
            <div class="dialog-actions">
              <button type="button" class="cancel-btn" @click="showCreateFolder = false">取消</button>
              <button type="submit" class="confirm-btn" :disabled="!folderForm.name">创建</button>
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
const notebookId = route.params.id

const notebook = ref(null)
const folders = ref([])
const loading = ref(true)
const error = ref(null)
const showCreateFolder = ref(false)
const folderForm = ref({ name: '' })

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [notebookRes, foldersRes] = await Promise.all([
      noteService.getNotebook(notebookId),
      noteService.getFolders(notebookId)
    ])
    notebook.value = notebookRes
    folders.value = foldersRes
  } catch (e) {
    error.value = '加载失败，请重试'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function createFolder() {
  if (!folderForm.value.name) return
  try {
    await noteService.createFolder({
      notebook_id: notebookId,
      name: folderForm.value.name
    })
    showCreateFolder.value = false
    folderForm.value = { name: '' }
    await fetchData()
  } catch (e) {
    console.error(e)
  }
}

function openFolder(folder) {
  router.push(`/notes/folder/${folder.id}`)
}

onMounted(fetchData)
</script>

<style scoped>
.notebook-detail-page {
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

.page-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: var(--spacing-xs) 0 0;
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

.folders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--spacing-lg);
}

.folder-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.folder-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.folder-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.folder-icon {
  width: 48px;
  height: 48px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.folder-icon svg {
  width: 28px;
  height: 28px;
  color: var(--color-primary);
}

.folder-info {
  flex: 1;
  min-width: 0;
}

.folder-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.folder-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
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

  .folders-grid {
    grid-template-columns: 1fr;
  }
}
</style>
