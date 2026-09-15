# Task 5 Implementation Report

## Status

Implemented the Task 5 finance core repair. The focused Task 5 backend tests and the required frontend regression tests pass. The broader selected backend set still contains one pre-existing shop idempotency failure from the earlier coin task; it is outside Task 5 files and scope.

## Changed Files

- `backend/app/services/finance.py`
- `backend/app/repositories/base.py`
- `backend/app/schemas/finance.py`
- `backend/app/api/finance.py`
- `backend/app/repositories/finance_transaction.py`
- `backend/tests/test_finance.py`
- `backend/tests/test_finance_security.py`
- `backend/tests/test_defect_closure.py`

The Task 5 frontend files were reviewed and did not require edits: the existing finance service forwards the API data, and `Finance.vue` and `FinanceTransactions.vue` already consume `account_name` and `category_name`; account mutation selectors are populated from the active-account API result. FIN-12 transaction-edit success messaging was left unchanged for Task 7.

## Implementation Notes

- Kept `_get_account_for_user` ownership-only for reads and added `_require_active_account` with the required `409` `ACCOUNT_INACTIVE` detail.
- Applied the active-account guard to transaction creation, transaction updates and deletion, transfers, recurring creation, and recurring triggers. Existing transfer targets are checked before reversing an old transfer. Inactive account reactivation remains allowed only for an update payload containing exactly `{"is_active": True}`.
- Added transaction category type validation for income and expense transactions. Transfers reject categories. The validation applies to create, update, and recurring transaction paths.
- Added scoped account/category joins in `FinanceTransactionRepository` and a service response builder. API transaction list, dashboard recent transactions, create, update, transfer, and recurring-trigger responses now include `account_name` and `category_name` keys.
- Changed `BaseRepository.update` to assign all supplied keys, including explicit `None`. Existing update callers already use `model_dump(exclude_unset=True)`, preserving omitted-field semantics.
- Added regression tests for inactive accounts, category mismatch, scoped transaction names, reactivation, and clearing goal, budget, and user avatar fields.

## Initial Red Runs

The first required command could not collect because the environment had no FastAPI:

```text
$ pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py -k 'inactive or name or category or null'
ImportError while loading conftest '/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/tests/conftest.py'.
tests/conftest.py:15: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fastapi'
EXIT_CODE=4
```

After installing the declared requirements in a temporary virtual environment and overriding SQLAlchemy to a Python 3.14-compatible release, the same test command reached the intended failures:

```text
$ pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py -k 'inactive or name or category or null'
..FF.FFFF                                                                [100%]
6 failed, 3 passed, 20 deselected, 374 warnings in 5.40s
EXIT_CODE=1
```

The failures were the expected inactive transaction acceptance, wrong category acceptance, missing `account_name`/`category_name`, and ignored explicit-null update behavior.

## Final Verification

```text
$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py -k 'inactive or name or category or null'
.........                                                                [100%]
9 passed, 20 deselected, 375 warnings in 5.14s
EXIT_CODE=0
```

```text
$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_finance.py tests/test_finance_security.py
....................                                                     [100%]
20 passed, 453 warnings in 17.24s
EXIT_CODE=0
```

```text
$ node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs
ℹ tests 73
ℹ pass 73
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
EXIT_CODE=0
```

```text
$ npm run build
> lifequest-frontend@1.14.5 prebuild
> node ../scripts/sync-version.mjs

Synchronized frontend metadata to 1.14.5

> lifequest-frontend@1.14.5 build
> vite build

✓ 2037 modules transformed.
✓ built in 16.27s
EXIT_CODE=0
```

The build also emitted the existing Rollup pure-annotation and large-chunk warnings.

The finance-related existing tests were also run:

```text
$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_audit_fixes.py
..........................................................               [100%]
58 passed, 353 warnings in 5.40s
EXIT_CODE=0

$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_debts_recurring.py
.                                                                        [100%]
1 passed, 347 warnings in 0.88s
EXIT_CODE=0
```

`git diff --check` also completed with exit code `0`.

## Self-Review And Concerns

- The Task 5-focused tests are green, and the finance/security suite is green. The response builder includes both name keys even when their values are `None`.
- The full selected command `/tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py` reported `1 failed, 28 passed`; the failure was `test_purchase_idempotency_key_returns_one_exchange`. Re-running that test alone reproduced it. The current earlier shop API does not read or pass the `Idempotency-Key` header, so this remains an existing coin-task defect and was not changed.
- The host is Python 3.14. The pinned SQLAlchemy `2.0.23` fails during import on that interpreter, so verification used the declared requirements plus temporary SQLAlchemy `2.0.53`. This is an environment compatibility concern, not a Task 5 code change.
- Existing deprecation and bundle-size warnings remain from the repository/toolchain; no unrelated cleanup was included.

## Fix Round 1

### Status

Implemented the Important review fixes for Task 5. Recurring triggers now revalidate category ownership and type at trigger time, inactive accounts are available to the owner through an explicit account-management query, and the frontend provides a reactivation action while keeping inactive accounts out of transfer choices.

### Changed Files

- `backend/app/api/finance.py`
- `backend/app/services/finance.py`
- `backend/tests/test_defect_closure.py`
- `frontend/src/services/finance.js`
- `frontend/src/views/FinanceAccounts.vue`
- `frontend/src/views/ui-regressions.test.mjs`
- `.superpowers/sdd/2026-09-15-lifequest-defect-closure/task-5-report.md`

### Implementation

- Added `include_inactive=false` to the account list API and passed `include_inactive=true` only from `FinanceAccounts.vue`; the repository default and all existing active-account consumers remain active-only.
- Added trigger-time `_validate_category_for_user` enforcement using the recurring record's user and transaction type. Legacy recurring rows with a foreign category or a category whose type does not match now fail before idempotency lookup, transaction creation, or balance mutation.
- Added backend coverage for inactive recurring creation and triggering, owner-scoped inactive account listing, and direct legacy category ownership/type mismatches. The tests assert the account balance, recurring date, and transaction count remain unchanged.
- Added the account-management UI flow: inactive rows are visibly marked, mutation controls are withheld, the reactivation button calls `financeService.updateAccount(id, { is_active: true })`, and active-only transfer selectors/net worth exclude inactive rows.

### TDD Red Runs

```text
$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_defect_closure.py tests/test_finance.py tests/test_finance_security.py -k 'recurring or inactive or category or reactivat'
....FF.....                                                              [100%]
2 failed, 9 passed, 22 deselected, 372 warnings in 5.53s
EXIT_CODE=1
```

The two failures were the legacy recurring category type and ownership cases, which returned `200` and `400` instead of rejecting before mutation.

```text
$ node --test src/views/ui-regressions.test.mjs --test-name-pattern 'finance accounts expose inactive accounts'
tests 67
pass 66
fail 1
EXIT_CODE=1
```

The frontend failure was the missing inactive-inclusive fetch/reactivation flow.

### Final Verification

```text
$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py -k 'inactive or name or category or null'
..............                                                           [100%]
14 passed, 20 deselected, 381 warnings in 7.29s
EXIT_CODE=0
```

```text
$ node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs
tests 74
pass 74
fail 0
EXIT_CODE=0
```

```text
$ /tmp/lifequest-task5-venv.ii04EV/bin/pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_audit_fixes.py tests/test_debts_recurring.py
79 passed, 471 warnings in 19.31s
EXIT_CODE=0
```

```text
$ npm run build
> lifequest-frontend@1.14.5 build
✓ 2037 modules transformed.
✓ built in 15.57s
EXIT_CODE=0
```

`git diff --check` completed with `EXIT_CODE=0`.

### Self-Review And Concerns

- The trigger guard executes after ownership-scoped account lookup and before idempotency, transaction creation, balance application, and recurring-date advancement. The rollback decorator preserves database state on rejection.
- The account list API remains owner-scoped. Its active-only default protects existing transaction and dashboard selectors; only the account-management page requests inactive rows, and its transfer controls use `activeAccounts`.
- No changes were made for the deferred transaction-enrichment N+1 Minor, and FIN-12 remains owned by Task 7.
- Tests emit existing Python 3.14/deprecation warnings and the frontend build emits existing Rollup annotation and chunk-size warnings. Backend verification used the existing temporary environment with SQLAlchemy `2.0.53` because the repository-pinned SQLAlchemy `2.0.23` does not import on Python 3.14.
