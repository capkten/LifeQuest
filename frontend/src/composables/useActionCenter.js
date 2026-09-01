import { ref, toValue } from 'vue'

function actionKey(item) {
  return item?.id == null ? null : `${item.kind}:${item.id}:${item.occurrence_date || ''}`
}

export function useActionCenter(options = {}) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const completingKey = ref(null)
  let requestId = 0

  const fetchActionCenter = options.fetchActionCenter || ((date) =>
    import('../services/actionCenter.js').then(({ actionCenterService }) => actionCenterService.getToday(date))
  )
  const completeTask = options.completeTask || ((id, occurrenceDate) =>
    import('../services/todo.js').then(({ todoService }) => todoService.completeTask(id, occurrenceDate))
  )
  const completeHabit = options.completeHabit || ((id) =>
    import('../services/todo.js').then(({ todoService }) => todoService.completeHabit(id))
  )
  const completeGoal = options.completeGoal || ((id) =>
    import('../services/todo.js').then(({ todoService }) => todoService.completeGoal(id))
  )

  async function load(date) {
    const currentRequestId = ++requestId
    loading.value = true
    error.value = null
    try {
      const result = await fetchActionCenter(toValue(date))
      if (currentRequestId === requestId) data.value = result
      return result
    } catch (cause) {
      if (currentRequestId === requestId) error.value = cause
      throw cause
    } finally {
      if (currentRequestId === requestId) loading.value = false
    }
  }

  async function complete(item) {
    const key = actionKey(item)
    if (!key || item.action !== 'complete' || item.completed) return null
    if (completingKey.value) return null

    completingKey.value = key
    error.value = null
    try {
      let result
      if (item.kind === 'task') result = await completeTask(item.id, item.occurrence_date)
      else if (item.kind === 'habit') result = await completeHabit(item.id)
      else if (item.kind === 'goal') result = await completeGoal(item.id)
      else return null
      await load()
      return result
    } catch (cause) {
      error.value = cause
      throw cause
    } finally {
      completingKey.value = null
    }
  }

  return {
    data,
    loading,
    error,
    completingKey,
    load,
    complete,
  }
}

export default useActionCenter
