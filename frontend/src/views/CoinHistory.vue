<template>
  <div class="coin-history-page">
    <div class="page-header">
      <h2 class="page-title">金币明细</h2>
    </div>

    <div class="summary-grid">
      <div class="summary-card summary-card--earned">
        <div class="summary-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ totals.total_earned || 0 }}</span>
          <span class="summary-label">累计收入</span>
        </div>
      </div>
      <div class="summary-card summary-card--spent">
        <div class="summary-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <polyline points="19 12 12 19 5 12" />
          </svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ totals.total_spent || 0 }}</span>
          <span class="summary-label">累计支出</span>
        </div>
      </div>
      <div class="summary-card summary-card--balance">
        <div class="summary-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v12M6 12h12" />
          </svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ user?.coins || 0 }}</span>
          <span class="summary-label">当前余额</span>
        </div>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        <button
          v-for="opt in typeOptions"
          :key="opt.value"
          class="filter-btn"
          :class="{ 'filter-btn--active': typeFilter === opt.value }"
          @click="typeFilter = opt.value; fetchHistory()"
        >
          {{ opt.label }}
        </button>
      </div>
      <select v-model="sourceFilter" class="filter-select" @change="fetchHistory()">
        <option value="">全部来源</option>
        <option value="task">任务</option>
        <option value="habit">习惯</option>
        <option value="goal">目标</option>
        <option value="checkin">签到</option>
        <option value="shop">商城</option>
        <option value="achievement">成就</option>
      </select>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchHistory">重试</button>
    </div>

    <div v-else-if="groupedTransactions.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v12M6 12h12" />
        </svg>
      </div>
      <h3 class="empty-title">暂无交易记录</h3>
      <p class="empty-text">完成任务、签到等操作可获得金币。</p>
    </div>

    <div v-else class="transaction-groups">
      <div v-for="group in groupedTransactions" :key="group.date" class="transaction-group">
        <div class="group-date">{{ group.date }}</div>
        <div class="group-items">
          <div v-for="tx in group.items" :key="tx.id" class="transaction-item">
            <div class="tx-icon" :class="tx.amount > 0 ? 'tx-icon--income' : 'tx-icon--expense'">
              <svg v-if="tx.amount > 0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="12" y1="5" x2="12" y2="19" />
                <polyline points="19 12 12 19 5 12" />
              </svg>
            </div>
            <div class="tx-info">
              <span class="tx-desc">{{ tx.description || tx.source || '交易' }}</span>
              <span class="tx-source">{{ sourceLabel(tx.source) }}</span>
            </div>
            <span class="tx-amount" :class="tx.amount > 0 ? 'tx-amount--positive' : 'tx-amount--negative'">
              {{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="hasMore && !loading" class="load-more">
      <button class="retry-btn" @click="loadMore">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStats } from '../composables/useUserStats'
import { coinService } from '../services/coin'

const { user } = useUserStats()

const transactions = ref([])
const totals = ref({ total_earned: 0, total_spent: 0 })
const loading = ref(true)
const error = ref(null)
const typeFilter = ref('')
const sourceFilter = ref('')
const page = ref(1)
const hasMore = ref(false)

const typeOptions = [
  { label: '全部', value: '' },
  { label: '收入', value: 'income' },
  { label: '支出', value: 'expense' }
]

const sourceMap = {
  task: '任务',
  habit: '习惯',
  goal: '目标',
  checkin: '签到',
  shop: '商城',
  achievement: '成就'
}

function sourceLabel(source) {
  return sourceMap[source] || source || '其他'
}

const groupedTransactions = computed(() => {
  const groups = {}
  for (const tx of transactions.value) {
    const d = tx.created_at ? new Date(tx.created_at) : new Date()
    const key = d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
    if (!groups[key]) groups[key] = []
    groups[key].push(tx)
  }
  return Object.entries(groups).map(([date, items]) => ({ date, items }))
})

async function fetchHistory() {
  loading.value = true
  error.value = null
  page.value = 1
  try {
    const params = { page: 1, limit: 20 }
    if (typeFilter.value) params.type = typeFilter.value
    if (sourceFilter.value) params.source = sourceFilter.value
    const result = await coinService.getHistory(params)
    transactions.value = Array.isArray(result) ? result : (result?.data || [])
    hasMore.value = transactions.value.length >= 20
  } catch (e) {
    error.value = '加载金币记录失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  page.value++
  try {
    const params = { page: page.value, limit: 20 }
    if (typeFilter.value) params.type = typeFilter.value
    if (sourceFilter.value) params.source = sourceFilter.value
    const result = await coinService.getHistory(params)
    const items = Array.isArray(result) ? result : (result?.data || [])
    transactions.value.push(...items)
    hasMore.value = items.length >= 20
  } catch (e) {
    page.value--
  }
}

async function fetchTotals() {
  try {
    totals.value = await coinService.getTotals()
  } catch (e) {
    // Non-critical
  }
}

onMounted(() => {
  fetchHistory()
  fetchTotals()
})
</script>

<style scoped>
.coin-history-page {
  padding: var(--spacing-xl);
  width: 100%;
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.summary-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: border-color 0.2s ease;
}

.summary-card:hover {
  border-color: var(--color-primary);
}

.summary-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.summary-icon svg {
  width: 24px;
  height: 24px;
}

.summary-card--earned .summary-icon {
  background: rgba(81, 207, 102, 0.15);
}

.summary-card--earned .summary-icon svg {
  color: var(--color-success);
}

.summary-card--spent .summary-icon {
  background: rgba(255, 107, 107, 0.15);
}

.summary-card--spent .summary-icon svg {
  color: var(--color-error);
}

.summary-card--balance .summary-icon {
  background: rgba(255, 217, 61, 0.15);
}

.summary-card--balance .summary-icon svg {
  color: var(--color-warning);
}

.summary-info {
  display: flex;
  flex-direction: column;
}

.summary-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.summary-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  gap: var(--spacing-xs);
}

.filter-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.filter-btn:hover {
  background: var(--color-bg-tertiary);
}

.filter-btn--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.filter-btn--active:hover {
  background: var(--color-primary-dark);
}

.filter-select {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: var(--color-primary);
}

/* Loading/Error/Empty */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
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

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--spacing-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  text-align: center;
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-xl);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-lg);
}

.empty-icon svg {
  width: 36px;
  height: 36px;
  color: var(--color-text-tertiary);
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-sm);
}

.empty-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* Transaction Groups */
.transaction-groups {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.transaction-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.group-date {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--color-border);
}

.group-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.transaction-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color 0.15s ease;
}

.transaction-item:hover {
  border-color: var(--color-primary);
}

.tx-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tx-icon svg {
  width: 20px;
  height: 20px;
}

.tx-icon--income {
  background: rgba(81, 207, 102, 0.15);
}

.tx-icon--income svg {
  color: var(--color-success);
}

.tx-icon--expense {
  background: rgba(255, 107, 107, 0.15);
}

.tx-icon--expense svg {
  color: var(--color-error);
}

.tx-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.tx-desc {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tx-source {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.tx-amount {
  font-size: var(--font-size-base);
  font-weight: 700;
  flex-shrink: 0;
}

.tx-amount--positive {
  color: var(--color-success);
}

.tx-amount--negative {
  color: var(--color-error);
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-xl);
}

/* Responsive */
@media (max-width: 1199px) {
  .coin-history-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .coin-history-page {
    padding: var(--spacing-md);
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .summary-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
