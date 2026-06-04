<template>
  <div class="finance-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push('/finance')" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 class="page-title">预算管理</h2>
      </div>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建预算
      </button>
    </div>

    <!-- Monthly Overview -->
    <div class="overview-card">
      <h3 class="overview-title">本月预算概览</h3>
      <div class="overview-grid">
        <div class="overview-item">
          <span class="overview-label">总预算</span>
          <span class="overview-value">{{ formatMoney(totalBudget) }}</span>
        </div>
        <div class="overview-item">
          <span class="overview-label">已支出</span>
          <span class="overview-value overview-value--spent">{{ formatMoney(totalSpent) }}</span>
        </div>
        <div class="overview-item">
          <span class="overview-label">剩余</span>
          <span class="overview-value" :class="totalRemaining >= 0 ? 'overview-value--ok' : 'overview-value--over'">
            {{ formatMoney(totalRemaining) }}
          </span>
        </div>
      </div>
      <div class="overview-bar">
        <div class="overview-bar-fill" :class="overviewBarClass" :style="{ width: Math.min(overviewPercent, 100) + '%' }"></div>
      </div>
      <span class="overview-percent">{{ overviewPercent }}%</span>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchBudgets">重试</button>
    </div>

    <div v-else-if="budgets.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
          <path d="M22 12A10 10 0 0 0 12 2v10z" />
        </svg>
      </div>
      <h3 class="empty-title">暂无预算</h3>
      <p class="empty-text">创建预算来更好地管理你的开支。</p>
      <button class="btn-create" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        创建预算
      </button>
    </div>

    <div v-else class="budgets-list">
      <div v-for="b in budgets" :key="b.id" class="budget-row">
        <div class="budget-row-header">
          <div class="budget-row-info">
            <span class="budget-row-name">{{ b.category_name || '未分类' }}</span>
            <span class="budget-row-period">{{ periodLabel(b.period) }}</span>
          </div>
          <div class="budget-row-actions">
            <button class="btn-icon btn-icon--edit" @click="openEdit(b)" aria-label="编辑">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
            </button>
            <button class="btn-icon btn-icon--delete" @click="openDelete(b)" aria-label="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
            </button>
          </div>
        </div>
        <div class="budget-row-amounts">
          <span>{{ formatMoney(b.spent || 0) }} 已支出</span>
          <span>预算 {{ formatMoney(b.amount) }}</span>
        </div>
        <div class="budget-progress-bar">
          <div class="budget-progress-fill" :class="budgetProgressClass(b)" :style="{ width: Math.min(budgetPercent(b), 100) + '%' }"></div>
        </div>
        <div class="budget-row-remaining" :class="budgetProgressClass(b)">
          <template v-if="budgetPercent(b) > 100">超支 {{ formatMoney((b.spent || 0) - b.amount) }}</template>
          <template v-else>剩余 {{ formatMoney(b.amount - (b.spent || 0)) }}</template>
          <span class="budget-percent">({{ budgetPercent(b) }}%)</span>
        </div>
      </div>
    </div>

    <!-- Create/Edit Budget Modal -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click.self="cancelDialog">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="budget-dialog-title" @keydown.escape="cancelDialog">
          <div class="dialog-header">
            <h3 id="budget-dialog-title" class="dialog-title">{{ editingBudget ? '编辑预算' : '新建预算' }}</h3>
            <button class="dialog-close" @click="cancelDialog" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="saveBudget">
            <div class="form-group">
              <label class="form-label">分类</label>
              <div class="category-grid">
                <button v-for="cat in expenseCategories" :key="cat.id" type="button" class="category-chip" :class="{ 'category-chip--active': form.category_id === cat.id }" @click="form.category_id = cat.id">
                  {{ cat.name }}
                </button>
                <div v-if="expenseCategories.length === 0" class="category-empty">暂无支出分类</div>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="budget-amount">预算金额</label>
              <input id="budget-amount" v-model.number="form.amount" type="number" class="form-input" min="0.01" step="0.01" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="budget-period">周期</label>
              <select id="budget-period" v-model="form.period" class="form-input" required>
                <option value="monthly">每月</option>
                <option value="weekly">每周</option>
              </select>
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDialog">取消</button>
              <button type="submit" class="btn-primary" :disabled="saving || !form.category_id || !form.amount">
                <span v-if="saving" class="loading-spinner loading-spinner--sm"></span>
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="cancelDelete">
        <div class="dialog dialog--confirm" role="dialog" aria-modal="true" aria-labelledby="del-budget-title" @keydown.escape="cancelDelete">
          <div class="dialog-header">
            <h3 id="del-budget-title" class="dialog-title">确认删除</h3>
            <button class="dialog-close" @click="cancelDelete" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">确定要删除「<strong>{{ deletingBudget?.category_name || '未分类' }}</strong>」的预算吗？</p>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="cancelDelete">取消</button>
              <button type="button" class="btn-danger" :disabled="deleting" @click="deleteBudget">
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

const budgets = ref([])
const categories = ref([])
const loading = ref(true)
const error = ref(null)

const showDialog = ref(false)
const editingBudget = ref(null)
const saving = ref(false)
const dialogError = ref(null)

const showDeleteDialog = ref(false)
const deletingBudget = ref(null)
const deleting = ref(false)

const form = ref({ category_id: '', amount: null, period: 'monthly' })

const expenseCategories = computed(() => categories.value.filter(c => c.type === 'expense'))

const totalBudget = computed(() => budgets.value.reduce((s, b) => s + Number(b.amount || 0), 0))
const totalSpent = computed(() => budgets.value.reduce((s, b) => s + Number(b.spent || 0), 0))
const totalRemaining = computed(() => totalBudget.value - totalSpent.value)
const overviewPercent = computed(() => {
  if (!totalBudget.value) return 0
  return Math.round((totalSpent.value / totalBudget.value) * 100)
})

const overviewBarClass = computed(() => {
  const pct = overviewPercent.value
  if (pct > 100) return 'bar--red'
  if (pct >= 80) return 'bar--yellow'
  return 'bar--green'
})

function formatMoney(val) { return Number(val || 0).toFixed(2) }

function periodLabel(period) {
  return period === 'weekly' ? '每周' : '每月'
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

function openCreate() {
  editingBudget.value = null
  form.value = { category_id: '', amount: null, period: 'monthly' }
  dialogError.value = null
  showDialog.value = true
}

function openEdit(b) {
  editingBudget.value = b
  form.value = { category_id: b.category_id || '', amount: b.amount, period: b.period || 'monthly' }
  dialogError.value = null
  showDialog.value = true
}

function cancelDialog() { showDialog.value = false; editingBudget.value = null; dialogError.value = null }

function openDelete(b) { deletingBudget.value = b; showDeleteDialog.value = true }
function cancelDelete() { showDeleteDialog.value = false; deletingBudget.value = null }

async function fetchBudgets() {
  loading.value = true
  error.value = null
  try {
    const [bData, cData] = await Promise.all([
      financeService.getBudgets().catch(() => []),
      financeService.getCategories().catch(() => [])
    ])
    budgets.value = Array.isArray(bData) ? bData : (bData.items || bData.budgets || [])
    categories.value = Array.isArray(cData) ? cData : (cData.items || cData.categories || [])
  } catch (e) {
    error.value = '加载预算失败，请重试。'
  } finally {
    loading.value = false
  }
}

async function saveBudget() {
  if (!form.value.category_id || !form.value.amount) return
  saving.value = true
  dialogError.value = null
  try {
    if (editingBudget.value) {
      const updated = await financeService.updateBudget(editingBudget.value.id, form.value)
      const idx = budgets.value.findIndex(b => b.id === editingBudget.value.id)
      if (idx !== -1) budgets.value[idx] = updated
      showSuccess('预算已更新')
    } else {
      const created = await financeService.createBudget(form.value)
      budgets.value.push(created)
      showSuccess('预算已创建')
    }
    cancelDialog()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '保存失败，请重试。'
  } finally {
    saving.value = false
  }
}

async function deleteBudget() {
  if (!deletingBudget.value) return
  deleting.value = true
  try {
    await financeService.deleteBudget(deletingBudget.value.id)
    budgets.value = budgets.value.filter(b => b.id !== deletingBudget.value.id)
    showSuccess('预算已删除')
    cancelDelete()
  } catch (e) {
    showError(e.response?.data?.detail || '删除失败，请重试。')
    cancelDelete()
  } finally {
    deleting.value = false
  }
}

onMounted(() => { fetchBudgets() })
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

/* Overview Card */
.overview-card {
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}
.overview-title { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text); margin: 0 0 var(--spacing-md) 0; }

.overview-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md); margin-bottom: var(--spacing-md);
}
.overview-item { display: flex; flex-direction: column; gap: 2px; }
.overview-label { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.overview-value { font-size: var(--font-size-lg); font-weight: 700; color: var(--color-text); }
.overview-value--spent { color: var(--color-error); }
.overview-value--ok { color: var(--color-success); }
.overview-value--over { color: var(--color-error); }

.overview-bar {
  height: 8px; background: var(--color-bg-tertiary);
  border-radius: var(--radius-full); overflow: hidden; margin-bottom: var(--spacing-xs);
}
.overview-bar-fill {
  height: 100%; border-radius: var(--radius-full); transition: width 0.5s ease;
}
.bar--green { background: var(--color-success); }
.bar--yellow { background: var(--color-warning); }
.bar--red { background: var(--color-error); }

.overview-percent { font-size: var(--font-size-xs); color: var(--color-text-tertiary); font-weight: 600; }

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

/* Budget List */
.budgets-list {
  display: flex; flex-direction: column; gap: var(--spacing-md);
}

.budget-row {
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: var(--spacing-lg);
  transition: border-color 0.2s ease;
}
.budget-row:hover { border-color: var(--color-primary); }

.budget-row-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--spacing-sm);
}
.budget-row-info { display: flex; flex-direction: column; gap: 2px; }
.budget-row-name { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text); }
.budget-row-period { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.budget-row-actions { display: flex; gap: 4px; }

.budget-row-amounts {
  display: flex; justify-content: space-between;
  font-size: var(--font-size-xs); color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-xs);
}

.budget-progress-bar {
  height: 6px; background: var(--color-bg-tertiary);
  border-radius: var(--radius-full); overflow: hidden; margin-bottom: var(--spacing-xs);
}
.budget-progress-fill {
  height: 100%; border-radius: var(--radius-full); transition: width 0.5s ease;
}
.budget--green .budget-progress-fill { background: var(--color-success); }
.budget--yellow .budget-progress-fill { background: var(--color-warning); }
.budget--red .budget-progress-fill { background: var(--color-error); }

.budget-row-remaining { font-size: var(--font-size-sm); font-weight: 500; }
.budget-row-remaining.budget--green { color: var(--color-success); }
.budget-row-remaining.budget--yellow { color: var(--color-warning); }
.budget-row-remaining.budget--red { color: var(--color-error); }

.budget-percent { font-size: var(--font-size-xs); color: var(--color-text-tertiary); margin-left: var(--spacing-xs); }

.btn-icon {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
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
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: var(--radius-md);
  cursor: pointer; color: var(--color-text-tertiary); transition: background 0.15s ease;
}
.dialog-close:hover { background: var(--color-bg-tertiary); color: var(--color-text); }
.dialog-close svg { width: 18px; height: 18px; }

.dialog-body { padding: var(--spacing-lg); display: flex; flex-direction: column; gap: var(--spacing-md); }

.form-group { display: flex; flex-direction: column; gap: var(--spacing-xs); }
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
  .overview-grid { grid-template-columns: 1fr; }
  .dialog { max-width: 100%; margin: var(--spacing-sm); }
  .dialog-body { padding: var(--spacing-md); }
}
</style>
