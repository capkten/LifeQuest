<template>
  <Teleport to="body">
    <Transition name="app-sheet">
      <div v-if="modelValue" class="app-sheet" @click.self="requestClose" @keydown.esc="requestClose">
        <div
          class="app-sheet__panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          ref="panelRef"
        >
          <header class="app-sheet__header">
            <h2 :id="titleId" class="app-sheet__title">{{ title }}</h2>
            <button
              type="button"
              class="app-sheet__close dialog-close"
              aria-label="关闭"
              :disabled="pending"
              @click="requestClose"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </header>

          <div class="app-sheet__body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="app-sheet__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  pending: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const generatedId = useId()
const titleId = computed(() => `app-sheet-title-${generatedId}`)
const panelRef = ref(null)

function requestClose() {
  if (props.pending) return
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    await nextTick()
    panelRef.value?.focus()
  },
)
</script>

<style scoped>
.app-sheet {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
  padding: env(safe-area-inset-top, 0px) 0 0;
}

.app-sheet__panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  width: min(100%, 520px);
  max-height: calc(100dvh - 40px);
  padding: var(--spacing-lg);
  padding-bottom: calc(var(--spacing-lg) + env(safe-area-inset-bottom, 0px));
  background: var(--color-card);
  border-radius: var(--radius-card) var(--radius-card) 0 0;
  box-shadow: var(--shadow-xl);
  outline: none;
}

.app-sheet__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.app-sheet__title {
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.app-sheet__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--touch-target-min);
  height: var(--touch-target-min);
  margin-right: calc(var(--spacing-xs) * -1);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.app-sheet__close svg {
  width: 18px;
  height: 18px;
}

.app-sheet__body {
  overflow-y: auto;
  overscroll-behavior: contain;
  min-height: 0;
}

.app-sheet__footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--spacing-xs);
}

.app-sheet-enter-active,
.app-sheet-leave-active {
  transition: opacity var(--transition-base);
}

.app-sheet-enter-active .app-sheet__panel,
.app-sheet-leave-active .app-sheet__panel {
  transition: transform var(--transition-base);
}

.app-sheet-enter-from,
.app-sheet-leave-to {
  opacity: 0;
}

.app-sheet-enter-from .app-sheet__panel,
.app-sheet-leave-to .app-sheet__panel {
  transform: translateY(12px);
}

@media (min-width: 768px) {
  .app-sheet {
    align-items: center;
    padding: var(--spacing-lg);
  }

  .app-sheet__panel {
    border-radius: var(--radius-card);
  }
}
</style>
