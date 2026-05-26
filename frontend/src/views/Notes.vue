<template>
  <div class="notes-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">笔记本</h2>
        <span class="notebook-count">{{ notebooks.length }} 个笔记本</span>
      </div>
      <button class="btn-create" @click="showDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建笔记本
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchNotebooks">重试</button>
    </div>

    <div v-else-if="notebooks.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      </div>
      <h3 class="empty-title">暂无笔记本</h3>
      <p class="empty-text">创建你的第一个笔记本，开始整理笔记吧。</p>
      <button class="btn-create" @click="showDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Create Notebook
      </button>
    </div>

    <div v-else class="notebook-grid">
      <div
        v-for="notebook in notebooks"
        :key="notebook.id"
        class="notebook-card"
        tabindex="0"
        role="button"
        @click="openNotebook(notebook)"
        @keydown.enter="openNotebook(notebook)"
      >
        <div class="notebook-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <div class="notebook-info">
          <h3 class="notebook-name">{{ notebook.name }}</h3>
          <p class="notebook-description">{{ notebook.description || '暂无描述' }}</p>
        </div>
      </div>
    </div>

    <!-- Create Notebook Dialog -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div
          class="dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="dialog-title"
          @keydown="trapFocus"
        >
          <div class="dialog-header">
            <h3 id="dialog-title" class="dialog-title">新建笔记本</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createNotebook">
            <div class="form-group">
              <label class="form-label" for="notebook-name">名称</label>
              <input
                id="notebook-name"
                ref="dialogNameInput"
                v-model="form.name"
                type="text"
                class="form-input"
                placeholder="我的笔记本"
                required
                maxlength="100"
                :aria-describedby="dialogError ? 'dialog-error-msg' : undefined"
              />
            </div>
            <div class="form-group">
              <label class="form-label" for="notebook-description">描述</label>
              <textarea
                id="notebook-description"
                v-model="form.description"
                class="form-textarea"
                placeholder="简短描述..."
                rows="3"
                maxlength="500"
              ></textarea>
            </div>
            <div v-if="dialogError" id="dialog-error-msg" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="creating || !form.name.trim()">
                <span v-if="creating" class="loading-spinner loading-spinner--sm"></span>
                {{ creating ? '创建中...' : '创建' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { noteService } from '../services/note'

const notebooks = ref([])
const loading = ref(true)
const error = ref(null)

const showDialog = ref(false)
const creating = ref(false)
const dialogError = ref(null)
const form = ref({ name: '', description: '' })
const dialogNameInput = ref(null)

// Auto-focus first input when dialog opens
watch(showDialog, (open) => {
  if (open) {
    nextTick(() => {
      dialogNameInput.value?.focus()
    })
  }
})

function openNotebook(notebook) {
  // TODO: navigate to notebook contents page
  console.log('Open notebook:', notebook.id)
}

function trapFocus(event) {
  if (event.key !== 'Tab') return
  const dialog = event.currentTarget
  const focusable = dialog.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey) {
    if (document.activeElement === first) {
      event.preventDefault()
      last.focus()
    }
  } else {
    if (document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }
}

async function fetchNotebooks() {
  loading.value = true
  error.value = null
  try {
    notebooks.value = await noteService.getNotebooks()
  } catch (e) {
    error.value = '加载笔记本失败，请重试。'
  } finally {
    loading.value = false
  }
}

function cancelDialog() {
  showDialog.value = false
  form.value = { name: '', description: '' }
  dialogError.value = null
}

async function createNotebook() {
  if (!form.value.name.trim()) return
  creating.value = true
  dialogError.value = null
  try {
    const notebook = await noteService.createNotebook({
      name: form.value.name.trim(),
      description: form.value.description.trim() || null
    })
    notebooks.value.push(notebook)
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建笔记本失败，请重试。'
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  fetchNotebooks()
})
</script>

<style scoped>
.notes-page {
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
  align-items: baseline;
  gap: var(--spacing-md);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.notebook-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.btn-create {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-create:hover {
  background: var(--color-primary-dark);
}

.btn-create:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-create svg {
  width: 18px;
  height: 18px;
}

/* Loading State */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--spacing-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-xl);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-lg);
}

.empty-icon svg {
  width: 36px;
  height: 36px;
  color: var(--color-text-tertiary);
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-sm);
}

.empty-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-xl);
  max-width: 320px;
}

/* Notebook Grid */
.notebook-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--spacing-lg);
}

.notebook-card {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.notebook-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.notebook-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  background: rgba(108, 99, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.notebook-icon svg {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}

.notebook-info {
  min-width: 0;
  flex: 1;
}

.notebook-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notebook-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.dialog {
  width: 100%;
  max-width: 440px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.dialog-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: background 0.15s ease;
}

.dialog-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.dialog-close svg {
  width: 18px;
  height: 18px;
}

.dialog-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.15s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  border-color: var(--color-primary);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--color-text-tertiary);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.dialog-error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
  padding: var(--spacing-xs) 0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-sm);
}

.btn-secondary {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-secondary:hover {
  background: var(--color-bg-tertiary);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 1199px) {
  .notes-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .notes-page {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .notebook-grid {
    grid-template-columns: 1fr;
  }

  .dialog {
    max-width: 100%;
    margin: var(--spacing-sm);
  }

  .dialog-body {
    padding: var(--spacing-md);
  }
}
</style>
