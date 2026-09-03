<template>
  <div class="weekly-review-page">
    <header class="page-header">
      <div>
        <span class="page-kicker">执行回顾</span>
        <h1 class="page-title">周复盘</h1>
        <p class="page-subtitle">看清本周完成了什么，决定下一步做什么。</p>
      </div>
      <div class="page-actions">
        <label class="week-picker" for="review-week-start">
          <span>周一</span>
          <input id="review-week-start" v-model="weekStartInput" type="date" @change="loadReview" />
        </label>
        <button type="button" class="refresh-btn" :disabled="loading" @click="loadReview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M20 11a8.1 8.1 0 0 0-14.8-3L3 11" />
            <path d="M3 4v7h7" />
            <path d="M4 13a8.1 8.1 0 0 0 14.8 3L21 13" />
            <path d="M21 20v-7h-7" />
          </svg>
          刷新
        </button>
      </div>
    </header>

    <div v-if="loading && !review" class="loading-state" aria-live="polite">
      <span class="loading-spinner"></span>
      <span>正在整理本周数据...</span>
    </div>

    <template v-else>
      <div v-if="error" class="error-state" role="alert">
        <span>{{ error }}</span>
        <button type="button" class="retry-btn" @click="loadReview">重试</button>
      </div>

      <div v-if="review" class="review-content">
        <section class="review-period" aria-labelledby="review-period-title">
          <div>
            <span class="section-kicker">本周范围</span>
            <h2 id="review-period-title">{{ formatDate(review.week_start) }} - {{ formatDate(review.week_end) }}</h2>
          </div>
          <span class="timezone-label">{{ review.timezone }}</span>
        </section>

        <section class="summary-grid" aria-label="本周概览">
          <article class="summary-item summary-item--accent">
            <span class="summary-label">已完成</span>
            <strong>{{ review.summary.completed_count }}</strong>
            <span class="summary-note">任务与习惯</span>
          </article>
          <article class="summary-item">
            <span class="summary-label">待处理</span>
            <strong>{{ review.summary.open_count }}</strong>
            <span class="summary-note">当前开放工作</span>
          </article>
          <article class="summary-item summary-item--warning">
            <span class="summary-label">逾期</span>
            <strong>{{ review.summary.overdue_count }}</strong>
            <span class="summary-note">需要重新安排</span>
          </article>
          <article class="summary-item">
            <span class="summary-label">习惯完成</span>
            <strong>{{ review.summary.habit_completed_count }} / {{ review.summary.habit_due_count }}</strong>
            <span class="summary-note">本周应完成</span>
          </article>
        </section>

        <div class="review-grid">
          <section class="review-section review-section--wide" aria-labelledby="reward-title">
            <div class="section-heading">
              <div>
                <span class="section-kicker">反馈</span>
                <h2 id="reward-title">本周获得</h2>
              </div>
              <span class="reward-total" :class="{ 'reward-total--negative': review.rewards.coins_delta < 0 }">
                {{ review.rewards.coins_delta >= 0 ? '+' : '' }}{{ review.rewards.coins_delta }} 灵石
              </span>
            </div>
            <div class="reward-grid">
              <div class="reward-item"><span>获得灵石</span><strong>+{{ review.rewards.coins_earned }}</strong></div>
              <div class="reward-item"><span>消费灵石</span><strong>-{{ review.rewards.coins_spent }}</strong></div>
              <div class="reward-item"><span>经验</span><strong>+{{ review.rewards.experience }}</strong></div>
              <div class="reward-item"><span>修为</span><strong>+{{ review.rewards.cultivation }}</strong></div>
              <div class="reward-item"><span>灵石资源</span><strong>+{{ review.rewards.spirit_stones }}</strong></div>
            </div>
          </section>

          <section class="review-section" aria-labelledby="streak-title">
            <div class="section-heading">
              <div>
                <span class="section-kicker">习惯</span>
                <h2 id="streak-title">连续变化</h2>
              </div>
            </div>
            <ul v-if="review.habit_streak_changes.length" class="review-list">
              <li v-for="habit in review.habit_streak_changes" :key="habit.id" class="review-list-item">
                <div>
                  <strong>{{ habit.title }}</strong>
                  <span>{{ habit.completed_count }} / {{ habit.due_count }} 次完成</span>
                </div>
                <span class="streak-delta" :class="{ 'streak-delta--muted': habit.delta === 0 }">
                  {{ habit.delta > 0 ? '+' : '' }}{{ habit.delta }}
                </span>
              </li>
            </ul>
            <p v-else class="empty-copy">本周没有习惯记录。</p>
          </section>

          <section class="review-section review-section--wide" aria-labelledby="priority-title">
            <div class="section-heading">
              <div>
                <span class="section-kicker">下一步</span>
                <h2 id="priority-title">未完成的高优先级工作</h2>
              </div>
              <router-link to="/todos?tab=tasks" class="section-link">查看待办</router-link>
            </div>
            <ul v-if="review.unfinished_high_priority.length" class="review-list review-list--cards">
              <li v-for="item in review.unfinished_high_priority" :key="`${item.id}-${item.occurrence_date || ''}`" class="review-list-item review-list-item--card">
                <router-link :to="reviewItemUrl(item)" class="review-item-link">
                  <span class="priority-mark" :class="`priority-mark--${item.priority}`" aria-hidden="true"></span>
                  <span class="review-item-main">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.priority === 'urgent' ? '紧急' : '高优先级' }} · {{ item.occurrence_date ? formatDate(item.occurrence_date) : '待处理' }}</span>
                  </span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
                </router-link>
              </li>
            </ul>
            <p v-else class="empty-copy">没有未完成的高优先级工作。</p>
          </section>

          <section class="review-section" aria-labelledby="projects-title">
            <div class="section-heading">
              <div>
                <span class="section-kicker">项目</span>
                <h2 id="projects-title">需要下一动作</h2>
              </div>
              <router-link to="/projects" class="section-link">查看项目</router-link>
            </div>
            <ul v-if="review.projects_without_next_action.length" class="review-list">
              <li v-for="item in review.projects_without_next_action" :key="item.id" class="review-list-item">
                <router-link :to="item.url" class="review-item-link review-item-link--compact">
                  <span class="review-item-main"><strong>{{ item.title }}</strong><span>暂无开放任务</span></span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
                </router-link>
              </li>
            </ul>
            <p v-else class="empty-copy">所有进行中的项目都有开放任务。</p>
          </section>

          <section class="review-section" aria-labelledby="notes-title">
            <div class="section-heading">
              <div>
                <span class="section-kicker">上下文</span>
                <h2 id="notes-title">本周笔记</h2>
              </div>
              <router-link to="/notes" class="section-link">查看笔记</router-link>
            </div>
            <ul v-if="review.notes.length" class="review-list">
              <li v-for="item in review.notes" :key="item.id" class="review-list-item">
                <router-link :to="item.url" class="review-item-link review-item-link--compact">
                  <span class="review-item-main"><strong>{{ item.title }}</strong><span>打开笔记</span></span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
                </router-link>
              </li>
            </ul>
            <p v-else class="empty-copy">本周还没有更新笔记。</p>
          </section>

          <section class="review-section review-section--wide" aria-labelledby="suggestion-title">
            <div class="section-heading">
              <div>
                <span class="section-kicker">建议</span>
                <h2 id="suggestion-title">下周可以这样开始</h2>
              </div>
            </div>
            <ol class="suggestion-list">
              <li v-for="suggestion in review.suggestions" :key="`${suggestion.title}-${suggestion.url}`">
                <router-link :to="suggestion.url" class="suggestion-link">
                  <span class="suggestion-index">{{ review.suggestions.indexOf(suggestion) + 1 }}</span>
                  <span class="suggestion-copy"><strong>{{ suggestion.title }}</strong><span>{{ suggestion.reason }}</span></span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
                </router-link>
              </li>
            </ol>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { reviewService } from '../services/review'
import { getErrorMessage } from '../utils/errorMessage'

const review = ref(null)
const loading = ref(true)
const error = ref(null)
const weekStartInput = ref('')
let requestId = 0

function formatDate(value) {
  if (!value) return ''
  const [year, month, day] = String(value).split('-')
  return `${year}年${Number(month)}月${Number(day)}日`
}

async function loadReview() {
  if (loading.value && review.value) return
  const currentRequestId = ++requestId
  loading.value = true
  error.value = null
  try {
    const result = await reviewService.getWeeklyReview(weekStartInput.value || undefined)
    if (currentRequestId !== requestId) return
    review.value = result
    weekStartInput.value = result.week_start
  } catch (requestError) {
    if (currentRequestId === requestId) {
      error.value = getErrorMessage(requestError, '周复盘加载失败，请重试。')
    }
  } finally {
    if (currentRequestId === requestId) loading.value = false
  }
}

function reviewItemUrl(item) {
  if (!item.occurrence_date || String(item.url).includes('occurrence_date=')) return item.url
  const occurrenceDateQuery = `occurrence_date=${item.occurrence_date}`
  const url = new URL(item.url, window.location.origin)
  url.search = url.search ? `${url.search}&${occurrenceDateQuery}` : `?${occurrenceDateQuery}`
  return `${url.pathname}${url.search}${url.hash}`
}

onMounted(loadReview)
</script>

<style scoped>
.weekly-review-page {
  width: 100%;
  min-height: 100%;
  padding: var(--page-padding-y) var(--page-padding-x);
  color: var(--color-text);
}

.page-header,
.section-heading,
.review-period,
.page-actions,
.week-picker,
.review-item-link,
.suggestion-link {
  display: flex;
  align-items: center;
}

.page-header,
.review-period,
.section-heading {
  justify-content: space-between;
  gap: var(--spacing-lg);
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.page-kicker,
.section-kicker {
  display: block;
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.page-title {
  margin-top: var(--spacing-xs);
  font-size: 2.35rem;
  line-height: 1.15;
}

.page-subtitle {
  margin-top: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.page-actions {
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.week-picker {
  gap: var(--spacing-xs);
  min-height: 44px;
  padding: 0 var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  background: var(--color-card);
}

.week-picker input {
  min-width: 132px;
  border: 0;
  color: var(--color-text);
  background: transparent;
  font: inherit;
}

.refresh-btn,
.retry-btn,
.section-link {
  cursor: pointer;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  min-height: 44px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: var(--color-primary-dark);
  background: transparent;
  font: inherit;
  font-size: var(--font-size-sm);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.refresh-btn svg {
  width: 16px;
  height: 16px;
}

.refresh-btn:hover:not(:disabled) {
  color: #fff;
  background: var(--color-primary);
}

.refresh-btn:disabled {
  cursor: wait;
  opacity: 0.6;
}

.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  min-height: 240px;
  color: var(--color-text-secondary);
}

.error-state {
  flex-wrap: wrap;
  color: var(--color-error);
}

.retry-btn {
  min-height: 36px;
  padding: 0 var(--spacing-md);
  border: 1px solid currentColor;
  border-radius: var(--radius-md);
  color: inherit;
  background: transparent;
  font: inherit;
}

.review-content {
  max-width: 1180px;
  margin: 0 auto;
}

.review-period,
.review-section,
.summary-item {
  border: 1px solid var(--color-border);
  background: var(--color-card);
  border-radius: var(--surface-radius);
  box-shadow: var(--shadow-sm);
}

.review-period {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-left: 4px solid var(--color-primary);
}

.review-period h2 {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.timezone-label,
.summary-note,
.review-list-item span,
.review-item-main span,
.suggestion-copy span,
.empty-copy {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

.timezone-label {
  white-space: nowrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--spacing-md);
  margin: var(--spacing-lg) 0;
}

.summary-item {
  display: flex;
  min-height: 128px;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-top: 3px solid var(--color-border);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.summary-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-border-strong);
}

.summary-item--accent { border-top-color: var(--color-primary); }
.summary-item--warning { border-top-color: var(--color-secondary); }

.summary-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.summary-item strong {
  margin: var(--spacing-xs) 0;
  font-size: 1.75rem;
  line-height: 1;
}

.review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-lg);
}

.review-section {
  min-width: 0;
  padding: var(--spacing-lg);
}

.review-section--wide { grid-column: span 2; }

.section-heading {
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
}

.section-heading h2 {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-lg);
}

.section-link {
  color: var(--color-primary-dark);
  font-size: var(--font-size-sm);
  text-decoration: none;
  white-space: nowrap;
}

.section-link:hover { color: var(--color-secondary-dark, var(--color-secondary)); }

.reward-total {
  color: var(--color-primary-dark);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.reward-total--negative { color: var(--color-error); }

.reward-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--spacing-sm);
}

.reward-item {
  display: flex;
  min-height: 72px;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light, var(--color-border));
  background: var(--color-surface-low);
}

.reward-item span { color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.reward-item strong { color: var(--color-text); font-size: var(--font-size-lg); }

.review-list,
.suggestion-list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.review-list-item {
  border-top: 1px solid var(--color-border-light, var(--color-border));
}

.review-list-item:first-child { border-top: 0; }

.review-list-item > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) 0;
}

.review-list-item > div,
.review-item-main,
.suggestion-copy {
  min-width: 0;
}

.review-item-main,
.suggestion-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.streak-delta {
  color: var(--color-primary-dark);
  font-weight: 700;
}

.streak-delta--muted { color: var(--color-text-tertiary); }

.review-list--cards .review-list-item {
  margin-top: var(--spacing-sm);
  border: 1px solid var(--color-border-light, var(--color-border));
}

.review-list--cards .review-list-item:first-child { margin-top: 0; }

.review-item-link,
.suggestion-link {
  width: 100%;
  min-width: 0;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  color: inherit;
  text-decoration: none;
}

.review-item-link:hover,
.suggestion-link:hover { background: var(--color-surface-low); }

.review-item-link svg,
.suggestion-link svg { width: 18px; height: 18px; flex: 0 0 auto; color: var(--color-text-tertiary); }
.review-item-link--compact { padding: var(--spacing-sm) 0; }

.priority-mark {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--color-secondary);
}

.priority-mark--urgent { background: var(--color-error); }

.suggestion-list { counter-reset: suggestion; }

.suggestion-list li { border-top: 1px solid var(--color-border-light, var(--color-border)); }
.suggestion-list li:first-child { border-top: 0; }

.suggestion-index {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--color-primary-light, var(--color-primary));
  border-radius: 50%;
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

@media (max-width: 900px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .reward-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 767px) {
  .weekly-review-page { padding-bottom: calc(var(--page-padding-y) + var(--bottom-nav-height)); }
  .page-title { font-size: 1.7rem; }
  .page-header,
  .review-period { align-items: flex-start; flex-direction: column; }
  .page-header { gap: var(--spacing-md); }
  .page-actions { width: 100%; justify-content: stretch; }
  .week-picker { flex: 1; }
  .week-picker input { min-width: 0; width: 100%; }
  .refresh-btn { justify-content: center; }
  .summary-grid,
  .review-grid { grid-template-columns: 1fr; }
  .review-section--wide { grid-column: span 1; }
  .reward-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (prefers-reduced-motion: reduce) {
  .refresh-btn { transition: none; }
}

.refresh-btn:focus-visible,
.retry-btn:focus-visible,
.week-picker input:focus-visible,
.section-link:focus-visible,
.review-item-link:focus-visible,
.suggestion-link:focus-visible {
  outline: 3px solid rgba(14, 165, 233, 0.35);
  outline-offset: 2px;
}
</style>
