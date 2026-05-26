import api from './api'

export const todoService = {
  /**
   * Get all tasks for current user
   * @returns {Promise<Array>} List of tasks
   */
  async getTasks() {
    const response = await api.get('/todos/tasks')
    return response.data
  },

  /**
   * Get all goals for current user
   * @returns {Promise<Array>} List of goals
   */
  async getGoals() {
    const response = await api.get('/todos/goals')
    return response.data
  }
}
