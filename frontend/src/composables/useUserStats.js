import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useCultivationStore } from '../stores/cultivation'

export function useUserStats() {
  const authStore = useAuthStore()
  const cultivationStore = useCultivationStore()
  const user = computed(() => authStore.user)
  const cultivationOverview = computed(() => cultivationStore.overview)

  const requiredExp = computed(() => {
    const level = user.value?.level || 1
    return Math.floor(100 * Math.pow(1.5, level - 1))
  })

  const expPercent = computed(() => {
    if (!user.value) return 0
    return Math.min(100, Math.round((user.value.experience / requiredExp.value) * 100))
  })

  const cultivationPercent = computed(() => {
    const overview = cultivationOverview.value
    const nextStage = overview?.next_stage
    if (!overview || !nextStage || nextStage.next_threshold == null) return 0

    const currentThreshold = Number(nextStage.current_threshold || 0)
    const nextThreshold = Number(nextStage.next_threshold)
    const currentCultivation = Number(overview.cultivation || 0)
    if (nextThreshold <= currentThreshold) return 100

    return Math.min(100, Math.max(0, Math.round(
      ((currentCultivation - currentThreshold) / (nextThreshold - currentThreshold)) * 100
    )))
  })

  return {
    user,
    requiredExp,
    expPercent,
    cultivationOverview,
    cultivationLoading: computed(() => cultivationStore.loading),
    cultivationError: computed(() => cultivationStore.error),
    cultivationPercent,
    loadCultivation: cultivationStore.loadOverview,
    refreshCultivation: cultivationStore.refresh,
    applyCultivationSettlement: cultivationStore.applySettlement
  }
}
