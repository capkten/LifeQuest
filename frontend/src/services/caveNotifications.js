import { ref } from 'vue'

let androidBridge

export function createCaveNotifications({ platform = 'web', storage = globalThis.localStorage,
  localNotifications = null, android = null, desktop = null, getOwnerId = () => null, now = () => Date.now(), api = {},
  setTimeout: scheduleTimeout = globalThis.setTimeout, clearTimeout: cancelTimeout = globalThis.clearTimeout } = {}) {
  let stored
  try { stored = storage?.getItem('cave:notifications') } catch {}
  const enabled = ref(stored !== 'false')
  const permission = ref(platform === 'web' ? 'in-app' : 'unknown')
  const notice = ref('')
  let revision = 0
  let disposed = false
  let runtimeTimer = null
  let removeListener = async () => {}
  let mutations = Promise.resolve()
  function serialize(operation) {
    const result = mutations.then(operation)
    mutations = result.catch(() => {})
    return result
  }

  async function local() {
    if (localNotifications) return localNotifications
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    // Capacitor proxies expose every property, including `then`; do not return the proxy from an async function.
    return Object.fromEntries(['checkPermissions', 'requestPermissions', 'createChannel', 'schedule', 'cancel',
      'removeDeliveredNotifications', 'checkExactNotificationSetting'].map(method =>
      [method, (...args) => LocalNotifications[method](...args)]))
  }

  function nativeDesktop() {
    if (desktop) return desktop
    const invoke = globalThis.window?.__TAURI__?.core?.invoke || globalThis.window?.__TAURI_INTERNALS__?.invoke
    return {
      checkPermissions: async () => ({ display: await invoke('plugin:notification|is_permission_granted') ? 'granted' : 'prompt' }),
      requestPermissions: async () => ({ display: await invoke('plugin:notification|request_permission') }),
      show: options => invoke('plugin:notification|notify', { options }),
    }
  }

  async function requestFromGesture() {
    if (disposed || !enabled.value || platform === 'web') return false
    try {
      const plugin = platform === 'windows' ? nativeDesktop() : await local()
      let result = await plugin.checkPermissions()
      if (result.display !== 'granted') result = await plugin.requestPermissions()
      permission.value = result.display === 'granted' ? 'granted' : 'denied'
    } catch { permission.value = 'denied' }
    notice.value = permission.value === 'granted' ? '' : '通知未开启，入定会继续，可在应用内迷你条查看。'
    return permission.value === 'granted'
  }

  async function nativeAndroid() {
    if (android) return android
    if (!androidBridge) {
      const { registerPlugin } = await import('@capacitor/core')
      if (androidBridge) return androidBridge
      const plugin = registerPlugin('CaveNotifications')
      androidBridge = Object.fromEntries(['showOngoing', 'cancel', 'getPendingAction', 'addListener'].map(method =>
        [method, (...args) => plugin[method](...args)]))
    }
    return androidBridge
  }

  async function syncSession(session, options = {}) {
    if (disposed) return false
    if (!session || session.status !== 'active' || !getOwnerId() || session.user_id !== String(getOwnerId())) {
      await clear()
      return false
    }
    const owner = getOwnerId()
    const requested = revision
    return serialize(() => requested === revision && owner === getOwnerId()
      ? updateSession(session, options) : false)
  }

  async function updateSession(session, { serverNow } = {}) {
    if (!enabled.value || !['android', 'windows'].includes(platform)) return false
    try {
      const plugin = platform === 'windows' ? nativeDesktop() : await local()
      permission.value = (await plugin.checkPermissions()).display === 'granted' ? 'granted' : 'denied'
      if (permission.value !== 'granted') {
        notice.value = '通知未开启，入定会继续，可在应用内迷你条查看。'
        return false
      }
      const parse = value => Date.parse(/(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`)
      const postedAt = now()
      const offset = serverNow ? parse(serverNow) - postedAt : 0
      const deadlineMs = parse(session.started_at) + session.target_duration * 60_000 - offset
      const ownerId = String(getOwnerId())
      if (platform === 'windows') {
        if (runtimeTimer !== null) cancelTimeout(runtimeTimer)
        const scheduledRevision = revision
        runtimeTimer = scheduleTimeout(async () => {
          if (disposed || !enabled.value || scheduledRevision !== revision || String(getOwnerId()) !== ownerId) return
          try { await plugin.show({ title: '入定结束，回来收功', body: session.todo_title || '这一段入定已结束，回来收功。' }) }
          catch { notice.value = '系统提醒暂不可用，可在应用内查看。' }
        }, Math.max(0, deadlineMs - now()))
        return true
      }
      const exact = await plugin.checkExactNotificationSetting?.()
      notice.value = exact?.exact_alarm === 'granted' ? '' : '未开启精确提醒，锁屏或省电时结束通知可能延迟。'
      await plugin.createChannel({ id: 'cave-completion', name: '入定结束提醒', importance: 3 })
      if (deadlineMs > postedAt) {
        await (await nativeAndroid()).showOngoing({ id: 190008, sessionId: session.id, ownerId,
          deadlineMs, taskTitle: session.todo_title || '安心入定', postedAt })
      }
      await plugin.schedule({ notifications: [{ id: 190008, title: '入定结束，回来收功',
        body: session.todo_title || '这一段入定已结束，回来收功。', channelId: 'cave-completion', smallIcon: 'ic_stat_cave',
        ...(deadlineMs > postedAt ? { schedule: { at: new Date(deadlineMs), allowWhileIdle: true } } : {}),
        ongoing: false, autoCancel: true,
        extra: { sessionId: session.id, ownerId, type: 'completion', postedAt: deadlineMs } }] })
      return true
    } catch {
      if (platform === 'android') await cancelAndroid()
      notice.value = '系统提醒暂不可用，入定会继续，可在应用内迷你条查看。'
      return false
    }
  }

  async function cancelAndroid() {
    const results = await Promise.allSettled([
      local().then(plugin => plugin.cancel({ notifications: [{ id: 190008 }] })),
      local().then(plugin => plugin.removeDeliveredNotifications({ notifications: [{ id: 190008 }] })),
      nativeAndroid().then(plugin => plugin.cancel({ id: 190008 })),
    ])
    if (results.some(result => result.status === 'rejected')) notice.value = '系统提醒暂不可用，可在应用内查看。'
  }

  async function clear() {
    revision += 1
    return serialize(async () => {
      if (runtimeTimer !== null) cancelTimeout(runtimeTimer)
      runtimeTimer = null
      if (platform === 'android') await cancelAndroid()
    })
  }

  async function setEnabled(value) {
    enabled.value = Boolean(value)
    try { storage?.setItem('cave:notifications', String(enabled.value)) } catch {}
    if (!enabled.value) await clear()
  }

  async function listen(onAction) {
    if (disposed || platform !== 'android') return async () => {}
    await removeListener()
    try {
      const plugin = await nativeAndroid()
      const receive = async event => {
        try {
          const actionRevision = revision
          const ownerId = getOwnerId()
          if (disposed || !enabled.value || !ownerId || event.ownerId !== String(ownerId) || !['open', 'finish'].includes(event.action) ||
            !['ongoing', 'completion'].includes(event.type) ||
            !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(event.sessionId)) return
          const result = await api.getSession(event.sessionId)
          if (actionRevision !== revision || getOwnerId() !== ownerId || result.session.id !== event.sessionId ||
            result.session.user_id !== String(ownerId)) return
          const current = Date.parse(result.server_now)
          const started = Date.parse(/(?:Z|[+-]\d\d:\d\d)$/.test(result.session.started_at)
            ? result.session.started_at : `${result.session.started_at}Z`)
          const duration = result.session.target_duration * 60_000
          const canComplete = result.session.status === 'active' && current - started >= duration * 0.8
          const returned = result.session.status !== 'active' || current - started >= duration ||
            (event.action === 'finish' && canComplete)
          await onAction({ action: event.action, type: event.type, sessionId: event.sessionId,
            session: result.session, canComplete, path: `/cave/${returned ? 'return' : 'session'}/${event.sessionId}`,
            delayMs: Math.max(0, Math.min(Number.MAX_SAFE_INTEGER, Math.floor(now() - event.postedAt) || 0)) })
        } catch { notice.value = '这段入定的回音暂时未到，可以回洞府查看。' }
      }
      const listener = await plugin.addListener('notificationAction', receive)
      removeListener = async () => { try { await listener.remove() } catch {} }
      if (disposed) { await removeListener(); return async () => {} }
      const pending = await plugin.getPendingAction()
      if (pending.action) await receive(pending.action)
      return removeListener
    } catch { return async () => {} }
  }

  async function dispose() {
    disposed = true
    await Promise.allSettled([clear(), removeListener()])
  }

  return { platform, isSupported: ['android', 'windows'].includes(platform), enabled, permission, notice,
    requestFromGesture, syncSession, clear, setEnabled, listen, dispose }
}
