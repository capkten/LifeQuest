import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cultivationService } from '../services/cultivation'

export const useCultivationStore = defineStore('cultivation', () => {
  const overview = ref(null)
  const loading = ref(false)
  const error = ref(null)
  let requestVersion = 0

  function clear() {
    requestVersion += 1
    overview.value = null
    loading.value = false
    error.value = null
  }

  async function loadOverview() {
    const version = requestVersion
    loading.value = true
    error.value = null
    try {
      const nextOverview = await cultivationService.getOverview()
      if (version !== requestVersion) return null
      overview.value = nextOverview
      return overview.value
    } catch (requestError) {
      if (version !== requestVersion) return null
      error.value = requestError
      throw requestError
    } finally {
      if (version === requestVersion) loading.value = false
    }
  }

  async function refresh() {
    return loadOverview()
  }

  async function applySettlement(settlement) {
    if (settlement) {
      const currentOverview = overview.value || {}
      overview.value = {
        ...currentOverview,
        cultivation: (currentOverview.cultivation || 0) + (settlement.cultivation || 0),
        spirit_stones: (currentOverview.spirit_stones || 0) + (settlement.spirit_stones || 0),
        merit: (currentOverview.merit || 0) + (settlement.merit || 0),
      }
    }
    return await refresh()
  }

  return { overview, loading, error, loadOverview, refresh, applySettlement, clear }
})
