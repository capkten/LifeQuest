import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const view = (name) => readFile(new URL(`./${name}`, import.meta.url), 'utf8')
const service = (name) => readFile(new URL(`../services/${name}`, import.meta.url), 'utf8')
const composable = (name) => readFile(new URL(`../composables/${name}`, import.meta.url), 'utf8')
const workflow = () => readFile(new URL('../../../.github/workflows/desktop-release.yml', import.meta.url), 'utf8')
const tauriConfig = () => readFile(new URL('../../../desktop/src-tauri/tauri.conf.json', import.meta.url), 'utf8')

test('desktop sync keeps one explicit Tauri service boundary and no server paths', async () => {
  const source = await service('noteSync.js')
  assert.match(source, /__TAURI__|__TAURI_INTERNALS__/)
  assert.match(source, /preview_sync|previewSync/)
  assert.match(source, /start_sync|startSync/)
  assert.match(source, /sync_now|syncNow/)
  assert.doesNotMatch(source, /content_path|notes_data/)
})

test('note sync composable exposes lifecycle-safe status and conflict actions', async () => {
  const source = await composable('useNoteSync.js')
  for (const name of ['binding', 'status', 'preview', 'conflicts', 'selectFolder', 'previewSync', 'start', 'pause', 'resume', 'syncNow', 'resolveConflict']) {
    assert.match(source, new RegExp(`\\b${name}\\b`))
  }
  assert.match(source, /onUnmounted/)
  assert.match(source, /unlisten|cleanup|stopListening/)
})

test('sync view requires an explicit first-sync confirmation and gates browser fallback', async () => {
  const source = await view('NoteSync.vue')
  assert.match(source, /isDesktop|桌面客户端|Windows 客户端/)
  assert.match(source, /window\.confirm/)
  assert.match(source, /预览|preview/i)
  assert.match(source, /冲突/)
  assert.match(source, /is_owner|canSync|owner/i)
})

test('notebook workspace exposes sync only to owners', async () => {
  const source = await view('NotebookFileManage.vue')
  assert.match(source, /canManageMembers|is_owner/)
  assert.match(source, /NoteSync|文件夹同步|同步/)
  assert.match(source, /notes.*sync|NoteSync/, 'workspace should link to the sync route')
})

test('desktop release embeds and validates a real API endpoint', async () => {
  const source = await workflow()
  assert.match(source, /DESKTOP_API_BASE_URL/)
  assert.match(source, /VITE_API_BASE_URL/)
  assert.match(source, /IsNullOrWhiteSpace\(\$env:DESKTOP_API_BASE_URL\)|test -n.*DESKTOP_API_BASE_URL/s)
})

test('desktop CSP permits the configured HTTPS API and websocket endpoint', async () => {
  const source = await tauriConfig()
  assert.match(source, /connect-src[^\"]*https:/)
  assert.match(source, /connect-src[^\"]*wss:/)
  assert.match(source, /img-src[^\"]*https:/)
})
