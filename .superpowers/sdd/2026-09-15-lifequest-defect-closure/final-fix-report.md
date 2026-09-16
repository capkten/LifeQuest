# Final Review Fix Report

Status: DONE_WITH_CONCERNS.

## Implementation

- TIME-02 now recomputes recoverable attempt dates from UTC timestamps into `Asia/Shanghai`, deletes older timestamp-backed attempts per user/business day, and stages updates safely around the existing unique index. For a stored-date collision, timestamp-backed history is authoritative and the null-timestamp row for that same user/day is deduplicated. When only null-timestamp rows share a stored day, the lexicographically greatest ID survives. The per-user/day unique index is always enforced after this deterministic deduplication. The model fallback uses the shared China-date helper.
- SHOP-04 backfills recoverable name/price snapshots and persists `未知商品` for a missing legacy item. A later catalog row cannot overwrite that sentinel; the history view never falls back to mutable catalog values. If the legacy database has no `shop_items` table, migration preserves unknown names while still backfilling transaction-derived prices.
- NOTE-04 takes a database-backed notebook row lock before planning and reloads mutable state after lock acquisition. The same lock now covers folder/note creation, collaboration content persistence, node deletion, and notebook deletion; each path/node is re-read after lock acquisition. Notebook deletion uses one guarded transaction, and failed deletes restore removed content/attachment files before rollback. Separate-process SQLite regressions verify all five mutations serialize with a paused tree move and leave matching DB/filesystem state. The rename result assertion maps outcomes by worker label, not queue arrival order.
- Project PUT completion uses the shared settlement path, retains supplied fields, and is idempotent across repeated PUT and explicit POST. Goal update followed by explicit completion is covered for coin, experience, and cultivation settlement. The Task 9 directory-restoration assertion was already present, so no duplicate was added.

## TDD Evidence

Commands below were run from `backend/` with the worktree interpreter. Each added migration regression was run red before its implementation; failures were behavioral assertions or the expected uniqueness errors:

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_defect_migrations.py::test_tribulation_date_repair_keeps_recoverable_collision_survivor
FAILED: expected only the timestamp-backed 2026-09-16 survivor; the old helper retained the null-timestamp row too.

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_defect_migrations.py::test_startup_migration_preserves_existing_unique_guard_on_unknown_collision
FAILED: SQLite UNIQUE constraint failed while updating the recoverable row to the null-timestamp row's stored date.

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_defect_migrations.py::test_startup_migration_preserves_duplicate_unrepairable_attempts
FAILED: CREATE UNIQUE INDEX rejected duplicate null-timestamp user/date rows.

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_defect_migrations.py::test_missing_exchange_item_stays_unknown_after_catalog_item_appears
FAILED: expected ('未知商品', 20), got ('Added later', 20).

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_defect_migrations.py::test_exchange_history_migration_backfills_only_provable_snapshots
FAILED: expected the unrecoverable item name to be '未知商品'; the old migration left it NULL.
```

Additional NOTE-04 same-notebook mutation regressions were run red before the lock extension:

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_notes.py::test_note_tree_move_serializes_same_notebook_mutations
5 failed, 349 warnings in 2.15s
The create-folder, create-note, collaboration-content, and notebook-delete cases reached commit while the move was paused; node and notebook deletion could leave the moved note file behind after deleting its row.

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_notes.py::test_delete_node_restores_content_when_database_delete_fails
1 failed, 352 warnings in 0.99s
The real SQLite trigger preserved the database row, but the content-file assertion raised FileNotFoundError after the aborted delete.
```

After implementing the lock coverage and file restoration, the focused regressions passed:

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_notes.py::test_delete_node_restores_content_when_database_delete_fails tests/test_notes.py::test_note_tree_move_serializes_same_notebook_mutations
6 passed, 352 warnings in 4.16s
```

Final NOTE-04 regression rerun after switching deletion compensation to same-directory staged renames:

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_notes.py::test_delete_node_restores_content_when_database_delete_fails tests/test_notes.py::test_note_tree_move_serializes_same_notebook_mutations
6 passed, 352 warnings in 4.30s
```

The first post-implementation focused run also exposed the existing migration compatibility test for a legacy database without `shop_items`; the catalog-dependent update was guarded, while the transaction-derived price update remains independent. The legacy test and migration suite then passed together:

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_task7_rework.py::test_old_cultivation_log_schema_migrates_without_shop_items_table tests/test_defect_migrations.py
13 passed, 363 warnings in 1.49s
```

The first fresh full-backend attempt before that guard was:

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q
1 failed, 591 passed, 1457 warnings in 174.36s
Failure: tests/test_task7_rework.py::test_old_cultivation_log_schema_migrates_without_shop_items_table, because the snapshot backfill referenced the absent catalog table.
```

After correcting that legacy schema path, the fresh full-backend command passed all 592 tests below.

## Verification

```text
/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_cultivation.py tests/test_defect_migrations.py tests/test_notes.py tests/test_projects.py tests/test_calendar_stats.py
187 passed, 748 warnings in 63.58s

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q tests/test_notes.py
55 passed, 596 warnings in 32.08s

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/pytest -q
598 passed, 1460 warnings in 178.57s

node --test src/views/defect-closure-regressions.test.mjs
23 passed, 0 failed

npm test
212 passed, 0 failed

npm run check:version
Version check passed: 1.14.6

/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure/backend/.venv/bin/python -m compileall -q app
exit 0

git diff --check
exit 0

npm run build
✓ built in 11.64s (Rollup emitted existing annotation and >500 kB chunk warnings)
```

## Changed Paths

- `backend/app/main.py`
- `backend/app/models/cultivation.py`
- `backend/app/services/note.py`
- `backend/app/services/project.py`
- `backend/tests/test_calendar_stats.py`
- `backend/tests/test_cultivation.py`
- `backend/tests/test_defect_migrations.py`
- `backend/tests/test_notes.py`
- `backend/tests/test_projects.py`
- `frontend/src/views/ExchangeHistory.vue`
- `frontend/src/views/defect-closure-regressions.test.mjs`
- `.superpowers/sdd/2026-09-15-lifequest-defect-closure/progress.md`
- `.superpowers/sdd/2026-09-15-lifequest-defect-closure/final-fix-report.md`

Implementation commit: `675840edabe8a748ad882fb66b63437a599026d5` (`fix: close final LifeQuest integration findings`).

NOTE-04 follow-up commit: `bfa208876e8993f162a23337cd358034b78e6657` (`fix(notes): serialize all notebook mutations`).

## Minor Triage

- Goal update followed by explicit completion, duplicate coin/experience/cultivation settlement, and the cultivation model's China-date fallback are covered and fixed/tested.
- The Task 3 report records 150 passed for its initial pre-review-fix focused run and 159 passed for the post-fix full Task 3 focused set. The report gives separate commands and outputs for both stages, so its wording is consistent; no count discrepancy remains.
- The coin-ledger database non-negative constraint is deferred: the review found no current negative-value write path, and existing production rows were not inspected. Adding a constraint without a data audit could make an upgrade fail on legacy rows.
- Finance transaction/debt N+1 enrichment is deferred as unrelated query optimization with no measured performance regression in this fix scope.
- Backpack history action styling, broad source-test matching, and the mobile alignment note are deferred as cosmetic/test-polish observations unrelated to the four integration behaviors.
- Task 9's directory-restoration assertion already checks the original directory returns, destination cleanup, and DB/file restoration after a failed move; no duplicate regression was added.
- Authenticated browser screenshots, authenticated production pause/resume, deployed-version confirmation, deployment, push, merge, and publishing remain unverified/not performed. Chromium and production credentials are unavailable, and this task explicitly forbids production mutations and deployment actions.

No unresolved implementation blocker remains. Remaining concerns are the deferred unrelated Minor items and external browser/production acceptance gates.
