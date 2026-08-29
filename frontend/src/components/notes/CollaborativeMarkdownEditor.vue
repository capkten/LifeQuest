<template>
  <section class="collaborative-editor" aria-label="Markdown 编辑器">
    <header class="editor-toolbar">
      <div class="editor-modes" role="tablist" aria-label="编辑模式">
        <button
          v-for="option in modes"
          :key="option.value"
          type="button"
          class="mode-button"
          :class="{ 'mode-button--active': mode === option.value }"
          role="tab"
          :aria-selected="mode === option.value"
          @click="mode = option.value"
        >
          {{ option.label }}
        </button>
      </div>
      <label v-if="!disabled && !uploadDisabled" class="upload-button" title="插入图片">
        <input type="file" accept="image/*" @change="handleFileChange" />
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <path d="m21 15-5-5L5 21" />
        </svg>
        <span>插入图片</span>
      </label>
    </header>

    <div class="editor-panels" :class="`editor-panels--${mode}`">
      <div v-show="mode !== 'preview'" class="editor-input-panel">
        <textarea
          ref="textarea"
          class="editor-textarea"
          :value="modelValue"
          :disabled="disabled"
          :placeholder="placeholder"
          spellcheck="false"
          @input="$emit('update:modelValue', $event.target.value)"
        ></textarea>
      </div>
      <div v-show="mode !== 'edit'" class="editor-preview-panel">
        <v-md-editor :model-value="previewContent || ''" mode="preview" height="100%" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { resolveNoteAttachmentUrls } from '../../services/note'

const emit = defineEmits(['update:modelValue', 'upload-image'])
const textarea = ref(null)
const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  uploadDisabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '使用 Markdown 编写内容...' },
})
const mode = ref('split')
const modes = [
  { value: 'edit', label: '编辑' },
  { value: 'split', label: '分屏' },
  { value: 'preview', label: '预览' },
]
const previewContent = computed(() => resolveNoteAttachmentUrls(props.modelValue))

function insertMarkdown(markdown) {
  const input = textarea.value
  if (!input) return
  const start = input.selectionStart ?? input.value.length
  const end = input.selectionEnd ?? start
  const next = `${input.value.slice(0, start)}${markdown}${input.value.slice(end)}`
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    input.focus()
    const cursor = start + markdown.length
    input.setSelectionRange(cursor, cursor)
  })
}

function handleFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  emit('upload-image', file, (url) => insertMarkdown(`![${file.name}](${url})`))
}
</script>

<style scoped>
.collaborative-editor { display: flex; flex-direction: column; height: 100%; min-height: 0; background: var(--color-bg-secondary); }
.editor-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); min-height: 48px; padding: 6px var(--spacing-md); border-bottom: 1px solid var(--color-border); background: var(--color-bg-tertiary); }
.editor-modes { display: inline-flex; gap: 4px; }
.mode-button, .upload-button { display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 6px 12px; border: 1px solid transparent; border-radius: var(--radius-sm); color: var(--color-text-secondary); background: transparent; cursor: pointer; font: inherit; font-size: var(--font-size-sm); }
.mode-button:hover, .mode-button:focus-visible, .upload-button:hover, .upload-button:focus-within { border-color: var(--color-border); color: var(--color-text); background: var(--color-card); outline: none; }
.mode-button--active { color: var(--color-primary); background: var(--color-card); border-color: var(--color-border); font-weight: 700; }
.upload-button input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.upload-button svg { width: 18px; height: 18px; }
.editor-panels { display: grid; flex: 1; min-height: 0; }
.editor-panels--edit, .editor-panels--preview { grid-template-columns: 1fr; }
.editor-panels--split { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.editor-input-panel, .editor-preview-panel { min-height: 0; overflow: auto; }
.editor-input-panel { border-right: 1px solid var(--color-border); }
.editor-textarea { width: 100%; height: 100%; box-sizing: border-box; resize: none; padding: var(--spacing-xl); border: 0; outline: none; color: var(--color-text); background: var(--color-bg-secondary); font: 15px/1.75 var(--font-family-mono, ui-monospace, SFMono-Regular, Menlo, monospace); }
.editor-textarea:focus { box-shadow: inset 0 0 0 2px var(--color-primary); }
.editor-textarea:disabled { opacity: .7; cursor: not-allowed; }
.editor-preview-panel { padding: var(--spacing-xl); background: var(--color-bg-secondary); }
.editor-preview-panel :deep(.v-md-editor) { border: 0; background: transparent; }
.editor-preview-panel :deep(.v-md-editor__preview-wrapper) { padding: 0; }
@media (max-width: 767px) {
  .editor-toolbar { padding: 6px var(--spacing-sm); }
  .mode-button, .upload-button { min-height: 40px; padding: 6px 9px; }
  .upload-button span { display: none; }
  .editor-panels--split { grid-template-columns: 1fr; }
  .editor-panels--split .editor-preview-panel { display: none; }
  .editor-textarea, .editor-preview-panel { padding: var(--spacing-md); }
}
@media (prefers-reduced-motion: reduce) { .mode-button, .upload-button { transition: none; } }
</style>
