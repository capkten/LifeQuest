# LifeQuest Current Issues Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five issues identified in `docs/superpowers/reports/2026-05-27-lifequest-current-issues.md` without introducing regressions in auth, todos, profile editing, or achievements.

**Architecture:** The fixes are concentrated in three areas: todo reward completion flow, auth/profile identity handling, and achievement trigger wiring. Keep changes incremental and compatible with the current FastAPI + SQLAlchemy backend and Vue 3 frontend, with backend tests added first and frontend validation done through build plus manual verification.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Pydantic, pytest, Vue 3, Pinia, Axios, Vite

---

## Scope And File Map

### Backend files likely to change
- `backend/app/api/auth.py`: token subject parsing and current-user lookup
- `backend/app/api/todos.py`: todo and subtask endpoint behavior
- `backend/app/api/users.py`: profile update error mapping
- `backend/app/services/auth.py`: token payload helper behavior if needed
- `backend/app/services/todo.py`: idempotent completion logic and achievement trigger calls
- `backend/app/services/user.py`: uniqueness validation before update
- `backend/app/services/achievement.py`: reusable unlock entrypoints and reward awarding consistency
- `backend/app/repositories/user.py`: optional helper queries if service-level validation needs them
- `backend/app/schemas/todo.py`: subtask response contract normalization if frontend keeps using `status`
- `backend/app/schemas/user.py`: token/user update support types if needed
- `backend/app/models/todo.py`: only if subtask state contract needs a computed compatibility field, not a schema change

### Frontend files likely to change
- `frontend/src/services/todo.js`: subtask API paths and payload mapping
- `frontend/src/views/Todos.vue`: subtask rendering, completion, and progress calculation
- `frontend/src/views/EditProfile.vue`: profile update success path and field-level error handling
- `frontend/src/stores/auth.js`: keep login state stable after profile update if token refresh is introduced
- `frontend/src/services/auth.js`: token refresh or post-update user fetch flow if needed

### Tests to add or update
- `backend/tests/test_todos.py`
- `backend/tests/test_auth.py`
- Add `backend/tests/test_users.py` if profile-update coverage does not fit cleanly in existing auth tests
- Add `backend/tests/test_achievements.py` if achievement trigger scenarios need isolated assertions

### Validation commands
- `cd backend && pytest`
- `cd frontend && npm run build`

---

### Task 1: Establish Regression Baseline

**Files:**
- Read: `docs/superpowers/reports/2026-05-27-lifequest-current-issues.md`
- Read: `backend/tests/test_todos.py`
- Read: `backend/tests/test_auth.py`
- Read: `frontend/src/services/todo.js`
- Read: `frontend/src/views/Todos.vue`

- [ ] Reproduce the five report items locally and record actual behavior, response codes, and any gaps between the report and current code.
- [ ] Confirm whether the frontend currently calls any non-existent subtask endpoints during manual use of the todos page.
- [ ] Confirm whether achievement rows are seeded in the local database before business actions run.
- [ ] Keep a short implementation log in the PR description or working notes so each fix can be traced to a concrete failing case.

**Exit criteria:**
- Every issue in the report has a confirmed reproduction path or a code-level confirmation.
- The dev implementing the fix knows which issue is backend-only, frontend-only, or cross-stack.

---

### Task 2: Fix Reward Idempotency For Habit, Task, And Goal Completion

**Files:**
- Modify: `backend/app/services/todo.py`
- Modify: `backend/app/api/todos.py` only if response codes/messages need adjustment
- Test: `backend/tests/test_todos.py`

- [ ] Add failing backend tests that call each completion endpoint twice and assert rewards are only granted once.
- [ ] Cover all three resource types separately:
  - task completion should not double-add `coins` or `experience`
  - goal completion should not double-add `coins` or `experience`
  - habit completion should not increment streak or rewards repeatedly within the protected completion rule
- [ ] Decide and document the intended idempotent behavior:
  - recommended for `task` and `goal`: second completion request returns `200` with unchanged completed entity
  - recommended for `habit`: if the product intends "once per day", second completion on the same day should return `400`; if no date tracking is added now, at minimum block repeated reward grants in the same completed state
- [ ] Implement service-level guards before reward updates:
  - if `task.status == completed`, do not mutate rewards again
  - if `goal.status == completed`, do not mutate rewards again
  - for `habit`, add an explicit completion marker the service can inspect, or introduce a same-day completion check if that data already exists elsewhere
- [ ] Keep reward updates and state updates in one transaction so partial success cannot mark completion without rewards or rewards without completion.
- [ ] Run focused tests first, then full `pytest`.

**Acceptance criteria:**
- Repeated requests cannot farm coins or experience.
- Existing one-time completion behavior still works for first-time completions.
- No unauthorized or 404 behavior regresses for completion endpoints.

**Risk note:**
- Habit idempotency is the only fix in this set that may require a data-model decision. If the product requirement is "habit can be completed once per day", dev should add an explicit timestamp or daily-completion record instead of relying on `streak` alone.

---

### Task 3: Align Subtask API Contract Between Frontend And Backend

**Files:**
- Modify: `frontend/src/services/todo.js`
- Modify: `frontend/src/views/Todos.vue`
- Modify: `backend/app/api/todos.py` if compatibility aliases are added
- Modify: `backend/app/schemas/todo.py` if frontend-facing response mapping is normalized
- Test: `backend/tests/test_todos.py`

- [ ] Add a backend test that creates a task, creates a subtask under that task, lists subtasks by task, updates a subtask to completed, and verifies the response shape.
- [ ] Replace incorrect frontend endpoint calls:
  - `GET /todos/goals/{goalId}/subtasks` must be changed to the actual backend path or the backend must expose a compatibility route
  - `POST /todos/goals/{goalId}/subtasks` must be changed to the actual backend path or the backend must expose a compatibility route
  - `POST /todos/subtasks/{subtaskId}/complete` currently has no backend route and must be implemented or replaced with `PUT /todos/subtasks/{subtaskId}`
- [ ] Remove the current goal/task terminology mismatch. Recommended approach:
  - keep backend domain model as `task -> subtasks`
  - update frontend state naming from `goalSubtasks` to task-scoped naming where practical
  - if UI is visually nested under goal cards, map the data intentionally instead of calling nonexistent goal-subtask APIs
- [ ] Normalize subtask completion contract. Recommended approach:
  - backend remains source of truth with `is_completed`
  - frontend maps `is_completed` to a local derived `status` only for display
  - do not introduce parallel backend fields `status` and `is_completed` unless backward compatibility forces it
- [ ] Add a clear subtask completion action:
  - either add `PUT /api/todos/subtasks/{id}` with `{"is_completed": true}`
  - or add a dedicated `POST /api/todos/subtasks/{id}/complete` endpoint
  - choose one and update all frontend callers to match it
- [ ] Verify the todos page can load, expand subtasks, complete subtasks, and recompute progress without console errors.

**Acceptance criteria:**
- Subtasks can be listed, created, completed, and deleted from the UI.
- No frontend code depends on nonexistent goal-subtask routes.
- The response field used by the UI is consistent everywhere.

**Decision note:**
- The cleanest short-term fix is to update the frontend to the backend contract and add one dedicated backend completion route. Avoid fabricating "goal subtasks" unless the product model is being redesigned.

---

### Task 4: Make Auth Identity Stable When Username Changes

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/services/auth.py` only if token helpers are adjusted
- Modify: `backend/app/schemas/user.py` if token payload types are made explicit
- Modify: `frontend/src/views/EditProfile.vue`
- Modify: `frontend/src/stores/auth.js` if a refreshed token must be stored after profile update
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/test_users.py` or `backend/tests/test_auth.py`

- [ ] Add a failing backend test that:
  - registers and logs in a user
  - updates the username through `/api/users/me`
  - calls `/api/users/me` again with the original token
  - asserts the request still succeeds
- [ ] Change JWT subject usage from mutable username to immutable user identifier. Recommended approach:
  - login writes `sub = str(user.id)`
  - `get_current_user()` parses `sub` as user id and fetches by `id`
- [ ] Keep username-based login unchanged at the credential entry step. Only the token identity should switch to user id.
- [ ] Check whether existing local tokens become invalid after deployment. If yes, document that a forced re-login is expected once after release.
- [ ] Verify profile update flow on the frontend:
  - successful username change should not trigger logout
  - `authStore.fetchUser()` should refresh the renamed username correctly
- [ ] If the implementation decides to rotate token on profile update, make sure the frontend stores the new token before calling `fetchUser()`. Otherwise, do not introduce token rotation unnecessarily.

**Acceptance criteria:**
- Username change no longer breaks the current session.
- Login continues to accept username and password as before.
- Token validation uses immutable identity.

---

### Task 5: Return Validation Errors Instead Of 500 For Duplicate Username Or Email

**Files:**
- Modify: `backend/app/services/user.py`
- Modify: `backend/app/api/users.py`
- Optionally modify: `backend/app/repositories/user.py`
- Test: `backend/tests/test_users.py` or `backend/tests/test_auth.py`
- Optional frontend adjustment: `frontend/src/views/EditProfile.vue`

- [ ] Add failing tests for updating the current user with:
  - another existing user's username
  - another existing user's email
  - unchanged current values to confirm no false-positive conflict
- [ ] Add service-layer uniqueness checks before `repository.update()`:
  - if `username` is changing, reject when another user already owns it
  - if `email` is changing, reject when another user already owns it
  - skip conflict errors when the value belongs to the same current user
- [ ] Convert service conflict failures into explicit `HTTPException(status_code=400)` or `409` in the API layer. Recommendation:
  - use `400` only if consistency with current register endpoint matters more
  - use `409 Conflict` if the team wants semantically correct uniqueness errors
- [ ] Return stable, user-readable error messages such as `Username already exists` and `Email already exists`.
- [ ] Keep the frontend catch block simple; it can continue surfacing `err.response.data.detail` once the backend returns deterministic messages.

**Acceptance criteria:**
- Duplicate username/email update attempts do not raise 500.
- The response tells the frontend which conflict occurred.
- Updating unrelated fields, such as avatar only, still succeeds.

---

### Task 6: Trigger Achievement Unlocks From Real Business Events

**Files:**
- Modify: `backend/app/services/achievement.py`
- Modify: `backend/app/services/todo.py`
- Optionally modify: `backend/app/repositories/user.py`
- Test: `backend/tests/test_achievements.py`
- Test: `backend/tests/test_todos.py`

- [ ] Add failing tests for at least these scenarios:
  - first completed task unlocks the `task_count = 1` achievement
  - completing enough experience to level up can unlock the `level = 5` achievement when the threshold is reached
  - rewarding coins contributes to `coins_earned` according to the intended definition
- [ ] Clarify the business definition of each seeded achievement before implementation:
  - `task_count`: count of completed tasks
  - `habit_streak`: best streak or current streak
  - `level`: current user level
  - `coins_earned`: cumulative lifetime earned coins, not current balance, unless product explicitly wants current balance
- [ ] Add explicit trigger calls from the business flows that actually change the relevant counters. Minimum expected hookup:
  - task completion should invoke achievement checks for `task_count`
  - habit completion should invoke checks for `habit_streak`
  - reward updates or level changes should invoke checks for `level` and `coins_earned` if those counters are available
- [ ] Avoid adding achievement logic only in the API layer. Keep it in services so future callers cannot bypass unlock checks.
- [ ] Review reward awarding in `AchievementService.check_and_unlock()` because it currently commits coin and experience rewards separately through repository helpers. Ensure unlock + reward grant stays transactionally safe enough to avoid duplicate partial grants.
- [ ] Verify `/api/achievements/me` returns unlocked items after the triggering action.

**Acceptance criteria:**
- Achievements are not just seeded; they become unlockable through real actions.
- Unlocking an achievement grants it once.
- Achievement rewards do not double-apply if the same condition is checked again.

**Risk note:**
- `coins_earned` may require a new persisted cumulative counter if the current schema only stores current balance. If so, dev should scope that schema change explicitly instead of inferring from `coins`.

---

### Task 7: Full Regression Verification And Release Notes

**Files:**
- Update as needed: test files touched above
- Optional docs update: `docs/superpowers/reports/2026-05-27-lifequest-current-issues.md` or release notes

- [ ] Run full backend test suite with `cd backend && pytest`.
- [ ] Run frontend production build with `cd frontend && npm run build`.
- [ ] Manually verify these UI flows:
  - edit username and remain logged in
  - duplicate username/email shows clear error
  - create and complete a task once, then repeat completion and verify no extra rewards
  - open todo page subtask section and complete a subtask successfully
  - complete the first task and check whether achievements appear in profile or achievement view
- [ ] Document any intentional behavior changes:
  - token subject migrated from username to user id
  - repeated completion requests now idempotent or rejected
  - subtask API contract standardized
- [ ] If existing tokens are invalidated by the auth fix, include one explicit release note for frontend and QA.

**Acceptance criteria:**
- The five reported defects are closed with automated or manual verification evidence.
- The team has a short release-risk note for token migration and any habit-completion rule change.

---

## Recommended Execution Order

1. Task 2: reward idempotency
2. Task 3: subtask contract alignment
3. Task 4: stable auth identity
4. Task 5: duplicate profile validation
5. Task 6: achievement triggers
6. Task 7: full regression verification

## Priority Summary

- P0: Task 2 reward idempotency
- P0: Task 3 subtask contract alignment
- P1: Task 4 stable auth after username change
- P1: Task 5 duplicate profile update validation
- P1: Task 6 achievement trigger wiring

## Open Decisions For The Implementing Developer

- Whether habit completion should become strictly "once per day" now, which likely requires persisted completion timing.
- Whether duplicate profile conflicts should return `400` for consistency or `409` for semantics.
- Whether to add a dedicated subtask complete endpoint or standardize on update semantics.
- Whether `coins_earned` needs a new cumulative persisted field.
