<template>
  <section class="sync-page" aria-labelledby="sync-title">
    <header class="sync-header">
      <div class="sync-heading">
        <button type="button" class="icon-button" aria-label="返回笔记本" title="返回笔记本" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <div>
          <p class="sync-kicker">笔记本同步</p>
          <h1 id="sync-title">{{ notebook?.name || '文件夹同步' }}</h1>
          <p class="sync-subtitle">把一个 Windows 文件夹映射为当前笔记本的 Markdown 目录</p>
        </div>
      </div>
      <span class="status-pill" :class="`status-pill--${statusTone}`" aria-live="polite">
        <span class="status-dot" aria-hidden="true"></span>{{ statusLabel }}
      </span>
    </header>

    <div v-if="notebookLoading" class="sync-state" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span><span>正在检查笔记本权限…</span>
    </div>
    <div v-else-if="notebookError" class="sync-state sync-state--error" role="alert">
      <strong>无法打开同步设置</strong>
      <p>{{ notebookError }}</p>
      <button type="button" class="button button--primary" @click="loadNotebook">重新加载</button>
    </div>
    <div v-else-if="!canSync" class="sync-state sync-state--quiet">
      <div class="sync-state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9" /><path d="M8 12h8M12 8v8" /></svg>
      </div>
      <strong>只有笔记本所有者可以管理文件夹同步</strong>
      <p>当前账号可以继续使用笔记本，但不能绑定或修改本地文件夹。</p>
      <button type="button" class="button button--quiet" @click="goBack">返回笔记本</button>
    </div>
    <template v-else>
      <div v-if="!isDesktop" class="desktop-notice" role="note">
        <div class="notice-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="14" rx="2" /><path d="M8 21h8M12 18v3" /></svg>
        </div>
        <div>
          <strong>请在 LifeQuest Windows 客户端中绑定文件夹</strong>
          <p>浏览器可以查看同步权限和冲突记录；本地目录选择、预览和文件写入只在 Windows 客户端执行。</p>
        </div>
      </div>

      <section class="sync-panel sync-panel--binding" aria-labelledby="binding-title">
        <div class="panel-heading">
          <div>
            <p class="panel-eyebrow">绑定</p>
            <h2 id="binding-title">本地文件夹</h2>
          </div>
          <span v-if="binding" class="binding-state">{{ binding.paused ? '已暂停' : '已绑定' }}</span>
        </div>
        <div class="binding-row">
          <div class="folder-symbol" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M3 9h18" /></svg>
          </div>
          <div class="binding-copy">
            <strong v-if="binding">{{ binding.folder }}</strong>
            <strong v-else>尚未选择文件夹</strong>
             <span>{{ binding ? `同步游标 ${binding.cursor || 0}${status.pending_operations ? ` · 待重试 ${status.pending_operations}` : ''}` : '选择一个空文件夹或已有 Markdown 文件夹开始' }}</span>
          </div>
          <button type="button" class="button button--quiet" :disabled="loading || !isDesktop" @click="chooseFolder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" /></svg>
            {{ binding ? '更换文件夹' : '选择文件夹' }}
          </button>
        </div>
      </section>

      <section class="sync-panel sync-panel--actions" aria-labelledby="actions-title">
        <div class="panel-heading">
          <div>
            <p class="panel-eyebrow">安全流程</p>
            <h2 id="actions-title">预览与同步</h2>
          </div>
          <div class="action-group">
            <button type="button" class="button button--quiet" :disabled="loading || !binding || !isDesktop" @click="runPreview">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
              生成预览
            </button>
            <button v-if="binding?.paused" type="button" class="button button--primary" :disabled="loading || !isDesktop" @click="resumeSync">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m8 5 11 7-11 7z" /></svg>
              恢复同步
            </button>
            <button v-else type="button" class="button button--primary" :disabled="loading || !binding || !isDesktop" @click="beginSync">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M20 11a8 8 0 1 1-2.3-5.7M20 4v7h-7" /></svg>
              {{ hasSynced ? '立即同步' : '开始同步' }}
            </button>
            <button v-if="binding && !binding.paused" type="button" class="icon-button icon-button--subtle" :disabled="loading || !isDesktop" title="暂停同步" aria-label="暂停同步" @click="pauseSync">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M8 5v14M16 5v14" /></svg>
            </button>
          </div>
        </div>

        <div v-if="preview" class="preview-summary" aria-live="polite">
          <div><strong>{{ preview.items.length }}</strong><span>项待处理</span></div>
          <div><strong>{{ countAction('download') }}</strong><span>下载</span></div>
          <div><strong>{{ countAction('upload') }}</strong><span>上传</span></div>
          <div><strong>{{ countAction('conflict') }}</strong><span>需处理</span></div>
        </div>
        <div v-if="preview?.items?.length" class="preview-table-wrap">
          <table class="preview-table">
            <thead><tr><th scope="col">路径</th><th scope="col">类型</th><th scope="col">动作</th><th scope="col">说明</th></tr></thead>
            <tbody>
              <tr v-for="item in preview.items" :key="`${item.action}-${item.relative_path}`">
                <td class="path-cell">{{ item.relative_path }}</td>
                <td>{{ item.node_type === 'folder' ? '文件夹' : 'Markdown' }}</td>
                <td><span class="action-label" :class="`action-label--${item.action}`">{{ actionLabel(item.action) }}</span></td>
                <td class="reason-cell">{{ item.reason }}</td>
              </tr>
            </tbody>
          </table>
          <p class="preview-footnote">预览不会修改本地文件。删除、覆盖和冲突项需要在确认后处理。</p>
        </div>
        <div v-else-if="preview" class="empty-preview">
          <strong>两边已经一致</strong><span>没有需要处理的 Markdown 文件或文件夹。</span>
        </div>
        <div v-else class="empty-preview empty-preview--hint">
          <strong>{{ binding ? '先生成一次预览' : '先选择一个文件夹' }}</strong>
          <span>{{ binding ? '确认文件变化后，再开始第一次同步。' : '客户端只会访问你选择的这一处文件夹。' }}</span>
        </div>
      </section>

      <section class="sync-panel" aria-labelledby="conflicts-title">
        <div class="panel-heading">
          <div>
            <p class="panel-eyebrow">恢复</p>
            <h2 id="conflicts-title">冲突记录</h2>
          </div>
          <button type="button" class="text-button" :disabled="loading" @click="refreshConflicts">刷新</button>
        </div>
        <div v-if="openConflicts.length" class="conflict-list">
          <article v-for="conflict in openConflicts" :key="conflict.id" class="conflict-item">
            <div class="conflict-copy">
              <strong>{{ conflict.local_path }}</strong>
              <span>远端修订 {{ conflict.remote_revision || '-' }} · {{ formatDate(conflict.created_at) }}</span>
            </div>
            <div class="conflict-actions">
              <button type="button" class="button button--quiet" :disabled="loading || !isDesktop" @click="resolve(conflict, 'keep_remote')">保留云端</button>
              <button type="button" class="button button--primary" :disabled="loading || !isDesktop" @click="resolve(conflict, 'keep_local')">保留本地</button>
            </div>
          </article>
        </div>
        <div v-else class="empty-preview empty-preview--compact">
          <strong>没有未处理冲突</strong><span>并发编辑时，双方版本会保留在恢复流程中。</span>
        </div>
      </section>

      <div v-if="error" class="sync-error" role="alert">
        <span>{{ errorMessage }}</span>
        <button type="button" class="text-button" @click="retry">重试</button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNoteSync } from '../composables/useNoteSync'
import { noteService } from '../services/note'
import { getErrorMessage } from '../utils/errorMessage'

const route = useRoute()
const router = useRouter()
const notebookId = computed(() => route.params.notebookId)
const notebook = ref(null)
const notebookLoading = ref(true)
const notebookError = ref(null)
const hasSynced = ref(false)

const {
  binding,
  status,
  preview,
  conflicts,
  loading,
  error,
  isDesktop,
  selectFolder,
  previewSync,
  start,
  pause,
  resume,
  refreshConflicts,
  resolveConflict,
} = useNoteSync(notebookId)

const canSync = computed(() => notebook.value?.is_owner === true)
const openConflicts = computed(() => conflicts.value.filter(item => item.status === 'open'))
const statusLabel = computed(() => ({
  unbound: '未绑定',
  bound: '已绑定',
  previewing: '正在预览',
  preview: '预览就绪',
  syncing: '同步中',
  synced: '已同步',
  paused: '已暂停',
  conflict: '需要处理',
  error: '同步异常',
}[status.value.state] || '未绑定'))
const statusTone = computed(() => status.value.state === 'error' ? 'error' : status.value.state === 'conflict' ? 'warning' : status.value.state === 'synced' ? 'success' : 'neutral')
const errorMessage = computed(() => getErrorMessage(error.value, '同步暂时不可用，请重试。'))

async function loadNotebook() {
  notebookLoading.value = true
  notebookError.value = null
  try {
    notebook.value = await noteService.getNotebook(notebookId.value)
    await refreshConflicts()
  } catch (cause) {
    notebookError.value = getErrorMessage(cause, '无法读取笔记本权限。')
  } finally {
    notebookLoading.value = false
  }
}

async function chooseFolder() {
  await selectFolder()
  await runPreview()
}

async function runPreview() {
  await previewSync()
}

async function beginSync() {
  if (!binding.value || !isDesktop.value) return
  if (!preview.value) await runPreview()
  if (preview.value?.items?.length && !window.confirm('确认按预览结果开始同步吗？本地文件不会在预览阶段改变。')) return
  await start()
  hasSynced.value = true
}

async function pauseSync() { await pause() }
async function resumeSync() { await resume(); hasSynced.value = true }
async function retry() { await runPreview() }

async function resolve(conflict, resolution, content) {
  await resolveConflict(conflict, resolution, content)
}

function countAction(action) { return preview.value?.items?.filter(item => item.action === action).length || 0 }
function actionLabel(action) {
  return { download: '下载', upload: '上传', keep_local: '保留本地', keep_remote: '保持一致', conflict: '冲突' }[action] || action
}
function formatDate(value) {
  if (!value) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}
function goBack() { router.push({ name: 'NotebookWorkspace', params: { notebookId: notebookId.value } }) }

onMounted(loadNotebook)
</script>

<style scoped>
.sync-page { width: 100%; max-width: 1180px; margin: 0 auto; color: var(--color-text); }
.sync-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 8px 0 28px; border-bottom: 1px solid var(--color-border); }
.sync-heading { display: flex; align-items: flex-start; gap: 14px; min-width: 0; }
.sync-heading h1 { margin: 2px 0 6px; font-size: clamp(1.55rem, 2.4vw, 2.1rem); line-height: 1.15; }
.sync-kicker, .panel-eyebrow { margin: 0; color: var(--color-text-muted); font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; }
.sync-subtitle { margin: 0; color: var(--color-text-muted); font-size: .92rem; }
.status-pill { display: inline-flex; align-items: center; gap: 8px; flex: 0 0 auto; padding: 7px 11px; border: 1px solid var(--color-border); color: var(--color-text-muted); font-size: .82rem; }
.status-pill--success { color: #167a50; border-color: rgba(22, 122, 80, .25); background: rgba(22, 122, 80, .06); }
.status-pill--warning { color: #9a5b08; border-color: rgba(154, 91, 8, .25); background: rgba(154, 91, 8, .06); }
.status-pill--error { color: #b23b3b; border-color: rgba(178, 59, 59, .25); background: rgba(178, 59, 59, .06); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.desktop-notice, .sync-panel, .sync-error { border: 1px solid var(--color-border); background: var(--color-surface); }
.desktop-notice { display: flex; align-items: flex-start; gap: 14px; margin-top: 22px; padding: 16px 18px; border-left: 3px solid #1d7b9e; }
.notice-icon, .sync-state-icon { color: #1d7b9e; flex: 0 0 auto; width: 24px; height: 24px; }
.notice-icon svg, .sync-state-icon svg { display: block; width: 100%; height: 100%; }
.desktop-notice strong { display: block; margin-bottom: 4px; }
.desktop-notice p { margin: 0; color: var(--color-text-muted); font-size: .88rem; line-height: 1.6; }
.sync-panel { margin-top: 18px; padding: 20px; }
.panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 18px; }
.panel-heading h2 { margin: 5px 0 0; font-size: 1.05rem; }
.binding-state { color: #167a50; font-size: .8rem; }
.binding-row { display: flex; align-items: center; gap: 14px; min-width: 0; }
.folder-symbol { display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 auto; color: #a66a1d; background: rgba(195, 134, 51, .12); }
.folder-symbol svg { width: 24px; height: 24px; }
.binding-copy { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 4px; }
.binding-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.binding-copy span { color: var(--color-text-muted); font-size: .83rem; }
.action-group { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
.button, .icon-button { white-space: nowrap; }
.button svg { width: 16px; height: 16px; }
.icon-button--subtle { color: var(--color-text-muted); }
.preview-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; margin: 0 0 18px; border: 1px solid var(--color-border); background: var(--color-border); }
.preview-summary div { display: flex; flex-direction: column; gap: 3px; padding: 12px; background: var(--color-surface-soft, var(--color-surface)); }
.preview-summary strong { font-size: 1.22rem; }
.preview-summary span { color: var(--color-text-muted); font-size: .78rem; }
.preview-table-wrap { overflow-x: auto; }
.preview-table { width: 100%; min-width: 640px; border-collapse: collapse; font-size: .84rem; }
.preview-table th, .preview-table td { padding: 11px 10px; border-bottom: 1px solid var(--color-border); text-align: left; vertical-align: top; }
.preview-table th { color: var(--color-text-muted); font-size: .74rem; font-weight: 600; }
.path-cell { max-width: 290px; overflow-wrap: anywhere; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.reason-cell { color: var(--color-text-muted); }
.action-label { display: inline-flex; padding: 3px 7px; border: 1px solid currentColor; font-size: .72rem; }
.action-label--download { color: #1d7b9e; }
.action-label--upload { color: #936019; }
.action-label--conflict { color: #b23b3b; }
.action-label--keep_remote, .action-label--keep_local { color: #167a50; }
.preview-footnote { margin: 12px 0 0; color: var(--color-text-muted); font-size: .78rem; }
.empty-preview { display: flex; flex-direction: column; gap: 5px; padding: 18px 0 2px; color: var(--color-text-muted); }
.empty-preview strong { color: var(--color-text); }
.empty-preview--hint { border-top: 1px solid var(--color-border); }
.empty-preview--compact { padding-top: 2px; }
.conflict-list { display: grid; gap: 10px; }
.conflict-item { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 14px; border: 1px solid rgba(178, 59, 59, .22); background: rgba(178, 59, 59, .035); }
.conflict-copy { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
.conflict-copy strong { overflow-wrap: anywhere; }
.conflict-copy span { color: var(--color-text-muted); font-size: .8rem; }
.conflict-actions { display: flex; flex: 0 0 auto; gap: 8px; }
.sync-state { display: flex; align-items: center; gap: 10px; min-height: 180px; justify-content: center; flex-direction: column; color: var(--color-text-muted); text-align: center; }
.sync-state--error { color: #b23b3b; }
.sync-state--error p, .sync-state--quiet p { max-width: 420px; margin: 0; color: var(--color-text-muted); line-height: 1.6; }
.sync-state--quiet { border: 1px dashed var(--color-border); margin-top: 22px; padding: 24px; }
.sync-error { display: flex; justify-content: space-between; gap: 12px; margin-top: 18px; padding: 12px 14px; color: #b23b3b; }
@media (max-width: 720px) {
  .sync-header, .binding-row, .conflict-item { align-items: stretch; flex-direction: column; }
  .sync-header { gap: 14px; }
  .status-pill { align-self: flex-start; }
  .sync-panel { padding: 16px; }
  .panel-heading { flex-direction: column; }
  .action-group { justify-content: flex-start; }
  .binding-row .button { align-self: flex-start; }
  .preview-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .conflict-actions { flex-wrap: wrap; }
}
</style>
