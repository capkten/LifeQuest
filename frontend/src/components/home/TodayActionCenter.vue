<template>
  <section class="today-action-center" aria-labelledby="today-action-title">
    <header class="today-action-header">
      <div>
        <span class="today-action-kicker">每日节奏</span>
        <h2 id="today-action-title">习惯与日程</h2>
        <p v-if="data" class="today-action-summary">
          {{ data.summary.habit_completed_count }}/{{ data.summary.habit_due_count }} 个习惯已完成
        </p>
      </div>
      <router-link to="/todos" class="today-action-link">管理习惯</router-link>
    </header>

    <div v-if="loading && !data" class="today-action-state" aria-live="polite">
      <span class="loading-spinner"></span>
      <span>正在整理今天的习惯…</span>
    </div>

    <div v-else-if="error && !data" class="today-action-state today-action-state--error" role="alert">
      <p>{{ errorText }}</p>
      <button type="button" class="retry-btn" @click="$emit('retry')">重试</button>
    </div>

    <template v-else-if="data">
      <div v-if="error" class="today-action-inline-error" role="alert" aria-live="polite">
        <span>{{ errorText }}</span>
        <button type="button" @click="$emit('retry')">重新加载</button>
      </div>

      <div v-if="hasActions" class="today-action-sections">
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
        <strong>今天没有到点的习惯</strong>
        <span>给自己安排一个每日节奏，进度会自己累积。</span>
        <router-link to="/todos" class="today-action-empty-link">创建习惯</router-link>
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
</script>

<style scoped>
.today-action-center {
  padding: clamp(18px, 2.4vw, 32px);
  border: 0;
  border-radius: 26px;
  background: #FFFFFF;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 18px 40px -28px rgba(15, 23, 42, 0.35);
}

.today-action-header,
.today-action-group-heading,
.today-action-item,
.today-action-state,
.today-action-inline-error {
  display: flex;
  align-items: center;
}

.today-action-header {
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.today-action-header h2 {
  margin: 0 0 6px;
  font-size: clamp(19px, 2.6vw, 22px);
  letter-spacing: -0.01em;
}

.today-action-kicker {
  display: inline-block;
  margin-bottom: 6px;
  color: var(--rank-1-accent);
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.today-action-summary {
  margin: 0;
  color: var(--home-ink-tertiary);
  font-size: 13px;
}

.today-action-link {
  color: var(--rank-1-accent);
  font-size: 13.5px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.today-action-state {
  gap: 10px;
  color: var(--home-ink-tertiary);
  font-size: 13.5px;
  padding: 18px 0;
}

.today-action-state--error {
  flex-direction: column;
  align-items: flex-start;
  color: #b42318;
}

.today-action-state--error p {
  margin: 0 0 10px;
}

.retry-btn {
  min-height: 44px;
  padding: 8px 16px;
  border-radius: 12px;
  border: 1px solid var(--home-hairline);
  background: #FFFFFF;
  color: var(--color-text);
  cursor: pointer;
}

.retry-btn:focus-visible,
.today-action-item-open:focus-visible,
.today-action-check:focus-visible,
.today-action-inline-error button:focus-visible {
  outline: 2px solid var(--rank-1-accent);
  outline-offset: 3px;
}

.today-action-inline-error {
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #FEF3F2;
  color: #b42318;
  font-size: 13px;
}

.today-action-inline-error button {
  min-height: 40px;
  padding: 6px 12px;
  border-radius: 10px;
  border: 1px solid rgba(180, 35, 24, 0.25);
  background: #FFFFFF;
  color: #b42318;
  cursor: pointer;
}

.today-action-sections {
  display: grid;
  gap: 4px;
  margin-top: 20px;
}

.today-action-group {
  padding: 18px 0 6px;
  border-top: 1px solid var(--home-hairline);
}

.today-action-group-heading {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}

.today-action-group-heading h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
}

.today-action-group-heading span {
  color: var(--home-ink-tertiary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  background: var(--home-soft);
  padding: 2px 9px;
  border-radius: 999px;
}

.today-action-list {
  display: grid;
}

.today-action-item {
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--home-hairline);
  min-width: 0;
  color: var(--color-text);
}

.today-action-item:last-child {
  border-bottom: 0;
}

.today-action-check {
  display: grid;
  place-items: center;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--home-hairline);
  background: #FFFFFF;
  color: var(--rank-1-accent);
  font-size: 18px;
  cursor: pointer;
}

.today-action-check > span:not(.loading-spinner) {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-radius: 50%;
}

.today-action-check--done {
  border-color: transparent;
  background: var(--rank-1-chip);
  color: var(--rank-1-accent);
}

.today-action-item-copy {
  display: grid;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.today-action-item-copy strong {
  font-weight: 600;
  font-size: 14.5px;
  overflow-wrap: anywhere;
}

.today-action-item-copy span {
  color: var(--home-ink-tertiary);
  font-size: 12.5px;
}

.today-action-item--done .today-action-item-copy strong {
  color: var(--color-text-secondary);
}

.today-action-symbol {
  display: grid;
  place-items: center;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  font-size: 16px;
}

.today-action-symbol--goal {
  background: var(--rank-3-chip);
  color: var(--rank-3-accent);
}

.today-action-item-open {
  flex-shrink: 0;
  min-height: 44px;
  padding: 8px 14px;
  border-radius: 12px;
  border: 1px solid var(--home-hairline);
  background: #FFFFFF;
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
}

.today-action-empty {
  display: grid;
  gap: 6px;
  justify-items: start;
  margin-top: 20px;
  padding: 24px;
  border-radius: 18px;
  background: var(--home-soft);
  color: var(--home-ink-tertiary);
  font-size: 13.5px;
}

.today-action-empty strong {
  color: var(--color-text);
  font-size: 15px;
}

.today-action-empty-link {
  margin-top: 6px;
  color: var(--rank-1-accent);
  font-weight: 600;
  text-decoration: none;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(15, 138, 103, 0.25);
  border-top-color: var(--rank-1-accent);
  border-radius: 50%;
  animation: ac-spin 0.8s linear infinite;
}

.loading-spinner--sm {
  width: 14px;
  height: 14px;
}

@keyframes ac-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .loading-spinner { animation: none; }
}

@media (max-width: 600px) {
  .today-action-center { border-radius: 20px; }
  .today-action-header { flex-wrap: wrap; }
  .today-action-check,
  .today-action-symbol { flex-basis: 44px; width: 44px; height: 44px; }
  .today-action-item-open { min-height: 48px; }
}
</style>
