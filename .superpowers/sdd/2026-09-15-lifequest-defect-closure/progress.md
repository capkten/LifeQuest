# SDD ledger — plan: docs/superpowers/plans/2026-09-15-lifequest-defect-closure.md

Worktree: `/home/capkin/apps/LifeQuest/.worktrees/lifequest-defect-closure`
Branch: `codex/lifequest-defect-closure`
Implementation and review model policy: every subagent must use `gpt-5.6-luna`.
Plan setup base before Task 1: `4d97624` (`docs: define shared defect test fixtures`)

## Baseline

- Frontend: `npm test` passed, 181 tests, 0 failures.
- Backend: `/home/capkin/apps/LifeQuest/backend/venv/bin/pytest -q` passed, 486 tests, 0 failures.
- A fresh worktree virtualenv with the locked SQLAlchemy 2.0.23 failed during collection on Python 3.14; the existing project environment uses SQLAlchemy 2.0.52 and is the baseline runner. This is an environment compatibility warning, not a code failure.
- Worktree was clean before Task 1; the isolated `.venv` is ignored and no application files have been changed.

## Preflight scan

The plan and approved spec were read before dispatch. The following table records every pair of tasks sharing a listed file. Shared regression files are intentional append-only integration surfaces; ownership is assigned in the ruling column.

| Pair | Shared file or interface | Finding and ruling |
| --- | --- | --- |
| 1-2 | `backend/tests/test_defect_closure.py` | Task 1 owns shared fixtures and foundation sentinels; Task 2 adds habit assertions after Task 1. Sequential. |
| 1-3 | `backend/app/models/user.py` | Task 1 adds `total_experience` and migration data; Task 3 consumes it for settlement. Sequential. |
| 1-4 | `backend/tests/test_defect_closure.py` | Task 4 appends coin contract tests after Task 1 fixtures. Sequential. |
| 1-5 | `backend/tests/test_defect_closure.py` | Task 5 appends finance tests after Task 1 fixtures. Sequential. |
| 1-6 | `backend/tests/test_defect_closure.py` | Task 6 appends budget tests after Task 1 fixtures. Sequential. |
| 1-7 | `backend/tests/test_defect_closure.py` | Task 7 appends debt tests after Task 1 fixtures. Sequential. |
| 1-8 | `backend/tests/test_defect_closure.py`; exchange idempotency/snapshot interface | Task 8 completes the purchase behavior whose schema primitives are introduced by Task 1. Sequential. |
| 1-9 | `backend/tests/test_defect_closure.py` | Task 9 appends note tests after Task 1 isolation helpers. Sequential. |
| 1-10 | `backend/tests/test_defect_closure.py` | Task 10 appends project tests after Task 1 fixtures. Sequential. |
| 1-11 | `backend/tests/test_defect_closure.py`; refresh-token interface | Task 1 creates the model/migration; Task 11 implements rotation. Sequential. |
| 1-12 | `frontend/src/views/defect-closure-regressions.test.mjs` | Task 1 creates the shared frontend regression file; Task 12 completes its cross-domain flows. Sequential. |
| 2-3 | `backend/app/schemas/todo.py`; `backend/app/services/todo.py`; `backend/tests/test_audit_fixes.py`; `frontend/src/views/Todos.vue` | Task 2 owns the daily state serializer; Task 3 extends the same service for calendar, goal and date semantics. Sequential. |
| 2-4 | `backend/tests/test_defect_closure.py` | Habit and coin tests share fixtures only; no implementation overlap. Append sequentially. |
| 2-5 | `backend/tests/test_defect_closure.py` | Habit and finance tests share fixtures only; no implementation overlap. Append sequentially. |
| 2-6 | `backend/tests/test_defect_closure.py` | Habit and budget tests share fixtures only; no implementation overlap. Append sequentially. |
| 2-7 | `backend/tests/test_defect_closure.py` | Habit and debt tests share fixtures only; no implementation overlap. Append sequentially. |
| 2-8 | `backend/tests/test_audit_fixes.py`; `backend/tests/test_defect_closure.py` | Task 8 extends existing shop/audit coverage after habit changes; no shared production file. Sequential. |
| 2-9 | `backend/tests/test_defect_closure.py` | Habit and notes tests share fixtures only. Append sequentially. |
| 2-10 | `backend/tests/test_defect_closure.py`; `frontend/src/views/ui-regressions.test.mjs` | Shared regression suites only; production domains are independent. Append sequentially. |
| 2-11 | `backend/tests/test_defect_closure.py`; `frontend/src/views/ui-regressions.test.mjs` | Shared regression suites only; production domains are independent. Append sequentially. |
| 3-4 | `frontend/src/views/Stats.vue` | Task 3 establishes cumulative stats/date consumers; Task 4 updates coin trend/history consumers in the same view. Sequential. |
| 3-8 | `backend/tests/test_audit_fixes.py` | Existing audit tests are shared; Task 8 runs after Task 3 and must preserve date fixes. |
| 4-5 | `backend/tests/test_defect_closure.py` | Coin and finance tests share fixtures only. Append sequentially. |
| 4-6 | `backend/tests/test_defect_closure.py` | Coin and budget tests share fixtures only. Append sequentially. |
| 4-7 | `backend/tests/test_defect_closure.py` | Coin and debt tests share fixtures only. Append sequentially. |
| 4-8 | `backend/app/services/shop.py`; `backend/tests/test_shop.py`; `backend/tests/test_defect_closure.py`; coin-direction interface | Task 4 defines the `spend` ledger direction; Task 8 changes the same shop service and consumes that contract. Task 4 first. |
| 4-9 | `backend/tests/test_defect_closure.py` | Coin and notes tests share fixtures only. Append sequentially. |
| 4-10 | `backend/tests/test_defect_closure.py` | Coin and project tests share fixtures only. Append sequentially. |
| 4-11 | `backend/tests/test_defect_closure.py` | Coin and auth tests share fixtures only. Append sequentially. |
| 5-6 | `backend/app/api/finance.py`; `backend/app/schemas/finance.py`; `backend/app/services/finance.py`; finance tests and services | Task 5 owns account/category/null primitives; Task 6 builds budget behavior on them. Task 5 first. |
| 5-7 | `backend/app/api/finance.py`; `backend/app/schemas/finance.py`; `backend/app/services/finance.py`; finance tests and service | Task 7 extends the finance service with debt/recurring behavior. Task 5 first, then Task 7 after Task 6. |
| 5-8 | `backend/tests/test_defect_closure.py` | Finance and shop tests share fixtures only. Append sequentially. |
| 5-9 | `backend/tests/test_defect_closure.py` | Finance and notes tests share fixtures only. Append sequentially. |
| 5-10 | `backend/tests/test_defect_closure.py` | Finance and project tests share fixtures only. Append sequentially. |
| 5-11 | `backend/tests/test_defect_closure.py` | Finance and auth tests share fixtures only. Append sequentially. |
| 6-7 | `backend/app/api/finance.py`; `backend/app/schemas/finance.py`; `backend/app/services/finance.py`; finance tests and service | Both modify finance boundaries; run Task 6 before Task 7. |
| 6-8 | `backend/tests/test_defect_closure.py` | Budget and shop tests share fixtures only. Append sequentially. |
| 6-9 | `backend/tests/test_defect_closure.py` | Budget and notes tests share fixtures only. Append sequentially. |
| 6-10 | `backend/tests/test_defect_closure.py` | Budget and project tests share fixtures only. Append sequentially. |
| 6-11 | `backend/tests/test_defect_closure.py` | Budget and auth tests share fixtures only. Append sequentially. |
| 7-8 | `backend/tests/test_defect_closure.py` | Debt and shop tests share fixtures only. Append sequentially. |
| 7-9 | `backend/tests/test_defect_closure.py` | Debt and notes tests share fixtures only. Append sequentially. |
| 7-10 | `backend/tests/test_defect_closure.py` | Debt and project tests share fixtures only. Append sequentially. |
| 7-11 | `backend/tests/test_defect_closure.py` | Debt and auth tests share fixtures only. Append sequentially. |
| 8-9 | `backend/tests/test_defect_closure.py` | Shop and notes tests share fixtures only. Append sequentially. |
| 8-10 | `backend/tests/test_defect_closure.py` | Shop and project tests share fixtures only. Append sequentially. |
| 8-11 | `backend/tests/test_defect_closure.py` | Shop and auth tests share fixtures only. Append sequentially. |
| 9-10 | `backend/tests/test_defect_closure.py` | Notes and project tests share fixtures only. Append sequentially. |
| 9-11 | `backend/app/api/auth.py`; `backend/tests/test_defect_closure.py`; authentication interface | Task 9 adds scope rejection to auth dependencies; Task 11 adds refresh/logout routes. Run Task 9 before Task 11 and keep route dependencies separate. |
| 10-11 | `backend/tests/test_defect_closure.py`; `frontend/src/views/ui-regressions.test.mjs` | Project and auth tests share regression suites only. Append sequentially. |
| 2-12 | daily habit and pause browser interface | Task 12 consumes the final Task 2 contract at all viewports; no production overlap. Final gate only. |
| 3-12 | China date, calendar and cumulative stats browser interface | Task 12 verifies the finalized Task 3 behavior; final gate only. |
| 4-12 | coin history browser interface | Task 12 verifies the finalized Task 4 behavior; final gate only. |
| 5-12 | finance account and transaction browser interface | Task 12 verifies the finalized Task 5 behavior; final gate only. |
| 6-12 | budget browser interface | Task 12 verifies the finalized Task 6 behavior; final gate only. |
| 7-12 | debt and recurring browser interface | Task 12 verifies the finalized Task 7 behavior; final gate only. |
| 8-12 | shop and backpack browser interface | Task 12 verifies the finalized Task 8 behavior; final gate only. |
| 9-12 | note move and collaboration browser interface | Task 12 verifies the finalized Task 9 behavior; final gate only. |
| 10-12 | project and milestone browser interface | Task 12 verifies the finalized Task 10 behavior; final gate only. |
| 11-12 | authentication browser interface | Task 12 verifies the finalized Task 11 behavior; final gate only. |

## Task self-consistency scan

| Task | Internal check | Result |
| --- | --- | --- |
| 1 | Creates the shared tests, models and migration primitives listed in Files; later consumers are named explicitly. The purchase endpoint test is intentionally a cross-task sentinel. | Consistent after fixture clarification; sentinel is allowed to remain red until Task 8. |
| 2 | Tests use Task 1 shared auth/habit fixtures and target the daily serializer and strict UI comparisons listed in Interfaces. | Consistent. |
| 3 | Tests exercise the date helper, goal settlement, weekly target denominator and cumulative experience promised by Interfaces. | Consistent after Task 1 adds `database`, `clock`, `user` and `create_habit_with_pause_interval`. |
| 4 | Tests use the stated coin query/response contract and shop direction, and files cover both API and UI consumers. | Consistent. |
| 5 | Tests cover the listed account, enrichment, category and null contracts; FIN-12 editing feedback is explicitly owned by Task 7. | Consistent after ownership clarification. |
| 6 | Budget tests cover period, computed response, category ownership and frontend field mapping named in Interfaces. | Consistent. |
| 7 | Debt and recurring tests match the canonical payload, filters, payments and update API; `Finance.vue` is now listed for FIN-12. | Consistent after file-list clarification. |
| 8 | Lifecycle tests cover every SHOP ID and depend on Task 1 snapshots plus Task 4 coin direction. | Consistent. |
| 9 | Nested path, filesystem rollback and scoped-token tests match the two-phase move and dependency split in Interfaces. | Consistent; shared auth file is serialized with Task 11. |
| 10 | Status schema, start transition, phase labels and milestone endpoint are all named in Files and Interfaces. | Consistent. |
| 11 | Security tests cover single-use refresh, concurrent frontend refresh and content-signature validation; Task 1 supplies the model. | Consistent. |
| 12 | Final tests consume every previous contract and release checks occur after all implementation tasks; deployment/publish remains an external gate. | Consistent with the ruling below. |

## Rulings

Ruling: Use the existing project virtualenv for backend verification because the fresh environment's locked SQLAlchemy 2.0.23 cannot import on Python 3.14, while the existing SQLAlchemy 2.0.52 environment passes the 486-test baseline — cost if wrong: environment drift could hide dependency-specific failures, so final verification must report the runner versions and retain the locked-dependency warning.

Ruling: Define the shared `database` fixture as an isolated SQLAlchemy session and add all helper names used by later task examples, including `clock`, `user`, `notebook`, `login_payload`, and `goal_or_budget` — cost if wrong: later tests would fail during fixture collection instead of testing the defects.

Ruling: Run all implementation tasks serially despite the plan's optional parallel workstream note, with Task 1 first, Tasks 2-3 before Task 4, Tasks 5-6-7 in order, Task 8 after Task 4, Task 9 before Task 11, and Task 12 last — cost if wrong: execution is slower, but parallel edits to shared finance/auth/test files would create unreviewable merge conflicts.

Ruling: Keep the Task 1 purchase-idempotency regression as a known cross-task sentinel and require it to pass by Task 8 rather than implementing purchase behavior in the foundation task — cost if wrong: Task 1's focused suite is temporarily red by design, but moving behavior earlier would blur ownership and make the task review less meaningful.

Ruling: Keep FIN-12 implementation in Task 7 and list `Finance.vue` there, while Task 5 only verifies its finance-core changes — cost if wrong: duplicate ownership could produce contradictory success messages or overwrite a reviewed frontend change.

Ruling: Use `gpt-5.6-luna` for every implementer, task reviewer, re-reviewer and final reviewer, overriding the skill's default model escalation because the user explicitly restricted all subagents — cost if wrong: subtle cross-domain issues may need more human/controller scrutiny during final review.

Ruling: Do not push, merge, publish, or trigger an external deployment from this task without a separate explicit authorization; perform local release checks and read-only online checks where possible, then leave integration to the finishing gate — cost if wrong: online acceptance or release automation remains incomplete until the user authorizes the external side effect.

## Progress

- [x] Task 1: fixtures and migration primitives
- [x] Task 2: habit daily contract and homepage behavior
- [x] Task 3: calendar, goals, statistics and China date boundaries
- [x] Task 4: coin history and shop spending direction
- [x] Task 5: finance account state and transaction core
- [x] Task 6: budget periods and computed responses
- [x] Task 7: debts, payments and recurring updates
- [x] Task 8: shop and backpack lifecycle
- [x] Task 9: note tree moves and collaboration scope
- [x] Task 10: project and milestone lifecycle
- [x] Task 11: refresh tokens and avatar validation
- [x] Task 12: full integration and release gates
- [ ] Task 13：串行化笔记附件上传与删除（最终复核跟进）

## Review loop

Task 1 review: `01a0a5e2-ccfd-7730-9839-2303314134df` returned spec compliance FAIL and code quality FAIL. Important findings:

- `create_weekly_target_habit` passes `frequency="weekly_target"` while `create_daily_habit` also passes `frequency="daily"`, producing duplicate keyword arguments at runtime.
- `run_startup_migrations` ignores its database argument and always migrates the application engine instead of the isolated database under test.
- Migration repeatability and constraints are tested, but there is no injected migration failure and rollback assertion despite the global constraint.

Task 1 fix round 1/5: all 3 findings addressed; scoped re-review passed with no new Critical/Important breakage. Commits `c5a816f..8e2f2e6`.

Task 1: complete (commits `c5a816f..8e2f2e6`, review clean).

Progress update: Task 1 is complete; Task 2 is next.

Task 2 review: `01a0a604-ab6a-71b1-988c-095068f5ec06` returned spec compliance FAIL and task quality FAIL. Important finding: `HabitDailySummary` and `_habit_daily_payload` omit required `pause_intervals` and `leave_intervals`, and the added tests only assert booleans. Task 2 fix round 1/5 is pending.

Task 2 fix round 1/5: interval fields and parity assertions added in `c594e9c`; scoped re-review passed with no new Critical/Important breakage.

Task 2: complete (commits `04bef9c..c594e9c`, review clean).

Progress update: Tasks 1-2 are complete; Task 3 is next.

Task 3 review: `01a0a632-d107-72c1-b913-874010a14490` returned Important findings:

- Weekly-target stats drop the current intersecting week in `backend/app/services/stats.py`, so valid completions before the visible window are reported as zero.
- `CalendarService.get_day_detail()` still filters `Habit.is_active == True`, so historical inactive habits can appear in the grid but disappear from day details.
- TIME-02 has only a private `_utc_today()` helper assertion and lacks real cultivation daily-limit/cooldown behavior at the China-midnight boundary.

Deferred Minor findings for final review:

- Goal regression does not test update-then-explicit-complete interoperability or duplicate experience/cultivation settlement.
- A UTC `date.today()` fallback remains in `backend/app/models/cultivation.py`.
- The Task 3 commit includes `task-3-report.md` even though the exact Task 3 staging list excludes it.
- No browser evidence was included for Calendar, Stats or Todos changes.

Task 3 fix round 1/5 is pending; the original implementer will address the three Important findings and rerun the covering tests.

Task 3 fix round 1/5: all 3 Important findings addressed in `573ea13`; scoped re-review passed with no new Critical/Important breakage.

Task 3: complete (commits `35b8c93..573ea13`, review clean).

Task 3 count reconciliation: `task-3-report.md` records 150 passed for the initial pre-review-fix focused run and 159 passed for the post-fix full Task 3 focused set, with separate commands and outputs. These are distinct verification stages; the report wording is consistent.

Progress update: Tasks 1-3 are complete; Task 4 is next.

Task 4 review: `01a0a658-2205-7b32-a61e-dd335b8a25a5` returned Task quality NEEDS FOLLOW-UP with two Important findings:

- `CoinHistory.vue` groups `created_at` with the browser timezone instead of the required `Asia/Shanghai` business date.
- The frontend regression tests are source-text regex checks and do not exercise real query serialization, income/expense mapping, loading-more `skip`, filtered counts, or rendered output; the backend test also lacks a combined source/date-range contract case.

Deferred Minor finding for final review: shop ledger writes bypass the non-negative validation method and the database column has no non-negative constraint.

Task 4 fix round 1/5 is pending; the original implementer will address both Important findings.

Task 4 fix round 1 review: date grouping was ADDRESSED, but runtime evidence remained incomplete. The re-reviewer marked finding 2 NOT ADDRESSED because `CoinHistory.vue` loading-more and filtered-count state were not executed, rendered output remained source-only, and `income` mapping lacked a runtime assertion. The report summary also still named the old commit `11044e4`.

Task 4 fix round 2/5 is pending; the original implementer will add component workflow/rendering coverage and correct report metadata.

Task 4 fix round 2/5: all remaining Important findings addressed; scoped re-review accepted with no new Critical/Important breakage. Commit `4c4f12c`.

Task 4: complete (commits `11044e4..4c4f12c`, review clean).

Progress update: Tasks 1-4 are complete; Task 5 is next.

Task 5 implementer: `01a0a689-587b-7560-ae70-cf25fd534c41` (Wegener), base `4c4f12c`, model `gpt-5.6-luna`.

Task 5 reviewer: `01a0a69e-6d37-7930-9f05-1c73e42bfd27` (Meitner), review `4c4f12c..a57590a`, model `gpt-5.6-luna`.

Task 5 review: spec compliance NEEDS CHANGES and task quality NEEDS CHANGES. Important findings: recurring triggers bypass category validation; inactive-account reactivation is unreachable from the frontend because inactive accounts are hidden and FinanceAccounts.vue has no reactivation flow; and required recurring inactive/category-mismatch paths lack regression coverage. Minor deferred for final review: transaction enrichment performs per-row N+1 name lookups.

Task 5 fix round 1/5 is pending; resume the original implementer with all three Important findings.

Task 5 fix-round implementer handoff: original agent could not accept the queued fix input after resume and was closed; fresh agent `01a0a6a7-d70e-7673-bfa8-7a11a635c2a6` (Galileo), model `gpt-5.6-luna`, is taking over the same round from base `a57590a`.

Task 5 scoped re-reviewer: `01a0a6b6-9dfb-77c0-ad3f-fa0179f39cd5` (Chandrasekhar), fix review `a57590a..126d682`, model `gpt-5.6-luna`.

Task 5 fix round 1/5: all 3 Important findings addressed; scoped re-review accepted with no new Critical/Important breakage. Commit `126d682`.

Task 5: complete (commits `a57590a..126d682`, review clean).

Progress update: Tasks 1-5 are complete; Task 6 is next.

Task 6 implementer: `01a0a6bc-d388-7f73-84e2-e95f6943305b` (Bernoulli), base `126d682`, model `gpt-5.6-luna`.

Task 6 reviewer: `01a0a6d1-e62a-7c51-b8d4-a0beb1699725` (Jason), review `126d682..92bd7e7`, model `gpt-5.6-luna`.

Task 6 review: spec compliance NEEDS CHANGES and task quality NEEDS CHANGES. Important findings: budget monetary arithmetic uses float instead of Decimal; and acceptance coverage is incomplete for start-date cutoff, monthly period, exclusive upper boundary, transfer exclusion, cross-user transaction isolation, and frontend mutation failure preservation/retry.

Task 6 fix round 1/5 is pending; resume the original implementer with both Important findings.

Task 6 fix-round implementer handoff: original agent did not execute the queued fix after resume and was closed; fresh agent `01a0a6db-2dbe-74f0-8b0e-79c6525ea32e` (Hegel), model `gpt-5.6-luna`, is taking over the same round from base `92bd7e7`.

Task 6 scoped re-reviewer: `01a0a6e4-30df-7a73-910b-e21f6019d097` (Confucius), fix review `92bd7e7..b8d3762`, model `gpt-5.6-luna`.

Task 6 fix round 1/5: both Important findings addressed; scoped re-review passed with no new Critical/Important breakage. Commit `b8d3762`.

Task 6: complete (commits `92bd7e7..b8d3762`, review clean).

Progress update: Tasks 1-6 are complete; Task 7 is next.

Task 7 implementer: `01a0a6e8-a11c-7ac0-b92f-ef8809e09e7c` (Dirac), base `b8d3762`, model `gpt-5.6-luna`.

Task 7 reviewer: `01a0a6fd-92da-7a80-bd96-3f0770c1aa37` (Kierkegaard), review `b8d3762..75e40b4`, model `gpt-5.6-luna`.

Task 7 review: spec compliance NEEDS CHANGES and task quality NEEDS CHANGES. Important findings: FIN-09 lacks status-filter and cross-user acceptance coverage; FIN-10 lacks multi-payment/date and same-date tie ordering coverage; FIN-13 lacks recurring ownership/account/category/type/field validation and rollback coverage; FIN-12 lacks runtime browser/failure-path acceptance evidence. Minor deferred for final review: payment enrichment performs per-debt N+1 lookups.

Task 7 fix round 1/5 is pending; resume the original implementer with all four Important findings.

Task 7 scoped re-reviewer: `01a0a717-f8bd-7d82-a153-b692dcb1fbbb` (Kant), fix review `75e40b4..76a8414`, model `gpt-5.6-luna`.

Task 7 fix round 1/5: all 4 Important findings addressed; scoped re-review accepted with no new Critical/Important breakage. Commit `76a8414`.

Task 7: complete (commits `75e40b4..76a8414`, review clean).

Progress update: Tasks 1-7 are complete; Task 8 is next.

Task 8 implementer: `01a0a71c-8f74-73e1-91ed-8931d49fa597` (Popper), base `76a8414`, model `gpt-5.6-luna`.

Task 8 reviewer: `01a0a72c-d953-7322-9b07-67b75c178647` (Helmholtz), review `76a8414..e51ff1e`, model `gpt-5.6-luna`.

Task 8 review: spec compliance NEEDS CHANGES and task quality NEEDS CHANGES. Important findings: archived exchange history still reads active shop items instead of snapshots; refund service has no frontend action or ITEM_EQUIPPED workflow; backpack item locking does not acquire an item-row lock; and SHOP-05 lacks same-key concurrent/unique-conflict acceptance coverage. Minor deferred for final review: missing CSS variants for new history actions and broad frontend source matching.

Task 8 fix round 1/5 is pending; resume the original implementer with all four Important findings.

Task 8 fix-round implementer handoff: original agent did not execute the queued fix after restart and was closed; fresh agent `01a0a741-cd6f-7793-a737-186db45c2253` (Poincare), model `gpt-5.6-luna`, is taking over the same round from base `e51ff1e`.

Task 8 scoped re-reviewer: `01a0a750-6dda-73e3-b751-31361e113629` (Hilbert), fix review `e51ff1e..60b3da5`, model `gpt-5.6-luna`.

Task 8 fix round 1/5: all 4 Important findings addressed; scoped re-review accepted with no new Critical/Important breakage. Commit `60b3da5`.

Task 8: complete (commits `e51ff1e..60b3da5`, review clean).
Task 8 minor (deferred): add/unequip/refund history icons lack dedicated CSS variants; frontend action contract matching remains broad; a mobile grid alignment observation is cosmetic.

Progress update: Tasks 1-8 are complete; Task 9 is next.

Task 9 implementer: `01a0a755-bd87-7ca0-8fa5-8232668af07b` (Nash), base `60b3da5`, model `gpt-5.6-luna`.

Task 9 reviewer: `01a0a769-efaa-74f1-b944-4b4822fde940` (Hypatia), review `60b3da5..2aaacf4`, model `gpt-5.6-luna`.

Task 9 review: spec compliance FAIL and task quality NEEDS WORK. Critical: backend/mcp_server.py performs a commit-false filesystem rename followed by a second move without restoring the first rename if the second move/commit fails. Important: note_collab scope is bypassed on attachment endpoints; directory create/remove side effects are absent from the move plan and rollback; apply_tree_move commits before refresh so refresh failure can diverge DB/files; planning runs outside the service lock; and tests omit exact descendant paths/content, directory cleanup, commit-failure rollback, concurrent plans, scoped attachment access, and the listed shared regression file. The mcp_server.py finding is load-bearing and is carried into the fix despite not being in the original Task 9 file list.

Task 9 fix round 1/5 is pending; resume the original implementer with all Critical/Important findings.

Task 9 scoped re-reviewer: `01a0a799-209e-7c33-af53-42677013cf77` (Hooke), fix review `2aaacf4..cebcc27`, model `gpt-5.6-luna`.

Task 9 fix round 1/5: findings 1-3 addressed, but finding 4 (post-commit detection can roll back files against durable DB state) and finding 5 (public plan/apply split and update_note stale pre-lock parent) remain open. No new Critical/Important breakage; directory-rollback direct assertion remains a deferred test-quality observation.

Task 9 fix round 2/5 is pending; resume the original implementer with findings 4 and 5.

Task 9 scoped re-reviewer (round 2): `01a0a7b4-6be1-7f12-894e-4e6acf0ab22e` (Halley), fix review `cebcc27..989171e`, model `gpt-5.6-luna`.

Task 9 fix round 2/5: both remaining Important findings addressed; scoped re-review accepted with no new Critical/Important breakage. Commit `989171e`.

Task 9: complete (commits `2aaacf4..989171e`, review clean).
Task 9 test-quality audit: the direct directory-restoration assertion is already covered by `test_note_tree_move_restores_db_and_files_when_rename_fails`; no duplicate test was added. Remaining test polish is outside this fix wave.

Progress update: Tasks 1-9 are complete; Task 10 is next.

Task 10 implementer: `01a0a7bc-6400-77f3-aea7-6b3e1f1c8059` (Kepler), base `989171e`, model `gpt-5.6-luna`.

Task 10 reviewer: `01a0a7ce-e818-7001-8511-ec0307d7c254` (Avicenna), review `989171e..2351df8`, model `gpt-5.6-luna`.

Task 10 review: spec compliance NEEDS CHANGES and task quality NEEDS CHANGES. Important findings: `complete_project()` can commit the project status before achievement/reward writes and then swallow reward failures, leaving a completed project without its reward; the frontend uses one global milestone request token so concurrent reach requests can discard an earlier milestone's successful response; and the acceptance report does not map Task 10's `PROJ-01` through `PROJ-04` evidence or state that the final Task 12 report owns the complete 44-defect mapping. Additional task-quality findings: phase status create/update boundaries lack sufficient regression coverage, and nested project-card keyboard handling can trigger navigation when the inner start action is activated.

Task 10 fix round 1/5 is pending; resume the original implementer with all Important findings and the task-quality test gaps.

Task 9 fix-round 2 handoff: original agent did not execute the queued fix after resume and was closed; fresh agent `01a0a7a5-f06a-7063-b4c5-26cdcf55e529` (Arendt), model `gpt-5.6-luna`, is taking over round 2 from base `cebcc27`.

Task 10 scoped re-reviewer: `01a0a7e9-73c3-71b2-a5bc-3bf011b0e020` (Descartes), fix review `2351df8..58eba7f`, model `gpt-5.6-luna`.

Task 10 fix round 1/5: all 5 findings addressed; scoped re-review accepted with no new Critical/Important breakage. Commit `58eba7f`.

Task 10: complete (commits `2351df8..58eba7f`, review clean).

Progress update: Tasks 1-10 are complete; Task 11 is next.

Task 11 implementer: `01a0a7ed-768d-7c60-b165-009890f7b9cc` (Hubble), base `58eba7f`, model `gpt-5.6-luna`.

Task 11 reviewer: `01a0a7fe-b236-7410-b1cc-5f871e8e31ab` (Godel), review `58eba7f..b617498`, model `gpt-5.6-luna`.

Task 11 review: spec compliance FAIL and task quality NEEDS FIXES. Important findings: truncated image headers such as minimal JPEG/other signatures can be accepted and written; avatar filesystem writes are not rolled back if the database update fails; `with_for_update()` does not serialize refresh rotation on the default SQLite database, so concurrent callers can both rotate or get a lock error instead of a 401; and the frontend interceptor can retry an in-flight request with a stale access token after local auth has been cleared. Minor: the highest-risk concurrency, commit-failure cleanup, and truncated-signature paths lack behavioral tests. The full backend suite also exposes a cross-task Task 10 MCP project completion regression from `planning`.

Task 11 fix round 1/5 is pending; resume the original implementer with the four Important findings and the required covering tests.

Task 11 scoped re-reviewer: `01a0a836-8248-74a0-9288-0fb123c0be55` (Mendel), fix review `b617498..672392a`, model `gpt-5.6-luna`.

Task 11 fix round 1/5: findings 2-4 addressed, but finding 1 (malformed JPEG/GIF/WebP payloads can still pass custom validation) remains open; no additional Critical/Important breakage in the fix diff. Out-of-scope observation for final triage: `authStore` can unconditionally clear a newer session after a stale refresh rejection. Commit `672392a`.

Task 11 fix round 2/5 is pending; resume the original implementer with the open image-validation finding and assess the stale-store-session observation in the same Task 11 contract.

Task 11 fix-round 2 handoff: original agent `01a0a7ed-768d-7c60-b165-009890f7b9cc` did not progress beyond the added tests after repeated resume/status prompts and was closed; a fresh `gpt-5.6-luna` implementer takes over round 2 from base `672392a` with the uncommitted tests preserved.

Task 11 scoped re-reviewer (round 2): `01a0a872-398e-7cd2-beee-f336ab160d16` (Nietzsche), fix review `672392a..2ff656a`, model `gpt-5.6-luna`.

Task 11 fix round 2/5: the malformed-image and stale-store findings were addressed; scoped re-review found new Important resource-exhaustion risk because Pillow loads up to 1,024 frames and 64M pixels per frame without a sufficiently tight aggregate work bound. Commit `2ff656a`.

Task 11 fix round 3/5 is pending; resume the round-2 implementer to add strict per-frame and aggregate decoded-work limits with behavioral coverage.

Task 11 scoped re-reviewer (round 3): `01a0a882-3036-7f43-b35f-f1f3457ac658` (Einstein), fix review `2ff656a..31e37a6`, model `gpt-5.6-luna`.

Task 11 fix round 3/5: the resource-exhaustion finding was addressed with validator-local dimension, per-frame pixel, frame-count and aggregate decoded-work limits; scoped re-review approved with no new Critical/Important breakage. Commit `31e37a6`.

Task 11: complete (commits `b617498..31e37a6`, review clean).

Task 11 out-of-scope carry-forward: full backend verification still fails at `tests/test_mcp_crud.py::test_mcp_project_lifecycle_covers_nested_resources_and_completion` because the MCP tool completes a new `planning` project directly while Task 10's canonical service requires `planning -> active -> completed`. This is a real Task 10 integration compatibility defect and must be fixed before Task 12 release gates.

Task 10 carry-forward implementer: `01a0a886-69c9-70c0-a964-2203cb33072c` (Aristotle), base `31e37a6`, model `gpt-5.6-luna`.

Task 10 carry-forward scoped reviewer: `01a0a891-fc0f-7923-b998-673c10ac33e0` (Franklin), review `31e37a6..37fa238`, model `gpt-5.6-luna`.

Task 10 carry-forward fix: MCP direct completion compatibility addressed; scoped review found no new Critical/Important breakage. Commit `37fa238`. Full backend suite became `582 passed`.

Task 12 implementer: final integration and release-gate work completed in `d836322`, model `gpt-5.6-luna`.

Task 12 verification: backend full suite `582 passed`, frontend full suite `211 passed`, migration/note focused suite `14 passed`, Python compilation, version check, production build, and `git diff --check` passed. `VERSION` was incremented from `1.14.5` to `1.14.6`; frontend package metadata was synchronized and Android `versionCode` advanced from `20` to `21` while `versionName` remains sourced from the root version.

Task 12 external gates: the strict browser gate is blocked because Chromium is unavailable and no authenticated storage-state fixture exists; no viewport screenshots were generated. Read-only live checks recorded `GET /api/health` 200, unauthenticated daily/pause/resume probes 401, and `/api/openapi.json` 404. Authenticated production pause/resume, deployed-version confirmation, deployment, publish, push, and merge were not performed.

Task 12: complete (commit `d836322`, automated gates clean; browser/authenticated-online gates deferred).

Deferred Minor findings for final review:

- Task 3: goal update/explicit-complete interoperability and duplicate settlement coverage; cultivation UTC fallback; focused-report count reconciliation; no browser evidence for Calendar/Stats/Todos.
- Task 4: shop ledger writes bypass the non-negative validation method and the database column has no non-negative constraint.
- Task 5: transaction enrichment performs per-row N+1 name lookups.
- Task 7: payment enrichment performs per-debt N+1 lookups.
- Task 8: history action CSS variants and broad frontend source matching; cosmetic mobile grid alignment observation.
- Task 9: remaining test-quality polish is deferred; the directory-restoration behavior already has a real assertion in `test_note_tree_move_restores_db_and_files_when_rename_fails`.
- Task 12: authenticated browser/online acceptance and browser-only visual/runtime checks remain blocked by missing Chromium and credentials.

## Final whole-branch review

Reviewer: `01a0a8bf-a08c-7262-8004-9e58800d139b`, model `gpt-5.6-luna`, range `590920d1..d836322`.

Strengths: all 44 acceptance IDs have a mapped repair/test record; broad backend/frontend/migration/ownership/rollback coverage; the Task 9 directory-restoration assertion is already present at `backend/tests/test_notes.py:208`.

Critical: none.

Important findings:

- TIME-02 migration skips rows whose `attempted_date` already exists and uses UTC date extraction for newly populated values; repair from UTC `attempted_at` to the China business date, deduplicate before enforcing uniqueness, and cover an already-present index.
- SHOP-04 legacy exchange snapshot columns remain null; backfill only recoverable values and stop using mutable catalog data as the fallback for explicit missing snapshots.
- NOTE-04 note tree moves use only process-local `RLock`; `deploy/supervisord.conf` configures two Uvicorn workers. Add a cross-worker per-notebook lock covering plan/filesystem/commit and a separate-process regression.
- Project `PUT` accepts active-to-completed and uses the generic committing repository update, bypassing transactional achievement settlement. Preserve the tested PUT contract but route completion through shared settlement and prove idempotency.

Minor triage from the review is recorded in `final-review-report.md`. The date fallback and goal interoperability test are addressed in the final fix wave. The Task 3 reports distinguish the 150-test initial run from the 159-test post-fix focused run; their wording is consistent. Coin DB non-negative constraint, finance N+1 lookups, backpack history styles/source-test specificity, and mobile alignment are deferred with reasons in `final-fix-report.md`. Task 9 directory-restoration coverage is already implemented.

Additional NOTE-04 follow-up: same-notebook `create_folder`, `create_note`, `persist_collaboration_content`, `delete_node`, and `delete_notebook` are serialized with tree moves using the per-notebook DB lock and fresh post-lock rows. Separate-process tests cover each mutation during a staged move; deletion rollback is also tested with a real SQLite trigger and restores the file before DB rollback. The follow-up focused backend set passes 187 tests and the full backend suite passes 598.

External gates: Chromium download re-attempt received about 14 MiB of the 184 MiB archive over nearly five minutes and was stopped. Temporary SQLite data, local login state, partial browser archive, and local servers were cleaned. Authenticated production mutation, deployed-version confirmation, deployment, publish, push, and merge remain unperformed.

Final fix wave implementer: `01a0a8d9-7b42-7251-bbe6-4f5ffa49802c` (Anscombe), model `gpt-5.6-luna`, base `d836322`.

Final fix wave implementation commits: `675840edabe8a748ad882fb66b63437a599026d5` and `bfa208876e8993f162a23337cd358034b78e6657`. Final verification and Minor triage are recorded in `final-fix-report.md`. Authenticated browser/production acceptance remains an external gate; no production mutation, deployment, push, or merge was performed.

## Final Scoped Re-Review

Reviewer: `01a0a92b-eb93-7ec1-a10d-97eec389b6bc`, model `gpt-5.6-luna`, range `d836322..7504ea0`.

Findings 1, 2, 4, and 5 were addressed. Finding 3 remains Important: the image-upload route writes the attachment file before `NoteService.create_attachment`, and that service does not acquire the per-notebook lock. `Attachment.note_id` has no database foreign key, so concurrent deletion can leave an attachment row or file without its note. No new Critical or Important breakage was reported. Minor report discrepancy: `final-fix-report.md:74` says 592 passed, while its final command output and the controller's fresh run report 598 passed.

## Post-Review Rulings

Ruling: For legacy tribulation rows without `attempted_at`, prefer a recoverable timestamp-backed row when its China date collides with the old stored date; when only timestamp-less rows share a stored user/day key, retain the lexicographically greatest ID — the migration still enforces the unique index and the key is deterministic — cost if wrong: UUID ordering is not chronology, so the retained row may not be the actual latest attempt.

Ruling: Freeze an unrecoverable legacy exchange name as `未知商品` even if a catalog row appears in a later startup — historical presentation must not be inferred from mutable future catalog state — cost if wrong: an item whose identity later becomes knowable remains labeled unknown.

Ruling: Extend the NOTE-04 notebook lock to folder/note creation, collaboration writes, node deletion, and notebook deletion, and stage deleted files until database commit — these operations share mutable paths and can race with a tree move or failed database transaction — cost if wrong: the wider lock and staging scope adds contention and transaction complexity.

Ruling: Treat the attachment-upload lock gap as a real Important residual and stop code changes after the single final fix wave and one scoped re-review — the upload file is written before the locked service boundary, and the table has no foreign key to serialize deletion — cost if wrong: concurrent upload/delete can leave an orphan attachment row or file until an authorized follow-up fixes the path.

Ruling: Park the `592` versus `598` final-fix-report sentence as a nonblocking documentation defect and use the fresh full-suite result of `598 passed` as final verification evidence — no implementation behavior is affected — cost if wrong: the committed report remains internally inconsistent.

Ruling: 按用户确认，将附件上传与删除竞态作为 Task 13 重新纳入同一修复计划；修复限定于现有笔记本锁、附件文件写入和附件记录事务，不新增数据库结构 — 最终复核已确认该问题会造成孤立数据，且用户原始目标要求修完全部问题 — 若判断错误，代价是最终复核后增加一项任务及相应并发回归维护成本。
