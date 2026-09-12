<template>
  <section class="today-workbench" aria-labelledby="workbench-heading">
    <header class="workbench-header">
      <div>
        <p class="eyebrow">先行动，再成长</p>
        <h2 id="workbench-heading">今日工作台</h2>
        <p class="muted">{{ data?.date || '正在获取日期' }} · 中国时间 · 今天最重要的事，从这里开始</p>
      </div>
      <button type="button" :disabled="busy || loading" @click="load()">{{ loading ? '刷新中…' : '刷新' }}</button>
    </header>

    <div v-if="data" class="workbench-metrics" aria-label="今日行动进展">
      <div><strong>{{ data.summary.completed_today }}</strong><span>今日已完成</span></div>
      <div><strong>{{ data.summary.today }}</strong><span>今日到期</span></div>
      <div><strong>{{ data.summary.overdue }}</strong><span>逾期待处理</span></div>
      <div><strong>{{ data.summary.focus_completed }}/{{ data.focus_tasks.length }}</strong><span>今日重点进展</span></div>
    </div>

    <form class="quick-task-form" @submit.prevent="createTask">
      <div class="title-field">
        <label for="workbench-task-title">快速新增任务</label>
        <input id="workbench-task-title" ref="titleInput" v-model="draft.title" type="text" maxlength="200"
          placeholder="写下下一步要做的事…" autocomplete="off" :disabled="busy" required />
      </div>
      <div>
        <label for="workbench-task-schedule">截止时间</label>
        <select id="workbench-task-schedule" v-model="draft.schedule" :disabled="busy">
          <option value="today">今天结束前</option>
          <option value="unscheduled">暂不安排时间</option>
          <option value="date">指定日期</option>
        </select>
      </div>
      <div v-if="draft.schedule === 'date'">
        <label for="workbench-task-date">截止日期（中国时间）</label>
        <input id="workbench-task-date" v-model="draft.due_date" type="date" :disabled="busy" required />
      </div>
      <button class="primary-button" type="submit" :disabled="busy || !draft.title.trim()">
        {{ pendingAction === 'create' ? '创建中…' : '添加任务' }}
      </button>
    </form>

    <p v-if="actionError" class="message error-message" role="alert">{{ actionError }}</p>
    <p v-if="feedback" class="message success-message" role="status">{{ feedback }}</p>
    <p v-if="warning" class="message warning-message" role="status">{{ warning }}</p>
    <div v-if="loadError" class="message error-message" role="alert">
      {{ loadError }}<span v-if="data"> 当前保留上次加载的内容。</span>
      <button type="button" :disabled="busy || loading" @click="load()">重试加载</button>
    </div>
    <p v-if="loading && !data" class="muted" role="status">正在整理今天的任务…</p>

    <template v-if="data">
      <section class="focus-section" aria-labelledby="focus-heading">
        <div class="section-heading">
          <div>
            <h3 id="focus-heading">今天最重要的三件事</h3>
            <p class="muted">最多选择三项，完成后会保留在这里。次日重新选择，不改变任务原有优先级。</p>
          </div>
          <button v-if="!editingFocus" ref="focusTrigger" type="button" :disabled="busy"
            :aria-expanded="editingFocus" aria-controls="focus-editor" @click="openFocus">
            {{ data.focus_tasks.length ? '调整重点' : '选择重点' }}
          </button>
        </div>
        <div v-if="data.focus_tasks.length" class="focus-tasks">
          <div v-for="(task, index) in data.focus_tasks" :key="task.id" class="focus-task-card">
            <span class="focus-rank">重点 {{ index + 1 }}</span>
            <WorkbenchTaskRow :task="task" :busy="busy" :pending="pendingAction === `complete:${task.id}`" @complete="completeTask" />
          </div>
        </div>
        <p v-else class="focus-empty">今天还没有选择重点。从下方任务中挑选最值得完成的三件事，也可以先快速新增。</p>

        <form v-if="editingFocus" id="focus-editor" class="focus-editor" @submit.prevent="saveFocus" @keydown.esc.prevent="closeFocus">
          <fieldset :disabled="busy">
            <legend>选择并排序 · 已选 {{ focusDraft.length }}/3</legend>
            <ol v-if="draftTasks.length" class="draft-order">
              <li v-for="(task, index) in draftTasks" :key="task.id">
                <span>{{ task.title }}</span>
                <div class="order-actions">
                  <button type="button" :disabled="index === 0" :aria-label="`上移 ${task.title}`" @click="moveFocus(task.id, -1)">↑</button>
                  <button type="button" :disabled="index === draftTasks.length - 1" :aria-label="`下移 ${task.title}`" @click="moveFocus(task.id, 1)">↓</button>
                  <button type="button" :aria-label="`移除重点 ${task.title}`" @click="toggleFocus(task.id)">移除</button>
                </div>
              </li>
            </ol>
            <label for="focus-task-search">筛选可选任务</label>
            <input id="focus-task-search" ref="focusSearchInput" v-model="focusSearch" type="search" placeholder="搜索任务标题" />
            <div class="focus-options">
              <label v-for="task in filteredCandidates" :key="task.id" class="focus-option">
                <input type="checkbox" :checked="focusDraft.includes(task.id)"
                  :disabled="focusDraft.length >= 3 && !focusDraft.includes(task.id)" @change="toggleFocus(task.id)" />
                <span>{{ task.title }}<small v-if="task.status === 'completed'"> · 已完成</small></span>
              </label>
              <p v-if="!filteredCandidates.length" class="muted">没有匹配的任务。可以先新增任务，再回来选择。</p>
            </div>
          </fieldset>
          <p v-if="focusError" class="message error-message" role="alert">{{ focusError }}</p>
          <div class="editor-actions">
            <button type="button" :disabled="busy" @click="closeFocus">取消</button>
            <button type="submit" class="primary-button" :disabled="busy">{{ pendingAction === 'focus' ? '保存中…' : '保存今日重点' }}</button>
          </div>
        </form>
      </section>

      <div class="task-groups">
        <section v-for="group in taskGroups" :key="group.key" class="task-group" :aria-labelledby="`workbench-${group.key}`">
          <div class="section-heading">
            <h3 :id="`workbench-${group.key}`">{{ group.label }}</h3>
            <span class="group-count">{{ data.task_groups[group.key].length }}</span>
          </div>
          <WorkbenchTaskRow v-for="task in data.task_groups[group.key].slice(0, expandedGroups[group.key] ? undefined : 5)"
            :key="task.id" :task="task" :busy="busy" :pending="pendingAction === `complete:${task.id}`" @complete="completeTask" />
          <p v-if="!data.task_groups[group.key].length" class="muted group-empty">{{ group.empty }}</p>
          <button v-if="data.task_groups[group.key].length > 5" class="more-button" type="button"
            :aria-expanded="Boolean(expandedGroups[group.key])" @click="expandedGroups[group.key] = !expandedGroups[group.key]">
            {{ expandedGroups[group.key] ? '收起' : `查看全部 ${data.task_groups[group.key].length} 项` }}
          </button>
        </section>
      </div>
      <footer class="workbench-footer">
        <span class="muted">完成任务会使用与待办、项目页一致的奖励结算。</span>
        <router-link to="/todos">管理全部待办 →</router-link>
      </footer>
    </template>
    <div v-else-if="!loading && !loadError" class="message error-message" role="alert">
      工作台没有返回可显示的数据。
      <button type="button" :disabled="busy" @click="load()">重试加载</button>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { todoService } from '../../services/todo'
import { useAuthStore } from '../../stores/auth'
import { useCultivationStore } from '../../stores/cultivation'
import { todayChinaDateKey } from '../../utils/dateTime'
import { useDailyWorkbench } from '../../composables/useDailyWorkbench'
import WorkbenchTaskRow from './WorkbenchTaskRow.vue'

const emit = defineEmits(['changed'])
const authStore = useAuthStore()
const cultivationStore = useCultivationStore()
const {
  data, loading, loadError, actionError, feedback, warning, pendingAction,
  draft, editingFocus, focusDraft, focusError,
  load, createTask, completeTask, beginFocus, cancelFocus, toggleFocus, moveFocus, saveFocus, dispose
} = useDailyWorkbench(todoService, {
  refreshRewards: () => Promise.all([authStore.fetchUser(), cultivationStore.refresh()]),
  onChanged: () => emit('changed')
})

const titleInput = ref(null)
const focusTrigger = ref(null)
const focusSearchInput = ref(null)
const focusSearch = ref('')
const expandedGroups = ref({})
const busy = computed(() => pendingAction.value !== null)
const candidates = computed(() => [...new Map([
  ...(data.value?.focus_tasks || []),
  ...Object.values(data.value?.task_groups || {}).flat()
].map(task => [task.id, task])).values()])
const draftTasks = computed(() => focusDraft.value.map(id =>
  candidates.value.find(task => task.id === id) || { id, title: '任务已不可用，请移除后重选' }
))
const filteredCandidates = computed(() => candidates.value.filter(task => task.title.toLocaleLowerCase().includes(focusSearch.value.trim().toLocaleLowerCase())))
const taskGroups = [
  { key: 'today', label: '今日到期', empty: '今天没有待完成的到期任务。' },
  { key: 'overdue', label: '已经逾期', empty: '没有逾期任务，继续保持。' },
  { key: 'unscheduled', label: '未安排时间', empty: '没有待安排时间的任务。' },
  { key: 'upcoming', label: '稍后到期', empty: '暂无未来到期的任务。' }
]
let dayTimer = null

watch(editingFocus, async (editing, previous) => {
  if (previous && !editing) {
    await nextTick()
    focusTrigger.value?.focus()
  }
})

async function openFocus() {
  beginFocus()
  focusSearch.value = ''
  await nextTick()
  focusSearchInput.value?.focus()
}

async function closeFocus() {
  cancelFocus()
  await nextTick()
  focusTrigger.value?.focus()
}

function refreshVisible() {
  if (document.visibilityState === 'visible' && !busy.value && !loading.value && !editingFocus.value) load()
}

onMounted(() => {
  load()
  window.addEventListener('focus', refreshVisible)
  document.addEventListener('visibilitychange', refreshVisible)
  dayTimer = setInterval(() => {
    if (data.value && data.value.date !== todayChinaDateKey()) refreshVisible()
  }, 60000)
})

onUnmounted(() => {
  dispose()
  clearInterval(dayTimer)
  window.removeEventListener('focus', refreshVisible)
  document.removeEventListener('visibilitychange', refreshVisible)
})

defineExpose({ focusQuickAdd: () => titleInput.value?.focus() })
</script>

<style scoped>
.today-workbench { padding: clamp(16px, 3vw, 28px); color: var(--color-text); background: var(--color-card); border: 1px solid var(--color-border); border-radius: var(--surface-radius); box-shadow: var(--shadow-sm); margin-bottom: var(--spacing-md); min-width: 0; }
.workbench-header, .section-heading, .workbench-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.workbench-header { align-items: flex-start; }
.eyebrow { margin: 0 0 6px; color: var(--color-primary); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
h2 { margin: 0 0 8px; font-size: clamp(22px, 4vw, 28px); }
h3 { margin: 0; font-size: 16px; }
.muted { color: var(--color-text-secondary); font-size: 13px; line-height: 1.6; margin: 6px 0; }
button, input, select { font: inherit; }
button { border: 1px solid var(--color-border); background: var(--color-card); color: var(--color-text); min-height: 44px; padding: 8px 14px; border-radius: 10px; cursor: pointer; flex-shrink: 0; }
button:disabled { opacity: .55; cursor: not-allowed; }
button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 3px; }
input:not([type=checkbox]), select { box-sizing: border-box; width: 100%; min-height: 44px; min-width: 0; border: 1px solid var(--color-border); border-radius: 10px; padding: 10px 12px; background: var(--color-card); color: var(--color-text); }
label { display: block; font-size: 13px; margin-bottom: 6px; }
.primary-button { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.workbench-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 20px 0; }
.workbench-metrics > div { background: var(--color-bg); border-radius: 12px; padding: 14px; display: grid; gap: 4px; }
.workbench-metrics strong { font-size: 24px; }
.workbench-metrics span { color: var(--color-text-secondary); font-size: 12px; }
.quick-task-form { display: flex; flex-wrap: wrap; align-items: end; gap: 12px; padding: 16px 0; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); }
.title-field { flex: 1 1 250px; }
.message { font-size: 14px; line-height: 1.7; padding: 12px; border-radius: 10px; background: var(--color-bg); overflow-wrap: anywhere; }
.error-message { color: #b42318; }
.success-message { color: #157347; }
.warning-message { color: #855400; }
.message button { margin-left: 10px; }
.focus-section { margin: 24px 0; }
.focus-tasks { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
.focus-task-card { border: 1px solid var(--color-border); border-radius: 12px; padding: 12px; background: var(--color-bg); min-width: 0; }
.focus-rank { color: var(--color-primary); font-size: 12px; font-weight: 700; }
.focus-empty { color: var(--color-text-secondary); font-size: 14px; padding: 18px; border: 1px dashed var(--color-border); border-radius: 12px; line-height: 1.7; }
.focus-editor { padding: 16px; margin-top: 16px; border: 1px solid var(--color-border); border-radius: 12px; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
legend { font-size: 14px; font-weight: 600; padding: 0 0 12px; }
.draft-order { padding-left: 24px; }
.draft-order li { margin-bottom: 8px; }
.draft-order li > span { overflow-wrap: anywhere; }
.order-actions { display: inline-flex; gap: 6px; margin-left: 10px; }
.order-actions button { min-width: 44px; }
.focus-options { max-height: 260px; overflow-y: auto; margin: 12px 0; }
.focus-option { display: flex; align-items: center; gap: 10px; min-height: 44px; cursor: pointer; overflow-wrap: anywhere; }
.focus-option input { width: 18px; height: 18px; flex-shrink: 0; accent-color: var(--color-primary); }
.focus-option small { color: var(--color-text-secondary); }
.editor-actions { display: flex; justify-content: flex-end; gap: 10px; }
.task-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.task-group { padding: 16px; border: 1px solid var(--color-border); border-radius: 12px; min-width: 0; }
.group-count { font-size: 13px; background: var(--color-bg); padding: 4px 10px; border-radius: 20px; }
.group-empty { padding: 16px 0; }
.more-button { width: 100%; color: var(--color-primary); }
.workbench-footer { margin-top: 18px; }
.workbench-footer a { color: var(--color-primary); font-size: 14px; flex-shrink: 0; }
@media (max-width: 900px) { .focus-tasks { grid-template-columns: 1fr; } }
@media (max-width: 600px) {
  .task-groups { grid-template-columns: 1fr; gap: 12px; }
  .workbench-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .quick-task-form > div { flex: 1 1 100%; }
  .quick-task-form > button { width: 100%; }
  .section-heading, .workbench-footer { align-items: flex-start; flex-wrap: wrap; }
  .order-actions { display: flex; margin: 6px 0 0; }
  button, input:not([type=checkbox]), select, .focus-option { min-height: 48px; }
  input:not([type=checkbox]), select { font-size: 16px; }
}
</style>
