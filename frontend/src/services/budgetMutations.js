export async function saveBudgetMutation({
  budgets,
  editingBudget = null,
  form,
  createBudget,
  updateBudget,
  getErrorMessage,
}) {
  try {
    if (editingBudget) {
      const updated = await updateBudget(editingBudget.id, form)
      return {
        ok: true,
        budgets: budgets.map(budget => budget.id === editingBudget.id ? updated : budget),
      }
    }

    const created = await createBudget(form)
    return { ok: true, budgets: [...budgets, created] }
  } catch (error) {
    return {
      ok: false,
      budgets,
      error: getErrorMessage(error),
    }
  }
}
