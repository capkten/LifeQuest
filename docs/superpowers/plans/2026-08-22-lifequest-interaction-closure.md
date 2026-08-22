# LifeQuest Interaction Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the verified interaction, feedback, layout, cultivation todo, NPC, tribulation, and shop issues while reusing the project's existing Toast and Element Plus dialog mechanisms.

**Architecture:** Keep existing APIs and stores authoritative. Use `useToast` for success/error feedback and `ElMessageBox` for confirmations; add no new global feedback component. Each page owns only its pending state and dialog context, while `getErrorMessage` remains the single translation boundary for backend error strings and stable item categories.

**Tech Stack:** Vue 3 Composition API, Pinia, Element Plus `ElMessage`/`ElMessageBox`, existing Axios services, FastAPI/pytest, Node `node:test`, Vite.

## Global Constraints

- Do not add `useFeedback.js` or `BaseDialog.vue`.
- Business-locked controls remain clickable; only in-flight controls use native `disabled`.
- Backend response state, rewards, and deltas remain authoritative.
- All user-facing stable keys and error strings render Chinese fallbacks.
- Failed operations preserve the current form or action context and allow retry.
- Responsive verification covers 375x812, 768x1024, 1024x900, and 1440x1000.
- Do not change user-wide npm configuration or commit secrets.

---

### Task 1: Verify authentication feedback and close missing error translations

**Files:**
- Modify: `frontend/src/utils/errorMessage.js`
- Modify only if runtime verification proves necessary: `frontend/src/views/Login.vue`, `frontend/src/views/Register.vue`, shared/global style or app shell containing Element Plus host styles
- Test: `frontend/src/views/ui-regressions.test.mjs`, `backend/tests/test_auth.py`

**Interfaces:**
- `getErrorMessage(error, fallback)` must translate exact backend details `sect is locked`, `messenger contact required before trial`, `leave current sect before joining another`, `messenger contact required before meeting NPC`, and related NPC/sect cooldown or capacity details.
- Login and register continue using existing `ElMessage.success/error` calls and preserve form values on failure.

- [ ] **Step 1: Add failing frontend assertions** for all exact backend detail strings and for login/register failure handlers invoking visible feedback.
- [ ] **Step 2: Run** `cd frontend; node --test src/views/ui-regressions.test.mjs`; expect the new unmapped-detail assertions to fail.
- [ ] **Step 3: Add exact Chinese mappings** in `CODE_MESSAGES` and add only the smallest auth feedback fix if browser verification identifies a z-index, mount, or navigation timing defect.
- [ ] **Step 4: Run** the focused Node tests and `cd backend; pytest tests/test_auth.py -q`; expect green.
- [ ] **Step 5: Manually verify** invalid login, duplicate registration, and successful registration in the running app; record whether a code change was needed.
- [ ] **Step 6: Commit** `fix(feedback): translate cultivation errors and verify auth messages`.

### Task 2: Fix notebook action density and note preview spacing

**Files:**
- Modify: `frontend/src/components/notes/NoteTree.vue`
- Modify: `frontend/src/components/notes/NoteViewer.vue`
- Test: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- Desktop tree rows keep the existing hover/focus reveal behavior without changing row geometry.
- Mobile tree rows expose one compact action trigger; the five actions appear in a click/tap menu with the existing event names: `create-folder`, `create-note`, `rename`, `move`, `delete`.

- [ ] **Step 1: Add failing source-contract tests** requiring mobile action-menu behavior, unchanged Chinese aria labels, no permanent five-button mobile row, and `.viewer-content` horizontal/bottom padding.
- [ ] **Step 2: Run** `cd frontend; node --test src/views/ui-regressions.test.mjs`; expect the new assertions to fail.
- [ ] **Step 3: Implement** a row-level mobile action trigger and menu in `NoteTree.vue`; keep desktop `.note-tree__row:hover .note-tree__actions` and `:focus-within` behavior, and close the menu after an emitted action.
- [ ] **Step 4: Change** `.viewer-content` to use theme spacing such as `padding: var(--spacing-xl) var(--spacing-lg)` and add mobile override `padding: var(--spacing-lg) var(--spacing-md)`; preserve overflow wrapping for markdown content.
- [ ] **Step 5: Run** the focused UI tests and `npm run build`; expect green build and no horizontal-overflow regression in the tested source contracts.
- [ ] **Step 6: Commit** `fix(notes): reduce mobile tree action density and pad previews`.

### Task 3: Add completion actions to the cultivation overview

**Files:**
- Modify: `frontend/src/views/Cultivation.vue`
- Modify: `frontend/src/services/todo.js` only if an existing completion wrapper is insufficient
- Modify: `frontend/src/stores/cultivation.js` only if refresh/apply settlement cannot update the authoritative overview
- Test: `frontend/src/views/cultivation-regressions.test.mjs`, `backend/tests/test_todos.py`

**Interfaces:**
- Cultivation overview `today` items already carry `kind` values `habits`, `tasks`, or `goals`, plus the corresponding todo `id` and completion/status fields from `CultivationService.get_overview`.
- Add a page-local dispatcher `completeTodayItem(item)` that calls `todoService.completeHabit`, `completeTask`, or `completeGoal` based on `item.kind`.

- [ ] **Step 1: Add failing frontend tests** requiring an actionable unfinished today item, kind-specific completion service calls, pending suppression, success feedback, and settlement/overview refresh.
- [ ] **Step 2: Run** `cd frontend; node --test src/views/cultivation-regressions.test.mjs`; expect the new assertions to fail.
- [ ] **Step 3: Render** an action button for unfinished items; use server status fields (`completed`, `status`) to determine whether the item is already complete, never infer completion from the title.
- [ ] **Step 4: Implement** `completeTodayItem(item)` with one `completingTodayId`, `getErrorMessage` on failure, `useToast` success/error feedback, `store.applySettlement(updated.cultivation_reward)` when present, and `store.loadOverview()` after success.
- [ ] **Step 5: Add/extend backend regression coverage** proving repeated completion of the same todo does not duplicate cultivation or cross-realm settlement.
- [ ] **Step 6: Run** `cd backend; pytest tests/test_todos.py -q` and the focused cultivation Node tests.
- [ ] **Step 7: Commit** `feat(cultivation): complete today todos from overview`.

### Task 4: Convert sect, NPC, and tribulation actions to actionable feedback

**Files:**
- Modify: `frontend/src/views/Sects.vue`
- Modify: `frontend/src/views/Npcs.vue`
- Modify: `frontend/src/views/Tribulations.vue`
- Modify: `frontend/src/utils/errorMessage.js` if Task 1 leaves additional exact details
- Test: `frontend/src/views/cultivation-regressions.test.mjs`, `frontend/src/views/sects-request-state.test.mjs`, `backend/tests/test_task8_sect_world.py`, `backend/tests/test_cultivation.py`

**Interfaces:**
- Sect actions retain existing service methods and server fields; clicking a business-locked action calls `showError` with a translated reason instead of rendering a persistent explanatory paragraph.
- `meetNpc()` shows success feedback after `cultivationService.meetNpc()` and translated failure feedback while preserving selected `sectKey` and `populationIndex`.
- `attempt()` in `Tribulations.vue` must call `ElMessageBox.confirm` before `cultivationService.attemptTribulation(...)`; cancellation must not submit a request.

- [ ] **Step 1: Add failing frontend tests** for locked sect action feedback, NPC success/error feedback, preserved NPC form state after failure, and tribulation confirmation cancellation/submission.
- [ ] **Step 2: Run** the focused frontend tests and confirm failures.
- [ ] **Step 3: Replace persistent sect lock copy** with click-triggered `showError`/existing feedback while retaining concise status labels and server-authoritative objective data.
- [ ] **Step 4: Update `meetNpc()`** to call `showSuccess('相遇已记录。')` after refresh and `showError(getErrorMessage(...))` on failure; keep the existing pending lock.
- [ ] **Step 5: Add the tribulation confirmation** with a Chinese message containing pill count, success probability, and failure loss; execute the request only after confirmation resolves.
- [ ] **Step 6: Add/adjust backend tests** for stable exact detail strings needed by the frontend mappings; do not change business rules unless a test demonstrates a real API defect.
- [ ] **Step 7: Run** `cd backend; pytest tests/test_task8_sect_world.py tests/test_cultivation.py -q` and all focused frontend tests.
- [ ] **Step 8: Commit** `fix(cultivation): make sect npc and tribulation feedback actionable`.

### Task 5: Move technique purchase confirmation into a modal and fix shop presentation

**Files:**
- Modify: `frontend/src/views/Techniques.vue`
- Modify: `frontend/src/views/Shop.vue`
- Modify: `frontend/src/utils/displayLabels.js` only if the existing item type helper cannot be reused
- Test: `frontend/src/views/cultivation-regressions.test.mjs`, `frontend/src/views/localization-regressions.test.mjs`, `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- Technique purchase uses the existing server preview object (`selectedSlot`) and existing `cultivationService.purchaseSlot(slot.slot_type)`.
- Shop category display uses the existing `labelItemType`/`ITEM_TYPE_LABELS` mapping; category filtering continues to use the raw internal key.

- [ ] **Step 1: Add failing tests** requiring a modal dialog for technique purchase, preserving preview values, retaining the dialog after failure, non-overlapping featured badge layout, and Chinese `consumable` display.
- [ ] **Step 2: Run** the focused frontend tests and confirm failures.
- [ ] **Step 3: Move the existing purchase panel content** into an `ElDialog` or equivalent existing modal pattern; keep `busy` only on the confirm button, close only after success, and preserve failure feedback for retry.
- [ ] **Step 4: Change Shop.vue** to render `labelItemType(item.category)` and category labels through the same helper; keep raw categories for filtering and form submission.
- [ ] **Step 5: Fix featured badge layout** by reserving top space in `.item-card-top` for featured cards on desktop as well as mobile, or by moving the badge into normal flow; verify it never overlaps `.item-card-icon`.
- [ ] **Step 6: Run** all frontend regressions and `npm run build`.
- [ ] **Step 7: Commit** `fix(ui): refine technique purchase and shop cards`.

### Task 6: Run integrated verification and update evidence

**Files:**
- Modify: `docs/superpowers/reports/2026-08-22-lifequest-interaction-closure-verification.md`
- Modify: `.harness/completion-ledger.json` only from actual evidence
- Browser evidence: `.harness/iterations/2026-08-22-interaction-closure/`

- [ ] **Step 1: Run backend focused and full tests:**
  `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_auth.py tests/test_todos.py tests/test_cultivation.py tests/test_task8_sect_world.py -q` then `pytest -q`.
- [ ] **Step 2: Run frontend focused and full regression tests:**
  `cd frontend; node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs src/views/immortal-regressions.test.mjs`.
- [ ] **Step 3: Run** `npm run build` and `git diff --check`.
- [ ] **Step 4: Start local backend with the Python 3.12 environment, inject a process-only `SECRET_KEY`, and start Vite on ports 8000/3000; do not write secrets to files.
- [ ] **Step 5: Manually verify** login/register, note tree, preview, cultivation todo, sect actions, NPC meet, tribulation confirmation, technique modal, and shop cards at all four viewports.
- [ ] **Step 6: Record** exact pass/fail status, console errors, request failures, and horizontal overflow; mark browser items `verified` only with evidence.
- [ ] **Step 7: Commit** `test: verify interaction closure`.

## Self-review checklist

- Authentication is conditional: first verify runtime visibility, then change CSS/app mounting only if reproduced.
- The plan does not create duplicate feedback components.
- The existing technique purchase behavior is not skipped; it is migrated to the requested modal interaction.
- Cultivation `today` items use the existing `kind` and `id` fields, so no new backend endpoint is required.
- Shop filtering uses raw keys while rendering uses Chinese labels.
- Browser claims depend on fresh four-viewport evidence.
