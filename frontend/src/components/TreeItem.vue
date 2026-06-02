<!-- frontend/src/components/TreeItem.vue -->
<template>
  <div class="tree-node" :class="{ 'tree-node--active': node.id === currentId }">
    <button class="tree-node-btn" @click="$emit('navigate', node.id)">
      <svg v-if="node.type === 'folder'" class="tree-node-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
      <svg v-else class="tree-node-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
      <span class="tree-node-name">{{ node.name }}</span>
    </button>
    <ul v-if="node.children?.length" class="tree-children">
      <li v-for="child in node.children" :key="child.id">
        <TreeItem :node="child" :current-id="currentId" @navigate="$emit('navigate', $event)" />
      </li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  node: { type: Object, required: true },
  currentId: { type: String, default: null },
})
defineEmits(['navigate'])
</script>

<style scoped>
.tree-node { margin-bottom: 2px; }
.tree-node-btn { display: flex; align-items: center; gap: var(--spacing-xs); width: 100%; padding: 6px 8px; background: transparent; border: none; border-radius: var(--radius-md); cursor: pointer; color: var(--color-text); font-size: var(--font-size-sm); font-family: var(--font-family); text-align: left; transition: background 0.15s; }
.tree-node-btn:hover { background: var(--color-bg-tertiary); }
.tree-node--active > .tree-node-btn { background: rgba(108, 99, 255, 0.1); color: var(--color-primary); font-weight: 600; }
.tree-node-icon { width: 16px; height: 16px; flex-shrink: 0; }
.tree-node-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tree-children { list-style: none; padding-left: 16px; margin: 0; }
</style>
