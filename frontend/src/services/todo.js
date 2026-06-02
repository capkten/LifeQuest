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
  },

  /**
   * Update a habit
   * @param {string} habitId - Habit ID
   * @param {Object} data - Updated habit data
   * @returns {Promise<Object>} Updated habit
   */
  async updateHabit(habitId, data) {
    const response = await api.put(`/todos/habits/${habitId}`, data)
    return response.data
  },

  /**
   * Delete a habit
   * @param {string} habitId - Habit ID
   */
  async deleteHabit(habitId) {
    await api.delete(`/todos/habits/${habitId}`)
  },

  /**
   * Update a task
   * @param {string} taskId - Task ID
   * @param {Object} data - Updated task data
   * @returns {Promise<Object>} Updated task
   */
  async updateTask(taskId, data) {
    const response = await api.put(`/todos/tasks/${taskId}`, data)
    return response.data
  },

  /**
   * Delete a task
   * @param {string} taskId - Task ID
   */
  async deleteTask(taskId) {
    await api.delete(`/todos/tasks/${taskId}`)
  },

  /**
   * Update a goal
   * @param {string} goalId - Goal ID
   * @param {Object} data - Updated goal data
   * @returns {Promise<Object>} Updated goal
   */
  async updateGoal(goalId, data) {
    const response = await api.put(`/todos/goals/${goalId}`, data)
    return response.data
  },

  /**
   * Delete a goal
   * @param {string} goalId - Goal ID
   */
  async deleteGoal(goalId) {
    await api.delete(`/todos/goals/${goalId}`)
  },

  /**
   * Get subtasks for a task
   * @param {string} taskId - Task ID
   * @returns {Promise<Array>} List of subtasks
   */
  async getSubtasks(taskId) {
    const response = await api.get(`/todos/subtasks/task/${taskId}`)
    return response.data
  },

  /**
   * Create a subtask for a task
   * @param {string} taskId - Task ID
   * @param {Object} data - Subtask data
   * @returns {Promise<Object>} Created subtask
   */
  async createSubtask(taskId, data) {
    const response = await api.post('/todos/subtasks', { ...data, task_id: taskId })
    return response.data
  },

  /**
   * Complete a subtask
   * @param {string} subtaskId - Subtask ID
   * @returns {Promise<Object>} Updated subtask
   */
  async completeSubtask(subtaskId) {
    const response = await api.put(`/todos/subtasks/${subtaskId}`, { is_completed: true })
    return response.data
  },

  /**
   * Delete a subtask
   * @param {string} subtaskId - Subtask ID
   */
  async deleteSubtask(subtaskId) {
    await api.delete(`/todos/subtasks/${subtaskId}`)
  }
}
