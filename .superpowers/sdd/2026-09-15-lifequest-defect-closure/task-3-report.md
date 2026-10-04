# Task 3 Report

Date: 2026-09-15

## Result

Implemented Task 3 defect closure for historical calendar behavior, completed calendar status, weekly-target denominators, idempotent goal rewards, progress bounds, cumulative experience, and unified China-local date boundaries.

## Changed Files

- `backend/app/timezone.py`
- `backend/app/models/checkin.py`
- `backend/app/repositories/user.py`
- `backend/app/schemas/todo.py`
- `backend/app/services/calendar.py`
- `backend/app/services/cultivation.py`
- `backend/app/services/stats.py`
- `backend/app/services/todo.py`
- `backend/tests/test_audit_fixes.py`
- `backend/tests/test_calendar_stats.py`
- `backend/tests/test_cultivation.py`
- `frontend/src/views/Calendar.vue`
- `frontend/src/views/Stats.vue`
- `frontend/src/views/Todos.vue`
- `frontend/src/views/defect-closure-regressions.test.mjs`

Task 1/2 interfaces in `backend/app/models/user.py` and the daily check-in service were already present and were preserved; they required no Task 3 edits.

## Verification

Commands were run from the requested worktree.

Focused backend regressions:

```text
$ /home/capkin/apps/LifeQuest/backend/venv/bin/pytest -q tests/test_calendar_stats.py tests/test_audit_fixes.py tests/test_cultivation.py
150 passed, 400 warnings in 22.59s
```

Frontend Node tests:

```text
$ npm test
ℹ tests 185
ℹ pass 185
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
```

Frontend production build:

```text
$ npm run build
✓ built in 13.66s
```

The build emitted the existing Rollup annotation and chunk-size warnings.

Full backend suite:

```text
$ /home/capkin/apps/LifeQuest/backend/venv/bin/pytest -q
1 failed, 501 passed, 1039 warnings in 139.59s (0:02:19)
```

## Concerns

The full backend suite still has one unrelated failure in `tests/test_defect_closure.py::test_purchase_idempotency_key_returns_one_exchange`: repeating the same shop purchase idempotency key returns a different exchange ID. This is outside Task 3 and no shop code was changed.

## Fix Round 1

Addressed the three reviewer findings:

- Weekly-target stats retain the China week that intersects the beginning of the visible window, anchoring its target slots and completions to the first visible day when the Monday falls earlier.
- Calendar day details include inactive habits when they were scheduled on the selected historical date, matching the calendar grid behavior.
- Replaced the cultivation helper-only midnight test with a real `settle_todo_reward` daily-cap operation: the eighth prior log blocks aptitude points before midnight, and the next operation receives the daily aptitude point after the China-local boundary.

Changed files in this fix round:

- `backend/app/services/stats.py`
- `backend/app/services/calendar.py`
- `backend/tests/test_calendar_stats.py`
- `backend/tests/test_cultivation.py`

### Red Verification

The new regressions were run before the production fixes:

```text
$ /home/capkin/apps/LifeQuest/backend/venv/bin/pytest -q tests/test_calendar_stats.py::test_weekly_target_stats_include_the_current_intersecting_china_week tests/test_calendar_stats.py::test_calendar_day_detail_keeps_historical_inactive_habits tests/test_cultivation.py::test_cultivation_daily_reward_cap_resets_at_china_midnight
2 failed, 1 passed, 342 warnings in 0.89s
```

The two calendar/stat regressions failed with `0 == 2` completed weekly slots and a missing historical habit; the cultivation behavior test passed against the existing round 1 implementation.

### Green Verification

Focused regression set:

```text
$ /home/capkin/apps/LifeQuest/backend/venv/bin/pytest -q tests/test_calendar_stats.py::test_weekly_target_stats_include_the_current_intersecting_china_week tests/test_calendar_stats.py::test_calendar_day_detail_keeps_historical_inactive_habits tests/test_cultivation.py::test_cultivation_daily_reward_cap_resets_at_china_midnight
3 passed, 342 warnings in 0.77s
```

Complete Task 3 focused backend set:

```text
$ /home/capkin/apps/LifeQuest/backend/venv/bin/pytest -q tests/test_calendar_stats.py tests/test_audit_fixes.py tests/test_cultivation.py
159 passed, 406 warnings in 24.57s
```

Frontend Node tests:

```text
$ npm test
ℹ tests 185
ℹ pass 185
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
```

The existing full-suite concern remains unchanged: the unrelated shop purchase idempotency test still needs separate repair.
