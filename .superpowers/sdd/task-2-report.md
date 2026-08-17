# Task 2 Report

## Scope

Implemented cultivation schemas, repositories, deterministic reward/stage services, and todo completion integration. No API routes or frontend pages were added.

## RED Evidence

Command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

Result before implementation: `3 failed, 2 passed`.

The failures were the expected missing-feature failures:

- `ModuleNotFoundError: No module named 'app.services.cultivation'`
- `ModuleNotFoundError: No module named 'app.schemas.cultivation'`

The first combined run also exposed a test fixture setup issue because the shared direct-session fixture does not create tables; the local cultivation user fixture was corrected to create the test metadata before rerunning RED.

## GREEN Evidence

Focused command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q
```

Result: `14 passed, 40 warnings`.

Full backend command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Result: `113 passed, 357 warnings`.

## Implemented Behavior

- Added `CultivationOverview`, `RewardSettlement`, and `StageProgress` schemas.
- Added profile and log repositories with same-session profile creation and lookup.
- Added deterministic difficulty-weighted cultivation settlement, spirit-stone calculation, profile/log persistence, and legacy user synchronization.
- Added first-stage threshold progress behavior from the cultivation world specification.
- Integrated task, habit, and goal completion with cultivation settlement.
- Preserved existing todo response values, legacy experience/coin totals, coin transaction creation, achievement checks, and completion idempotency.
- Verified repeated task completion creates only one cultivation log.

## Concerns

- The backend suite still emits the repository's existing FastAPI and JWT deprecation warnings.
- The todo integration intentionally neutralizes the cultivation settlement's legacy wallet mirror after settlement so existing todo coin semantics remain unchanged; spirit stones remain persisted on `CultivationProfile`.
- No code-review subagent was available in the current environment, so the final review was performed from the scoped diff and test results.

## Review Fixes

- Updated settlement to use the exact formula `floor(base * difficulty * importance * efficiency * quality)` with the specification coefficients `easy=0.8`, `medium=1.0`, and `hard=1.35`.
- Added the explicit `importance: float = 1.0` service argument. Task completion maps `Task.priority` as `low=0.8`, `medium=1.0`, `high=1.3`, and `urgent=1.6`; habits and goals retain the medium default.
- Added focused coverage for non-default importance and invalid difficulty validation. Unknown difficulty now raises `ValueError("Unknown difficulty: ...")` instead of leaking `KeyError`.
- Preserved legacy coin/experience semantics, achievement checks, idempotency, and same-session persistence. The integration test now completes an urgent hard task and verifies cultivation `32`, spirit stones `19`, legacy coins `70`, legacy experience `15`, and one cultivation log.

## Review Fix Test Evidence

Focused command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q
```

Result: `16 passed, 40 warnings in 7.26s`.

Full backend command:

```text
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Result: `115 passed, 357 warnings in 70.91s`.
