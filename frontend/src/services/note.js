import api from './api'

const NOTE_FIELDS = ['title', 'content', 'summary', 'tags', 'is_pinned']

function notePayload(data = {}) {
  return NOTE_FIELDS.reduce((payload, field) => {
    if (data[field] !== undefined) payload[field] = data[field]
    return payload
  }, {})
}

export const noteService = {
  // --- Notebooks ---
  async getNotebooks() {
    const response = await api.get('/notes/notebooks')
    return response.data
  },

  async getNotebook(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}`)
    return response.data
  },

  async createNotebook(data) {
    const response = await api.post('/notes/notebooks', data)
    return response.data
  },

  async updateNotebook(notebookId, data) {
    const response = await api.put(`/notes/notebooks/${notebookId}`, data)
    return response.data
  },

  async deleteNotebook(notebookId) {
    await api.delete(`/notes/notebooks/${notebookId}`)
  },

  // --- Node tree ---
  async getTree(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}/tree`)
    return response.data
  },

  async getChildren(notebookId, parentId = null) {
    const params = parentId ? { parent_id: parentId } : {}
    const response = await api.get(`/notes/notebooks/${notebookId}/children`, { params })
    return response.data
  },

  // --- Folders ---
  async createFolder(notebookId, data) {
    const response = await api.post(`/notes/notebooks/${notebookId}/folders`, data)
    return response.data
  },

  // --- Notes ---
  async createNote(notebookId, data) {
    const payload = notePayload(data)
    if (Object.prototype.hasOwnProperty.call(data, 'parent_id')) payload.parent_id = data.parent_id
    const response = await api.post(`/notes/notebooks/${notebookId}/notes`, payload)
    return response.data
  },

  async getNote(noteId) {
    const response = await api.get(`/notes/${noteId}`)
    return response.data
  },

  async updateNote(noteId, data) {
    const response = await api.put(`/notes/${noteId}`, notePayload(data))
    return response.data
  },

  // --- Node operations ---
  async renameNode(nodeId, name) {
    const response = await api.patch(`/notes/nodes/${nodeId}`, { name })
    return response.data
  },

  async moveNode(nodeId, parentId) {
    const response = await api.patch(`/notes/nodes/${nodeId}`, { parent_id: parentId })
    return response.data
  },

  async deleteNode(nodeId) {
    await api.delete(`/notes/nodes/${nodeId}`)
  },

  // --- Search ---
  async searchNotes(query) {
    const response = await api.get('/notes/search', { params: { query } })
    return response.data
  },

  async getRecentNotes(limit) {
    const response = await api.get('/notes/recent', { params: { limit } })
    return response.data
  },

  async markNoteOpened(noteId) {
    const response = await api.post(`/notes/${noteId}/open`)
    return response.data
  },

  async discoverNotes(params) {
    const response = await api.get('/notes/discover', { params })
    return response.data
  },

  // --- Image upload ---
  async uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/notes/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data.url
  },
}
