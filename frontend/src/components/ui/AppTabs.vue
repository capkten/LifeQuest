<template>
  <div class="app-tabs" role="tablist" aria-label="视图切换">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      role="tab"
      class="app-tabs__tab"
      :class="{ 'app-tabs__tab--active': item.key === modelValue }"
      :aria-selected="item.key === modelValue"
      :tabindex="item.key === modelValue ? 0 : -1"
      @click="select(item)"
    >
      <span class="app-tabs__label">{{ item.label }}</span>
      <span v-if="item.count !== undefined && item.count !== null" class="app-tabs__count">{{ item.count }}</span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  items: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

function select(item) {
  if (item.key === props.modelValue) return
  emit('update:modelValue', item.key)
}
</script>

<style scoped>
/* Hugs its tabs so a two-tab filter does not stretch across a desktop page. */
.app-tabs {
  display: inline-flex;
  max-width: 100%;
  gap: 4px;
  padding: 4px;
  overflow-x: auto;
  border-radius: var(--radius-control);
  background: var(--color-bg-tertiary);
  scrollbar-width: none;
}

.app-tabs::-webkit-scrollbar {
  display: none;
}

.app-tabs__tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex: 0 1 auto;
  min-height: 36px;
  padding: 0 var(--spacing-sm);
  border: 1px solid transparent;
  border-radius: calc(var(--radius-control) - 4px);
  background: transparent;
  color: var(--color-text-secondary);
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.app-tabs__tab--active {
  background: var(--color-card);
  color: var(--color-primary-dark);
  box-shadow: var(--shadow-sm);
}

.app-tabs__count {
  min-width: 18px;
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.app-tabs__tab--active .app-tabs__count {
  background: rgba(14, 165, 233, 0.14);
  color: var(--color-primary-dark);
}
</style>
