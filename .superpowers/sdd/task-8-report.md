# Task 8 Report

Status: DONE_WITH_CONCERNS

## Changed Files

- `backend/app/api/cultivation.py`
- `backend/app/services/cultivation.py`
- `backend/tests/test_cultivation.py`
- `frontend/src/components/cultivation/TribulationProbability.vue`
- `frontend/src/router/index.js`
- `frontend/src/services/cultivation.js`
- `frontend/src/views/Tribulations.vue`
- `frontend/src/views/cultivation-regressions.test.mjs`

User-owned existing changes were preserved and not staged: `frontend/components.d.ts`, `.agents/`, `.claude/skills/`, `.codex/`, and `frontend/vite-check.log`.

## Implementation

- Backend owns target-realm base probability, weighted five-part readiness, readiness bonus, pill bonus, clamp, failure loss, random roll, persisted attempt log, and next-day cooldown.
- Attempt requests accept only `pill_count`; server-controlled probability and roll fields are rejected.
- Failed tribulations preserve realm, minor stage name, techniques, equipment, slots, sect records, and NPC relationships; only current minor-stage cultivation is reduced.
- `/tribulations` now loads the real view and retains preview, submitting, success, failure, and cooldown states.

## Commits

- Implementation: `981aac98537018e5f1a6bbd2b6d52283b9db02fd`

## Verification Commands and Output

Command:

```powershell
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

Output: `33 passed, 26 warnings in 10.19s`

Command:

```powershell
cd frontend; node --test src/views/cultivation-regressions.test.mjs
```

Output: `18 passed, 0 failed`

Command:

```powershell
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Output: `141 passed, 376 warnings in 88.79s (0:01:28)`

Command:

```powershell
cd frontend; npm run build
```

Output: exit code `0`; Vite production build completed successfully.

Command:

```powershell
git diff --check
```

Output: no output; exit code `0`.

## Concerns

- The full backend suite and frontend build emit existing deprecation, npm configuration, and large-chunk warnings; none are Task 8 failures.
- Habit and task readiness are calculated from currently persisted seven-day data. When no task history exists, task quality remains the documented neutral score of `50.0`; trial and compatibility now derive from persisted sect access, active membership, and learned-technique state.
- No browser screenshot/manual session was run; frontend verification is static regression coverage plus the production build.

## Review Fixes

1. Probability transitions now use an explicit `(current_realm, target_realm)` rule table. `great_vehicle -> tribulation` is 25%, while `tribulation -> ascension` is 20%; both transitions have explicit failure-loss percentages. Added regression coverage.
2. `tribulation -> ascension` now settles success as `realm_key=ascended`, marks the result terminal, and exposes an unavailable terminal preview. The frontend shows a terminal state without adding an仙界空页面.
3. Habit timestamps are normalized to UTC before Python comparisons, covering persisted naive timestamps.
4. Daily attempt check and write are protected by a process lock plus `SELECT ... FOR UPDATE` on the cultivation profile. Added a concurrent two-worker test proving one attempt succeeds and the duplicate is rejected.
5. Trial readiness derives from confirmed `SectAccessProgress`; compatibility derives from active sect membership and learned techniques. Added stateful readiness coverage.
6. The tribulation page now displays current minor-stage cultivation and the actual loss amount from the server.
7. The probability panel formats and displays the concrete `cooldown_until` timestamp.
8. Pill preview refreshes use an incrementing request id and `AbortController`, preventing stale responses from overwriting the latest pill count.

Review-fix verification commands and actual output:

```powershell
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

Output: `38 passed, 26 warnings in 9.32s`

```powershell
cd frontend; node --test src/views/cultivation-regressions.test.mjs
```

Output: `18 passed, 0 failed`

```powershell
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Output: `146 passed, 376 warnings in 88.95s (0:01:28)`

```powershell
cd frontend; npm run build
```

Output: exit code `0`; Vite production build completed successfully.

```powershell
git diff --check
```

Output: no output; exit code `0`.

Final review-fix implementation commit: `f4dd7250d435105bacbb333b00a0c4573b2a52f3`

## Review Fixes Final Confirmation

The Review Fixes section above is persisted in this report and includes the actual post-fix outputs: cultivation tests `38 passed`, frontend regression tests `18 passed`, full backend tests `146 passed`, frontend build exit code `0`, and `git diff --check` exit code `0`. No production code was changed during this report-only finalization.

## Review Fixes - Latest Re-review

1. Daily tribulation protection now relies on the database-level `(user_id, attempted_date)` unique index, with a compatibility migration that only runs when the legacy database already has `tribulation_attempts`. The migration guard preserves older migration test doubles and databases without that table; no process-local lock is used as the deployment guarantee.
2. `ascended` is included in the canonical realm order and comparison paths. Post-ascension overview, techniques, sects, slots, and world access are covered by regression tests and remain within the existing mortal-realm UI.
3. Tribulation preview cancellation sends `skipErrorToast: true`, preventing expected `AbortController` cancellation from becoming a network-error toast.
4. `loadPreview` clears the previous preview error at request start and on success, so a later successful preview cannot retain stale failure text.
5. The migration compatibility regression found during full-suite verification was fixed in `backend/app/main.py`; `tests/test_notes.py` now passes against the existing inspector test double while real tribulation migrations remain enabled.

Latest verification commands and actual output:

```powershell
cd backend; pytest tests/test_notes.py -q
```

Output: `41 passed, 143 warnings in 32.95s`

```powershell
cd backend; pytest
```

Output: `148 passed, 376 warnings in 90.10s (0:01:30)`

```powershell
cd frontend; node --test src/views/cultivation-regressions.test.mjs
```

Output: `18 passed, 0 failed`

```powershell
cd frontend; npm run build
```

Output: exit code `0`; `1958 modules transformed`; Vite production build completed successfully. Existing npm config, Rollup annotation, and large-chunk warnings were emitted.

```powershell
git diff --check
```

Output: no output; exit code `0`.

Latest code commit: `2eea4a59599d7373d971ea8b76956b6848013c41`.

## Review Fixes - Latest Re-review 2

1. Added an idempotent pre-index migration step for legacy duplicate daily attempts. Rows are ordered by user, day, latest `attempted_at`, and deterministic id; the newest record is retained and older duplicates are deleted before creating the unique index.
2. Added `CultivationOverview.ascended` to the backend schema and service response. Sidebar仙界/仙官 links now consume that explicit API field, so only `realm_key=ascended` exposes them.
3. Added targeted detection for the `uq_tribulation_attempt_user_day` constraint and SQLite user/day column error text. Other `IntegrityError` instances are re-raised after rollback instead of being mislabeled as cooldown conflicts.

Exact verification commands and actual output:

```powershell
cd backend; pytest tests/test_notes.py::test_migrate_columns_deduplicates_daily_tribulation_attempts_before_unique_index tests/test_cultivation.py::test_overview_exposes_explicit_ascended_state tests/test_cultivation.py::test_non_daily_integrity_error_is_not_reported_as_cooldown -q
```

Output: `3 passed, 7 warnings in 0.45s`

```powershell
cd frontend; node --test src/views/cultivation-regressions.test.mjs
```

Output: `19 passed, 0 failed`

```powershell
cd backend; pytest
```

Output: `151 passed, 376 warnings in 92.92s (0:01:32)`

```powershell
cd frontend; npm run build
```

Output: exit code `0`; `1958 modules transformed`; Vite production build completed successfully. Existing npm/Rollup and large-chunk warnings were emitted.

```powershell
git diff --check
```

Output: no output; exit code `0`.

Latest code commit: `42bc8c3f68d882d17786930769565869bca0146b`.

## Review Fixes - Final Important Items

1. `Tribulations.vue` now refreshes the shared Pinia cultivation store after a successful server result before reloading the local page state. Sidebar therefore receives the authoritative `ascended=true` overview immediately.
2. `/api/cultivation/npcs` now checks the user profile server-side before seeding or returning any NPC records. Mortal users receive stable HTTP 409 `NPCs require ascended realm`; ascended users retain the existing fixed-core NPC response. The frontend route carries `requiresAscended` metadata, loads the cultivation overview when needed, and redirects non-ascended users to cultivation.
3. SQLite fallback cooldown detection now requires either the explicit `uq_tribulation_attempt_user_day` constraint name or the normalized exact SQLite message ending in `UNIQUE constraint failed: tribulation_attempts.user_id, tribulation_attempts.attempted_date`. Similar field errors without `UNIQUE constraint failed` are re-raised. Attempt ids are cached after flush to avoid expired ORM access during concurrent completion; a process-local lock only protects SQLite same-process connection use, while the database unique constraint remains the cross-process guarantee.

Exact verification commands and actual output:

```powershell
cd backend; pytest tests/test_cultivation.py::test_concurrent_tribulation_attempts_allow_only_one_daily_attempt tests/test_cultivation.py::test_non_daily_integrity_error_is_not_reported_as_cooldown tests/test_cultivation.py::test_similar_daily_fields_without_unique_error_are_not_reported_as_cooldown -q
```

Output: `3 passed, 7 warnings in 0.27s`

```powershell
cd frontend; node --test src/views/cultivation-regressions.test.mjs
```

Output: `20 passed, 0 failed`

```powershell
cd backend; pytest
```

Output: `153 passed, 376 warnings in 85.82s (0:01:25)`

```powershell
cd frontend; npm run build
```

Output: exit code `0`; `1958 modules transformed`; Vite production build completed successfully. Existing npm/Rollup and large-chunk warnings were emitted.

```powershell
git diff --check
```

Output: no output; exit code `0`.

Latest code commit: `4fa776b554be79746bd22e7c99d8d0c7fd06192a`.
