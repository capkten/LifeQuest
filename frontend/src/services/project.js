import api from './api'

export const projectService = {
  // Projects
  async getProjects(params) {
    const r = await api.get('/projects', { params })
    return r.data
  },
  async createProject(data) {
    const r = await api.post('/projects', data)
    return r.data
  },
  async getProject(id) {
    const r = await api.get(`/projects/${id}`)
    return r.data
  },
  async updateProject(id, data) {
    const r = await api.put(`/projects/${id}`, data)
    return r.data
  },
  async deleteProject(id) {
    await api.delete(`/projects/${id}`)
  },
  async completeProject(id) {
    const r = await api.post(`/projects/${id}/complete`)
    return r.data
  },

  // Phases
  async createPhase(projectId, data) {
    const r = await api.post(`/projects/${projectId}/phases`, data)
    return r.data
  },
  async updatePhase(phaseId, data) {
    const r = await api.put(`/projects/phases/${phaseId}`, data)
    return r.data
  },
  async deletePhase(phaseId) {
    await api.delete(`/projects/phases/${phaseId}`)
  },

  // Milestones
  async createMilestone(projectId, data) {
    const r = await api.post(`/projects/${projectId}/milestones`, data)
    return r.data
  },
  async updateMilestone(msId, data) {
    const r = await api.put(`/projects/milestones/${msId}`, data)
    return r.data
  },
  async deleteMilestone(msId) {
    await api.delete(`/projects/milestones/${msId}`)
  },
  async reachMilestone(msId) {
    const r = await api.post(`/projects/milestones/${msId}/reach`)
    return r.data
  },

  // Project tasks
  async createTask(projectId, data) {
    const r = await api.post(`/projects/${projectId}/tasks`, data)
    return r.data
  },
  async getProjectTasks(projectId, params) {
    const r = await api.get(`/projects/${projectId}/tasks`, { params })
    return r.data
  },
  async moveTask(taskId, data) {
    const r = await api.put(`/projects/tasks/${taskId}/move`, data)
    return r.data
  }
}
