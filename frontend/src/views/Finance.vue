<template>
  <div class="finance-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">记账</h2>
      </div>
      <button class="btn-create" @click="openQuickAdd">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        快速记账
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchDashboard">重试</button>
    </div>

    <template v-else>
      <!-- Account Cards -->
      <div class="accounts-row">
        <div v-if="accounts.length === 0" class="accounts-empty">
          <span>暂无账户</span>
        </div>
        <div
          v-for="acct in accounts"
          :key="acct.id"
          class="account-card"
          @click="$router.push('/finance/accounts')"
        >
          <div class="account-card-icon">
            <svg v-if="acct.type === 'cash'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M2 10h20" />
            </svg>
            <svg v-else-if="acct.type === 'bank'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M3 21h18" />
              <path d="M3 10h18" />
              <path d="M5 6l7-3 7 3" />
              <path d="M4 10v11" /><path d="M20 10v11" />
              <path d="M8 14v3" /><path d="M12 14v3" /><path d="M16 14v3" />
            </svg>
            <svg v-else-if="acct.type === 'credit'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
              <line x1="1" y1="10" x2="23" y2="10" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v12M6 12h12" />
            </svg>
          </div>
          <div class="account-card-info">
            <span class="account-card-name">{{ acct.name }}</span>
            <span class="account-card-balance">{{ formatMoney(acct.balance) }}</span>
          </div>
        </div>
      </div>

      <!-- Monthly Summary -->
      <div class="summary-card">
        <h3 class="summary-title">本月概览</h3>
        <div class="summary-grid">
          <div class="summary-item summary-item--income">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
              <polyline points="17 6 23 6 23 12" />
            </svg>
            <div class="summary-item-info">
              <span class="summary-item-label">收入</span>
              <span class="summary-item-value summary-item-value--income">+{{ formatMoney(dashboard.monthly_income || 0) }}</span>
            </div>
          </div>
          <div class="summary-item summary-item--expense">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
              <polyline points="17 18 23 18 23 12" />
            </svg>
            <div class="summary-item-info">
              <span class="summary-item-label">支出</span>
              <span class="summary-item-value summary-item-value--expense">-{{ formatMoney(dashboard.monthly_expense || 0) }}</span>
            </div>
          </div>
          <div class="summary-item summary-item--net">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="12" y1="1" x2="12" y2="23" />
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            <div class="summary-item-info">
              <span class="summary-item-label">结余</span>
              <span class="summary-item-value summary-item-value--net">{{ formatNet((dashboard.monthly_income || 0) - (dashboard.monthly_expense || 0)) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Budget Progress -->
      <div v-if="budgets.length > 0" class="budgets-card">
        <div class="section-header">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
              <path d="M22 12A10 10 0 0 0 12 2v10z" />
            </svg>
            预算进度
          </h3>
          <router-link to="/finance/budgets" class="section-link">管理预算</router-link>
        </div>
        <div class="budgets-body">
          <div v-for="b in budgets" :key="b.id" class="budget-item">
            <div class="budget-item-header">
              <span class="budget-item-name">{{ b.category_name || '未分类' }}</span>
              <span class="budget-item-amount">{{ formatMoney(b.spent || 0) }} / {{ formatMoney(b.amount) }}</span>
            </div>
            <div class="budget-progress-bar">
              <div
                class="budget-progress-fill"
                :class="budgetProgressClass(b)"
                :style="{ width: Math.min(budgetPercent(b), 100) + '%' }"
              ></div>
            </div>
            <span class="budget-item-remaining" :class="budgetProgressClass(b)">
              <template v-if="budgetPercent(b) > 100">超支 {{ formatMoney((b.spent || 0) - b.amount) }}</template>
              <template v-else>剩余 {{ formatMoney(b.amount - (b.spent || 0)) }}</template>
            </span>
          </div>
        </div>
      </div>

      <!-- Recent Transactions -->
      <div class="transactions-card">
        <div class="section-header">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            最近流水
          </h3>
          <router-link to="/finance/transactions" class="section-link">查看全部</router-link>
        </div>
        <div class="transactions-body">
          <div v-if="recentTransactions.length === 0" class="empty-state">
            <p>暂无流水记录，开始记账吧！</p>
          </div>
          <div v-else class="transaction-list">
            <div v-for="tx in recentTransactions" :key="tx.id" class="transaction-item">
              <div class="transaction-icon">
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
              <div class="transaction-info">
                <span class="transaction-desc">{{ tx.description || '无备注' }}</span>
                <span class="transaction-meta">{{ tx.category_name || '' }} {{ tx.account_name ? '- ' + tx.account_name : '' }}</span>
              </div>
              <div class="transaction-right">
                <span
                  class="transaction-amount"
                  :class="{
                    'transaction-amount--income': tx.type === 'income',
                    'transaction-amount--expense': tx.type === 'expense',
                    'transaction-amount--transfer': tx.type === 'transfer'
                  }"
                >
                  {{ tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : '' }}{{ formatMoney(tx.amount) }}
                </span>
                <span class="transaction-date">{{ formatDate(tx.date) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Links -->
      <div class="quick-links">
        <router-link to="/finance/accounts" class="quick-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="M2 10h20" />
          </svg>
          <span>账户管理</span>
        </router-link>
        <router-link to="/finance/transactions" class="quick-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <line x1="3" y1="6" x2="3.01" y2="6" />
            <line x1="3" y1="12" x2="3.01" y2="12" />
            <line x1="3" y1="18" x2="3.01" y2="18" />
          </svg>
          <span>全部流水</span>
        </router-link>
        <router-link to="/finance/budgets" class="quick-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
            <path d="M22 12A10 10 0 0 0 12 2v10z" />
          </svg>
          <span>预算管理</span>
        </router-link>
        <router-link to="/finance/debts" class="quick-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="8.5" cy="7" r="4" />
            <line x1="20" y1="8" x2="20" y2="14" />
            <line x1="23" y1="11" x2="17" y2="11" />
          </svg>
          <span>借贷管理</span>
        </router-link>
      </div>
    </template>

    <!-- Quick Add Transaction Modal -->
    <Teleport to="body">
      <div v-if="showQuickAdd" class="dialog-overlay" @click.self="cancelQuickAdd">
        <div class="dialog dialog--wide" role="dialog" aria-modal="true" aria-labelledby="quick-add-title" @keydown.escape="cancelQuickAdd">
          <div class="dialog-header">
            <h3 id="quick-add-title" class="dialog-title">{{ editingTx ? '编辑流水' : '快速记账' }}</h3>
            <button class="dialog-close" @click="cancelQuickAdd" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveTransaction">
            <!-- Type Toggle -->
            <div class="type-toggle">
              <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': txForm.type === 'expense' }" @click="txForm.type = 'expense'">支出</button>
              <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': txForm.type === 'income' }" @click="txForm.type = 'income'">收入</button>
              <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': txForm.type === 'transfer' }" @click="txForm.type = 'transfer'">转账</button>
            </div>

            <!-- Amount -->
            <div class="form-group">
              <label class="form-label" for="tx-amount">金额</label>
              <input id="tx-amount" v-model.number="txForm.amount" type="number" class="form-input form-input--amount" min="0.01" step="0.01" required placeholder="0.00" />
            </div>

            <!-- Account -->
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

            <!-- Category (not for transfer) -->
            <div v-if="txForm.type !== 'transfer'" class="form-group">
              <label class="form-label">分类</label>
              <div class="category-grid">
                <button
                  v-for="cat in filteredCategories"
                  :key="cat.id"
                  type="button"
                  class="category-chip"
                  :class="{ 'category-chip--active': txForm.category_id === cat.id }"
                  @click="txForm.category_id = cat.id"
                >
                  {{ cat.name }}
                </button>
                <div v-if="filteredCategories.length === 0" class="category-empty">暂无分类</div>
              </div>
            </div>

            <!-- Description -->
            <div class="form-group">
              <label class="form-label" for="tx-desc">备注</label>
              <input id="tx-desc" v-model="txForm.description" type="text" class="form-input" placeholder="可选备注..." maxlength="200" />
            </div>

            <!-- Date -->
            <div class="form-group">
              <label class="form-label" for="tx-date">日期</label>
              <input id="tx-date" v-model="txForm.date" type="date" class="form-input" required />
            </div>

            <div v-if="txError" class="dialog-error" role="alert">{{ txError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelQuickAdd">取消</button>
              <button type="submit" class="btn-primary" :disabled="savingTx || !txForm.amount || !txForm.account_id">
                <span v-if="savingTx" class="loading-spinner loading-spinner--sm"></span>
                {{ savingTx ? '保存中...' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Toast Notifications -->
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

const { successToast, errorToast, showSuccess, showError } = useToast()

const loading = ref(true)
const error = ref(null)
const dashboard = ref({})
const accounts = ref([])
const budgets = ref([])
const recentTransactions = ref([])
const categories = ref([])

const showQuickAdd = ref(false)
const savingTx = ref(false)
const txError = ref(null)
const editingTx = ref(null)

const today = new Date().toISOString().split('T')[0]

const txForm = ref({
  type: 'expense',
  amount: null,
  account_id: '',
  to_account_id: '',
  category_id: '',
  description: '',
  date: today
})

const filteredCategories = computed(() => {
  return categories.value.filter(c => c.type === txForm.value.type)
})

function formatMoney(val) {
  return Number(val || 0).toFixed(2)
}

function formatNet(val) {
  const v = Number(val || 0)
  return (v >= 0 ? '+' : '') + v.toFixed(2)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function budgetPercent(b) {
  if (!b.amount) return 0
  return Math.round(((b.spent || 0) / b.amount) * 100)
}

function budgetProgressClass(b) {
  const pct = budgetPercent(b)
  if (pct > 100) return 'budget--red'
  if (pct >= 80) return 'budget--yellow'
  return 'budget--green'
}

function resetTxForm() {
  txForm.value = {
    type: 'expense',
    amount: null,
    account_id: '',
    to_account_id: '',
    category_id: '',
    description: '',
    date: today
  }
  txError.value = null
  editingTx.value = null
}

function openQuickAdd() {
  resetTxForm()
  showQuickAdd.value = true
}

function cancelQuickAdd() {
  showQuickAdd.value = false
  resetTxForm()
}

async function fetchDashboard() {
  loading.value = true
  error.value = null
  try {
    const [dash, accts, bds, txs, cats] = await Promise.all([
      financeService.getDashboard().catch(() => ({})),
      financeService.getAccounts().catch(() => []),
      financeService.getBudgets().catch(() => []),
      financeService.getTransactions({ limit: 5 }).catch(() => []),
      financeService.getCategories().catch(() => [])
    ])
    dashboard.value = dash || {}
    accounts.value = Array.isArray(accts) ? accts : (accts.items || accts.accounts || [])
    budgets.value = Array.isArray(bds) ? bds : (bds.items || bds.budgets || [])
    recentTransactions.value = Array.isArray(txs) ? txs : (txs.items || txs.transactions || [])
    categories.value = Array.isArray(cats) ? cats : (cats.items || cats.categories || [])
  } catch (e) {
    error.value = '加载财务数据失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function saveTransaction() {
  if (!txForm.value.amount || !txForm.value.account_id) return
  savingTx.value = true
  txError.value = null
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
        type: txForm.value.type,
        amount: txForm.value.amount,
        account_id: txForm.value.account_id,
        category_id: txForm.value.category_id || undefined,
        description: txForm.value.description || undefined,
        date: txForm.value.date
      })
    } else {
      await financeService.createTransaction({
        type: txForm.value.type,
        amount: txForm.value.amount,
        account_id: txForm.value.account_id,
        category_id: txForm.value.category_id || undefined,
        description: txForm.value.description || undefined,
        date: txForm.value.date
      })
    }
    cancelQuickAdd()
    showSuccess(editingTx.value ? '流水已更新' : '记账成功！')
    await fetchDashboard()
  } catch (e) {
    txError.value = e.response?.data?.detail || '保存失败，请重试。'
  } finally {
    savingTx.value = false
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style scoped>
.finance-page {
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
}

.btn-create:hover { background: var(--color-primary-dark); }
.btn-create svg { width: 18px; height: 18px; }

/* Loading / Error / Empty */
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

.loading-spinner--sm { width: 16px; height: 16px; border-width: 2px; }

@keyframes spin { to { transform: rotate(360deg); } }

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

.retry-btn:hover { background: var(--color-primary); color: #fff; }

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* Account Cards */
.accounts-row {
  display: flex;
  gap: var(--spacing-md);
  overflow-x: auto;
  padding-bottom: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  -webkit-overflow-scrolling: touch;
}

.accounts-row::-webkit-scrollbar { height: 4px; }
.accounts-row::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: var(--radius-full); }

.accounts-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: var(--spacing-lg);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.account-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  min-width: 180px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  flex-shrink: 0;
}

.account-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.account-card-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: rgba(108, 99, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.account-card-icon svg { width: 22px; height: 22px; color: var(--color-primary); }

.account-card-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.account-card-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.account-card-balance {
  font-size: var(--font-size-base);
  font-weight: 700;
  color: var(--color-text);
}

/* Summary Card */
.summary-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.summary-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-md) 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
}

.summary-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--color-bg-tertiary);
}

.summary-item svg { width: 24px; height: 24px; flex-shrink: 0; }
.summary-item--income svg { color: var(--color-success); }
.summary-item--expense svg { color: var(--color-error); }
.summary-item--net svg { color: var(--color-secondary); }

.summary-item-info { display: flex; flex-direction: column; }
.summary-item-label { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.summary-item-value { font-size: var(--font-size-lg); font-weight: 700; }
.summary-item-value--income { color: var(--color-success); }
.summary-item-value--expense { color: var(--color-error); }
.summary-item-value--net { color: var(--color-secondary); }

/* Budgets */
.budgets-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--spacing-lg);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.section-title svg { width: 18px; height: 18px; color: var(--color-primary); }

.section-link {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.section-link:hover { color: var(--color-primary-light); text-decoration: underline; }

.budgets-body {
  padding: var(--spacing-md) var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.budget-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.budget-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.budget-item-name { font-size: var(--font-size-sm); font-weight: 500; color: var(--color-text); }
.budget-item-amount { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.budget-progress-bar {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.budget-progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.budget--green .budget-progress-fill, .budget--green { color: var(--color-success); }
.budget--green .budget-progress-fill { background: var(--color-success); }
.budget--yellow .budget-progress-fill, .budget--yellow { color: var(--color-warning); }
.budget--yellow .budget-progress-fill { background: var(--color-warning); }
.budget--red .budget-progress-fill, .budget--red { color: var(--color-error); }
.budget--red .budget-progress-fill { background: var(--color-error); }

.budget-item-remaining {
  font-size: var(--font-size-xs);
  font-weight: 500;
}

/* Transactions */
.transactions-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--spacing-lg);
}

.transactions-body { padding: var(--spacing-md) var(--spacing-lg); }

.transaction-list { display: flex; flex-direction: column; gap: var(--spacing-xs); }

.transaction-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.transaction-item:hover { background: var(--color-bg-tertiary); }

.transaction-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.transaction-icon svg { width: 18px; height: 18px; color: var(--color-primary); }

.transaction-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.transaction-desc {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.transaction-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.transaction-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
}

.transaction-amount { font-size: var(--font-size-sm); font-weight: 700; }
.transaction-amount--income { color: var(--color-success); }
.transaction-amount--expense { color: var(--color-error); }
.transaction-amount--transfer { color: var(--color-secondary); }
.transaction-date { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

/* Quick Links */
.quick-links {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}

.quick-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-decoration: none;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: all 0.2s ease;
}

.quick-link:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.quick-link svg { width: 24px; height: 24px; }

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

.success-toast-content svg { width: 18px; height: 18px; }

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

.error-toast-content svg { width: 18px; height: 18px; flex-shrink: 0; }

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-20px); }

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
  max-width: 480px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.dialog--wide { max-width: 520px; }

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

.dialog-close:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.dialog-close svg { width: 18px; height: 18px; }

.dialog-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-group { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.form-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }

.form-input {
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

.form-input:focus { border-color: var(--color-primary); }
.form-input::placeholder { color: var(--color-text-tertiary); }

select.form-input {
  appearance: auto;
}

.form-input--amount {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  text-align: center;
  padding: var(--spacing-md);
}

/* Type Toggle */
.type-toggle {
  display: flex;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  padding: 3px;
  gap: 3px;
}

.type-toggle-btn {
  flex: 1;
  padding: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.type-toggle-btn--active {
  background: var(--color-card);
  color: var(--color-text);
  box-shadow: var(--shadow-sm);
}

/* Category Grid */
.category-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.category-chip {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.category-chip:hover { border-color: var(--color-primary); color: var(--color-primary); }
.category-chip--active {
  background: rgba(108, 99, 255, 0.12);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.category-empty {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  padding: var(--spacing-xs) 0;
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

.btn-secondary:hover { background: var(--color-bg-tertiary); }

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

.btn-primary:hover { background: var(--color-primary-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

/* Responsive */
@media (max-width: 1199px) {
  .finance-page { padding: var(--spacing-lg); }
}

@media (max-width: 767px) {
  .finance-page { padding: var(--spacing-md); }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .summary-grid { grid-template-columns: 1fr; }
  .quick-links { grid-template-columns: repeat(2, 1fr); }
  .form-row { grid-template-columns: 1fr; }

  .dialog { max-width: 100%; margin: var(--spacing-sm); }
  .dialog-body { padding: var(--spacing-md); }
}
</style>
