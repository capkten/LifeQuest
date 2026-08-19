# Task 2 Final Rework Report

Date: 2026-08-19
Model: gpt-5.6-luna
Commit message: `fix(todo): harden idempotent completion verification`

## Scope

- Hardened the two-process regression helpers in `backend/tests/test_regressions.py`.
- Added direct rollback/error propagation coverage in `backend/tests/test_achievements.py`.
- Narrowed achievement claim `IntegrityError` handling in `backend/app/services/achievement.py`.
- No unrelated production or frontend code was changed.

## TDD Evidence

The new assertions were run before the production fix and failed for the intended reasons:

- The worker queues contained only final `ok` outcomes and no barrier markers.
- A real SQLite `NOT NULL` claim failure was swallowed instead of being re-raised.

The focused green run then passed:

```text
5 passed
```

This covered the achievement rollback case, the achievement threshold race, and task/habit/goal distinct-process completion races.

## Changes

- Each SQL synchronization hook emits a `barrier_reached` message before waiting.
- Parent tests collect queue messages with a bounded timeout, require exactly two markers and two final outcomes, and retain process liveness, exit-code, and worker-error assertions.
- Achievement claim errors are swallowed only when the named `uq_user_achievement_user_achievement` constraint or the portable SQLite composite uniqueness message matches. Other integrity failures are re-raised after the nested savepoint rolls back.

## Verification

```text
Task 2/rework backend selection: 53 passed, 105 warnings
Cultivation suite: 69 passed, 46 warnings
Full backend suite: 234 passed, 460 warnings
Frontend regression tests: 56 passed
Frontend build: passed
git diff --check: passed
```

The frontend has no `npm test` script. The configured Node regression command was used instead.

Strict Playwright evaluation used the configured authenticated runner and Chrome channel:

```text
checks: 52
consoleErrors: 0
requestFailures: 0
failures: 2
```

Evidence: `.harness/iterations/2026-08-18T17-37-38.058Z/results.json`

The two failures are existing mobile blank-DOM results for `/` and `/todos`. They are outside this scoped backend/test rework and produced no console or request errors.
