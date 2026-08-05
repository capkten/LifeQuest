# LifeQuest Notebook Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将笔记模块改造成保留左侧目录的笔记本工作区，并提供阅读模式、独立编辑模式、跨设备最近打开、元数据编辑、自动保存和可筛选排序的查找体验。

**Architecture:** 保留现有 FastAPI、SQLAlchemy、Markdown 文件存储、Vue Router 和 VMdEditor。后端为 `NoteNode` 增加 `last_opened_at`，提供打开记录和最近笔记接口；前端以 `NotebookFileManage.vue` 为工作区壳层，抽取 `NoteTree.vue`、`NoteViewer.vue` 和 `useNoteWorkspace.js`，让 `NoteEditor.vue` 只负责编辑模式。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3 Composition API, Vue Router, VMdEditor, scoped CSS.

## Global Constraints

- 保留现有笔记 API、Markdown 文件存储、图片上传和旧路由兼容性。
- 点击笔记默认进入阅读模式；编辑完成后回到当前笔记阅读模式，并保持原笔记本、原文件夹和目录位置。
- 最近打开记录使用后端 `last_opened_at` 持久化，跨设备同步，不依赖 localStorage。
- 标题、正文、摘要、标签或置顶变化都参与 dirty/自动保存状态。
- 桌面端为目录 + 内容双栏；移动端目录为抽屉；375px、768px、1024px、1440px 不得出现页面级横向溢出。
- 所有主要交互控件最小触控区域为 44px，使用现有 SVG 图标系统，不新增 emoji 图标。
- 新增后端行为必须有 pytest 覆盖；前端至少运行 `npm run build`、`git diff --check` 和浏览器验证。

---

### Task 1: Persist recent-open metadata

**Files:** `backend/app/models/note_node.py`, `backend/app/schemas/note.py`, `backend/app/repositories/note.py`, `backend/app/services/note.py`, `backend/app/api/notes.py`, `backend/app/main.py`, `backend/tests/test_notes.py`

**Produces:** `NoteNode.last_opened_at: Optional[datetime]`; `NoteService.mark_note_opened(note_id, user_id)`; `NoteService.get_recent_notes(user_id, limit)`; `POST /api/notes/{note_id}/open`; `GET /api/notes/recent?limit=8`; response fields on `NodeResponse` and `NoteDetailResponse`.

- [ ] Write failing tests for opening a note, sorting recent notes, user isolation, folder rejection and limit validation.
- [ ] Run `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q backend/tests/test_notes.py -k "open or recent"` and confirm failure because the field/endpoints do not exist.
- [ ] Add nullable `last_opened_at` and an idempotent startup migration for existing `note_nodes` tables.
- [ ] Implement repository/service/API behavior scoped through `Notebook.user_id`; reject folders with 404 and other users with 403; order by `last_opened_at DESC NULLS LAST`, then `updated_at DESC`; bound limit to 1–50.
- [ ] Run the focused note tests and full `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q` from `backend`.
- [ ] Commit with `git commit -m "feat(notes): persist recent opened notes"` after the focused and full suites pass.

### Task 2: Add filtered note discovery

**Files:** `backend/app/repositories/note.py`, `backend/app/services/note.py`, `backend/app/api/notes.py`, `backend/app/schemas/note.py`, `frontend/src/services/note.js`, `backend/tests/test_notes.py`

**Produces:** `GET /api/notes/discover` with fixed sort values `last_opened`, `updated`, `created`, `title` and filters `notebook_id`, `tag`, `pinned`, `updated_after`, `updated_before`, `limit`; frontend methods `getRecentNotes`, `markNoteOpened`, `discoverNotes`.

- [ ] Add failing tests for title/updated/recent sorting, pinned/tag/notebook/date filters and cross-user isolation.
- [ ] Implement a whitelist for sort values and user-scoped SQLAlchemy filters; unknown sort values return 422; null timestamps sort last.
- [ ] Keep `/api/notes/search` compatible and add the new route before `/{note_id}`; return path, tags, summary, word count, timestamps and pin state.
- [ ] Add frontend service wrappers without changing existing method signatures.
- [ ] Run `backend/tests/test_notes.py` and the full backend suite.
- [ ] Commit with `git commit -m "feat(notes): add filtered note discovery"`.

### Task 3: Build the persistent notebook workspace

**Files:** `frontend/src/router/index.js`, `frontend/src/views/NotebookFileManage.vue`, `frontend/src/components/notes/NoteTree.vue`, `frontend/src/composables/useNoteWorkspace.js`

**Produces:** route names `NotebookWorkspace`, `NotebookWorkspaceView`, `NotebookWorkspaceEdit`, `NewNoteInWorkspace`; composable methods `loadTree`, `selectNote`, `createFolder`, `createNote`, `renameNode`, `moveNode`, `deleteNode`; tree events `select`, `toggle`, `create-folder`, `create-note`, `rename`, `move`, `delete`.

- [ ] Add contextual routes while preserving `/notes/edit/:id` and `/notes/new/:notebookId` compatibility redirects.
- [ ] Extract the existing tree rendering and node actions into `NoteTree.vue`; selecting a note must update the selected id without removing the directory shell.
- [ ] Implement desktop two-column layout with workspace empty state, current-folder quick-create actions, selected-node state and preserved expansion state.
- [ ] Implement the mobile drawer using the same tree component; selecting a note closes the drawer and preserves bottom-nav safe-area spacing.
- [ ] Run `cd frontend; npm run build` and `git diff --check`; manually verify nested folders at 375px, 768px, 1024px and 1440px.
- [ ] Commit with `git commit -m "feat(notes): add persistent notebook workspace"`.

### Task 4: Add read-only Markdown viewing

**Files:** `frontend/src/components/notes/NoteViewer.vue`, `frontend/src/views/NotebookFileManage.vue`, `frontend/src/services/note.js`, `frontend/src/router/index.js`

**Produces:** viewer props `noteId`, `note`, `loading`, `error`; viewer events `edit`, `toggle-pin`, `move`, `delete`, `retry`.

- [ ] Define and verify loading, error, empty and loaded viewer states before implementation.
- [ ] Render Markdown through the existing VMdEditor theme/configuration; do not introduce another parser.
- [ ] Route selection to `/notes/:notebookId/view/:noteId`, load the note once, and call `markNoteOpened` once per successful view entry with a duplicate guard.
- [ ] Display title, summary, tags, pin state, word count, updated time, path and an Edit action; reuse existing node operations for pin/move/delete.
- [ ] Build and manually verify switching among notes keeps the tree, expansion and current folder intact.

### Task 5: Make NoteEditor contextual with metadata and autosave

**Files:** `frontend/src/views/NoteEditor.vue`, `frontend/src/router/index.js`, `frontend/src/services/note.js`, `frontend/src/composables/useNoteAutosave.js`

**Produces:** `useNoteAutosave({ snapshot, save, delay = 900 })` returning `dirty`, `status`, `lastSavedAt`, `schedule`, `saveNow`, `cancel`; statuses exactly `idle`, `dirty`, `saving`, `saved`, `error`; save payload `{ title, content, summary, tags, is_pinned }`.

- [ ] Add deterministic cases for dirty state, debounce, successful save, rejected save and cancel; use an existing test harness if available, otherwise verify with a documented browser console harness.
- [ ] Add summary, tags and pin fields; preserve backend comma-separated tags format.
- [ ] Implement one in-flight save guard, debounced autosave, manual flush, visible status and retry after error; new-note creation still requires a title.
- [ ] Preserve notebook/folder context in route state and return to the view route after save; add `onBeforeRouteLeave` and browser unload protection while dirty.
- [ ] Build and manually verify edit, autosave, save failure retry, browser back, directory switching and mobile full-screen editing.

### Task 6: Add recent/pinned/discovery UI

**Files:** `frontend/src/views/Notes.vue`, `frontend/src/components/notes/NoteTree.vue` if needed, `frontend/src/styles/stitch-overrides.css`

- [ ] Add independent loading/error/empty states for recent notes, pinned notes, notebooks and global search.
- [ ] Render backend recent and pinned cards with title, summary, tags, word count, updated time, last-opened time and notebook/path; clicking routes directly to contextual reading mode.
- [ ] Add clearable notebook, tag, pin, date-range and sort controls; keep search query while changing filters and make controls keyboard accessible.
- [ ] Add quick-new-note actions from notebook cards, recent sections and workspace empty state.
- [ ] Build and manually verify recent-open refresh, pinned toggling, filters, sorting and mobile layout.

### Task 7: Regression, API docs and final QA

**Files:** `backend/tests/test_notes.py`, `docs/API.md`, `docs/superpowers/reports/2026-08-05-lifequest-notebook-workspace-verification.md`

- [ ] Document `last_opened_at`, `POST /api/notes/{note_id}/open`, `GET /api/notes/recent`, discovery parameters and error behavior in `docs/API.md`.
- [ ] Run `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q` from `backend` and `npm run build` from `frontend`; expected backend result is zero failures.
- [ ] Run `git diff --check`.
- [ ] Browser-verify `/notes`, workspace empty state, nested folders, reading mode, editing mode, autosave failure, unsaved navigation, recent list and discovery filters at 375px, 768px, 1024px and 1440px; confirm no page-level horizontal overflow.
- [ ] Record known limitations, including bundle-size warning only if still present.
- [ ] Commit with `git commit -m "feat(notes): add persistent notebook workspace and reading mode"` after all checks pass.
