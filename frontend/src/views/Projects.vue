<template>
  <div class="projects-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">项目</h2>
        <span class="item-count">{{ filteredProjects.length }} 个项目</span>
      </div>
      <button class="btn-create" @click="openCreateDialog">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建项目
      </button>
    </div>

    <div class="filter-tabs">
      <button
        v-for="tab in filterTabs"
        :key="tab.value"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeFilter === tab.value }"
        @click="activeFilter = tab.value"
      >
        <span class="tab-label">{{ tab.label }}</span>
        <span class="tab-count">{{ getCount(tab.value) }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchProjects">重试</button>
    </div>

    <div v-else-if="filteredProjects.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h3 class="empty-title">还没有项目</h3>
      <p class="empty-text">还没有项目，创建第一个吧！</p>
      <button class="btn-create" @click="openCreateDialog">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建项目
      </button>
    </div>

    <div v-else class="projects-grid">
      <div
        v-for="project in filteredProjects"
        :key="project.id"
        class="project-card"
        @click="$router.push(`/projects/${project.id}`)"
      >
        <div class="project-card-color" :style="{ background: project.color || 'var(--color-primary)' }"></div>
        <div class="project-card-body">
          <div class="project-card-top">
            <div class="project-card-info">
              <h3 class="project-card-name">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                </svg>
                {{ project.name }}
              </h3>
            </div>
            <span class="status-badge" :class="'status-badge--' + project.status">
              {{ formatStatus(project.status) }}
            </span>
          </div>

          <div class="project-progress">
            <div class="progress-info">
              <span class="progress-label">进度</span>
              <span class="progress-value">{{ getProgress(project) }}%</span>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: getProgress(project) + '%', background: project.color || 'var(--color-primary)' }"
              ></div>
            </div>
          </div>

          <div class="project-card-footer">
            <span v-if="project.start_date || project.end_date" class="stat-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              {{ formatDate(project.start_date) || '未设定' }} ~ {{ formatDate(project.end_date) || '未设定' }}
            </span>
            <span class="stat-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
              {{ project.completed_tasks || 0 }}/{{ project.total_tasks || 0 }} 任务
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Project Dialog -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog" @keydown.escape="cancelDialog">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" @keydown="trapFocus">
          <div class="dialog-header">
            <h3 id="dialog-title" class="dialog-title">新建项目</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveProject">
            <div class="form-group">
              <label class="form-label" for="project-name">名称</label>
              <input
                id="project-name"
                ref="dialogNameInput"
                v-model="form.name"
                type="text"
                class="form-input"
                placeholder="项目名称"
                required
                maxlength="200"
              />
            </div>
            <div class="form-group">
              <label class="form-label" for="project-desc">描述</label>
              <textarea
                id="project-desc"
                v-model="form.description"
                class="form-textarea"
                placeholder="可选描述..."
                rows="2"
              ></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">颜色</label>
              <div class="color-picker">
                <button
                  v-for="c in presetColors"
                  :key="c"
                  type="button"
                  class="color-dot"
                  :class="{ 'color-dot--active': form.color === c }"
                  :style="{ background: c }"
                  @click="form.color = c"
                ></button>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="project-start">开始日期</label>
                <input id="project-start" v-model="form.start_date" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label" for="project-end">结束日期</label>
                <input id="project-end" v-model="form.end_date" type="date" class="form-input" />
              </div>
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
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

    <!-- Error Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="errorToast" class="error-toast" role="status" aria-live="polite">
          <div class="error-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>{{ errorToast }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { projectService } from '../services/project'
import { useToast } from '../composables/useToast'

const { errorToast, showError } = useToast()

const projects = ref([])
const loading = ref(true)
const error = ref(null)
const activeFilter = ref('all')
const showDialog = ref(false)
const creating = ref(false)
const dialogError = ref(null)
const dialogNameInput = ref(null)

const presetColors = [
  '#6c63ff', '#00d9ff', '#51cf66', '#ff6b6b',
  '#ffd93d', '#ff922b', '#845ef7', '#20c997'
]

const filterTabs = [
  { value: 'all', label: '全部' },
  { value: 'active', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'archived', label: '已归档' }
]

const defaultForm = {
  name: '',
  description: '',
  color: '#6c63ff',
  start_date: '',
  end_date: ''
}

const form = ref({ ...defaultForm })

const filteredProjects = computed(() => {
  if (activeFilter.value === 'all') return projects.value
  return projects.value.filter(p => p.status === activeFilter.value)
})

function getCount(filter) {
  if (filter === 'all') return projects.value.length
  return projects.value.filter(p => p.status === filter).length
}

function formatStatus(status) {
  const map = {
    planning: '规划中',
    active: '进行中',
    completed: '已完成',
    archived: '已归档'
  }
  return map[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function getProgress(project) {
  if (!project.total_tasks || project.total_tasks === 0) return 0
  return Math.round(((project.completed_tasks || 0) / project.total_tasks) * 100)
}

function trapFocus(event) {
  if (event.key !== 'Tab') return
  const dialog = event.currentTarget
  const focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey) {
    if (document.activeElement === first) { event.preventDefault(); last.focus() }
  } else {
    if (document.activeElement === last) { event.preventDefault(); first.focus() }
  }
}

watch(showDialog, (open) => {
  if (open) nextTick(() => dialogNameInput.value?.focus())
})

function openCreateDialog() {
  form.value = { ...defaultForm }
  dialogError.value = null
  showDialog.value = true
}

function cancelDialog() {
  showDialog.value = false
  form.value = { ...defaultForm }
  dialogError.value = null
}

async function fetchProjects() {
  loading.value = true
  error.value = null
  try {
    projects.value = await projectService.getProjects()
  } catch (e) {
    error.value = '加载项目失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function saveProject() {
  if (!form.value.name.trim()) return
  creating.value = true
  dialogError.value = null
  try {
    const data = {
      name: form.value.name.trim(),
      description: form.value.description?.trim() || undefined,
      color: form.value.color
    }
    if (form.value.start_date) data.start_date = form.value.start_date
    if (form.value.end_date) data.end_date = form.value.end_date

    const project = await projectService.createProject(data)
    projects.value.push(project)
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建失败，请重试。'
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.projects-page {
  padding: var(--spacing-xl);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
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

.item-count {
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

.btn-create svg {
  width: 18px;
  height: 18px;
}

/* Filter Tabs */
.filter-tabs {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--font-family);
  transition: color 0.15s ease, border-color 0.15s ease;
  margin-bottom: -1px;
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-count {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

/* Loading / Error / Empty */
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

/* Projects Grid */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-lg);
}

.project-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.project-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.project-card-color {
  height: 4px;
  width: 100%;
}

.project-card-body {
  padding: var(--spacing-lg);
}

.project-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.project-card-info {
  flex: 1;
  min-width: 0;
}

.project-card-name {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  word-break: break-word;
}

.project-card-name svg {
  width: 18px;
  height: 18px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.status-badge {
  font-size: var(--font-size-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.status-badge--planning {
  background: rgba(156, 163, 175, 0.15);
  color: var(--color-text-tertiary);
}

.status-badge--active {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

.status-badge--completed {
  background: rgba(81, 207, 102, 0.15);
  color: var(--color-success);
}

.status-badge--archived {
  background: rgba(156, 163, 175, 0.15);
  color: var(--color-text-tertiary);
}

/* Progress */
.project-progress {
  margin-bottom: var(--spacing-md);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.progress-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.progress-value {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  font-weight: 700;
}

.progress-bar {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

/* Card Footer */
.project-card-footer {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.stat-item svg {
  width: 14px;
  height: 14px;
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
  max-width: 480px;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
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
  min-height: 60px;
}

.color-picker {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.color-dot {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 3px solid transparent;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
  padding: 0;
}

.color-dot:hover {
  transform: scale(1.1);
}

.color-dot--active {
  border-color: var(--color-text);
  transform: scale(1.15);
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

/* Error Toast */
.error-toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 1100;
}

.error-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-error);
  color: #fff;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.error-toast-content svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* Responsive */
@media (max-width: 1199px) {
  .projects-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .projects-page {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .filter-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: var(--spacing-xs);
  }

  .tab-btn {
    white-space: nowrap;
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-xs);
  }

  .projects-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .dialog {
    max-width: 100%;
    margin: var(--spacing-sm);
  }
}
</style>
