import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cultivationService } from '../services/cultivation'

export const useCultivationStore = defineStore('cultivation', () => {
  const overview = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function loadOverview() {
    loading.value = true
    error.value = null
    try {
      overview.value = await cultivationService.getOverview()
      return overview.value
    } catch (requestError) {
      error.value = requestError
      throw requestError
    } finally {
      loading.value = false
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

  return { overview, loading, error, loadOverview, refresh, applySettlement }
})
