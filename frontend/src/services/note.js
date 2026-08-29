import api from './api'

const ATTACHMENT_PATH_PATTERN = /\/api\/notes\/[0-9a-f-]+\/attachments\/[0-9a-f-]+/gi

export function resolveNoteAttachmentUrls(markdown = '') {
  const token = typeof localStorage === 'undefined' ? '' : localStorage.getItem('token')
  if (!token || !markdown) return markdown
  return markdown.replace(ATTACHMENT_PATH_PATTERN, (path) => `${path}?token=${encodeURIComponent(token)}`)
}

const NOTE_FIELDS = ['title', 'content', 'summary', 'tags', 'is_pinned', 'base_revision']

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

  // --- Sharing ---
  async getNotebookMembers(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}/members`)
    return response.data
  },

  async addNotebookMember(notebookId, data) {
    const response = await api.post(`/notes/notebooks/${notebookId}/members`, data)
    return response.data
  },

  async updateNotebookMember(notebookId, userId, data) {
    const response = await api.patch(`/notes/notebooks/${notebookId}/members/${userId}`, data)
    return response.data
  },

  async removeNotebookMember(notebookId, userId) {
    await api.delete(`/notes/notebooks/${notebookId}/members/${userId}`)
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

  async getCollaborationTicket(noteId) {
    const response = await api.post(`/notes/${noteId}/collaboration-ticket`, null)
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
    const response = await api.post(`/notes/${noteId}/open`, null, { skipErrorToast: true })
    return response.data
  },

  async discoverNotes(params) {
    const response = await api.get('/notes/discover', { params })
    return response.data
  },

  // --- Image upload ---
  async uploadImage(file, noteId) {
    if (!noteId) throw new Error('NOTE_MUST_BE_SAVED_BEFORE_UPLOAD')
    const formData = new FormData()
    formData.append('file', file)
    formData.append('note_id', noteId)
    const response = await api.post('/notes/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data.url
  },
}
