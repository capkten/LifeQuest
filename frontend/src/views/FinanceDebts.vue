<template>
  <div class="finance-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push('/finance')" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 class="page-title">借贷管理</h2>
      </div>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建借贷
      </button>
    </div>

    <!-- Tab Toggle -->
    <div class="tab-toggle">
      <button class="tab-btn" :class="{ 'tab-btn--active': activeTab === 'borrowed' }" @click="activeTab = 'borrowed'; fetchDebts()">
        借入
      </button>
      <button class="tab-btn" :class="{ 'tab-btn--active': activeTab === 'lent' }" @click="activeTab = 'lent'; fetchDebts()">
        借出
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchDebts">重试</button>
    </div>

    <div v-else-if="debts.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="8.5" cy="7" r="4" />
          <line x1="20" y1="8" x2="20" y2="14" />
          <line x1="23" y1="11" x2="17" y2="11" />
        </svg>
      </div>
      <h3 class="empty-title">暂无{{ activeTab === 'borrowed' ? '借入' : '借出' }}记录</h3>
      <p class="empty-text">添加借贷记录来追踪你的债务。</p>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        添加借贷
      </button>
    </div>

    <div v-else class="debts-list">
      <div v-for="d in debts" :key="d.id" class="debt-card" :class="{ 'debt-card--settled': d.status === 'settled' }">
        <div class="debt-header">
          <div class="debt-info">
            <h4 class="debt-name">{{ d.creditor_name }}</h4>
            <span class="debt-status" :class="'debt-status--' + d.status">
              {{ d.status === 'settled' ? '已结清' : '进行中' }}
            </span>
          </div>
          <div class="debt-actions">
            <button v-if="d.status !== 'settled'" class="btn-icon btn-icon--pay" @click="openPayment(d)" aria-label="还款" title="添加还款">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
            <button class="btn-icon btn-icon--edit" @click="openEdit(d)" aria-label="编辑">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
            </button>
            <button class="btn-icon btn-icon--delete" @click="openDelete(d)" aria-label="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
            </button>
          </div>
        </div>
        <div class="debt-details">
          <div class="debt-detail">
            <span class="debt-detail-label">总额</span>
            <span class="debt-detail-value">{{ formatMoney(d.amount) }}</span>
          </div>
          <div class="debt-detail">
            <span class="debt-detail-label">剩余</span>
            <span class="debt-detail-value debt-detail-value--remaining">{{ formatMoney(d.remaining || d.amount) }}</span>
          </div>
          <div v-if="d.interest_rate" class="debt-detail">
            <span class="debt-detail-label">利率</span>
            <span class="debt-detail-value">{{ d.interest_rate }}%</span>
          </div>
          <div v-if="d.due_date" class="debt-detail">
            <span class="debt-detail-label">到期</span>
            <span class="debt-detail-value" :class="{ 'debt-detail-value--overdue': isOverdue(d.due_date) && d.status !== 'settled' }">
              {{ formatDate(d.due_date) }}
            </span>
          </div>
        </div>
        <p v-if="d.description" class="debt-desc">{{ d.description }}</p>

        <!-- Payment History -->
        <div v-if="d.payments && d.payments.length > 0" class="debt-payments">
          <button class="btn-toggle-payments" @click="togglePayments(d.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ 'rotated': expandedPayments[d.id] }" aria-hidden="true">
              <polyline points="6 9 12 15 18 9" />
            </svg>
            还款记录 ({{ d.payments.length }})
          </button>
          <div v-if="expandedPayments[d.id]" class="payment-list">
            <div v-for="p in d.payments" :key="p.id" class="payment-item">
              <span class="payment-date">{{ formatDate(p.date) }}</span>
              <span class="payment-amount">{{ formatMoney(p.amount) }}</span>
              <span v-if="p.description" class="payment-desc">{{ p.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Debt Modal -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="debt-dialog-title" @keydown.escape="cancelDialog">
          <div class="dialog-header">
            <h3 id="debt-dialog-title" class="dialog-title">{{ editingDebt ? '编辑借贷' : '新建借贷' }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveDebt">
            <div class="form-group">
              <label class="form-label" for="debt-creditor">{{ activeTab === 'borrowed' ? '出借人' : '借款人' }}</label>
              <input id="debt-creditor" v-model="form.creditor_name" type="text" class="form-input" required maxlength="100" />
            </div>
            <div class="form-group">
              <label class="form-label">类型</label>
              <div class="type-toggle">
                <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': form.type === 'borrowed' }" @click="form.type = 'borrowed'">借入</button>
                <button type="button" class="type-toggle-btn" :class="{ 'type-toggle-btn--active': form.type === 'lent' }" @click="form.type = 'lent'">借出</button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="debt-amount">金额</label>
              <input id="debt-amount" v-model.number="form.amount" type="number" class="form-input" min="0.01" step="0.01" required />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="debt-interest">利率 (%)</label>
                <input id="debt-interest" v-model.number="form.interest_rate" type="number" class="form-input" min="0" step="0.01" />
              </div>
              <div class="form-group">
                <label class="form-label" for="debt-due">到期日</label>
                <input id="debt-due" v-model="form.due_date" type="date" class="form-input" />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="debt-desc">备注</label>
              <input id="debt-desc" v-model="form.description" type="text" class="form-input" maxlength="200" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="saving || !form.creditor_name.trim() || !form.amount">
                <span v-if="saving" class="loading-spinner loading-spinner--sm"></span>
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Add Payment Modal -->
    <Teleport to="body">
      <div v-if="showPaymentDialog" class="dialog-overlay" @click.self="cancelPayment">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="pay-dialog-title" @keydown.escape="cancelPayment">
          <div class="dialog-header">
            <h3 id="pay-dialog-title" class="dialog-title">添加还款</h3>
            <button class="dialog-close" @click="cancelPayment" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="doPayment">
            <p class="pay-summary">剩余待还: <strong>{{ formatMoney(payingDebt?.remaining || payingDebt?.amount || 0) }}</strong></p>
            <div class="form-group">
              <label class="form-label" for="pay-amount">还款金额</label>
              <input id="pay-amount" v-model.number="paymentForm.amount" type="number" class="form-input" min="0.01" step="0.01" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="pay-date">日期</label>
              <input id="pay-date" v-model="paymentForm.date" type="date" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="pay-desc">备注</label>
              <input id="pay-desc" v-model="paymentForm.description" type="text" class="form-input" maxlength="200" />
            </div>
            <div v-if="paymentError" class="dialog-error" role="alert">{{ paymentError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelPayment">取消</button>
              <button type="submit" class="btn-primary" :disabled="paying || !paymentForm.amount">
                <span v-if="paying" class="loading-spinner loading-spinner--sm"></span>
                {{ paying ? '保存中...' : '确认还款' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="cancelDelete">
        <div class="dialog dialog--confirm" role="dialog" aria-modal="true" aria-labelledby="del-debt-title" @keydown.escape="cancelDelete">
          <div class="dialog-header">
            <h3 id="del-debt-title" class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="cancelDelete" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">确定要删除与「<strong>{{ deletingDebt?.creditor_name }}</strong>」的借贷记录吗？</p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDelete">取消</button>
              <button type="button" class="btn-danger" :disabled="deleting" @click="deleteDebt">
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
import { ref, onMounted } from 'vue'
import { financeService } from '../services/finance'
import { useToast } from '../composables/useToast'

const { successToast, errorToast, showSuccess, showError } = useToast()

const debts = ref([])
const loading = ref(true)
const error = ref(null)
const activeTab = ref('borrowed')
const expandedPayments = ref({})

const showDialog = ref(false)
const editingDebt = ref(null)
const saving = ref(false)
const dialogError = ref(null)

const showDeleteDialog = ref(false)
const deletingDebt = ref(null)
const deleting = ref(false)

const showPaymentDialog = ref(false)
const payingDebt = ref(null)
const paying = ref(false)
const paymentError = ref(null)

const today = new Date().toISOString().split('T')[0]

const form = ref({
  creditor_name: '', type: 'borrowed', amount: null,
  interest_rate: 0, due_date: '', description: ''
})

const paymentForm = ref({ amount: null, date: today, description: '' })

function formatMoney(val) { return Number(val || 0).toFixed(2) }

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

function isOverdue(dateStr) {
  if (!dateStr) return false
  return new Date(dateStr) < new Date(new Date().toDateString())
}

function togglePayments(id) {
  expandedPayments.value[id] = !expandedPayments.value[id]
}

function openCreate() {
  editingDebt.value = null
  form.value = {
    creditor_name: '', type: activeTab.value, amount: null,
    interest_rate: 0, due_date: '', description: ''
  }
  dialogError.value = null
  showDialog.value = true
}

function openEdit(d) {
  editingDebt.value = d
  form.value = {
    creditor_name: d.creditor_name, type: d.type || activeTab.value,
    amount: d.amount, interest_rate: d.interest_rate || 0,
    due_date: d.due_date ? d.due_date.split('T')[0] : '',
    description: d.description || ''
  }
  dialogError.value = null
  showDialog.value = true
}

function cancelDialog() { showDialog.value = false; editingDebt.value = null; dialogError.value = null }

function openPayment(d) {
  payingDebt.value = d
  paymentForm.value = { amount: null, date: today, description: '' }
  paymentError.value = null
  showPaymentDialog.value = true
}

function cancelPayment() { showPaymentDialog.value = false; payingDebt.value = null; paymentError.value = null }

function openDelete(d) { deletingDebt.value = d; showDeleteDialog.value = true }
function cancelDelete() { showDeleteDialog.value = false; deletingDebt.value = null }

async function fetchDebts() {
  loading.value = true
  error.value = null
  try {
    const data = await financeService.getDebts({ type: activeTab.value })
    debts.value = Array.isArray(data) ? data : (data.items || data.debts || [])
  } catch (e) {
    error.value = '加载借贷数据失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function saveDebt() {
  if (!form.value.creditor_name.trim() || !form.value.amount) return
  saving.value = true
  dialogError.value = null
  try {
    const payload = {
      creditor_name: form.value.creditor_name.trim(),
      type: form.value.type,
      amount: form.value.amount,
      interest_rate: form.value.interest_rate || 0,
      due_date: form.value.due_date || undefined,
      description: form.value.description || undefined
    }
    if (editingDebt.value) {
      const updated = await financeService.updateDebt(editingDebt.value.id, payload)
      const idx = debts.value.findIndex(d => d.id === editingDebt.value.id)
      if (idx !== -1) debts.value[idx] = updated
      showSuccess('借贷记录已更新')
    } else {
      const created = await financeService.createDebt(payload)
      debts.value.push(created)
      showSuccess('借贷记录已创建')
    }
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '保存失败，请重试。'
  } finally {
    saving.value = false
  }
}

async function doPayment() {
  if (!payingDebt.value || !paymentForm.value.amount) return
  paying.value = true
  paymentError.value = null
  try {
    await financeService.addPayment(payingDebt.value.id, {
      amount: paymentForm.value.amount,
      date: paymentForm.value.date,
      description: paymentForm.value.description || undefined
    })
    showSuccess('还款记录已添加')
    cancelPayment()
    await fetchDebts()
  } catch (e) {
    paymentError.value = e.response?.data?.detail || '还款失败，请重试。'
  } finally {
    paying.value = false
  }
}

async function deleteDebt() {
  if (!deletingDebt.value) return
  deleting.value = true
  try {
    await financeService.deleteDebt(deletingDebt.value.id)
    debts.value = debts.value.filter(d => d.id !== deletingDebt.value.id)
    showSuccess('借贷记录已删除')
    cancelDelete()
  } catch (e) {
    showError(e.response?.data?.detail || '删除失败，请重试。')
    cancelDelete()
  } finally {
    deleting.value = false
  }
}

onMounted(() => { fetchDebts() })
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

/* Tab Toggle */
.tab-toggle {
  display: flex; background: var(--color-bg-tertiary);
  border-radius: var(--radius-md); padding: 3px; gap: 3px;
  margin-bottom: var(--spacing-lg); max-width: 200px;
}
.tab-btn {
  flex: 1; padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm); font-weight: 600;
  color: var(--color-text-secondary); background: transparent;
  border: none; border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: all 0.15s ease;
}
.tab-btn--active { background: var(--color-card); color: var(--color-text); box-shadow: var(--shadow-sm); }

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
.empty-text { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin-bottom: var(--spacing-xl); max-width: 320px; }

/* Debt Cards */
.debts-list { display: flex; flex-direction: column; gap: var(--spacing-md); }

.debt-card {
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: var(--spacing-lg);
  transition: border-color 0.2s ease;
}
.debt-card:hover { border-color: var(--color-primary); }
.debt-card--settled { opacity: 0.65; }

.debt-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--spacing-md);
}
.debt-info { display: flex; align-items: center; gap: var(--spacing-md); }
.debt-name { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text); margin: 0; }

.debt-status {
  font-size: var(--font-size-xs); font-weight: 500;
  padding: 2px 10px; border-radius: var(--radius-full);
}
.debt-status--active { background: rgba(0, 217, 255, 0.12); color: var(--color-secondary); }
.debt-status--settled { background: rgba(81, 207, 102, 0.12); color: var(--color-success); }

.debt-actions { display: flex; gap: 4px; }

.debt-details {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: var(--spacing-md); margin-bottom: var(--spacing-sm);
}
.debt-detail { display: flex; flex-direction: column; gap: 2px; }
.debt-detail-label { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.debt-detail-value { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }
.debt-detail-value--remaining { color: var(--color-warning); }
.debt-detail-value--overdue { color: var(--color-error); }

.debt-desc { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin: 0; }

/* Payment History */
.debt-payments { margin-top: var(--spacing-md); border-top: 1px solid var(--color-border); padding-top: var(--spacing-sm); }
.btn-toggle-payments {
  display: inline-flex; align-items: center; gap: var(--spacing-xs);
  font-size: var(--font-size-xs); font-weight: 500;
  color: var(--color-primary); background: transparent;
  border: none; cursor: pointer; font-family: var(--font-family);
  padding: var(--spacing-xs) 0; transition: color 0.15s ease;
}
.btn-toggle-payments:hover { color: var(--color-primary-light); }
.btn-toggle-payments svg { width: 14px; height: 14px; transition: transform 0.2s ease; }
.btn-toggle-payments svg.rotated { transform: rotate(180deg); }

.payment-list {
  display: flex; flex-direction: column; gap: var(--spacing-xs);
  margin-top: var(--spacing-sm); padding-left: var(--spacing-md);
}
.payment-item {
  display: flex; align-items: center; gap: var(--spacing-md);
  padding: var(--spacing-xs) 0; font-size: var(--font-size-xs);
}
.payment-date { color: var(--color-text-tertiary); min-width: 80px; }
.payment-amount { font-weight: 600; color: var(--color-success); }
.payment-desc { color: var(--color-text-tertiary); }

/* Buttons */
.btn-icon {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid var(--color-border);
  border-radius: var(--radius-md); cursor: pointer;
  color: var(--color-text-tertiary); transition: all 0.15s ease;
}
.btn-icon svg { width: 14px; height: 14px; }
.btn-icon--edit:hover { background: var(--color-primary); border-color: var(--color-primary); color: #fff; }
.btn-icon--delete:hover { background: var(--color-error); border-color: var(--color-error); color: #fff; }
.btn-icon--pay:hover { background: var(--color-success); border-color: var(--color-success); color: #fff; }

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

.pay-summary { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin: 0; }
.pay-summary strong { color: var(--color-warning); }

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
  .debt-details { grid-template-columns: repeat(2, 1fr); }
  .form-row { grid-template-columns: 1fr; }
  .dialog { max-width: 100%; margin: var(--spacing-sm); }
  .dialog-body { padding: var(--spacing-md); }
}
</style>
