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
  },

  /**
   * Get all habits for current user
   * @returns {Promise<Array>} List of habits
   */
  async getHabits() {
    const response = await api.get('/todos/habits')
    return response.data
  },

  /**
   * Create a new habit
   * @param {Object} data - Habit data
   * @returns {Promise<Object>} Created habit
   */
  async createHabit(data) {
    const response = await api.post('/todos/habits', data)
    return response.data
  },

  /**
   * Create a new task
   * @param {Object} data - Task data
   * @returns {Promise<Object>} Created task
   */
  async createTask(data) {
    const response = await api.post('/todos/tasks', data)
    return response.data
  },

  /**
   * Complete a task
   * @param {string} taskId - Task ID
   * @returns {Promise<Object>} Updated task
   */
  async completeTask(taskId) {
    const response = await api.post(`/todos/tasks/${taskId}/complete`)
    return response.data
  },

  /**
   * Create a new goal
   * @param {Object} data - Goal data
   * @returns {Promise<Object>} Created goal
   */
  async createGoal(data) {
    const response = await api.post('/todos/goals', data)
    return response.data
  },

  /**
   * Complete a habit
   * @param {string} habitId - Habit ID
   * @returns {Promise<Object>} Updated habit
   */
  async completeHabit(habitId) {
    const response = await api.post(`/todos/habits/${habitId}/complete`)
    return response.data
  },

  /**
   * Complete a goal
   * @param {string} goalId - Goal ID
   * @returns {Promise<Object>} Updated goal
   */
  async completeGoal(goalId) {
    const response = await api.post(`/todos/goals/${goalId}/complete`)
    return response.data
  }
}
