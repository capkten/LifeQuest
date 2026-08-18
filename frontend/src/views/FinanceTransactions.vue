<template>
  <div class="finance-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push('/finance')" aria-label="返回财务总览">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div class="page-heading">
          <h2 class="page-title">全部流水</h2>
          <p class="page-subtitle">保留现有筛选、编辑、删除与转账记账行为，只调整信息层级与响应式呈现。</p>
        </div>
      </div>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        记一笔
      </button>
    </div>

    <section class="finance-summary-grid">
      <article class="summary-panel summary-panel--primary stitch-surface">
        <div class="summary-panel__eyebrow">钱包概览</div>
        <div class="summary-panel__hero">
          <div>
            <span class="summary-panel__label">净流动</span>
            <div class="summary-panel__value" :class="filteredNet >= 0 ? 'is-positive' : 'is-negative'">
              {{ filteredNet >= 0 ? '+' : '' }}{{ formatMoney(filteredNet) }}
            </div>
          </div>
          <span class="summary-pill">{{ transactions.length }} 条记录</span>
        </div>
        <div class="summary-chip-row">
          <span class="summary-tag summary-tag--income">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
              <polyline points="17 6 23 6 23 12" />
            </svg>
            收入 {{ formatMoney(filteredIncome) }}
          </span>
          <span class="summary-tag summary-tag--expense">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
              <polyline points="17 18 23 18 23 12" />
            </svg>
            支出 {{ formatMoney(filteredExpense) }}
          </span>
        </div>
        <div class="summary-stats">
          <div class="summary-stat">
            <span class="summary-stat__label">账户</span>
            <strong class="summary-stat__value">{{ accounts.length }}</strong>
          </div>
          <div class="summary-stat">
            <span class="summary-stat__label">分类</span>
            <strong class="summary-stat__value">{{ categories.length }}</strong>
          </div>
          <div class="summary-stat">
            <span class="summary-stat__label">筛选中</span>
            <strong class="summary-stat__value">{{ activeFilterCount }}</strong>
          </div>
        </div>
      </article>

      <article class="summary-panel stitch-surface">
        <div class="summary-panel__header">
          <div>
            <div class="summary-panel__eyebrow">最近流水</div>
            <h3 class="summary-panel__title">筛选与范围</h3>
          </div>
          <span class="summary-panel__meta">{{ activeFilterCount === 0 ? '当前查看全部' : `已启用 ${activeFilterCount} 个筛选` }}</span>
        </div>

        <div class="filter-bar">
          <div class="filter-type-group" role="tablist" aria-label="交易类型">
            <button
              v-for="t in typeFilters"
              :key="t.value"
              class="filter-btn"
              :class="{ 'filter-btn--active': filters.type === t.value }"
              role="tab"
              :aria-selected="filters.type === t.value"
              @click="filters.type = t.value; fetchTransactions()"
            >
              {{ t.value ? labelTransactionType(t.value) : '全部' }}
            </button>
          </div>

          <div class="filter-selects">
            <label class="sr-only" for="transactions-account-filter">账户</label>
            <select id="transactions-account-filter" v-model="filters.account_id" class="filter-select" @change="fetchTransactions()">
              <option value="">全部账户</option>
              <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
            <label class="sr-only" for="transactions-category-filter">分类</label>
            <select id="transactions-category-filter" v-model="filters.category_id" class="filter-select" @change="fetchTransactions()">
              <option value="">全部分类</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <label class="sr-only" for="transactions-start-date">开始日期</label>
            <input id="transactions-start-date" v-model="filters.start_date" type="date" class="filter-select" @change="fetchTransactions()" />
            <label class="sr-only" for="transactions-end-date">结束日期</label>
            <input id="transactions-end-date" v-model="filters.end_date" type="date" class="filter-select" @change="fetchTransactions()" />
          </div>
        </div>
      </article>
    </section>

    <div v-if="supportError" class="inline-error" role="alert">
      <span>{{ supportError }}</span>
      <button type="button" class="retry-btn" @click="fetchSupportData">重试账户和分类</button>
    </div>
    <div v-if="supportLoading" class="inline-loading" aria-live="polite">正在加载账户和分类...</div>
    <div v-if="loadMoreError" class="inline-error" role="alert">
      <span>{{ loadMoreError }}</span>
      <button type="button" class="retry-btn" @click="loadMore">重试加载更多</button>
    </div>

    <div v-if="loading && !transactions.length" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error && !transactions.length" class="error-state stitch-surface">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchTransactions">重试</button>
    </div>

    <div v-else>
    <div v-if="error" class="inline-error" role="alert"><span>{{ error }}</span><button type="button" class="retry-btn" @click="fetchTransactions">重试</button></div>
    <div v-if="transactions.length === 0 && !supportError" class="empty-state stitch-surface">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      </div>
      <h3 class="empty-title">暂无流水记录</h3>
      <p class="empty-text">开始记账后，这里会按日期展示最近交易。</p>
    </div>

    <div v-else-if="transactions.length === 0 && supportError" class="error-state stitch-surface" role="alert">
      <p>账户和分类加载失败，流水暂不可完整展示。</p>
    </div>

    <section v-else class="transactions-section">
      <div class="section-heading">
        <div>
          <div class="section-eyebrow">最近活动</div>
          <h3 class="section-title">按日期查看流水</h3>
        </div>
      </div>

      <div v-for="(group, dateKey) in groupedTransactions" :key="dateKey" class="date-group stitch-surface">
        <div class="date-group-header">
          <span class="date-group-label">{{ formatGroupDate(dateKey) }}</span>
          <span class="date-group-sum">收 {{ formatMoney(groupIncome(group)) }} / 支 {{ formatMoney(groupExpense(group)) }}</span>
        </div>

        <div class="date-group-list">
          <div v-for="tx in group" :key="tx.id" class="tx-item">
            <div class="tx-icon" :class="'tx-icon--' + tx.type">
              <svg v-if="tx.type === 'income'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                <polyline points="17 6 23 6 23 12" />
              </svg>
              <svg v-else-if="tx.type === 'expense'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
                <polyline points="17 18 23 18 23 12" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="17 1 21 5 17 9" />
                <path d="M3 11V9a4 4 0 0 1 4-4h14" />
                <polyline points="7 23 3 19 7 15" />
                <path d="M21 13v2a4 4 0 0 1-4 4H3" />
              </svg>
            </div>

            <div class="tx-info">
              <span class="tx-desc">{{ tx.description || '无备注' }}</span>
              <span class="tx-meta">
                {{ tx.category_name || '未分类' }}
                <template v-if="tx.account_name"> · {{ tx.account_name }}</template>
              </span>
            </div>

            <div class="tx-right">
              <span class="tx-amount" :class="'tx-amount--' + tx.type">
                {{ tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : '' }}{{ formatMoney(tx.amount) }}
              </span>
            </div>

            <div class="tx-actions">
              <button class="btn-icon btn-icon--edit" @click="openEdit(tx)" aria-label="编辑">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
              </button>
              <button class="btn-icon btn-icon--delete" @click="openDelete(tx)" aria-label="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasMore" class="load-more">
        <button class="btn-load-more" :disabled="loadingMore" @click="loadMore">
          <span v-if="loadingMore" class="loading-spinner loading-spinner--sm"></span>
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </section>
    </div>

    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div class="dialog dialog--wide" role="dialog" aria-modal="true" aria-labelledby="tx-dialog-title" tabindex="-1" @keydown.escape="cancelDialog">
          <div class="dialog-header">
            <h3 id="tx-dialog-title" class="dialog-title">{{ editingTx ? '编辑流水' : '记一笔' }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveTransaction">
            <div class="type-toggle">
              <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': txForm.type === 'expense' }" @click="txForm.type = 'expense'">支出</button>
              <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': txForm.type === 'income' }" @click="txForm.type = 'income'">收入</button>
              <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': txForm.type === 'transfer' }" @click="txForm.type = 'transfer'">转账</button>
            </div>
            <div class="form-group">
              <label class="form-label" for="tx-amount">金额</label>
              <input id="tx-amount" v-model.number="txForm.amount" type="number" class="form-input form-input--amount" min="0.01" step="0.01" required />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="tx-account">{{ txForm.type === 'transfer' ? '转出账户' : '账户' }}</label>
                <select id="tx-account" v-model="txForm.account_id" class="form-input" required>
                  <option value="" disabled>选择账户</option>
                  <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
                </select>
              </div>
              <div v-if="txForm.type === 'transfer'" class="form-group">
                <label class="form-label" for="tx-to-account">转入账户</label>
                <select id="tx-to-account" v-model="txForm.to_account_id" class="form-input" required>
                  <option value="" disabled>选择账户</option>
                  <option v-for="a in accounts" :key="a.id" :value="a.id" :disabled="a.id === txForm.account_id">{{ a.name }}</option>
                </select>
              </div>
            </div>
            <div v-if="txForm.type !== 'transfer'" class="form-group">
              <label class="form-label">分类</label>
              <div class="category-grid">
                <button v-for="cat in filteredCategories" :key="cat.id" type="button" class="category-chip" :class="{ 'category-chip--active': txForm.category_id === cat.id }" @click="txForm.category_id = cat.id">
                  {{ cat.name }}
                </button>
                <div v-if="filteredCategories.length === 0" class="category-empty">暂无分类</div>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="tx-desc">备注</label>
              <input id="tx-desc" v-model="txForm.description" type="text" class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label class="form-label" for="tx-date">日期</label>
              <input id="tx-date" v-model="txForm.date" type="date" class="form-input" required />
            </div>
            <div v-if="txDialogError" class="dialog-error" role="alert">{{ txDialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="savingTx || !txForm.amount || !txForm.account_id">
                <span v-if="savingTx" class="loading-spinner loading-spinner--sm"></span>
                {{ savingTx ? '保存中…' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="cancelDelete">
        <div class="dialog dialog--confirm" role="dialog" aria-modal="true" aria-labelledby="del-dialog-title" tabindex="-1" @keydown.escape="cancelDelete">
          <div class="dialog-header">
            <h3 id="del-dialog-title" class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="cancelDelete" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">确定要删除这笔流水记录吗？此操作无法撤销。</p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDelete">取消</button>
              <button type="button" class="btn-danger" :disabled="deleting" @click="deleteTransaction">
                <span v-if="deleting" class="loading-spinner loading-spinner--sm"></span>
                {{ deleting ? '删除中…' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { financeService } from '../services/finance'
import { useToast } from '../composables/useToast'
import { getErrorMessage } from '../utils/errorMessage'
import { labelTransactionType } from '../utils/displayLabels'

const { successToast, errorToast, showSuccess, showError } = useToast()

const transactions = ref([])
const accounts = ref([])
const categories = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const error = ref(null)
const accountsError = ref(null)
const categoriesError = ref(null)
const loadMoreError = ref(null)
const supportLoading = ref(false)
const page = ref(1)
const hasMore = ref(false)
let requestSequence = 0
let filterGeneration = 0
let supportRequestId = 0

const supportError = computed(() => accountsError.value || categoriesError.value)

const filters = ref({
  type: '',
  account_id: '',
  category_id: '',
  start_date: '',
  end_date: ''
})

const typeFilters = [
  { value: '' },
  { value: 'income' },
  { value: 'expense' },
  { value: 'transfer' }
]

const showDialog = ref(false)
const editingTx = ref(null)
const savingTx = ref(false)
const txDialogError = ref(null)

const showDeleteDialog = ref(false)
const deletingTx = ref(null)
const deleting = ref(false)

const today = new Date().toISOString().split('T')[0]

const txForm = ref({
  type: 'expense', amount: null, account_id: '', to_account_id: '',
  category_id: '', description: '', date: today
})

const filteredCategories = computed(() => {
  return categories.value.filter(c => c.type === txForm.value.type)
})

const filteredIncome = computed(() => {
  return transactions.value.filter(t => t.type === 'income').reduce((s, t) => s + Number(t.amount || 0), 0)
})

const filteredExpense = computed(() => {
  return transactions.value.filter(t => t.type === 'expense').reduce((s, t) => s + Number(t.amount || 0), 0)
})

const filteredNet = computed(() => filteredIncome.value - filteredExpense.value)

const activeFilterCount = computed(() => {
  return ['type', 'account_id', 'category_id', 'start_date', 'end_date'].filter(key => !!filters.value[key]).length
})

const groupedTransactions = computed(() => {
  const groups = {}
  for (const tx of transactions.value) {
    const key = (tx.date || '').split('T')[0]
    if (!groups[key]) groups[key] = []
    groups[key].push(tx)
  }
  return groups
})

function groupIncome(group) { return group.filter(t => t.type === 'income').reduce((s, t) => s + Number(t.amount || 0), 0) }
function groupExpense(group) { return group.filter(t => t.type === 'expense').reduce((s, t) => s + Number(t.amount || 0), 0) }

function formatMoney(val) { return Number(val || 0).toFixed(2) }

function formatGroupDate(dateKey) {
  if (!dateKey) return ''
  const d = new Date(dateKey + 'T00:00:00')
  const today = new Date()
  const todayStr = today.toISOString().split('T')[0]
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const yesterdayStr = yesterday.toISOString().split('T')[0]
  if (dateKey === todayStr) return '今天'
  if (dateKey === yesterdayStr) return '昨天'
  return d.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' })
}

function resetTxForm() {
  txForm.value = { type: 'expense', amount: null, account_id: '', to_account_id: '', category_id: '', description: '', date: today }
  txDialogError.value = null
  editingTx.value = null
}

function openCreate() { resetTxForm(); showDialog.value = true }

function openEdit(tx) {
  editingTx.value = tx
  txForm.value = {
    type: tx.type, amount: tx.amount, account_id: tx.account_id || '',
    to_account_id: tx.to_account_id || '', category_id: tx.category_id || '',
    description: tx.description || '', date: (tx.date || '').split('T')[0]
  }
  txDialogError.value = null
  showDialog.value = true
}

function cancelDialog() { showDialog.value = false; resetTxForm() }

function openDelete(tx) { deletingTx.value = tx; showDeleteDialog.value = true }
function cancelDelete() { showDeleteDialog.value = false; deletingTx.value = null }

async function fetchTransactions() {
  const requestId = ++requestSequence
  const generation = ++filterGeneration
  loading.value = true
  error.value = null
  loadMoreError.value = null
  loadingMore.value = false
  hasMore.value = false
  page.value = 1
  try {
    const params = { page: 1, limit: 50 }
    if (filters.value.type) params.type = filters.value.type
    if (filters.value.account_id) params.account_id = filters.value.account_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = await financeService.getTransactions(params)
    if (requestId !== requestSequence) return
    transactions.value = Array.isArray(data) ? data : (data.items || data.transactions || [])
    hasMore.value = data.has_more || (Array.isArray(data) ? false : (data.total > transactions.value.length))
  } catch (e) {
    if (requestId === requestSequence) error.value = getErrorMessage(e)
  } finally {
    if (requestId === requestSequence) loading.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  const requestId = ++requestSequence
  const generation = filterGeneration
  const nextPage = page.value + 1
  loadingMore.value = true
  loadMoreError.value = null
  try {
    const params = { page: nextPage, limit: 50 }
    if (filters.value.type) params.type = filters.value.type
    if (filters.value.account_id) params.account_id = filters.value.account_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = await financeService.getTransactions(params)
    const items = Array.isArray(data) ? data : (data.items || data.transactions || [])
    if (requestId !== requestSequence || generation !== filterGeneration) return
    transactions.value.push(...items)
    page.value = nextPage
    hasMore.value = data.has_more || false
  } catch (e) {
    if (requestId === requestSequence && generation === filterGeneration) {
      loadMoreError.value = getErrorMessage(e, '加载更多流水失败，请重试。')
    }
  } finally {
    if (requestId === requestSequence && generation === filterGeneration) loadingMore.value = false
  }
}

async function fetchSupportData() {
  const requestId = ++supportRequestId
  supportLoading.value = true
  accountsError.value = null
  categoriesError.value = null
  try {
    const [accountResult, categoryResult] = await Promise.allSettled([
      Promise.resolve().then(() => financeService.getAccounts()),
      Promise.resolve().then(() => financeService.getCategories()),
    ])
    if (requestId !== supportRequestId) return

    if (accountResult.status === 'fulfilled') {
      const data = accountResult.value
      accounts.value = Array.isArray(data) ? data : (data.items || data.accounts || [])
    } else {
      accountsError.value = getErrorMessage(accountResult.reason, '加载账户失败，请重试。')
    }

    if (categoryResult.status === 'fulfilled') {
      const data = categoryResult.value
      categories.value = Array.isArray(data) ? data : (data.items || data.categories || [])
    } else {
      categoriesError.value = getErrorMessage(categoryResult.reason, '加载分类失败，请重试。')
    }
  } finally {
    if (requestId === supportRequestId) supportLoading.value = false
  }
}

async function saveTransaction() {
  if (!txForm.value.amount || !txForm.value.account_id) return
  if (txForm.value.type === 'transfer' && !txForm.value.to_account_id) {
    txDialogError.value = '请选择转入账户'
    return
  }
  savingTx.value = true
  txDialogError.value = null
  try {
    if (editingTx.value) {
      await financeService.updateTransaction(editingTx.value.id, {
        type: txForm.value.type,
        amount: txForm.value.amount,
        account_id: txForm.value.account_id,
        to_account_id: txForm.value.type === 'transfer' ? txForm.value.to_account_id : null,
        category_id: txForm.value.type === 'transfer' ? null : (txForm.value.category_id || null),
        description: txForm.value.description || undefined,
        date: txForm.value.date
      })
    } else if (txForm.value.type === 'transfer') {
      await financeService.transfer({
        from_account_id: txForm.value.account_id,
        to_account_id: txForm.value.to_account_id,
        amount: txForm.value.amount,
        description: txForm.value.description || undefined,
        date: txForm.value.date
      })
    } else {
      await financeService.createTransaction({
        type: txForm.value.type, amount: txForm.value.amount,
        account_id: txForm.value.account_id,
        category_id: txForm.value.category_id || undefined,
        description: txForm.value.description || undefined,
        date: txForm.value.date
      })
    }
    const wasEditing = !!editingTx.value
    cancelDialog()
    showSuccess(wasEditing ? '流水已更新' : '记账成功')
    await fetchTransactions()
  } catch (e) {
    txDialogError.value = getErrorMessage(e)
  } finally {
    savingTx.value = false
  }
}

async function deleteTransaction() {
  if (!deletingTx.value) return
  deleting.value = true
  try {
    await financeService.deleteTransaction(deletingTx.value.id)
    transactions.value = transactions.value.filter(t => t.id !== deletingTx.value.id)
    showSuccess('流水已删除')
    cancelDelete()
  } catch (e) {
    showError(getErrorMessage(e))
    cancelDelete()
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchSupportData()
  fetchTransactions()
})
</script>

<style scoped>
.finance-page {
  display: grid;
  gap: var(--page-gap);
  width: 100%;
  padding: var(--spacing-xl);
  overflow-x: clip;
}

.page-header,
.header-left,
.summary-panel__header,
.date-group-header,
.dialog-header,
.dialog-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.header-left,
.page-heading,
.summary-panel,
.filter-bar,
.transactions-section,
.date-group,
.date-group-list,
.tx-info,
.form-group,
.dialog-body {
  min-width: 0;
}

.page-heading,
.summary-panel,
.tx-info,
.form-group,
.dialog-body,
.transactions-section,
.date-group {
  display: grid;
}

.page-heading,
.summary-panel,
.tx-info,
.dialog-body,
.transactions-section,
.date-group {
  gap: var(--spacing-sm);
}

.page-subtitle,
.summary-panel__label,
.summary-panel__meta,
.summary-stat__label,
.tx-meta,
.empty-text,
.confirm-text,
.dialog-error {
  color: var(--color-text-tertiary);
}

.page-subtitle,
.summary-stat__label,
.summary-panel__meta,
.tx-meta,
.empty-text {
  font-size: var(--font-size-sm);
}

.page-title,
.summary-panel__title,
.section-title,
.dialog-title {
  margin: 0;
  color: var(--color-text);
}

.page-title {
  font-size: clamp(1.4rem, 1.15rem + 0.6vw, 1.85rem);
  font-weight: 700;
}

.page-subtitle {
  margin: 0;
  max-width: 48rem;
}

.btn-back,
.btn-icon,
.dialog-close {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background var(--transition-base), border-color var(--transition-base), color var(--transition-base), transform var(--transition-base);
}

.btn-back:hover,
.btn-icon:hover,
.dialog-close:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.btn-create,
.btn-load-more,
.btn-primary,
.btn-secondary,
.btn-danger,
.retry-btn,
.filter-btn,
.type-toggle-btn,
.category-chip {
  min-height: 44px;
  font-family: var(--font-family);
  cursor: pointer;
  transition: background var(--transition-base), border-color var(--transition-base), color var(--transition-base), transform var(--transition-base), box-shadow var(--transition-base), opacity var(--transition-base);
}

.btn-create,
.btn-load-more,
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: 0.75rem 1.05rem;
  border: none;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  box-shadow: var(--shadow-sm);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.btn-create:hover,
.btn-load-more:hover,
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-secondary,
.retry-btn,
.filter-btn,
.type-toggle-btn {
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text-secondary);
  border-radius: 14px;
  padding: 0.65rem 0.9rem;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.btn-secondary:hover,
.retry-btn:hover,
.filter-btn:hover,
.type-toggle-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 14px;
  background: var(--color-error);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.btn-danger:hover { opacity: 0.92; }

.btn-create svg,
.btn-back svg,
.dialog-close svg { width: 18px; height: 18px; }

.finance-summary-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: var(--page-gap);
}

.summary-panel {
  padding: clamp(1rem, 0.8rem + 0.6vw, 1.5rem);
  border-radius: var(--surface-radius);
}

.summary-panel--primary {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(29, 78, 216, 0.06)), var(--color-card);
}

.summary-panel__eyebrow,
.section-eyebrow {
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-tertiary);
}

.summary-panel__hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.summary-panel__value {
  font-size: clamp(2rem, 1.55rem + 1vw, 2.75rem);
  font-weight: 700;
  color: var(--color-text);
  line-height: 1;
  margin-top: 4px;
}

.summary-panel__value.is-positive { color: var(--color-success-dark); }
.summary-panel__value.is-negative { color: var(--color-error-dark); }

.summary-pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
}

.summary-chip-row,
.summary-stats,
.filter-type-group,
.category-grid,
.tx-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.summary-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  min-height: 32px;
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.summary-tag svg { width: 16px; height: 16px; }
.summary-tag--income { background: rgba(34, 197, 94, 0.12); color: var(--color-success-dark); }
.summary-tag--expense { background: rgba(239, 68, 68, 0.12); color: var(--color-error-dark); }

.summary-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }

.summary-stat {
  display: grid;
  gap: 4px;
  padding: 0.9rem;
  border-radius: 14px;
  border: 1px solid rgba(168, 215, 232, 0.45);
  background: rgba(255, 255, 255, 0.72);
}

.summary-stat__value {
  font-size: var(--font-size-lg);
  color: var(--color-text);
}

.summary-panel__title,
.section-title {
  font-size: var(--font-size-xl);
}

.filter-bar {
  display: grid;
  gap: var(--spacing-md);
}

.filter-type-group { gap: 8px; }

.filter-btn--active,
.type-toggle-btn--active,
.category-chip--active {
  background: rgba(14, 165, 233, 0.12);
  border-color: rgba(14, 165, 233, 0.25);
  color: var(--color-primary-dark);
}

.filter-selects,
.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
}

.filter-select,
.form-input {
  width: 100%;
  min-width: 0;
  min-height: 44px;
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-bg-secondary);
  color: var(--color-text);
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.filter-select:focus,
.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.12);
}

.transactions-section { gap: var(--spacing-md); }

.date-group {
  padding: clamp(1rem, 0.85rem + 0.3vw, 1.3rem);
  gap: var(--spacing-sm);
}

.date-group-header {
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border);
}

.date-group-label {
  font-size: var(--font-size-base);
  font-weight: 700;
  color: var(--color-text);
}

.date-group-sum {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.date-group-list { gap: 0; }

.tx-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--spacing-md);
  padding: 0.95rem 0;
  border-bottom: 1px solid rgba(217, 231, 239, 0.72);
}

.tx-item:last-child { border-bottom: none; }

.tx-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tx-icon svg { width: 18px; height: 18px; }
.tx-icon--income { background: rgba(34, 197, 94, 0.12); color: var(--color-success-dark); }
.tx-icon--expense { background: rgba(239, 68, 68, 0.12); color: var(--color-error-dark); }
.tx-icon--transfer { background: rgba(29, 78, 216, 0.12); color: var(--color-secondary); }

.tx-desc {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tx-right { text-align: right; }

.tx-amount {
  font-size: var(--font-size-base);
  font-weight: 700;
}

.tx-amount--income { color: var(--color-success-dark); }
.tx-amount--expense { color: var(--color-error-dark); }
.tx-amount--transfer { color: var(--color-secondary); }

.btn-icon {
  width: var(--touch-target-min);
  height: var(--touch-target-min);
}

.btn-icon svg { width: 14px; height: 14px; }
.btn-icon--edit:hover { background: rgba(14, 165, 233, 0.12); color: var(--color-primary-dark); }
.btn-icon--delete:hover { background: rgba(239, 68, 68, 0.12); color: var(--color-error-dark); }

.loading-state,
.error-state,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 280px;
  gap: var(--spacing-md);
  text-align: center;
}

.empty-state,
.error-state {
  padding: var(--spacing-xl);
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: 22px;
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon svg { width: 36px; height: 36px; color: var(--color-text-tertiary); }
.empty-title { margin: 0; font-size: var(--font-size-lg); color: var(--color-text); }

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

.load-more {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-sm);
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8, 15, 28, 0.48);
}

.dialog {
  width: min(100%, 520px);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 22px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.dialog--wide { width: min(100%, 560px); }
.dialog--confirm { width: min(100%, 420px); }

.dialog-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.dialog-body { padding: var(--spacing-lg); }

.type-toggle {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  padding: 6px;
  border-radius: 16px;
  background: var(--color-bg-tertiary);
}

.type-toggle-btn {
  border-radius: 12px;
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text);
}

.form-input--amount {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  text-align: center;
}

.category-grid { gap: 8px; }

.category-chip {
  min-height: 36px;
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.category-empty {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  padding: 0.4rem 0;
}

.confirm-text {
  margin: 0;
  line-height: 1.6;
  font-size: var(--font-size-sm);
}

.success-toast,
.error-toast {
  position: fixed;
  right: var(--spacing-lg);
  z-index: 1100;
  max-width: calc(100vw - 32px);
}

.success-toast { top: var(--spacing-lg); }
.error-toast { top: calc(var(--spacing-lg) + 60px); }

.success-toast-content,
.error-toast-content {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: 14px;
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
  box-shadow: var(--shadow-lg);
}

.success-toast-content { background: var(--color-success); }
.error-toast-content { background: var(--color-error); }

.success-toast-content svg,
.error-toast-content svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

@media (max-width: 1199px) {
  .finance-page {
    padding: var(--spacing-lg);
  }

  .finance-summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .finance-page {
    padding: var(--spacing-md);
    padding-bottom: calc(var(--spacing-md) + var(--bottom-nav-height));
  }

  .page-header,
  .header-left,
  .summary-panel__header,
  .summary-panel__hero,
  .date-group-header,
  .dialog-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-left {
    width: 100%;
  }

  .btn-create {
    width: 100%;
  }

  .summary-stats,
  .filter-selects,
  .form-row {
    grid-template-columns: 1fr;
  }

  .tx-item {
    grid-template-columns: auto minmax(0, 1fr);
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .tx-right {
    grid-column: 2;
    text-align: left;
  }

  .tx-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
    width: 100%;
  }

  .dialog-overlay {
    padding: var(--spacing-sm);
    align-items: flex-end;
  }

  .dialog {
    width: 100%;
    max-height: calc(100vh - 24px);
    overflow-y: auto;
  }

  .success-toast,
  .error-toast {
    left: var(--spacing-md);
    right: var(--spacing-md);
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Stitch refinement: dense transactions use cards and safe horizontal filter space. */
.finance-page {
  min-width: 0;
}

.summary-panel,
.filter-bar,
.transactions-section,
.date-group,
.tx-info,
.tx-actions,
.dialog-body {
  min-width: 0;
}

.btn-back,
.btn-icon,
.dialog-close,
.btn-create,
.btn-load-more,
.btn-primary,
.btn-secondary,
.btn-danger,
.filter-btn,
.type-toggle-btn {
  min-height: 44px;
}

.btn-back:focus-visible,
.btn-icon:focus-visible,
.dialog-close:focus-visible,
.btn-create:focus-visible,
.btn-load-more:focus-visible,
.btn-primary:focus-visible,
.btn-secondary:focus-visible,
.btn-danger:focus-visible,
.filter-btn:focus-visible,
.type-toggle-btn:focus-visible,
.filter-select:focus-visible,
.form-input:focus-visible {
  outline: 3px solid rgba(14, 165, 233, 0.35);
  outline-offset: 2px;
}

.filter-bar {
  align-items: stretch;
}

.filter-type-group {
  flex-wrap: wrap;
}

.filter-selects {
  min-width: 0;
}

.date-group-list {
  min-width: 0;
  overflow: hidden;
}

.tx-item {
  min-width: 0;
}

.tx-desc,
.tx-meta,
.tx-amount {
  overflow-wrap: anywhere;
}

.dialog-overlay {
  z-index: 1200;
  padding: max(var(--spacing-md), env(safe-area-inset-top)) var(--spacing-md) max(var(--spacing-md), env(safe-area-inset-bottom));
}

.dialog {
  max-height: min(720px, calc(100dvh - 2 * var(--spacing-md)));
  overflow-y: auto;
  overscroll-behavior: contain;
}

@media (max-width: 767px) {
  .finance-page {
    padding-bottom: calc(var(--spacing-md) + var(--bottom-nav-height) + env(safe-area-inset-bottom));
  }

  .filter-bar {
    gap: 10px;
  }

  .filter-type-group {
    width: 100%;
    overflow-x: auto;
    flex-wrap: nowrap;
    scrollbar-width: thin;
    padding-bottom: 2px;
  }

  .filter-btn {
    flex: 0 0 auto;
    white-space: nowrap;
  }

  .filter-selects {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .tx-item {
    grid-template-columns: 40px minmax(0, 1fr);
    align-items: start;
    padding: 14px 12px;
  }

  .tx-right {
    grid-column: 2;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 10px;
    text-align: left;
  }

  .tx-actions {
    grid-column: 1 / -1;
    width: 100%;
    justify-content: flex-end;
  }

  .dialog-overlay {
    align-items: flex-end;
    padding: 8px 8px max(8px, env(safe-area-inset-bottom));
  }

  .dialog {
    width: 100%;
    max-height: calc(100dvh - 16px);
    border-radius: var(--surface-radius) var(--surface-radius) 18px 18px;
  }
}
</style>
