import { computed, getCurrentInstance, onUnmounted, ref } from 'vue'

let fallbackService = null

export function useCultivationRetreat(injectedApi = null, { autoTick = true } = {}) {
  const activeRetreat = ref(null)
  const remainingSeconds = ref(0)
  const loading = ref(false)
  const error = ref('')
  const latestEncounter = ref(null)
  const history = ref([])
  const catalog = ref([])

  let timerId = null

  async function getApi() {
    if (injectedApi) return injectedApi
    if (!fallbackService) {
      const mod = await import('../services/cultivationRetreat.js')
      fallbackService = mod.cultivationRetreatService
    }
    return fallbackService
  }

  const totalSeconds = computed(() => {
    return activeRetreat.value ? activeRetreat.value.target_duration * 60 : 0
  })

  const progressRatio = computed(() => {
    if (!totalSeconds.value) return 0
    const elapsed = totalSeconds.value - remainingSeconds.value
    return Math.min(1, Math.max(0, elapsed / totalSeconds.value))
  })

  const isFocusing = computed(() => activeRetreat.value !== null && remainingSeconds.value > 0)
  const isCompleted = computed(() => activeRetreat.value !== null && remainingSeconds.value <= 0)

  const canComplete = computed(() => {
    if (!activeRetreat.value) return false
    const elapsed = totalSeconds.value - remainingSeconds.value
    return elapsed >= Math.floor(totalSeconds.value * 0.8)
  })

  function syncRemaining(now = Date.now()) {
    if (!activeRetreat.value) {
      remainingSeconds.value = 0
      return
    }
    const started = new Date(activeRetreat.value.started_at).getTime()
    const targetEnd = started + activeRetreat.value.target_duration * 60 * 1000
    remainingSeconds.value = Math.max(0, Math.round((targetEnd - now) / 1000))
  }

  function tick(customNow) {
    syncRemaining(customNow)
  }

  function startTimer() {
    stopTimer()
    timerId = setInterval(() => {
      syncRemaining()
      if (remainingSeconds.value <= 0) {
        stopTimer()
      }
    }, 1000)
  }

  function stopTimer() {
    if (timerId) {
      clearInterval(timerId)
      timerId = null
    }
  }

  async function fetchActive() {
    loading.value = true
    error.value = ''
    try {
      const api = await getApi()
      const data = await api.getActive()
      if (data && data.status === 'active') {
        activeRetreat.value = data
        syncRemaining()
        if (autoTick && remainingSeconds.value > 0) {
          startTimer()
        }
      } else {
        activeRetreat.value = null
        remainingSeconds.value = 0
        stopTimer()
      }
      return activeRetreat.value
    } catch (err) {
      error.value = err?.message || '获取活跃闭关状态失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function startRetreat({ targetDuration = 25, todoId = null } = {}) {
    loading.value = true
    error.value = ''
    try {
      const api = await getApi()
      const data = await api.startRetreat({
        target_duration: targetDuration,
        todo_id: todoId,
      })
      activeRetreat.value = data
      syncRemaining()
      if (autoTick) {
        startTimer()
      }
      return data
    } catch (err) {
      error.value = err?.message || '开启闭关失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function completeRetreat({ markTodoComplete = false } = {}) {
    if (!activeRetreat.value) return null
    loading.value = true
    error.value = ''
    try {
      const api = await getApi()
      const data = await api.completeRetreat(activeRetreat.value.id, {
        mark_todo_complete: markTodoComplete,
      })
      if (data.encounter_result) {
        latestEncounter.value = data.encounter_result
      }
      activeRetreat.value = null
      remainingSeconds.value = 0
      stopTimer()
      return data
    } catch (err) {
      error.value = err?.message || '结算闭关失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function abortRetreat() {
    if (!activeRetreat.value) return null
    loading.value = true
    error.value = ''
    try {
      const api = await getApi()
      const data = await api.abortRetreat(activeRetreat.value.id)
      activeRetreat.value = null
      remainingSeconds.value = 0
      stopTimer()
      return data
    } catch (err) {
      error.value = err?.message || '中止闭关失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory({ limit = 20, offset = 0 } = {}) {
    try {
      const api = await getApi()
      const data = await api.getHistory({ limit, offset })
      history.value = data
      return data
    } catch (err) {
      error.value = err?.message || '获取闭关记录失败'
      return []
    }
  }

  async function fetchCatalog() {
    try {
      const api = await getApi()
      const data = await api.getCatalog()
      catalog.value = data
      return data
    } catch (err) {
      error.value = err?.message || '获取机缘图鉴失败'
      return []
    }
  }

  function clearLatestEncounter() {
    latestEncounter.value = null
  }

  if (getCurrentInstance()) {
    onUnmounted(() => {
      stopTimer()
    })
  }

  return {
    activeRetreat,
    remainingSeconds,
    totalSeconds,
    progressRatio,
    isFocusing,
    isCompleted,
    canComplete,
    loading,
    error,
    latestEncounter,
    history,
    catalog,
    tick,
    syncRemaining,
    fetchActive,
    startRetreat,
    completeRetreat,
    abortRetreat,
    fetchHistory,
    fetchCatalog,
    clearLatestEncounter,
    stopTimer,
  }
}
