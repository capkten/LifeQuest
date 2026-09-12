import { computed, ref } from 'vue'
import { getErrorMessage } from '../utils/errorMessage.js'
import { chinaDateKey } from '../utils/dateTime.js'

export { chinaDateKey }

export function useDailyWorkbench(api, {
  refreshRewards = async () => {},
  onChanged = () => {},
  newRequestId = () => crypto.randomUUID()
} = {}) {
  const data = ref(null)
  const loading = ref(false)
  const loadError = ref('')
  const actionError = ref('')
  const feedback = ref('')
  const warning = ref('')
  const pendingAction = ref(null)
  const draft = ref({ title: '', schedule: 'today', due_date: '' })
  const editingFocus = ref(false)
  const focusDraft = ref([])
  const focusError = ref('')
  let focusBase = null
  let creationRequest = null
  let sequence = 0
  let active = true

  const isCurrent = request => active && request === sequence
  const write = (request, callback) => {
    if (!isCurrent(request)) return false
    callback()
    return true
  }

  const busy = computed(() => pendingAction.value !== null)
  const candidates = computed(() => [...new Map([
    ...(data.value?.focus_tasks || []),
    ...Object.values(data.value?.task_groups || {}).flat()
  ].map(task => [task.id, task])).values()])
  const draftTasks = computed(() => focusDraft.value.map(id =>
    candidates.value.find(task => task.id === id) || { id, title: '任务已不可用，请移除后重选' }
  ))

  async function load(internal = false) {
    if (!active || (busy.value && !internal)) return false
    const request = ++sequence
    write(request, () => {
      loading.value = true
      loadError.value = ''
    })
    try {
      const result = await api.getWorkbench()
      if (!isCurrent(request)) return false
      if (!editingFocus.value) write(request, () => { data.value = result })
      return true
    } catch (error) {
      write(request, () => {
        loadError.value = getErrorMessage(error, '今日工作台加载失败，请重试。')
      })
      return false
    } finally {
      write(request, () => { loading.value = false })
    }
  }

  function beginAction(action) {
    if (!active || busy.value) return false
    const request = ++sequence
    write(request, () => {
      loading.value = false
      pendingAction.value = action
      actionError.value = ''
      feedback.value = ''
      warning.value = ''
    })
    return request
  }

  function finishAction(action, request) {
    write(request, () => {
      if (pendingAction.value === action) pendingAction.value = null
    })
  }

  function updateLocalTask(task, request) {
    if (!isCurrent(request) || !data.value) return
    const previous = candidates.value.find(candidate => candidate.id === task.id)
    const groups = Object.fromEntries(Object.entries(data.value.task_groups).map(([key, tasks]) =>
      [key, tasks.filter(candidate => candidate.id !== task.id)]
    ))
    if (task.status === 'pending' || task.status === 'in_progress') {
      const due = task.deadline ? chinaDateKey(task.deadline) : null
      const group = !due ? 'unscheduled' : due === data.value.date ? 'today' : due < data.value.date ? 'overdue' : 'upcoming'
      groups[group] = [task, ...groups[group]]
    }
    const focus = data.value.focus_tasks.map(candidate => candidate.id === task.id ? task : candidate)
    write(request, () => {
      data.value = {
        ...data.value,
        task_groups: groups,
        focus_tasks: focus,
        summary: {
          ...data.value.summary,
          open_tasks: Object.values(groups).reduce((count, tasks) => count + tasks.length, 0),
          today: groups.today.length,
          overdue: groups.overdue.length,
          unscheduled: groups.unscheduled.length,
          focus_completed: focus.filter(candidate => candidate.status === 'completed').length,
          completed_today: data.value.summary.completed_today + Number(Boolean(
            previous && previous.status !== 'completed' && task.status === 'completed' &&
            chinaDateKey(task.completed_at) === data.value.date
          ))
        }
      }
    })
  }

  async function refreshAfterSuccess(withRewards) {
    const workbenchRefresh = load(true)
    const request = sequence
    const refreshRewardsSafely = () => active ? refreshRewards() : undefined
    const notifyChangeSafely = () => active ? onChanged() : undefined
    const results = await Promise.allSettled([
      workbenchRefresh,
      withRewards ? Promise.resolve().then(refreshRewardsSafely) : Promise.resolve(),
      Promise.resolve().then(notifyChangeSafely)
    ])
    if (!isCurrent(request)) return request
    if (results.some(result => result.status === 'rejected') || results[0].value !== true) {
      write(request, () => {
        warning.value = '操作已保存，部分信息刷新失败。请刷新查看最新状态，无需重复提交。'
      })
    }
    return request
  }

  async function createTask() {
    if (!active) return false
    const title = draft.value.title.trim()
    if (!title || title.length > 200) {
      write(sequence, () => { actionError.value = '请输入 1 至 200 字的任务标题。' })
      return false
    }
    if (draft.value.schedule === 'date' && !draft.value.due_date) {
      write(sequence, () => { actionError.value = '请选择截止日期。' })
      return false
    }
    let request = beginAction('create')
    if (!request) return false
    try {
      const payload = { title, schedule: draft.value.schedule,
        due_date: draft.value.schedule === 'date' ? draft.value.due_date : null }
      const signature = JSON.stringify(payload)
      if (creationRequest?.signature !== signature) {
        creationRequest = { signature, id: newRequestId() }
      }
      const task = await api.createQuickTask({ ...payload, request_id: creationRequest.id })
      if (!isCurrent(request)) return false
      updateLocalTask(task, request)
      write(request, () => { draft.value = { title: '', schedule: 'today', due_date: '' } })
      creationRequest = null
      write(request, () => { feedback.value = '任务已创建，可以直接在下方完成或设为今日重点。' })
      request = await refreshAfterSuccess(false)
      return true
    } catch (error) {
      write(request, () => {
        actionError.value = getErrorMessage(error, '创建结果未确认，请重试；相同内容的重试不会重复创建任务。')
      })
      return false
    } finally {
      finishAction('create', request)
    }
  }

  async function completeTask(task) {
    if (!task || !['pending', 'in_progress'].includes(task.status)) return false
    let request = beginAction(`complete:${task.id}`)
    if (!request) return false
    try {
      const updated = await api.completeTask(task.id)
      if (!isCurrent(request)) return false
      updateLocalTask(updated, request)
      write(request, () => { feedback.value = `“${updated.title}”已完成，奖励已由服务器结算。` })
      request = await refreshAfterSuccess(true)
      return true
    } catch (error) {
      write(request, () => { actionError.value = getErrorMessage(error, '完成任务失败，请重试。') })
      return false
    } finally {
      finishAction(`complete:${task.id}`, request)
    }
  }

  function beginFocus() {
    if (!active || busy.value || !data.value) return
    write(sequence, () => {
      focusBase = { date: data.value.date, revision: data.value.revision }
      focusDraft.value = data.value.focus_tasks.map(task => task.id)
      focusError.value = ''
      editingFocus.value = true
    })
  }

  function cancelFocus() {
    if (!active || busy.value) return
    write(sequence, () => {
      editingFocus.value = false
      focusError.value = ''
    })
  }

  function toggleFocus(taskId) {
    if (!active || busy.value || !editingFocus.value) return
    write(sequence, () => {
      focusError.value = ''
      if (focusDraft.value.includes(taskId)) {
        focusDraft.value = focusDraft.value.filter(id => id !== taskId)
      } else if (focusDraft.value.length < 3 && candidates.value.some(task => task.id === taskId)) {
        focusDraft.value = [...focusDraft.value, taskId]
      } else {
        focusError.value = '每天最多选择三件事，请先移除一项。'
      }
    })
  }

  function moveFocus(taskId, direction) {
    if (!active || busy.value || !editingFocus.value) return
    const index = focusDraft.value.indexOf(taskId)
    const next = index + direction
    if (index < 0 || next < 0 || next >= focusDraft.value.length) return
    const ids = [...focusDraft.value]
    ids.splice(next, 0, ids.splice(index, 1)[0])
    write(sequence, () => { focusDraft.value = ids })
  }

  async function saveFocus() {
    if (!editingFocus.value || !focusBase) return false
    const request = beginAction('focus')
    if (!request) return false
    write(request, () => { focusError.value = '' })
    try {
      const result = await api.saveDailyFocus({ ...focusBase, task_ids: [...focusDraft.value] })
      if (!isCurrent(request)) return false
      write(request, () => {
        data.value = result
        editingFocus.value = false
        feedback.value = '今日重点已保存，其他设备刷新后也可看到。'
      })
      return true
    } catch (error) {
      write(request, () => {
        focusError.value = getErrorMessage(error, '保存失败，已保留你的选择，请重试。')
        if (error?.response?.status === 409) {
          focusError.value += ' 当前选择已保留，请取消编辑并重新加载后再选择。'
        }
      })
      return false
    } finally {
      finishAction('focus', request)
    }
  }

  function dispose() {
    active = false
    sequence += 1
  }

  return {
    data, loading, loadError, actionError, feedback, warning, pendingAction,
    draft, editingFocus, focusDraft, focusError,
    load, createTask, completeTask, beginFocus, cancelFocus, toggleFocus, moveFocus, saveFocus, dispose
  }
}
