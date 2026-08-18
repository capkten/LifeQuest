<template>
  <div class="history-page">
    <section class="history-hero">
      <div class="history-hero-main">
        <router-link to="/shop" class="back-link" aria-label="返回商城">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          返回商城
        </router-link>
        <span class="history-kicker">奖励记录</span>
        <h1 class="history-title">兑换历史</h1>
        <p class="history-subtitle">查看奖励兑换、状态变化与金币支出，保留原有历史记录与退款状态展示。</p>
      </div>
      <div class="history-hero-stats" v-if="!loading && !error && records.length">
        <div class="summary-chip">
          <span class="summary-chip-label">累计记录</span>
          <strong>{{ records.length }}</strong>
        </div>
        <div class="summary-chip">
          <span class="summary-chip-label">累计支出</span>
          <strong>{{ totalSpent }}</strong>
        </div>
        <div class="summary-chip">
          <span class="summary-chip-label">待处理</span>
          <strong>{{ pendingCount }}</strong>
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
      <h2>暂无兑换记录</h2>
      <p>前往商城兑换奖励后，记录会自动出现在这里。</p>
      <router-link to="/shop" class="primary-link">前往商城</router-link>
    </div>

    <template v-else>
      <section class="summary-grid">
        <article class="summary-card">
          <span class="summary-card-label">累计记录</span>
          <strong class="summary-card-value">{{ records.length }}</strong>
          <span class="summary-card-note">包含兑换、退款与处理中状态</span>
        </article>
        <article class="summary-card">
          <span class="summary-card-label">累计支出金币</span>
          <strong class="summary-card-value">{{ totalSpent }}</strong>
          <span class="summary-card-note">按消费总额汇总</span>
        </article>
        <article class="summary-card">
          <span class="summary-card-label">最近兑换</span>
          <strong class="summary-card-value summary-card-value--small">{{ latestRecordDate }}</strong>
          <span class="summary-card-note">按记录创建时间展示</span>
        </article>
      </section>

      <section class="timeline-card">
        <div class="section-heading">
          <div>
            <span class="section-kicker">时间线</span>
            <h2>兑换时间线</h2>
          </div>
          <span class="section-meta">{{ records.length }} 条记录</span>
        </div>

        <div class="history-list">
          <article
            v-for="record in records"
            :key="record.id"
            class="history-card"
          >
            <div class="history-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                <line x1="7" y1="7" x2="7.01" y2="7" />
              </svg>
            </div>

            <div class="history-card-body">
              <div class="history-card-header">
                <div>
                  <h3 class="history-card-name">{{ getItemName(record.item_id) }}</h3>
                  <p class="history-card-copy">奖励兑换已同步到原有商城记录系统。</p>
                </div>
                <span class="status-badge" :class="'status-badge--' + record.status">
                  {{ formatStatus(record.status) }}
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

            <div class="history-card-right">
              <span class="cost-pill">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v12M6 12h12" />
                </svg>
                -{{ record.total_cost }}
              </span>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { shopService } from '../services/shop'
import { labelExchangeStatus } from '../utils/displayLabels'

const records = ref([])
const shopItemsMap = ref({})
const loading = ref(true)
const error = ref(null)

const totalSpent = computed(() => records.value.reduce((sum, record) => sum + (record.total_cost || 0), 0))
const pendingCount = computed(() => records.value.filter((record) => record.status === 'pending').length)
const latestRecordDate = computed(() => {
  if (!records.value.length) return '暂无'
  return formatDate(records.value[0].created_at)
})

function getItemName(itemId) {
  const shopItem = shopItemsMap.value[itemId]
  return shopItem?.name || '未知商品'
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

function formatStatus(status) {
  return labelExchangeStatus(status)
}

async function fetchShopItems() {
  try {
    const shopItems = await shopService.getItems()
    const map = {}
    for (const si of shopItems) {
      map[si.id] = si
    }
    shopItemsMap.value = map
  } catch (e) {
    console.error('Failed to fetch shop items for name lookup:', e)
  }
}

async function fetchHistory() {
  records.value = await shopService.getExchangeHistory()
}

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([fetchShopItems(), fetchHistory()])
  } catch (e) {
    error.value = '加载兑换历史失败，请重试。'
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
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #eef8fb 100%);
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
  border: 1px solid rgba(14, 165, 233, 0.12);
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
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  padding: 18px;
  border-radius: 20px;
  background: var(--color-bg-secondary);
  border: 1px solid rgba(14, 165, 233, 0.08);
}

.history-card-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(14, 165, 233, 0.1);
  color: var(--color-primary-dark);
}

.history-card-icon svg {
  width: 22px;
  height: 22px;
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

.meta-item,
.cost-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid rgba(14, 165, 233, 0.1);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.meta-item svg,
.cost-pill svg {
  width: 14px;
  height: 14px;
}

.history-card-right {
  display: flex;
  align-items: center;
}

.cost-pill {
  color: var(--color-error);
}

.status-badge {
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

.status-badge--completed {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.status-badge--pending {
  background: rgba(245, 158, 11, 0.15);
  color: #b45309;
}

.status-badge--cancelled {
  background: rgba(148, 163, 184, 0.16);
  color: var(--color-text-secondary);
}

.status-badge--refunded {
  background: rgba(14, 165, 233, 0.14);
  color: var(--color-primary-dark);
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

  .history-card-right {
    justify-content: flex-start;
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
