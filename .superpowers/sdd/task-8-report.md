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
