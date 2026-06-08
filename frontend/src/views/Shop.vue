<template>
  <div class="shop-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">商城</h2>
        <span class="item-count">{{ items.length }} 件商品</span>
      </div>
      <div class="header-right">
        <div class="balance-display">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v12M6 12h12" />
          </svg>
          <span class="balance-value">{{ user?.coins || 0 }}</span>
          <span class="balance-label">金币</span>
        </div>
        <button class="btn-history" @click="$router.push('/shop/history')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          兑换历史
        </button>
        <button class="btn-create" @click="showCreateDialog = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建商品
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchItems">重试</button>
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 0 1-8 0" />
        </svg>
      </div>
      <h3 class="empty-title">商城暂无商品</h3>
      <p class="empty-text">创建第一件商品来开始吧。</p>
      <button class="btn-create" @click="showCreateDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        创建商品
      </button>
    </div>

    <div v-else class="items-grid">
      <div
        v-for="item in items"
        :key="item.id"
        class="item-card"
      >
        <div class="item-card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
            <line x1="7" y1="7" x2="7.01" y2="7" />
          </svg>
          <div v-if="user && item.created_by === user.id" class="item-card-actions">
            <button class="btn-icon btn-icon--edit" @click.stop="openEditDialog(item)" aria-label="编辑" title="编辑">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
            <button class="btn-icon btn-icon--delete" @click.stop="openDeleteDialog(item)" aria-label="删除" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </div>
        </div>
        <div class="item-card-body">
          <h3 class="item-card-name">{{ item.name }}</h3>
          <p v-if="item.description" class="item-card-desc">{{ item.description }}</p>
          <div class="item-card-tags">
            <span v-if="item.category" class="item-tag item-tag--category">{{ item.category }}</span>
            <span v-if="item.stock === -1" class="item-tag item-tag--stock">无限</span>
            <span v-else class="item-tag item-tag--stock" :class="{ 'item-tag--low-stock': item.stock <= 5 }">
              库存: {{ item.stock }}
            </span>
          </div>
        </div>
        <div class="item-card-footer">
          <div class="item-price">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v12M6 12h12" />
            </svg>
            <span>{{ item.coin_price }}</span>
          </div>
          <button
            class="btn-purchase"
            :disabled="purchasingId === item.id || (user?.coins || 0) < item.coin_price || (item.stock !== -1 && item.stock <= 0)"
            @click="purchaseItem(item)"
          >
            <span v-if="purchasingId === item.id" class="loading-spinner loading-spinner--sm"></span>
            <span v-else-if="item.stock !== -1 && item.stock <= 0">已售罄</span>
            <span v-else-if="(user?.coins || 0) < item.coin_price">金币不足</span>
            <span v-else>购买</span>
          </button>
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

    <!-- Create/Edit Dialog -->
    <Teleport to="body">
      <div v-if="showCreateDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div
          class="dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-dialog-title"
          @keydown="trapFocus"
        >
          <div class="dialog-header">
            <h3 id="create-dialog-title" class="dialog-title">{{ dialogMode === 'edit' ? '编辑商品' : '新建商品' }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="dialogMode === 'edit' ? updateItem() : createItem()">
            <div class="form-group">
              <label class="form-label" for="item-name">名称</label>
              <input
                id="item-name"
                ref="dialogNameInput"
                v-model="form.name"
                type="text"
                class="form-input"
                placeholder="商品名称"
                required
                maxlength="200"
              />
            </div>
            <div class="form-group">
              <label class="form-label" for="item-description">描述</label>
              <textarea
                id="item-description"
                v-model="form.description"
                class="form-textarea"
                placeholder="可选描述..."
                rows="2"
              ></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="item-price">价格（金币）</label>
                <input
                  id="item-price"
                  v-model.number="form.coin_price"
                  type="number"
                  class="form-input"
                  min="0"
                  max="100000"
                  required
                />
              </div>
              <div class="form-group">
                <label class="form-label" for="item-category">分类</label>
                <input
                  id="item-category"
                  v-model="form.category"
                  type="text"
                  class="form-input"
                  placeholder="例如：消耗品、装备"
                  maxlength="50"
                />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="item-stock">库存</label>
              <input
                id="item-stock"
                v-model.number="form.stock"
                type="number"
                class="form-input"
                min="-1"
                max="100000"
                required
              />
              <span class="form-hint">使用 -1 表示无限库存</span>
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="creating || !form.name.trim()">
                <span v-if="creating" class="loading-spinner loading-spinner--sm"></span>
                {{ creating ? (dialogMode === 'edit' ? '更新中...' : '创建中...') : (dialogMode === 'edit' ? '更新' : '创建') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Dialog -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="cancelDelete">
        <div
          class="dialog dialog--confirm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
          @keydown="trapFocus"
        >
          <div class="dialog-header">
            <h3 id="delete-dialog-title" class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="cancelDelete" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">
              确定要删除商品「<strong>{{ deletingItem?.name }}</strong>」吗？此操作无法撤销。
            </p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDelete">取消</button>
              <button type="button" class="btn-danger" :disabled="deleting" @click="deleteItem">
                <span v-if="deleting" class="loading-spinner loading-spinner--sm"></span>
                {{ deleting ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { shopService } from '../services/shop'
import { useToast } from '../composables/useToast'

const authStore = useAuthStore()
const user = computed(() => authStore.user)
const { successToast, errorToast, showSuccess, showError } = useToast()

const items = ref([])
const loading = ref(true)
const error = ref(null)
const purchasingId = ref(null)

const showCreateDialog = ref(false)
const creating = ref(false)
const dialogError = ref(null)
const dialogNameInput = ref(null)
const dialogMode = ref('create')
const editingItem = ref(null)

const showDeleteDialog = ref(false)
const deletingItem = ref(null)
const deleting = ref(false)

const form = ref({
  name: '',
  description: '',
  coin_price: 10,
  category: '',
  stock: -1
})

const defaultForm = {
  name: '',
  description: '',
  coin_price: 10,
  category: '',
  stock: -1
}

watch(showCreateDialog, (open) => {
  if (open) {
    nextTick(() => {
      dialogNameInput.value?.focus()
    })
  }
})

function trapFocus(event) {
  if (event.key === 'Escape') {
    cancelDialog()
    return
  }
  if (event.key !== 'Tab') return
  const dialog = event.currentTarget
  const focusable = dialog.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey) {
    if (document.activeElement === first) {
      event.preventDefault()
      last.focus()
    }
  } else {
    if (document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }
}

async function fetchItems() {
  loading.value = true
  error.value = null
  try {
    items.value = await shopService.getItems()
  } catch (e) {
    error.value = '加载商城商品失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function purchaseItem(item) {
  if (purchasingId.value) return
  purchasingId.value = item.id
  try {
    await shopService.purchaseItem(item.id)
    // Update item stock locally if not unlimited
    if (item.stock !== -1) {
      const idx = items.value.findIndex(i => i.id === item.id)
      if (idx !== -1) {
        items.value[idx] = { ...items.value[idx], stock: items.value[idx].stock - 1 }
      }
    }
    // Refresh user data to update coins
    await authStore.fetchUser()
    showSuccess(`成功购买 ${item.name}！`)
  } catch (e) {
    showError(e.response?.data?.detail || '购买失败，请重试。')
  } finally {
    purchasingId.value = null
  }
}

function cancelDialog() {
  showCreateDialog.value = false
  dialogMode.value = 'create'
  editingItem.value = null
  form.value = { ...defaultForm }
  dialogError.value = null
}

function openEditDialog(item) {
  dialogMode.value = 'edit'
  editingItem.value = item
  form.value = {
    name: item.name,
    description: item.description || '',
    coin_price: item.coin_price,
    category: item.category || '',
    stock: item.stock
  }
  showCreateDialog.value = true
}

function openDeleteDialog(item) {
  deletingItem.value = item
  showDeleteDialog.value = true
}

function cancelDelete() {
  showDeleteDialog.value = false
  deletingItem.value = null
}

async function deleteItem() {
  if (!deletingItem.value) return
  deleting.value = true
  try {
    await shopService.deleteItem(deletingItem.value.id)
    items.value = items.value.filter(i => i.id !== deletingItem.value.id)
    const name = deletingItem.value.name
    cancelDelete()
    showSuccess(`"${name}" 已删除！`)
  } catch (e) {
    showError(e.response?.data?.detail || '删除失败，请重试。')
    cancelDelete()
  } finally {
    deleting.value = false
  }
}

async function createItem() {
  if (!form.value.name.trim()) return
  creating.value = true
  dialogError.value = null
  try {
    const payload = {
      name: form.value.name.trim(),
      description: form.value.description?.trim() || undefined,
      coin_price: form.value.coin_price,
      category: form.value.category?.trim() || undefined,
      stock: form.value.stock
    }
    const newItem = await shopService.createItem(payload)
    items.value.push(newItem)
    cancelDialog()
    showSuccess(`"${newItem.name}" 已添加到商城！`)
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建商品失败，请重试。'
  } finally {
    creating.value = false
  }
}

async function updateItem() {
  if (!form.value.name.trim() || !editingItem.value) return
  creating.value = true
  dialogError.value = null
  try {
    const payload = {
      name: form.value.name.trim(),
      description: form.value.description?.trim() || undefined,
      coin_price: form.value.coin_price,
      category: form.value.category?.trim() || undefined,
      stock: form.value.stock
    }
    const updated = await shopService.updateItem(editingItem.value.id, payload)
    const idx = items.value.findIndex(i => i.id === editingItem.value.id)
    if (idx !== -1) {
      items.value[idx] = updated
    }
    cancelDialog()
    showSuccess(`"${updated.name}" 已更新！`)
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '更新商品失败，请重试。'
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  fetchItems()
})
</script>

<style scoped>
.shop-page {
  padding: var(--page-padding-y) var(--page-padding-x);
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

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.balance-display {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: rgba(255, 217, 61, 0.12);
  border: 1px solid rgba(255, 217, 61, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-warning);
}

.balance-display svg {
  width: 18px;
  height: 18px;
}

.balance-value {
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.balance-label {
  font-weight: 400;
  opacity: 0.8;
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
  transition: background 0.15s ease;
  white-space: nowrap;
}

.btn-create:hover {
  background: var(--color-primary-dark);
}

.btn-create:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-create svg {
  width: 18px;
  height: 18px;
}

.btn-history {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-history:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.btn-history svg {
  width: 18px;
  height: 18px;
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.item-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius-sm);
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  padding: 14px;
}

.item-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.item-card-icon {
  width: 100%;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: var(--surface-radius-sm) var(--surface-radius-sm) 0 0;
  position: relative;
  margin-bottom: 12px;
}

.item-card-icon svg {
  width: 36px;
  height: 36px;
  color: var(--color-primary);
}

.item-card-actions {
  position: absolute;
  top: var(--spacing-xs);
  right: var(--spacing-xs);
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.item-card:hover .item-card-actions {
  opacity: 1;
}

.btn-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
}

.btn-icon svg {
  width: 14px;
  height: 14px;
}

.btn-icon--edit:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.btn-icon--delete:hover {
  background: var(--color-error);
  border-color: var(--color-error);
  color: #fff;
}

.item-card-body {
  padding: 0;
  flex: 1;
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
  margin-bottom: var(--spacing-sm);
}

.item-card-tags {
  display: flex;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
}

.item-tag {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 500;
  text-transform: capitalize;
}

.item-tag--category {
  background: rgba(108, 99, 255, 0.12);
  color: var(--color-primary);
}

.item-tag--stock {
  background: rgba(81, 207, 102, 0.12);
  color: var(--color-success);
}

.item-tag--low-stock {
  background: rgba(255, 107, 107, 0.12);
  color: var(--color-error);
}

.item-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 0;
  border-top: 1px solid var(--color-border);
  gap: 10px;
}

.item-price {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-base);
  font-weight: 700;
  color: var(--color-warning);
}

.item-price svg {
  width: 18px;
  height: 18px;
}

.btn-purchase {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 100px;
  padding: var(--spacing-xs) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
  width: 100%;
  min-height: 44px;
}

.btn-purchase:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-purchase:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
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
  width: min(100% - 24px, 480px);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
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
  gap: var(--spacing-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.15s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  border-color: var(--color-primary);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--color-text-tertiary);
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.form-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.dialog-error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
  padding: var(--spacing-xs) 0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-sm);
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

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dialog--confirm {
  max-width: 400px;
}

.confirm-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.confirm-text strong {
  color: var(--color-text);
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
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

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 1199px) {
  .shop-page {
    padding: var(--page-padding-y) var(--page-padding-x);
  }
}

@media (min-width: 768px) {
  .btn-purchase {
    width: auto;
    min-width: 120px;
  }
}

@media (max-width: 767px) {
  .shop-page {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .items-grid {
    grid-template-columns: 1fr;
  }

  .item-card-footer {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }

  .item-card-actions {
    opacity: 1;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .dialog {
    max-width: 100%;
    margin: var(--spacing-sm);
  }

  .dialog-body {
    padding: var(--spacing-md);
    gap: 12px;
  }
}
</style>
