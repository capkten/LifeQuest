<template>
  <button
    :type="nativeType"
    class="app-button"
    :class="[`app-button--${variant}`, `app-button--${size}`, { 'app-button--block': block }]"
    :disabled="disabled || loading"
    :aria-busy="loading ? 'true' : undefined"
  >
    <span v-if="loading" class="app-button__spinner" aria-hidden="true"></span>
    <slot />
  </button>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  nativeType: { type: String, default: 'button' },
  block: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  min-height: var(--touch-target-min);
  padding: 0 var(--spacing-md);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
  transition: background-color var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.app-button--block {
  width: 100%;
}

.app-button--sm {
  min-height: 36px;
  padding: 0 var(--spacing-sm);
  font-size: var(--font-size-xs);
}

.app-button--lg {
  min-height: var(--touch-target-android);
  font-size: var(--font-size-base);
}

.app-button--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.app-button--secondary {
  background: var(--color-bg-secondary);
  border-color: var(--color-border);
  color: var(--color-text);
}

.app-button--ghost {
  background: transparent;
  border-color: transparent;
  color: var(--color-primary-dark);
}

.app-button--danger {
  background: var(--color-error);
  border-color: var(--color-error);
  color: #fff;
}

.app-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.app-button__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: var(--radius-full);
  animation: app-button-spin 700ms linear infinite;
}

@keyframes app-button-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
