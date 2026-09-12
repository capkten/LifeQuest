<template>
  <Teleport to="body">
    <div v-if="visible" class="history-overlay" @click.self="close" @keydown.esc="close">
      <section class="history-dialog" role="dialog" aria-modal="true" aria-labelledby="habit-history-title">
        <header class="history-header">
          <div>
            <p class="history-kicker">习惯记录</p>
            <h2 id="habit-history-title">{{ habit?.title }}</h2>
            <p class="history-subtitle">中国时间 · 记录可追溯，补记不重复发放奖励</p>
          </div>
          <button type="button" class="icon-button" aria-label="关闭习惯记录" title="关闭" @click="close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>

        <div class="history-body">
          <div class="history-metrics" aria-label="习惯累计统计">
            <div><strong>{{ habit?.total_completed || 0 }}</strong><span>累计完成</span></div>
            <div><strong>{{ habit?.streak || 0 }}</strong><span>当前连续</span></div>
            <div><strong>{{ habit?.best_streak || 0 }}</strong><span>最佳连续</span></div>
            <div><strong>{{ formatRate(habit?.completion_rate) }}%</strong><span>计划完成率</span></div>
          </div>

          <div v-if="error" class="history-error" role="alert">
            <span>{{ error }}</span>
            <button type="button" @click="loadHistory">重试</button>
          </div>
          <div v-if="message" class="history-message" role="status">{{ message }}</div>

          <section v-if="history" class="history-section" aria-labelledby="history-calendar-title">
            <div class="history-section-heading">
              <div>
                <h3 id="history-calendar-title">最近记录</h3>
                <p>{{ history.start_on }} 至 {{ history.end_on }} · {{ history.completed_count }}/{{ history.scheduled_count }} 个{{ historyTargetLabel }}</p>
              </div>
              <span class="rate-badge">{{ formatRate(history.completion_rate) }}%</span>
            </div>
            <div class="history-week-labels" aria-hidden="true">
              <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
            </div>
            <div class="history-grid" aria-label="习惯历史热力图">
              <span
                v-for="day in heatmapDays"
                :key="day.placeholder ? day.key : day.date"
                class="history-day"
                :class="day.placeholder ? 'history-day--empty' : dayClass(day)"
                :title="day.placeholder ? '' : dayTitle(day)"
                :aria-hidden="day.placeholder ? 'true' : undefined"
              ></span>
            </div>
            <div class="history-legend" aria-label="热力图图例">
              <span><i class="legend-dot legend-dot--done"></i>已完成</span>
              <span><i class="legend-dot legend-dot--planned"></i>待完成</span>
              <span><i class="legend-dot legend-dot--excused"></i>请假</span>
              <span><i class="legend-dot legend-dot--paused"></i>暂停</span>
            </div>
          </section>

          <div class="history-actions">
            <section class="history-form-section" aria-labelledby="history-checkin-title">
              <div class="history-section-heading">
                <div>
                  <h3 id="history-checkin-title">今天打卡</h3>
                  <p>可选填写本次行动的备注。</p>
                </div>
              </div>
              <textarea
                v-model="todayNote"
                class="history-textarea"
                maxlength="500"
                rows="3"
                placeholder="例如：完成了 30 分钟训练"
                :disabled="busy"
              ></textarea>
              <button
                type="button"
                class="primary-button"
                :disabled="busy"
                :aria-disabled="!canCompleteToday"
                :title="todayBlockedReason"
                @click="completeToday"
              >
                {{ completing ? '提交中...' : (habit?.completed_today ? '今天已完成' : todayBlockedReason) }}
              </button>
              <p v-if="!canCompleteToday" class="history-blocked-reason">{{ todayBlockedReason }}</p>
            </section>

            <section class="history-form-section" aria-labelledby="history-leave-title">
              <div class="history-section-heading">
                <div>
                  <h3 id="history-leave-title">安排请假</h3>
                  <p>恢复日期当天重新纳入计划。</p>
                </div>
              </div>
              <div class="history-form-grid">
                <label>请假开始<input v-model="leaveForm.leave_on" type="date" :min="today" :disabled="busy" /></label>
                <label>恢复日期<input v-model="leaveForm.return_on" type="date" :min="leaveForm.leave_on || today" :disabled="busy" /></label>
              </div>
              <input v-model="leaveForm.reason" class="history-input" maxlength="500" placeholder="可选原因" :disabled="busy" />
              <button type="button" class="secondary-button" :disabled="busy" @click="submitLeave">
                {{ action === 'leave' ? '保存中...' : '保存请假区间' }}
              </button>
            </section>
          </div>

          <section class="history-form-section" aria-labelledby="history-backfill-title">
            <div class="history-section-heading">
              <div>
                <h3 id="history-backfill-title">补记过去的完成</h3>
                <p>仅支持最近 90 天的计划日；补记不会补发金币或经验。</p>
              </div>
            </div>
            <div class="history-form-grid history-form-grid--backfill">
              <label for="habit-backfill-date">完成日期</label>
              <input id="habit-backfill-date" v-model="backfillForm.completed_on" type="date" :min="backfillMin" :max="yesterday" :disabled="busy" />
              <label for="habit-backfill-note">补记备注</label>
              <textarea id="habit-backfill-note" v-model="backfillForm.note" class="history-textarea" maxlength="500" rows="2" placeholder="可选备注" :disabled="busy"></textarea>
            </div>
            <button type="button" class="secondary-button" :disabled="busy" @click="submitBackfill">
              {{ action === 'backfill' ? '保存中...' : '保存补记' }}
            </button>
          </section>

          <section v-if="habit?.leave_intervals?.length" class="history-form-section" aria-labelledby="history-leave-list-title">
            <div class="history-section-heading">
              <div>
                <h3 id="history-leave-list-title">已安排的请假</h3>
                <p>删除后，覆盖的计划日会恢复为待完成。</p>
              </div>
            </div>
            <ul class="leave-list">
              <li v-for="interval in habit.leave_intervals" :key="interval.id">
                <span>{{ interval.leave_on }} 至 {{ interval.return_on }}{{ interval.reason ? ` · ${interval.reason}` : '' }}</span>
                <button type="button" class="text-button" :disabled="busy" @click="removeLeave(interval.id)">撤销</button>
              </li>
            </ul>
          </section>

          <div v-if="loading" class="history-loading" role="status">正在加载历史记录...</div>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { todoService } from '../services/todo'
import { getErrorMessage } from '../utils/errorMessage'
import { chinaDateKey, shiftDateKey, weekdayForDateKey } from '../utils/dateTime'

const props = defineProps({
  visible: Boolean,
  habit: { type: Object, default: null },
  completing: Boolean,
})

const emit = defineEmits(['close', 'complete', 'updated'])

const history = ref(null)
const loading = ref(false)
const action = ref('')
const error = ref('')
const message = ref('')
const todayNote = ref('')
const leaveForm = ref({ leave_on: '', return_on: '', reason: '' })
const backfillForm = ref({ completed_on: '', note: '' })
let historyRequestId = 0

const today = computed(() => chinaDateKey(new Date()) || '')
const yesterday = computed(() => shiftDateKey(today.value, -1))
const backfillMin = computed(() => shiftDateKey(today.value, -90))
const historyTargetLabel = computed(() => (
  props.habit?.frequency === 'weekly_target' ? '计划槽位' : '计划日'
))
const heatmapDays = computed(() => {
  if (!history.value?.days?.length) return []
  const mondayOffset = weekdayForDateKey(history.value.days[0].date) ?? 0
  const placeholders = Array.from({ length: mondayOffset }, (_, index) => ({
    key: `empty-${index}`,
    placeholder: true,
  }))
  return [...placeholders, ...history.value.days]
})
const busy = computed(() => loading.value || Boolean(action.value) || props.completing)
const canCompleteToday = computed(() => Boolean(
  props.habit
  && props.habit.is_active
  && !props.habit.completed_today
  && !props.habit.paused_today
  && !props.habit.excused_today
  && props.habit.scheduled_today
  && (props.habit.frequency !== 'weekly_target' || props.habit.weekly_remaining > 0)
))
const todayBlockedReason = computed(() => {
  if (props.habit?.completed_today) return '今天已完成'
  if (props.habit?.paused_today) return '习惯已暂停'
  if (props.habit?.excused_today) return '今天已请假'
  if (props.habit?.frequency === 'weekly_target' && props.habit.weekly_remaining <= 0) return '本周已完成目标次数'
  if (!props.habit?.scheduled_today) return '今天不是计划日'
  return '今天打卡并保存'
})

function resetForms() {
  leaveForm.value = { leave_on: today.value, return_on: shiftDateKey(today.value, 1), reason: '' }
  backfillForm.value = { completed_on: yesterday.value, note: '' }
  todayNote.value = ''
  error.value = ''
  message.value = ''
}

async function loadHistory() {
  const habitId = props.habit?.id
  if (!props.visible || !habitId) return
  const requestId = ++historyRequestId
  if (props.visible && props.habit?.id === habitId && requestId === historyRequestId) {
    loading.value = true
    error.value = ''
  }
  try {
    const nextHistory = await todoService.getHabitHistory(habitId)
    if (props.visible && props.habit?.id === habitId && requestId === historyRequestId) {
      history.value = nextHistory
    }
  } catch (requestError) {
    if (props.visible && props.habit?.id === habitId && requestId === historyRequestId) {
      error.value = getErrorMessage(requestError, '习惯历史加载失败，请重试。')
    }
  } finally {
    if (props.visible && props.habit?.id === habitId && requestId === historyRequestId) {
      loading.value = false
    }
  }
}

function close() {
  if (!busy.value) {
    historyRequestId += 1
    emit('close')
  }
}

function completeToday() {
  if (!canCompleteToday.value || busy.value) return
  emit('complete', { note: todayNote.value.trim() || undefined })
}

async function submitLeave() {
  if (busy.value) return
  if (!leaveForm.value.leave_on || !leaveForm.value.return_on) {
    error.value = '请选择请假开始日期和恢复日期。'
    return
  }
  if (leaveForm.value.return_on <= leaveForm.value.leave_on) {
    error.value = '恢复日期必须晚于请假开始日期。'
    return
  }
  action.value = 'leave'
  error.value = ''
  const nextLeaveOn = leaveForm.value.return_on
  try {
    const updated = await todoService.createHabitLeave(props.habit.id, {
      leave_on: leaveForm.value.leave_on,
      return_on: leaveForm.value.return_on,
      reason: leaveForm.value.reason.trim() || undefined,
    })
    emit('updated', updated)
    leaveForm.value = { leave_on: nextLeaveOn, return_on: shiftDateKey(nextLeaveOn, 1), reason: '' }
    message.value = '请假区间已保存。'
    await loadHistory()
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    action.value = ''
  }
}

async function removeLeave(leaveId) {
  if (busy.value) return
  action.value = `remove-leave:${leaveId}`
  error.value = ''
  try {
    const updated = await todoService.deleteHabitLeave(props.habit.id, leaveId)
    emit('updated', updated)
    message.value = '请假记录已撤销。'
    await loadHistory()
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    action.value = ''
  }
}

async function submitBackfill() {
  if (busy.value) return
  if (!backfillForm.value.completed_on) {
    error.value = '请选择需要补记的日期。'
    return
  }
  action.value = 'backfill'
  error.value = ''
  try {
    const updated = await todoService.backfillHabit(props.habit.id, {
      completed_on: backfillForm.value.completed_on,
      note: backfillForm.value.note.trim() || undefined,
    })
    emit('updated', updated)
    message.value = '补记已保存，不会重复发放奖励。'
    backfillForm.value = { completed_on: yesterday.value, note: '' }
    await loadHistory()
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    action.value = ''
  }
}

function formatRate(value) {
  return Number(value || 0).toFixed(1).replace('.0', '')
}

function dayClass(day) {
  return {
    'history-day--done': day.completed,
    'history-day--planned': day.scheduled && !day.completed,
    'history-day--excused': day.excused,
    'history-day--paused': day.paused,
    'history-day--makeup': day.completed && day.is_makeup,
  }
}

function dayTitle(day) {
  if (day.completed) return `${day.date} · ${day.is_makeup ? '补记完成' : '已完成'}${day.note ? ` · ${day.note}` : ''}`
  if (day.excused) return `${day.date} · 请假`
  if (day.paused) return `${day.date} · 暂停`
  if (day.scheduled) return `${day.date} · 待完成`
  return `${day.date} · 非计划日`
}

watch(() => props.visible, (visible) => {
  if (visible) {
    resetForms()
    loadHistory()
  } else {
    historyRequestId += 1
  }
})

watch(() => props.habit?.id, (habitId, previousHabitId) => {
  if (habitId === previousHabitId) return
  historyRequestId += 1
  if (props.visible && habitId) {
    resetForms()
    loadHistory()
  }
})

watch(() => props.habit?.last_completed_at, (current, previous) => {
  if (props.visible && current !== previous) loadHistory()
})

onMounted(() => {
  if (props.visible) {
    resetForms()
    loadHistory()
  }
})
</script>

<style scoped>
.history-overlay { position: fixed; inset: 0; z-index: 1200; display: grid; place-items: center; padding: 16px; background: rgba(2, 6, 23, .66); }
.history-dialog { width: min(780px, 100%); max-height: min(900px, 92dvh); overflow: hidden; border: 1px solid var(--color-border); border-radius: 16px; background: var(--color-card); color: var(--color-text); box-shadow: var(--shadow-xl); }
.history-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 22px 24px; border-bottom: 1px solid var(--color-border); }
.history-kicker { margin: 0 0 5px; color: var(--color-primary); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
.history-header h2 { margin: 0; font-size: 22px; line-height: 1.25; }
.history-subtitle, .history-section-heading p { margin: 5px 0 0; color: var(--color-text-secondary); font-size: 12px; line-height: 1.5; }
.icon-button { display: inline-grid; flex: 0 0 auto; place-items: center; width: 40px; height: 40px; border: 1px solid var(--color-border); border-radius: 9px; color: var(--color-text-secondary); background: transparent; cursor: pointer; }
.icon-button:hover, .icon-button:focus-visible { color: var(--color-text); background: var(--color-bg-secondary); outline: 2px solid rgba(14, 165, 233, .2); outline-offset: 2px; }
.icon-button svg { width: 19px; height: 19px; }
.history-body { max-height: calc(min(900px, 92dvh) - 85px); overflow-y: auto; padding: 20px 24px 24px; }
.history-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 20px; }
.history-metrics > div { display: grid; gap: 4px; min-width: 0; padding: 13px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-secondary); }
.history-metrics strong { overflow: hidden; color: var(--color-text); font-size: 22px; text-overflow: ellipsis; white-space: nowrap; }
.history-metrics span { color: var(--color-text-secondary); font-size: 11px; }
.history-section, .history-form-section { padding: 16px 0; border-top: 1px solid var(--color-border); }
.history-section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.history-section-heading h3 { margin: 0; font-size: 15px; }
.history-blocked-reason { margin: -4px 0 0; color: var(--color-text-secondary); font-size: 12px; line-height: 1.5; }
.rate-badge { flex: 0 0 auto; padding: 4px 8px; border-radius: 999px; color: var(--color-success); background: rgba(81, 207, 102, .12); font-size: 12px; font-weight: 800; }
.history-week-labels, .history-grid { display: grid; grid-template-columns: repeat(7, minmax(20px, 1fr)); gap: 5px; }
.history-week-labels { margin-bottom: 5px; color: var(--color-text-tertiary); font-size: 10px; text-align: center; }
.history-day { aspect-ratio: 1; min-width: 0; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-bg-secondary); }
.history-day--planned { border-color: rgba(14, 165, 233, .45); background: rgba(14, 165, 233, .16); }
.history-day--done { border-color: rgba(81, 207, 102, .65); background: var(--color-success); }
.history-day--makeup { border-style: dashed; }
.history-day--excused { border-color: rgba(255, 217, 61, .65); background: rgba(255, 217, 61, .26); }
.history-day--paused { border-color: rgba(156, 163, 175, .6); background: rgba(156, 163, 175, .2); }
.history-day--empty { visibility: hidden; border-color: transparent; background: transparent; }
.history-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; color: var(--color-text-secondary); font-size: 11px; }
.history-legend span { display: inline-flex; align-items: center; gap: 5px; }
.legend-dot { width: 10px; height: 10px; border: 1px solid var(--color-border); border-radius: 3px; background: var(--color-bg-secondary); }
.legend-dot--done { border-color: rgba(81, 207, 102, .65); background: var(--color-success); }
.legend-dot--planned { border-color: rgba(14, 165, 233, .45); background: rgba(14, 165, 233, .16); }
.legend-dot--excused { border-color: rgba(255, 217, 61, .65); background: rgba(255, 217, 61, .26); }
.legend-dot--paused { border-color: rgba(156, 163, 175, .6); background: rgba(156, 163, 175, .2); }
.history-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.history-form-section { display: grid; gap: 11px; }
.history-actions .history-form-section { min-width: 0; }
.history-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.history-form-grid--backfill { align-items: end; }
.history-form-grid label { display: grid; gap: 5px; color: var(--color-text-secondary); font-size: 12px; }
.history-input, .history-textarea, .history-form-grid input { width: 100%; box-sizing: border-box; padding: 9px 10px; border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text); background: var(--color-bg-secondary); font: inherit; font-size: 13px; }
.history-textarea { resize: vertical; min-height: 68px; }
.history-input:focus, .history-textarea:focus, .history-form-grid input:focus { border-color: var(--color-primary); outline: 2px solid rgba(14, 165, 233, .15); outline-offset: 1px; }
.primary-button, .secondary-button, .text-button, .history-error button { min-height: 40px; padding: 8px 13px; border-radius: 8px; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; }
.primary-button { border: 1px solid var(--color-primary); color: #fff; background: var(--color-primary); }
.secondary-button { border: 1px solid var(--color-border); color: var(--color-text); background: var(--color-bg-secondary); }
.primary-button:hover:not(:disabled), .secondary-button:hover:not(:disabled) { border-color: var(--color-primary); }
.primary-button:disabled, .secondary-button:disabled, .text-button:disabled { cursor: not-allowed; opacity: .55; }
.history-error, .history-message { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 12px; border-radius: 8px; font-size: 13px; line-height: 1.5; }
.history-error { color: var(--color-error-dark, #b42318); background: rgba(239, 68, 68, .08); }
.history-message { color: var(--color-success-dark, #157347); background: rgba(81, 207, 102, .1); }
.history-error button { min-height: 32px; border: 1px solid currentColor; color: inherit; background: transparent; }
.leave-list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.leave-list li { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 10px; border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-secondary); font-size: 12px; line-height: 1.5; }
.text-button { min-height: 32px; flex: 0 0 auto; border: 1px solid var(--color-border); color: var(--color-error-dark, #b42318); background: transparent; }
.history-loading { padding: 18px 0 4px; color: var(--color-text-secondary); text-align: center; font-size: 13px; }
@media (max-width: 620px) {
  .history-overlay { padding: 8px; }
  .history-header { padding: 18px 16px; }
  .history-body { padding: 16px; }
  .history-metrics { gap: 7px; }
  .history-metrics > div { padding: 10px 8px; }
  .history-metrics strong { font-size: 18px; }
  .history-metrics span { font-size: 10px; }
  .history-actions { grid-template-columns: 1fr; gap: 0; }
  .history-grid, .history-week-labels { gap: 4px; }
  .leave-list li { align-items: flex-start; }
}
</style>
