import { ref, toValue } from 'vue'
import { noteService } from '../services/note'

function getId(value) {
  if (value && typeof value === 'object') return value.id
  return value
}

function getParentId(value) {
  if (value && typeof value === 'object') return value.parentId ?? value.parent_id ?? null
  return value ?? null
}

function nodeIdEquals(left, right) {
  return left != null && right != null && String(left) === String(right)
}

function collectNodes(nodes, result = new Map()) {
  for (const node of nodes || []) {
    result.set(String(node.id), node)
    collectNodes(node.children, result)
  }
  return result
}

function collectFolderIds(nodes, result = new Set()) {
  for (const node of nodes || []) {
    if (node.type === 'folder') {
      result.add(node.id)
      collectFolderIds(node.children, result)
    }
  }
  return result
}

function nodeIsInside(nodes, ancestorId, targetId) {
  for (const node of nodes || []) {
    if (nodeIdEquals(node.id, ancestorId)) {
      return collectNodes(node.children).has(String(targetId)) || nodeIdEquals(node.id, targetId)
    }
    if (nodeIsInside(node.children, ancestorId, targetId)) return true
  }
  return false
}

export function useNoteWorkspace(notebookId) {
  const tree = ref([])
  const selectedNoteId = ref(null)
  const currentFolderId = ref(null)
  const expandedIds = ref(new Set())
  const loading = ref(false)
  const error = ref(null)
  const actionLocks = ref(new Set())

  function resolveNotebookId(value = notebookId) {
    return toValue(value)
  }

  function setExpanded(id, expanded) {
    if (id == null) return
    const next = new Set(expandedIds.value)
    if (expanded) next.add(id)
    else next.delete(id)
    expandedIds.value = next
  }

  function findNode(nodeId) {
    return collectNodes(tree.value).get(String(nodeId)) || null
  }

  function expandAncestors(node) {
    let parentId = node?.parent_id ?? node?.parentId
    while (parentId != null) {
      setExpanded(parentId, true)
      const parent = findNode(parentId)
      parentId = parent?.parent_id ?? parent?.parentId ?? null
    }
  }

  function reconcileTree(nextTree, { preserveExpansion = true } = {}) {
    const previousExpanded = expandedIds.value
    tree.value = Array.isArray(nextTree) ? nextTree : (nextTree?.children || [])

    const folderIds = collectFolderIds(tree.value)
    if (!preserveExpansion || previousExpanded.size === 0) {
      expandedIds.value = folderIds
    } else {
      expandedIds.value = new Set(
        [...previousExpanded].filter((id) => [...folderIds].some((folderId) => nodeIdEquals(folderId, id)))
      )
    }

    if (selectedNoteId.value && !findNode(selectedNoteId.value)) {
      selectedNoteId.value = null
    }
    if (currentFolderId.value && !findNode(currentFolderId.value)) {
      currentFolderId.value = null
    }
  }

  async function loadTree(options = {}) {
    const targetNotebookId = resolveNotebookId(options.notebookId ?? notebookId)
    if (targetNotebookId == null) return []

    loading.value = true
    error.value = null
    try {
      const nextTree = await noteService.getTree(targetNotebookId)
      reconcileTree(nextTree, options)
      return tree.value
    } catch (cause) {
      error.value = cause
      throw cause
    } finally {
      loading.value = false
    }
  }

  function toggleFolder(nodeOrId) {
    const id = getId(nodeOrId)
    setExpanded(id, !expandedIds.value.has(id) && !expandedIds.value.has(String(id)))
  }

  function selectNote(nodeOrId) {
    const node = typeof nodeOrId === 'object' ? nodeOrId : findNode(nodeOrId)
    if (!node) return null

    if (node.type === 'folder') {
      selectedNoteId.value = null
      currentFolderId.value = node.id
      expandAncestors(node)
    } else {
      selectedNoteId.value = node.id
      currentFolderId.value = node.parent_id ?? node.parentId ?? null
      expandAncestors(node)
    }
    return node
  }

  async function runMutation(operation, { selectResult = false, action = 'mutation' } = {}) {
    if (actionLocks.value.has(action)) {
      const cause = new Error('NOTE_ACTION_IN_PROGRESS')
      error.value = cause
      throw cause
    }
    actionLocks.value = new Set([...actionLocks.value, action])
    error.value = null
    try {
      const result = await operation()
      await loadTree()
      if (selectResult && result?.id != null) selectNote(result.id)
      return result
    } catch (cause) {
      error.value = cause
      throw cause
    } finally {
      const next = new Set(actionLocks.value)
      next.delete(action)
      actionLocks.value = next
    }
  }

  async function createFolder(nameOrOptions, parentId = currentFolderId.value) {
    const options = typeof nameOrOptions === 'object' ? nameOrOptions : { name: nameOrOptions, parentId }
    const targetParentId = getParentId(options)
    const name = String(options.name ?? '').trim()
    if (!name) throw new Error('Folder name is required')

    const result = await runMutation(() => noteService.createFolder(resolveNotebookId(), {
      name,
      parent_id: targetParentId,
    }), { action: 'create-folder' })
    if (targetParentId != null) setExpanded(targetParentId, true)
    currentFolderId.value = targetParentId
    return result
  }

  async function createNote(titleOrOptions, parentId = currentFolderId.value) {
    const options = typeof titleOrOptions === 'object' ? titleOrOptions : { title: titleOrOptions, parentId }
    const targetParentId = getParentId(options)
    const title = String(options.title ?? options.name ?? '').trim()
    if (!title) throw new Error('Note title is required')

    const payload = {
      title,
      parent_id: targetParentId,
    }
    for (const key of ['content', 'summary', 'tags']) {
      if (options[key] !== undefined) payload[key] = options[key]
    }

    const result = await runMutation(() => noteService.createNote(resolveNotebookId(), payload), { selectResult: true, action: 'create-note' })
    if (targetParentId != null) setExpanded(targetParentId, true)
    currentFolderId.value = targetParentId
    return result
  }

  async function renameNode(nodeOrId, name) {
    const nodeId = getId(nodeOrId)
    const nextName = String(name ?? '').trim()
    if (nodeId == null || !nextName) throw new Error('Node id and name are required')
    return runMutation(() => noteService.renameNode(nodeId, nextName), { action: 'rename' })
  }

  async function moveNode(nodeOrId, parentId = null) {
    const nodeId = getId(nodeOrId)
    const targetParentId = getParentId(parentId)
    if (nodeId == null) throw new Error('Node id is required')
    if (nodeIdEquals(nodeId, targetParentId) || nodeIsInside(tree.value, nodeId, targetParentId)) {
      throw new Error('A node cannot be moved inside itself')
    }

    const result = await runMutation(() => noteService.moveNode(nodeId, targetParentId), { action: 'move' })
    if (nodeIdEquals(selectedNoteId.value, nodeId)) currentFolderId.value = targetParentId
    if (targetParentId != null) setExpanded(targetParentId, true)
    return result
  }

  async function deleteNode(nodeOrId) {
    const nodeId = getId(nodeOrId)
    if (nodeId == null) throw new Error('Node id is required')

    const deletesSelection = nodeIdEquals(selectedNoteId.value, nodeId) || nodeIsInside(tree.value, nodeId, selectedNoteId.value)
    const deletesFolder = nodeIdEquals(currentFolderId.value, nodeId) || nodeIsInside(tree.value, nodeId, currentFolderId.value)
    const result = await runMutation(() => noteService.deleteNode(nodeId), { action: 'delete' })
    if (deletesSelection) selectedNoteId.value = null
    if (deletesFolder) currentFolderId.value = null
    expandedIds.value = new Set([...expandedIds.value].filter((id) => !nodeIdEquals(id, nodeId)))
    return result
  }

  return {
    tree,
    selectedNoteId,
    currentFolderId,
    expandedIds,
    loading,
    error,
    actionLocks,
    loadTree,
    selectNote,
    toggleFolder,
    createFolder,
    createNote,
    renameNode,
    moveNode,
    deleteNode,
  }
}

export default useNoteWorkspace
