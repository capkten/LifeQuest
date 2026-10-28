<template>
  <div
    class="app-state"
    :class="[`app-state--${state}`, { 'app-state--compact': compact }]"
    :role="state === 'error' ? 'alert' : 'status'"
    :aria-busy="state === 'loading' ? 'true' : undefined"
  >
    <span v-if="state === 'loading'" class="app-state__spinner" aria-hidden="true"></span>
    <span v-else class="app-state__icon" aria-hidden="true">
      <slot name="icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <template v-if="state === 'error'">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v5" />
            <path d="M12 16.5v.01" />
          </template>
          <template v-else>
            <circle cx="12" cy="12" r="9" />
            <path d="M8 13.5 11 16.5 16.5 9" />
          </template>
        </svg>
      </slot>
    </span>

    <p class="app-state__title">{{ title || defaultTitle }}</p>
    <p v-if="description" class="app-state__description">{{ description }}</p>
    <div v-if="$slots.actions" class="app-state__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const DEFAULT_TITLES = {
  loading: '正在加载…',
  empty: '这里还没有内容',
  error: '加载失败',
}

const props = defineProps({
  state: {
    type: String,
    default: 'empty',
    validator: (value) => ['loading', 'empty', 'error'].includes(value),
  },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const defaultTitle = computed(() => DEFAULT_TITLES[props.state] || DEFAULT_TITLES.empty)
</script>

<style scoped>
.app-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  min-height: 180px;
  padding: var(--spacing-xl) var(--spacing-lg);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-card);
  color: var(--color-text-secondary);
  text-align: center;
}

.app-state--compact {
  min-height: 0;
  padding: var(--spacing-md);
  gap: 2px;
}

.app-state--error {
  border-color: rgba(239, 68, 68, 0.32);
  background: rgba(239, 68, 68, 0.04);
}

.app-state__icon svg {
  width: 28px;
  height: 28px;
  color: var(--color-text-tertiary);
}

.app-state--error .app-state__icon svg {
  color: var(--color-error);
}

.app-state__spinner {
  width: 22px;
  height: 22px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: app-state-spin 700ms linear infinite;
}

.app-state__title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.app-state__description {
  max-width: 34ch;
  font-size: var(--font-size-xs);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.app-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
}

@keyframes app-state-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-state__spinner {
    animation-duration: 1.6s;
  }
}
</style>
