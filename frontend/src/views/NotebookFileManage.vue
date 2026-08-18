<template>
  <div class="workspace-shell">
    <header class="workspace-header">
      <div class="workspace-heading">
        <button
          type="button"
          class="icon-button mobile-only"
          aria-label="打开笔记目录"
          aria-controls="notes-directory-panel"
          :aria-expanded="treeOpen"
          @click="treeOpen = true"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div>
          <p class="workspace-kicker">笔记工作区</p>
          <h1 class="workspace-title">{{ notebook?.name || '笔记本' }}</h1>
          <p class="workspace-subtitle">{{ contextLabel }}</p>
        </div>
      </div>

      <div class="workspace-actions">
        <button type="button" class="button button--quiet" @click="openCreateFolder()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <path d="M12 11v6M9 14h6" />
          </svg>
          <span>新建文件夹</span>
        </button>
        <button type="button" class="button button--primary" @click="openCreateNote()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6M12 11v6M9 14h6" />
          </svg>
          <span>新建笔记</span>
        </button>
      </div>
    </header>

    <div class="workspace-layout">
      <div v-if="treeOpen" class="workspace-overlay" aria-hidden="true" @click="treeOpen = false"></div>

      <aside id="notes-directory-panel" class="directory-panel" :class="{ 'directory-panel--open': treeOpen }" aria-label="笔记目录">
        <div class="directory-header">
          <div>
            <p class="panel-kicker">目录</p>
            <h2 class="panel-title">{{ notebook?.name || '笔记本目录' }}</h2>
          </div>
          <button
            type="button"
            class="icon-button mobile-only"
            aria-label="关闭笔记目录"
            @click="treeOpen = false"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>

        <div v-if="workspaceLoading" class="directory-state" aria-live="polite">
          <span class="spinner" aria-hidden="true"></span>
          <span>正在加载目录…</span>
        </div>
        <div v-else-if="workspaceError" class="directory-state directory-state--error" role="alert">
          <p>目录加载失败</p>
          <button type="button" class="text-button" @click="loadWorkspace">重试</button>
        </div>
        <NoteTree
          v-else
          :nodes="tree"
          :selected-id="selectedNoteId"
          :current-folder-id="currentFolderId"
          :expanded-ids="expandedIds"
          label="笔记目录"
          empty-label="还没有笔记内容"
          @select="handleSelect"
          @toggle="toggleFolder"
          @create-folder="handleCreateFolderRequest"
          @create-note="handleCreateNoteRequest"
          @rename="openRename"
          @move="openMove"
          @delete="handleDelete"
        />
      </aside>

      <main class="workspace-content">
        <div class="content-toolbar">
          <button type="button" class="toolbar-button mobile-only" aria-controls="notes-directory-panel" :aria-expanded="treeOpen" @click="treeOpen = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <span>目录</span>
          </button>
          <nav class="breadcrumbs" aria-label="当前位置">
            <button type="button" class="breadcrumb-button" :class="{ 'breadcrumb-button--active': !currentFolderId }" @click="goToRoot">
              {{ notebook?.name || '笔记本' }}
            </button>
            <template v-for="crumb in breadcrumbs" :key="crumb.id">
              <span class="breadcrumb-separator" aria-hidden="true">/</span>
              <button
                type="button"
                class="breadcrumb-button"
                :class="{ 'breadcrumb-button--active': String(crumb.id) === String(currentFolderId) }"
                @click="goToFolder(crumb.id)"
              >
                {{ crumb.name }}
              </button>
            </template>
          </nav>
        </div>

        <div v-if="workspaceLoading" class="content-state" aria-live="polite">
          <span class="spinner spinner--large" aria-hidden="true"></span>
          <p>正在准备你的工作区…</p>
        </div>
        <div v-else-if="workspaceError" class="content-state content-state--error" role="alert">
          <div class="state-icon state-icon--error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5M12 16h.01" />
            </svg>
          </div>
          <h2>工作区暂时无法打开</h2>
          <p>{{ workspaceError }}</p>
          <button type="button" class="button button--primary" @click="loadWorkspace">重新加载</button>
        </div>
        <template v-else>
          <NoteViewer
            v-if="selectedNode"
            :note-id="selectedNode.id"
            :note="viewerNote"
            :loading="viewerLoading"
            :error="viewerError"
            @edit="editViewer"
            @toggle-pin="toggleViewerPin"
            @move="openMove"
            @delete="handleDelete"
            @retry="retryViewer"
          />
          <article v-else-if="false" class="selection-card">
            <div class="selection-icon selection-icon--note">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6M8 13h8M8 17h5" />
              </svg>
            </div>
            <div class="selection-copy">
              <p class="selection-eyebrow">{{ routeModeLabel }}</p>
              <h2>{{ selectedNode.name }}</h2>
              <p>目录已保持打开。阅读器和编辑器将在后续任务中接入这里。</p>
              <div class="selection-links">
                <router-link class="button button--primary" :to="{ name: 'NotebookWorkspaceView', params: { notebookId, noteId: selectedNode.id } }">
                  打开阅读视图
                </router-link>
                <router-link class="button button--quiet" :to="{ name: 'NotebookWorkspaceEdit', params: { notebookId, noteId: selectedNode.id } }">
                  打开编辑视图
                </router-link>
                <router-link class="context-link" :to="{ name: 'NoteEditor', params: { id: selectedNode.id } }">
                  使用旧版编辑器
                </router-link>
              </div>
            </div>
          </article>

          <article v-else-if="isNewNoteRoute" class="selection-card selection-card--new">
            <div class="selection-icon selection-icon--accent">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6M12 11v6M9 14h6" />
              </svg>
            </div>
            <div class="selection-copy">
              <p class="selection-eyebrow">新建笔记</p>
              <h2>从当前目录开始</h2>
              <p>新笔记编辑器将在任务 5 接入。你可以先选择保存位置，然后继续创建。</p>
              <button type="button" class="button button--primary" @click="openCreateNote()">新建笔记</button>
            </div>
          </article>

          <article v-else class="selection-card selection-card--empty">
            <div class="selection-icon selection-icon--folder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <div class="selection-copy">
              <p class="selection-eyebrow">{{ currentFolderId ? '当前文件夹' : '工作区概览' }}</p>
              <h2>{{ currentFolderName }}</h2>
              <p>{{ currentFolderId ? '在这里快速创建内容，目录会保留你的展开状态。' : '从左侧目录选择笔记，或创建一个新的文件夹和笔记。' }}</p>
              <div class="selection-links">
                <button type="button" class="button button--primary" @click="openCreateNote()">新建笔记</button>
                <button type="button" class="button button--quiet" @click="openCreateFolder()">新建文件夹</button>
              </div>
            </div>
          </article>
        </template>
      </main>
    </div>

    <Teleport to="body">
      <div v-if="dialogMode" class="dialog-overlay" @click.self="closeDialog">
        <div class="dialog" role="dialog" aria-modal="true" :aria-labelledby="dialogTitleId" tabindex="-1" @keydown.esc="closeDialog">
          <div class="dialog-header">
            <div>
              <p class="dialog-kicker">工作区操作</p>
              <h2 :id="dialogTitleId" class="dialog-title">{{ dialogTitle }}</h2>
            </div>
            <button type="button" class="icon-button" aria-label="关闭对话框" @click="closeDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="m6 6 12 12M18 6 6 18" />
              </svg>
            </button>
          </div>

          <form v-if="dialogMode === 'folder'" class="dialog-body" @submit.prevent="submitCreateFolder">
            <label class="form-label" for="workspace-folder-name">文件夹名称</label>
            <input id="workspace-folder-name" ref="dialogInput" v-model="folderForm.name" class="form-input" type="text" maxlength="100" placeholder="例如：项目资料" required />
            <p v-if="dialogError" class="form-error" role="alert">{{ dialogError }}</p>
            <div class="dialog-actions">
              <button type="button" class="button button--quiet" @click="closeDialog">取消</button>
              <button type="submit" class="button button--primary" :disabled="!folderForm.name.trim()">创建文件夹</button>
            </div>
          </form>

          <form v-else-if="dialogMode === 'note'" class="dialog-body" @submit.prevent="submitCreateNote">
            <label class="form-label" for="workspace-note-title">笔记标题</label>
            <input id="workspace-note-title" ref="dialogInput" v-model="noteForm.title" class="form-input" type="text" maxlength="200" placeholder="例如：本周计划" required />
            <p v-if="dialogError" class="form-error" role="alert">{{ dialogError }}</p>
            <div class="dialog-actions">
              <button type="button" class="button button--quiet" @click="closeDialog">取消</button>
              <button type="submit" class="button button--primary" :disabled="!noteForm.title.trim()">创建笔记</button>
            </div>
          </form>

          <form v-else-if="dialogMode === 'rename'" class="dialog-body" @submit.prevent="submitRename">
            <label class="form-label" for="workspace-rename">新名称</label>
            <input id="workspace-rename" ref="dialogInput" v-model="renameForm.name" class="form-input" type="text" maxlength="200" required />
            <p v-if="dialogError" class="form-error" role="alert">{{ dialogError }}</p>
            <div class="dialog-actions">
              <button type="button" class="button button--quiet" @click="closeDialog">取消</button>
              <button type="submit" class="button button--primary" :disabled="!renameForm.name.trim()">保存名称</button>
            </div>
          </form>

          <form v-else class="dialog-body" @submit.prevent="submitMove">
            <label class="form-label" for="workspace-move">移动到</label>
            <select id="workspace-move" v-model="moveForm.parentId" class="form-input">
              <option :value="null">笔记本根目录</option>
              <option v-for="folder in folderOptions" :key="folder.id" :value="folder.id" :disabled="String(folder.id) === String(moveForm.nodeId)">
                {{ folder.label }}
              </option>
            </select>
            <p v-if="dialogError" class="form-error" role="alert">{{ dialogError }}</p>
            <div class="dialog-actions">
              <button type="button" class="button button--quiet" @click="closeDialog">取消</button>
              <button type="submit" class="button button--primary">移动</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show" class="workspace-toast" :class="`workspace-toast--${toast.type}`" role="status">{{ toast.message }}</div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NoteTree from '../components/notes/NoteTree.vue'
import NoteViewer from '../components/notes/NoteViewer.vue'
import { useNoteWorkspace } from '../composables/useNoteWorkspace'
import { noteService } from '../services/note'
import { getErrorMessage } from '../utils/errorMessage'

const route = useRoute()
const router = useRouter()
const notebookId = computed(() => route.params.notebookId)
const workspace = useNoteWorkspace(notebookId)

const {
  tree,
  selectedNoteId,
  currentFolderId,
  expandedIds,
  loading,
  loadTree,
  selectNote,
  toggleFolder,
  createFolder,
  createNote,
  renameNode,
  moveNode,
  deleteNode,
} = workspace

const notebook = ref(null)
const notebookError = ref(null)
const treeOpen = ref(false)
const dialogMode = ref(null)
const dialogError = ref(null)
const dialogInput = ref(null)
const folderForm = ref({ name: '', parentId: null })
const noteForm = ref({ title: '', parentId: null })
const renameForm = ref({ name: '', nodeId: null })
const moveForm = ref({ nodeId: null, parentId: null })
const dialogTrigger = ref(null)
const toast = ref({ show: false, message: '', type: 'success' })
const viewerNote = ref(null)
const viewerLoading = ref(false)
const viewerError = ref(null)
const openedViewerNotes = new Set()
let toastTimer = null
let loadRequest = 0

const workspaceLoading = computed(() => loading.value || !notebook.value && !notebookError.value)
const workspaceError = computed(() => notebookError.value)
const isNewNoteRoute = computed(() => route.name === 'NewNoteInWorkspace')
const routeModeLabel = computed(() => route.name === 'NotebookWorkspaceEdit' ? '编辑上下文' : '已选择笔记')

function findNode(nodes, nodeId) {
  for (const node of nodes || []) {
    if (String(node.id) === String(nodeId)) return node
    const nested = findNode(node.children, nodeId)
    if (nested) return nested
  }
  return null
}

function getBreadcrumbs(nodes, targetId, parents = []) {
  for (const node of nodes || []) {
    if (String(node.id) === String(targetId)) return [...parents, { id: node.id, name: node.name }]
    const nested = getBreadcrumbs(node.children, targetId, [...parents, { id: node.id, name: node.name }])
    if (nested) return nested
  }
  return []
}

function getFolderOptions(nodes, depth = 0, result = []) {
  for (const node of nodes || []) {
    if (node.type !== 'folder') continue
    result.push({ id: node.id, label: `${'　'.repeat(depth)}${node.name}` })
    getFolderOptions(node.children, depth + 1, result)
  }
  return result
}

const selectedNode = computed(() => selectedNoteId.value ? findNode(tree.value, selectedNoteId.value) : null)
const breadcrumbs = computed(() => currentFolderId.value ? getBreadcrumbs(tree.value, currentFolderId.value) : [])
const folderOptions = computed(() => getFolderOptions(tree.value))
const currentFolderName = computed(() => {
  if (!currentFolderId.value) return '选择一个笔记开始'
  return findNode(tree.value, currentFolderId.value)?.name || '当前文件夹'
})
const contextLabel = computed(() => {
  if (selectedNode.value) return `正在查看 · ${selectedNode.value.name}`
  if (currentFolderId.value) return `当前位置 · ${currentFolderName.value}`
  return '目录和内容会一直保持在身边'
})
const dialogTitle = computed(() => ({
  folder: '新建文件夹',
  note: '新建笔记',
  rename: '重命名节点',
  move: '移动节点',
}[dialogMode.value] || '工作区操作'))
const dialogTitleId = computed(() => `workspace-dialog-${dialogMode.value || 'default'}`)

function showToast(message, type = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 2800)
}

async function loadWorkspace() {
  const requestId = ++loadRequest
  notebookError.value = null
  notebook.value = null
  try {
    const [nextNotebook] = await Promise.all([
      noteService.getNotebook(notebookId.value),
      loadTree({ preserveExpansion: true }),
    ])
    if (requestId !== loadRequest) return
    notebook.value = nextNotebook
    syncRouteSelection()
  } catch (cause) {
    if (requestId === loadRequest) notebookError.value = getErrorMessage(cause)
  }
}

function syncRouteSelection() {
  const routeNoteId = route.params.noteId
  if (!routeNoteId) {
    selectedNoteId.value = null
    viewerNote.value = null
    return
  }
  const node = selectNote(routeNoteId)
  if (!node || node.type !== 'note') {
    router.replace({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } })
    return
  }
  loadViewer(routeNoteId)
}

async function loadViewer(noteId) {
  viewerLoading.value = true
  viewerError.value = null
  try {
    let lastError
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        viewerNote.value = await noteService.getNote(noteId)
        lastError = null
        break
      } catch (cause) {
        lastError = cause
        if (cause.response?.status !== 404 || attempt === 2) throw cause
        await new Promise(resolve => setTimeout(resolve, 200 * (attempt + 1)))
      }
    }
    if (lastError) throw lastError
    if (!openedViewerNotes.has(String(noteId))) {
      openedViewerNotes.add(String(noteId))
      try {
        await noteService.markNoteOpened(noteId)
      } catch {
        // Opening metadata is best-effort; it must not hide successfully loaded content.
      }
    }
  } catch (cause) {
    viewerNote.value = null
    viewerError.value = getErrorMessage(cause)
  } finally {
    viewerLoading.value = false
  }
}

function retryViewer() { if (route.params.noteId) loadViewer(route.params.noteId) }
function editViewer() {
  if (selectedNode.value) router.push({ name: 'NotebookWorkspaceEdit', params: { notebookId: notebookId.value, noteId: selectedNode.value.id } })
}

async function toggleViewerPin() {
  if (!viewerNote.value) return
  try {
    viewerNote.value = await noteService.updateNote(viewerNote.value.id, { is_pinned: !viewerNote.value.is_pinned })
    showToast(viewerNote.value.is_pinned ? '已置顶' : '已取消置顶')
  } catch (cause) {
    showToast(getErrorMessage(cause), 'error')
  }
}

function goToRoot() {
  selectedNoteId.value = null
  currentFolderId.value = null
  router.replace({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } })
}

function goToFolder(folderId) {
  selectedNoteId.value = null
  currentFolderId.value = folderId
  const folder = findNode(tree.value, folderId)
  if (folder) selectNote(folder)
  router.replace({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } })
}

function handleSelect(node) {
  const selected = selectNote(node)
  if (!selected) return
  treeOpen.value = false
  if (selected.type === 'folder') {
    selectedNoteId.value = null
    router.replace({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } })
    return
  }
  router.push({ name: 'NotebookWorkspaceView', params: { notebookId: notebookId.value, noteId: selected.id } })
}

function handleCreateFolderRequest(payload = {}) {
  openCreateFolder(payload.parentId ?? currentFolderId.value)
}

function handleCreateNoteRequest(payload = {}) {
  openCreateNote(payload.parentId ?? currentFolderId.value)
}

function openCreateFolder(parentId = currentFolderId.value) {
  dialogTrigger.value = document.activeElement
  dialogMode.value = 'folder'
  dialogError.value = null
  folderForm.value = { name: '', parentId: parentId ?? null }
  focusDialogInput()
}

function openCreateNote(parentId = currentFolderId.value) {
  dialogTrigger.value = document.activeElement
  dialogMode.value = 'note'
  dialogError.value = null
  noteForm.value = { title: '', parentId: parentId ?? null }
  focusDialogInput()
}

function openRename(node) {
  dialogTrigger.value = document.activeElement
  dialogMode.value = 'rename'
  dialogError.value = null
  renameForm.value = { name: node.name, nodeId: node.id }
  focusDialogInput(true)
}

function openMove(node) {
  dialogTrigger.value = document.activeElement
  dialogMode.value = 'move'
  dialogError.value = null
  moveForm.value = { nodeId: node.id, parentId: node.parent_id ?? node.parentId ?? null }
}

function closeDialog() {
  dialogMode.value = null
  dialogError.value = null
  nextTick(() => dialogTrigger.value?.focus?.())
  dialogTrigger.value = null
}

function focusDialogInput(select = false) {
  nextTick(() => {
    dialogInput.value?.focus()
    if (select) dialogInput.value?.select()
  })
}

async function submitCreateFolder() {
  try {
    await createFolder({ name: folderForm.value.name, parentId: folderForm.value.parentId })
    closeDialog()
    showToast('文件夹已创建')
  } catch (cause) {
    dialogError.value = getErrorMessage(cause)
  }
}

async function submitCreateNote() {
  try {
    const node = await createNote({ title: noteForm.value.title, parentId: noteForm.value.parentId })
    closeDialog()
    treeOpen.value = false
    showToast('笔记已创建')
    if (node?.id != null) {
      router.push({ name: 'NotebookWorkspaceView', params: { notebookId: notebookId.value, noteId: node.id } })
    }
  } catch (cause) {
    dialogError.value = getErrorMessage(cause)
  }
}

async function submitRename() {
  try {
    await renameNode(renameForm.value.nodeId, renameForm.value.name)
    closeDialog()
    showToast('名称已更新')
  } catch (cause) {
    dialogError.value = getErrorMessage(cause)
  }
}

async function submitMove() {
  try {
    await moveNode(moveForm.value.nodeId, moveForm.value.parentId)
    closeDialog()
    showToast('节点已移动')
  } catch (cause) {
    dialogError.value = getErrorMessage(cause)
  }
}

async function handleDelete(node) {
  const kind = node.type === 'folder' ? '文件夹及其内容' : '笔记'
  if (!window.confirm(`确定删除${kind}「${node.name}」吗？此操作不可撤销。`)) return
  try {
    await deleteNode(node)
    if (!selectedNoteId.value && route.params.noteId) {
      selectedNoteId.value = null
      router.replace({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } })
    }
    showToast('已删除')
  } catch (cause) {
    showToast(getErrorMessage(cause), 'error')
  }
}

watch(notebookId, loadWorkspace, { immediate: true })
watch(() => route.params.noteId, syncRouteSelection)
watch(isNewNoteRoute, (isNew) => {
  if (isNew) openCreateNote(currentFolderId.value)
})
watch(dialogMode, (mode) => {
  if (mode) nextTick(focusDialogInput)
})

onUnmounted(() => {
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<style scoped>
.workspace-shell {
  --workspace-line: rgba(148, 163, 184, 0.22);
  --workspace-soft: rgba(14, 165, 233, 0.08);
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  min-height: calc(100vh - 150px);
  overflow: hidden;
  color: var(--color-text);
}

.workspace-header,
.workspace-layout,
.workspace-heading,
.workspace-actions,
.directory-header,
.content-toolbar,
.selection-card,
.selection-links,
.dialog-header,
.dialog-actions {
  display: flex;
}

.workspace-header {
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg);
  padding: 0 0 var(--spacing-lg);
  border-bottom: 1px solid var(--workspace-line);
}

.workspace-heading {
  align-items: center;
  min-width: 0;
  gap: var(--spacing-sm);
}

.workspace-kicker,
.panel-kicker,
.selection-eyebrow,
.dialog-kicker {
  margin: 0 0 4px;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.workspace-title,
.panel-title,
.selection-copy h2,
.dialog-title {
  margin: 0;
  color: var(--color-text);
  font-weight: 700;
}

.workspace-title {
  font-size: clamp(1.35rem, 2.4vw, 1.9rem);
  line-height: 1.2;
}

.workspace-subtitle {
  max-width: 58vw;
  margin: 5px 0 0;
  overflow: hidden;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-actions {
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

.workspace-layout {
  flex: 1;
  min-height: 0;
  padding-top: var(--spacing-lg);
  gap: var(--spacing-lg);
}

.directory-panel {
  display: flex;
  flex: 0 0 min(350px, 31%);
  flex-direction: column;
  min-width: 0;
  min-height: 420px;
  overflow: hidden;
  background: var(--color-card);
  border: 1px solid var(--workspace-line);
  border-radius: var(--radius-xl);
}

.directory-header {
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--workspace-line);
}

.panel-title {
  overflow: hidden;
  font-size: var(--font-size-base);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.directory-panel :deep(.note-tree) {
  min-height: 0;
  overflow: auto;
}

.directory-panel :deep(.note-tree__list) {
  padding: var(--spacing-sm);
}

.directory-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  text-align: center;
}

.directory-state--error {
  flex-direction: column;
  color: var(--color-error);
}

.directory-state--error p {
  margin: 0;
}

.workspace-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 420px;
  overflow: hidden;
  background: var(--color-bg-secondary);
  border: 1px solid var(--workspace-line);
  border-radius: var(--radius-xl);
}

.content-toolbar {
  align-items: center;
  min-width: 0;
  min-height: 58px;
  gap: var(--spacing-md);
  padding: 0 var(--spacing-lg);
  border-bottom: 1px solid var(--workspace-line);
}

.breadcrumbs {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 7px;
  overflow: auto;
}

.breadcrumb-button,
.toolbar-button,
.icon-button,
.text-button,
.context-link {
  cursor: pointer;
  font-family: var(--font-family);
}

.breadcrumb-button {
  min-height: 44px;
  max-width: 220px;
  overflow: hidden;
  padding: 0 4px;
  color: var(--color-text-tertiary);
  background: transparent;
  border: 0;
  font-size: var(--font-size-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumb-button:hover,
.breadcrumb-button:focus-visible,
.breadcrumb-button--active {
  color: var(--color-primary);
}

.breadcrumb-separator {
  flex: 0 0 auto;
  color: var(--color-text-tertiary);
}

.toolbar-button {
  align-items: center;
  gap: 7px;
  min-height: 44px;
  padding: 0 var(--spacing-sm);
  color: var(--color-text-secondary);
  background: transparent;
  border: 0;
  font-size: var(--font-size-sm);
}

.toolbar-button svg,
.button svg,
.icon-button svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.content-state {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  min-height: 320px;
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  text-align: center;
}

.content-state p {
  margin: 0;
}

.content-state--error h2 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-lg);
}

.content-state--error p {
  max-width: 340px;
}

.state-icon,
.selection-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: var(--radius-xl);
}

.state-icon {
  width: 64px;
  height: 64px;
}

.state-icon svg,
.selection-icon svg {
  width: 30px;
  height: 30px;
}

.state-icon--error {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.1);
}

.selection-card {
  align-items: flex-start;
  max-width: 720px;
  margin: auto;
  padding: clamp(var(--spacing-lg), 6vw, 4rem);
  gap: var(--spacing-xl);
}

.selection-icon {
  width: 68px;
  height: 68px;
}

.selection-icon--note {
  color: var(--color-primary);
  background: rgba(14, 165, 233, 0.12);
}

.selection-icon--folder {
  color: var(--color-secondary);
  background: rgba(20, 184, 166, 0.12);
}

.selection-icon--accent {
  color: var(--color-cta, #f97316);
  background: rgba(249, 115, 22, 0.12);
}

.selection-copy {
  min-width: 0;
}

.selection-copy h2 {
  overflow-wrap: anywhere;
  font-size: clamp(1.35rem, 3vw, 2rem);
}

.selection-copy > p:not(.selection-eyebrow) {
  max-width: 480px;
  margin: var(--spacing-sm) 0 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  line-height: 1.7;
}

.selection-links {
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xl);
}

.button,
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-decoration: none;
  transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.button {
  gap: 8px;
  padding: 0 var(--spacing-md);
  border: 1px solid transparent;
  white-space: nowrap;
}

.button--primary {
  color: #fff;
  background: var(--color-primary);
}

.button--primary:hover {
  background: var(--color-primary-dark);
}

.button--quiet {
  color: var(--color-text-secondary);
  background: transparent;
  border-color: var(--workspace-line);
}

.button--quiet:hover,
.button--quiet:focus-visible,
.toolbar-button:hover,
.toolbar-button:focus-visible,
.icon-button:hover,
.icon-button:focus-visible {
  color: var(--color-primary);
  background: var(--workspace-soft);
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.context-link,
.text-button {
  min-height: 44px;
  padding: 0 var(--spacing-sm);
  color: var(--color-primary);
  background: transparent;
  border: 0;
  font-size: var(--font-size-sm);
  text-decoration: none;
}

.context-link:hover,
.context-link:focus-visible,
.text-button:hover,
.text-button:focus-visible {
  text-decoration: underline;
}

.icon-button {
  width: 44px;
  padding: 0;
  color: var(--color-text-secondary);
  background: transparent;
  border: 0;
}

.mobile-only {
  display: none;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--workspace-line);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: workspace-spin 0.8s linear infinite;
}

.spinner--large {
  width: 32px;
  height: 32px;
  border-width: 3px;
}

@keyframes workspace-spin {
  to { transform: rotate(360deg); }
}

.dialog-overlay {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
  background: rgba(15, 23, 42, 0.52);
}

.dialog {
  width: min(100%, 440px);
  overflow: hidden;
  background: var(--color-card);
  border: 1px solid var(--workspace-line);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
}

.dialog-header {
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--workspace-line);
}

.dialog-title {
  font-size: var(--font-size-lg);
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
}

.form-label {
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.form-input {
  width: 100%;
  min-height: 44px;
  box-sizing: border-box;
  padding: 0 var(--spacing-md);
  color: var(--color-text);
  background: var(--color-bg-secondary);
  border: 1px solid var(--workspace-line);
  border-radius: var(--radius-md);
  outline: none;
  font: inherit;
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.12);
}

.form-error {
  margin: 0;
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.dialog-actions {
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.workspace-toast {
  position: fixed;
  z-index: 1100;
  right: var(--spacing-lg);
  bottom: calc(var(--spacing-lg) + var(--safe-area-bottom));
  max-width: min(360px, calc(100vw - 2rem));
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.workspace-toast--success {
  color: #fff;
  background: var(--color-primary);
}

.workspace-toast--error {
  color: #fff;
  background: var(--color-error);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (prefers-reduced-motion: reduce) {
  .spinner { animation: none; }
  .button,
  .icon-button { transition: none; }
}

@media (max-width: 767px) {
  .workspace-shell {
    min-height: calc(100vh - 130px);
  }

  .workspace-header {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .workspace-heading {
    width: 100%;
  }

  .workspace-subtitle {
    max-width: calc(100vw - 100px);
  }

  .workspace-actions {
    width: 100%;
  }

  .workspace-actions .button {
    flex: 1;
  }

  .workspace-layout {
    position: relative;
    min-height: 0;
    padding-top: var(--spacing-md);
  }

  .mobile-only {
    display: inline-flex;
  }

  .directory-panel {
    position: fixed;
    z-index: 101;
    top: var(--safe-area-top);
    bottom: calc(var(--bottom-nav-height) + var(--safe-area-bottom));
    left: 0;
    width: min(88vw, 350px);
    min-height: 0;
    border-radius: 0 var(--radius-xl) var(--radius-xl) 0;
    padding-bottom: var(--safe-area-bottom);
    box-sizing: border-box;
    transform: translateX(-105%);
    transition: transform 0.22s ease;
  }

  .directory-panel--open {
    transform: translateX(0);
  }

  .workspace-overlay {
    position: fixed;
    z-index: 100;
    inset: 0;
    background: rgba(15, 23, 42, 0.42);
  }

  .workspace-content {
    min-height: 520px;
  }

  .content-toolbar {
    gap: var(--spacing-sm);
    padding: 0 var(--spacing-sm);
  }

  .breadcrumbs {
    gap: 4px;
  }

  .breadcrumb-button {
    max-width: 140px;
  }

  .selection-card {
    flex-direction: column;
    margin: 0;
    padding: var(--spacing-xl) var(--spacing-lg);
    gap: var(--spacing-lg);
  }

  .selection-links {
    align-items: stretch;
    flex-direction: column;
  }

  .selection-links .button,
  .selection-links .context-link {
    width: 100%;
    box-sizing: border-box;
    justify-content: center;
    text-align: center;
  }

  .dialog-overlay {
    align-items: flex-end;
    padding: var(--spacing-sm);
  }

  .dialog-actions {
    flex-direction: column-reverse;
  }

  .dialog-actions .button {
    width: 100%;
  }

  .workspace-toast {
    right: var(--spacing-md);
    left: var(--spacing-md);
    max-width: none;
    text-align: center;
  }
}
</style>
