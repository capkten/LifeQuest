# Task 12 Report

## Scope

Implemented Task 12 only: server-authorized technique learning, spirit-stone and realm gates, idempotent learning, tribulation preview lock reasons, idempotent todo reward events, and the Techniques/TribulationProbability UI states. Task 13-14 were not changed.

## TDD Evidence

RED command:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_user_can_learn_realm_eligible_technique_and_repeat_is_idempotent tests/test_cultivation.py::test_learning_rejects_realm_and_spirit_stone_gates tests/test_cultivation.py::test_tribulation_preview_exposes_lock_reason_for_non_final_stage_and_cooldown tests/test_cultivation.py::test_ascended_tribulation_preview_has_terminal_lock_reason tests/test_todos.py::test_task_reward_log_uses_unique_stable_source_key -q
```

Output: `FFFFF [100%]`; failures were the missing learning route, missing `lock_reason`, and missing `CultivationLog.source_key`.

GREEN command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_user_can_learn_realm_eligible_technique_and_repeat_is_idempotent tests/test_cultivation.py::test_learning_rejects_realm_and_spirit_stone_gates tests/test_cultivation.py::test_tribulation_preview_exposes_lock_reason_for_non_final_stage_and_cooldown tests/test_cultivation.py::test_ascended_tribulation_preview_has_terminal_lock_reason tests/test_todos.py::test_task_reward_log_uses_unique_stable_source_key -q
```

Output: `5 passed`.

## Verification

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Output: `174 passed, 399 warnings in 104.75s (0:01:44)`.

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs
```

Output: `27 passed, 0 failed`.

```powershell
npm run build
```

Output: Vite build completed successfully: `✓ built in 13.98s`.

```powershell
cd D:\codes\LifeQuest
git diff --check
```

Output: no output, exit code 0.

## Commit

Implementation commit: `40bca352f6fed9677d17c267c7df64ce3f619b2c` (`feat(cultivation): close learning and tribulation gates`).

## Concerns

- The full backend suite emitted 399 existing dependency/framework deprecation warnings.
- The first full-suite run had one transient concurrency-test failure; the isolated test passed, and the subsequent complete run passed with 174 tests.
- `npm run build` emitted existing npm config and Rollup chunk-size warnings, but exited successfully.

## Review Fixes

### TDD Evidence

RED command:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py -q
```

Output: `3 failed, 1 passed`; failures covered legacy LearnedTechnique deduplication, reset/replay reward duplication, and independent-session source-key conflict duplication.

GREEN command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py -q
```

Output: `4 passed`.

### Changes

- Startup migration now keeps the latest duplicate LearnedTechnique row per `(user_id, technique_id)`, then adds the composite unique definition only when fresh `create_all` did not already create one. The migration is rerunnable.
- Todo reward settlement claims the unique `source_key` and cultivation mutations in one savepoint. A duplicate or unique-conflict result returns the existing settlement before legacy coins, legacy experience, or coin transactions are changed.
- Added reset/replay and independent-session conflict coverage in `backend/tests/test_task12_review_fixes.py`.

### Verification

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py tests/test_todos.py tests/test_cultivation.py -q
```

Output: `78 passed, 86 warnings`.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_notes.py::test_migrate_columns_deduplicates_daily_tribulation_attempts_before_unique_index tests/test_notes.py::test_migrate_columns_ignores_only_duplicate_last_opened_at_column tests/test_notes.py::test_migrate_columns_does_not_canonicalize_before_old_note_migration -q
```

Output: `3 passed, 7 warnings`.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Output: `177 passed, 1 failed, 403 warnings in 97.06s`; the only failure was the existing `test_concurrent_tribulation_attempts_allow_only_one_daily_attempt`, where the second concurrent result was not a `PermissionError`. An isolated rerun of that same test also failed with the same assertion (`1 failed, 7 warnings`), so the full backend result is recorded as not stable green and the existing tribulation concurrency fluctuation remains explicit.

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs
```

Output: `27 passed, 0 failed`.

```powershell
npm run build
```

Output: Vite build succeeded in `14.54s`; existing npm config, Rollup annotation, and chunk-size warnings were emitted.

```powershell
cd D:\codes\LifeQuest
git diff --check
```

Output: no output, exit code 0.

### Commit

Implementation commit: `f86d0e63f5b6a418d59b3de1e74e55860ef14adb` (`fix(cultivation): close migration and reward idempotency gaps`).

## Review Fixes - Second Round

### Scope

- Replaced a legacy non-unique index named `uq_learned_technique_user_technique` before creating the required unique definition. Duplicate learned rows are removed first, and rerunning the migration remains safe.
- Limited SQLite source-key lock recovery to three attempts with a 50ms delay. Each target lock error rolls back the failed session transaction, expires ORM state, and re-reads a committed settlement before any legacy wallet or coin transaction mutation can occur. Non-lock `OperationalError` instances are re-raised unchanged.
- Preserved the existing tribulation concurrency fluctuation as a failure; it is not reported as stable green.

### TDD Evidence

RED migration command:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py::test_same_named_non_unique_learned_technique_index_is_replaced -q
```

Observed: `1 failed`; the same-named index remained non-unique before the migration fix.

RED SQLite lock command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py::test_locked_source_key_session_reloads_committed_settlement_without_duplicates -q
```

Observed: `OperationalError: database is locked` escaped from the loser session before bounded recovery existed.

GREEN command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py -q
```

Observed: `7 passed`.

### Verification

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_task12_review_fixes.py tests/test_todos.py tests/test_cultivation.py -q
```

Observed: `80 passed, 1 failed, 86 warnings in 30.60s`. The only failure was the existing `test_concurrent_tribulation_attempts_allow_only_one_daily_attempt`: one concurrent result was not a `PermissionError`. This remains explicitly unstable and was not changed in this round.

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs
```

Observed: `27 passed, 0 failed`.

```powershell
npm run build
```

Observed: Vite build exited `0` after transforming 1959 modules. Existing npm config, Rollup annotation, and chunk-size warnings were emitted.

## Review Fixes - Third Round

### Changes

- Source-key reward lock recovery now keeps the caller's task, habit, or goal transaction intact. The claim uses the existing nested savepoint and never calls the outer `Session.rollback()`.
- Lock retries use a short-lived independent session only to observe a committed winner settlement, avoiding stale SQLite read transactions.
- Non-lock `OperationalError` coverage injects a real SQLAlchemy exception at the engine boundary, re-raises the original exception, and verifies the session remains usable.
- Lock tests use independent sessions, an explicit barrier and lock window, WAL-backed SQLite, and a bounded exhaustion assertion. No session is shared across worker threads.

### Verification

- RED: the focused lock/status command failed with `3 failed, 2 passed`; task, habit, and goal completion state was lost under the old outer rollback.
- Focused GREEN: `5 passed` for task/habit/goal preservation, independent real-lock retry, and non-lock error handling.
- Bounded lock exhaustion: `1 passed`; the held-lock path raised within one second.
- The first Task 12 file run reached `10 passed, 1 failed`; the failure was a test-fixture bug from reading an expired `user.id` in the holder thread. The corrected test passed in the short verification above; the long file run was not repeated.
- Frontend regression: `27 passed, 0 failed`.
- `npm run build`: exited `0`, with existing npm config, Rollup annotation, and chunk-size warnings.
- `git diff --check`: no output, exit code `0`.

The full backend suite remains explicitly not green because the existing `test_concurrent_tribulation_attempts_allow_only_one_daily_attempt` failure still reports a concurrent loser result that is not consistently a `PermissionError`. This existing tribulation concurrency failure was not changed or hidden in this round.
