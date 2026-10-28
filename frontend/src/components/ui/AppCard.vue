<template>
  <div class="app-card" :class="{ 'app-card--interactive': interactive }">
    <header v-if="title || $slots.header" class="app-card__header">
      <slot name="header">
        <h3 class="app-card__title">{{ title }}</h3>
        <p v-if="subtitle" class="app-card__subtitle">{{ subtitle }}</p>
      </slot>
      <div v-if="$slots.actions" class="app-card__actions">
        <slot name="actions" />
      </div>
    </header>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  interactive: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-card {
  display: grid;
  gap: var(--spacing-sm);
  min-width: 0;
  padding: var(--surface-padding);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
}

.app-card--interactive {
  cursor: pointer;
  transition: border-color var(--transition-base), box-shadow var(--transition-base), transform var(--transition-base);
}

.app-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  min-width: 0;
}

.app-card__title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
}

.app-card__subtitle {
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.app-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

@media (hover: hover) {
  .app-card--interactive:hover {
    border-color: var(--color-border-strong);
    box-shadow: var(--shadow-md);
  }
}
</style>
