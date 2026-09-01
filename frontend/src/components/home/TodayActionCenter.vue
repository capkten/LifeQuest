<template>
  <section class="today-action-center" aria-labelledby="today-action-title">
    <header class="today-action-header">
      <div>
        <span class="today-action-kicker">今日行动</span>
        <h2 id="today-action-title">先完成最重要的一件事</h2>
        <p v-if="data" class="today-action-summary">
          {{ data.summary.open_count }} 个待处理事项，{{ data.summary.completed_count }} 个事项已完成
        </p>
      </div>
      <router-link to="/todos" class="today-action-link">管理待办</router-link>
    </header>

    <div v-if="loading && !data" class="today-action-state" aria-live="polite">
      <span class="loading-spinner"></span>
      <span>正在整理今天的行动...</span>
    </div>

    <div v-else-if="error && !data" class="today-action-state today-action-state--error" role="alert">
      <p>{{ errorText }}</p>
      <button type="button" class="retry-btn" @click="$emit('retry')">重试</button>
    </div>

    <template v-else-if="data">
      <div class="today-action-metrics" aria-label="今日行动统计">
        <div class="today-action-metric">
          <strong>{{ data.summary.open_count }}</strong>
          <span>待处理</span>
        </div>
        <div class="today-action-metric today-action-metric--danger">
          <strong>{{ data.summary.overdue_count }}</strong>
          <span>已逾期</span>
        </div>
        <div class="today-action-metric today-action-metric--success">
          <strong>{{ data.summary.habit_completed_count }}/{{ data.summary.habit_due_count }}</strong>
          <span>习惯完成</span>
        </div>
      </div>

      <div v-if="error" class="today-action-inline-error" role="alert" aria-live="polite">
        <span>{{ errorText }}</span>
        <button type="button" @click="$emit('retry')">重新加载</button>
      </div>

      <div v-if="data.next_action" class="today-next-action">
        <div>
          <span class="today-next-action-label">下一步</span>
          <strong>{{ data.next_action.title }}</strong>
        </div>
        <button
          type="button"
          class="today-next-action-button"
          :disabled="data.next_action.action === 'complete' && completingKey !== null"
          @click="handleItem(data.next_action)"
        >
          {{ data.next_action.action === 'complete' ? '完成' : '查看' }}
        </button>
      </div>

      <div v-if="hasActions" class="today-action-sections">
        <section v-if="data.sections.overdue.length" class="today-action-group" aria-labelledby="overdue-actions-title">
          <div class="today-action-group-heading">
            <h3 id="overdue-actions-title">逾期事项</h3>
            <span>{{ data.sections.overdue.length }}</span>
          </div>
          <div class="today-action-list">
            <article v-for="item in data.sections.overdue" :key="itemKey(item)" class="today-action-item today-action-item--overdue">
              <button
                v-if="item.action === 'complete'"
                type="button"
                class="today-action-check"
                :disabled="completingKey !== null"
                :aria-label="`完成 ${item.title}`"
                @click="handleItem(item)"
              >
                <span v-if="isCompleting(item)" class="loading-spinner loading-spinner--sm"></span>
                <span v-else aria-hidden="true"></span>
              </button>
              <div class="today-action-item-copy">
                <strong>{{ item.title }}</strong>
                <span>{{ itemMeta(item) }}</span>
              </div>
              <button v-if="item.action === 'open'" type="button" class="today-action-item-open" @click="handleItem(item)">查看</button>
            </article>
          </div>
        </section>

        <section v-if="data.sections.today.length" class="today-action-group" aria-labelledby="today-actions-title">
          <div class="today-action-group-heading">
            <h3 id="today-actions-title">今天安排</h3>
            <span>{{ data.sections.today.length }}</span>
          </div>
          <div class="today-action-list">
            <article v-for="item in data.sections.today" :key="itemKey(item)" class="today-action-item">
              <button
                v-if="item.action === 'complete'"
                type="button"
                class="today-action-check"
                :disabled="completingKey !== null"
                :aria-label="`完成 ${item.title}`"
                @click="handleItem(item)"
              >
                <span v-if="isCompleting(item)" class="loading-spinner loading-spinner--sm"></span>
                <span v-else aria-hidden="true"></span>
              </button>
              <div class="today-action-item-copy">
                <strong>{{ item.title }}</strong>
                <span>{{ itemMeta(item) }}</span>
              </div>
              <button v-if="item.action === 'open'" type="button" class="today-action-item-open" @click="handleItem(item)">查看</button>
            </article>
          </div>
        </section>

        <section v-if="data.sections.habits.length" class="today-action-group" aria-labelledby="habit-actions-title">
          <div class="today-action-group-heading">
            <h3 id="habit-actions-title">今日习惯</h3>
            <span>{{ data.summary.habit_completed_count }}/{{ data.summary.habit_due_count }}</span>
          </div>
          <div class="today-action-list">
            <article
              v-for="item in data.sections.habits"
              :key="itemKey(item)"
              class="today-action-item"
              :class="{ 'today-action-item--done': item.completed }"
            >
              <button
                v-if="!item.completed"
                type="button"
                class="today-action-check"
                :disabled="completingKey !== null"
                :aria-label="`完成 ${item.title}`"
                @click="handleItem(item)"
              >
                <span v-if="isCompleting(item)" class="loading-spinner loading-spinner--sm"></span>
                <span v-else aria-hidden="true"></span>
              </button>
              <span v-else class="today-action-check today-action-check--done" aria-label="已完成">✓</span>
              <div class="today-action-item-copy">
                <strong>{{ item.title }}</strong>
                <span>{{ item.completed ? '今天已完成' : `连续 ${item.streak || 0} 天` }}</span>
              </div>
            </article>
          </div>
        </section>

        <section v-if="data.sections.calendar.length" class="today-action-group" aria-labelledby="calendar-actions-title">
          <div class="today-action-group-heading">
            <h3 id="calendar-actions-title">日程节点</h3>
            <span>{{ data.sections.calendar.length }}</span>
          </div>
          <div class="today-action-list">
            <article v-for="item in data.sections.calendar" :key="itemKey(item)" class="today-action-item">
              <span class="today-action-symbol today-action-symbol--goal" aria-hidden="true">◎</span>
              <div class="today-action-item-copy">
                <strong>{{ item.title }}</strong>
                <span>{{ item.progress == null ? '打开目标查看进度' : `目标进度 ${Math.round(item.progress)}%` }}</span>
              </div>
              <button type="button" class="today-action-item-open" @click="handleItem(item)">查看</button>
            </article>
          </div>
        </section>
      </div>

      <div v-else class="today-action-empty">
        <strong>今天没有需要处理的事项</strong>
        <span>为自己安排一个小目标，保持行动节奏。</span>
        <router-link to="/todos" class="today-action-empty-link">创建任务</router-link>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { getErrorMessage } from '../../utils/errorMessage'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: [Object, String], default: null },
  completingKey: { type: String, default: null },
})

const emit = defineEmits(['complete', 'open', 'retry'])

const errorText = computed(() => getErrorMessage(props.error, '今日行动加载失败，请重试。'))
const hasActions = computed(() => {
  const sections = props.data?.sections
  if (!sections) return false
  return Object.values(sections).some((items) => items.length > 0)
})

function itemKey(item) {
  return `${item.kind}:${item.id}:${item.occurrence_date || ''}`
}

function isCompleting(item) {
  return props.completingKey === itemKey(item)
}

function handleItem(item) {
  if (!item) return
  if (item.action === 'complete' && !item.completed) {
    emit('complete', item)
  } else if (item.action === 'open') {
    emit('open', item)
  }
}

function itemMeta(item) {
  const labels = []
  if (item.overdue) labels.push('已逾期')
  if (item.priority) labels.push(item.priority === 'urgent' ? '紧急' : item.priority === 'high' ? '高优先级' : '')
  if (item.deadline) {
    const deadline = new Date(item.deadline)
    if (!Number.isNaN(deadline.getTime())) labels.push(`截止 ${deadline.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`)
  }
  return labels.filter(Boolean).join(' · ') || '立即行动'
}
</script>

<style scoped>
.today-action-center {
  padding: var(--surface-padding);
  border: 1px solid rgba(14, 116, 144, 0.18);
  border-radius: var(--surface-radius);
  background: linear-gradient(160deg, #f7fcfb 0%, #ffffff 60%);
  box-shadow: var(--shadow-md);
}

.today-action-header,
.today-action-group-heading,
.today-action-item,
.today-next-action {
  display: flex;
  align-items: center;
}

.today-action-header,
.today-action-group-heading,
.today-next-action {
  justify-content: space-between;
  gap: var(--spacing-md);
}

.today-action-kicker,
.today-next-action-label {
  display: block;
  color: #0f766e;
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.today-action-header h2 {
  margin: 4px 0 0;
  color: #17324d;
  font-size: var(--font-size-xl);
  line-height: 1.25;
}

.today-action-summary {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.today-action-link,
.today-action-empty-link {
  color: #0f766e;
  font-size: var(--font-size-sm);
  font-weight: 700;
  white-space: nowrap;
}

.today-action-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: var(--spacing-lg) 0;
}

.today-action-metric {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border-left: 3px solid #0e7490;
  background: #f0fdfa;
}

.today-action-metric strong {
  color: #17324d;
  font-size: var(--font-size-lg);
}

.today-action-metric span {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
}

.today-action-metric--danger { border-left-color: #e11d48; background: #fff1f2; }
.today-action-metric--success { border-left-color: #15803d; background: #f0fdf4; }

.today-action-inline-error,
.today-action-state--error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #be123c;
  background: #fff1f2;
}

.today-action-inline-error {
  padding: 8px 10px;
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
}

.today-action-inline-error button {
  border: 0;
  color: inherit;
  background: transparent;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.today-action-state {
  display: flex;
  min-height: 100px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-secondary);
}

.today-action-state--error {
  min-height: 100px;
  padding: 12px;
  border-radius: 6px;
}

.today-action-state--error p { margin: 0; }

.today-next-action {
  padding: 12px 14px;
  margin-bottom: var(--spacing-lg);
  border: 1px solid rgba(15, 118, 110, 0.2);
  border-radius: 6px;
  background: #ecfdf5;
}

.today-next-action strong {
  display: block;
  margin-top: 3px;
  color: #134e4a;
  font-size: var(--font-size-sm);
}

.today-next-action-button {
  min-width: 64px;
  min-height: 38px;
  padding: 6px 12px;
  border: 1px solid #0f766e;
  border-radius: 5px;
  color: #ffffff;
  background: #0f766e;
  font-weight: 700;
  cursor: pointer;
}

.today-next-action-button:disabled { cursor: wait; opacity: 0.65; }

.today-action-sections { display: grid; gap: var(--spacing-lg); }

.today-action-group-heading {
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.today-action-group-heading h3 {
  margin: 0;
  color: #17324d;
  font-size: var(--font-size-sm);
}

.today-action-group-heading span {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
}

.today-action-list { display: grid; gap: 6px; margin-top: 8px; }

.today-action-item {
  min-height: 52px;
  gap: 10px;
  padding: 8px 0;
}

.today-action-item--overdue { color: #9f1239; }
.today-action-item--done { opacity: 0.7; }

.today-action-check,
.today-action-symbol {
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
}

.today-action-check {
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid #94a3b8;
  border-radius: 50%;
  color: #ffffff;
  background: transparent;
  cursor: pointer;
}

.today-action-check > span[aria-hidden="true"] { width: 7px; height: 7px; border-radius: 50%; background: #94a3b8; }
.today-action-check:disabled { cursor: wait; opacity: 0.65; }

.today-action-check--done {
  display: grid;
  place-items: center;
  border: 1px solid #15803d;
  border-radius: 50%;
  color: #15803d;
  font-size: 18px;
  font-weight: 700;
}

.today-action-symbol {
  display: grid;
  place-items: center;
  color: #0e7490;
  font-size: 24px;
}

.today-action-item-copy { min-width: 0; flex: 1; }

.today-action-item-copy strong,
.today-action-item-copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-action-item-copy strong { color: #17324d; font-size: var(--font-size-sm); }
.today-action-item-copy span { margin-top: 3px; color: var(--text-secondary); font-size: var(--font-size-xs); }

.today-action-item-open {
  min-height: 34px;
  padding: 4px 9px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  color: #0e7490;
  background: #ffffff;
  cursor: pointer;
}

.today-action-empty {
  display: grid;
  justify-items: start;
  gap: 6px;
  padding: 22px 0 4px;
  color: var(--text-secondary);
}

.today-action-empty strong { color: #17324d; }

@media (max-width: 600px) {
  .today-action-center { padding: 16px; }
  .today-action-header { align-items: flex-start; }
  .today-action-header h2 { font-size: var(--font-size-lg); }
  .today-action-metrics { gap: 6px; }
  .today-action-metric { padding: 9px 8px; }
  .today-action-metric strong { font-size: var(--font-size-md); }
  .today-action-inline-error { align-items: flex-start; flex-direction: column; }
}
</style>
