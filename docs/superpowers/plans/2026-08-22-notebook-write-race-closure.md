# Notebook Write Race Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure notebook mutations and note selection changes cannot apply stale responses or lose retryable failure context.

**Architecture:** Preserve the existing `useNoteWorkspace` action locks and tree request generation. Add a narrowly scoped selection generation in the composable and a viewer generation in `NotebookFileManage.vue`; asynchronous responses update state only when their captured generation is current. Keep mutation dialogs open on failure and retain their entered values.

**Tech Stack:** Vue 3, JavaScript ES modules, Node `node:test`, Vue compiler template checks, Vite.

## Global Constraints

- Do not change backend routes or note persistence formats.
- Business locks remain clickable; only in-flight requests use native `disabled`.
- Every production behavior change must have a failing test first.
- Preserve existing action-specific locks and retry behavior.
- Validate at 375x812, 768x1024, 1024x900, and 1440x1000 in the strict browser flow.

---

### Task 1: Add failing regression coverage for selection generations

**Files:**
- Modify: `frontend/src/views/ui-regressions.test.mjs`
- Test target: `frontend/src/composables/useNoteWorkspace.js`, `frontend/src/views/NotebookFileManage.vue`

**Interfaces:**
- `useNoteWorkspace` must expose selection state whose latest generation invalidates earlier asynchronous selection work.
- `NotebookFileManage.vue` must guard viewer response writes with a viewer request generation.

- [x] **Step 1: Add a test that requires a selection generation in the workspace composable.**

  Extend the existing notebook stale-response test with an assertion for a distinct selection generation identifier, such as `selectionRequestId`, `selectionSequence`, or `selectionGeneration`, and an equality guard around the selected-note asynchronous work.

- [x] **Step 2: Run the focused test and confirm the new assertion fails for the missing selection generation.**

  Run `node --test frontend/src/views/ui-regressions.test.mjs` from the repository root. Expected result: the existing tests continue to run, and the new assertion fails because the composable has tree-only request generation.

### Task 2: Implement latest-selection protection minimally

**Files:**
- Modify: `frontend/src/composables/useNoteWorkspace.js`
- Modify: `frontend/src/views/NotebookFileManage.vue`

**Interfaces:**
- The composable increments its selection generation whenever `selectNote` changes the selection context.
- Viewer loading/error/detail state is updated only by the current viewer request generation.

- [x] **Step 1: Add the composable selection generation and invalidate it in `selectNote`.**

  Keep `treeRequestId` unchanged. Add a local counter that increments before changing `selectedNoteId` or `currentFolderId`; do not introduce a new network request or public API unless the existing component needs it.

- [x] **Step 2: Add a viewer generation guard around note detail loading.**

  Increment the viewer request generation when the selected note changes. Capture it before loading the note detail, and guard success, error, and `finally` assignments with `requestId === viewerRequestId`.

- [x] **Step 3: Run the focused test and confirm it passes.**

  Run `node --test frontend/src/views/ui-regressions.test.mjs`. Expected result: all tests pass.

### Task 3: Verify mutation dialog retention and build

**Files:**
- Modify only if a failing test identifies a real gap: `frontend/src/views/NotebookFileManage.vue`
- Test: `frontend/src/views/ui-regressions.test.mjs`

- [x] **Step 1: Run the focused notebook mutation and selection tests.**

  Run `node --test frontend/src/views/ui-regressions.test.mjs` and confirm the pending action locks, failed form retention, and latest-response checks pass.

- [x] **Step 2: Run the frontend production build.**

  Run `npm run build` from `frontend`. Expected result: Vite exits successfully; existing bundle-size and dependency warnings may remain documented but are not treated as failures.

- [ ] **Step 3: Run the strict G-11 browser flow at all required viewports.**

  Run the project’s strict runner with the G-11 iteration configuration. Confirm one request per in-flight mutation, retryable inline failure, and final A→B→A content selection without stale overwrite.

- [ ] **Step 4: Commit the completed Task 1 implementation.**

  Commit only the Task 1 test and source changes with message `fix(notes): close notebook write race contracts`.
