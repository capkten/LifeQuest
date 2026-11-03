<template>
  <section class="today-workbench" aria-labelledby="workbench-heading">
    <header class="workbench-header">
      <div>
        <p class="eyebrow">先行动，再成长</p>
        <h2 id="workbench-heading">今日工作台</h2>
        <p class="muted">{{ data?.date || '正在获取日期' }} · 中国时间</p>
      </div>
      <div class="header-actions">
        <button type="button" class="retreat-trigger-btn" @click="openRetreatModal(null)">
          <Sparkles class="retreat-icon" aria-hidden="true" /> 闭关专注
        </button>
        <button type="button" class="ghost-button" :disabled="busy || loading" @click="load()">{{ loading ? '刷新中…' : '刷新' }}</button>
      </div>
    </header>

    <div v-if="data" class="workbench-metrics" aria-label="今日行动进展">
      <div class="workbench-metric">
        <span class="metric-glyph metric-glyph--done" aria-hidden="true"></span>
        <strong class="metric-figure">{{ data.summary.completed_today }}</strong>
        <span class="workbench-metric-label">今日已完成</span>
      </div>
      <div class="workbench-metric">
        <span class="metric-glyph metric-glyph--due" aria-hidden="true"></span>
        <strong class="metric-figure">{{ data.summary.today }}</strong>
        <span class="workbench-metric-label">今日到期</span>
      </div>
      <div class="workbench-metric">
        <span class="metric-glyph metric-glyph--late" aria-hidden="true"></span>
        <strong class="metric-figure">{{ data.summary.overdue }}</strong>
        <span class="workbench-metric-label">逾期待处理</span>
      </div>
      <div class="workbench-metric">
        <span class="metric-glyph metric-glyph--focus" aria-hidden="true"></span>
        <strong class="metric-figure">{{ focusProgress }}</strong>
        <span class="workbench-metric-label">今日重点进展</span>
      </div>
    </div>

    <form class="quick-task-form" @submit.prevent="createTask">
      <label class="sr-only" for="workbench-task-title">新任务的标题</label>
      <input id="workbench-task-title" ref="titleInput" v-model="draft.title" type="text" maxlength="200"
        placeholder="写下下一步要做的事…" autocomplete="off" :disabled="busy" required />
      <label class="sr-only" for="workbench-task-schedule">截止时间</label>
      <select id="workbench-task-schedule" v-model="draft.schedule" :disabled="busy">
        <option value="today">今天结束前</option>
        <option value="unscheduled">暂不安排时间</option>
        <option value="date">指定日期</option>
      </select>
      <template v-if="draft.schedule === 'date'">
        <label class="sr-only" for="workbench-task-date">截止日期（中国时间）</label>
        <input id="workbench-task-date" v-model="draft.due_date" type="date" :disabled="busy" required />
      </template>
      <button class="primary-button" type="submit" :disabled="busy || !draft.title.trim()">
        {{ pendingAction === 'create' ? '创建中…' : '添加任务' }}
      </button>
    </form>

    <Transition name="reward">
      <p v-if="rewardFlash" class="reward-flash" role="status" aria-live="polite">
        <span class="reward-flash-mark" aria-hidden="true">✦</span>
        本次结算 {{ rewardFlash.text }}
      </p>
    </Transition>

    <p v-if="actionError" class="message error-message" role="alert">{{ actionError }}</p>
    <p v-if="feedback && !rewardFlash" class="message success-message" role="status">{{ feedback }}</p>
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
            <p class="muted">最多三项。次日重新选择，不改变任务原有优先级。</p>
          </div>
          <button v-if="!editingFocus && data.focus_tasks.length" ref="focusTrigger" type="button" :disabled="busy"
            :aria-expanded="editingFocus" aria-controls="focus-editor" @click="openFocus">调整重点</button>
        </div>
        <div class="focus-tasks">
          <div
            v-for="rank in 3"
            :key="rank"
            class="focus-task-card"
            :class="`focus-task-card--${rank}`"
          >
            <span class="focus-rank"><i aria-hidden="true">{{ rank }}</i>重点</span>
            <WorkbenchTaskRow
              v-if="data.focus_tasks[rank - 1]"
              :task="data.focus_tasks[rank - 1]"
              :busy="busy"
              :pending="pendingAction === `complete:${data.focus_tasks[rank - 1].id}`"
              :flash="rewardFlash?.id === data.focus_tasks[rank - 1].id ? rewardFlash.text : ''"
              @complete="handleComplete"
            />
            <button v-else type="button" class="focus-slot-empty" :disabled="busy" @click="openFocus">
              <span aria-hidden="true">＋</span>选择重点
            </button>
          </div>
        </div>

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
            :key="task.id" :task="task" :busy="busy" :pending="pendingAction === `complete:${task.id}`"
            :flash="rewardFlash?.id === task.id ? rewardFlash.text : ''" @complete="handleComplete" />
          <p v-if="!data.task_groups[group.key].length" class="muted group-empty">{{ group.empty }}</p>
          <button v-if="data.task_groups[group.key].length > 5" class="more-button" type="button"
            :aria-expanded="Boolean(expandedGroups[group.key])" @click="expandedGroups[group.key] = !expandedGroups[group.key]">
            {{ expandedGroups[group.key] ? '收起' : `查看全部 ${data.task_groups[group.key].length} 项` }}
          </button>
        </section>
      </div>
      <footer class="workbench-footer">
        <span class="muted">完成任务会即时结算修为与灵石。</span>
        <router-link to="/todos">管理全部待办 →</router-link>
      </footer>
    </template>
    <div v-else-if="!loading && !loadError" class="message error-message" role="alert">
      工作台没有返回可显示的数据。
      <button type="button" :disabled="busy" @click="load()">重试加载</button>
    </div>
    <!-- Cultivation Retreat Modal -->
    <CultivationRetreatModal
      v-model="showRetreatModal"
      :todo-item="retreatSelectedTodo"
      @completed="load()"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import { todoService } from '../../services/todo'
import { useAuthStore } from '../../stores/auth'
import { useCultivationStore } from '../../stores/cultivation'
import { todayChinaDateKey } from '../../utils/dateTime'
import { labelFromServer, labelResource } from '../../utils/displayLabels'
import { useDailyWorkbench } from '../../composables/useDailyWorkbench'
import WorkbenchTaskRow from './WorkbenchTaskRow.vue'
import CultivationRetreatModal from '../retreat/CultivationRetreatModal.vue'

const showRetreatModal = ref(false)
const retreatSelectedTodo = ref(null)

function openRetreatModal(todo = null) {
  retreatSelectedTodo.value = todo
  showRetreatModal.value = true
}

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
const focusProgress = computed(() => {
  if (!data.value) return '0'
  const total = data.value.focus_tasks.length
  return total ? `${data.value.summary.focus_completed}/${total}` : '未选'
})
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

/*
 * The reward for a completion is only ever the difference between two
 * authoritative cultivation snapshots, so the flash can never invent a number
 * the server did not settle.
 */
const rewardFlash = ref(null)
let flashTimer = null

function snapshotResources() {
  const overview = cultivationStore.overview
  return {
    cultivation: Number(overview?.cultivation ?? 0),
    spiritStones: Number(overview?.spirit_stones ?? 0)
  }
}

function flashReward(taskId, before) {
  const after = snapshotResources()
  const parts = []
  const cultivationGain = after.cultivation - before.cultivation
  const stoneGain = after.spiritStones - before.spiritStones
  if (cultivationGain > 0) parts.push(`+${cultivationGain} ${labelFromServer(cultivationStore.overview, 'cultivation_label', 'cultivation', labelResource)}`)
  if (stoneGain > 0) parts.push(`+${stoneGain} ${labelFromServer(cultivationStore.overview, 'spirit_stones_label', 'spirit_stones', labelResource)}`)
  if (!parts.length) return
  rewardFlash.value = { id: taskId, text: parts.join(' · ') }
  clearTimeout(flashTimer)
  flashTimer = setTimeout(() => { rewardFlash.value = null }, 3600)
}

async function handleComplete(task) {
  if (!task) return
  const before = snapshotResources()
  const completed = await completeTask(task)
  if (completed) flashReward(task.id, before)
}

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
  clearTimeout(flashTimer)
  window.removeEventListener('focus', refreshVisible)
  document.removeEventListener('visibilitychange', refreshVisible)
})

defineExpose({ focusQuickAdd: () => titleInput.value?.focus() })
</script>

<style scoped>
.today-workbench {
  padding: clamp(18px, 2.4vw, 32px);
  color: var(--color-text);
  background: #FFFFFF;
  border: 0;
  border-radius: 26px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 18px 40px -28px rgba(15, 23, 42, 0.35);
  margin-bottom: var(--page-gap);
  min-width: 0;
}
.workbench-header, .section-heading, .workbench-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.workbench-header { align-items: flex-start; }
.eyebrow { margin: 0 0 6px; color: var(--rank-1-accent); font-size: 11.5px; font-weight: 700; letter-spacing: .06em; }
h2 { margin: 0 0 6px; font-size: clamp(21px, 3.2vw, 26px); letter-spacing: -0.01em; }
h3 { margin: 0; font-size: 15px; font-weight: 650; letter-spacing: -0.005em; }
.muted { color: var(--home-ink-tertiary); font-size: 13px; line-height: 1.6; margin: 4px 0 0; }
button, input, select { font: inherit; }
button {
  border: 1px solid var(--home-hairline);
  background: #FFFFFF;
  color: var(--color-text);
  min-height: 44px;
  padding: 8px 14px;
  border-radius: 12px;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 160ms ease, border-color 160ms ease;
}
button:hover:not(:disabled) { background: var(--home-soft); }
button:disabled { opacity: .55; cursor: not-allowed; }
button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible { outline: 2px solid var(--rank-1-accent); outline-offset: 3px; }
.ghost-button { background: transparent; border-color: transparent; color: var(--home-ink-tertiary); }
input:not([type=checkbox]), select {
  box-sizing: border-box;
  width: 100%;
  min-height: 44px;
  min-width: 0;
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 10px 14px;
  background: var(--home-soft);
  color: var(--color-text);
  transition: background 160ms ease, border-color 160ms ease;
}
input:not([type=checkbox]):focus, select:focus { background: #FFFFFF; border-color: rgba(15, 138, 103, 0.35); }
label { display: block; font-size: 13px; margin-bottom: 6px; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.primary-button { background: var(--rank-1-accent); color: #FFFFFF; border-color: transparent; font-weight: 600; }
.primary-button:hover:not(:disabled) { background: #0B7357; }

.workbench-metrics {
  display: flex;
  align-items: stretch;
  gap: 0;
  margin: 22px 0 18px;
  padding: 4px 0;
}
.workbench-metric {
  flex: 1 1 0;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px 8px;
  padding: 4px 18px;
  min-height: 46px;
  border-left: 1px solid var(--home-hairline);
}
.workbench-metric:first-child { padding-left: 0; border-left: 0; }
.workbench-metric .metric-figure { font-size: 22px; font-weight: 650; letter-spacing: -0.02em; }
.workbench-metric-label { width: 100%; color: var(--home-ink-tertiary); font-size: 12px; }
.metric-glyph { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; align-self: center; }
.metric-glyph--done { background: var(--rank-1-chip); box-shadow: inset 0 0 0 1px rgba(15, 138, 103, .28); }
.metric-glyph--due { background: var(--rank-2-chip); box-shadow: inset 0 0 0 1px rgba(169, 105, 15, .26); }
.metric-glyph--late { background: #FBE0DE; box-shadow: inset 0 0 0 1px rgba(180, 35, 24, .24); }
.metric-glyph--focus { background: var(--rank-3-chip); box-shadow: inset 0 0 0 1px rgba(158, 68, 121, .24); }

.quick-task-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 16px;
  background: var(--home-soft);
}
.quick-task-form > input:not([type=date]) { flex: 1 1 260px; background: transparent; }
.quick-task-form > select { flex: 0 0 auto; width: auto; min-width: 132px; background: #FFFFFF; }
.quick-task-form > input[type=date] { flex: 0 0 auto; width: auto; background: #FFFFFF; }
.quick-task-form > input:not([type=date]):focus { background: #FFFFFF; }
.quick-task-form > .primary-button { margin-left: auto; }
.message { font-size: 13.5px; line-height: 1.7; padding: 10px 12px; border-radius: 12px; background: var(--home-soft); overflow-wrap: anywhere; }
.error-message { color: #b42318; }
.success-message { color: #157347; }
.warning-message { color: #855400; }
.message button { margin-left: 10px; }

.reward-flash {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 12px 0 0;
  padding: 7px 14px;
  border-radius: 999px;
  background: var(--rank-1-bg);
  color: var(--rank-1-accent);
  font-size: 13px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.reward-flash-mark { font-size: 12px; }
.reward-enter-active, .reward-leave-active { transition: opacity 220ms ease, transform 220ms cubic-bezier(0.22, 1, 0.36, 1); }
.reward-enter-from, .reward-leave-to { opacity: 0; transform: translateY(-4px); }

.focus-section { margin: 26px 0 8px; }
.focus-tasks { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }
.focus-task-card {
  border: 0;
  border-radius: 18px;
  padding: 14px 16px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.focus-task-card--1 { background: var(--rank-1-bg); }
.focus-task-card--2 { background: var(--rank-2-bg); }
.focus-task-card--3 { background: var(--rank-3-bg); }
.focus-task-card--1 .focus-rank { color: var(--rank-1-accent); }
.focus-task-card--2 .focus-rank { color: var(--rank-2-accent); }
.focus-task-card--3 .focus-rank { color: var(--rank-3-accent); }
.focus-rank { display: inline-flex; align-items: center; gap: 7px; font-size: 11.5px; font-weight: 700; letter-spacing: .02em; }
.focus-rank i {
  font-style: normal;
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.75);
  font-size: 11px;
}
.focus-slot-empty {
  min-height: 52px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px dashed rgba(15, 23, 42, 0.12);
  color: var(--home-ink-tertiary);
  width: 100%;
  font-size: 13px;
}
.focus-editor { padding: 18px; margin-top: 16px; border-radius: 18px; background: var(--home-soft); }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
legend { font-size: 14px; font-weight: 600; padding: 0 0 12px; }
.draft-order { padding-left: 22px; }
.draft-order li { margin-bottom: 8px; }
.draft-order li > span { overflow-wrap: anywhere; }
.order-actions { display: inline-flex; gap: 6px; margin-left: 10px; }
.order-actions button { min-width: 44px; }
.focus-options { max-height: 260px; overflow-y: auto; margin: 12px 0; }
.focus-option { display: flex; align-items: center; gap: 10px; min-height: 44px; cursor: pointer; overflow-wrap: anywhere; }
.focus-option input { width: 18px; height: 18px; flex-shrink: 0; accent-color: var(--rank-1-accent); }
.focus-option small { color: var(--home-ink-tertiary); }
.editor-actions { display: flex; justify-content: flex-end; gap: 10px; }

.task-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 40px; margin-top: 20px; }
.task-group { padding: 18px 0 6px; border-top: 1px solid var(--home-hairline); min-width: 0; }
.task-group .section-heading { margin-bottom: 6px; }
.group-count { font-size: 12px; color: var(--home-ink-tertiary); background: var(--home-soft); padding: 2px 9px; border-radius: 999px; font-variant-numeric: tabular-nums; }
.group-empty { padding: 10px 0; }
.more-button { width: 100%; color: var(--rank-1-accent); background: transparent; border-color: transparent; margin-top: 4px; }
.workbench-footer { margin-top: 22px; padding-top: 16px; border-top: 1px solid var(--home-hairline); }
.workbench-footer a { color: var(--rank-1-accent); font-size: 13.5px; font-weight: 600; flex-shrink: 0; }
.header-actions { display: flex; align-items: center; gap: 6px; }
.retreat-trigger-btn {
  background: var(--rank-1-bg);
  border: 1px solid transparent;
  color: var(--rank-1-accent);
  font-weight: 600;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.retreat-trigger-btn:hover:not(:disabled) { background: var(--rank-1-chip); }

@media (max-width: 900px) { .focus-tasks { grid-template-columns: 1fr; } }
@media (max-width: 600px) {
  .today-workbench { border-radius: 20px; padding: 16px; }
  .workbench-header { flex-wrap: nowrap; align-items: flex-start; gap: 8px; }
  .workbench-header h2 { font-size: 20px; }
  .header-actions { width: auto; gap: 4px; flex-wrap: nowrap; }
  .header-actions button { padding: 6px 10px; font-size: 12.5px; }
  .task-groups { grid-template-columns: 1fr; gap: 2px; }
  .task-group { padding: 14px 0 4px; }
  .workbench-metrics { flex-wrap: nowrap; gap: 0; margin: 16px 0 12px; }
  .workbench-metric { flex: 1 1 0; padding: 0 8px; min-width: 0; }
  .workbench-metric:first-child { border-left: 0; padding-left: 0; }
  .workbench-metric .metric-figure { font-size: 18px; }
  .workbench-metric-label { font-size: 10.5px; white-space: nowrap; }
  .metric-glyph { display: none; }
  .quick-task-form { padding: 8px; gap: 6px; flex-wrap: wrap; }
  .quick-task-form > input:not([type=date]) { flex: 1 1 auto; background: #FFFFFF; padding: 10px 12px; }
  .quick-task-form > select { flex: 0 0 auto; width: auto; min-width: 0; max-width: 116px; padding: 10px 6px; }
  .quick-task-form > input[type=date] { flex: 1 1 100%; }
  .quick-task-form > .primary-button { flex: 0 0 auto; width: auto; margin-left: 0; padding: 10px 16px; }
  .focus-task-card { padding: 10px 12px; gap: 4px; border-radius: 14px; }
  .focus-rank { font-size: 11px; }
  .focus-slot-empty { min-height: 44px; }
  .section-heading, .workbench-footer { align-items: flex-start; flex-wrap: wrap; }
  .order-actions { display: flex; margin: 6px 0 0; }
  button, input:not([type=checkbox]), select, .focus-option { min-height: 48px; }
  input:not([type=checkbox]), select { font-size: 16px; }
}

.retreat-icon { width: 14px; height: 14px; vertical-align: -2px; }
</style>
