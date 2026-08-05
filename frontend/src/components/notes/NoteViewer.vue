<template>
  <section class="note-viewer" aria-live="polite">
    <div v-if="loading" class="viewer-state"><span class="viewer-spinner" aria-hidden="true"></span><p>正在加载笔记…</p></div>
    <div v-else-if="error" class="viewer-state viewer-state--error"><p>{{ errorMessage }}</p><button class="viewer-button" type="button" @click="$emit('retry')">重试</button></div>
    <div v-else-if="!note" class="viewer-state"><p>从左侧目录选择一篇笔记开始阅读。</p></div>
    <article v-else class="viewer-article">
      <header class="viewer-header">
        <div class="viewer-heading">
          <p v-if="note.path" class="viewer-path">{{ note.path }}</p>
          <h1>{{ note.title || note.name || '未命名笔记' }}</h1>
          <p v-if="note.summary" class="viewer-summary">{{ note.summary }}</p>
          <div class="viewer-meta"><span>{{ formatDate(note.updated_at) }}</span><span v-if="note.word_count != null">{{ note.word_count }} 字</span><span v-if="note.is_pinned">已置顶</span></div>
          <div v-if="tagList.length" class="viewer-tags"><span v-for="tag in tagList" :key="tag">#{{ tag }}</span></div>
        </div>
        <div class="viewer-actions">
          <button class="viewer-button viewer-button--primary" type="button" @click="$emit('edit', note)">编辑</button>
          <button class="viewer-icon-button" type="button" :aria-label="note.is_pinned ? '取消置顶' : '置顶笔记'" @click="$emit('toggle-pin', note)">{{ note.is_pinned ? '取消置顶' : '置顶' }}</button>
          <button class="viewer-icon-button" type="button" aria-label="移动笔记" @click="$emit('move', note)">移动</button>
          <button class="viewer-icon-button viewer-icon-button--danger" type="button" aria-label="删除笔记" @click="$emit('delete', note)">删除</button>
        </div>
      </header>
      <div class="viewer-content">
        <v-md-editor :model-value="note.content || ''" mode="preview" height="auto" />
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ noteId: { type: [String, Number], default: null }, note: { type: Object, default: null }, loading: Boolean, error: { type: [String, Object], default: null } })
defineEmits(['edit', 'toggle-pin', 'move', 'delete', 'retry'])
const tagList = computed(() => String(props.note?.tags || '').split(',').map(tag => tag.trim()).filter(Boolean))
const errorMessage = computed(() => typeof props.error === 'string' ? props.error : props.error?.response?.data?.detail || '笔记加载失败，请重试。')
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN') : '尚未更新' }
</script>

<style scoped>
.note-viewer { width: 100%; min-width: 0; color: var(--color-text); }
.viewer-article { min-width: 0; }
.viewer-header { display: flex; gap: var(--spacing-lg); justify-content: space-between; padding-bottom: var(--spacing-lg); border-bottom: 1px solid var(--color-border); }
.viewer-heading { min-width: 0; }
.viewer-path, .viewer-meta, .viewer-summary { color: var(--color-text-tertiary); font-size: var(--font-size-sm); }
.viewer-path { margin: 0 0 var(--spacing-sm); overflow-wrap: anywhere; }
.viewer-heading h1 { margin: 0; font-size: clamp(1.5rem, 3vw, 2.4rem); overflow-wrap: anywhere; }
.viewer-summary { margin: var(--spacing-sm) 0 0; max-width: 72ch; }
.viewer-meta, .viewer-tags { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); margin-top: var(--spacing-md); }
.viewer-tags span { color: var(--color-primary); background: var(--workspace-soft, rgba(14,165,233,.08)); border-radius: 999px; padding: 4px 10px; }
.viewer-actions { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); align-items: flex-start; justify-content: flex-end; }
.viewer-button, .viewer-icon-button { min-height: 44px; padding: var(--spacing-sm) var(--spacing-md); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-card); color: var(--color-text); cursor: pointer; font: inherit; }
.viewer-button--primary { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.viewer-icon-button--danger { color: var(--color-error); }
.viewer-button:focus-visible, .viewer-icon-button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.viewer-content { min-width: 0; padding-top: var(--spacing-xl); overflow-wrap: anywhere; }
.viewer-content :deep(.v-md-editor) { border: 0; background: transparent; }
.viewer-content :deep(.v-md-editor__preview-wrapper) { padding: 0; }
.viewer-state { min-height: 360px; display: grid; place-items: center; gap: var(--spacing-md); color: var(--color-text-tertiary); text-align: center; }
.viewer-state--error { color: var(--color-error); }
.viewer-spinner { width: 28px; height: 28px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 767px) { .viewer-header { flex-direction: column; } .viewer-actions { justify-content: flex-start; } }
@media (prefers-reduced-motion: reduce) { .viewer-spinner { animation: none; } }
</style>
