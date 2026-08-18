<template>
  <div class="shop-page">
    <section class="shop-hero" aria-labelledby="shop-hero-title">
      <div class="shop-hero-copy">
        <span class="shop-hero-kicker">LIFEQUEST REWARDS</span>
        <h1 id="shop-hero-title">用今天的努力，兑换生活里的小奖励</h1>
        <p>把完成任务获得的金币，换成真正让你开心的时刻。</p>
      </div>
      <div class="shop-hero-summary">
        <strong>{{ filteredItems.length }}</strong>
        <span>个奖励等待兑换</span>
      </div>
    </section>
    <div class="page-header">
      <div class="page-header-main">
        <div class="header-left">
          <span class="shop-kicker">REWARD MARKET</span>
          <h2 class="page-title">商城</h2>
          <span class="item-count">{{ filteredItems.length }} 件奖励可兑换</span>
        </div>
        <div class="balance-display">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v12M6 12h12" />
          </svg>
          <span class="balance-copy">
            <span class="balance-label">当前钱包</span>
            <span class="balance-value">{{ user?.coins || 0 }}</span>
          </span>
          <span class="balance-unit">金币</span>
        </div>
      </div>
      <div class="shop-actions">
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

    <nav v-if="items.length > 0" class="shop-categories" aria-label="商品分类">
      <button
        v-for="category in categoryOptions"
        :key="category"
        type="button"
        class="shop-category"
        :class="{ 'shop-category--active': activeCategory === category }"
        @click="activeCategory = category"
      >
        {{ category }}
      </button>
    </nav>

    <div v-if="items.length > 0" class="shop-toolbar">
      <label class="shop-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-4-4" />
        </svg>
        <span class="sr-only">搜索商品</span>
        <input v-model="searchQuery" type="search" placeholder="搜索奖励名称或描述" />
        <button v-if="searchQuery" type="button" class="shop-search-clear" aria-label="清除搜索" @click="searchQuery = ''">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </label>
      <div class="shop-toolbar-meta">
        <span>{{ filteredItems.length }} 个结果</span>
        <select v-model="sortOrder" aria-label="商品排序">
          <option value="recommended">推荐排序</option>
          <option value="price-asc">金币从低到高</option>
          <option value="price-desc">金币从高到低</option>
          <option value="name">名称排序</option>
        </select>
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

    <div v-else-if="filteredItems.length === 0" class="empty-state empty-state--filtered">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-4-4" />
        </svg>
      </div>
      <h3 class="empty-title">{{ searchQuery ? '没有找到匹配的奖励' : '这个分类还没有商品' }}</h3>
      <p class="empty-text">{{ searchQuery ? '试试更短的关键词，或切换其他分类。' : '换个分类看看，或者创建一个新的商品。' }}</p>
    </div>

    <div v-else class="items-grid">
      <div
        v-for="(item, index) in filteredItems"
        :key="item.id"
        class="item-card"
        :class="{ 'item-card--featured': index === 0 }"
      >
        <span v-if="index === 0" class="item-card-featured">本页推荐</span>
        <div class="item-card-top">
          <div class="item-card-icon">
            <component :is="resolveShopIcon(item.icon)" />
          </div>
          <div class="item-card-meta">
            <div v-if="user && item.created_by === user.id" class="item-card-admin">
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
            <div class="item-price">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v12M6 12h12" />
              </svg>
              <span class="item-price-label">兑换</span>
              <strong>{{ item.coin_price }}</strong>
              <small>金币</small>
            </div>
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
          <button
            class="btn-purchase"
            :disabled="purchasingId === item.id || (user?.coins || 0) < item.coin_price || (item.stock !== -1 && item.stock <= 0)"
            @click="purchaseItem(item)"
          >
            <span v-if="purchasingId === item.id" class="loading-spinner loading-spinner--sm"></span>
            <span v-else-if="item.stock !== -1 && item.stock <= 0">已售罄</span>
            <span v-else-if="(user?.coins || 0) < item.coin_price">金币不足</span>
            <span v-else>立即兑换</span>
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
              <label class="form-label">图标</label>
              <div class="icon-grid">
                <button
                  v-for="option in iconOptions"
                  :key="option.value"
                  type="button"
                  class="icon-option"
                  :class="{ 'icon-option--active': form.icon === option.value }"
                  @click="form.icon = option.value"
                >
                  <component :is="option.component" />
                </button>
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
import { getErrorMessage } from '../utils/errorMessage'
import {
  Apple,
  Box,
  Coffee,
  Coin,
  Goblet,
  Goods,
  Handbag,
  MagicStick,
  Medal,
  Moon,
  Present,
  Shop,
  Star,
  SwitchButton,
  Ticket,
  Trophy
} from '@element-plus/icons-vue'

const authStore = useAuthStore()
const user = computed(() => authStore.user)
const { successToast, errorToast, showSuccess, showError } = useToast()

const items = ref([])
const loading = ref(true)
const error = ref(null)
const purchasingId = ref(null)
const activeCategory = ref('全部')
const searchQuery = ref('')
const sortOrder = ref('recommended')

const categoryOptions = computed(() => [
  '全部',
  ...Array.from(new Set(items.value.map(item => item.category).filter(Boolean)))
])

const filteredItems = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const visibleItems = items.value.filter((item) => {
    const inCategory = activeCategory.value === '全部' || item.category === activeCategory.value
    const searchableText = `${item.name || ''} ${item.description || ''} ${item.category || ''}`.toLowerCase()
    return inCategory && (!query || searchableText.includes(query))
  })

  return [...visibleItems].sort((left, right) => {
    if (sortOrder.value === 'price-asc') return left.coin_price - right.coin_price
    if (sortOrder.value === 'price-desc') return right.coin_price - left.coin_price
    if (sortOrder.value === 'name') return (left.name || '').localeCompare(right.name || '')
    return 0
  })
})

const showCreateDialog = ref(false)
const creating = ref(false)
const dialogError = ref(null)
const dialogNameInput = ref(null)
const dialogMode = ref('create')
const editingItem = ref(null)

const showDeleteDialog = ref(false)
const deletingItem = ref(null)
const deleting = ref(false)

const iconOptions = [
  { value: 'Box', component: Box },
  { value: 'Present', component: Present },
  { value: 'Goods', component: Goods },
  { value: 'Handbag', component: Handbag },
  { value: 'Shop', component: Shop },
  { value: 'Ticket', component: Ticket },
  { value: 'Coin', component: Coin },
  { value: 'Trophy', component: Trophy },
  { value: 'Medal', component: Medal },
  { value: 'Star', component: Star },
  { value: 'MagicStick', component: MagicStick },
  { value: 'Goblet', component: Goblet },
  { value: 'Coffee', component: Coffee },
  { value: 'Apple', component: Apple },
  { value: 'Moon', component: Moon },
  { value: 'SwitchButton', component: SwitchButton }
]

const iconMap = Object.fromEntries(iconOptions.map((option) => [option.value, option.component]))

const form = ref({
  name: '',
  description: '',
  icon: 'Box',
  coin_price: 10,
  category: '',
  stock: -1
})

const defaultForm = {
  name: '',
  description: '',
  icon: 'Box',
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

function resolveShopIcon(icon) {
  return iconMap[icon] || Box
}

async function fetchItems() {
  loading.value = true
  error.value = null
  try {
    items.value = await shopService.getItems()
  } catch (e) {
    error.value = getErrorMessage(e)
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
    showError(getErrorMessage(e))
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
    icon: item.icon || 'Box',
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
    showError(getErrorMessage(e))
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
      icon: form.value.icon || 'Box',
      coin_price: form.value.coin_price,
      category: form.value.category?.trim() || undefined,
      stock: form.value.stock
    }
    const newItem = await shopService.createItem(payload)
    items.value.push(newItem)
    cancelDialog()
    showSuccess(`"${newItem.name}" 已添加到商城！`)
  } catch (e) {
    dialogError.value = getErrorMessage(e)
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
      icon: form.value.icon || 'Box',
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
    dialogError.value = getErrorMessage(e)
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

.shop-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 22px 24px;
  overflow: hidden;
  border: 1px solid rgba(14, 165, 233, 0.18);
  border-radius: 16px;
  background:
    radial-gradient(circle at 90% 0%, rgba(110, 231, 183, 0.34), transparent 28%),
    linear-gradient(120deg, #123b5d 0%, #0a6c94 66%, #0ea5e9 100%);
  color: #fff;
  box-shadow: var(--shadow-md);
}

.shop-hero-copy {
  min-width: 0;
}

.shop-hero-kicker {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.shop-hero h1 {
  margin: 0;
  color: #fff;
  font-family: var(--font-family-display);
  font-size: clamp(1.15rem, 1rem + 0.45vw, 1.65rem);
  line-height: 1.2;
}

.shop-hero p {
  margin-top: 7px;
  color: rgba(255, 255, 255, 0.78);
  font-size: var(--font-size-sm);
}

.shop-hero-summary {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding-left: 20px;
  border-left: 1px solid rgba(255, 255, 255, 0.25);
  color: rgba(255, 255, 255, 0.78);
  font-size: var(--font-size-xs);
  text-align: right;
}

.shop-hero-summary strong {
  color: #fff;
  font-family: var(--font-family-display);
  font-size: 1.8rem;
  line-height: 1;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.page-header-main {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  min-width: 0;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
}

.item-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.shop-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.balance-display {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 14px;
  background: rgba(255, 217, 61, 0.12);
  border: 1px solid rgba(255, 217, 61, 0.3);
  border-radius: 14px;
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
  justify-content: center;
  gap: var(--spacing-sm);
  min-height: 44px;
  padding: 10px 14px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: 12px;
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
  justify-content: center;
  gap: var(--spacing-sm);
  min-height: 44px;
  padding: 10px 14px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 12px;
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
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.item-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  padding: 12px;
  position: relative;
}

.item-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.item-card-top,
.item-card-footer {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 10px;
}

.item-card-top {
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
}

.item-card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: 12px;
  flex-shrink: 0;
}

.item-card-icon svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.item-card-icon :deep(svg) {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.item-card-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: flex-start;
  gap: 6px;
  min-width: 0;
}

.item-card-admin {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: nowrap;
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
  padding: 10px 0 0;
  flex: 1;
}

.item-card-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
  line-height: 1.3;
}

.item-card-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 6px;
}

.item-card-tags {
  display: flex;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
}

.item-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  font-weight: 500;
  text-transform: capitalize;
  line-height: 18px;
}

.item-tag--category {
  background: rgba(14, 165, 233, 0.12);
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
  padding: 10px 0 0;
  border-top: 1px solid var(--color-border);
  margin-top: 10px;
}

.item-price {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-warning);
  justify-content: flex-end;
  text-align: right;
}

.item-price-label,
.item-price small {
  color: var(--color-text-tertiary);
  font-size: 10px;
  font-weight: 500;
}

.item-price strong {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: 1.15rem;
  line-height: 1;
}

.item-price svg {
  width: 16px;
  height: 16px;
}

.btn-purchase {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
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
  max-height: min(88vh, 760px);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
  overflow-y: auto;
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

.icon-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.icon-option {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-option :deep(svg) {
  width: 18px;
  height: 18px;
}

.icon-option:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(14, 165, 233, 0.06);
}

.icon-option--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(14, 165, 233, 0.1);
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

  .shop-toolbar {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .shop-toolbar-meta {
    justify-content: space-between;
  }

  .shop-hero {
    align-items: flex-start;
    flex-direction: column;
    gap: 16px;
    padding: 18px;
  }

  .shop-hero-summary {
    align-items: flex-start;
    width: 100%;
    padding-top: 12px;
    padding-left: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.25);
    border-left: 0;
    text-align: left;
  }

  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }

  .page-header-main {
    flex-direction: column;
    width: 100%;
    align-items: stretch;
    gap: 12px;
  }

  .shop-actions {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .items-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .btn-history,
  .btn-create {
    width: 100%;
  }

  .item-card {
    padding: 10px;
  }

  .item-card-top {
    padding-bottom: 8px;
  }

  .item-card-meta {
    gap: 4px;
  }

  .item-card-body {
    padding-top: 8px;
  }

  .item-card-icon {
    width: 36px;
    height: 36px;
  }

  .item-card-icon svg {
    width: 18px;
    height: 18px;
  }

  .item-card-icon :deep(svg) {
    width: 18px;
    height: 18px;
  }

  .item-price {
    font-size: 12px;
  }

  .item-price strong {
    font-size: 1rem;
  }

  .item-card-footer {
    padding-top: 8px;
    margin-top: 8px;
  }

  .btn-purchase {
    min-height: 40px;
    padding: 8px 10px;
    font-size: 12px;
  }

  .btn-icon {
    width: 24px;
    height: 24px;
  }

  .btn-icon svg {
    width: 12px;
    height: 12px;
  }

  .form-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .dialog {
    max-width: 100%;
    width: calc(100% - 16px);
    max-height: calc(100vh - 16px);
    margin: var(--spacing-sm);
  }

  .dialog-body {
    padding: 12px;
    gap: 12px;
  }

  .icon-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 6px;
  }

  .icon-option {
    height: 40px;
  }
}
@media (min-width: 768px) {
  .shop-page {
    padding: 0;
  }

  .items-grid {
    gap: 14px;
  }

  .item-card {
    border-radius: 12px;
    padding: 13px;
  }
}

.shop-categories {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 18px;
  padding: 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.shop-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.shop-search {
  display: flex;
  align-items: center;
  flex: 1 1 360px;
  gap: 9px;
  min-height: 44px;
  max-width: 520px;
  padding: 0 13px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-card);
  color: var(--color-text-tertiary);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.shop-search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.12);
}

.shop-search svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.shop-search input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  font-size: var(--font-size-sm);
}

.shop-search input::placeholder {
  color: var(--color-text-tertiary);
}

.shop-search-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.shop-search-clear:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.shop-search-clear svg {
  width: 15px;
  height: 15px;
}

.shop-toolbar-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
  white-space: nowrap;
}

.shop-toolbar-meta select {
  min-height: 40px;
  padding: 0 30px 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-card);
  color: var(--color-text-secondary);
  font: inherit;
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.shop-kicker {
  display: block;
  color: var(--color-accent-dark);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  line-height: 1;
  text-transform: uppercase;
}

.shop-page .header-left {
  gap: 5px;
}

.shop-page .balance-display {
  border-color: rgba(16, 185, 129, 0.24);
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-accent-dark);
}

.shop-categories::-webkit-scrollbar {
  display: none;
}

.shop-category {
  min-height: 36px;
  padding: 7px 14px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 600;
  white-space: nowrap;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.shop-category:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.shop-category--active {
  border-color: rgba(14, 165, 233, 0.2);
  background: var(--color-bg-tertiary);
  color: var(--color-primary-dark);
}

.empty-state--filtered {
  min-height: 280px;
}

@media (min-width: 1200px) {
  .items-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
  }

  .item-card {
    min-height: 248px;
  }
}

.shop-page .btn-purchase {
  background: var(--color-accent);
  border: 1px solid var(--color-accent);
}

.shop-page .btn-purchase:hover:not(:disabled) {
  background: var(--color-accent-dark);
  border-color: var(--color-accent-dark);
}

.balance-copy {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  line-height: 1;
}

.balance-copy .balance-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.balance-unit {
  align-self: flex-end;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.item-card--featured {
  border-color: rgba(16, 185, 129, 0.38);
  box-shadow: 0 10px 24px rgba(16, 185, 129, 0.08);
}

.item-card-featured {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1;
  padding: 3px 7px;
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 999px;
  background: var(--color-card);
  color: var(--color-accent-dark);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.item-card-name,
.item-card-desc {
  overflow-wrap: anywhere;
}

.shop-category,
.shop-search-clear,
.btn-icon {
  min-height: 44px;
}

.shop-search-clear {
  width: 44px;
  height: 44px;
}

.btn-icon {
  width: 44px;
  height: 44px;
}

@media (max-width: 767px) {
  .shop-search {
    flex: 0 0 44px;
    max-width: none;
    height: 44px;
    min-height: 44px;
    padding-top: 0;
    padding-bottom: 0;
  }

  .shop-search input {
    height: 100%;
    min-height: 0;
    line-height: 1.2;
  }

  .balance-display {
    width: 100%;
    justify-content: flex-start;
  }

  .balance-unit {
    margin-left: auto;
  }

  .shop-category {
    min-height: 44px;
  }

  .item-card-featured {
    top: 8px;
    left: 8px;
  }

  .item-card--featured .item-card-top {
    padding-top: 24px;
  }

  .btn-icon {
    width: 44px;
    height: 44px;
  }
}
</style>
