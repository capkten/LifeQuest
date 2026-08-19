# Task 2 Rework Report

Date: 2026-08-19
Model: gpt-5.6-luna
Evaluation: strict Playwright

## Scope

- Added startup migration for `user_achievements(user_id, achievement_id)`.
- Added startup migration for `coin_transactions(user_id, source, source_id)`.
- Legacy duplicate policy is deterministic: keep the lowest `id` for each exact key.
- Deduplication only considers rows where every key column is non-null. Existing nullable rows, including repeated `source_id IS NULL` ledger rows, remain untouched.
- Existing SQLite databases receive idempotent unique indexes; fresh schemas continue to use the existing ORM unique definitions.
- Added exact achievement row and achievement-ledger assertions after repeated threshold checks.
- Added distinct-process/session coverage for achievement threshold checks and task, habit, and goal completion. Each source is asserted to settle once, with one coin transaction and one cultivation log.

## TDD Evidence

RED command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_startup_config.py::test_startup_migrates_reward_idempotency_constraints_deterministically tests/test_achievements.py::test_achievement_does_not_double_unlock tests/test_regressions.py::test_achievement_threshold_race_uses_database_constraint_not_process_lock tests/test_regressions.py::test_distinct_process_completion_claims_one_settlement_per_source -q
```

Result before implementation: `2 failed, 4 passed`. The migration test retained both duplicate legacy achievement rows, and the process race exposed the missing database constraint as a SQLite lock failure.

GREEN command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_startup_config.py::test_startup_migrates_reward_idempotency_constraints_deterministically tests/test_regressions.py::test_achievement_threshold_race_uses_database_constraint_not_process_lock tests/test_regressions.py::test_distinct_process_completion_claims_one_settlement_per_source -q
```

Result: `5 passed`.

## Verification

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py tests/test_auth.py tests/test_users.py tests/test_achievements.py tests/test_regressions.py tests/test_task12_review_fixes.py tests/test_startup_config.py -q
```

Result: `52 passed, 105 warnings`.

```text
cd frontend
node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs
```

Result: `56 passed, 0 failed`.

```text
cd frontend
npm run build
```

Result: exit code `0`. Existing dependency annotation and bundle-size warnings remain.

```text
node .harness/playwright-runner.mjs
```

Result: `52 checks`, `0 failures`, `0 consoleErrors`, `0 requestFailures`.
Evidence: `.harness/iterations/2026-08-19-task-2-rework/results.json`.

```text
git diff --check
```

Result: passed.

## Remaining Concerns

- The backend suite still emits existing deprecation warnings from FastAPI lifecycle APIs and JWT UTC handling.
- The frontend build retains existing large-chunk and dependency annotation warnings.
- The process tests use SQLite's normal write-lock waiting and retry only test-side transient `database is locked` errors; correctness is provided by the database unique indexes and the service's existing integrity-error path.
