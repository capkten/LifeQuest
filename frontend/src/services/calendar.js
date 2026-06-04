import api from './api'

export const calendarService = {
  /**
   * Get events in a date range
   * @param {string} start - Start date (YYYY-MM-DD)
   * @param {string} end - End date (YYYY-MM-DD)
   * @returns {Promise<Array>} List of events
   */
  async getEvents(start, end) {
    const response = await api.get('/calendar/events', { params: { start, end } })
    return response.data
  },

  /**
   * Get detail for a specific day
   * @param {string} date - Date string (YYYY-MM-DD)
   * @returns {Promise<Object>} Day detail
   */
  async getDayDetail(date) {
    const response = await api.get(`/calendar/day/${date}`)
    return response.data
  },
}
