import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('mobile shell reserves the fixed navigation and supports dynamic viewport height', async () => {
  const [app, layout] = await Promise.all([
    source('../App.vue'),
    source('../components/layout/AppLayout.vue'),
  ])

  assert.match(app, /--touch-target-android:\s*48px/)
  assert.match(app, /100dvh/)
  assert.match(layout, /--mobile-content-bottom-inset/)
  assert.match(layout, /padding-bottom:\s*var\(--mobile-content-bottom-inset\)/)
  assert.match(layout, /\.bottom-nav-item\s*\{[\s\S]*min-width:\s*var\(--touch-target-android\)[\s\S]*min-height:\s*var\(--touch-target-android\)/)
})

test('Notes entries expose keyboard semantics and both dialogs expose accessible focus hooks', async () => {
  const notes = await source('./Notes.vue')

  const searchCard = notes.match(/<button[\s\S]*?class="search-result-card"[\s\S]*?<\/button>/)?.[0] || ''
  assert.notEqual(searchCard, '')
  assert.doesNotMatch(searchCard, /role="button"/)
  assert.match(notes, /class="search-result-card"[^>]*type="button"/)
  assert.match(notes, /class="notebook-card"[^>]*role="button"/)
  assert.match(notes, /class="notebook-card"[\s\S]*@keydown.space.prevent/)
  assert.match(notes, /aria-labelledby="delete-dialog-title"/)
  assert.match(notes, /@keydown\.escape="cancelDialog"/)
  assert.match(notes, /aria-label="删除笔记本"/)
  assert.match(notes, /@keydown="trapDeleteFocus"/)
  assert.match(notes, /dialogTriggerRef\.value\?\.focus\(/)
})

test('mobile editor and calendar layouts have dynamic viewport fallbacks', async () => {
  const [editor, calendar] = await Promise.all([
    source('./NoteEditor.vue'),
    source('./Calendar.vue'),
  ])

  assert.match(editor, /100vh[\s\S]*100dvh/)
  assert.match(calendar, /100vh[\s\S]*100dvh/)
})

test('Home daily empty state offers a next action', async () => {
  const home = await source('./Home.vue')
  assert.match(home, /class="empty-state"[\s\S]*to="\/todos"[\s\S]*创建任务/)
})

test('shared mobile overrides keep controls readable and touchable across pages', async () => {
  const styles = await source('../styles/stitch-overrides.css')

  assert.match(styles, /\.dialog-close[\s\S]*min-width:\s*var\(--touch-target-min\)/)
  assert.match(styles, /\.dialog-close[\s\S]*min-height:\s*var\(--touch-target-min\)/)
  assert.match(styles, /\.dialog-close[\s\S]*min-width:\s*var\(--touch-target-android\)/)
  assert.match(styles, /\.dialog-close[\s\S]*min-height:\s*var\(--touch-target-android\)/)
  assert.match(styles, /\.bottom-nav-item[\s\S]*font-size:\s*11px/)
  assert.match(styles, /\.login-container[\s\S]*100dvh/)
  assert.match(styles, /\.register-container[\s\S]*100dvh/)
  assert.match(styles, /\.file-manager[\s\S]*100dvh/)
})

test('shared mobile state cards reduce excess empty space without losing separation', async () => {
  const styles = await source('../styles/stitch-overrides.css')
  assert.match(styles, /\.empty-state,\s*\.loading-state,\s*\.error-state[\s\S]*min-height:\s*180px/)
  assert.match(styles, /input,\s*textarea,\s*select[\s\S]*font-size:\s*16px/)
})
