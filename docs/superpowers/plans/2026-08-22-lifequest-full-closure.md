# LifeQuest Full Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a fully verified LifeQuest product with closed mortal cultivation, sect/world/NPC progression, ascension, and a playable immortal loop while preserving existing mortal data.

**Architecture:** Keep existing mortal models and APIs authoritative, add an explicit transition domain for idempotent ascension and cross-realm settlement, and add isolated immortal models/services/APIs. Vue pages consume server-provided state and use shared error/loading/request-generation contracts; every workstream ends with backend, frontend, and browser evidence.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3, Vite, Node `node:test`, Playwright strict runner, SQLite test database, existing deployment scripts.

## Global Constraints

- 飞升不是赛季，不重置用户，不删除凡界数据。
- 飞升后仍可完成凡界待办；每个来源键只能产生一次结算。
- 修为不跨界继承；凡界修为奖励转换为仙元，资源映射使用代码固定常量。
- 所有权威条件、资源、奖励和错误码由后端返回，前端不得自行推导。
- 业务锁定按钮保持可点击并显示原因；只有请求处理中使用原生 `disabled`。
- 每个写操作必须具备事务一致性、幂等键或数据库唯一约束。
- 每个功能先写失败测试，再写最小实现，再运行全量相关测试。
- 浏览器验收覆盖 `375x812`、`768x1024`、`1024x900`、`1440x1000`。
- 不引入新的可配置后台资源规则；跨界比例写入领域常量并由测试锁定。

## File map

- Mortal cultivation rules: `backend/app/models/cultivation.py`, `backend/app/models/technique.py`, `backend/app/services/cultivation.py`, `backend/app/schemas/cultivation.py`, `backend/app/api/cultivation.py`.
- Sect/world/NPC rules: `backend/app/models/world.py`, `backend/app/services/cultivation.py`, `backend/app/api/cultivation.py`, related Vue views under `frontend/src/views/`.
- Transition and immortal domain: new focused modules under `backend/app/models/immortal.py`, `backend/app/services/ascension.py`, `backend/app/services/immortal.py`, `backend/app/schemas/immortal.py`, `backend/app/api/immortal.py`.
- Shared frontend behavior: `frontend/src/utils/errorMessage.js`, `frontend/src/services/cultivation.js`, `frontend/src/views/Cultivation.vue`, `World.vue`, `Sects.vue`, `Techniques.vue`, `Tribulations.vue`, and new immortal views.
- Verification: `backend/tests/`, `frontend/src/views/*regressions.test.mjs`, `.harness/strict-playwright-runner.mjs`, `.harness/completion-ledger.json`, `docs/superpowers/reports/`.

---

## Workstream 1 — General stability closure

### Task 1: Verify and close notebook write races

**Files:**
- Modify: `frontend/src/views/NotebookFileManage.vue`, `frontend/src/composables/useNoteWorkspace.js`
- Test: `frontend/src/views/ui-regressions.test.mjs`
- Browser: `.harness/strict-playwright-runner.mjs` or a focused strict runner under `.harness/`

**Interfaces:**
- `useNoteWorkspace` must expose independent pending state for create, rename, move, and delete actions.
- Selection changes must increment a request generation so stale list/view responses cannot replace current state.

- [ ] **Step 1: Write failing tests** for rename and move requests resolving out of order, failed mutations preserving the dialog, and rapid notebook selection.
- [ ] **Step 2: Run** `cd frontend; node --test src/views/ui-regressions.test.mjs`; expect the new assertions to fail.
- [ ] **Step 3: Implement** per-action request generations and visible error/retry state without clearing the active notebook context.
- [ ] **Step 4: Run** the focused test file; expect all related assertions to pass.
- [ ] **Step 5: Run** the authenticated browser flow at all four viewports; assert one rename, one move, one failure/retry, and no stale overwrite.
- [ ] **Step 6: Commit** `fix(notes): close notebook write race contracts`.

### Task 2: Close project detail write and delete contracts

**Files:**
- Modify: `frontend/src/views/ProjectDetail.vue`, `backend/app/api/projects.py`, `backend/app/services/project.py`
- Test: `frontend/src/views/ui-regressions.test.mjs`, `backend/tests/test_projects.py`

**Interfaces:**
- Project mutation handlers must expose `savePending`, `phasePending`, and `deletePending` independently.
- Phase deletion must preserve task ownership and return a stable confirmation/error result.

- [ ] **Step 1: Add failing backend tests** for unauthorized phase deletion, task ownership preservation, duplicate mutation submission, and failed save transaction rollback.
- [ ] **Step 2: Add failing frontend tests** for confirmation, pending dialog retention, retry, and duplicate-click suppression.
- [ ] **Step 3: Implement** backend transaction boundaries and frontend independent locks.
- [ ] **Step 4: Run** `cd backend; pytest tests/test_projects.py -q` and the focused frontend tests; expect green.
- [ ] **Step 5: Run** strict browser flows for save, phase delete, and failure recovery at four viewports.
- [ ] **Step 6: Commit** `fix(projects): close detail mutation contracts`.

### Task 3: Close Header menu propagation and ledger updates

**Files:**
- Modify: `frontend/src/components/layout/Header.vue`, `.harness/completion-ledger.json`
- Test: `frontend/src/views/ui-regressions.test.mjs`
- Report: `docs/superpowers/reports/2026-08-22-general-stability-verification.md`

- [ ] **Step 1: Add a failing test** proving profile navigation and logout do not reopen the menu.
- [ ] **Step 2: Implement** `stopPropagation()` on inner actions and close the menu before navigation.
- [ ] **Step 3: Run** the focused frontend tests and build.
- [ ] **Step 4: Run** strict browser flows for G-11, G-12, and G-13.
- [ ] **Step 5: Change ledger states only when the browser evidence exists and write the verification report.
- [ ] **Step 6: Commit** `test: verify general stability closure`.

## Workstream 2 — Mortal cultivation closure

### Task 4: Add mortal resource ledger and tribulation pill inventory

**Files:**
- Modify: `backend/app/models/cultivation.py`, `backend/app/models/backpack.py`, `backend/app/models/__init__.py`
- Modify: `backend/app/services/cultivation.py`, `backend/app/services/backpack.py`
- Test: `backend/tests/test_cultivation.py`, `backend/tests/test_backpack.py`

**Interfaces:**
- `CultivationService.get_resource_state(user_id) -> ResourceState` returns功德、资质、心境、宗门贡献、渡劫丹库存。
- `CultivationService.consume_tribulation_pills(user_id, amount, source_key) -> SettlementResult` is idempotent and transactional.

- [ ] **Step 1: Add failing tests** for default resource values, positive-only inventory changes, insufficient inventory, duplicate consumption, and transaction rollback.
- [ ] **Step 2: Add columns/tables and migration-safe startup initialization with zero defaults for existing users.
- [ ] **Step 3: Implement** inventory consume/add methods with a unique source key and row-level transaction protection.
- [ ] **Step 4: Run** `cd backend; pytest tests/test_cultivation.py tests/test_backpack.py -q`; expect green.
- [ ] **Step 5: Commit** `feat(cultivation): add mortal resource ledger and pill inventory`.

### Task 5: Implement explicit tribulation prerequisites and preparation score

**Files:**
- Modify: `backend/app/services/cultivation.py`, `backend/app/schemas/cultivation.py`, `backend/app/api/cultivation.py`
- Modify: `frontend/src/views/Tribulations.vue`, `frontend/src/services/cultivation.js`, `frontend/src/utils/errorMessage.js`
- Test: `backend/tests/test_cultivation.py`, `frontend/src/views/cultivation-regressions.test.mjs`

**Interfaces:**
- `CultivationService.get_tribulation_preview(user_id, target_realm) -> TribulationPreview` returns ordered checks and `failure_code` values.
- `CultivationService.attempt_tribulation(user_id, target_realm, pill_count, request_id) -> TribulationResult` checks cooldown, prerequisites, inventory, and idempotency in that order.

- [ ] **Step 1: Add failing tests** for every prerequisite, ordered failures, localized parameters, cooldown precedence, and repeated request IDs.
- [ ] **Step 2: Implement** a pure `calculate_preparation_score(snapshot) -> PreparationScore` using recent habits, goals, important adventures, sect contribution, realm readiness, and equipment efficiency.
- [ ] **Step 3: Implement** preview and attempt APIs with one transaction covering checks, pill deduction, result, and state update.
- [ ] **Step 4: Add frontend states** for loading, locked reason, submitting, success, failure, and retry; keep business-locked controls clickable.
- [ ] **Step 5: Run** backend and frontend focused tests, then strict tribulation flows at four viewports.
- [ ] **Step 6: Commit** `feat(cultivation): enforce tribulation prerequisites and scoring`.

### Task 6: Connect technique effects and resource growth

**Files:**
- Modify: `backend/app/models/technique.py`, `backend/app/services/cultivation.py`, `backend/app/services/todo.py`, `backend/app/services/checkin.py`
- Modify: `backend/app/schemas/cultivation.py`, `frontend/src/views/Techniques.vue`, `frontend/src/views/Cultivation.vue`
- Test: `backend/tests/test_task9_techniques.py`, `backend/tests/test_cultivation.py`, `backend/tests/test_todos.py`, `frontend/src/views/cultivation-regressions.test.mjs`

**Interfaces:**
- `TechniqueService.calculate_effective_modifiers(user_id) -> EffectModifiers` is the only source for equipped technique effects.
- `CultivationService.settle_todo_reward(...)` returns both mortal and immortal-facing deltas without double settlement.

- [ ] **Step 1: Add failing tests** for equip/unequip efficiency, conflict handling, resource growth from check-in/todo/sect activity, and reward idempotency.
- [ ] **Step 2: Implement** structured effect aggregation with the existing `+0.80` efficiency cap.
- [ ] **Step 3: Add at least one real source and one real sink/use for功德、资质、心境、宗门贡献; expose authoritative deltas in responses.
- [ ] **Step 4: Run** focused backend/frontend tests and full backend tests.
- [ ] **Step 5: Commit** `feat(cultivation): connect technique effects and resource growth`.

## Workstream 3 — Sect, world, and NPC state machines

### Task 7: Implement sect trial state machine and contribution effects

**Files:**
- Modify: `backend/app/models/world.py`, `backend/app/services/cultivation.py`, `backend/app/api/cultivation.py`
- Modify: `frontend/src/views/Sects.vue`, `frontend/src/services/cultivation.js`
- Test: `backend/tests/test_task8_sect_world.py`, `frontend/src/views/sects-request-state.test.mjs`

**Interfaces:**
- `SectService.get_trial(user_id, sect_id) -> SectTrialState` returns objectives, progress, eligibility, and status.
- `SectService.complete_trial(user_id, sect_id, request_id) -> SectTrialResult` is idempotent and awards contribution only once.

- [ ] **Step 1: Add failing tests** for trial objective progress, blocked completion, success, failure, duplicate completion, and contribution reward.
- [ ] **Step 2: Add explicit trial status and objective persistence with defaults for existing memberships.
- [ ] **Step 3: Implement** state transitions and server-ordered eligibility fields.
- [ ] **Step 4: Update frontend** to show objectives and actionable blocked reasons.
- [ ] **Step 5: Run** focused tests and strict sect flows at four viewports.
- [ ] **Step 6: Commit** `feat(sects): implement trial state machine`.

### Task 8: Implement hidden sects and progressive world map

**Files:**
- Modify: `backend/app/models/world.py`, `backend/app/services/cultivation.py`, `backend/app/api/cultivation.py`
- Modify: `frontend/src/views/World.vue`, `frontend/src/views/Sects.vue`
- Test: `backend/tests/test_task8_sect_world.py`, `frontend/src/views/cultivation-regressions.test.mjs`

- [ ] **Step 1: Add failing tests** for hidden-sect reveal conditions, one-time unlock, region ordering, node prerequisites, and simultaneous unlock prevention.
- [ ] **Step 2: Implement** explicit reveal and region-progress records with unique constraints.
- [ ] **Step 3: Return server-authoritative node states and lock reasons; remove frontend assumptions based only on realm.
- [ ] **Step 4: Run** focused tests and strict world/sect flows.
- [ ] **Step 5: Commit** `feat(world): add progressive regions and hidden sect unlocks`.

### Task 9: Add NPC uniqueness, limits, and event cooldowns

**Files:**
- Modify: `backend/app/models/world.py`, `backend/app/services/cultivation.py`, `backend/app/api/cultivation.py`
- Modify: `frontend/src/views/Npcs.vue`, `frontend/src/views/Sects.vue`
- Test: `backend/tests/test_task8_sect_world.py`, `backend/tests/test_cultivation.py`, `frontend/src/views/cultivation-regressions.test.mjs`

- [ ] **Step 1: Add failing tests** for population cap, duplicate relationship prevention, repeat-meeting cooldown, and invalid state transitions.
- [ ] **Step 2: Add database uniqueness and bounded counters with migration-safe cleanup of duplicate legacy rows.
- [ ] **Step 3: Implement** server-side NPC event state transitions and actionable frontend feedback.
- [ ] **Step 4: Run** focused tests, migration tests, and browser NPC flows.
- [ ] **Step 5: Commit** `fix(world): constrain NPC relationships and events`.

## Workstream 4 — Ascension and complete immortal loop

### Task 10: Add immortal models and dual-track migration

**Files:**
- Create: `backend/app/models/immortal.py`, `backend/app/schemas/immortal.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/database.py`, `backend/app/main.py`
- Test: `backend/tests/test_ascension_migration.py`

**Interfaces:**
- `ImmortalProfile` has one row per user and starts only when ascension succeeds.
- `AscensionRecord` and `CrossRealmSettlement` have unique source/request keys.

- [ ] **Step 1: Add failing migration tests** proving existing users keep mortal values and no immortal row exists before ascension.
- [ ] **Step 2: Add models, indexes, defaults, and startup migration logic without rewriting mortal tables.
- [ ] **Step 3: Add rollback test that restores the pre-migration database snapshot when immortal table creation or backfill fails.
- [ ] **Step 4: Run** `cd backend; pytest tests/test_ascension_migration.py -q`.
- [ ] **Step 5: Commit** `feat(ascension): add dual-track immortal data model`.

### Task 11: Implement idempotent ascension and cross-realm settlement

**Files:**
- Create: `backend/app/services/ascension.py`, `backend/app/api/immortal.py`
- Modify: `backend/app/services/cultivation.py`, `backend/app/services/todo.py`, `backend/app/api/todos.py`, `backend/app/main.py`
- Test: `backend/tests/test_ascension.py`, `backend/tests/test_todos.py`

**Interfaces:**
- `AscensionService.preview(user_id) -> AscensionPreview` returns ordered eligibility checks.
- `AscensionService.ascend(user_id, request_id) -> AscensionResult` creates the immortal profile once and records the result.
- `AscensionService.settle_mortal_todo_after_ascension(user_id, source_key, mortal_exp, mortal_coins) -> CrossRealmSettlement` converts only configured reward types; mortal cultivation exp is not copied.

- [ ] **Step 1: Add failing tests** for eligibility, successful ascension, repeated requests, concurrent requests, failed transaction rollback, and post-ascension todo settlement.
- [ ] **Step 2: Implement fixed constants in `backend/app/services/ascension.py`: `MORTAL_EXP_TO_IMMORTAL_ESSENCE = 1` and `MORTAL_COIN_TO_IMMORTAL_STONE = 1`; keep them internal and covered by tests.
- [ ] **Step 3: Implement one transaction for ascension and unique-source settlement records.
- [ ] **Step 4: Update todo completion to branch on authoritative ascended state without duplicating the completion path.
- [ ] **Step 5: Run** focused backend tests plus the existing todo reward suite.
- [ ] **Step 6: Commit** `feat(ascension): add idempotent transition and cross-realm rewards`.

### Task 12: Implement immortal resources, map, officials, activities, and progression

**Files:**
- Create: `backend/app/services/immortal.py`, `frontend/src/views/ImmortalWorld.vue`, `frontend/src/views/ImmortalOfficials.vue`, `frontend/src/views/ImmortalActivities.vue`
- Modify: `backend/app/models/immortal.py`, `backend/app/schemas/immortal.py`, `backend/app/api/immortal.py`, `frontend/src/router/index.js`, `frontend/src/components/layout/Sidebar.vue`
- Test: `backend/tests/test_immortal.py`, `frontend/src/views/immortal-regressions.test.mjs`

**Interfaces:**
- `ImmortalService.get_overview(user_id) -> ImmortalOverview` returns authoritative resources, realm, regions, officials, activities, and stage goals.
- `ImmortalService.run_activity(user_id, activity_id, request_id) -> ImmortalActivityResult` enforces unlocks/cooldowns and records one reward settlement.
- `ImmortalService.advance_stage(user_id, request_id) -> ImmortalStageResult` checks goals and updates progression once.

- [ ] **Step 1: Add failing tests** for pre-ascension access denial, overview shape, repeatable activity, cooldown activity, official commission, stage unlock, and duplicate requests.
- [ ] **Step 2: Implement** immortal resource ledger and region/stage state transitions in one service module.
- [ ] **Step 3: Add API routes under `/api/immortal` with stable error codes and authentication.
- [ ] **Step 4: Build the three Vue surfaces with loading, locked, submitting, success, failure, and retry states.
- [ ] **Step 5: Add routes and sidebar visibility based only on server `ascended` state.
- [ ] **Step 6: Run** backend tests, frontend Node tests, production build, and strict browser flows at four viewports.
- [ ] **Step 7: Commit** `feat(immortal): add complete immortal progression loop`.

### Task 13: Verify mortal todo continuity after ascension

**Files:**
- Modify: `frontend/src/views/Todos.vue`, `frontend/src/views/Home.vue`, `frontend/src/utils/displayLabels.js`
- Test: `backend/tests/test_todos.py`, `frontend/src/views/immortal-regressions.test.mjs`

- [ ] **Step 1: Add failing tests** proving an ascended user can list/create/complete mortal todos and sees仙元/仙石 deltas without mortal修为增长.
- [ ] **Step 2: Implement** authoritative reward delta rendering and history labels for converted settlements.
- [ ] **Step 3: Run** focused backend/frontend tests and a browser flow that ascends, completes a mortal task, retries it, and checks one settlement.
- [ ] **Step 4: Commit** `feat(todos): preserve mortal task continuity after ascension`.

## Workstream 5 — Release quality gate

### Task 14: Add full strict browser contracts

**Files:**
- Create/Modify: `.harness/strict-playwright-runner.mjs`, `.harness/iterations/`
- Test: `frontend/src/views/ui-regressions.test.mjs`, `frontend/src/views/cultivation-regressions.test.mjs`, `frontend/src/views/immortal-regressions.test.mjs`

- [ ] **Step 1: Add contracts** for G-11/G-12/G-13, tribulation prerequisites, sect trials, hidden sect unlock, ascension, post-ascension mortal todo, immortal activity, official commission, and stage advancement.
- [ ] **Step 2: Run** each contract at all four viewports with authenticated data fixtures.
- [ ] **Step 3: Fail the run** on unexpected console errors, unexpected requests, stale UI state, horizontal overflow, or missing actionable errors.
- [ ] **Step 4: Store JSON results and screenshots under a dated `.harness/iterations/` directory.
- [ ] **Step 5: Commit** `test: add full LifeQuest strict browser contracts`.

### Task 15: Synchronize ledger, reports, and deployment checks

**Files:**
- Modify: `.harness/completion-ledger.json`, `docs/superpowers/reports/`
- Verify: `deploy/healthcheck.sh`, `deploy/entrypoint.sh`, `docker-compose.yml`, `Dockerfile`

- [ ] **Step 1: Mark each ledger item from evidence, keeping `implemented` when only static/unit evidence exists.
- [ ] **Step 2: Run** `cd backend; pytest -q`; expected result is zero failures.
- [ ] **Step 3: Run** `cd frontend; node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs src/views/immortal-regressions.test.mjs`; expected result is zero failures.
- [ ] **Step 4: Run** `cd frontend; npm run build`; expected result is a successful Vite build.
- [ ] **Step 5: Run** Python compile, `git diff --check`, migration rollback tests, deployment health check, and the full strict runner.
- [ ] **Step 6: Write** `docs/superpowers/reports/2026-08-22-lifequest-full-closure-verification.md` containing exact commands, counts, browser evidence paths, known warnings, and any remaining non-blocking work.
- [ ] **Step 7: Commit** `chore: finalize LifeQuest full closure evidence`.

### Task 16: Optimize the production bundle and close known warnings

**Files:**
- Modify: `frontend/vite.config.js`, `frontend/src/router/index.js`, `frontend/package.json` only where the warning has a verified fix
- Test: `frontend/npm run build`

- [ ] **Step 1: Record the current main chunk size and warnings before changes.
- [ ] **Step 2: Add route-level manual chunks only for stable third-party groups that do not alter runtime behavior.
- [ ] **Step 3: Remove the obsolete npm `always-auth` project setting if it exists in project configuration; do not modify the user-wide npm config.
- [ ] **Step 4: Run** `cd frontend; npm run build` and compare chunk sizes and warnings to the baseline.
- [ ] **Step 5: Re-run** the full frontend tests and strict browser runner to prove no routing or loading regression.
- [ ] **Step 6: Commit** `perf(frontend): reduce production bundle warnings` only if the measured output improves without new failures.

## Parallel execution map

Dispatch these first in parallel:

- Agent A: Tasks 1–3, general stability.
- Agent B: Tasks 4–6, mortal cultivation resources and tribulation.

After Agent B’s interfaces are reviewed, dispatch:

- Agent C: Tasks 7–9, sect/world/NPC state machines.
- Agent D: Tasks 10–13, dual-track ascension and immortal loop.

After all feature agents return, run Tasks 14–16 sequentially as the integration and release gate. Each agent must return changed files, test commands/results, migrations, unresolved risks, and commit hashes. The integrator must inspect all diffs for overlapping edits before running the full suite.

## Self-review checklist

- Spec coverage: all five workstreams, fixed cross-realm rules, dual-track data, mortal continuity, immortal loop, and release evidence have explicit tasks.
- Placeholder scan: every task contains concrete files, interfaces, commands, expected results, and a commit boundary.
- Type consistency: `AscensionService.preview`, `ascend`, `settle_mortal_todo_after_ascension`, `ImmortalService.get_overview`, `run_activity`, and `advance_stage` are named once and consumed consistently.
- Verification boundary: no task marks an item `verified` before strict browser evidence exists.
