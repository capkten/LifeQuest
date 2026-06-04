<template>
  <div class="finance-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push('/finance')" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 class="page-title">全部流水</h2>
      </div>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        记一笔
      </button>
    </div>

    <!-- Summary -->
    <div class="filter-summary">
      <span class="summary-tag summary-tag--income">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></svg>
        收入 {{ formatMoney(filteredIncome) }}
      </span>
      <span class="summary-tag summary-tag--expense">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" /></svg>
        支出 {{ formatMoney(filteredExpense) }}
      </span>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <div class="filter-type-group">
        <button v-for="t in typeFilters" :key="t.value" class="filter-btn" :class="{ 'filter-btn--active': filters.type === t.value }" @click="filters.type = t.value; fetchTransactions()">
          {{ t.label }}
        </button>
      </div>
      <div class="filter-selects">
        <select v-model="filters.account_id" class="filter-select" @change="fetchTransactions()">
          <option value="">全部账户</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <select v-model="filters.category_id" class="filter-select" @change="fetchTransactions()">
          <option value="">全部分类</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <input v-model="filters.start_date" type="date" class="filter-select" @change="fetchTransactions()" />
        <input v-model="filters.end_date" type="date" class="filter-select" @change="fetchTransactions()" />
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchTransactions">重试</button>
    </div>

    <div v-else-if="transactions.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      </div>
      <h3 class="empty-title">暂无流水记录</h3>
      <p class="empty-text">开始记账来查看你的收支流水。</p>
    </div>

    <template v-else>
      <!-- Grouped by date -->
      <div v-for="(group, dateKey) in groupedTransactions" :key="dateKey" class="date-group">
        <div class="date-group-header">
          <span class="date-group-label">{{ formatGroupDate(dateKey) }}</span>
          <span class="date-group-sum">
            收 {{ formatMoney(groupIncome(group)) }} / 支 {{ formatMoney(groupExpense(group)) }}
          </span>
        </div>
        <div class="date-group-list">
          <div v-for="tx in group" :key="tx.id" class="tx-item">
            <div class="tx-icon">
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
              <span class="tx-meta">{{ tx.category_name || '' }} {{ tx.account_name ? '- ' + tx.account_name : '' }}</span>
            </div>
            <div class="tx-right">
              <span class="tx-amount" :class="'tx-amount--' + tx.type">
                {{ tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : '' }}{{ formatMoney(tx.amount) }}
              </span>
            </div>
            <div class="tx-actions">
              <button class="btn-icon btn-icon--edit" @click="openEdit(tx)" aria-label="编辑">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
              </button>
              <button class="btn-icon btn-icon--delete" @click="openDelete(tx)" aria-label="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Load More -->
      <div v-if="hasMore" class="load-more">
        <button class="btn-load-more" :disabled="loadingMore" @click="loadMore">
          <span v-if="loadingMore" class="loading-spinner loading-spinner--sm"></span>
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </template>

    <!-- Create/Edit Transaction Modal -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div class="dialog dialog--wide" role="dialog" aria-modal="true" aria-labelledby="tx-dialog-title" @keydown.escape="cancelDialog">
          <div class="dialog-header">
            <h3 id="tx-dialog-title" class="dialog-title">{{ editingTx ? '编辑流水' : '记一笔' }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
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
                {{ savingTx ? '保存中...' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="cancelDelete">
        <div class="dialog dialog--confirm" role="dialog" aria-modal="true" aria-labelledby="del-dialog-title" @keydown.escape="cancelDelete">
          <div class="dialog-header">
            <h3 id="del-dialog-title" class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="cancelDelete" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">确定要删除这笔流水记录吗？此操作无法撤销。</p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDelete">取消</button>
              <button type="button" class="btn-danger" :disabled="deleting" @click="deleteTransaction">
                <span v-if="deleting" class="loading-spinner loading-spinner--sm"></span>
                {{ deleting ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="successToast" class="success-toast" role="status" aria-live="polite">
          <div class="success-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="20 6 9 17 4 12" /></svg>
            <span>{{ successToast }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="errorToast" class="error-toast" role="status" aria-live="polite">
          <div class="error-toast-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
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

const { successToast, errorToast, showSuccess, showError } = useToast()

const transactions = ref([])
const accounts = ref([])
const categories = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const error = ref(null)
const page = ref(1)
const hasMore = ref(false)

const filters = ref({
  type: '',
  account_id: '',
  category_id: '',
  start_date: '',
  end_date: ''
})

const typeFilters = [
  { value: '', label: '全部' },
  { value: 'income', label: '收入' },
  { value: 'expense', label: '支出' },
  { value: 'transfer', label: '转账' }
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
  loading.value = true
  error.value = null
  page.value = 1
  try {
    const params = { page: 1, limit: 50 }
    if (filters.value.type) params.type = filters.value.type
    if (filters.value.account_id) params.account_id = filters.value.account_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = await financeService.getTransactions(params)
    transactions.value = Array.isArray(data) ? data : (data.items || data.transactions || [])
    hasMore.value = data.has_more || (Array.isArray(data) ? false : (data.total > transactions.value.length))
  } catch (e) {
    error.value = '加载流水失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  loadingMore.value = true
  page.value++
  try {
    const params = { page: page.value, limit: 50 }
    if (filters.value.type) params.type = filters.value.type
    if (filters.value.account_id) params.account_id = filters.value.account_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = await financeService.getTransactions(params)
    const items = Array.isArray(data) ? data : (data.items || data.transactions || [])
    transactions.value.push(...items)
    hasMore.value = data.has_more || false
  } catch (e) {
    page.value--
  } finally {
    loadingMore.value = false
  }
}

async function fetchSupportData() {
  try {
    const [acctData, catData] = await Promise.all([
      financeService.getAccounts().catch(() => []),
      financeService.getCategories().catch(() => [])
    ])
    accounts.value = Array.isArray(acctData) ? acctData : (acctData.items || acctData.accounts || [])
    categories.value = Array.isArray(catData) ? catData : (catData.items || catData.categories || [])
  } catch (e) {
    // Non-critical
  }
}

async function saveTransaction() {
  if (!txForm.value.amount || !txForm.value.account_id) return
  savingTx.value = true
  txDialogError.value = null
  try {
    if (txForm.value.type === 'transfer') {
      await financeService.transfer({
        from_account_id: txForm.value.account_id,
        to_account_id: txForm.value.to_account_id,
        amount: txForm.value.amount,
        description: txForm.value.description || undefined,
        date: txForm.value.date
      })
    } else if (editingTx.value) {
      await financeService.updateTransaction(editingTx.value.id, {
        type: txForm.value.type, amount: txForm.value.amount,
        account_id: txForm.value.account_id,
        category_id: txForm.value.category_id || undefined,
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
    cancelDialog()
    showSuccess(editingTx.value ? '流水已更新' : '记账成功！')
    await fetchTransactions()
  } catch (e) {
    txDialogError.value = e.response?.data?.detail || '保存失败，请重试。'
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
    showError(e.response?.data?.detail || '删除失败，请重试。')
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
.finance-page { padding: var(--spacing-xl); width: 100%; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}
.header-left { display: flex; align-items: center; gap: var(--spacing-md); }

.btn-back {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid var(--color-border);
  border-radius: var(--radius-md); cursor: pointer;
  color: var(--color-text-secondary); transition: all 0.15s ease;
}
.btn-back:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.btn-back svg { width: 20px; height: 20px; }

.page-title { font-size: var(--font-size-2xl); font-weight: 700; color: var(--color-text); }

.btn-create {
  display: inline-flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm); font-weight: 600; color: #fff;
  background: var(--color-primary); border: none;
  border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: background 0.15s ease;
}
.btn-create:hover { background: var(--color-primary-dark); }
.btn-create svg { width: 18px; height: 18px; }

/* Summary */
.filter-summary {
  display: flex; gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.summary-tag {
  display: inline-flex; align-items: center; gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm); font-weight: 600;
  border-radius: var(--radius-full);
}
.summary-tag svg { width: 16px; height: 16px; }
.summary-tag--income { background: rgba(81, 207, 102, 0.12); color: var(--color-success); }
.summary-tag--expense { background: rgba(255, 107, 107, 0.12); color: var(--color-error); }

/* Filter Bar */
.filter-bar {
  display: flex; flex-wrap: wrap; gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg); align-items: center;
}
.filter-type-group { display: flex; gap: 2px; background: var(--color-bg-tertiary); border-radius: var(--radius-md); padding: 2px; }
.filter-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-xs); font-weight: 500;
  color: var(--color-text-secondary); background: transparent;
  border: none; border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: all 0.15s ease;
}
.filter-btn--active { background: var(--color-card); color: var(--color-text); box-shadow: var(--shadow-sm); }

.filter-selects { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); }
.filter-select {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-xs); font-family: var(--font-family);
  color: var(--color-text); background: var(--color-card);
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
  outline: none; cursor: pointer;
}
.filter-select:focus { border-color: var(--color-primary); }

/* States */
.loading-state { display: flex; align-items: center; justify-content: center; min-height: 300px; }
.loading-spinner {
  width: 32px; height: 32px; border: 3px solid var(--color-border);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.loading-spinner--sm { width: 16px; height: 16px; border-width: 2px; }
@keyframes spin { to { transform: rotate(360deg); } }

.error-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 300px; gap: var(--spacing-md);
  color: var(--color-error); font-size: var(--font-size-sm);
}
.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md); font-size: var(--font-size-sm);
  color: var(--color-primary); background: transparent;
  border: 1px solid var(--color-primary); border-radius: var(--radius-md);
  cursor: pointer; font-family: var(--font-family); transition: all 0.15s ease;
}
.retry-btn:hover { background: var(--color-primary); color: #fff; }

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 400px; text-align: center;
}
.empty-icon {
  width: 72px; height: 72px; border-radius: var(--radius-xl);
  background: var(--color-bg-tertiary); display: flex;
  align-items: center; justify-content: center; margin-bottom: var(--spacing-lg);
}
.empty-icon svg { width: 36px; height: 36px; color: var(--color-text-tertiary); }
.empty-title { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text); margin-bottom: var(--spacing-sm); }
.empty-text { font-size: var(--font-size-sm); color: var(--color-text-tertiary); max-width: 320px; }

/* Date Groups */
.date-group { margin-bottom: var(--spacing-lg); }
.date-group-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--spacing-sm) 0; margin-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border);
}
.date-group-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }
.date-group-sum { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.date-group-list {
  display: flex; flex-direction: column; gap: 2px;
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); overflow: hidden;
}

.tx-item {
  display: flex; align-items: center; gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  transition: background 0.15s ease;
}
.tx-item:hover { background: var(--color-bg-tertiary); }

.tx-icon {
  width: 32px; height: 32px; border-radius: var(--radius-full);
  background: var(--color-bg-tertiary); display: flex;
  align-items: center; justify-content: center; flex-shrink: 0;
}
.tx-icon svg { width: 16px; height: 16px; color: var(--color-primary); }

.tx-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.tx-desc {
  font-size: var(--font-size-sm); font-weight: 500; color: var(--color-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tx-meta { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.tx-right { flex-shrink: 0; text-align: right; }
.tx-amount { font-size: var(--font-size-sm); font-weight: 700; }
.tx-amount--income { color: var(--color-success); }
.tx-amount--expense { color: var(--color-error); }
.tx-amount--transfer { color: var(--color-secondary); }

.tx-actions { display: flex; gap: 4px; flex-shrink: 0; opacity: 0; transition: opacity 0.15s ease; }
.tx-item:hover .tx-actions { opacity: 1; }

.btn-icon {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid var(--color-border);
  border-radius: var(--radius-md); cursor: pointer;
  color: var(--color-text-tertiary); transition: all 0.15s ease;
}
.btn-icon svg { width: 13px; height: 13px; }
.btn-icon--edit:hover { background: var(--color-primary); border-color: var(--color-primary); color: #fff; }
.btn-icon--delete:hover { background: var(--color-error); border-color: var(--color-error); color: #fff; }

/* Load More */
.load-more { display: flex; justify-content: center; padding: var(--spacing-lg) 0; }
.btn-load-more {
  display: inline-flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-xl);
  font-size: var(--font-size-sm); font-weight: 500;
  color: var(--color-primary); background: transparent;
  border: 1px solid var(--color-primary); border-radius: var(--radius-md);
  cursor: pointer; font-family: var(--font-family); transition: all 0.15s ease;
}
.btn-load-more:hover { background: var(--color-primary); color: #fff; }
.btn-load-more:disabled { opacity: 0.6; cursor: not-allowed; }

/* Dialog */
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: var(--spacing-lg);
}
.dialog {
  width: 100%; max-width: 480px; background: var(--color-card);
  border: 1px solid var(--color-border); border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl); overflow: hidden;
}
.dialog--wide { max-width: 520px; }
.dialog--confirm { max-width: 400px; }

.dialog-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--spacing-lg); border-bottom: 1px solid var(--color-border);
}
.dialog-title { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text); }
.dialog-close {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: var(--radius-md);
  cursor: pointer; color: var(--color-text-tertiary); transition: background 0.15s ease;
}
.dialog-close:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.dialog-close svg { width: 18px; height: 18px; }

.dialog-body { padding: var(--spacing-lg); display: flex; flex-direction: column; gap: var(--spacing-md); }

.type-toggle {
  display: flex; background: var(--color-bg-tertiary);
  border-radius: var(--radius-md); padding: 3px; gap: 3px;
}
.type-toggle-btn {
  flex: 1; padding: var(--spacing-sm); font-size: var(--font-size-sm);
  font-weight: 600; color: var(--color-text-secondary);
  background: transparent; border: none; border-radius: var(--radius-md);
  cursor: pointer; font-family: var(--font-family); transition: all 0.15s ease;
}
.type-toggle-btn--active { background: var(--color-card); color: var(--color-text); box-shadow: var(--shadow-sm); }

.form-group { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.form-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }

.form-input {
  width: 100%; padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm); font-family: var(--font-family);
  color: var(--color-text); background: var(--color-bg-secondary);
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
  outline: none; transition: border-color 0.15s ease; box-sizing: border-box;
}
.form-input:focus { border-color: var(--color-primary); }
select.form-input { appearance: auto; }
.form-input--amount { font-size: var(--font-size-2xl); font-weight: 700; text-align: center; padding: var(--spacing-md); }

.category-grid { display: flex; flex-wrap: wrap; gap: var(--spacing-xs); }
.category-chip {
  padding: var(--spacing-xs) var(--spacing-md); font-size: var(--font-size-xs);
  font-weight: 500; color: var(--color-text-secondary);
  background: var(--color-bg-tertiary); border: 1px solid transparent;
  border-radius: var(--radius-full); cursor: pointer;
  font-family: var(--font-family); transition: all 0.15s ease;
}
.category-chip:hover { border-color: var(--color-primary); color: var(--color-primary); }
.category-chip--active { background: rgba(108, 99, 255, 0.12); border-color: var(--color-primary); color: var(--color-primary); }
.category-empty { font-size: var(--font-size-xs); color: var(--color-text-tertiary); padding: var(--spacing-xs) 0; }

.dialog-error { font-size: var(--font-size-sm); color: var(--color-error); padding: var(--spacing-xs) 0; }
.dialog-actions { display: flex; justify-content: flex-end; gap: var(--spacing-sm); padding-top: var(--spacing-sm); }

.btn-secondary {
  padding: var(--spacing-sm) var(--spacing-lg); font-size: var(--font-size-sm);
  font-weight: 500; color: var(--color-text-secondary);
  background: transparent; border: 1px solid var(--color-border);
  border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: background 0.15s ease;
}
.btn-secondary:hover { background: var(--color-bg-tertiary); }

.btn-primary {
  display: inline-flex; align-items: center; gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg); font-size: var(--font-size-sm);
  font-weight: 600; color: #fff; background: var(--color-primary);
  border: none; border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: background 0.15s ease;
}
.btn-primary:hover { background: var(--color-primary-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.confirm-text { font-size: var(--font-size-sm); color: var(--color-text-secondary); line-height: 1.6; }
.confirm-text strong { color: var(--color-text); }

.btn-danger {
  display: inline-flex; align-items: center; gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg); font-size: var(--font-size-sm);
  font-weight: 600; color: #fff; background: var(--color-error);
  border: none; border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: opacity 0.15s ease;
}
.btn-danger:hover { opacity: 0.9; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

/* Toast */
.success-toast { position: fixed; top: var(--spacing-lg); right: var(--spacing-lg); z-index: 1100; }
.success-toast-content {
  display: inline-flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg); background: var(--color-success);
  color: #fff; border-radius: var(--radius-md); font-size: var(--font-size-sm);
  font-weight: 600; box-shadow: var(--shadow-lg);
}
.success-toast-content svg { width: 18px; height: 18px; }

.error-toast { position: fixed; top: calc(var(--spacing-lg) + 60px); right: var(--spacing-lg); z-index: 1100; }
.error-toast-content {
  display: inline-flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg); background: var(--color-error);
  color: #fff; border-radius: var(--radius-md); font-size: var(--font-size-sm);
  font-weight: 600; box-shadow: var(--shadow-lg);
}
.error-toast-content svg { width: 18px; height: 18px; flex-shrink: 0; }

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-20px); }

/* Responsive */
@media (max-width: 1199px) { .finance-page { padding: var(--spacing-lg); } }

@media (max-width: 767px) {
  .finance-page { padding: var(--spacing-md); }
  .page-header { flex-direction: column; align-items: flex-start; gap: var(--spacing-md); }
  .filter-bar { flex-direction: column; }
  .filter-selects { width: 100%; }
  .filter-select { flex: 1; min-width: 0; }
  .tx-actions { opacity: 1; }
  .form-row { grid-template-columns: 1fr; }
  .dialog { max-width: 100%; margin: var(--spacing-sm); }
  .dialog-body { padding: var(--spacing-md); }
}
</style>
