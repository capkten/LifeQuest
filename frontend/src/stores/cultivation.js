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

  function applySettlement(settlement) {
    const nextOverview = settlement?.overview || settlement
    if (nextOverview?.next_stage && nextOverview?.realm_key) {
      overview.value = nextOverview
    }
  }

  return { overview, loading, error, loadOverview, refresh, applySettlement }
})
