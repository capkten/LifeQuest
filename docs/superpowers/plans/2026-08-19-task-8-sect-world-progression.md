# Task 8 Sect And World Progression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the real sect trial state machine, objective rewards, hidden sect evaluation, sect effects, distinct world progression, and the concurrent wallet invariant.

**Architecture:** Extend the existing world ORM and cultivation service in place. Catalogs remain the server-owned source of fixed content; service methods own state transitions, reward idempotency, hidden evaluation, and node progression. Existing endpoints remain compatible while new endpoints expose detailed state.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, pytest, SQLite-compatible migrations.

## Global Constraints

- Do not modify `.harness/completion-ledger.json`.
- Preserve Task 5-7 behavior and existing API response fields.
- Production behavior is test-first: each new behavior must have a failing regression before implementation.
- Do not claim Playwright verification for this backend task.
- Concurrent different-source wallet settlement must produce 40 coins, 40 total coins earned, and 30 legacy experience.

### Task 1: Add Task 8 failing contract tests

**Files:**
- Create: `backend/tests/test_task8_sect_world.py`
- Modify: `backend/tests/test_task13_review_fixes.py`

**Interfaces:**
- Tests will call `CultivationService.update_trial_objective`, `get_sect_access`, `evaluate_hidden_sects`, and `complete_world_node`.
- Existing `contact_sect_messenger`, `complete_sect_trial`, `get_world`, and `get_sects` remain callable.

- [ ] Write tests for each required transition, fixed objective snapshots, unmet-objective details, idempotent trial reward, hidden lock/reveal conditions, sect effects, region/project node unlocks, and wallet accumulation.
- [ ] Run `pytest -q tests/test_task8_sect_world.py tests/test_task13_review_fixes.py::test_different_source_keys_in_independent_sessions_accumulate_every_wallet_and_log` and record RED failures.

### Task 2: Persist trial and world progression state

**Files:**
- Modify: `backend/app/models/world.py`
- Modify: `backend/app/schemas/cultivation.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Add nullable/defaulted columns to preserve existing rows: trial state, objective snapshot/progress JSON, score, completion time; world region/project/completion/visibility/lock fields.
- Add Pydantic response models for detailed sect access, hidden evaluation, and world node actions.

- [ ] Add model fields and startup migration columns independently of one another.
- [ ] Add response models with defaults so legacy records deserialize.
- [ ] Run the Task 8 model/migration tests.

### Task 3: Implement catalog-backed trial and sect effects

**Files:**
- Modify: `backend/app/services/content_catalog.py`
- Modify: `backend/app/services/cultivation.py`

**Interfaces:**
- Add stable `SECT_TRIAL_CATALOG`, hidden reveal conditions, and world node progression metadata.
- Implement `get_sect_access(user_id, sect_key)`, `update_trial_objective(user_id, sect_key, objective_key, completed=True)`, and stateful `complete_sect_trial`.
- Use source key `sect-trial:{sect_key}` plus an objective-specific key for reward logs.

- [ ] Make RED tests pass with atomic progress updates, fixed snapshots, actionable unmet conditions, and idempotent rewards.
- [ ] Apply preference/core/contribution effects in server-side score/reward calculations.
- [ ] Run scoped cultivation and content tests.

### Task 4: Implement hidden sect evaluation and world nodes

**Files:**
- Modify: `backend/app/services/cultivation.py`
- Modify: `backend/app/api/cultivation.py`
- Modify: `frontend/src/services/cultivation.js`

**Interfaces:**
- Add `evaluate_hidden_sects(user_id)` and a reveal-aware sect listing path.
- Add node completion/progression service and endpoints; return `region_key`, `required_project_phase`, `completed`, `visible`, and `lock_reason`.

- [ ] Make hidden and world RED tests pass without direct DB flag toggles.
- [ ] Preserve old `/sects` and `/world` callers and add focused API coverage.
- [ ] Run scoped backend tests and frontend build.

### Task 5: Repair the wallet concurrency regression

**Files:**
- Modify: `backend/app/services/cultivation.py`
- Modify: `backend/app/services/todo.py`
- Modify: `backend/tests/test_task13_review_fixes.py`

**Interfaces:**
- Keep `_update_rewards` legacy semantics while serializing the user wallet update against concurrent cultivation settlements.

- [ ] Reproduce the 40-vs-20 failure.
- [ ] Implement the smallest atomic update/refresh strategy that preserves both source keys and their logs.
- [ ] Run the focused concurrency test repeatedly and then the full suite.

### Task 6: Final verification and report

**Files:**
- Modify: `docs/superpowers/reports/2026-08-19-task-8-verification.md`

- [ ] Run scoped tests, full backend tests, compileall, and diff check.
- [ ] Record exact pass/fail counts, warnings, unresolved concerns, and explicitly state Playwright was not run.
