# Windows Note Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Windows desktop client that reuses the existing LifeQuest Vue application and safely synchronizes one selected local folder with one LifeQuest notebook as Markdown files and folders.

**Architecture:** Use Tauri 2 as a thin Windows shell around the existing Vue/Vite build. The FastAPI server remains the cloud authority for notebook permissions, revisions, conflict detection, and sync changes; Rust owns local scanning, file watching, hashing, the durable queue, and filesystem writes. Version 1 is online-first and bidirectional with an explicit first-sync preview; it does not run FastAPI locally and does not expose `backend/notes_data`.

**Tech Stack:** Vue 3, Vite, FastAPI, SQLAlchemy, Pydantic, Tauri 2, Rust, `notify`, `reqwest`, `serde`, `serde_json`, `sha2`, Tauri dialog/store/filesystem capabilities, pytest, Rust unit tests, Playwright, Windows NSIS/MSI packaging.

## Global Constraints

- The repository-root `VERSION` file is the only project version source; desktop metadata must be generated from it and must not introduce a second manual version.
- The first release synchronizes UTF-8 `.md` files and folders only; attachments, arbitrary binary files, and a local FastAPI database are out of scope.
- One local root maps to one notebook in the first release; only the notebook owner can create or change a binding.
- The mapped path is selected by the user and is the only filesystem root the client may read or write.
- Never map or expose the server implementation directory `backend/notes_data` to the desktop client.
- No destructive delete is automatic: the first sync previews deletes, and later deletes use a recoverable conflict/trash path.
- Local file events are debounced and followed by a fresh directory scan; an event payload is never treated as the complete truth.
- Every remote write carries a unique `client_operation_id` and the last known `base_revision`.
- A conflict never uses last-write-wins. The original local file, remote content, and conflict metadata remain recoverable.
- All sync writes go through the same `NoteService` transaction path used by the web editor and notify Yjs collaboration rooms.
- Every feature starts with a failing test. Release verification includes backend tests, Rust tests, frontend build, and Windows integration evidence.

## Decision Record

### Why Tauri 2

The current frontend can be reused without introducing a second UI stack, while Rust is appropriate for path validation, file watching, atomic writes, and a persistent sync queue. Electron remains a viable fallback if an integration requirement cannot be met, but it should not be introduced alongside Tauri.

### What “mapping” means

The user chooses a local folder such as `D:\Notes\LifeQuest`. Its relative tree mirrors one notebook:

```text
D:\Notes\LifeQuest\Projects\Plan.md
                         -> notebook node path /Projects/Plan.md
D:\Notes\LifeQuest\Journal\
                         -> notebook folder /Journal
```

The hidden metadata directory `.lifequest` is reserved by the client and excluded from notebook content. The client stores stable remote node IDs there so rename and move do not create duplicate notes.

### Conflict policy

- Local changed and remote revision unchanged: upload local content with `base_revision`.
- Remote changed and local hash unchanged: download the remote content.
- Both changed: attempt a line-based three-way merge against the last synced content.
- Non-overlapping edits are merged and uploaded as a new revision.
- Overlapping edits create `.lifequest-conflicts/<relative-path>.<timestamp>.md`, keep the working file untouched, and show a conflict requiring explicit resolution.
- Local or remote delete versus an edit is always a conflict, never an implicit hard delete.

---

## Workstream 1 — Server sync protocol

### Task 1: Add notebook sync cursor and change log

**Files:**
- Create: `backend/app/models/note_sync.py`
- Create: `backend/app/schemas/note_sync.py`
- Modify: `backend/app/models/note.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/main.py`
- Test: `backend/tests/test_note_sync.py`, `backend/tests/test_notes.py`

**Data contract:**

- Add `Notebook.sync_revision: int` with default `0`.
- Add `NoteSyncChange` with `notebook_id`, `sequence`, `node_id`, `operation` (`create`, `update`, `move`, `delete`), `node_type`, `path`, `parent_id`, `content_revision`, `content_hash`, and `created_at`.
- Add `NoteSyncOperation` with `notebook_id`, `client_operation_id`, `operation`, `result_json`, and `created_at`; `(notebook_id, client_operation_id)` is unique.
- Add `NoteSyncConflict` with notebook/node IDs, local path, base hash, remote revision, conflict artifact path, status, and timestamps.
- `SyncManifestItem` exposes only stable node metadata and a SHA-256 hash. It never exposes `content_path` or any server filesystem path.

- [ ] **Step 1: Write failing tests** for monotonic notebook sequences, unique operation replay, manifest omission of `content_path`, delete tombstones, and database initialization with existing notebooks.
- [ ] **Step 2: Run** `cd backend; pytest tests/test_note_sync.py -q`; expect failures.
- [ ] **Step 3: Implement** the models and idempotent startup DDL using the existing `Base.metadata.create_all` plus manual migration pattern; do not introduce Alembic.
- [ ] **Step 4: Run** the focused tests and the existing note suite; expect PASS.
- [ ] **Step 5: Commit** `feat(notes): add sync cursor and operation ledger`.

### Task 2: Record every notebook mutation

**Files:**
- Modify: `backend/app/services/note.py`
- Modify: `backend/app/collaboration.py`, `backend/app/api/notes.py`
- Test: `backend/tests/test_note_sync.py`, `backend/tests/test_note_sharing.py`, `backend/tests/test_notes.py`

**Interface:**

`NoteService.record_sync_change(notebook_id, node_id, operation, path, parent_id, node_type, content_revision, content_hash) -> NoteSyncChange` allocates the next notebook sequence in the same transaction as the mutation.

- [ ] **Step 1: Write failing tests** for create folder/note, update content, rename, move, delete, and Yjs persistence each producing exactly one change with the correct path and hash.
- [ ] **Step 2: Add** a single internal helper in `NoteService` and call it before the existing commit in `create_folder`, `create_note`, `rename_node`, `move_node`, `update_note`, `persist_collaboration_content`, and `delete_node`.
- [ ] **Step 3: Add** an external-update broadcast in the collaboration manager. The broadcast must invalidate or update the room snapshot so a desktop upload cannot be overwritten by a stale collaborative editor.
- [ ] **Step 4: Run** `cd backend; pytest tests/test_note_sync.py tests/test_note_sharing.py tests/test_notes.py -q`; expect PASS.
- [ ] **Step 5: Commit** `feat(notes): emit sync changes for notebook mutations`.

### Task 3: Expose manifest, pull, apply, and conflict APIs

**Files:**
- Create: `backend/app/api/note_sync.py`
- Modify: `backend/app/schemas/note_sync.py`, `backend/app/services/note.py`, `backend/app/main.py`
- Test: `backend/tests/test_note_sync_api.py`

**Interfaces:**

```text
GET  /api/notes/notebooks/{notebook_id}/sync/manifest
GET  /api/notes/notebooks/{notebook_id}/sync/changes?after={cursor}&limit={n}
POST /api/notes/notebooks/{notebook_id}/sync/content
POST /api/notes/notebooks/{notebook_id}/sync/apply
GET  /api/notes/notebooks/{notebook_id}/sync/conflicts
POST /api/notes/notebooks/{notebook_id}/sync/conflicts/{conflict_id}/resolve
```

`POST /content` accepts `{ "node_ids": ["..."] }` and returns note content keyed by node ID. `POST /apply` accepts ordered operations:

```json
{
  "operations": [
    {
      "client_operation_id": "device-uuid:counter",
      "kind": "update_note",
      "node_id": "uuid",
      "path": "/Projects/Plan.md",
      "parent_id": "uuid",
      "content": "# Plan",
      "base_revision": 4,
      "base_hash": "sha256"
    }
  ]
}
```

Each result contains `client_operation_id`, `status` (`applied`, `already_applied`, `conflict`, `rejected`), the current node metadata, and a stable error code. A retry with the same operation ID returns the stored result and never applies the write twice.

- [ ] **Step 1: Write failing API tests** for owner-only access, viewer/editor rejection, manifest cursor, paginated changes, batch content, create/update/move/delete operations, idempotent retry, stale `base_revision`, and invalid path/name input.
- [ ] **Step 2: Implement** manifest and change queries without returning server filesystem paths.
- [ ] **Step 3: Implement** apply dispatch through `NoteService` and its existing atomic write/revision conflict path; record operation results in the same transaction.
- [ ] **Step 4: Implement** conflict creation and explicit resolve operations for `keep_local`, `keep_remote`, and `merged_content`.
- [ ] **Step 5: Run** `cd backend; pytest tests/test_note_sync_api.py tests/test_note_sync.py -q`; expect PASS.
- [ ] **Step 6: Commit** `feat(notes): expose bidirectional sync protocol`.

## Workstream 2 — Tauri desktop foundation

### Task 4: Scaffold the Windows shell and version flow

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/src-tauri/Cargo.toml`
- Create: `desktop/src-tauri/tauri.conf.json`
- Create: `desktop/src-tauri/capabilities/default.json`
- Create: `desktop/src-tauri/src/lib.rs`
- Modify: `scripts/sync-version.mjs`, `scripts/check-version.mjs`
- Create: `scripts/build-desktop.ps1`
- Test: `desktop/src-tauri/src/lib.rs`, `scripts/check-version.mjs`

**Interface:**

`desktop/package.json` provides `dev`, `build`, and `check:version` scripts. Tauri `beforeDevCommand` runs `npm --prefix ../frontend run dev`, and `beforeBuildCommand` runs `npm --prefix ../frontend run build`; `frontendDist` points to `../frontend/dist`.

- [ ] **Step 1: Write a failing version test** proving the desktop package and Tauri config read the root `VERSION` after `node scripts/sync-version.mjs`.
- [ ] **Step 2: Scaffold** the Tauri app with a single authenticated WebView and explicit dialog/fs capabilities.
- [ ] **Step 3: Add** the Windows build script that validates `VERSION`, builds Vue, and invokes `tauri build --bundles nsis,msi`.
- [ ] **Step 4: Run** `node scripts/check-version.mjs`, `cd frontend; npm run build`, and `cd desktop; npm run build`; expect version checks and builds to pass on a Windows machine with Rust installed.
- [ ] **Step 5: Commit** `feat(desktop): scaffold tauri windows client`.

### Task 5: Implement safe local filesystem state

**Files:**
- Create: `desktop/src-tauri/src/fs.rs`
- Create: `desktop/src-tauri/src/sync/mod.rs`
- Create: `desktop/src-tauri/src/sync/manifest.rs`
- Create: `desktop/src-tauri/src/state.rs`
- Test: `desktop/src-tauri/src/fs.rs`, `desktop/src-tauri/src/sync/manifest.rs`, `desktop/src-tauri/src/state.rs`

**Data contract:**

The mapped folder contains `.lifequest/manifest.json` with `{schema_version, notebook_id, device_id, entries}`. Each entry has `node_id`, `relative_path`, `node_type`, `content_hash`, `remote_revision`, `last_synced_content`, and `updated_at`. The durable queue and endpoint/token session metadata live under `%AppData%\\LifeQuest`, never in arbitrary user folders.

- [ ] **Step 1: Write failing Rust tests** for UTF-8 Markdown scanning, ignored `.lifequest` and `.lifequest-conflicts`, path separator normalization, reserved/invalid names, symlink or reparse-point escape, atomic manifest write, and hash stability.
- [ ] **Step 2: Implement** canonical root validation and reject every path whose canonical form is outside the selected root.
- [ ] **Step 3: Implement** a scanner that returns sorted relative paths and SHA-256 hashes; read files as UTF-8 and report an explicit encoding error for invalid content.
- [ ] **Step 4: Implement** atomic write/rename with a temporary sibling file and replace operation, followed by manifest persistence.
- [ ] **Step 5: Run** `cd desktop/src-tauri; cargo test`; expect PASS.
- [ ] **Step 6: Commit** `feat(desktop): add safe local notebook state`.

### Task 6: Implement the bidirectional sync engine and watcher

**Files:**
- Modify: `desktop/src-tauri/src/sync/mod.rs`, `desktop/src-tauri/src/fs.rs`, `desktop/src-tauri/src/lib.rs`
- Create: `desktop/src-tauri/src/sync/diff.rs`
- Create: `desktop/src-tauri/src/sync/queue.rs`
- Create: `desktop/src-tauri/src/sync/merge.rs`
- Test: `desktop/src-tauri/src/sync/diff.rs`, `desktop/src-tauri/src/sync/queue.rs`, `desktop/src-tauri/src/sync/merge.rs`

**Commands/events:**

```text
select_sync_folder() -> SyncFolder
preview_sync(notebook_id, folder) -> SyncPreview
start_sync(binding) -> SyncStatus
sync_now(binding) -> SyncReport
pause_sync(binding) -> SyncStatus
resume_sync(binding) -> SyncStatus
resolve_conflict(conflict_id, resolution) -> SyncReport
```

Emit `sync://status`, `sync://progress`, `sync://conflict`, and `sync://error` events to Vue. The watcher uses `notify`, debounces bursts for 500 ms, ignores client-generated writes, then rescans and reconciles.

- [ ] **Step 1: Write failing Rust tests** for initial remote pull, initial local upload, equal state, local-only create/update/rename/delete, remote-only changes, stale cursor recovery, offline queueing, retry after restart, and duplicate event coalescing.
- [ ] **Step 2: Implement** a preview diff with explicit actions `download`, `upload`, `keep_local`, `keep_remote`, and `conflict`; no file is changed during preview.
- [ ] **Step 3: Implement** ordered reconciliation: create folders, create/update notes, apply renames/moves by node ID, then process deletes through the recoverable conflict/trash path.
- [ ] **Step 4: Implement** the durable operation queue with exponential retry, operation IDs, server cursor persistence, pause/resume, and crash-safe state writes.
- [ ] **Step 5: Implement** the three-way merge and conflict artifact rules from the decision record; exclude conflict artifacts from scanning.
- [ ] **Step 6: Run** `cd desktop/src-tauri; cargo test`; expect PASS.
- [ ] **Step 7: Commit** `feat(desktop): add bidirectional markdown sync engine`.

## Workstream 3 — Desktop UX and integration

### Task 7: Add notebook binding and sync controls

**Files:**
- Create: `frontend/src/services/noteSync.js`
- Create: `frontend/src/composables/useNoteSync.js`
- Create: `frontend/src/views/NoteSync.vue`
- Create: `frontend/src/components/notes/NoteSyncDialog.vue`
- Modify: `frontend/src/views/Notes.vue`, `frontend/src/views/NotebookFileManage.vue`, `frontend/src/router/index.js`
- Test: `frontend/src/views/note-sync-regressions.test.mjs`

**Interface:**

Vue calls Tauri commands through one service boundary. `useNoteSync(notebookId)` exposes `binding`, `status`, `preview`, `conflicts`, `loading`, `error`, `selectFolder`, `preview`, `start`, `pause`, `resume`, `syncNow`, and `resolveConflict`.

- [ ] **Step 1: Write failing Node tests** for owner-only binding visibility, first-sync confirmation, rendering a preview without writes, status transitions, error preservation, retry, and conflict resolution.
- [ ] **Step 2: Implement** the service/composable and listen to the four sync events; unregister listeners when the view unmounts.
- [ ] **Step 3: Build** the binding dialog with folder selection, notebook identity, local/remote counts, per-item action, explicit delete confirmation, and a final “开始同步” action.
- [ ] **Step 4: Add** notebook-level entry points and a dedicated route without exposing sync controls to viewer/editor members.
- [ ] **Step 5: Run** `cd frontend; node --test src/views/note-sync-regressions.test.mjs` and `npm run build`; expect PASS.
- [ ] **Step 6: Commit** `feat(notes): add desktop sync controls`.

### Task 8: Add end-to-end Windows acceptance coverage

**Files:**
- Create: `.harness/desktop-note-sync-runner.mjs`
- Create: `.harness/fixtures/note-sync-fixture.json`
- Modify: `.harness/completion-ledger.json`
- Test: `backend/tests/test_note_sync_api.py`, `frontend/src/views/note-sync-regressions.test.mjs`, Rust tests

- [ ] **Step 1: Create** an authenticated fixture with one notebook containing nested folders, a Markdown note, and a collaborator session.
- [ ] **Step 2: Add** the strict flow: bind empty folder, preview remote download, edit local file, observe upload, edit web note, observe local pull, create a conflict, resolve it, restart the client, and verify the queue/cursor.
- [ ] **Step 3: Assert** no server path leaks to the client, no duplicate operation is applied, no horizontal overflow exists, and no unexpected console/request error appears.
- [ ] **Step 4: Run** the flow at `1024x900` and `1440x1000`, then run mobile web regression flows separately at `375x812` and `768x1024`.
- [ ] **Step 5: Commit** `test(desktop): add note sync acceptance flow`.

## Workstream 4 — Windows release hardening

### Task 9: Package, update, and document the client

**Files:**
- Create: `.github/workflows/build-windows-release.yml`
- Modify: `desktop/src-tauri/tauri.conf.json`, `desktop/package.json`, `docs/API.md`
- Create: `docs/windows-note-sync.md`
- Test: `scripts/build-desktop.ps1`, version check, CI artifact inspection

- [ ] **Step 1: Add** a Windows workflow that installs Node/Rust, runs frontend/backend contract tests, builds NSIS/MSI artifacts, and publishes them only when the workflow is green.
- [ ] **Step 2: Configure** Tauri updater metadata and a visible release channel; an update must never replace the user-selected folder or `.lifequest` manifest.
- [ ] **Step 3: Document** folder mapping, first-sync preview, conflict files, ignored paths, permissions, recovery, and uninstall behavior.
- [ ] **Step 4: Run** `cd frontend; npm run check:version; npm run build`, `cd backend; pytest -q`, `cd desktop; npm run build`, and `git diff --check`.
- [ ] **Step 5: Inspect** the generated NSIS/MSI contents to confirm the app contains no backend database, `notes_data`, uploads, or local secrets.
- [ ] **Step 6: Commit** `chore(desktop): package and document windows client`.

## MVP acceptance criteria

- A user can select one local directory and bind it to an owned notebook.
- First sync presents a per-item preview and does not delete without explicit confirmation.
- Creating/editing/renaming/moving a Markdown note on either side converges to the same tree after `sync_now`.
- Same-file concurrent edits create a recoverable conflict; neither version disappears.
- Restarting the client preserves the cursor, manifest, queue, and binding.
- A retry with the same operation ID does not duplicate a note or reward.
- Web collaborative editing receives external desktop writes through the existing Yjs room contract.
- Invalid paths, symlink/reparse-point escapes, non-UTF-8 files, and unauthorized notebooks fail with actionable errors.

## Explicitly excluded from MVP

- Image and attachment synchronization.
- Running the FastAPI backend or SQLite database inside the Windows client.
- Full offline editing with a local replica of every LifeQuest domain.
- Silent last-write-wins conflict behavior.
- Syncing arbitrary file types or the server's private storage directories.
- System tray background sync and OS startup registration; these are separate release increments after the core flow is stable.

## Self-review

- The server protocol is independent of Tauri, so a future macOS/Linux shell or CLI can reuse it.
- Stable node IDs and a local manifest cover rename/move; content hashes and base revisions cover external edits.
- Change events cover deletes that a full manifest alone cannot distinguish from never-existing files.
- The plan preserves current note APIs and Yjs behavior by routing external writes through `NoteService`.
- The first-sync preview and conflict artifacts provide recovery before any destructive behavior is enabled.
