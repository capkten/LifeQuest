import api from './api'

export const financeService = {
  // Dashboard
  async getDashboard() { const r = await api.get('/finance/dashboard'); return r.data },

  // Accounts
  async getAccounts() { const r = await api.get('/finance/accounts'); return r.data },
  async createAccount(data) { const r = await api.post('/finance/accounts', data); return r.data },
  async updateAccount(id, data) { const r = await api.put(`/finance/accounts/${id}`, data); return r.data },
  async deleteAccount(id) { await api.delete(`/finance/accounts/${id}`) },
  async transfer(data) { const r = await api.post('/finance/accounts/transfer', data); return r.data },

  // Categories
  async getCategories() { const r = await api.get('/finance/categories'); return r.data },
  async createCategory(data) { const r = await api.post('/finance/categories', data); return r.data },
  async deleteCategory(id) { await api.delete(`/finance/categories/${id}`) },

  // Transactions
  async getTransactions(params) { const r = await api.get('/finance/transactions', { params }); return r.data },
  async createTransaction(data) { const r = await api.post('/finance/transactions', data); return r.data },
  async updateTransaction(id, data) { const r = await api.put(`/finance/transactions/${id}`, data); return r.data },
  async deleteTransaction(id) { await api.delete(`/finance/transactions/${id}`) },

  // Budgets
  async getBudgets() { const r = await api.get('/finance/budgets'); return r.data },
  async createBudget(data) { const r = await api.post('/finance/budgets', data); return r.data },
  async updateBudget(id, data) { const r = await api.put(`/finance/budgets/${id}`, data); return r.data },
  async deleteBudget(id) { await api.delete(`/finance/budgets/${id}`) },

  // Recurring
  async getRecurring() { const r = await api.get('/finance/recurring'); return r.data },
  async createRecurring(data) { const r = await api.post('/finance/recurring', data); return r.data },
  async triggerRecurring(id) { const r = await api.post(`/finance/recurring/${id}/trigger`); return r.data },
  async deleteRecurring(id) { await api.delete(`/finance/recurring/${id}`) },

  // Debts
  async getDebts(params) { const r = await api.get('/finance/debts', { params }); return r.data },
  async createDebt(data) { const r = await api.post('/finance/debts', data); return r.data },
  async updateDebt(id, data) { const r = await api.put(`/finance/debts/${id}`, data); return r.data },
  async deleteDebt(id) { await api.delete(`/finance/debts/${id}`) },
  async addPayment(debtId, data) { const r = await api.post(`/finance/debts/${debtId}/payments`, data); return r.data },
}
