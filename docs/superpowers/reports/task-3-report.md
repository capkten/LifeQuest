# Task 3 — Persistent notebook workspace

## Pre-implementation browser harness

No frontend test runner is configured in `frontend/package.json`, so this task uses a documented browser harness in place of an automated red test. Before implementation, the existing `/notes/:notebookId` page was verified as the baseline: it rendered a tree and folder contents, but selecting a note navigated to the legacy editor, the tree had no action event surface, and there were no contextual workspace route names.

Run `cd frontend && npm run dev`, authenticate with a test account, and exercise these checks at 375px, 768px, 1024px, and 1440px:

1. Open a notebook with nested folders and a note. The directory remains visible after selecting a note; the selected id is highlighted and the right pane changes without losing expanded folders.
2. On desktop, confirm a two-column workspace, root/current-folder empty state, quick-create folder/note actions, and selected-node placeholder state.
3. On mobile, open and close the directory drawer, select a note, confirm the drawer closes, and confirm content remains above the bottom navigation and safe-area inset.
4. Confirm route names/paths are `NotebookWorkspace`, `NotebookWorkspaceView`, `NotebookWorkspaceEdit`, and `NewNoteInWorkspace`; legacy `/notes/edit/:id` and `/notes/new/:notebookId` still resolve.
5. Confirm tree interactions expose select, toggle, create-folder, create-note, rename, move, and delete behavior with keyboard-focusable controls and no emoji icons.
6. Confirm `document.documentElement.scrollWidth <= document.documentElement.clientWidth` at every viewport size.

The pre-implementation baseline fails checks 1, 2, 4, and 5, which is the expected red state for the manual TDD harness.

## Implementation status

Stopped at the user’s request before implementation. Task 3 workspace requirements are not complete.

## Changed files

This turn changed only:

- `docs/superpowers/reports/task-3-report.md`

The requested implementation files were not modified:

- `frontend/src/router/index.js`
- `frontend/src/views/NotebookFileManage.vue`
- `frontend/src/components/notes/NoteTree.vue`
- `frontend/src/composables/useNoteWorkspace.js`

## Build output summary

The pre-implementation baseline command `cd frontend && npm run build` exited 0. It reported the existing npm `always-auth` warning, Rollup `@vueuse/core` annotation warnings, and the existing large-chunk warning.

## Manual verification notes

No post-implementation browser verification was run because implementation and testing were stopped. The pre-implementation harness records the expected failures: no contextual workspace route names, no reusable tree event surface, and note selection leaves the workspace for the legacy editor.

## Remaining integration assumptions

The approved Task 3 plan still requires implementation of contextual routes, reusable tree actions, persisted workspace selection/expansion state, desktop two-column layout, mobile drawer behavior, and responsive overflow verification. Existing unrelated worktree changes were preserved and no commit was created.

## P1 review follow-up: Todo reward source_id length

Status: fixed.

Todo coin transactions now use compact, type-distinct source IDs without changing the existing `String(36)` database column or the existing cultivation source keys. Task and goal IDs use `t:` and `g:` plus a URL-safe UUID encoding; habit IDs use `h:` plus the same encoding and the completion date. The longest generated value is 33 characters, and the three reward paths remain independently identifiable. Coin history localization recognizes both the compact IDs and the existing `todo:<source>:` IDs, preserving source label semantics and legacy history display.

Regression coverage was added for all three reward writes and all three localized history displays.

Verification:

- `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_content_localization.py tests/test_todos.py -q` — 31 passed, 63 existing warnings.
- `cd backend; python -m compileall -q app` — passed.
- `git diff --check` — passed.

Fix commit: `ec36cb4` (`fix(todos): keep reward source ids within limit`).
