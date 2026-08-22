# Notebook Write Race Closure Design

**Date:** 2026-08-22

**Goal:** Close the notebook workspace race conditions so that rapid selection changes and overlapping mutations cannot leave the tree or viewer showing stale state.

## Scope

This change is limited to the existing notebook workspace. It does not change backend APIs, persistence formats, or unrelated note features.

The existing per-action mutation locks remain authoritative for create, rename, move, and delete. The new behavior adds a separate selection/viewer request generation so a response is applied only when it belongs to the latest selection context.

## Design

`useNoteWorkspace` keeps its existing `treeRequestId` for notebook tree loads and adds a selection generation that increments whenever the selected note or folder changes. `NotebookFileManage.vue` keeps a viewer request generation tied to the selected note. Each asynchronous viewer response captures its generation and may update `viewerNote`, `viewerError`, and `viewerLoading` only when it is still current.

When a mutation fails, the active dialog remains open, its entered values remain unchanged, and the error is rendered inline. The existing action lock prevents a second request while the first is pending. After failure the lock is released, so submitting the same dialog again retries the operation without duplicating the original request.

## Verification

Tests will first reproduce stale selection responses and confirm they fail before the implementation. They will then verify the generation guard, mutation lock behavior, and failed-dialog retention. The focused frontend test file and production build must pass. The strict browser runner must finally cover G-11 at 375x812, 768x1024, 1024x900, and 1440x1000 with request counts, retry behavior, and final selection assertions.

## Non-goals

- No `AbortController` migration.
- No rewrite of the note service or backend routes.
- No changes to the existing notebook data model.
