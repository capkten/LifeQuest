<template>
  <div class="history-page">
    <div class="page-header">
      <div class="header-left">
        <router-link to="/shop" class="back-link" aria-label="返回商城">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          返回商城
        </router-link>
        <h2 class="page-title">兑换历史</h2>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchAll">重试</button>
    </div>

    <div v-else-if="records.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      </div>
      <h3 class="empty-title">暂无兑换记录</h3>
      <p class="empty-text">前往商城购买商品后，兑换记录将显示在这里。</p>
      <router-link to="/shop" class="btn-create">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 0 1-8 0" />
        </svg>
        前往商城
      </router-link>
    </div>

    <div v-else class="history-list">
      <div
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
          <h3 class="history-card-name">{{ getItemName(record.item_id) }}</h3>
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
              数量: {{ record.quantity }}
            </span>
          </div>
        </div>
        <div class="history-card-right">
          <div class="history-card-cost">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v12M6 12h12" />
            </svg>
            <span>-{{ record.total_cost }}</span>
          </div>
          <span class="status-badge" :class="'status-badge--' + record.status">
            {{ formatStatus(record.status) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { shopService } from '../services/shop'

const records = ref([])
const shopItemsMap = ref({})
const loading = ref(true)
const error = ref(null)

const statusMap = {
  pending: '处理中',
  completed: '已完成',
  cancelled: '已取消',
  refunded: '已退款'
}

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
  return statusMap[status] || status
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
  padding: var(--spacing-xl);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  text-decoration: none;
  transition: color 0.15s ease;
}

.back-link:hover {
  color: var(--color-primary);
}

.back-link svg {
  width: 16px;
  height: 16px;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

/* Loading State */
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

/* Error State */
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

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
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
  margin-bottom: var(--spacing-xl);
  max-width: 320px;
}

.btn-create {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  text-decoration: none;
  transition: background 0.15s ease;
}

.btn-create:hover {
  background: var(--color-primary-dark);
}

.btn-create svg {
  width: 18px;
  height: 18px;
}

/* History List */
.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.history-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.history-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.history-card-icon {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-card-icon svg {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}

.history-card-body {
  flex: 1;
  min-width: 0;
}

.history-card-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
}

.history-card-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.meta-item svg {
  width: 14px;
  height: 14px;
}

.history-card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.history-card-cost {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-base);
  font-weight: 700;
  color: var(--color-error);
}

.history-card-cost svg {
  width: 18px;
  height: 18px;
  color: var(--color-warning);
}

.status-badge {
  font-size: var(--font-size-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;
  white-space: nowrap;
}

.status-badge--completed {
  background: rgba(81, 207, 102, 0.12);
  color: var(--color-success);
}

.status-badge--pending {
  background: rgba(255, 217, 61, 0.12);
  color: var(--color-warning);
}

.status-badge--cancelled {
  background: rgba(156, 163, 175, 0.15);
  color: var(--color-text-tertiary);
}

.status-badge--refunded {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

/* Responsive */
@media (max-width: 1199px) {
  .history-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .history-page {
    padding: var(--spacing-md);
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .history-card {
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .history-card-right {
    flex-direction: row;
    align-items: center;
    gap: var(--spacing-md);
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
