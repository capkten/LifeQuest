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
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  background: var(--color-card);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
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
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.today-action-header h2 {
  margin: 4px 0 0;
  color: var(--color-text);
  font-size: var(--font-size-xl);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.today-action-summary {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.today-action-link,
.today-action-empty-link {
  color: var(--color-primary-dark);
  font-size: var(--font-size-sm);
  font-weight: 700;
  white-space: nowrap;
  transition: color 0.15s ease;
}

.today-action-link:hover,
.today-action-empty-link:hover {
  color: var(--color-primary);
}

.today-action-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: var(--spacing-lg) 0;
}

.today-action-metric {
  display: grid;
  gap: 3px;
  padding: 10px 14px;
  border-left: 3px solid var(--color-primary);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  background: var(--color-bg-tertiary);
  border-top: 1px solid var(--color-border);
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.today-action-metric strong {
  color: var(--color-text);
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.today-action-metric span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.today-action-metric--danger {
  border-left-color: var(--color-error);
  background: rgba(239, 68, 68, 0.06);
  border-color: rgba(239, 68, 68, 0.15);
}

.today-action-metric--danger strong {
  color: var(--color-error-dark);
}

.today-action-metric--success {
  border-left-color: var(--color-accent);
  background: rgba(16, 185, 129, 0.06);
  border-color: rgba(16, 185, 129, 0.15);
}

.today-action-metric--success strong {
  color: var(--color-accent-dark);
}

.today-action-inline-error,
.today-action-state--error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-error-dark);
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--radius-md);
}

.today-action-inline-error {
  padding: 8px 12px;
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  border: 1px solid rgba(239, 68, 68, 0.2);
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
  color: var(--color-text-secondary);
}

.today-action-state--error {
  min-height: 100px;
  padding: 14px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.today-action-state--error p { margin: 0; }

.today-next-action {
  padding: 12px 16px;
  margin-bottom: var(--spacing-lg);
  border: 1px solid rgba(14, 165, 233, 0.25);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(16, 185, 129, 0.06) 100%);
}

.today-next-action strong {
  display: block;
  margin-top: 3px;
  color: var(--color-text);
  font-size: var(--font-size-base);
  font-weight: 700;
}

.today-next-action-button {
  min-width: 72px;
  min-height: 38px;
  padding: 6px 14px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: #ffffff;
  background: var(--color-primary);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.25);
}

.today-next-action-button:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.35);
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

.today-action-list { display: grid; gap: 8px; margin-top: 10px; }

.today-action-item {
  display: flex;
  align-items: center;
  min-height: 56px;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-low);
  border: 1px solid var(--color-border);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.today-action-item:hover {
  background: #ffffff;
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.today-action-item--overdue {
  border-left: 3px solid var(--color-error);
  color: var(--color-error-dark);
}
.today-action-item--done { opacity: 0.7; }

.today-action-check,
.today-action-symbol {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
}

.today-action-check {
  display: grid;
  place-items: center;
  padding: 0;
  border: 1.5px solid var(--color-border-strong);
  border-radius: 50%;
  color: #ffffff;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.today-action-check:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: rgba(14, 165, 233, 0.1);
}

.today-action-check > span[aria-hidden="true"] { width: 8px; height: 8px; border-radius: 50%; background: var(--color-text-tertiary); }
.today-action-check:disabled { cursor: wait; opacity: 0.65; }

.today-action-check--done {
  display: grid;
  place-items: center;
  border: 1.5px solid var(--color-success);
  background: rgba(34, 197, 94, 0.12);
  border-radius: 50%;
  color: var(--color-success-dark);
  font-size: 16px;
  font-weight: 700;
}

.today-action-symbol {
  display: grid;
  place-items: center;
  color: var(--color-primary-dark);
  font-size: 20px;
  border-radius: var(--radius-md);
  background: rgba(14, 165, 233, 0.08);
}

.today-action-item-copy { min-width: 0; flex: 1; }

.today-action-item-copy strong,
.today-action-item-copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-action-item-copy strong { color: var(--color-text); font-size: var(--font-size-sm); font-weight: 600; }
.today-action-item-copy span { margin-top: 2px; color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.today-action-item-open {
  min-height: 34px;
  padding: 4px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-primary-dark);
  background: #ffffff;
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.today-action-item-open:hover {
  background: var(--color-surface-low);
  border-color: var(--color-primary);
  color: var(--color-primary);
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
