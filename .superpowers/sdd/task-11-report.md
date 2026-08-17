# Task 11 Report

## Status

Implemented Task 11 only on branch `codex/cultivation-progression-ui`.

Implementation commit: `20b85da04851e817933179ca9c9e3dc0f2c193c7`

## Verification

RED command, run before production changes:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_meeting_same_disciple_is_permanent_and_stable -q
```

Output:

```text
FAILED ... test_meeting_same_disciple_is_permanent_and_stable
AttributeError: 'CultivationService' object has no attribute 'meet_npc'
1 failed
```

Backend cultivation and todo regression:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q
```

Output:

```text
61 passed, 67 warnings in 19.62s
```

Frontend regression:

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs
```

Output:

```text
23 passed, 0 failed
```

Frontend build:

```powershell
cd D:\codes\LifeQuest\frontend
npm run build
```

Output:

```text
vite v5.4.21 building for production...
1959 modules transformed.
✓ built in 15.66s
```

Diff validation:

```powershell
cd D:\codes\LifeQuest
git diff --check
```

Output: no output, exit code 0.

## Concerns

- The repository has no Alembic or other migration directory; application startup uses SQLAlchemy `create_all`, which does not add the new `npcs` columns to an already-existing production database. A schema migration is required before deploying against an existing database.
- The backend tests emit existing FastAPI lifecycle and `datetime.utcnow()` deprecation warnings.
- The existing concurrent tribulation test was intermittent during verification: one run reported 60 passed/1 failed, an immediate isolated rerun passed, and the final full command passed 61/61. No tribulation code was changed.
- `npm test` is not configured in `frontend/package.json`; the repository's frontend regression suite was run directly with Node's test runner.

## Scope

Task 12-14 were not modified or implemented. Existing user changes and unrelated generated files were preserved.

## Review Fixes

### Scope

Fixed the independent-review gaps for Task 11 only. The implementation adds an idempotent startup migration for legacy `npcs` tables and the named unique index, uses UTC natural days for ordinary disciple cultivation, scopes NPC and event queries to the authenticated user, retries the first-create unique conflict, adds the authenticated meet API, returns event timeline data, and connects the frontend service and `Npcs.vue` entry form. Task 12 technique learning and Task 13 unrelated full refactors were not changed.

### TDD Red

Backend command:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_npc_cultivation_uses_utc_day_across_midnight_and_is_idempotent tests/test_cultivation.py::test_npc_events_and_relationships_are_strictly_user_scoped tests/test_cultivation.py::test_meeting_npc_recovers_from_first_creation_unique_conflict tests/test_cultivation.py::test_meet_npc_api_creates_a_user_scoped_event tests/test_cultivation.py::test_npc_startup_migration_adds_legacy_columns_and_reuses_unique_index -q
```

Output before production changes:

```text
FFFFF                                                                    [100%]
5 failed, 7 warnings in 2.93s
```

The failures were the missing UTC-default refresh argument, cross-user NPC leakage, uncaught unique conflict, missing `POST /api/cultivation/npcs/meet` route, and missing legacy-table migration.

Frontend command:

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs
```

Output before production changes:

```text
ℹ tests 24
ℹ pass 23
ℹ fail 1
```

The failing assertion was the missing `meetNpc` service/page entry.

### Verification

Task 11 backend tests and the existing cultivation/todo regression tests:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

```text
55 passed, 28 warnings in 12.38s
```

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py -q
```

```text
11 passed, 48 warnings in 8.33s
```

Combined regression command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q
```

```text
66 passed, 69 warnings in 20.09s
```

Frontend regression:

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs
```

```text
ℹ tests 24
ℹ pass 24
ℹ fail 0
```

Frontend build:

```powershell
npm run build
```

```text
vite v5.4.21 building for production...
✓ 1959 modules transformed.
✓ built in 13.33s
```

Diff validation:

```powershell
cd D:\codes\LifeQuest
git diff --check
```

Output: no output, exit code `0`.

Implementation commit: `2a57035edd387ddba1269c45e818aca6d0205dc2` (`fix(cultivation): close task 11 review gaps`).

### Concerns

- Backend tests retain existing FastAPI lifecycle and `datetime.utcnow()` deprecation warnings.
- The frontend build retains existing npm `always-auth`, VueUse pure-comment, and large-chunk warnings; the build exits successfully.
- The frontend verification is the repository's static Node regression suite plus production build; no browser visual pass was added for this narrow closure fix.
- The report itself is appended in a separate documentation commit after the implementation commit above.

## Review Fixes

### Scope

Second-round independent review fixes for Task 11. Legacy NPC deduplication now re-parents `npc_events` before deleting duplicate NPC rows, including with SQLite foreign-key enforcement enabled, and remains idempotent. NPC meeting now reuses sect visibility, realm, and messenger-contact eligibility and returns stable 404/409 API responses. Mortal users see the NPC relationship entry while ascended-only official data remains gated; Sects.vue consumes server `getNpcs()` records without fabricated names. NPC events now use `NpcEventSummary` with `event_id`, `npc_id`, `event_key`, `summary`, and `created_at`. The concurrency regression uses two independent SQLAlchemy sessions and the real unique constraint.

### TDD Red

Backend command, before production changes:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_concurrent_meet_npc_with_independent_sessions_returns_one_npc tests/test_cultivation.py::test_meet_npc_requires_visible_contacted_sect_and_stable_api_errors tests/test_cultivation.py::test_npc_event_response_uses_explicit_schema tests/test_cultivation.py::test_npc_migration_moves_events_before_deleting_duplicate_npcs -q
```

Actual output: `1 passed, 3 failed`. Failures were hidden sect returning `200` instead of `409`, missing `NpcEventSummary`, and migration setup/implementation not yet handling duplicate NPC events under foreign-key constraints.

Frontend command, before frontend changes:

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs --test-name-pattern "mortal NPCs|sects page consumes"
```

Actual output: `26 tests`, `24 passed`, `2 failed`. Failures were the missing mortal NPC Sidebar entry and missing Sects.vue server NPC relationship area.

### Verification

Task 11 backend-related tests:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q
```

```text
69 passed, 74 warnings in 22.22s
```

Frontend regression tests:

```powershell
cd D:\codes\LifeQuest\frontend
node --test src/views/cultivation-regressions.test.mjs src/views/ui-regressions.test.mjs src/composables/useNoteAutosave.test.mjs
```

```text
29 passed, 0 failed
```

Frontend production build:

```powershell
cd D:\codes\LifeQuest\frontend
npm run build
```

Actual output included `1959 modules transformed` and `built in 16.94s`; npm config, VueUse pure-comment, and large-chunk warnings remained, with exit code `0`.

Diff validation:

```powershell
cd D:\codes\LifeQuest
git diff --check
```

Actual output: no output, exit code `0`.

Additional full backend command:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Actual output: `168 passed, 1 failed, 391 warnings in 95.17s`. The failure was the pre-existing `tests/test_cultivation.py::test_concurrent_tribulation_attempts_allow_only_one_daily_attempt`; it expected one `PermissionError`, but observed zero. This failure is outside the Task 11 NPC/sect changes. The required cultivation+todo related command passed as recorded above.

Implementation commit: `41027f6` (`fix(cultivation): close second-round task 11 review gaps`).

### Concerns

- Existing FastAPI lifecycle and `datetime.utcnow()` deprecation warnings remain.
- The full backend suite retains one unrelated/intermittent tribulation concurrency failure; the Task 11-related backend suite is green.
- Frontend verification is static Node regression coverage plus the production build; no browser visual pass was added.
- User worktree changes were preserved: `frontend/components.d.ts`, `.agents/`, `.claude/skills/`, `.codex/`, `docs/superpowers/plans/2026-08-17-lifequest-cultivation-closure.md`, and `frontend/vite-check.log` were not included in the implementation commit.
