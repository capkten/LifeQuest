<template>
  <div class="finance-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push('/finance')" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 class="page-title">账户管理</h2>
      </div>
      <div class="header-right">
        <button class="btn-secondary" @click="showTransferDialog = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="17 1 21 5 17 9" />
            <path d="M3 11V9a4 4 0 0 1 4-4h14" />
            <polyline points="7 23 3 19 7 15" />
            <path d="M21 13v2a4 4 0 0 1-4 4H3" />
          </svg>
          转账
        </button>
        <button class="btn-create" @click="openCreate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建账户
        </button>
      </div>
    </div>

    <!-- Total Assets -->
    <div class="total-assets">
      <span class="total-assets-label">总资产</span>
      <span class="total-assets-value">{{ formatMoney(totalAssets) }}</span>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchAccounts">重试</button>
    </div>

    <div v-else-if="accounts.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M2 10h20" />
        </svg>
      </div>
      <h3 class="empty-title">暂无账户</h3>
      <p class="empty-text">创建第一个账户来开始记账吧。</p>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        创建账户
      </button>
    </div>

    <div v-else class="accounts-list">
      <div v-for="acct in accounts" :key="acct.id" class="account-row">
        <div class="account-row-icon">
          <svg v-if="acct.type === 'cash'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="M2 10h20" />
          </svg>
          <svg v-else-if="acct.type === 'bank'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M3 21h18" /><path d="M3 10h18" /><path d="M5 6l7-3 7 3" />
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
        <div class="account-row-info">
          <span class="account-row-name">{{ acct.name }}</span>
          <span class="account-row-type">{{ accountTypeLabel(acct.type) }}</span>
        </div>
        <div class="account-row-balance">
          {{ formatMoney(acct.balance) }}
        </div>
        <div class="account-row-actions">
          <button class="btn-icon btn-icon--edit" @click="openEdit(acct)" aria-label="编辑" title="编辑">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button class="btn-icon btn-icon--delete" @click="openDelete(acct)" aria-label="删除" title="删除">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Account Modal -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="account-dialog-title" @keydown.escape="cancelDialog">
          <div class="dialog-header">
            <h3 id="account-dialog-title" class="dialog-title">{{ dialogMode === 'edit' ? '编辑账户' : '新建账户' }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveAccount">
            <div class="form-group">
              <label class="form-label" for="acct-name">名称</label>
              <input id="acct-name" v-model="form.name" type="text" class="form-input" required maxlength="100" />
            </div>
            <div class="form-group">
              <label class="form-label" for="acct-type">类型</label>
              <select id="acct-type" v-model="form.type" class="form-input" required>
                <option value="cash">现金</option>
                <option value="bank">银行卡</option>
                <option value="credit">信用卡</option>
                <option value="alipay">支付宝</option>
                <option value="wechat">微信</option>
                <option value="debt">借贷</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="acct-balance">初始余额</label>
              <input id="acct-balance" v-model.number="form.balance" type="number" class="form-input" step="0.01" required />
            </div>
            <div v-if="form.type === 'credit'" class="form-row">
              <div class="form-group">
                <label class="form-label" for="acct-credit-limit">信用额度</label>
                <input id="acct-credit-limit" v-model.number="form.credit_limit" type="number" class="form-input" min="0" step="0.01" />
              </div>
              <div class="form-group">
                <label class="form-label" for="acct-billing-day">账单日</label>
                <input id="acct-billing-day" v-model.number="form.billing_day" type="number" class="form-input" min="1" max="31" />
              </div>
            </div>
            <div v-if="form.type === 'credit'" class="form-group">
              <label class="form-label" for="acct-repayment-day">还款日</label>
              <input id="acct-repayment-day" v-model.number="form.repayment_day" type="number" class="form-input" min="1" max="31" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="saving || !form.name.trim()">
                <span v-if="saving" class="loading-spinner loading-spinner--sm"></span>
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Transfer Modal -->
    <Teleport to="body">
      <div v-if="showTransferDialog" class="dialog-overlay" @click.self="cancelTransfer">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="transfer-dialog-title" @keydown.escape="cancelTransfer">
          <div class="dialog-header">
            <h3 id="transfer-dialog-title" class="dialog-title">转账</h3>
            <button class="dialog-close" @click="cancelTransfer" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="doTransfer">
            <div class="form-group">
              <label class="form-label" for="transfer-from">转出账户</label>
              <select id="transfer-from" v-model="transferForm.from_account_id" class="form-input" required>
                <option value="" disabled>选择账户</option>
                <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }} ({{ formatMoney(a.balance) }})</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="transfer-to">转入账户</label>
              <select id="transfer-to" v-model="transferForm.to_account_id" class="form-input" required>
                <option value="" disabled>选择账户</option>
                <option v-for="a in accounts" :key="a.id" :value="a.id" :disabled="a.id === transferForm.from_account_id">{{ a.name }} ({{ formatMoney(a.balance) }})</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="transfer-amount">金额</label>
              <input id="transfer-amount" v-model.number="transferForm.amount" type="number" class="form-input" min="0.01" step="0.01" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="transfer-desc">备注</label>
              <input id="transfer-desc" v-model="transferForm.description" type="text" class="form-input" maxlength="200" />
            </div>
            <div v-if="transferError" class="dialog-error" role="alert">{{ transferError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelTransfer">取消</button>
              <button type="submit" class="btn-primary" :disabled="transferring || !transferForm.from_account_id || !transferForm.to_account_id || !transferForm.amount">
                <span v-if="transferring" class="loading-spinner loading-spinner--sm"></span>
                {{ transferring ? '转账中...' : '确认转账' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="cancelDelete">
        <div class="dialog dialog--confirm" role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title" @keydown.escape="cancelDelete">
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
            <p class="confirm-text">确定要删除账户「<strong>{{ deletingAccount?.name }}</strong>」吗？此操作无法撤销。</p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDelete">取消</button>
              <button type="button" class="btn-danger" :disabled="deleting" @click="deleteAccount">
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

const accounts = ref([])
const loading = ref(true)
const error = ref(null)

const showDialog = ref(false)
const dialogMode = ref('create')
const editingAccount = ref(null)
const saving = ref(false)
const dialogError = ref(null)

const showDeleteDialog = ref(false)
const deletingAccount = ref(null)
const deleting = ref(false)

const showTransferDialog = ref(false)
const transferring = ref(false)
const transferError = ref(null)

const defaultForm = {
  name: '', type: 'cash', balance: 0,
  credit_limit: 0, billing_day: 1, repayment_day: 20
}

const form = ref({ ...defaultForm })

const transferForm = ref({
  from_account_id: '', to_account_id: '', amount: null, description: ''
})

const totalAssets = computed(() => {
  return accounts.value.reduce((sum, a) => sum + Number(a.balance || 0), 0)
})

function formatMoney(val) {
  return Number(val || 0).toFixed(2)
}

function accountTypeLabel(type) {
  const map = { cash: '现金', bank: '银行卡', credit: '信用卡', alipay: '支付宝', wechat: '微信', debt: '借贷', other: '其他' }
  return map[type] || type
}

function openCreate() {
  dialogMode.value = 'create'
  editingAccount.value = null
  form.value = { ...defaultForm }
  dialogError.value = null
  showDialog.value = true
}

function openEdit(acct) {
  dialogMode.value = 'edit'
  editingAccount.value = acct
  form.value = {
    name: acct.name, type: acct.type, balance: acct.balance,
    credit_limit: acct.credit_limit || 0,
    billing_day: acct.billing_day || 1,
    repayment_day: acct.repayment_day || 20
  }
  dialogError.value = null
  showDialog.value = true
}

function cancelDialog() {
  showDialog.value = false
  editingAccount.value = null
  form.value = { ...defaultForm }
  dialogError.value = null
}

function openDelete(acct) {
  deletingAccount.value = acct
  showDeleteDialog.value = true
}

function cancelDelete() {
  showDeleteDialog.value = false
  deletingAccount.value = null
}

function cancelTransfer() {
  showTransferDialog.value = false
  transferForm.value = { from_account_id: '', to_account_id: '', amount: null, description: '' }
  transferError.value = null
}

async function fetchAccounts() {
  loading.value = true
  error.value = null
  try {
    const data = await financeService.getAccounts()
    accounts.value = Array.isArray(data) ? data : (data.items || data.accounts || [])
  } catch (e) {
    error.value = '加载账户失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function saveAccount() {
  if (!form.value.name.trim()) return
  saving.value = true
  dialogError.value = null
  try {
    const payload = {
      name: form.value.name.trim(),
      type: form.value.type,
      balance: form.value.balance
    }
    if (form.value.type === 'credit') {
      payload.credit_limit = form.value.credit_limit || 0
      payload.billing_day = form.value.billing_day || 1
      payload.repayment_day = form.value.repayment_day || 20
    }
    if (dialogMode.value === 'edit' && editingAccount.value) {
      const updated = await financeService.updateAccount(editingAccount.value.id, payload)
      const idx = accounts.value.findIndex(a => a.id === editingAccount.value.id)
      if (idx !== -1) accounts.value[idx] = updated
      showSuccess('账户已更新')
    } else {
      const created = await financeService.createAccount(payload)
      accounts.value.push(created)
      showSuccess('账户已创建')
    }
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '保存失败，请重试。'
  } finally {
    saving.value = false
  }
}

async function deleteAccount() {
  if (!deletingAccount.value) return
  deleting.value = true
  try {
    await financeService.deleteAccount(deletingAccount.value.id)
    accounts.value = accounts.value.filter(a => a.id !== deletingAccount.value.id)
    showSuccess('账户已删除')
    cancelDelete()
  } catch (e) {
    showError(e.response?.data?.detail || '删除失败，请重试。')
    cancelDelete()
  } finally {
    deleting.value = false
  }
}

async function doTransfer() {
  if (!transferForm.value.from_account_id || !transferForm.value.to_account_id || !transferForm.value.amount) return
  transferring.value = true
  transferError.value = null
  try {
    await financeService.transfer({
      from_account_id: transferForm.value.from_account_id,
      to_account_id: transferForm.value.to_account_id,
      amount: transferForm.value.amount,
      description: transferForm.value.description || undefined
    })
    showSuccess('转账成功')
    cancelTransfer()
    await fetchAccounts()
  } catch (e) {
    transferError.value = e.response?.data?.detail || '转账失败，请重试。'
  } finally {
    transferring.value = false
  }
}

onMounted(() => { fetchAccounts() })
</script>

<style scoped>
.finance-page { padding: var(--spacing-xl); width: 100%; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.header-left { display: flex; align-items: center; gap: var(--spacing-md); }
.header-right { display: flex; align-items: center; gap: var(--spacing-sm); }

.btn-back {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
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

.btn-secondary {
  display: inline-flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm); font-weight: 500;
  color: var(--color-text-secondary); background: transparent;
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
  cursor: pointer; font-family: var(--font-family); transition: all 0.15s ease;
}
.btn-secondary:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.btn-secondary svg { width: 16px; height: 16px; }

/* Total Assets */
.total-assets {
  display: flex; align-items: baseline; gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: var(--radius-lg); margin-bottom: var(--spacing-lg);
  color: #fff;
}
.total-assets-label { font-size: var(--font-size-base); opacity: 0.85; }
.total-assets-value { font-size: var(--font-size-2xl); font-weight: 700; }

/* Loading / Error / Empty */
.loading-state { display: flex; align-items: center; justify-content: center; min-height: 300px; }

.loading-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--color-border); border-top-color: var(--color-primary);
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
.loading-spinner--sm { width: 16px; height: 16px; border-width: 2px; }
@keyframes spin { to { transform: rotate(360deg); } }

.error-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 300px; gap: var(--spacing-md);
  color: var(--color-error); font-size: var(--font-size-sm);
}
.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm); color: var(--color-primary);
  background: transparent; border: 1px solid var(--color-primary);
  border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: all 0.15s ease;
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

/* Account List */
.accounts-list {
  display: flex; flex-direction: column; gap: var(--spacing-sm);
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); overflow: hidden;
}

.account-row {
  display: flex; align-items: center; gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.15s ease;
}
.account-row:last-child { border-bottom: none; }
.account-row:hover { background: var(--color-bg-tertiary); }

.account-row-icon {
  width: 40px; height: 40px; border-radius: var(--radius-md);
  background: rgba(108, 99, 255, 0.12); display: flex;
  align-items: center; justify-content: center; flex-shrink: 0;
}
.account-row-icon svg { width: 22px; height: 22px; color: var(--color-primary); }

.account-row-info { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.account-row-name { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text); }
.account-row-type { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.account-row-balance {
  font-size: var(--font-size-base); font-weight: 700;
  color: var(--color-text); flex-shrink: 0; min-width: 100px; text-align: right;
}

.account-row-actions { display: flex; gap: 4px; flex-shrink: 0; }

.btn-icon {
  width: 28px; height: 28px; display: flex;
  align-items: center; justify-content: center;
  background: transparent; border: 1px solid var(--color-border);
  border-radius: var(--radius-md); cursor: pointer;
  color: var(--color-text-tertiary); transition: all 0.15s ease;
}
.btn-icon svg { width: 14px; height: 14px; }
.btn-icon--edit:hover { background: var(--color-primary); border-color: var(--color-primary); color: #fff; }
.btn-icon--delete:hover { background: var(--color-error); border-color: var(--color-error); color: #fff; }

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
  width: 32px; height: 32px; display: flex;
  align-items: center; justify-content: center;
  background: transparent; border: none;
  border-radius: var(--radius-md); cursor: pointer;
  color: var(--color-text-tertiary); transition: background 0.15s ease;
}
.dialog-close:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.dialog-close svg { width: 18px; height: 18px; }

.dialog-body {
  padding: var(--spacing-lg); display: flex;
  flex-direction: column; gap: var(--spacing-md);
}

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

.dialog-error { font-size: var(--font-size-sm); color: var(--color-error); padding: var(--spacing-xs) 0; }
.dialog-actions { display: flex; justify-content: flex-end; gap: var(--spacing-sm); padding-top: var(--spacing-sm); }

.btn-primary {
  display: inline-flex; align-items: center; gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm); font-weight: 600; color: #fff;
  background: var(--color-primary); border: none;
  border-radius: var(--radius-md); cursor: pointer;
  font-family: var(--font-family); transition: background 0.15s ease;
}
.btn-primary:hover { background: var(--color-primary-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.confirm-text { font-size: var(--font-size-sm); color: var(--color-text-secondary); line-height: 1.6; }
.confirm-text strong { color: var(--color-text); }

.btn-danger {
  display: inline-flex; align-items: center; gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm); font-weight: 600; color: #fff;
  background: var(--color-error); border: none;
  border-radius: var(--radius-md); cursor: pointer;
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
  .header-right { width: 100%; }
  .account-row { flex-wrap: wrap; }
  .account-row-balance { min-width: auto; }
  .form-row { grid-template-columns: 1fr; }
  .dialog { max-width: 100%; margin: var(--spacing-sm); }
  .dialog-body { padding: var(--spacing-md); }
}
</style>
