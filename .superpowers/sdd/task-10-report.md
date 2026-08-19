# Closure Task 10 Report

## Status

Implemented Closure Task 10 only. The cultivation reward loop now returns settlement data, advances the current minor stage without changing the major realm, exposes stable overview arrays, and keeps the mortal world reachable for unascended users. Legacy `exp_reward` and `coins_reward` remain supported.

## Changed Files

- `backend/app/services/cultivation.py`
- `backend/app/schemas/cultivation.py`
- `backend/app/services/todo.py`
- `backend/app/schemas/todo.py`
- `backend/tests/test_cultivation.py`
- `backend/tests/test_todos.py`
- `frontend/src/components/layout/Sidebar.vue`
- `frontend/src/views/World.vue`
- `frontend/src/views/cultivation-regressions.test.mjs`

User-owned existing files were preserved and not staged.

## Tests

### TDD red

Command: `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q`

Actual output: `5 failed, 51 passed`.

Command: `cd frontend; node --test src/views/cultivation-regressions.test.mjs`

Actual output: `21 passed, 2 failed`.

### Focused green

Command: `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_reward_uses_difficulty_and_never_writes_negative_resources tests/test_cultivation.py::test_overview_returns_profile_resources_and_stage_progress tests/test_cultivation.py::test_settlement_advances_minor_stage_but_does_not_bypass_tribulation tests/test_cultivation.py::test_settlement_marks_final_stage_ready_without_changing_realm tests/test_todos.py::test_todo_completion_responses_include_cultivation_reward -q`

Actual output: `5 passed, 13 warnings`.

### Regression and build

Command: `cd frontend; node --test src/views/cultivation-regressions.test.mjs`

Actual output: `23 passed, 0 failed`.

Command: `cd frontend; npm run build`

Actual output: exit code `0`; `1959 modules transformed`; Vite reported a successful production build. Existing npm/Rollup chunk-size warnings remain.

Command: `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_concurrent_tribulation_attempts_allow_only_one_daily_attempt -q`

Actual output: `1 passed, 7 warnings`.

Command: `git diff --check`

Actual output: exit code `0`, no output.

## Commit

`d0c0f66`

## Concerns

- The combined cultivation/todo command has an order-sensitive concurrent tribulation test failure: `55 passed, 1 failed`. The same test passes in isolation. It is outside Task 10 and was not changed because it belongs to the explicitly excluded concurrency scope.
- Existing deprecation warnings from FastAPI/HTTPX/Jose and existing Vite/Rollup warnings remain.

## Closure Task 10 Ascended Reward Fix (2026-08-17)

### Status

Fixed the scoped ascended reward regression. `settle_todo_reward` now skips mortal minor-stage threshold progression for `profile.realm_key == "ascended"`, while preserving cultivation, spirit stones, cultivation logs, `RewardSettlement`, and legacy todo rewards. The final-stage helper treats ascended as terminal without accessing `REALM_THRESHOLDS["ascended"]`; ascended settlements do not report mortal tribulation readiness.

### Added Regression Test

`backend/tests/test_todos.py::test_ascended_todo_completion_keeps_rewards_and_does_not_progress_mortal_stage`

TDD red command:

`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py::test_ascended_todo_completion_keeps_rewards_and_does_not_progress_mortal_stage -q`

Actual result: `1 failed`; failure was the expected `KeyError: 'ascended'` at `settle_todo_reward` before the fix.

TDD green command:

`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py::test_ascended_todo_completion_keeps_rewards_and_does_not_progress_mortal_stage -q`

Actual result: `1 passed, 9 warnings`.

### Final Verification

- `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q` -> `57 passed, 67 warnings in 23.61s`
- `cd frontend; node --test src/views/cultivation-regressions.test.mjs` -> `23 passed, 0 failed`
- `cd frontend; npm run build` -> exit code `0`; `1959 modules transformed`; Vite build completed in `17.83s`. Existing npm/Rollup warnings remain.
- `git diff --check` -> exit code `0`, no output.
