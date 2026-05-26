<template>
  <div class="backpack-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">背包</h2>
        <span class="item-count">{{ filteredItems.length }} 件物品</span>
      </div>
    </div>

    <div class="filter-tabs">
      <button
        v-for="tab in filterTabs"
        :key="tab.value"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeFilter === tab.value }"
        @click="activeFilter = tab.value"
      >
        <span class="tab-label">{{ tab.label }}</span>
        <span class="tab-count" :class="'tab-count--' + tab.value">{{ getCount(tab.value) }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchAll">重试</button>
    </div>

    <div v-else-if="filteredItems.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 7V5a4 4 0 0 0-8 0v2" />
          <line x1="12" y1="12" x2="12" y2="16" />
          <line x1="10" y1="14" x2="14" y2="14" />
        </svg>
      </div>
      <h3 class="empty-title">你的背包是空的</h3>
      <p class="empty-text">前往商城购买物品来填满你的背包吧。</p>
      <router-link to="/shop" class="btn-create">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 0 1-8 0" />
        </svg>
        前往商城
      </router-link>
    </div>

    <div v-else class="items-grid">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="item-card"
      >
        <div class="item-card-header">
          <div class="item-card-main">
            <div class="item-card-icon">
              <svg v-if="item.item_type === 'consumable'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              <svg v-else-if="item.item_type === 'gear'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <svg v-else-if="item.item_type === 'collectible'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="6" />
                <circle cx="12" cy="12" r="2" />
              </svg>
            </div>
            <div class="item-card-info">
              <h3 class="item-card-name">{{ getItemName(item) }}</h3>
              <p v-if="getItemDescription(item)" class="item-card-desc">{{ getItemDescription(item) }}</p>
            </div>
          </div>
          <div class="item-card-badges">
            <span class="type-badge" :class="'type-badge--' + item.item_type">
              {{ formatType(item.item_type) }}
            </span>
            <span v-if="item.is_equipped" class="status-badge status-badge--equipped">已装备</span>
            <span v-else class="status-badge status-badge--active">可用</span>
          </div>
        </div>
        <div class="item-card-footer">
          <div class="item-card-stats">
            <span class="stat-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="8" y1="6" x2="21" y2="6" />
                <line x1="8" y1="12" x2="21" y2="12" />
                <line x1="8" y1="18" x2="21" y2="18" />
                <line x1="3" y1="6" x2="3.01" y2="6" />
                <line x1="3" y1="12" x2="3.01" y2="12" />
                <line x1="3" y1="18" x2="3.01" y2="18" />
              </svg>
              数量: {{ item.quantity }}
            </span>
            <span class="stat-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4l3 3" />
              </svg>
              {{ formatDate(item.obtained_at) }}
            </span>
          </div>
          <div class="item-card-actions">
            <button
              v-if="item.item_type === 'consumable'"
              class="btn-action btn-action--use"
              :disabled="actionId === item.id"
              @click="useItem(item)"
            >
              <span v-if="actionId === item.id" class="loading-spinner loading-spinner--sm"></span>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              使用
            </button>
            <button
              v-if="(item.item_type === 'gear' || item.item_type === 'collectible') && !item.is_equipped"
              class="btn-action btn-action--equip"
              :disabled="actionId === item.id"
              @click="equipItem(item)"
            >
              <span v-if="actionId === item.id" class="loading-spinner loading-spinner--sm"></span>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              装备
            </button>
            <button
              class="btn-action btn-action--discard"
              :disabled="actionId === item.id"
              @click="requestDiscard(item)"
            >
              <span v-if="actionId === item.id" class="loading-spinner loading-spinner--sm"></span>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              丢弃
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Success Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="successToast" class="success-toast" role="status" aria-live="polite">
          <div class="success-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span>{{ successToast }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Error Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="errorToast" class="error-toast" role="status" aria-live="polite">
          <div class="error-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>{{ errorToast }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Discard Confirmation Dialog -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="confirmDialog" class="dialog-overlay" @click.self="cancelConfirm" @keydown.escape="cancelConfirm">
          <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" @keydown.escape="cancelConfirm">
            <div class="dialog-header">
              <h3 id="confirm-dialog-title" class="dialog-title">确认丢弃</h3>
              <button class="dialog-close" @click="cancelConfirm" aria-label="Close">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div class="dialog-body">
              <p>确定要丢弃 <strong>{{ confirmDialog.name }}</strong> 吗？</p>
              <p class="dialog-hint">此操作无法撤销。</p>
            </div>
            <div class="dialog-actions">
              <button class="btn-secondary" @click="cancelConfirm">取消</button>
              <button class="btn-danger" @click="confirmDiscard">丢弃</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { backpackService } from '../services/backpack'
import { shopService } from '../services/shop'
import { useToast } from '../composables/useToast'

const authStore = useAuthStore()
const { successToast, errorToast, showSuccess, showError } = useToast()

const items = ref([])
const shopItemsMap = ref({})
const loading = ref(true)
const error = ref(null)
const actionId = ref(null)
const activeFilter = ref('all')
const confirmDialog = ref(null)

const filterTabs = [
  { value: 'all', label: '全部' },
  { value: 'consumable', label: '消耗品' },
  { value: 'gear', label: '装备' },
  { value: 'collectible', label: '收藏品' },
  { value: 'quest', label: '任务' }
]

const filteredItems = computed(() => {
  if (activeFilter.value === 'all') return items.value
  return items.value.filter(item => item.item_type === activeFilter.value)
})

function getCount(filter) {
  if (filter === 'all') return items.value.length
  return items.value.filter(item => item.item_type === filter).length
}

function getItemName(item) {
  const shopItem = shopItemsMap.value[item.shop_item_id]
  return shopItem?.name || 'Unknown Item'
}

function getItemDescription(item) {
  const shopItem = shopItemsMap.value[item.shop_item_id]
  return shopItem?.description || ''
}

function formatType(type) {
  const typeMap = {
    'consumable': '消耗品',
    'gear': '装备',
    'collectible': '收藏品',
    'quest': '任务'
  }
  return typeMap[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
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
    showError('无法加载物品详情，物品名称可能不可用。')
  }
}

async function fetchBackpackItems() {
  items.value = await backpackService.getItems()
}

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([fetchShopItems(), fetchBackpackItems()])
  } catch (e) {
    error.value = '加载背包物品失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function useItem(item) {
  if (actionId.value) return
  actionId.value = item.id
  try {
    const updated = await backpackService.useItem(item.id)
    if (updated.quantity <= 0) {
      items.value = items.value.filter(i => i.id !== item.id)
    } else {
      const idx = items.value.findIndex(i => i.id === item.id)
      if (idx !== -1) {
        items.value[idx] = updated
      }
    }
    await authStore.fetchUser()
    showSuccess('物品使用成功！')
  } catch (e) {
    showError(e.response?.data?.detail || '使用物品失败，请重试。')
  } finally {
    actionId.value = null
  }
}

async function equipItem(item) {
  if (actionId.value) return
  actionId.value = item.id
  try {
    const updated = await backpackService.equipItem(item.id)
    const idx = items.value.findIndex(i => i.id === item.id)
    if (idx !== -1) {
      items.value[idx] = updated
    }
    items.value = items.value.map(i => {
      if (i.id !== item.id && i.item_type === item.item_type && i.is_equipped) {
        return { ...i, is_equipped: false, status: 'active' }
      }
      return i
    })
    showSuccess('物品已装备！')
  } catch (e) {
    showError(e.response?.data?.detail || '装备物品失败，请重试。')
  } finally {
    actionId.value = null
  }
}

function requestDiscard(item) {
  const shopItem = shopItemsMap.value[item.shop_item_id]
  confirmDialog.value = {
    id: item.id,
    name: shopItem?.name || 'this item'
  }
}

function cancelConfirm() {
  confirmDialog.value = null
}

async function confirmDiscard() {
  if (!confirmDialog.value || actionId.value) return
  const itemId = confirmDialog.value.id
  confirmDialog.value = null
  actionId.value = itemId
  try {
    const updated = await backpackService.discardItem(itemId)
    if (updated.quantity <= 0) {
      items.value = items.value.filter(i => i.id !== itemId)
    } else {
      const idx = items.value.findIndex(i => i.id === itemId)
      if (idx !== -1) {
        items.value[idx] = updated
      }
    }
    showSuccess('物品已丢弃。')
  } catch (e) {
    showError(e.response?.data?.detail || '丢弃物品失败，请重试。')
  } finally {
    actionId.value = null
  }
}

onMounted(() => {
  fetchAll()
})
</script>

<style scoped>
.backpack-page {
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
  align-items: baseline;
  gap: var(--spacing-md);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.item-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
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

/* Filter Tabs */
.filter-tabs {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--font-family);
  transition: color 0.15s ease, border-color 0.15s ease;
  margin-bottom: -1px;
  text-transform: capitalize;
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-count {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

.tab-count--all {
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

.tab-count--consumable {
  background: rgba(255, 107, 107, 0.12);
  color: var(--color-error);
}

.tab-count--gear {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

.tab-count--collectible {
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

.tab-count--quest {
  background: rgba(255, 217, 61, 0.12);
  color: var(--color-warning);
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

.loading-spinner--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
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

/* Items Grid */
.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-lg);
}

.item-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.item-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.item-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
}

.item-card-main {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  flex: 1;
  min-width: 0;
}

.item-card-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.item-card-icon svg {
  width: 22px;
  height: 22px;
  color: var(--color-primary);
}

.item-card-info {
  flex: 1;
  min-width: 0;
}

.item-card-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
}

.item-card-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-card-badges {
  display: flex;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.type-badge,
.status-badge {
  font-size: var(--font-size-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;
  text-transform: capitalize;
  white-space: nowrap;
}

.type-badge--consumable {
  background: rgba(255, 107, 107, 0.12);
  color: var(--color-error);
}

.type-badge--gear {
  background: rgba(0, 217, 255, 0.12);
  color: var(--color-secondary);
}

.type-badge--collectible {
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

.type-badge--quest {
  background: rgba(255, 217, 61, 0.12);
  color: var(--color-warning);
}

.status-badge--equipped {
  background: rgba(81, 207, 102, 0.15);
  color: var(--color-success);
}

.status-badge--active {
  background: rgba(156, 163, 175, 0.15);
  color: var(--color-text-tertiary);
}

.item-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border);
}

.item-card-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.stat-item svg {
  width: 14px;
  height: 14px;
}

.item-card-actions {
  display: flex;
  gap: var(--spacing-xs);
}

.btn-action {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
  background: transparent;
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-action svg {
  width: 14px;
  height: 14px;
}

.btn-action--use {
  color: var(--color-success);
  border-color: rgba(81, 207, 102, 0.3);
}

.btn-action--use:hover:not(:disabled) {
  background: rgba(81, 207, 102, 0.1);
}

.btn-action--equip {
  color: var(--color-secondary);
  border-color: rgba(0, 217, 255, 0.3);
}

.btn-action--equip:hover:not(:disabled) {
  background: rgba(0, 217, 255, 0.1);
}

.btn-action--discard {
  color: var(--color-error);
  border-color: rgba(255, 107, 107, 0.3);
}

.btn-action--discard:hover:not(:disabled) {
  background: rgba(255, 107, 107, 0.1);
}

/* Toast Notifications */
.success-toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 1100;
}

.success-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-success);
  color: #fff;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.success-toast-content svg {
  width: 18px;
  height: 18px;
}

.error-toast {
  position: fixed;
  top: calc(var(--spacing-lg) + 60px);
  right: var(--spacing-lg);
  z-index: 1100;
}

.error-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-error);
  color: #fff;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.error-toast-content svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.dialog {
  width: 100%;
  max-width: 420px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.dialog-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: background 0.15s ease;
}

.dialog-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.dialog-close svg {
  width: 18px;
  height: 18px;
}

.dialog-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.dialog-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border);
}

.btn-secondary {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-secondary:hover {
  background: var(--color-bg-tertiary);
}

.btn-danger {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-error);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: opacity 0.15s ease;
}

.btn-danger:hover {
  opacity: 0.9;
}

/* Responsive */
@media (max-width: 1199px) {
  .backpack-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .backpack-page {
    padding: var(--spacing-md);
  }

  .filter-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: var(--spacing-xs);
  }

  .tab-btn {
    white-space: nowrap;
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-xs);
  }

  .items-grid {
    grid-template-columns: 1fr;
  }

  .item-card-header {
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .item-card-badges {
    flex-wrap: wrap;
  }

  .item-card-footer {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }

  .item-card-actions {
    justify-content: flex-end;
  }

  .dialog {
    max-width: 100%;
    margin: var(--spacing-sm);
  }
}
</style>
