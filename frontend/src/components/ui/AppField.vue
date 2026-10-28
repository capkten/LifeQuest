<template>
  <div class="app-field">
    <label class="app-field__label" :for="fieldId">
      {{ label }}
      <span v-if="required" class="app-field__required" aria-hidden="true">*</span>
    </label>

    <slot name="control" :id="fieldId" :ariaDescribedby="describedBy" :aria-describedby="describedBy" />

    <p v-if="hint && !error" :id="`${fieldId}-hint`" class="app-field__hint">{{ hint }}</p>
    <p v-if="error" :id="`${fieldId}-error`" class="app-field__error" role="alert">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  id: { type: String, default: '' },
  label: { type: String, required: true },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
})

const generatedId = useId()
const fieldId = computed(() => props.id || `app-field-${generatedId}`)

const describedBy = computed(() => {
  if (props.error) return `${fieldId.value}-error`
  if (props.hint) return `${fieldId.value}-hint`
  return undefined
})
</script>

<style scoped>
.app-field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.app-field__label {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.app-field__required {
  color: var(--color-error);
}

.app-field__hint {
  font-size: var(--font-size-xs);
  line-height: 1.5;
  color: var(--color-text-tertiary);
}

.app-field__error {
  font-size: var(--font-size-xs);
  line-height: 1.5;
  color: var(--color-error);
}

.app-field :deep(input:not([type='checkbox']):not([type='radio'])),
.app-field :deep(select),
.app-field :deep(textarea) {
  width: 100%;
  min-height: var(--touch-target-min);
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-bg-secondary);
  color: var(--color-text);
  font-family: var(--font-family);
}

.app-field :deep(input:focus-visible),
.app-field :deep(select:focus-visible),
.app-field :deep(textarea:focus-visible) {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}
</style>
