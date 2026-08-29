import * as Y from 'yjs'
import { computed, ref } from 'vue'
import { noteService } from '../services/note'
import { resolveWebSocketUrl } from '../services/api'

function encodeUpdate(update) {
  let binary = ''
  const bytes = update instanceof Uint8Array ? update : new Uint8Array(update)
  for (let index = 0; index < bytes.length; index += 1) binary += String.fromCharCode(bytes[index])
  return btoa(binary)
}

function decodeUpdate(value) {
  const binary = atob(value)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  return bytes
}

export function useNoteCollaboration() {
  const content = ref('')
  const status = ref('idle')
  const error = ref(null)
  const peers = ref([])
  const serverRevision = ref(1)
  const connected = computed(() => status.value === 'connected')
  const syncing = ref(false)

  let socket = null
  let doc = null
  let text = null
  let noteId = null
  let updateBuffer = []
  let updateTimer = null
  let snapshotTimer = null
  let heartbeatTimer = null
  let flushPromise = null
  let resolveFlush = null
  let rejectFlush = null
  let pendingAcks = 0
  let lastCursor = 0
  let localChange = false

  function setContentFromDocument() {
    if (!text) return
    content.value = text.toString()
  }

  function settleFlushIfIdle() {
    if (!resolveFlush || pendingAcks > 0 || updateBuffer.length > 0) return
    resolveFlush()
    flushPromise = null
    resolveFlush = null
    rejectFlush = null
  }

  function rejectPendingFlush(error) {
    if (rejectFlush) rejectFlush(error)
    flushPromise = null
    resolveFlush = null
    rejectFlush = null
    pendingAcks = 0
  }

  function flushUpdates() {
    if (!updateBuffer.length) {
      settleFlushIfIdle()
      return
    }
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      rejectPendingFlush(new Error('COLLAB_NOT_CONNECTED'))
      return
    }
    const update = Y.mergeUpdates(updateBuffer)
    updateBuffer = []
    pendingAcks += 1
    try {
      socket.send(JSON.stringify({
        type: 'update',
        update: encodeUpdate(update),
        content: content.value,
      }))
    } catch (error) {
      pendingAcks = Math.max(0, pendingAcks - 1)
      rejectPendingFlush(error)
    }
  }

  function queueUpdate(update) {
    updateBuffer.push(update)
    if (updateTimer) return
    updateTimer = setTimeout(() => {
      updateTimer = null
      flushUpdates()
    }, 100)
  }

  function handleDocumentUpdate(update, origin) {
    setContentFromDocument()
    if (origin === 'remote' || origin === 'bootstrap') return
    localChange = true
    queueUpdate(update)
  }

  function createDocument() {
    doc = new Y.Doc()
    text = doc.getText('markdown')
    doc.on('update', handleDocumentUpdate)
  }

  function initializeDocument(initialContent) {
    createDocument()
    doc.transact(() => text.insert(0, initialContent || ''), 'bootstrap')
    setContentFromDocument()
  }

  function applySync(message) {
    createDocument()
    Y.applyUpdate(doc, decodeUpdate(message.snapshot), 'remote')
    for (const update of message.updates || []) {
      Y.applyUpdate(doc, decodeUpdate(update.update), 'remote')
      lastCursor = Math.max(lastCursor, Number(update.cursor) || 0)
    }
    lastCursor = Math.max(lastCursor, Number(message.snapshot_cursor) || 0)
    setContentFromDocument()
    serverRevision.value = message.revision || 1
    status.value = 'connected'
    syncing.value = false
  }

  function sendSnapshot() {
    if (!socket || socket.readyState !== WebSocket.OPEN || !doc) return
    socket.send(JSON.stringify({
      type: 'snapshot',
      snapshot: encodeUpdate(Y.encodeStateAsUpdate(doc)),
      content: content.value,
      cursor: lastCursor,
    }))
  }

  function handleMessage(event) {
    const message = JSON.parse(event.data)
    if (message.type === 'init') {
      initializeDocument(message.content || '')
      serverRevision.value = message.revision || 1
      status.value = 'connected'
      syncing.value = false
      sendSnapshot()
      return
    }
    if (message.type === 'sync') {
      applySync(message)
      return
    }
    if (message.type === 'waiting') {
      status.value = 'syncing'
      syncing.value = true
      return
    }
    if (message.type === 'update') {
      if (doc) {
        Y.applyUpdate(doc, decodeUpdate(message.update), 'remote')
        lastCursor = Math.max(lastCursor, Number(message.cursor) || 0)
      }
      serverRevision.value = Math.max(serverRevision.value, Number(message.revision) || serverRevision.value)
      return
    }
    if (message.type === 'ack') {
      lastCursor = Math.max(lastCursor, Number(message.cursor) || 0)
      serverRevision.value = message.revision || serverRevision.value
      localChange = false
      pendingAcks = Math.max(0, pendingAcks - 1)
      settleFlushIfIdle()
      return
    }
    if (message.type === 'snapshot-ack') {
      serverRevision.value = Math.max(serverRevision.value, Number(message.revision) || serverRevision.value)
      return
    }
    if (message.type === 'presence') {
      peers.value = message.users || []
      return
    }
    if (message.type === 'error') {
      error.value = message.code || 'COLLAB_ERROR'
      if (message.code === 'READ_ONLY') status.value = 'readonly'
      rejectPendingFlush(new Error(message.code || 'COLLAB_ERROR'))
    }
  }

  async function connect(nextNoteId, initialContent = '') {
    disconnect()
    noteId = nextNoteId
    status.value = 'connecting'
    error.value = null
    try {
      const { ticket } = await noteService.getCollaborationTicket(nextNoteId)
      if (noteId !== nextNoteId) return
      const nextSocket = new WebSocket(resolveWebSocketUrl(`/api/notes/${nextNoteId}/collab?ticket=${encodeURIComponent(ticket)}`))
      socket = nextSocket
      nextSocket.onopen = () => {
        if (socket !== nextSocket) return
        status.value = 'syncing'
        if (heartbeatTimer) clearInterval(heartbeatTimer)
        heartbeatTimer = setInterval(() => {
          if (socket !== nextSocket || nextSocket.readyState !== WebSocket.OPEN) return
          nextSocket.send(JSON.stringify({ type: 'ping' }))
        }, 20000)
      }
      nextSocket.onmessage = (event) => {
        if (socket === nextSocket) handleMessage(event)
      }
      nextSocket.onerror = () => {
        if (socket !== nextSocket) return
        error.value = 'COLLAB_CONNECTION_FAILED'
        status.value = 'error'
        rejectPendingFlush(new Error('COLLAB_CONNECTION_FAILED'))
      }
      nextSocket.onclose = () => {
        if (socket !== nextSocket) return
        if (heartbeatTimer) clearInterval(heartbeatTimer)
        heartbeatTimer = null
        if (noteId === nextNoteId && status.value !== 'idle') status.value = 'disconnected'
        rejectPendingFlush(new Error('COLLAB_CONNECTION_CLOSED'))
      }
      content.value = initialContent || ''
    } catch (cause) {
      if (noteId !== nextNoteId) return
      error.value = cause
      status.value = 'error'
    }
  }

  function setLocalContent(nextContent) {
    if (!text || syncing.value || nextContent === text.toString()) return
    const current = text.toString()
    let prefix = 0
    while (prefix < current.length && prefix < nextContent.length && current[prefix] === nextContent[prefix]) prefix += 1
    let suffix = 0
    while (
      suffix < current.length - prefix &&
      suffix < nextContent.length - prefix &&
      current[current.length - suffix - 1] === nextContent[nextContent.length - suffix - 1]
    ) suffix += 1
    doc.transact(() => {
      if (current.length - prefix - suffix > 0) text.delete(prefix, current.length - prefix - suffix)
      if (nextContent.length - prefix - suffix > 0) text.insert(prefix, nextContent.slice(prefix, nextContent.length - suffix))
    }, 'local')
  }

  function flush() {
    if (updateTimer) {
      clearTimeout(updateTimer)
      updateTimer = null
    }
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      if (updateBuffer.length || pendingAcks > 0) return Promise.reject(new Error('COLLAB_NOT_CONNECTED'))
      return Promise.resolve()
    }
    if (!flushPromise) {
      flushPromise = new Promise((resolve, reject) => {
        resolveFlush = resolve
        rejectFlush = reject
      })
    }
    const pendingFlush = flushPromise
    flushUpdates()
    settleFlushIfIdle()
    return pendingFlush || Promise.resolve()
  }

  function disconnect() {
    if (updateTimer) clearTimeout(updateTimer)
    if (snapshotTimer) clearInterval(snapshotTimer)
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    updateTimer = null
    snapshotTimer = null
    heartbeatTimer = null
    updateBuffer = []
    localChange = false
    rejectPendingFlush(new Error('COLLAB_DISCONNECTED'))
    if (socket) socket.close()
    socket = null
    if (doc) doc.destroy()
    doc = null
    text = null
    noteId = null
    peers.value = []
    status.value = 'idle'
    syncing.value = false
  }

  function startSnapshotTimer() {
    if (snapshotTimer) clearInterval(snapshotTimer)
    snapshotTimer = setInterval(() => {
      flushUpdates()
      sendSnapshot()
    }, 5000)
  }

  function isReady() {
    return connected.value && !!doc && socket?.readyState === WebSocket.OPEN
  }

  return {
    content,
    status,
    error,
    peers,
    serverRevision,
    connected,
    isReady,
    connect,
    disconnect,
    setLocalContent,
    flush,
    startSnapshotTimer,
  }
}

export default useNoteCollaboration
