<template>
  <section class="note-viewer" aria-live="polite">
    <div v-if="loading" class="viewer-state">
      <span class="viewer-spinner" aria-hidden="true"></span>
      <p>正在加载笔记…</p>
    </div>
    <div v-else-if="error" class="viewer-state viewer-state--error">
      <p>{{ errorMessage }}</p>
      <button class="viewer-button viewer-button--primary" type="button" @click="$emit('retry')">重试</button>
    </div>
    <div v-else-if="!note" class="viewer-state">
      <div class="viewer-empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
        </svg>
      </div>
      <h3>选择一篇笔记</h3>
      <p>从左侧目录树选择或新建笔记，开始专注写作与阅读。</p>
    </div>
    <article v-else class="viewer-article">
      <header class="viewer-header">
        <div class="viewer-top-meta">
          <p v-if="note.path" class="viewer-path">{{ note.path }}</p>
          <div class="viewer-actions">
            <span v-if="!canEdit" class="viewer-readonly">只读成员</span>
            <button v-if="canEdit" class="viewer-button viewer-button--primary" type="button" @click="$emit('edit', note)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" />
              </svg>
              <span>编辑</span>
            </button>
            <button v-if="canEdit" class="viewer-icon-button" type="button" :aria-label="note.is_pinned ? '取消置顶' : '置顶笔记'" @click="$emit('toggle-pin', note)">
              {{ note.is_pinned ? '取消置顶' : '置顶' }}
            </button>
            <button v-if="canEdit" class="viewer-icon-button" type="button" aria-label="移动笔记" @click="$emit('move', note)">
              移动
            </button>
            <button v-if="canEdit" class="viewer-icon-button viewer-icon-button--danger" type="button" aria-label="删除笔记" @click="$emit('delete', note)">
              删除
            </button>
          </div>
        </div>

        <div class="viewer-heading">
          <h1 class="viewer-title">{{ note.title || note.name || '未命名笔记' }}</h1>
          <p v-if="note.summary" class="viewer-summary">{{ note.summary }}</p>
          <div class="viewer-meta">
            <span class="viewer-meta-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              {{ formatDate(note.updated_at) }}
            </span>
            <span v-if="note.word_count != null" class="viewer-meta-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
              {{ note.word_count }} 字
            </span>
            <span v-if="note.is_pinned" class="viewer-meta-item viewer-meta-item--pinned">
              📌 已置顶
            </span>
          </div>
          <div v-if="tagList.length" class="viewer-tags">
            <span v-for="tag in tagList" :key="tag"># {{ tag }}</span>
          </div>
        </div>
      </header>
      <div class="viewer-content">
        <v-md-editor :model-value="previewContent" mode="preview" height="auto" />
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { getErrorMessage } from '../../utils/errorMessage'
import { resolveNoteAttachmentUrls } from '../../services/note'

const props = defineProps({
  noteId: { type: [String, Number], default: null },
  note: { type: Object, default: null },
  loading: Boolean,
  error: { type: [String, Object], default: null },
  canEdit: { type: Boolean, default: true }
})
defineEmits(['edit', 'toggle-pin', 'move', 'delete', 'retry'])

const tagList = computed(() => String(props.note?.tags || '').split(',').map(tag => tag.trim()).filter(Boolean))
const previewContent = computed(() => resolveNoteAttachmentUrls(props.note?.content || ''))
const errorMessage = computed(() => typeof props.error === 'string' ? props.error : getErrorMessage(props.error))

function formatDate(value) {
  if (!value) return '尚未更新'
  const d = new Date(value)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.note-viewer {
  width: 100%;
  min-width: 0;
  color: var(--color-text);
  background: #ffffff;
}

.viewer-article {
  max-width: 100%;
  padding: 32px 48px 80px;
  width: 100%;
  box-sizing: border-box;
}

.viewer-header {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--color-border);
}

.viewer-top-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.viewer-path {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-tertiary);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.viewer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.viewer-button,
.viewer-icon-button {
  min-height: 36px;
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #ffffff;
  color: var(--color-text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.viewer-button svg {
  width: 15px;
  height: 15px;
}

.viewer-button:hover,
.viewer-icon-button:hover {
  background: var(--color-surface-low);
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.viewer-button--primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 2px 6px rgba(14, 165, 233, 0.25);
}

.viewer-button--primary:hover {
  background: var(--color-primary-dark);
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(14, 165, 233, 0.35);
}

.viewer-icon-button--danger {
  color: var(--color-error);
}

.viewer-icon-button--danger:hover {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
}

.viewer-readonly {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.viewer-heading {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.viewer-title {
  margin: 0;
  font-size: clamp(2rem, 3.5vw, 2.6rem);
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: -0.025em;
  color: #0F172A;
  overflow-wrap: anywhere;
}

.viewer-summary {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.viewer-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.viewer-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.viewer-meta-item svg {
  width: 14px;
  height: 14px;
}

.viewer-meta-item--pinned {
  color: var(--color-primary-dark);
  font-weight: 600;
}

.viewer-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.viewer-tags span {
  color: var(--color-primary-dark);
  background: rgba(14, 165, 233, 0.08);
  border: 1px solid rgba(14, 165, 233, 0.18);
  border-radius: var(--radius-full);
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
}

/* Notion Document Typography */
.viewer-content {
  min-width: 0;
  padding: var(--spacing-xl) var(--spacing-lg) var(--spacing-xl);
  font-size: 16px;
  line-height: 1.8;
  color: #1E293B;
  overflow-wrap: anywhere;
}

.viewer-content :deep(.v-md-editor) {
  border: 0;
  background: transparent;
  font-family: inherit;
}

.viewer-content :deep(.v-md-editor__preview-wrapper) {
  padding: 0;
}

.viewer-content :deep(h1) {
  font-size: 1.85rem;
  font-weight: 700;
  margin: 1.8em 0 0.6em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid var(--color-border);
  color: #0F172A;
}

.viewer-content :deep(h2) {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 1.5em 0 0.5em;
  color: #0F172A;
}

.viewer-content :deep(h3) {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1.2em 0 0.4em;
  color: #0F172A;
}

.viewer-content :deep(p) {
  margin: 0.8em 0;
  line-height: 1.8;
}

.viewer-content :deep(blockquote) {
  margin: 1.2em 0;
  padding: 10px 18px;
  border-left: 3px solid var(--color-primary);
  background: var(--color-surface-low);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--color-text-secondary);
}

.viewer-content :deep(code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--color-surface-low);
  border: 1px solid var(--color-border);
  color: #0284C7;
  font-size: 0.9em;
  font-family: var(--font-family-mono, monospace);
}

.viewer-content :deep(pre) {
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  background: #0F172A;
  color: #F8FAFC;
  overflow-x: auto;
}

.viewer-content :deep(pre code) {
  background: transparent;
  border: none;
  color: inherit;
  padding: 0;
}

.viewer-state {
  min-height: 380px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  color: var(--color-text-tertiary);
  text-align: center;
  padding: 40px;
}

.viewer-empty-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-xl);
  background: var(--color-surface-low);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.viewer-empty-icon svg {
  width: 32px;
  height: 32px;
  color: var(--color-text-tertiary);
}

.viewer-state h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
}

.viewer-state p {
  margin: 0;
  font-size: var(--font-size-sm);
  max-width: 360px;
}

.viewer-state--error {
  color: var(--color-error);
}

.viewer-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 767px) {
  .viewer-article {
    padding: 24px 20px 60px;
  }
  .viewer-top-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
