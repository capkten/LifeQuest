<template>
  <span class="app-badge" :class="`app-badge--${tone}`">
    <slot />
  </span>
</template>

<script setup>
defineProps({
  tone: { type: String, default: 'neutral' },
})
</script>

<style scoped>
.app-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 22px;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 600;
  white-space: nowrap;
}

.app-badge--primary {
  background: rgba(14, 165, 233, 0.12);
  color: var(--color-primary-dark);
}

.app-badge--success {
  background: rgba(16, 185, 129, 0.12);
  color: var(--color-success-dark);
}

.app-badge--warning {
  background: rgba(245, 158, 11, 0.14);
  color: var(--color-warning-dark);
}

.app-badge--danger {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error-dark);
}

/* Achievement and realm markers carry the gold token so the reward layer
   stays visually distinct from navigation and status chrome. */
.app-badge--gold {
  background: rgba(245, 158, 11, 0.16);
  color: var(--color-gold);
  border: 1px solid rgba(245, 158, 11, 0.28);
}
</style>
