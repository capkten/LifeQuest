import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

export function useUserStats() {
  const authStore = useAuthStore()
  const user = computed(() => authStore.user)

  const requiredExp = computed(() => {
    const level = user.value?.level || 1
    return Math.floor(100 * Math.pow(1.5, level - 1))
  })

  const expPercent = computed(() => {
    if (!user.value) return 0
    return Math.min(100, Math.round((user.value.experience / requiredExp.value) * 100))
  })

  return { user, requiredExp, expPercent }
}
