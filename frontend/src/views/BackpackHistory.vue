<template>
  <div class="history-page">
    <section class="history-hero">
      <div class="history-hero-main">
        <router-link to="/backpack" class="back-link" aria-label="返回背包">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          返回背包
        </router-link>
        <span class="history-kicker">INVENTORY LOG</span>
        <h1 class="history-title">使用历史</h1>
        <p class="history-subtitle">集中查看背包物品的使用、装备与丢弃记录，同时保留现有 API 返回的动作轨迹。</p>
      </div>
      <div class="history-hero-stats" v-if="!loading && !error && records.length">
        <div class="summary-chip">
          <span class="summary-chip-label">总记录</span>
          <strong>{{ records.length }}</strong>
        </div>
        <div class="summary-chip">
          <span class="summary-chip-label">使用次数</span>
          <strong>{{ useCount }}</strong>
        </div>
        <div class="summary-chip">
          <span class="summary-chip-label">装备次数</span>
          <strong>{{ equipCount }}</strong>
        </div>
      </div>
    </section>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="feedback-card feedback-card--error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchAll">重试</button>
    </div>

    <div v-else-if="records.length === 0" class="feedback-card">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      </div>
      <h2>暂无使用记录</h2>
      <p>当你使用、装备或丢弃背包物品后，对应记录会在这里展示。</p>
      <router-link to="/backpack" class="primary-link">前往背包</router-link>
    </div>

    <template v-else>
      <section class="summary-grid">
        <article class="summary-card">
          <span class="summary-card-label">使用次数</span>
          <strong class="summary-card-value">{{ useCount }}</strong>
          <span class="summary-card-note">消耗类物品动作</span>
        </article>
        <article class="summary-card">
          <span class="summary-card-label">装备次数</span>
          <strong class="summary-card-value">{{ equipCount }}</strong>
          <span class="summary-card-note">含装备与收藏品激活</span>
        </article>
        <article class="summary-card">
          <span class="summary-card-label">最近操作</span>
          <strong class="summary-card-value summary-card-value--small">{{ latestActionDate }}</strong>
          <span class="summary-card-note">按 created_at 展示</span>
        </article>
      </section>

      <section class="timeline-card">
        <div class="section-heading">
          <div>
            <span class="section-kicker">TIMELINE</span>
            <h2>背包动作时间线</h2>
          </div>
          <span class="section-meta">{{ records.length }} 条动作</span>
        </div>

        <div class="history-list">
          <article
            v-for="record in records"
            :key="record.id"
            class="history-card"
          >
            <div class="history-card-icon" :class="'history-card-icon--' + record.action_type">
              <svg v-if="record.action_type === 'use'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <svg v-else-if="record.action_type === 'equip'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </div>

            <div class="history-card-body">
              <div class="history-card-header">
                <div>
                  <h3 class="history-card-name">{{ record.item_name || '未知物品' }}</h3>
                  <p class="history-card-copy">保留原有动作类型与记录时间展示。</p>
                </div>
                <span class="action-badge" :class="'action-badge--' + record.action_type">
                  {{ formatAction(record.action_type) }}
                </span>
              </div>

              <div class="history-card-meta">
                <span class="meta-item">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  {{ formatDate(record.created_at) }}
                </span>
                <span class="meta-item" v-if="record.quantity > 1">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <line x1="8" y1="6" x2="21" y2="6" />
                    <line x1="8" y1="12" x2="21" y2="12" />
                    <line x1="8" y1="18" x2="21" y2="18" />
                    <line x1="3" y1="6" x2="3.01" y2="6" />
                    <line x1="3" y1="12" x2="3.01" y2="12" />
                    <line x1="3" y1="18" x2="3.01" y2="18" />
                  </svg>
                  数量 {{ record.quantity }}
                </span>
              </div>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { backpackService } from '../services/backpack'

const records = ref([])
const loading = ref(true)
const error = ref(null)

const actionMap = {
  use: '使用',
  equip: '装备',
  discard: '丢弃'
}

const useCount = computed(() => records.value.filter((record) => record.action_type === 'use').length)
const equipCount = computed(() => records.value.filter((record) => record.action_type === 'equip').length)
const latestActionDate = computed(() => {
  if (!records.value.length) return '暂无'
  return formatDate(records.value[0].created_at)
})

function formatAction(action) {
  return actionMap[action] || action
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function fetchHistory() {
  records.value = await backpackService.getHistory()
}

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    await fetchHistory()
  } catch (e) {
    error.value = '加载使用历史失败，请重试。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAll()
})
</script>

<style scoped>
.history-page {
  padding: var(--page-padding-y) var(--page-padding-x);
  display: grid;
  gap: 16px;
}

.history-hero,
.timeline-card,
.summary-card,
.feedback-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  box-shadow: var(--shadow-sm);
}

.history-hero {
  padding: var(--surface-padding);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgba(29, 78, 216, 0.16), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #eef5ff 100%);
}

.history-hero-main {
  display: grid;
  gap: 8px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.back-link:hover {
  color: var(--color-primary-dark);
}

.back-link svg {
  width: 16px;
  height: 16px;
}

.history-kicker,
.section-kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-primary-dark);
  font-weight: 700;
}

.history-title,
.section-heading h2 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-family-display);
}

.history-title {
  font-size: clamp(1.75rem, 2vw, 2.25rem);
}

.history-subtitle {
  margin: 0;
  max-width: 560px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.history-hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  min-width: min(100%, 320px);
}

.summary-chip,
.summary-card {
  padding: 16px;
}

.summary-chip {
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(29, 78, 216, 0.1);
  display: grid;
  gap: 6px;
}

.summary-chip-label,
.summary-card-label,
.summary-card-note,
.section-meta,
.history-card-copy,
.meta-item {
  color: var(--color-text-tertiary);
}

.summary-chip strong,
.summary-card-value {
  color: var(--color-text);
  font-family: var(--font-family-display);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: grid;
  gap: 8px;
}

.summary-card-value {
  font-size: 1.5rem;
}

.summary-card-value--small {
  font-size: 1rem;
}

.timeline-card {
  padding: var(--surface-padding);
  display: grid;
  gap: 16px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 12px;
}

.history-list {
  display: grid;
  gap: 12px;
}

.history-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  padding: 18px;
  border-radius: 20px;
  background: var(--color-bg-secondary);
  border: 1px solid rgba(29, 78, 216, 0.08);
}

.history-card-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-card-icon svg {
  width: 22px;
  height: 22px;
}

.history-card-icon--use {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.history-card-icon--equip {
  background: rgba(14, 165, 233, 0.14);
  color: var(--color-primary-dark);
}

.history-card-icon--discard {
  background: rgba(248, 113, 113, 0.14);
  color: var(--color-error);
}

.history-card-body,
.history-card-header {
  display: grid;
  gap: 10px;
}

.history-card-header {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.history-card-name {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text);
}

.history-card-copy {
  margin: 4px 0 0;
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.history-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid rgba(29, 78, 216, 0.08);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.meta-item svg {
  width: 14px;
  height: 14px;
}

.action-badge {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
}

.action-badge--use {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.action-badge--equip {
  background: rgba(14, 165, 233, 0.14);
  color: var(--color-primary-dark);
}

.action-badge--discard {
  background: rgba(248, 113, 113, 0.14);
  color: var(--color-error);
}

.feedback-card {
  min-height: 320px;
  padding: 28px;
  display: grid;
  place-items: center;
  text-align: center;
  gap: 12px;
}

.feedback-card--error {
  color: var(--color-error);
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
}

.empty-icon svg {
  width: 34px;
  height: 34px;
}

.primary-link,
.retry-btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  text-decoration: none;
  border: 1px solid transparent;
  cursor: pointer;
}

.primary-link {
  background: var(--color-primary);
  color: #fff;
}

.retry-btn {
  background: transparent;
  color: var(--color-primary-dark);
  border-color: rgba(14, 165, 233, 0.2);
}

.loading-state {
  min-height: 280px;
  display: grid;
  place-items: center;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1023px) {
  .history-hero,
  .section-heading,
  .history-card {
    grid-template-columns: 1fr;
  }

  .history-hero {
    align-items: stretch;
  }

  .history-hero-stats,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .history-page {
    padding: var(--spacing-md);
  }

  .history-hero,
  .timeline-card,
  .summary-card,
  .feedback-card {
    border-radius: 22px;
  }

  .history-card {
    padding: 16px;
  }

  .history-card-header {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 768px) {
  .history-page {
    padding: 0;
  }
}
</style>
