<!-- frontend/src/views/NotebookFileManage.vue -->
<template>
  <div class="file-manager">
    <!-- Breadcrumb -->
    <div class="fm-toolbar">
      <div class="fm-breadcrumb">
        <button class="breadcrumb-item" @click="navigateTo(null)">
          {{ notebook?.name || '笔记本' }}
        </button>
        <template v-for="crumb in breadcrumbs" :key="crumb.id">
          <span class="breadcrumb-sep">/</span>
          <button class="breadcrumb-item" @click="navigateTo(crumb.id)">
            {{ crumb.name }}
          </button>
        </template>
      </div>
      <div class="fm-actions">
        <button class="action-btn" @click="showCreateFolder = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <line x1="12" y1="11" x2="12" y2="17" />
            <line x1="9" y1="14" x2="15" y2="14" />
          </svg>
          新建文件夹
        </button>
        <button class="action-btn action-btn--primary" @click="showCreateNote = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建笔记
        </button>
      </div>
    </div>

    <!-- Main content area: tree sidebar + content list -->
    <div class="fm-body">
      <!-- Tree sidebar -->
      <aside class="fm-tree" :class="{ 'fm-tree--open': treeOpen }">
        <div class="tree-header">
          <span class="tree-title">目录</span>
          <button class="tree-close" @click="treeOpen = false" aria-label="关闭目录">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div v-if="treeLoading" class="tree-loading">
          <span class="loading-spinner loading-spinner--sm"></span>
        </div>
        <ul v-else class="tree-list">
          <li v-for="node in tree" :key="node.id">
            <TreeItem :node="node" :current-id="currentFolderId" @navigate="navigateTo" />
          </li>
        </ul>
      </aside>

      <!-- Content list -->
      <div class="fm-content">
        <button class="tree-toggle" @click="treeOpen = !treeOpen" aria-label="切换目录">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
        </button>

        <div v-if="loading" class="loading-state">
          <span class="loading-spinner"></span>
        </div>

        <div v-else-if="error" class="error-state">
          <p>{{ error }}</p>
          <button class="retry-btn" @click="fetchChildren">重试</button>
        </div>

        <div v-else-if="children.length === 0" class="empty-state">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <h3>暂无内容</h3>
          <p>点击上方按钮创建文件夹或笔记</p>
        </div>

        <div v-else class="node-list">
          <div
            v-for="node in children"
            :key="node.id"
            class="node-card"
            tabindex="0"
            role="button"
            @click="openNode(node)"
            @keydown.enter="openNode(node)"
          >
            <div class="node-icon" :class="{ 'node-icon--folder': node.type === 'folder' }">
              <svg v-if="node.type === 'folder'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <div class="node-info">
              <h3 class="node-name">{{ node.name }}</h3>
              <p class="node-meta" v-if="node.type === 'note' && node.updated_at">
                {{ formatDate(node.updated_at) }}
                <span v-if="node.word_count"> · {{ node.word_count }} 字</span>
              </p>
              <p class="node-meta" v-else-if="node.type === 'folder'">文件夹</p>
            </div>
            <div class="node-actions">
              <button class="node-action-btn" @click.stop="startRename(node)" title="重命名">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button class="node-action-btn node-action-btn--danger" @click.stop="confirmDelete(node)" title="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Folder Dialog -->
    <Teleport to="body">
      <div v-if="showCreateFolder" class="dialog-overlay" @click.self="showCreateFolder = false">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">新建文件夹</h3>
            <button class="dialog-close" @click="showCreateFolder = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createFolder">
            <div class="form-group">
              <label class="form-label" for="folder-name-input">文件夹名称</label>
              <input id="folder-name-input" ref="folderNameRef" v-model="folderForm.name" type="text" class="form-input" placeholder="我的文件夹" required maxlength="100" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showCreateFolder = false">取消</button>
              <button type="submit" class="btn-primary" :disabled="!folderForm.name.trim()">创建</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Create Note Dialog -->
    <Teleport to="body">
      <div v-if="showCreateNote" class="dialog-overlay" @click.self="showCreateNote = false">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">新建笔记</h3>
            <button class="dialog-close" @click="showCreateNote = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createNote">
            <div class="form-group">
              <label class="form-label" for="note-title-input">笔记标题</label>
              <input id="note-title-input" ref="noteTitleRef" v-model="noteForm.title" type="text" class="form-input" placeholder="我的笔记" required maxlength="200" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showCreateNote = false">取消</button>
              <button type="submit" class="btn-primary" :disabled="!noteForm.title.trim()">创建</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Rename Dialog -->
    <Teleport to="body">
      <div v-if="showRename" class="dialog-overlay" @click.self="showRename = false">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">重命名</h3>
            <button class="dialog-close" @click="showRename = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="doRename">
            <div class="form-group">
              <label class="form-label" for="rename-input">新名称</label>
              <input id="rename-input" ref="renameRef" v-model="renameForm.name" type="text" class="form-input" required maxlength="200" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showRename = false">取消</button>
              <button type="submit" class="btn-primary" :disabled="!renameForm.name.trim()">确认</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { noteService } from '../services/note'
import TreeItem from '../components/TreeItem.vue'

const route = useRoute()
const router = useRouter()
const notebookId = computed(() => route.params.notebookId)

const notebook = ref(null)
const tree = ref([])
const children = ref([])
const currentFolderId = ref(null)
const loading = ref(true)
const treeLoading = ref(true)
const error = ref(null)
const treeOpen = ref(false)

// Dialogs
const showCreateFolder = ref(false)
const showCreateNote = ref(false)
const showRename = ref(false)
const dialogError = ref(null)
const folderForm = ref({ name: '' })
const noteForm = ref({ title: '' })
const renameForm = ref({ name: '', nodeId: null })
const folderNameRef = ref(null)
const noteTitleRef = ref(null)
const renameRef = ref(null)

// Toast
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null

function showToast(message, type = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

// Build breadcrumbs from tree data
const breadcrumbs = computed(() => {
  if (!currentFolderId.value) return []
  const crumbs = []
  const findPath = (nodes, targetId, path) => {
    for (const n of nodes) {
      if (n.id === targetId) return [...path, { id: n.id, name: n.name }]
      if (n.children?.length) {
        const found = findPath(n.children, targetId, [...path, { id: n.id, name: n.name }])
        if (found) return found
      }
    }
    return null
  }
  return findPath(tree.value, currentFolderId.value, []) || []
})

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

async function fetchTree() {
  treeLoading.value = true
  try {
    tree.value = await noteService.getTree(notebookId.value)
  } catch (e) {
    console.error('Failed to load tree:', e)
  } finally {
    treeLoading.value = false
  }
}

async function fetchChildren() {
  loading.value = true
  error.value = null
  try {
    children.value = await noteService.getChildren(notebookId.value, currentFolderId.value)
  } catch (e) {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

async function fetchAll() {
  await Promise.all([fetchTree(), fetchChildren()])
}

function navigateTo(folderId) {
  currentFolderId.value = folderId
  fetchChildren()
}

function openNode(node) {
  if (node.type === 'folder') {
    navigateTo(node.id)
  } else {
    router.push({ name: 'NoteEditor', params: { id: node.id } })
  }
}

async function createFolder() {
  if (!folderForm.value.name.trim()) return
  dialogError.value = null
  try {
    await noteService.createFolder(notebookId.value, {
      name: folderForm.value.name.trim(),
      parent_id: currentFolderId.value,
    })
    showCreateFolder.value = false
    folderForm.value = { name: '' }
    await fetchAll()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建失败，请重试。'
  }
}

async function createNote() {
  if (!noteForm.value.title.trim()) return
  dialogError.value = null
  try {
    const node = await noteService.createNote(notebookId.value, {
      title: noteForm.value.title.trim(),
      parent_id: currentFolderId.value,
    })
    showCreateNote.value = false
    noteForm.value = { title: '' }
    router.push({ name: 'NoteEditor', params: { id: node.id } })
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建失败，请重试。'
  }
}

function startRename(node) {
  renameForm.value = { name: node.name, nodeId: node.id }
  dialogError.value = null
  showRename.value = true
}

async function doRename() {
  if (!renameForm.value.name.trim()) return
  dialogError.value = null
  try {
    await noteService.renameNode(renameForm.value.nodeId, renameForm.value.name.trim())
    showRename.value = false
    await fetchAll()
    showToast('重命名成功')
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '重命名失败。'
  }
}

async function confirmDelete(node) {
  const label = node.type === 'folder' ? '文件夹' : '笔记'
  if (!confirm(`确定要删除${label}「${node.name}」吗？${node.type === 'folder' ? '文件夹内的所有内容将被删除。' : ''}`)) return
  try {
    await noteService.deleteNode(node.id)
    await fetchAll()
    showToast('删除成功')
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

// Auto-focus dialog inputs
watch(showCreateFolder, (open) => {
  if (open) { nextTick(() => folderNameRef.value?.focus()) }
  else { dialogError.value = null }
})
watch(showCreateNote, (open) => {
  if (open) { nextTick(() => noteTitleRef.value?.focus()) }
  else { dialogError.value = null }
})
watch(showRename, (open) => {
  if (open) { nextTick(() => renameRef.value?.select()) }
  else { dialogError.value = null }
})

onMounted(async () => {
  notebook.value = await noteService.getNotebook(notebookId.value)
  await fetchAll()
})
</script>

<style scoped>
.file-manager { display: flex; flex-direction: column; height: 100%; width: 100%; }
.fm-toolbar { display: flex; align-items: center; justify-content: space-between; padding: var(--spacing-md) var(--spacing-xl); border-bottom: 1px solid var(--color-border); flex-shrink: 0; gap: var(--spacing-md); flex-wrap: wrap; }
.fm-breadcrumb { display: flex; align-items: center; gap: var(--spacing-xs); font-size: var(--font-size-sm); min-width: 0; overflow-x: auto; }
.breadcrumb-item { background: none; border: none; cursor: pointer; padding: var(--spacing-xs) var(--spacing-sm); border-radius: var(--radius-sm); color: var(--color-text-secondary); font-size: var(--font-size-sm); font-family: var(--font-family); white-space: nowrap; transition: color 0.15s; }
.breadcrumb-item:hover { color: var(--color-primary); }
.breadcrumb-sep { color: var(--color-text-tertiary); }
.fm-actions { display: flex; gap: var(--spacing-sm); }
.action-btn { display: inline-flex; align-items: center; gap: var(--spacing-xs); padding: var(--spacing-xs) var(--spacing-md); font-size: var(--font-size-sm); font-weight: 500; color: var(--color-text-secondary); background: transparent; border: 1px solid var(--color-border); border-radius: var(--radius-md); cursor: pointer; font-family: var(--font-family); transition: all 0.15s; white-space: nowrap; }
.action-btn:hover { background: var(--color-bg-tertiary); }
.action-btn--primary { color: #fff; background: var(--color-primary); border-color: var(--color-primary); }
.action-btn--primary:hover { background: var(--color-primary-dark); }
.action-btn svg { width: 16px; height: 16px; }
.fm-body { display: flex; flex: 1; min-height: 0; }
.fm-tree { width: 240px; border-right: 1px solid var(--color-border); overflow-y: auto; flex-shrink: 0; padding: var(--spacing-md); }
.tree-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--spacing-md); }
.tree-title { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.tree-close { display: none; background: none; border: none; cursor: pointer; padding: 4px; color: var(--color-text-tertiary); }
.tree-close svg { width: 16px; height: 16px; }
.tree-loading { display: flex; justify-content: center; padding: var(--spacing-lg); }
.tree-list { list-style: none; padding: 0; margin: 0; }
.fm-content { flex: 1; overflow-y: auto; padding: var(--spacing-lg) var(--spacing-xl); min-width: 0; }
.tree-toggle { display: none; background: none; border: none; cursor: pointer; padding: var(--spacing-sm); margin-bottom: var(--spacing-md); color: var(--color-text); border-radius: var(--radius-md); }
.tree-toggle:hover { background: var(--color-bg-tertiary); }
.tree-toggle svg { width: 20px; height: 20px; }
.node-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.node-card { display: flex; align-items: center; gap: var(--spacing-md); padding: var(--spacing-md) var(--spacing-lg); background: var(--color-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s; }
.node-card:hover { border-color: var(--color-primary); box-shadow: var(--shadow-sm); }
.node-icon { width: 40px; height: 40px; border-radius: var(--radius-md); background: var(--color-bg-tertiary); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.node-icon--folder { background: rgba(108, 99, 255, 0.12); }
.node-icon svg { width: 22px; height: 22px; color: var(--color-primary); }
.node-info { flex: 1; min-width: 0; }
.node-name { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text); margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-meta { font-size: var(--font-size-xs); color: var(--color-text-tertiary); margin: var(--spacing-xs) 0 0; }
.node-actions { display: flex; gap: var(--spacing-xs); opacity: 0; transition: opacity 0.15s; }
.node-card:hover .node-actions { opacity: 1; }
.node-action-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; border-radius: var(--radius-md); cursor: pointer; color: var(--color-text-tertiary); transition: background 0.15s, color 0.15s; }
.node-action-btn:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.node-action-btn--danger:hover { color: var(--color-error); }
.node-action-btn svg { width: 16px; height: 16px; }
.loading-state { display: flex; align-items: center; justify-content: center; min-height: 300px; }
.loading-spinner { width: 32px; height: 32px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
.loading-spinner--sm { width: 16px; height: 16px; border-width: 2px; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; gap: var(--spacing-md); color: var(--color-error); font-size: var(--font-size-sm); }
.retry-btn { padding: var(--spacing-xs) var(--spacing-md); font-size: var(--font-size-sm); color: var(--color-primary); background: transparent; border: 1px solid var(--color-primary); border-radius: var(--radius-md); cursor: pointer; font-family: var(--font-family); }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; text-align: center; color: var(--color-text-tertiary); }
.empty-icon { width: 56px; height: 56px; margin-bottom: var(--spacing-md); }
.empty-state h3 { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text); margin: 0 0 var(--spacing-xs); }
.empty-state p { font-size: var(--font-size-sm); margin: 0; }
.dialog-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: var(--spacing-lg); }
.dialog { width: 100%; max-width: 440px; background: var(--color-card); border: 1px solid var(--color-border); border-radius: var(--radius-xl); box-shadow: var(--shadow-xl); overflow: hidden; }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: var(--spacing-lg); border-bottom: 1px solid var(--color-border); }
.dialog-title { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text); margin: 0; }
.dialog-close { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; border-radius: var(--radius-md); cursor: pointer; color: var(--color-text-tertiary); transition: background 0.15s; }
.dialog-close:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.dialog-close svg { width: 18px; height: 18px; }
.dialog-body { padding: var(--spacing-lg); display: flex; flex-direction: column; gap: var(--spacing-md); }
.form-group { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.form-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }
.form-input { width: 100%; padding: var(--spacing-sm) var(--spacing-md); font-size: var(--font-size-sm); font-family: var(--font-family); color: var(--color-text); background: var(--color-bg-secondary); border: 1px solid var(--color-border); border-radius: var(--radius-md); outline: none; transition: border-color 0.15s; box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }
.dialog-error { font-size: var(--font-size-sm); color: var(--color-error); padding: var(--spacing-xs) 0; }
.dialog-actions { display: flex; justify-content: flex-end; gap: var(--spacing-sm); padding-top: var(--spacing-sm); }
.btn-secondary { padding: var(--spacing-sm) var(--spacing-lg); font-size: var(--font-size-sm); font-weight: 500; color: var(--color-text-secondary); background: transparent; border: 1px solid var(--color-border); border-radius: var(--radius-md); cursor: pointer; font-family: var(--font-family); }
.btn-secondary:hover { background: var(--color-bg-tertiary); }
.btn-primary { display: inline-flex; align-items: center; gap: var(--spacing-xs); padding: var(--spacing-sm) var(--spacing-lg); font-size: var(--font-size-sm); font-weight: 600; color: #fff; background: var(--color-primary); border: none; border-radius: var(--radius-md); cursor: pointer; font-family: var(--font-family); }
.btn-primary:hover { background: var(--color-primary-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.toast { position: fixed; bottom: var(--spacing-xl); left: 50%; transform: translateX(-50%); padding: var(--spacing-md) var(--spacing-xl); border-radius: var(--radius-md); font-size: var(--font-size-sm); font-weight: 500; z-index: 200; box-shadow: var(--shadow-lg); pointer-events: none; }
.toast.success { background: #10b981; color: white; }
.toast.error { background: #ef4444; color: white; }
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(20px); }
@media (max-width: 767px) {
  .fm-toolbar { padding: var(--spacing-sm) var(--spacing-md); }
  .fm-actions { width: 100%; }
  .action-btn { flex: 1; justify-content: center; }
  .fm-tree { position: fixed; left: 0; top: 0; bottom: 0; z-index: 100; background: var(--color-card); transform: translateX(-100%); transition: transform 0.3s ease; }
  .fm-tree--open { transform: translateX(0); }
  .tree-close { display: flex; }
  .tree-toggle { display: flex; }
  .fm-content { padding: var(--spacing-md); }
}
</style>
