<template>
  <ul class="app-list" :class="{ 'app-list--dense': dense }">
    <slot />
  </ul>
</template>

<script setup>
defineProps({
  dense: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-list {
  display: grid;
  gap: var(--spacing-xs);
  margin: 0;
  padding: 0;
  list-style: none;
  min-width: 0;
}

.app-list--dense {
  gap: 0;
}

.app-list :deep(> li) {
  min-width: 0;
}

.app-list--dense :deep(> li) {
  padding-block: 6px;
  border-bottom: 1px solid var(--color-border);
}

.app-list--dense :deep(> li:last-child) {
  border-bottom: 0;
}
</style>
