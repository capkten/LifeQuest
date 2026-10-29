# LifeQuest Product Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make LifeQuest useful as a daily execution system before expanding more cultivation content: one reliable place to see today's work, act on it, connect it to notes and projects, and review progress.

**Architecture:** Keep the existing task, habit, goal, calendar, project, and notebook APIs authoritative. Add a server-computed action-center read model instead of duplicating business rules in Vue, then add recurrence and note relationships as small domain modules. The Windows client sync is a separate plan because it has a native filesystem trust and release surface.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3, Vite, existing Node `node:test` regression tests, Asia/Shanghai date handling.

## Global Constraints

- The repository-root `VERSION` file is the only project version source; run `cd frontend && npm run sync:version` after a release increment.
- Daily completion and action-center dates use the `Asia/Shanghai` calendar boundary.
- Existing mortal and immortal data remains intact; new read models must not change reward or ascension semantics.
- The backend returns authoritative status, due dates, lock reasons, and reward deltas; Vue does not reconstruct business state from partial fields.
- Every write is protected by a transaction, a database uniqueness constraint, or an idempotency key.
- Every feature starts with a failing test and is verified with focused tests, the frontend build, and strict browser checks at `375x812`, `768x1024`, `1024x900`, and `1440x1000`.
- Do not add a reminder daemon to the web backend; desktop notifications belong to the Windows client plan.

## Current Baseline

- `Task` already has `deadline`, `start_date`, `priority`, project links, and completion rewards.
- `Habit` already has daily/weekly/monthly frequency and China-local completion protection.
- `/api/todos/daily` and `/api/calendar/events` expose partial daily data, but they do not provide one ordered action queue.
- The calendar is read-only: it displays due tasks, goals, habits, and check-ins but has no event creation or rescheduling workflow.
- Notes already use stable node UUIDs, materialized paths, `content_revision`, `base_revision`, atomic writes, and Yjs collaboration.

## Product Order

1. Stabilize the existing mobile and notebook interaction contracts already tracked in the repository.
2. Ship the daily action center and quick completion flow.
3. Add recurring tasks, snooze/postpone, and calendar rescheduling.
4. Connect notes, tasks, goals, and projects with explicit links.
5. Add a weekly review surface and only then deepen reward economy and optional finance/immortal content.

---

## Workstream 1 — Daily action center

### Task 1: Define the authoritative today contract

**Files:**
- Create: `backend/app/schemas/action_center.py`
- Create: `backend/app/services/action_center.py`
- Create: `backend/app/api/action_center.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_action_center.py`

**Interface:**

`ActionCenterService.get_today(user_id: UUID, target_date: date | None) -> TodayActionCenter` returns:

```json
{
  "date": "2026-08-31",
  "timezone": "Asia/Shanghai",
  "summary": {
    "open_count": 3,
    "overdue_count": 1,
    "completed_count": 2,
    "habit_due_count": 2,
    "habit_completed_count": 1
  },
  "sections": {
    "overdue": [{"kind": "task", "id": "...", "title": "...", "action": "complete"}],
    "today": [{"kind": "task", "id": "...", "title": "...", "action": "complete"}],
    "habits": [{"kind": "habit", "id": "...", "title": "...", "action": "complete"}],
    "calendar": [{"kind": "goal", "id": "...", "title": "...", "action": "open"}]
  },
  "next_action": {"kind": "task", "id": "...", "title": "..."}
}
```

- [ ] **Step 1: Write failing backend tests** for user isolation, China-local midnight, overdue ordering, completed-item exclusion from open sections, weekly/monthly habit due dates, and an empty-day response.
- [ ] **Step 2: Run the focused test** with `cd backend; pytest tests/test_action_center.py -q`; expect failures because the endpoint and schema do not exist.
- [ ] **Step 3: Implement** `GET /api/action-center/today` using one service-level query composition. Order overdue items by deadline, then today's items by priority and deadline, then choose `next_action` from the first actionable item.
- [ ] **Step 4: Run** `cd backend; pytest tests/test_action_center.py -q`; expect all focused tests to pass.
- [ ] **Step 5: Commit** `feat(action-center): add authoritative daily action contract`.

### Task 2: Build the home action surface

**Files:**
- Create: `frontend/src/services/actionCenter.js`
- Create: `frontend/src/components/home/TodayActionCenter.vue`
- Modify: `frontend/src/views/Home.vue`
- Test: `frontend/src/views/action-center-regressions.test.mjs`

**Interface:**

`TodayActionCenter.vue` consumes the `TodayActionCenter` response and emits `complete`, `open`, and `retry`. It must expose visible loading, error, empty, completing, and success states without replacing failed data with an empty list.

- [ ] **Step 1: Write failing Node tests** that assert the service calls `/action-center/today`, failed refresh preserves prior data, duplicate completion clicks emit one request, and an empty day still exposes a create-task action.
- [ ] **Step 2: Implement** the service wrapper and component with the existing `todoService`, `calendarService`, `useToast`, and `getErrorMessage` conventions.
- [ ] **Step 3: Replace** the current home task/goal-only summary with the action center while retaining cultivation status, check-in, and reward feedback.
- [ ] **Step 4: Run** `cd frontend; node --test src/views/action-center-regressions.test.mjs`; expect PASS.
- [ ] **Step 5: Run** `cd frontend; npm run build`; expect a successful Vite build.
- [ ] **Step 6: Commit** `feat(home): add today action center`.

## Workstream 2 — Repeatable work and scheduling

### Task 3: Add recurrence and occurrence records

**Files:**
- Create: `backend/app/models/task_schedule.py`
- Create: `backend/app/schemas/task_schedule.py`
- Create: `backend/app/services/task_schedule.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/main.py`, `backend/app/api/todos.py`, `backend/app/schemas/todo.py`
- Test: `backend/tests/test_task_schedule.py`, `backend/tests/test_todos.py`

**Data contract:**

- `TaskSchedule` stores `task_id`, `rule_type` (`daily`, `weekly`, `monthly`), `interval`, `weekdays_json`, `day_of_month`, `starts_on`, `ends_on`, `timezone`, and `is_active`.
- `TaskOccurrence` stores `task_id`, `occurrence_date`, `status`, `snoozed_until`, `completed_at`, and `source_key`; `(task_id, occurrence_date)` is unique.
- One-off tasks keep their current behavior. A recurring task is a template; completion rewards use `task:{id}:{occurrence_date}` so each occurrence pays once.

- [ ] **Step 1: Write failing tests** for daily/weekly/monthly generation, end dates, invalid weekday/month-day input, same-day repeated completion, snooze visibility, and post-ascension reward continuity.
- [ ] **Step 2: Run** `cd backend; pytest tests/test_task_schedule.py -q`; expect failures.
- [ ] **Step 3: Implement** deterministic occurrence generation in `TaskScheduleService.materialize_until(user_id, target_date)` and call it from the action-center read path and task completion path.
- [ ] **Step 4: Extend** task create/update schemas and routes with `schedule`; keep old payloads valid and keep the existing reward settlement path.
- [ ] **Step 5: Run** `cd backend; pytest tests/test_task_schedule.py tests/test_todos.py -q`; expect PASS.
- [ ] **Step 6: Commit** `feat(todos): add repeatable task occurrences`.

### Task 4: Add postpone and calendar rescheduling

**Files:**
- Modify: `backend/app/schemas/todo.py`, `backend/app/api/todos.py`, `backend/app/services/todo.py`, `backend/app/services/calendar.py`
- Modify: `frontend/src/services/todo.js`, `frontend/src/views/Todos.vue`, `frontend/src/views/Calendar.vue`
- Test: `backend/tests/test_calendar_stats.py`, `backend/tests/test_todos.py`, `frontend/src/views/calendar-regressions.test.mjs`

**Interface:**

- `POST /api/todos/tasks/{task_id}/snooze` accepts `{ "until": "2026-09-01T09:00:00+08:00" }` and returns the updated occurrence/task state.
- `PATCH /api/todos/tasks/{task_id}/schedule` accepts a new deadline or occurrence date and returns the authoritative calendar item.
- Completed items cannot be silently moved; the service returns `TASK_ALREADY_COMPLETED`.

- [ ] **Step 1: Write failing tests** for postpone, reschedule, invalid past dates, completed-item rejection, user isolation, and idempotent repeated requests.
- [ ] **Step 2: Implement** the service operations with the existing task ownership checks and a request key derived from task/occurrence/date.
- [ ] **Step 3: Update** calendar day detail to include an actionable item type and the target route/id rather than only display strings.
- [ ] **Step 4: Add** a task edit/reschedule action in `Calendar.vue` and a snooze menu in `Todos.vue`, including loading, failure, retry, and success states.
- [ ] **Step 5: Run** focused backend/frontend tests and the four-viewport calendar flow through the strict browser runner.
- [ ] **Step 6: Commit** `feat(calendar): support rescheduling and snoozing`.

## Workstream 3 — Notes and execution context

### Task 5: Add explicit note links to tasks, goals, and projects

**Files:**
- Create: `backend/app/models/note_link.py`
- Create: `backend/app/schemas/note_link.py`
- Create: `backend/app/services/note_link.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/main.py`, `backend/app/api/notes.py`, `backend/app/api/todos.py`, `backend/app/api/projects.py`
- Modify: `frontend/src/services/note.js`, `frontend/src/services/todo.js`, `frontend/src/services/project.js`, `frontend/src/views/NoteEditor.vue`, `frontend/src/views/Todos.vue`, `frontend/src/views/ProjectDetail.vue`
- Test: `backend/tests/test_note_links.py`, `frontend/src/views/note-link-regressions.test.mjs`

**Data contract:**

Use separate association tables for task-note, goal-note, and project-note links so foreign-key ownership checks remain explicit. Each table has a unique pair constraint and `created_at`; delete is unlinking, not note deletion.

- [ ] **Step 1: Write failing tests** for link creation, duplicate rejection, cross-user rejection, unlinking, note deletion cleanup, and returned summary fields.
- [ ] **Step 2: Implement** the model/service/API layer with notebook access checks and target ownership checks.
- [ ] **Step 3: Add** `GET /api/notes/{note_id}/links` and target-specific link endpoints returning `{kind, id, title, url}`.
- [ ] **Step 4: Add** “关联任务/项目/目标” controls to the editor and “打开关联笔记” controls to task/project views.
- [ ] **Step 5: Run** `cd backend; pytest tests/test_note_links.py -q`, `cd frontend; node --test src/views/note-link-regressions.test.mjs`, and `npm run build`.
- [ ] **Step 6: Commit** `feat(notes): connect notes with execution objects`.

### Task 6: Add a weekly review read model

**Files:**
- Create: `backend/app/schemas/review.py`
- Create: `backend/app/services/review.py`
- Create: `backend/app/api/review.py`
- Create: `frontend/src/services/review.js`
- Create: `frontend/src/views/WeeklyReview.vue`
- Modify: `backend/app/main.py`, `frontend/src/router/index.js`, `frontend/src/components/layout/Sidebar.vue`
- Test: `backend/tests/test_review.py`, `frontend/src/views/review-regressions.test.mjs`

**Interface:**

`GET /api/review/weekly?week_start=YYYY-MM-DD` returns completed/open/overdue counts, habit streak changes, reward deltas, unfinished high-priority work, linked projects with no next action, and three server-generated suggestions. It is derived data; no durable review table is needed for the first release.

- [ ] **Step 1: Write failing tests** for week boundaries, user isolation, China-local timestamps, no-data output, and stable suggestion ordering.
- [ ] **Step 2: Implement** the service from task occurrences, habits, projects, and reward ledgers without copying frontend calculations.
- [ ] **Step 3: Build** the review page with retryable loading/error states and direct links to overdue tasks, projects, and notes.
- [ ] **Step 4: Run** focused tests, `npm run build`, and strict browser checks at all four viewports.
- [ ] **Step 5: Commit** `feat(review): add weekly execution review`.

## Release gate

- [ ] Run `cd backend; pytest -q` with zero failures.
- [ ] Run the focused frontend Node tests plus `cd frontend; npm run build`.
- [ ] Run `git diff --check`, Python compilation, and strict browser flows with authenticated fixtures.
- [ ] Update `docs/superpowers/reports/2026-08-31-lifequest-product-loop-verification.md` with exact commands, screenshots, known warnings, and residual risks.
- [ ] Increment `VERSION` only for the release that contains the approved user-visible changes, then run `cd frontend; npm run sync:version`, `npm run check:version`, and `npm run build`.

## Self-review

- The plan keeps the existing reward, ascension, notebook revision, and timezone contracts intact.
- Recurrence has a unique occurrence key, so repeated clicks cannot pay twice.
- Calendar editing reuses task ownership and update semantics rather than introducing a second task store.
- Note links use explicit association tables, avoiding a polymorphic foreign-key field.
- Windows filesystem work is intentionally excluded from this plan and is specified separately.
