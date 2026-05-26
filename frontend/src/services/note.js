import api from './api'

export const noteService = {
  /**
   * Get all notebooks for current user
   * @returns {Promise<Array>} List of notebooks
   */
  async getNotebooks() {
    const response = await api.get('/notes/notebooks')
    return response.data
  },

  /**
   * Get a single notebook by ID
   * @param {string} notebookId - Notebook ID
   * @returns {Promise<Object>} Notebook data
   */
  async getNotebook(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}`)
    return response.data
  },

  /**
   * Create a new notebook
   * @param {Object} data - Notebook data (name, description)
   * @returns {Promise<Object>} Created notebook
   */
  async createNotebook(data) {
    const response = await api.post('/notes/notebooks', data)
    return response.data
  },

  /**
   * Get folders in a notebook
   * @param {string} notebookId - Notebook ID
   * @returns {Promise<Array>} List of folders
   */
  async getFolders(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}/folders`)
    return response.data
  },

  /**
   * Create a new folder
   * @param {Object} data - Folder data (notebook_id, name, parent_id?)
   * @returns {Promise<Object>} Created folder
   */
  async createFolder(data) {
    const response = await api.post('/notes/folders', data)
    return response.data
  },

  /**
   * Get notes in a folder
   * @param {string} folderId - Folder ID
   * @returns {Promise<Array>} List of notes
   */
  async getNotesByFolder(folderId) {
    const response = await api.get(`/notes/folder/${folderId}`)
    return response.data
  },

  /**
   * Get a single note by ID
   * @param {string} noteId - Note ID
   * @returns {Promise<Object>} Note data
   */
  async getNote(noteId) {
    const response = await api.get(`/notes/${noteId}`)
    return response.data
  },

  /**
   * Create a new note
   * @param {Object} data - Note data (folder_id, title, content?, summary?, tags?)
   * @returns {Promise<Object>} Created note
   */
  async createNote(data) {
    const response = await api.post('/notes/', data)
    return response.data
  },

  /**
   * Update a note
   * @param {string} noteId - Note ID
   * @param {Object} data - Note data to update
   * @returns {Promise<Object>} Updated note
   */
  async updateNote(noteId, data) {
    const response = await api.put(`/notes/${noteId}`, data)
    return response.data
  },

  /**
   * Delete a note
   * @param {string} noteId - Note ID
   * @returns {Promise<void>}
   */
  async deleteNote(noteId) {
    await api.delete(`/notes/${noteId}`)
  },

  /**
   * Search notes
   * @param {string} query - Search query
   * @returns {Promise<Array>} List of matching notes
   */
  async searchNotes(query) {
    const response = await api.get('/notes/search', { params: { query } })
    return response.data
  }
}
