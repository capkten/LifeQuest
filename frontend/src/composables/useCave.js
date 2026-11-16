import { computed, ref } from 'vue'
import { chinaDateKey } from '../utils/dateTime.js'
import { defaultCavePersistence } from '../services/cavePersistence.js'
import { defaultCaveConnectivity } from '../services/caveConnectivity.js'

function requestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, letter => {
    const value = globalThis.crypto.getRandomValues(new Uint8Array(1))[0] & 15
    return (letter === 'x' ? value : (value & 3) | 8).toString(16)
  })
}

export function useCave(api, {
  now = () => Date.now(),
  newRequestId = requestId,
  identity = null,
  persistence = defaultCavePersistence,
  connectivity = defaultCaveConnectivity,
  scheduler = {},
} = {}) {
  let active = true
  let sequence = 0
  let currentUserId = identity || null
  let hydratedUserId = null
  let cachedEnvelope = null
  let unsubscribeConnectivity = null
  const timers = new Map()
  const scheduleTimeout = scheduler.setTimeout || globalThis?.setTimeout?.bind(globalThis)
  const clearScheduledTimeout = scheduler.clearTimeout || globalThis?.clearTimeout?.bind(globalThis)
  const currentTime = ref(now())
  const mode = computed(() => {
    const hour = Number(new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Shanghai', hour: '2-digit', hourCycle: 'h23',
    }).format(currentTime.value))
    return hour >= 5 && hour < 11 ? 'morning' : hour >= 11 && hour < 17 ? 'day' : hour >= 17 && hour < 21 ? 'dusk' : 'night'
  })

  const data = ref(null)
  const onboarding = computed(() => data.value?.onboarding || null)
  const onboardingPending = ref(null)
  const onboardingError = ref('')
  let onboardingRequest = null
  let onboardingRevision = 0

  async function onboardingAction(action, method, payload = {}) {
    if (!active || onboardingPending.value) return false
    if (!connectivity.isOnline()) {
      onboardingError.value = '联网后再确认引导，眼前的进度已留好。'
      return false
    }
    const userId = currentUserId
    const epoch = identityEpoch
    onboardingPending.value = action
    onboardingError.value = ''
    const signature = JSON.stringify({ action, ...payload })
    if (onboardingRequest?.signature !== signature) onboardingRequest = { signature, id: newRequestId() }
    try {
      const result = await api[method]({ ...payload, request_id: onboardingRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      onboardingRequest = null
      offline.value = false
      onboardingRevision += 1
      data.value = { ...data.value, onboarding: result }
      if (currentUserId) {
        try { await persistCache() } catch {
          if (currentIdentity(userId, epoch)) onboardingError.value = '引导已确认，本地保存稍慢，请保持联网。'
        }
      }
      return currentIdentity(userId, epoch) ? result : false
    } catch (error) {
      if (currentIdentity(userId, epoch)) {
        if (currentUserId && transportFailure(error)) offline.value = true
        onboardingError.value = error?.response?.data?.detail || '引导的回音稍慢，可以再试一次。'
      }
      return false
    } finally {
      if (currentIdentity(userId, epoch)) onboardingPending.value = null
    }
  }

  const skipOnboarding = () => onboardingAction('skip', 'skipOnboarding')
  const completeOnboarding = sessionId => onboardingAction('complete', 'completeOnboarding', { session_id: sessionId })
  const offline = ref(false)
  const cacheDate = ref(null)
  const staleCache = ref(false)
  const pendingSettlements = ref([])
  const panels = Object.fromEntries(['growth', 'codex', 'companions', 'letters', 'letter'].map(key => [key, {
    value: ref(null), loading: ref(false), error: ref(''), sequence: 0,
  }]))

  let companionRevision = 0
  let letterRevision = 0

  async function loadPanel(key, method, ...args) {
    if (!active) return false
    const revision = companionRevision
    const inboxRevision = letterRevision
    const panel = panels[key]
    const request = ++panel.sequence
    panel.loading.value = true
    panel.error.value = ''
    try {
      let result = await api[method](...args)
      if (!active || request !== panel.sequence) return false
      if (revision !== companionRevision) {
        if (key === 'companions') result = panels.companions.value.value
        if (key === 'growth') result = { ...result, companions: panels.companions.value.value }
      }
      if (inboxRevision !== letterRevision) {
        if (key === 'letters') result = panels.letters.value.value
        if (key === 'letter') result = panels.letters.value.value.letters.find(letter => letter.id === args[0]) || result
      }
      panel.value.value = result
      return result
    } catch {
      if (active && request === panel.sequence) panel.error.value = '山中来信稍慢，可以再试一次。'
      return false
    } finally {
      if (active && request === panel.sequence) panel.loading.value = false
    }
  }

  const companionPending = ref(null)
  let companionRequest = null

  async function activateCompanion(key) {
    if (!active || companionPending.value || !onlineWrite()) return false
    const userId = currentUserId
    const epoch = identityEpoch
    companionPending.value = key
    panels.companions.error.value = ''
    if (companionRequest?.key !== key) companionRequest = { key, id: newRequestId() }
    try {
      const result = await api.activateCompanion(key, { request_id: companionRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      companionRequest = null
      companionRevision += 1
      panels.companions.value.value = result
      if (panels.growth.value.value) panels.growth.value.value = { ...panels.growth.value.value, companions: result }
      if (data.value) data.value = { ...data.value, companions: result, daily_note: result.daily_note }
      return result
    } catch (error) {
      if (currentIdentity(userId, epoch)) panels.companions.error.value = error?.response?.data?.detail || '伙伴的回音稍慢，可以再试一次。'
      return false
    } finally {
      if (currentIdentity(userId, epoch)) companionPending.value = null
    }
  }

  const letterPending = ref(null)
  let letterRequest = null

  async function letterAction(id, action, method) {
    if (!active || letterPending.value || !onlineWrite()) return false
    const userId = currentUserId
    const epoch = identityEpoch
    letterPending.value = { id, action }
    panels.letter.error.value = ''
    const signature = `${id}:${action}`
    if (letterRequest?.signature !== signature) letterRequest = { signature, id: newRequestId() }
    try {
      const result = await api[method](id, { request_id: letterRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      letterRequest = null
      letterRevision += 1
      panels.letters.value.value = result
      if (panels.letter.value.value?.id === id) {
        panels.letter.value.value = result.letters.find(letter => letter.id === id)
      }
      if (data.value) data.value = { ...data.value, unread_letters_count: result.unread_count }
      return result
    } catch (error) {
      if (currentIdentity(userId, epoch)) panels.letter.error.value = error?.response?.data?.detail || '书信的回音稍慢，可以再试一次。'
      return false
    } finally {
      if (currentIdentity(userId, epoch)) letterPending.value = null
    }
  }

  const claimLetter = id => letterAction(id, 'claim', 'claimLetter')
  const declineLetter = id => letterAction(id, 'decline', 'declineLetter')
  const acceptLetter = id => letterAction(id, 'accept', 'acceptLetter')
  const readLetter = id => letterAction(id, 'read', 'readLetter')
  const loadLetter = id => loadPanel('letter', 'getLetter', id)
  const loadLetters = () => loadPanel('letters', 'getLetters')
  const loadGrowth = () => loadPanel('growth', 'getGrowth')
  const loadCodex = () => loadPanel('codex', 'getCodex')
  const loadCompanions = () => loadPanel('companions', 'getCompanions')
  const defaultDuration = computed(() => data.value?.first_session !== false ? 15 : mode.value === 'morning' ? 45 : 25)
  const selectedDuration = ref(15)
  const preparingSession = ref(false)
  const sessionTask = ref(null)
  const markTodoComplete = ref(true)
  const settledSession = ref(null)

  function prepareSession(task = primarySign.value) {
    if (!active || pendingAction.value || activeSession.value) return false
    sessionTask.value = task
    markTodoComplete.value = true
    selectedDuration.value = defaultDuration.value
    preparingSession.value = true
    return true
  }

  const loading = ref(false)
  const loadError = ref('')
  const primarySign = computed(() => data.value?.primary_sign || null)
  const signs = computed(() => data.value?.signs || [])
  const rerollUsed = computed(() => data.value?.reroll_used === true)
  const activeSession = computed(() => data.value?.active_session || null)
  const serverOffset = ref(0)
  const getServerNow = () => new Date(now() + serverOffset.value).toISOString()
  const remainingSeconds = computed(() => {
    if (!activeSession.value) return 0
    const startedAt = activeSession.value.started_at
    const started = Date.parse(/(?:Z|[+-]\d\d:\d\d)$/.test(startedAt) ? startedAt : `${startedAt}Z`)
    return Math.max(0, Math.ceil((started + activeSession.value.target_duration * 60_000 - currentTime.value - serverOffset.value) / 1000))
  })
  const pendingReturn = computed(() => {
    if (data.value?.pending_return) return data.value.pending_return
    if (activeSession.value && remainingSeconds.value === 0) {
      return { session_id: activeSession.value.id, status: 'ready', todo_title: activeSession.value.todo_title || null }
    }
    return null
  })
  const canComplete = computed(() => Boolean(activeSession.value) &&
    remainingSeconds.value <= activeSession.value.target_duration * 60 * 0.2)
  const actionError = ref('')
  const pendingAction = ref(null)

  function transportFailure(error) {
    return !error?.response && !error?.status
  }

  function onlineWrite() {
    if (!currentUserId || (!offline.value && connectivity.isOnline())) return true
    actionError.value = '离线时先安心坐一会儿，联网后再继续这件事。'
    return false
  }

  function currentIdentity(requestUser, epoch) {
    return active && requestUser === currentUserId && epoch === identityEpoch
  }

  let identityEpoch = 0
  let hydration = null

  function maskStaleDaily() {
    if (!currentUserId || !data.value) return
    const today = chinaDateKey(now() + serverOffset.value)
    staleCache.value = cacheDate.value !== today
    if (staleCache.value) data.value = { ...data.value, date: today, fortune: null,
      signs: [], primary_sign: null, summary: null, reroll_used: false, all_signs_done: false }
  }

  function visibleCache(cache) {
    if (!cache?.snapshot) return false
    serverOffset.value = Number(cache.serverOffsetMs) || 0
    currentTime.value = now()
    cacheDate.value = cache.date || cache.snapshot.date || null
    data.value = cache.snapshot
    maskStaleDaily()
    settledSession.value = cache.settledSession || null
    return true
  }

  async function hydrate() {
    if (!currentUserId) return false
    if (hydratedUserId === currentUserId) return Boolean(cachedEnvelope?.cache)
    if (hydration) return hydration
    const userId = currentUserId
    const epoch = identityEpoch
    hydration = (async () => {
      try {
        const envelope = await persistence.load(userId)
        if (!currentIdentity(userId, epoch)) return false
        cachedEnvelope = envelope || { cache: null, queue: [] }
        pendingSettlements.value = Array.isArray(cachedEnvelope.queue) ? cachedEnvelope.queue : []
        hydratedUserId = userId
        pendingSettlements.value.forEach(scheduleRetry)
        return visibleCache(cachedEnvelope.cache)
      } catch {
        if (currentIdentity(userId, epoch)) loadError.value = '洞府的本地来信暂时无法读取，请联网后再试。'
        return false
      }
    })().finally(() => { if (currentIdentity(userId, epoch)) hydration = null })
    return hydration
  }

  let persistenceWrite = Promise.resolve()

  function writeEnvelope(update) {
    const userId = currentUserId
    const epoch = identityEpoch
    const write = persistenceWrite.catch(() => {}).then(async () => {
      if (!currentIdentity(userId, epoch)) return false
      const envelope = update(cachedEnvelope || { cache: null, queue: [] })
      await persistence.save(userId, envelope)
      if (!currentIdentity(userId, epoch)) return false
      cachedEnvelope = envelope
      pendingSettlements.value = envelope.queue
      return true
    })
    persistenceWrite = write
    return write
  }

  async function persistCache(queue) {
    if (!currentUserId || !data.value) return false
    const snapshot = JSON.parse(JSON.stringify(data.value))
    const date = staleCache.value ? cacheDate.value : snapshot.date || cacheDate.value
    const cache = { date, snapshot, serverOffsetMs: serverOffset.value,
      settledSession: settledSession.value ? JSON.parse(JSON.stringify(settledSession.value)) : null }
    return writeEnvelope(envelope => ({ cache, queue: queue || envelope.queue }))
  }

  async function setUser(userId) {
    if (!active) return false
    const nextId = userId || null
    if (nextId !== currentUserId) {
      const previous = currentUserId
      identityEpoch += 1
      sequence += 1
      currentUserId = nextId
      hydration = null
      hydratedUserId = null
      cachedEnvelope = null
      data.value = null
      settledSession.value = null
      pendingSettlements.value = []
      cacheDate.value = null
      staleCache.value = false
      pendingAction.value = null
      preparingSession.value = false
      sessionTask.value = null
      markTodoComplete.value = true
      selectedDuration.value = 15
      serverOffset.value = 0
      currentTime.value = now()
      loading.value = false
      loadError.value = ''
      actionError.value = ''
      draftTitle.value = ''
      candidates.value = []
      candidatesLoading.value = false
      candidatesError.value = ''
      candidateSequence += 1
      companionRevision += 1
      letterRevision += 1
      Object.values(panels).forEach(panel => {
        panel.sequence += 1
        panel.value.value = null
        panel.loading.value = false
        panel.error.value = ''
      })
      companionPending.value = null
      letterPending.value = null
      onboardingPending.value = null
      onboardingError.value = ''
      onboardingRequest = null
      onboardingRevision += 1
      companionRequest = letterRequest = startRequest = settlementRequest = null
      acknowledgementRequest = rerollRequest = selectionRequest = creationRequest = null
      opened = false
      rolloverDate = null
      retryPromise = null
      timers.forEach(timer => clearScheduledTimeout?.(timer))
      timers.clear()
      const epoch = identityEpoch
      if (previous) {
        try {
          await persistenceWrite.catch(() => {})
          await persistence.clear(previous)
        } catch {
          if (active && epoch === identityEpoch) loadError.value = '本地洞府记录未能清除，请检查设备存储。'
        }
      }
      if (!active || epoch !== identityEpoch) return false
    }
    offline.value = currentUserId ? !connectivity.isOnline() : false
    if (currentUserId) return hydrate()
    return false
  }

  let startRequest = null

  async function startSession() {
    if (!active || pendingAction.value || !onlineWrite()) return false
    if (!data.value) {
      actionError.value = '洞府的来信尚未送到，请刷新后再入定。'
      return false
    }
    if (activeSession.value) {
      preparingSession.value = false
      return activeSession.value
    }
    sequence += 1
    loading.value = false
    const userId = currentUserId
    const epoch = identityEpoch
    pendingAction.value = 'start'
    actionError.value = ''
    try {
      const task = preparingSession.value ? sessionTask.value : primarySign.value
      const payload = { target_duration: selectedDuration.value, todo_id: task?.id || null,
        mark_todo_complete: markTodoComplete.value }
      const signature = JSON.stringify(payload)
      if (startRequest?.signature !== signature) startRequest = { signature, id: newRequestId() }
      const session = await api.startSession({ ...payload, request_id: startRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      startRequest = null
      preparingSession.value = false
      data.value = { ...data.value, active_session: session, first_session: false }
      if (currentUserId) {
        try { await persistCache() } catch {
          if (currentIdentity(userId, epoch)) actionError.value = '入定已开始，本地保存未确认，请保持联网。'
        }
      }
      if (!currentIdentity(userId, epoch)) return false
      tick()
      return session
    } catch (error) {
      if (currentIdentity(userId, epoch)) {
        if (currentUserId && transportFailure(error)) offline.value = true
        actionError.value = '入定的回音暂时未到，请再试一次。'
      }
      return false
    } finally {
      if (currentIdentity(userId, epoch)) pendingAction.value = null
    }
  }

  function cachedSession(id) {
    const session = activeSession.value?.id === id ? activeSession.value : settledSession.value?.id === id ? settledSession.value : null
    if (session?.status === 'active') {
      sessionTask.value = session.todo_id ? { id: session.todo_id, title: session.todo_title } : session.todo_title ? { title: session.todo_title } : null
      markTodoComplete.value = session.mark_todo_complete === true
    }
    return session || false
  }

  async function loadSession(id) {
    if (!active || pendingAction.value) return false
    const userId = currentUserId
    const epoch = identityEpoch
    if (currentUserId) {
      await hydrate()
      if (!currentIdentity(userId, epoch) || pendingAction.value) return false
      if (!connectivity.isOnline()) {
        offline.value = true
        return cachedSession(id)
      }
    }
    const request = ++sequence
    loading.value = true
    actionError.value = ''
    try {
      const result = await api.getSession(id)
      if (!currentIdentity(userId, epoch) || request !== sequence) return false
      offline.value = false
      serverOffset.value = Date.parse(result.server_now) - now()
      currentTime.value = now()
      const session = result.session
      if (session.status === 'active') {
        data.value = { ...data.value, active_session: session, first_session: false }
        sessionTask.value = session.todo_id ? { id: session.todo_id, title: session.todo_title } : null
        markTodoComplete.value = session.mark_todo_complete
      } else {
        settledSession.value = session
        if (activeSession.value?.id === session.id) data.value = { ...data.value, active_session: null }
        if (session.return_summary && result.acknowledged === false &&
          (!data.value?.pending_return || data.value.pending_return.status === 'ready')) {
          data.value = { ...data.value, pending_return: {
            session_id: session.id, status: 'unviewed', todo_title: session.todo_title || null,
          } }
        }
      }
      if (currentUserId) {
        try { await persistCache() } catch {
          if (currentIdentity(userId, epoch)) actionError.value = '这段入定已送达，本地保存稍慢。'
        }
      }
      return currentIdentity(userId, epoch) && request === sequence ? session : false
    } catch (error) {
      if (currentIdentity(userId, epoch) && request === sequence && currentUserId && transportFailure(error)) {
        offline.value = true
        const restored = cachedSession(id)
        if (restored) return restored
      }
      if (currentIdentity(userId, epoch) && request === sequence) {
        if ([401, 403].includes(error?.response?.status || error?.status)) {
          data.value = null
          settledSession.value = null
          offline.value = false
        }
        actionError.value = '这段入定的回音暂时未到，可以再试一次。'
      }
      return false
    } finally {
      if (active && request === sequence) loading.value = false
    }
  }

  function receiptState(result, session) {
    settledSession.value = result
    if (!pendingReturn.value || pendingReturn.value.session_id === session.id) {
      data.value = { ...data.value, pending_return: {
        session_id: session.id, status: 'unviewed', todo_title: result.todo_title || null,
      } }
    }
    if (activeSession.value?.id === session.id) data.value = { ...data.value, active_session: null }
  }

  function clearRetry(id) {
    if (timers.has(id)) clearScheduledTimeout?.(timers.get(id))
    timers.delete(id)
  }

  function saveQueue(queue) {
    const savedQueue = JSON.parse(JSON.stringify(queue))
    return writeEnvelope(envelope => ({ cache: envelope.cache, queue: savedQueue }))
  }

  function scheduleRetry(item) {
    clearRetry(item.id)
    if (!active || !currentUserId || item.status === 'blocked' || !connectivity.isOnline() || !scheduleTimeout) return
    const epoch = identityEpoch
    timers.set(item.id, scheduleTimeout(() => {
      timers.delete(item.id)
      if (!active || epoch !== identityEpoch) return false
      if (pendingAction.value) { scheduleRetry({ ...item, nextAttemptAt: now() + 1000 }); return false }
      return retryPendingSettlements({ force: false })
    }, Math.max(0, item.nextAttemptAt - now())))
  }

  let retryPromise = null

  async function attemptSettlement(item) {
    const userId = currentUserId
    const epoch = identityEpoch
    clearRetry(item.id)
    let result
    try {
      result = await api.settleSession(item.session_id, { early: item.early, request_id: item.request_id })
    } catch (error) {
      if (!currentIdentity(userId, epoch)) return false
      const status = error?.response?.status || error?.status
      const blocked = status >= 400 && status < 500
      if (transportFailure(error)) offline.value = true
      const attempts = (item.attempts || 0) + 1
      const updated = { ...item, attempts, status: blocked ? 'blocked' : 'pending',
        error: typeof error?.response?.data?.detail === 'string' ? error.response.data.detail : blocked ? '收功暂未确认，请检查后再试。' : null,
        nextAttemptAt: blocked ? null : now() + Math.min(60_000, 1000 * 2 ** Math.min(attempts - 1, 6)) }
      try {
        if (!await saveQueue(pendingSettlements.value.map(entry => entry.id === item.id ? updated : entry))) return false
      } catch {
        if (!currentIdentity(userId, epoch)) return false
        pendingSettlements.value = pendingSettlements.value.map(entry => entry.id === item.id ? updated : entry)
        actionError.value = '本地待收功记录未能更新，请保持联网再试。'
      }
      scheduleRetry(updated)
      return { status: 'pending_settlement', id: item.id }
    }
    if (!currentIdentity(userId, epoch)) return false
    offline.value = false
    receiptState(result, item.session)
    try {
      if (!await persistCache(pendingSettlements.value.filter(entry => entry.id !== item.id))) return false
    } catch {
      if (!currentIdentity(userId, epoch)) return false
      actionError.value = '收功已确认，本地保存稍慢，请保持联网。'
      scheduleRetry({ ...item, status: 'pending', nextAttemptAt: now() + 1000 })
    }
    return result
  }

  function retryPendingSettlements({ includeBlocked = false, force = true } = {}) {
    if (retryPromise) return retryPromise
    if (!active || !currentUserId || !connectivity.isOnline() || pendingAction.value) return Promise.resolve(false)
    const epoch = identityEpoch
    sequence += 1
    loading.value = false
    pendingAction.value = 'retry-settle'
    retryPromise = (async () => {
      let result = false
      for (const item of [...pendingSettlements.value]) {
        if (!active || epoch !== identityEpoch) break
        if (item.status === 'blocked' && !includeBlocked) continue
        if (!force && item.nextAttemptAt && item.nextAttemptAt > now()) { scheduleRetry(item); continue }
        result = await attemptSettlement(item)
      }
      return result
    })().finally(() => {
      if (active && epoch === identityEpoch) {
        retryPromise = null
        pendingAction.value = null
      }
    })
    return retryPromise
  }

  async function durableSettlement(session, early) {
    const userId = currentUserId
    const epoch = identityEpoch
    await hydrate()
    if (!currentIdentity(userId, epoch)) return false
    let item = pendingSettlements.value.find(entry => entry.id === session.id)
    if (!item) {
      item = { id: session.id, session_id: session.id, early, request_id: newRequestId(),
        session: JSON.parse(JSON.stringify(session)), mark_todo_complete: session.mark_todo_complete === true,
        status: 'pending', error: null, attempts: 0, nextAttemptAt: null }
      try {
        if (!await saveQueue([...pendingSettlements.value, item])) return false
      } catch {
        actionError.value = '本地未能保存待收功，请保持联网并再试一次。'
        return false
      }
    }
    if (!connectivity.isOnline() || offline.value) return { status: 'pending_settlement', id: item.id }
    return attemptSettlement(item)
  }

  let settlementRequest = null

  async function settleSession({ early = false } = {}) {
    if (!active || pendingAction.value || !activeSession.value) return false
    if (!early && !canComplete.value) {
      actionError.value = '先安心坐一会儿，或选择提前结束。'
      return false
    }
    const session = activeSession.value
    sequence += 1
    loading.value = false
    const userId = currentUserId
    const epoch = identityEpoch
    pendingAction.value = 'settle'
    actionError.value = ''
    try {
      if (currentUserId) return await durableSettlement(session, early)
      const signature = `${session.id}:${early}`
      if (settlementRequest?.signature !== signature) settlementRequest = { signature, id: newRequestId() }
      const result = await api.settleSession(session.id, { early, request_id: settlementRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      settlementRequest = null
      settledSession.value = result
      if (!pendingReturn.value || pendingReturn.value.session_id === session.id) {
        data.value = { ...data.value, pending_return: {
          session_id: session.id, status: 'unviewed', todo_title: result.todo_title || null,
        } }
      }
      if (activeSession.value?.id === session.id) data.value = { ...data.value, active_session: null }
      return result
    } catch {
      if (currentIdentity(userId, epoch)) actionError.value = '收功的回音暂时未到，会话已留好，可以再试一次。'
      return false
    } finally {
      if (currentIdentity(userId, epoch)) pendingAction.value = null
    }
  }

  function recordReturnView(id) {
    if (!active || !api.recordEvent || (currentUserId && (offline.value || !connectivity.isOnline()))) return Promise.resolve(false)
    const userId = currentUserId
    const epoch = identityEpoch
    const event = { event: 'return_view', session_id: id, source: 'return_page', mode: mode.value,
      has_active_session: Boolean(activeSession.value), request_id: newRequestId() }
    return Promise.resolve().then(async () => {
      if (!currentIdentity(userId, epoch)) return false
      await api.recordEvent(event)
      return currentIdentity(userId, epoch)
    }).catch(() => false)
  }

  let acknowledgementRequest = null

  async function acknowledgeReturn(id) {
    if (!active || pendingAction.value || !onlineWrite()) return false
    const userId = currentUserId
    const epoch = identityEpoch
    pendingAction.value = 'acknowledge'
    actionError.value = ''
    if (acknowledgementRequest?.sessionId !== id) acknowledgementRequest = { sessionId: id, id: newRequestId() }
    try {
      await api.acknowledgeReturn(id, { request_id: acknowledgementRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      acknowledgementRequest = null
      if (pendingReturn.value?.session_id === id) data.value = { ...data.value, pending_return: null }
      await load({ internal: true })
      return currentIdentity(userId, epoch)
    } catch (error) {
      if (currentIdentity(userId, epoch)) {
        if (currentUserId && transportFailure(error)) offline.value = true
        actionError.value = '这段归来已留好，确认的回音稍慢，可以再试一次。'
      }
      return false
    } finally {
      if (currentIdentity(userId, epoch)) pendingAction.value = null
    }
  }

  let rerollRequest = null

  async function reroll() {
    if (!active || pendingAction.value || !data.value || rerollUsed.value || !onlineWrite()) return false
    const request = ++sequence
    const inboxRevision = letterRevision
    const guideRevision = onboardingRevision
    loading.value = false
    pendingAction.value = 'reroll'
    actionError.value = ''
    if (rerollRequest?.date !== data.value.date) rerollRequest = { date: data.value.date, id: newRequestId() }
    try {
      const result = await api.reroll({ date: rerollRequest.date, request_id: rerollRequest.id })
      if (!active || request !== sequence) return false
      data.value = { ...result,
        ...(inboxRevision !== letterRevision ? { unread_letters_count: panels.letters.value.value.unread_count } : {}),
        ...(guideRevision !== onboardingRevision ? { onboarding: onboarding.value } : {}) }
      rerollRequest = null
      if (currentUserId) {
        try { await persistCache() } catch {
          if (active && request === sequence) actionError.value = '换签已确认，本地保存稍慢。'
        }
      }
      return active && request === sequence
    } catch (error) {
      if (active && request === sequence) actionError.value = error?.response?.data?.detail || '换签的回音暂时未到，可以再试一次。'
      return false
    } finally {
      if (active && request === sequence) pendingAction.value = null
    }
  }

  let selectionRequest = null

  async function selectSign(taskId) {
    if (!active || pendingAction.value || !data.value || !onlineWrite()) return false
    const request = ++sequence
    const inboxRevision = letterRevision
    const guideRevision = onboardingRevision
    loading.value = false
    pendingAction.value = 'select'
    actionError.value = ''
    const signature = `${data.value.date}:${taskId}`
    if (selectionRequest?.signature !== signature) selectionRequest = { signature, id: newRequestId() }
    try {
      const result = await api.selectSign({ date: data.value.date, task_id: taskId, request_id: selectionRequest.id })
      if (!active || request !== sequence) return false
      data.value = { ...result,
        ...(inboxRevision !== letterRevision ? { unread_letters_count: panels.letters.value.value.unread_count } : {}),
        ...(guideRevision !== onboardingRevision ? { onboarding: onboarding.value } : {}) }
      selectionRequest = null
      if (currentUserId) {
        try { await persistCache() } catch {
          if (active && request === sequence) actionError.value = '自选已确认，本地保存稍慢。'
        }
      }
      return active && request === sequence
    } catch (error) {
      if (active && request === sequence) actionError.value = error?.response?.data?.detail || '选签的回音暂时未到，可以再试一次。'
      return false
    } finally {
      if (active && request === sequence) pendingAction.value = null
    }
  }

  const candidates = ref([])
  const candidatesLoading = ref(false)
  const candidatesError = ref('')
  let candidateSequence = 0

  async function loadCandidates() {
    if (!active) return false
    const request = ++candidateSequence
    candidatesLoading.value = true
    candidatesError.value = ''
    try {
      const tasks = await api.getCandidates()
      if (!active || request !== candidateSequence) return false
      candidates.value = tasks.filter(task => ['pending', 'in_progress'].includes(task.status))
      return true
    } catch {
      if (active && request === candidateSequence) candidatesError.value = '签筒暂时未送到，可以再试一次。'
      return false
    } finally {
      if (active && request === candidateSequence) candidatesLoading.value = false
    }
  }

  const draftTitle = ref('')
  let creationRequest = null

  async function createTask() {
    if (!active || pendingAction.value || !onlineWrite()) return false
    const title = draftTitle.value.trim()
    if (!title || title.length > 200) {
      actionError.value = '写下 1 至 200 字的一件小事就好。'
      return false
    }
    sequence += 1
    loading.value = false
    const userId = currentUserId
    const epoch = identityEpoch
    pendingAction.value = 'create'
    actionError.value = ''
    if (creationRequest?.title !== title) creationRequest = { title, id: newRequestId() }
    try {
      await api.createQuickTask({ title, schedule: 'today', request_id: creationRequest.id })
      if (!currentIdentity(userId, epoch)) return false
      creationRequest = null
      draftTitle.value = ''
      await load({ internal: true })
      return currentIdentity(userId, epoch)
    } catch (error) {
      if (currentIdentity(userId, epoch)) {
        if (currentUserId && transportFailure(error)) offline.value = true
        actionError.value = '这件事的回音暂时未到，文字已留好，可以再试一次。'
      }
      return false
    } finally {
      if (currentIdentity(userId, epoch)) pendingAction.value = null
    }
  }

  const greeting = computed(() => ({
    morning: '晨雾未散，先把眼前这一件事做起来。',
    day: '山间正明亮，留一段时间给眼前的事。',
    dusk: '把白日轻轻放下，从这一件小事开始。',
    night: '灯已点好，今晚也给自己留一点时间。',
  })[mode.value])
  const ctaLabel = computed(() => ({ morning: '迎晨入定', day: '静心入定', dusk: '伴暮入定', night: '灯下入定' })[mode.value])
  let opened = false

  async function load({ source = 'direct', recordOpen = false, internal = false } = {}) {
    if (!active || (pendingAction.value && !internal)) return false
    const userId = currentUserId
    const epoch = identityEpoch
    if (currentUserId) {
      await hydrate()
      if (!currentIdentity(userId, epoch) || (pendingAction.value && !internal)) return false
      if (!connectivity.isOnline()) {
        offline.value = true
        return Boolean(data.value)
      }
    }
    const request = ++sequence
    loading.value = true
    loadError.value = ''
    try {
      const previousDefault = defaultDuration.value
      const revision = companionRevision
      const inboxRevision = letterRevision
      const guideRevision = onboardingRevision
      let snapshot = await api.getCave()
      if (!active || request !== sequence) return false
      if (revision !== companionRevision) snapshot = { ...snapshot, companions: panels.companions.value.value,
        daily_note: panels.companions.value.value.daily_note }
      if (inboxRevision !== letterRevision) snapshot = { ...snapshot, unread_letters_count: panels.letters.value.value.unread_count }
      if (guideRevision !== onboardingRevision) snapshot = { ...snapshot, onboarding: onboarding.value }
      data.value = snapshot
      cacheDate.value = snapshot.date || null
      staleCache.value = false
      offline.value = false
      if (data.value.server_now) serverOffset.value = Date.parse(data.value.server_now) - now()
      if (selectedDuration.value === previousDefault) selectedDuration.value = defaultDuration.value
      if (currentUserId) {
        try { await persistCache() } catch {
          if (currentIdentity(userId, epoch) && request === sequence) loadError.value = '洞府已送达，本地保存稍慢，离线时可能无法查看。'
        }
      }
      if (!currentIdentity(userId, epoch) || request !== sequence) return false
      if ((!opened || recordOpen) && api.recordEvent) {
        opened = true
        const event = { event: 'cave_open', source, mode: mode.value,
          has_active_session: Boolean(activeSession.value), request_id: newRequestId() }
        Promise.resolve().then(() => currentIdentity(userId, epoch) ? api.recordEvent(event) : false).catch(() => {})
      }
      return true
    } catch (error) {
      if (!active || request !== sequence || !currentIdentity(userId, epoch)) return false
      if (currentUserId && transportFailure(error)) {
        offline.value = true
        if (cachedEnvelope?.cache) return visibleCache(cachedEnvelope.cache)
      }
      if ([401, 403].includes(error?.response?.status || error?.status)) {
        data.value = null
        settledSession.value = null
        offline.value = false
      }
      loadError.value = data.value ? '山中来信稍慢，先留住眼前的景色。可以再试一次。' : '山路有些远，洞府暂时未能连上。请再试一次。'
      return false
    } finally {
      if (active && request === sequence) loading.value = false
    }
  }

  let rolloverDate = null

  function tick() {
    if (!active) return
    const previousDefault = defaultDuration.value
    currentTime.value = now()
    if (selectedDuration.value === previousDefault) selectedDuration.value = defaultDuration.value
    const previousDate = data.value?.date
    maskStaleDaily()
    const today = chinaDateKey(currentTime.value + serverOffset.value)
    if (previousDate && previousDate !== today && rolloverDate !== today && !pendingAction.value && !loading.value) {
      rolloverDate = today
      return load()
    }
  }
  function dispose() {
    active = false
    unsubscribeConnectivity?.()
    timers.forEach(timer => clearScheduledTimeout?.(timer))
    timers.clear()
  }

  offline.value = currentUserId ? !connectivity.isOnline() : false
  unsubscribeConnectivity = connectivity.subscribe(async online => {
    if (!active || !currentUserId) return
    const userId = currentUserId
    const epoch = identityEpoch
    offline.value = !online
    if (online) {
      await hydrate()
      if (!currentIdentity(userId, epoch)) return
      await retryPendingSettlements()
      if (currentIdentity(userId, epoch)) await load()
    }
  })

  return { data, onboarding, onboardingPending, onboardingError, skipOnboarding, completeOnboarding,
    offline, cacheDate, staleCache, pendingSettlements, setUser, retryPendingSettlements,
    mode, defaultDuration, selectedDuration, loading, loadError, primarySign,
    growth: panels.growth.value, growthLoading: panels.growth.loading, growthError: panels.growth.error,
    codex: panels.codex.value, codexLoading: panels.codex.loading, codexError: panels.codex.error,
    companions: panels.companions.value, companionsLoading: panels.companions.loading, companionsError: panels.companions.error,
    letters: panels.letters.value, lettersLoading: panels.letters.loading, lettersError: panels.letters.error,
    letter: panels.letter.value, letterLoading: panels.letter.loading, letterError: panels.letter.error,
    loadLetters, loadLetter, readLetter, acceptLetter, declineLetter, claimLetter, letterPending, loadGrowth, loadCodex, loadCompanions, companionPending, activateCompanion,
    activeSession, getServerNow, remainingSeconds, canComplete, loadSession, settleSession, pendingReturn, acknowledgeReturn, recordReturnView, preparingSession, sessionTask, markTodoComplete, settledSession, prepareSession,
    actionError, pendingAction, draftTitle, greeting, ctaLabel,
    signs, rerollUsed, reroll, selectSign, candidates, candidatesLoading, candidatesError, loadCandidates, startSession, createTask, load, tick, dispose }
}
