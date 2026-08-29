<template>
  <div v-if="!nested" class="note-tree">
    <div v-if="showToolbar && !readOnly" class="note-tree__toolbar" aria-label="笔记操作">
      <button
        type="button"
        class="note-tree__toolbar-button"
        @click="controller.emit('create-folder', { parentId: currentFolderId || null })"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          <path d="M12 11v6M9 14h6" />
        </svg>
        <span>新建文件夹</span>
      </button>
      <button
        type="button"
        class="note-tree__toolbar-button note-tree__toolbar-button--primary"
        @click="controller.emit('create-note', { parentId: currentFolderId || null })"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6M12 11v6M9 14h6" />
        </svg>
        <span>新建笔记</span>
      </button>
    </div>
  </div>

  <ul
    :role="nested ? 'group' : 'tree'"
    :aria-label="nested ? undefined : label"
    class="note-tree__list"
  >
    <li
      v-for="(node, index) in nodes"
      :key="node.id"
      role="treeitem"
      class="note-tree__item"
      :class="{ 'note-tree__item--selected': isSelected(node) }"
      :aria-level="level"
      :aria-posinset="index + 1"
      :aria-setsize="nodes.length"
      :aria-expanded="isFolder(node) ? isExpanded(node) : undefined"
      :aria-selected="isSelected(node)"
    >
      <div class="note-tree__row">
        <button
          type="button"
          class="note-tree__label"
          :class="{ 'note-tree__label--focused': controller.focusedId.value === node.id }"
          :data-note-tree-id="node.id"
          :tabindex="controller.focusedId.value === node.id ? 0 : -1"
          @focus="controller.setFocus(node.id)"
          @click="controller.emit('select', node)"
          @keydown="controller.handleKeydown($event, node)"
        >
          <span
            class="note-tree__disclosure"
            :class="{ 'note-tree__disclosure--open': isExpanded(node) }"
            :aria-hidden="!isFolder(node)"
            @click.stop="isFolder(node) && controller.emit('toggle', node.id)"
          >
            <svg v-if="isFolder(node)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </span>
          <svg v-if="isFolder(node)" class="note-tree__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <svg v-else class="note-tree__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6" />
          </svg>
          <span class="note-tree__name">{{ node.name }}</span>
        </button>

        <div v-if="!readOnly" class="note-tree__actions" aria-label="节点操作">
          <button
            v-if="isFolder(node)"
            type="button"
            class="note-tree__action"
            aria-label="在此文件夹中新建文件夹"
            title="新建文件夹"
            @click.stop="controller.emit('create-folder', { parentId: node.id, node })"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              <path d="M12 11v6M9 14h6" />
            </svg>
          </button>
          <button
            v-if="isFolder(node)"
            type="button"
            class="note-tree__action"
            aria-label="在此文件夹中新建笔记"
            title="新建笔记"
            @click.stop="controller.emit('create-note', { parentId: node.id, node })"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6M12 11v6M9 14h6" />
            </svg>
          </button>
          <button
            type="button"
            class="note-tree__action"
            aria-label="重命名"
            title="重命名"
            @click.stop="controller.emit('rename', node)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" />
            </svg>
          </button>
          <button
            type="button"
            class="note-tree__action"
            aria-label="移动"
            title="移动"
            @click.stop="controller.emit('move', node)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
          <button
            type="button"
            class="note-tree__action note-tree__action--danger"
            aria-label="删除"
            title="删除"
            @click.stop="controller.emit('delete', node)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 10v7M14 10v7" />
            </svg>
          </button>
        </div>
        <button
          v-if="!readOnly"
          type="button"
          class="note-tree__mobile-trigger"
          aria-label="打开节点操作"
          :aria-expanded="mobileMenuOpen"
          @click.stop="mobileMenuOpen = !mobileMenuOpen"
        >
          <span aria-hidden="true">•••</span>
        </button>
        <div v-if="!readOnly && mobileMenuOpen" class="note-tree__mobile-menu" role="menu" aria-label="节点操作">
          <button v-if="isFolder(node)" type="button" role="menuitem" @click.stop="emitMobile('create-folder', { parentId: node.id, node })">新建文件夹</button>
          <button v-if="isFolder(node)" type="button" role="menuitem" @click.stop="emitMobile('create-note', { parentId: node.id, node })">新建笔记</button>
          <button type="button" role="menuitem" @click.stop="emitMobile('rename', node)">重命名</button>
          <button type="button" role="menuitem" @click.stop="emitMobile('move', node)">移动</button>
          <button type="button" role="menuitem" @click.stop="emitMobile('delete', node)">删除</button>
        </div>
      </div>

      <NoteTree
        v-if="isFolder(node) && isExpanded(node) && node.children?.length"
        :nodes="node.children"
        :selected-id="selectedId"
        :current-folder-id="currentFolderId"
        :expanded-ids="expandedIds"
        :level="level + 1"
        :nested="true"
        :show-toolbar="false"
        :read-only="readOnly"
      />
    </li>
    <li v-if="!nodes.length" class="note-tree__empty" role="none">{{ emptyLabel }}</li>
  </ul>
</template>

<script setup>
import { computed, inject, nextTick, provide, ref, watch } from 'vue'

defineOptions({ name: 'NoteTree' })

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  selectedId: { type: [String, Number], default: null },
  currentFolderId: { type: [String, Number], default: null },
  expandedIds: { type: Object, default: () => new Set() },
  label: { type: String, default: '笔记目录' },
  emptyLabel: { type: String, default: '暂无笔记' },
  level: { type: Number, default: 1 },
  nested: { type: Boolean, default: false },
  showToolbar: { type: Boolean, default: true },
  readOnly: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'toggle', 'create-folder', 'create-note', 'rename', 'move', 'delete'])
const treeControllerKey = 'note-tree-controller'
const parentController = inject(treeControllerKey, null)
const mobileMenuOpen = ref(false)

function flattenVisible(nodes, expanded, parentId = null, level = 1, result = []) {
  for (const node of nodes || []) {
    result.push({ node, parentId, level })
    if (node.type === 'folder' && expanded.has(node.id)) {
      flattenVisible(node.children, expanded, node.id, level + 1, result)
    }
  }
  return result
}

function createController() {
  const focusedId = ref(null)
  const visibleNodes = computed(() => flattenVisible(props.nodes, props.expandedIds))

  function setFocus(id) {
    focusedId.value = id
  }

  function focusNode(id) {
    if (!id) return
    focusedId.value = id
    nextTick(() => {
      const element = [...document.querySelectorAll('[data-note-tree-id]')]
        .find((candidate) => candidate.dataset.noteTreeId === String(id))
      element?.focus()
    })
  }

  function emitEvent(eventName, payload) {
    emit(eventName, payload)
  }

  function handleKeydown(event, node) {
    const current = visibleNodes.value.findIndex((entry) => String(entry.node.id) === String(node.id))
    const entry = visibleNodes.value[current]
    if (current < 0 || !entry) return

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      emitEvent('select', node)
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const nextIndex = event.key === 'ArrowDown' ? current + 1 : current - 1
      const next = visibleNodes.value[nextIndex]
      if (next) focusNode(next.node.id)
      return
    }

    if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault()
      const target = event.key === 'Home' ? visibleNodes.value[0] : visibleNodes.value.at(-1)
      if (target) focusNode(target.node.id)
      return
    }

    if (event.key === 'ArrowRight' && node.type === 'folder') {
      event.preventDefault()
      if (!props.expandedIds.has(node.id)) {
        emitEvent('toggle', node.id)
      } else if (node.children?.length) {
        focusNode(node.children[0].id)
      }
      return
    }

    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      if (node.type === 'folder' && props.expandedIds.has(node.id)) {
        emitEvent('toggle', node.id)
      } else if (entry.parentId) {
        focusNode(entry.parentId)
      }
    }
  }

  watch(visibleNodes, (entries) => {
    if (!entries.length) {
      focusedId.value = null
    } else if (!entries.some((entry) => String(entry.node.id) === String(focusedId.value))) {
      focusedId.value = entries[0].node.id
    }
  }, { immediate: true })

  return { focusedId, emit: emitEvent, setFocus, focusNode, handleKeydown }
}

const controller = parentController || createController()
if (!parentController) provide(treeControllerKey, controller)

function isFolder(node) {
  return node.type === 'folder'
}

function isExpanded(node) {
  return isFolder(node) && props.expandedIds.has(node.id)
}

function isSelected(node) {
  return String(node.id) === String(props.selectedId)
}

function emitMobile(eventName, payload) {
  mobileMenuOpen.value = false
  controller.emit(eventName, payload)
}
</script>

<style scoped>
.note-tree {
  min-width: 0;
}

.note-tree__toolbar {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-bottom: 1px solid var(--color-border);
}

.note-tree__toolbar-button,
.note-tree__action,
.note-tree__disclosure {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  border: 0;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  background: transparent;
  cursor: pointer;
  font-family: var(--font-family);
}

.note-tree__toolbar-button {
  flex: 1;
  gap: 6px;
  padding: 6px 10px;
  font-size: var(--font-size-sm);
  text-align: left;
}

.note-tree__toolbar-button:hover,
.note-tree__toolbar-button:focus-visible,
.note-tree__action:hover,
.note-tree__action:focus-visible {
  color: var(--color-primary);
  background: var(--color-bg-tertiary);
  outline: none;
}

.note-tree__toolbar-button--primary {
  color: var(--color-primary);
}

.note-tree__toolbar-button svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.note-tree__list {
  list-style: none;
  padding: 6px;
  margin: 0;
}

.note-tree__list[role='group'] {
  padding: 0 0 0 20px;
}

.note-tree__item {
  min-width: 0;
  margin: 2px 0;
}

.note-tree__row {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: 44px;
  border-radius: var(--radius-md);
}

.note-tree__item--selected > .note-tree__row {
  background: rgba(14, 165, 233, 0.1);
}

.note-tree__label {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  min-height: 44px;
  gap: 5px;
  padding: 0 4px;
  border: 0;
  border-radius: var(--radius-md);
  color: var(--color-text);
  background: transparent;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.note-tree__label:hover,
.note-tree__label--focused {
  background: var(--color-bg-tertiary);
}

.note-tree__label:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.note-tree__disclosure {
  width: 44px;
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.note-tree__disclosure svg {
  width: 16px;
  height: 16px;
  transition: transform 0.15s ease;
}

.note-tree__disclosure--open svg {
  transform: rotate(90deg);
}

.note-tree__icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--color-primary);
}

.note-tree__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.note-tree__actions {
  display: flex;
  flex: 0 0 auto;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.note-tree__row { position: relative; }
.note-tree__mobile-trigger,
.note-tree__mobile-menu { display: none; }

.note-tree__row:hover .note-tree__actions,
.note-tree__row:focus-within .note-tree__actions {
  opacity: 1;
}

.note-tree__action {
  width: 44px;
  padding: 0;
}

.note-tree__action svg {
  width: 17px;
  height: 17px;
}

.note-tree__action--danger:hover,
.note-tree__action--danger:focus-visible {
  color: var(--color-error);
}

.note-tree__empty {
  padding: 16px 12px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  text-align: center;
}

@media (max-width: 767px) {
  .note-tree__actions {
    display: none;
  }

  .note-tree__mobile-trigger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    min-height: 44px;
    border: 0;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--color-text-secondary);
    cursor: pointer;
    font: inherit;
  }

  .note-tree__mobile-menu {
    position: absolute;
    right: 8px;
    top: calc(100% - 4px);
    z-index: 5;
    display: grid;
    min-width: 150px;
    padding: 4px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-card);
    box-shadow: var(--shadow-md);
  }

  .note-tree__mobile-menu button {
    min-height: 40px;
    padding: 8px 12px;
    border: 0;
    background: transparent;
    color: var(--color-text);
    text-align: left;
    cursor: pointer;
    font: inherit;
  }

  .note-tree__mobile-menu button:hover,
  .note-tree__mobile-menu button:focus-visible {
    background: var(--color-bg-secondary);
  }
}

</style>
