# LifeQuest Defect Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 2026-09-15 审计中列出的全部 44 个缺陷，统一跨模块契约，保护已有数据，并用后端、前端、浏览器和线上证据完成验收。

**Architecture:** 保留现有 FastAPI、SQLAlchemy、Vue 3 和 Pinia 分层，只在受影响的 schema、service、repository、model、migration 和 view/service 边界增加明确契约。服务端负责状态、权限、时间、奖励、余额、库存和文件事务；前端只负责 DTO 映射、请求状态和展示。启动迁移沿用 `backend/app/main.py` 的幂等迁移入口。

**Tech Stack:** Python 3、FastAPI、Pydantic、SQLAlchemy、SQLite/PostgreSQL 兼容 SQL、pytest、Vue 3、Pinia、Axios、Node test runner、Vite、Playwright。

**Spec:** `docs/superpowers/specs/2026-09-15-lifequest-defect-closure-design.md`

## Global Constraints

- 所有 44 个缺陷编号 HAB-01 至 AUTH-03 都必须有修复、测试和验收证据。
- 不把 FEAT-01 至 FEAT-10 新功能混入本次修复，不做无关页面重构。
- 数据库时间戳保存 UTC，业务日期统一使用 `Asia/Shanghai`；同一习惯同一中国日期最多一条有效完成记录。
- 金币金额保持非负 magnitude，方向由 `CoinType.EARN`/`CoinType.SPEND` 决定；前端按类型渲染正负，不批量篡改旧金币金额。
- 停用账户拒绝新流水、转账和周期流水，但允许用户重新激活账户。
- 所有跨资源写操作使用现有 `rollback_on_error` 或等价的同一 SQLAlchemy 事务；金额计算使用 `Decimal`。
- 所有新增数据库结构必须支持新鲜数据库和旧数据库，迁移可重复执行并有回滚/失败测试。
- 写操作先写失败测试，再写最小实现，再运行聚焦测试和全量测试；每个任务单独提交。
- 用户可见修复在最终集成任务统一将根目录 `VERSION` 从 `1.14.5` 增至 `1.14.6`，再运行前端版本同步和检查。
- 保留现有用户修改；提交时只暂存本计划涉及的文件。

## Defect coverage map

| Task | 缺陷编号 | 验收主题 |
| --- | --- | --- |
| 1 | 基础设施 | 回归测试入口、迁移、累计经验、refresh token、购买幂等和历史快照结构 |
| 2 | HAB-01、HAB-02、HAB-08 | 首页日报完整状态、暂停/恢复响应和线上接口验收 |
| 3 | HAB-03 至 HAB-07、TIME-01、TIME-02、STAT-01 | 日历、每周目标、目标奖励、日期边界和累计经验 |
| 4 | FIN-01、FIN-02 | 金币历史契约和商城消费方向 |
| 5 | FIN-07、FIN-14、FIN-16、FIN-17 | 流水名称、账户状态、分类类型和可选字段清空 |
| 6 | FIN-03 至 FIN-06、FIN-15 | 预算统计、字段、分类归属和保存后响应 |
| 7 | FIN-08 至 FIN-13 | 借贷契约、筛选、还款、零余额、编辑提示和周期流水更新 |
| 8 | SHOP-01 至 SHOP-05 | 背包历史、卸下、退款、商品历史和购买幂等 |
| 9 | NOTE-01 至 NOTE-04 | 笔记树路径、文件移动、协作 scope 和原子操作 |
| 10 | PROJ-01 至 PROJ-04 | 项目状态、开始入口、阶段状态和里程碑 |
| 11 | AUTH-01 至 AUTH-03 | Refresh Token、并发刷新和头像文件验证 |
| 12 | 全部 | 跨域回归、浏览器、迁移、版本和线上发布门禁 |
| 13 | 最终复核跟进 | 笔记图片附件上传与节点/笔记本删除互斥，失败不遗留文件或记录 |

## Defect-by-defect acceptance index

The grouped map above is the execution view. This index is the completeness gate: every individual audit ID has one owning task, one concrete repair outcome, and a dynamic acceptance target.

| 编号 | 完整需求 / 修复结果 | 负责任务与验收证据 |
| --- | --- | --- |
| HAB-01 | 日报返回 `is_active`、`paused_today`、`scheduled_today` 等服务端状态；正常习惯不能被首页判定为暂停，且可完成。 | Task 2：日报 API 契约测试、首页/待办源码测试、浏览器完成流程 |
| HAB-02 | 暂停和恢复使用真实状态响应；线上失败必须通过真实状态码、响应体和部署版本定位并复验。 | Task 2、12：暂停/恢复往返测试、线上 HTTP 证据 |
| HAB-03 | 日历查询包含停用后的历史计划，并按历史日期判断是否曾有效。 | Task 3：暂停区间与历史日历测试 |
| HAB-04 | 日历已完成习惯返回 `completed`，未完成的计划日才返回 `due`。 | Task 3：日历状态测试与浏览器检查 |
| HAB-05 | 每周目标习惯按 `weekly_target` 统计周计划槽位，不按每日计划次数放大分母。 | Task 3：周目标统计测试 |
| HAB-06 | 普通目标更新为 `completed` 与显式完成入口共享结算路径，奖励只能发放一次。 | Task 3：重复完成奖励测试 |
| HAB-07 | `GoalUpdate.progress` 只接受 `0..100`，非法进度由 API 明确拒绝。 | Task 3：schema 边界测试 |
| HAB-08 | 首页、待办页与日报使用同一习惯状态计算，不因字段缺失、旧响应或刷新顺序产生相反状态。 | Task 2、3、12：统一 serializer、旧响应防御和浏览器往返测试 |
| FIN-01 | 金币历史统一使用 `coin_type`、`skip`、`limit` 请求参数和 `transactions` 响应字段，筛选、分页、汇总一致。 | Task 4：后端契约测试与前端请求源码测试 |
| FIN-02 | 商城消费记录的金额保持非负 magnitude，由 `type=spend` 表示支出，历史页面显示为负向消费。 | Task 4：商城账本测试与金币历史 UI 测试 |
| FIN-03 | 预算前端读取规范字段 `spent_amount`，支出金额不再因读取 `spent` 而显示错误。 | Task 6：预算 API/UI 字段测试 |
| FIN-04 | 预算响应返回 `category_name`，页面正确显示分类名称。 | Task 6：预算响应测试 |
| FIN-05 | 预算统计按 `monthly/weekly` 周期和 `start_date` 计算，只计入有效周期内的支出。 | Task 6：周期与起始日期测试 |
| FIN-06 | 创建和更新预算返回带有支出、剩余、进度和分类的完整计算响应，前端保存后不丢统计字段。 | Task 6：创建/更新响应与保存后刷新测试 |
| FIN-07 | 流水响应包含当前归属范围内的 `account_name` 和 `category_name`。 | Task 5：流水关联名称测试 |
| FIN-08 | 借贷创建统一使用 `creditor`、`type=borrow/lend`、`amount`、`remaining`；旧字段仅在无冲突时兼容。 | Task 7：规范/旧字段创建测试 |
| FIN-09 | 借贷列表同时正确应用 `status` 和借入/借出类型筛选，并隔离其他用户数据。 | Task 7：筛选与越权测试 |
| FIN-10 | 借贷响应包含按时间排序的 `payments`，还款历史可展示。 | Task 7：还款历史响应测试 |
| FIN-11 | 借贷剩余金额为 `0` 时按零显示，不使用会吞掉零值的真假判断。 | Task 7：零余额 API/UI 测试 |
| FIN-12 | 总览页编辑流水显示“流水已更新”，创建流水才显示“记账成功”。 | Task 7：编辑成功反馈源码与浏览器测试 |
| FIN-13 | 已定义的周期流水支持归属校验、字段校验、显式清空和更新接口，前端有对应 service 方法。 | Task 7：`PUT /recurring/{id}` API/UI 测试 |
| FIN-14 | 停用账户禁止新流水、转账和周期流水，失败时不改变余额或记录；账户仍可重新激活。 | Task 5：账户状态、事务回滚和重新激活测试 |
| FIN-15 | 创建或更新预算时分类必须属于当前用户或合法系统分类，跨用户分类不能改写预算。 | Task 6：跨用户分类归属测试 |
| FIN-16 | 可选字段显式传 `null` 可以清空，省略字段仍保持原值；通用更新逻辑不再无条件跳过 `None`。 | Task 5：repository、目标/预算/头像清空测试 |
| FIN-17 | 收入只能使用收入分类，支出只能使用支出分类，转账不能携带分类；创建、更新和周期流水一致校验。 | Task 5：分类类型边界测试 |
| SHOP-01 | 背包历史统一返回并读取 `action_type`，动作图标和统计覆盖所有动作。 | Task 8：历史响应与前端字段测试 |
| SHOP-02 | 提供直接卸下装备的 API 和按钮，状态回到 `active` 并记录 `unequip` 历史。 | Task 8：卸下生命周期测试 |
| SHOP-03 | 已装备物品退款明确拒绝，要求先卸下，且不发生部分扣减或退款。 | Task 8：装备退款事务测试 |
| SHOP-04 | 被兑换、背包或使用历史引用的商品只归档不物理删除，历史使用名称/价格快照可读。 | Task 8：商品生命周期与历史快照测试 |
| SHOP-05 | 商城购买使用用户维度幂等键；重试只返回第一次成功兑换，不重复扣金币、扣库存或加背包。 | Task 1、8：唯一约束、竞态和重复购买测试 |
| PROJ-01 | 项目创建后的 `planning` 状态有明确的“开始项目”入口，可幂等转为 `active` 并进入进行中统计。 | Task 10：开始接口和浏览器操作测试 |
| PROJ-02 | 项目状态只接受 `planning/active/completed/archived`，未知新状态拒绝，旧未知值只读兼容。 | Task 10：状态 schema、迁移数据和统计隔离测试 |
| PROJ-03 | 阶段状态使用统一状态词或显式映射，所有页面显示可识别的中文标签。 | Task 10：阶段状态映射与 UI 源码测试 |
| PROJ-04 | 项目详情提供里程碑 `/reach` 达成入口，操作可重试且不会重复结算。 | Task 10：里程碑 API/UI 测试 |
| NOTE-01 | 文件夹改名或移动递归更新所有后代节点的数据库 `path` 和 `content_path`。 | Task 9：嵌套目录数据库路径测试 |
| NOTE-02 | 文件夹改名或移动同步移动真实文件和目录，节点 ID 与笔记内容保持不变。 | Task 9：临时文件树真实路径测试 |
| NOTE-03 | `note_collab` 票据只能调用协作接口，普通用户和待办接口拒绝该 scope。 | Task 9：协作 scope 403 测试 |
| NOTE-04 | 数据库路径更新和文件移动具备可恢复原子性，任一阶段失败都恢复文件和数据库。 | Task 9：注入 rename 失败回滚测试 |
| TIME-01 | 签到日期使用 `Asia/Shanghai` 业务日，不受 UTC/中国跨日边界误导。 | Task 3：`15:59:59/16:00:00 UTC` 边界测试 |
| TIME-02 | 修仙每日限制、冷却和奖励使用同一中国业务日，与签到、习惯和统计边界一致。 | Task 3：修仙每日边界测试 |
| STAT-01 | 总览 `total_exp` 返回累计经验，而不是当前等级内的局部经验。 | Task 1、3：迁移回填、经验结算和总览测试 |
| AUTH-01 | Refresh Token 持久化保存哈希并一次性轮换，旧 token 重放返回 401 并可撤销链路。 | Task 1、11：模型/迁移和单次刷新安全测试 |
| AUTH-02 | 前端并发 401 只发起一次 refresh，共享同一个 Promise，失败后不会递归重试。 | Task 11、12：并发刷新源码与行为测试 |
| AUTH-03 | 头像上传校验真实文件签名、扩展名、MIME 和大小，伪造图片内容不得进入公开目录。 | Task 11：伪造文件与合法图片测试 |

---

### Task 1: Add defect-closure regression fixtures and migration primitives

**Files:**
- Create: `backend/tests/test_defect_closure.py`
- Create: `backend/tests/test_defect_migrations.py`
- Create: `frontend/src/views/defect-closure-regressions.test.mjs`
- Create: `backend/app/models/refresh_token.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/shop.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/conftest.py`

**Interfaces:**
- Produces `User.total_experience` for all experience settlement paths.
- Produces `RefreshToken` with `id`, `user_id`, `token_hash`, `jti`, `expires_at`, `revoked_at`, `replaced_by_id`, `created_at`.
- Produces nullable `ExchangeHistory.idempotency_key`, `item_name_snapshot`, and `unit_price_snapshot` with a unique `(user_id, idempotency_key)` guard for non-null keys.
- Produces test helpers that create two users and assert no cross-user resource mutation.
- Defines the isolated shared test fixtures/helpers used by later tasks: `database` yields a SQLAlchemy session (not the legacy `(session, factory)` tuple), and `user`, `clock`, `client`, `auth_headers`, `login_payload`, `notebook`, `project`, `shop_item`, `equipped_item`, `referenced_item`, `exchange`, `debt`, `budget`, `transaction`, `goal`, `goal_or_budget`, `inactive_account`, `active_account`, `coin_rows`, `create_daily_habit`, `create_habit_with_pause_interval`, `create_nested_note_tree`, `snapshot_tree`, `snapshot_shop_user_state`, `latest_history_action`, `get_item`, `exchange_history_name`, `create_weekly_target_habit`, `add_completion_dates`, `complete_on`, `count_goal_reward`, `run_startup_migrations`, `has_column`, and `fail_on_second_rename`. Existing module-local fixtures may override these names for older tests.

- [ ] **Step 1: Write failing regression tests for the current cross-layer failures.**

Add focused tests with these exact names and assertions:

```python
def test_daily_summary_habit_contract_contains_server_state(client, auth_headers):
    response = client.get("/api/todos/daily", headers=auth_headers)
    assert response.status_code == 200
    habit = response.json()["habits"][0]
    assert habit["is_active"] is True
    assert habit["paused_today"] is False
    assert habit["scheduled_today"] is True


def test_purchase_idempotency_key_returns_one_exchange(client, auth_headers, shop_item):
    first = client.post(
        "/api/shop/exchange",
        headers={**auth_headers, "Idempotency-Key": "purchase-test-1"},
        json={"item_id": str(shop_item.id), "quantity": 1},
    )
    second = client.post(
        "/api/shop/exchange",
        headers={**auth_headers, "Idempotency-Key": "purchase-test-1"},
        json={"item_id": str(shop_item.id), "quantity": 1},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_startup_migration_is_repeatable(migration_database):
    run_startup_migrations(migration_database)
    run_startup_migrations(migration_database)
    assert has_column(migration_database, "users", "total_experience")
```

Implement the test database fixture using the existing `Base.metadata.create_all` and temporary file isolation. Do not point tests at `backend/lifequest.db`.

- [ ] **Step 2: Run the focused tests to record the failure.**

Run: `cd backend && pytest -q tests/test_defect_closure.py tests/test_defect_migrations.py`
Expected: the daily response and migration assertions fail against the current implementation; the output is recorded in the task notes before implementation.

- [ ] **Step 3: Add the schema primitives and idempotent startup migration.**

Add `total_experience` to `User`, the `RefreshToken` model, and the nullable exchange snapshot/idempotency columns. Register the model in `backend/app/models/__init__.py`. Extend the existing startup migration path in `backend/app/main.py` to:

1. Add missing columns without dropping data.
2. Create the refresh-token table.
3. Create the non-null unique index for `(user_id, idempotency_key)` using the existing `_ensure_unique_index` pattern.
4. Backfill `total_experience` as the sum of completed level thresholds plus the current `experience`; do not infer missing reward events.
5. Keep null idempotency keys allowed for legacy exchange rows.

Use this shape for the backfill calculation:

```python
def cumulative_experience(level: int, current_experience: int) -> int:
    return sum(int(100 * (1.5 ** (rank - 1))) for rank in range(1, level)) + current_experience
```

- [ ] **Step 4: Run migration and model tests.**

Run: `cd backend && pytest -q tests/test_defect_migrations.py tests/test_defect_closure.py::test_purchase_idempotency_key_returns_one_exchange`
Expected: migration tests pass; purchase test remains failing only because purchase service has not consumed the key yet.

- [ ] **Step 5: Commit the foundation.**

```bash
git add backend/app/models/refresh_token.py backend/app/models/__init__.py backend/app/models/user.py backend/app/models/shop.py backend/app/main.py backend/tests/conftest.py backend/tests/test_defect_closure.py backend/tests/test_defect_migrations.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "test: add defect closure fixtures and migration primitives"
```

### Task 2: Repair the habit daily contract and homepage behavior

**Files:**
- Modify: `backend/app/schemas/todo.py`
- Modify: `backend/app/services/todo.py`
- Modify: `backend/app/api/todos.py`
- Modify: `frontend/src/services/todo.js`
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/views/Todos.vue`
- Modify: `backend/tests/test_defect_closure.py`
- Modify: `backend/tests/test_audit_fixes.py`
- Modify: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- Adds `HabitDailySummary` and `DailySummaryResponse` schemas, with explicit booleans `is_active`, `paused_today`, `scheduled_today`, and `excused_today`.
- Adds `TodoService._habit_daily_payload(habit)` as the only serializer used by `/todos/daily`.
- Keeps `POST /api/todos/habits/{habit_id}/pause` and `/resume` returning a complete `HabitResponse`.

- [ ] **Step 1: Add the failing API and frontend regression assertions.**

Add backend assertions for every state field and a paused/resumed round trip:

```python
def test_daily_summary_preserves_active_and_schedule_state(client, auth_headers, db_session):
    habit = create_daily_habit(db_session, auth_headers)
    data = client.get("/api/todos/daily", headers=auth_headers).json()
    row = next(item for item in data["habits"] if item["id"] == str(habit.id))
    assert row["is_active"] is True
    assert row["paused_today"] is False
    assert row["scheduled_today"] is True

    paused = client.post(f"/api/todos/habits/{habit.id}/pause", headers=auth_headers)
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False
    assert paused.json()["paused_today"] is True
```

Add a source contract test that checks `Home.vue` and `Todos.vue` use explicit boolean comparisons for optional server fields and that the daily service does not read `result.data` for this response.

- [ ] **Step 2: Run the focused tests and confirm the current failure.**

Run: `cd backend && pytest -q tests/test_defect_closure.py -k 'daily_summary or pause'`
Run: `cd frontend && node --test src/views/ui-regressions.test.mjs`
Expected: the daily response lacks the fields; the frontend contract test identifies the unsafe missing-field behavior.

- [ ] **Step 3: Implement one server-side habit serializer.**

Add `HabitDailySummary` and `DailySummaryResponse` in `backend/app/schemas/todo.py`. In `TodoService.get_daily_summary`, call `_set_completed_today(habit)` once and return all state fields through `_habit_daily_payload`. Update the route decorator in `backend/app/api/todos.py` to use `response_model=DailySummaryResponse`.

Do not duplicate pause logic in the route. Preserve `paused_today = not habit.is_active or is_paused_on(...)` and `scheduled_today = is_due(...) and not paused_today and not excused_today`.

- [ ] **Step 4: Make the frontend defensive while the deployment rolls forward.**

Change `Home.vue` and `Todos.vue` to test `habit.paused_today === true`, `habit.is_active === false`, `habit.excused_today === true`, and `habit.scheduled_today === false`. The server contract remains mandatory; the strict comparisons prevent an old response from being interpreted as paused. Keep the existing action lock and preserve the success/error message behavior.

- [ ] **Step 5: Run the repaired habit flow.**

Run: `cd backend && pytest -q tests/test_defect_closure.py -k 'daily_summary or pause' tests/test_audit_fixes.py -k habit`
Run: `cd frontend && node --test src/views/ui-regressions.test.mjs`
Expected: normal habits are completable, pause returns `is_active=false`, resume returns `is_active=true`, and all focused tests pass.

- [ ] **Step 6: Commit the habit contract repair.**

```bash
git add backend/app/schemas/todo.py backend/app/services/todo.py backend/app/api/todos.py frontend/src/services/todo.js frontend/src/views/Home.vue frontend/src/views/Todos.vue backend/tests/test_defect_closure.py backend/tests/test_audit_fixes.py frontend/src/views/ui-regressions.test.mjs
git commit -m "fix(todos): return complete habit state in daily summary"
```

### Task 3: Correct calendar, habit statistics, goals, and daily time boundaries

**Files:**
- Modify: `backend/app/timezone.py`
- Modify: `backend/app/models/checkin.py`
- Modify: `backend/app/services/checkin.py`
- Modify: `backend/app/services/calendar.py`
- Modify: `backend/app/services/stats.py`
- Modify: `backend/app/services/cultivation.py`
- Modify: `backend/app/services/todo.py`
- Modify: `backend/app/schemas/todo.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/repositories/user.py`
- Modify: `frontend/src/views/Calendar.vue`
- Modify: `frontend/src/views/Stats.vue`
- Modify: `frontend/src/views/Todos.vue`
- Modify: `backend/tests/test_calendar_stats.py`
- Modify: `backend/tests/test_audit_fixes.py`
- Modify: `backend/tests/test_cultivation.py`

**Interfaces:**
- `app.timezone.today()` is the single China-local business-date helper used by check-in, cultivation daily actions, calendar and stats.
- `StatsService.get_habit_stats()` counts `weekly_target` as `weekly_target` slots per active week; it does not count every day as a slot.
- `StatsService.get_overview()` returns cumulative `total_exp` from `User.total_experience`.
- Goal completion through update and the explicit complete endpoint share one idempotent settlement path.

- [ ] **Step 1: Add failing tests for historical calendar status, weekly targets, goal rewards, and midnight behavior.**

Add these cases:

```python
def test_calendar_keeps_pre_pause_history_and_marks_completed_habits(client, auth_headers, db_session):
    habit = create_habit_with_pause_interval(db_session, auth_headers, paused_on=date(2026, 9, 10))
    complete_on(db_session, habit, date(2026, 9, 9))
    events = client.get("/api/calendar/events", params={"start_date": "2026-09-09", "end_date": "2026-09-11"}, headers=auth_headers).json()
    assert next(event for event in events if event["date"] == "2026-09-09")["status"] == "completed"
    assert not any(event["date"] == "2026-09-11" for event in events)


def test_weekly_target_stats_use_target_slots_not_daily_slots(database, clock):
    habit = create_weekly_target_habit(database, weekly_target=3)
    add_completion_dates(database, habit, [date(2026, 9, 8), date(2026, 9, 10)])
    rows = StatsService(database).get_habit_stats(habit.user_id, "week")
    assert sum(row["total"] for row in rows) == 3
    assert sum(row["completed"] for row in rows) == 2


def test_goal_status_update_settles_reward_once(client, auth_headers, goal):
    response = client.put(f"/api/todos/goals/{goal.id}", headers=auth_headers, json={"status": "completed", "progress": 100})
    assert response.status_code == 200
    repeat = client.put(f"/api/todos/goals/{goal.id}", headers=auth_headers, json={"status": "completed", "progress": 100})
    assert repeat.status_code == 200
    assert count_goal_reward(goal.id) == 1
```

Add clock cases at `2026-09-15 15:59:59 UTC` and `2026-09-15 16:00:00 UTC`, which are `23:59:59` and `00:00:00` in China. Assert check-in, habit, stats and cultivation daily limits use the same date.

- [ ] **Step 2: Run the focused tests to capture the failures.**

Run: `cd backend && pytest -q tests/test_calendar_stats.py tests/test_audit_fixes.py -k 'calendar or stats or goal or china_day' tests/test_cultivation.py -k 'day or daily'`
Expected: inactive history/status, weekly target denominator, goal reward, total experience and at least one date-boundary assertion fail before implementation.

- [ ] **Step 3: Centralize China-local date use.**

Update `backend/app/timezone.py` with a direct `today()` helper backed by the configured `ZoneInfo("Asia/Shanghai")`. Change `DailyCheckin.checkin_date` default from `date.today` to that helper. Replace direct UTC `.date()` calls in the daily cultivation paths covered by the audit with the helper; leave event timestamps as UTC.

- [ ] **Step 4: Correct calendar and habit statistics.**

In `CalendarService`, query all user habits for the requested range, use pause intervals to determine whether each historical date was active, and query valid completion records to set `status="completed"`; retain `status="due"` only for an uncompleted scheduled date. In `StatsService.get_habit_stats`, aggregate weekly-target completions per China week and add exactly `weekly_target` scheduled slots once per active week, anchored to the week-start bucket used by the existing chart.

- [ ] **Step 5: Make goal completion and cumulative experience authoritative.**

Add `ge=0, le=100` to `GoalUpdate.progress`. Refactor `TodoService.update_goal` so a transition to `completed` calls the same idempotent settlement helper as `/goals/{id}/complete`; use a source key unique to the goal. Use the `User.total_experience` column introduced in Task 1: update `UserRepository.update_experience` and `_update_experience_no_commit` to increment both `experience` and `total_experience` before level rollover. Update achievement, check-in, finance, cultivation and todo reward paths that call the no-commit method. Return `total_experience` in the stats overview.

- [ ] **Step 6: Update the affected views and verify.**

Ensure `Calendar.vue` renders the completed status, `Stats.vue` consumes the corrected `total_exp`, and `Todos.vue` does not show a duplicate reward after a goal update. Preserve existing request sequence guards.

Run: `cd backend && pytest -q tests/test_calendar_stats.py tests/test_audit_fixes.py tests/test_cultivation.py`
Expected: all focused tests pass, including the UTC-to-China boundary cases.

- [ ] **Step 7: Commit the date and statistics repair.**

```bash
git add backend/app/timezone.py backend/app/models/checkin.py backend/app/services/checkin.py backend/app/services/calendar.py backend/app/services/stats.py backend/app/services/cultivation.py backend/app/services/todo.py backend/app/schemas/todo.py backend/app/models/user.py backend/app/repositories/user.py frontend/src/views/Calendar.vue frontend/src/views/Stats.vue frontend/src/views/Todos.vue backend/tests/test_calendar_stats.py backend/tests/test_audit_fixes.py backend/tests/test_cultivation.py
git commit -m "fix: unify daily boundaries and habit statistics"
```

### Task 4: Align coin history and shop coin-direction semantics

**Files:**
- Modify: `backend/app/api/coins.py`
- Modify: `backend/app/schemas/coin.py`
- Modify: `backend/app/services/coin.py`
- Modify: `backend/app/services/shop.py`
- Modify: `frontend/src/services/coin.js`
- Modify: `frontend/src/views/CoinHistory.vue`
- Modify: `frontend/src/views/Stats.vue`
- Modify: `backend/tests/test_defect_closure.py`
- Modify: `backend/tests/test_shop.py`

**Interfaces:**
- `GET /api/coins/history` accepts `coin_type`, `source`, `start_date`, `end_date`, `skip`, and `limit`.
- The response contains `transactions`, `total_earned`, `total_spent`, and `count`.
- `CoinTransaction.amount` remains a non-negative magnitude; `type` is authoritative for display and totals.

- [ ] **Step 1: Add failing contract tests.**

```python
def test_coin_history_filters_and_returns_transactions_key(client, auth_headers, coin_rows):
    response = client.get(
        "/api/coins/history",
        params={"coin_type": "spend", "skip": 1, "limit": 1},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert set(response.json()) >= {"transactions", "total_earned", "total_spent", "count"}
    assert len(response.json()["transactions"]) == 1
    assert response.json()["transactions"][0]["type"] == "spend"
```

Add a shop purchase test asserting the history row has `type="spend"`, positive magnitude, and the UI renders a minus sign from the type rather than from the amount.

- [ ] **Step 2: Run the focused tests and record the contract mismatch.**

Run: `cd backend && pytest -q tests/test_defect_closure.py -k coin tests/test_shop.py -k purchase`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs`
Expected: the frontend currently sends the wrong parameter names/reads the wrong response key, and the source contract test fails.

- [ ] **Step 3: Normalize the backend and frontend contract.**

Keep `CoinService.get_history` as the response authority. Add explicit validation for `coin_type` and pass `skip/limit` unchanged to the repository. Update `coin.js` and `CoinHistory.vue` to map UI values `income/expense` to `earn/spend`, send `skip`, and read `result.transactions`. Keep pagination metadata based on filtered `count`.

Update the coin history amount renderer and coin trend consumers to use `transaction.type === "spend"` for direction. Do not change existing persisted positive shop amounts.

- [ ] **Step 4: Verify filters, pagination, totals and display.**

Run: `cd backend && pytest -q tests/test_defect_closure.py -k coin tests/test_shop.py tests/test_finance.py -k coin`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs`
Expected: filtered history contains the requested rows, loading more advances `skip`, and shop spending is displayed as an expense.

- [ ] **Step 5: Commit the coin contract repair.**

```bash
git add backend/app/api/coins.py backend/app/schemas/coin.py backend/app/services/coin.py backend/app/services/shop.py frontend/src/services/coin.js frontend/src/views/CoinHistory.vue frontend/src/views/Stats.vue backend/tests/test_defect_closure.py backend/tests/test_shop.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "fix(coins): align history contract and spending direction"
```

### Task 5: Enforce finance account state, transaction enrichment, category type, and nullable updates

**Files:**
- Modify: `backend/app/services/finance.py`
- Modify: `backend/app/repositories/base.py`
- Modify: `backend/app/schemas/finance.py`
- Modify: `backend/app/api/finance.py`
- Modify: `backend/app/repositories/finance_transaction.py`
- Modify: `frontend/src/services/finance.js`
- Modify: `frontend/src/views/Finance.vue`
- Modify: `frontend/src/views/FinanceTransactions.vue`
- Modify: `frontend/src/views/FinanceAccounts.vue`
- Modify: `backend/tests/test_finance.py`
- Modify: `backend/tests/test_finance_security.py`
- Modify: `backend/tests/test_defect_closure.py`

**Interfaces:**
- `FinanceService._get_account_for_user` returns only an owned account; mutating operations additionally require `is_active=True` and raise `{code: "ACCOUNT_INACTIVE"}`.
- Transaction response always includes `account_name` and `category_name`.
- `category_id` must belong to the current user or be a system category whose `type` matches the transaction type.
- `BaseRepository.update` sets explicit `None`; callers use `exclude_unset=True` to distinguish omitted fields.

- [ ] **Step 1: Add failing tests for inactive accounts, enrichment, category mismatch, and clearing fields.**

```python
def test_inactive_account_rejects_transaction_and_transfer(client, auth_headers, inactive_account, active_account):
    transaction = client.post("/api/finance/transactions", headers=auth_headers, json={
        "account_id": str(inactive_account.id), "type": "expense", "amount": 1,
    })
    assert transaction.status_code == 409
    assert transaction.json()["detail"]["code"] == "ACCOUNT_INACTIVE"


def test_transaction_response_contains_account_and_category_names(client, auth_headers, transaction):
    response = client.get("/api/finance/transactions", headers=auth_headers)
    row = response.json()["items"][0]
    assert row["account_name"]
    assert row["category_name"]


def test_explicit_null_update_clears_optional_field(client, auth_headers, goal_or_budget):
    response = client.put(goal_or_budget.url, headers=auth_headers, json={"description": None})
    assert response.status_code == 200
    assert response.json()["description"] is None
```

- [ ] **Step 2: Run focused finance tests and capture the failures.**

Run: `cd backend && pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py -k 'inactive or name or category or null'`
Expected: inactive account mutations currently succeed, names are absent, mismatched categories are accepted, or explicit null is ignored.

- [ ] **Step 3: Add one account mutation guard and apply it to every mutation source.**

Keep `_get_account_for_user` for reads. Add `_require_active_account(account)` and call it from create/update/delete transaction balance paths, transfer source and target paths, and recurring trigger. Do not apply it to the account update path when the payload is only reactivating an account.

Return the stable conflict detail:

```python
raise HTTPException(
    status_code=409,
    detail={"code": "ACCOUNT_INACTIVE", "message": "账户已停用，无法创建新的财务操作。"},
)
```

- [ ] **Step 4: Enrich responses and validate category type.**

Update the repository/service response builder to join account and category names in the same user scope. Validate `income` against income categories and `expense` against expense categories; transfers must not accept a category. Apply the same validation to updates and recurring transactions.

- [ ] **Step 5: Fix explicit-null persistence without changing omitted-field semantics.**

Change `BaseRepository.update` to assign every key present in `obj_in`, including `None`. Audit every caller and ensure optional update schemas use `model_dump(exclude_unset=True)`. Where a caller intentionally wants to preserve a value, omit the key instead of passing `None`. Add regression coverage for goal description/deadline, budget category/start date and user avatar clearing.

- [ ] **Step 6: Run the finance-core verification.**

Run the finance-core tests below. The transaction editing feedback is owned by Task 7 because that task already changes `Finance.vue` for the debt/recurring flow.

`cd backend && pytest -q tests/test_finance.py tests/test_finance_security.py tests/test_defect_closure.py -k 'inactive or name or category or null'`
`cd frontend && node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs`

Expected: all focused tests pass and inactive account operations leave no balance or transaction mutation.

- [ ] **Step 7: Commit the finance core repair.**

```bash
git add backend/app/services/finance.py backend/app/repositories/base.py backend/app/schemas/finance.py backend/app/api/finance.py backend/app/repositories/finance_transaction.py frontend/src/services/finance.js frontend/src/views/Finance.vue frontend/src/views/FinanceTransactions.vue frontend/src/views/FinanceAccounts.vue backend/tests/test_finance.py backend/tests/test_finance_security.py backend/tests/test_defect_closure.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "fix(finance): enforce account state and enrich transaction contracts"
```

### Task 6: Correct budget periods, computed fields, category names, and ownership

**Files:**
- Modify: `backend/app/repositories/budget.py`
- Modify: `backend/app/services/finance.py`
- Modify: `backend/app/schemas/finance.py`
- Modify: `backend/app/api/finance.py`
- Modify: `frontend/src/services/finance.js`
- Modify: `frontend/src/views/Finance.vue`
- Modify: `frontend/src/views/FinanceBudgets.vue`
- Modify: `backend/tests/test_finance.py`
- Modify: `backend/tests/test_defect_closure.py`

**Interfaces:**
- `BudgetRepository.get_spent_amount(budget, period_start, period_end)` queries only the budget's effective period and user-owned transactions.
- `FinanceService._budget_payload(budget, as_of)` returns `spent_amount`, `remaining_amount`, `progress`, `category_name`, period and start-date metadata.
- Create and update budget APIs return the computed payload, not a bare ORM object.

- [ ] **Step 1: Add failing tests for the five budget defects.**

```python
def test_weekly_budget_uses_week_period_and_start_date(database, user):
    budget = create_budget(database, user, period="weekly", amount=100, start_date=date(2026, 9, 8))
    add_expense(database, user, date(2026, 9, 9), 20)
    add_expense(database, user, date(2026, 9, 16), 30)
    payload = FinanceService(database).get_budgets(user.id)[0]
    assert payload["spent_amount"] == 20


def test_budget_response_has_names_and_computed_values(client, auth_headers, budget):
    response = client.get("/api/finance/budgets", headers=auth_headers)
    row = response.json()[0]
    assert row["category_name"]
    assert row["spent_amount"] == 0
    assert row["remaining_amount"] == row["amount"]
    assert row["progress"] == 0
```

Add a cross-user category update test that expects 404/403 and asserts the budget category remains unchanged. Add frontend source tests requiring `spent_amount`, not `spent`.

- [ ] **Step 2: Run the budget tests to confirm the current mismatch.**

Run: `cd backend && pytest -q tests/test_finance.py tests/test_defect_closure.py -k budget`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs`
Expected: weekly/date filtering, response fields, category name and ownership assertions fail against the current code.

- [ ] **Step 3: Implement period-aware spending queries.**

Use `BudgetPeriod.MONTHLY` and `BudgetPeriod.WEEKLY` to derive the current China-local period. Clamp the effective start to `max(period_start, budget.start_date)` and the end to the exclusive next period boundary. Sum only `FinanceTransactionType.EXPENSE` rows belonging to the budget user and category. Do not count transfers or transactions before `start_date`.

- [ ] **Step 4: Build one computed budget response.**

Join the category under the current user/system scope, compute `spent_amount`, `remaining_amount=max(amount-spent_amount, 0)`, and `progress=min(spent_amount / amount * 100, 100)` with a zero-amount guard. Use `_budget_payload` for list, create and update responses. Validate category ownership and category type before create and update.

- [ ] **Step 5: Update the budget views and verify save behavior.**

Change `FinanceBudgets.vue` and the budget section in `Finance.vue` to consume `spent_amount`, `remaining_amount`, `progress`, and `category_name`. After create/update, write the computed response into the list or refetch once; do not insert the bare POST response. Add a retryable error state that preserves the existing list.

- [ ] **Step 6: Run and commit.**

Run: `cd backend && pytest -q tests/test_finance.py tests/test_defect_closure.py -k budget`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs`
Expected: all budget contract, period, ownership and UI-field tests pass.

```bash
git add backend/app/repositories/budget.py backend/app/services/finance.py backend/app/schemas/finance.py backend/app/api/finance.py frontend/src/services/finance.js frontend/src/views/Finance.vue frontend/src/views/FinanceBudgets.vue backend/tests/test_finance.py backend/tests/test_defect_closure.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "fix(finance): return period-aware budget statistics"
```

### Task 7: Repair debt contracts, payments, filters, and recurring updates

**Files:**
- Modify: `backend/app/schemas/finance.py`
- Modify: `backend/app/services/finance.py`
- Modify: `backend/app/api/finance.py`
- Modify: `frontend/src/services/finance.js`
- Modify: `frontend/src/views/FinanceDebts.vue`
- Modify: `frontend/src/views/Finance.vue`
- Modify: `backend/tests/test_debts_recurring.py`
- Modify: `backend/tests/test_finance.py`
- Modify: `backend/tests/test_defect_closure.py`

**Interfaces:**
- `POST /api/finance/debts` accepts `creditor`, `type=borrow|lend`, `amount`, `remaining`, `interest_rate`, `description`, and `due_date`.
- New debt forms send `remaining=amount` unless the user enters a smaller initial remaining amount.
- `GET /api/finance/debts` accepts `status` and an optional `type` compatibility filter; the service applies both conditions.
- Adds `PUT /api/finance/recurring/{recurring_id}` using `RecurringUpdate` and `financeService.updateRecurring`.
- `DebtResponse.payments` is a list of payment records; zero remaining is rendered as zero.

- [ ] **Step 1: Add failing API and UI contract tests.**

```python
def test_create_debt_accepts_canonical_payload(client, auth_headers):
    response = client.post("/api/finance/debts", headers=auth_headers, json={
        "creditor": "测试对象", "type": "borrow", "amount": 100, "remaining": 100,
    })
    assert response.status_code == 200
    assert response.json()["creditor"] == "测试对象"


def test_debt_response_contains_payments_and_zero_remaining(client, auth_headers, debt):
    response = client.get("/api/finance/debts", headers=auth_headers)
    row = response.json()[0]
    assert "payments" in row
    assert row["remaining"] == 0
```

Add a frontend source test that requires `creditor`, `borrow/lend`, `remaining`, `status`, and `updateRecurring`, and forbids `remaining || amount` for display.

- [ ] **Step 2: Run the focused debt tests and confirm current failures.**

Run: `cd backend && pytest -q tests/test_debts_recurring.py tests/test_defect_closure.py -k debt`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs`
Expected: old payload naming, missing remaining, ignored type filter or missing payments causes failures.

- [ ] **Step 3: Normalize debt schemas and service filters.**

Keep canonical backend names. Add a Pydantic pre-validation adapter that accepts legacy `creditor_name` only when `creditor` is absent, maps legacy type values `borrowed/lent` to `borrow/lend`, and rejects conflicting values. Require `remaining` on canonical create; the frontend always supplies it. Update `FinanceService.get_debts` to filter by status and type without returning another user's records.

- [ ] **Step 4: Include payment history and add recurring update.**

Build `payments` from `DebtPayment` rows ordered by payment date/id. Add `FinanceService.update_recurring` with ownership, account/category/type validation, explicit-null semantics and `is_active` support. Add `PUT /recurring/{id}` and `financeService.updateRecurring(id, data)`. Preserve the existing trigger/delete endpoints.

- [ ] **Step 5: Fix the debt UI.**

Change `FinanceDebts.vue` payload fields and tab filter mapping, send `remaining`, display `Number.isFinite(remaining) ? remaining : amount` only as a compatibility fallback, and render zero correctly. Render `payments` when present. Add `financeService.updateRecurring(id, data)` for the new recurring update endpoint; no new recurring page is introduced because the current repository has no recurring view. In `Finance.vue`, capture `const wasEditing = Boolean(editingTx.value)` before `cancelQuickAdd()`, then show “流水已更新” when true and “记账成功” otherwise. The service consumer must retain its form on failure.

- [ ] **Step 6: Run and commit.**

Run: `cd backend && pytest -q tests/test_debts_recurring.py tests/test_finance.py tests/test_defect_closure.py -k 'debt or recurring'`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs`
Expected: create, filter, payment history, zero remaining and recurring update tests pass.

```bash
git add backend/app/schemas/finance.py backend/app/services/finance.py backend/app/api/finance.py frontend/src/services/finance.js frontend/src/views/FinanceDebts.vue frontend/src/views/Finance.vue backend/tests/test_debts_recurring.py backend/tests/test_finance.py backend/tests/test_defect_closure.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "fix(finance): align debt and recurring transaction flows"
```

### Task 8: Complete shop and backpack lifecycle operations

**Files:**
- Modify: `backend/app/api/backpack.py`
- Modify: `backend/app/schemas/backpack.py`
- Modify: `backend/app/services/backpack.py`
- Modify: `backend/app/services/shop.py`
- Modify: `backend/app/api/shop.py`
- Modify: `backend/app/schemas/shop.py`
- Modify: `frontend/src/services/backpack.js`
- Modify: `frontend/src/services/shop.js`
- Modify: `frontend/src/views/Backpack.vue`
- Modify: `frontend/src/views/BackpackHistory.vue`
- Modify: `frontend/src/views/Shop.vue`
- Modify: `backend/tests/test_backpack.py`
- Modify: `backend/tests/test_shop.py`
- Modify: `backend/tests/test_audit_fixes.py`
- Modify: `backend/tests/test_defect_closure.py`

**Interfaces:**
- Adds `POST /api/backpack/items/{item_id}/unequip`, returning `BackpackItemResponse` and recording `UsageAction.UNEQUIP`.
- `UsageHistoryResponse` returns canonical `action_type`; `action` is accepted only as a legacy response alias during the compatibility window.
- Purchase requires `Idempotency-Key`; same user/key returns the original exchange without a second charge, stock decrement or backpack increment.
- Refund rejects equipped items with `ITEM_EQUIPPED` and instructs the client to unequip first; no partial refund occurs.
- User-created shop items are archived (`is_active=false`) when referenced by history instead of being physically deleted. Exchange history uses name/price snapshots.

- [ ] **Step 1: Add failing lifecycle tests.**

```python
def test_unequip_item_records_history(client, auth_headers, equipped_item):
    response = client.post(f"/api/backpack/items/{equipped_item.id}/unequip", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert latest_history_action(equipped_item.user_id) == "unequip"


def test_refund_equipped_item_is_rejected_without_mutation(client, auth_headers, exchange, equipped_item):
    before = snapshot_shop_user_state(exchange.user_id)
    response = client.post(f"/api/shop/exchange/{exchange.id}/refund", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ITEM_EQUIPPED"
    assert snapshot_shop_user_state(exchange.user_id) == before


def test_delete_referenced_item_archives_it(client, auth_headers, referenced_item):
    response = client.delete(f"/api/shop/items/{referenced_item.id}", headers=auth_headers)
    assert response.status_code == 200
    assert get_item(referenced_item.id).is_active is False
    assert exchange_history_name(referenced_item.id)
```

Add a contract assertion that `BackpackHistory.vue` reads `action_type` and that a repeated purchase with the same header returns the same exchange.

- [ ] **Step 2: Run current shop/backpack tests and capture failures.**

Run: `cd backend && pytest -q tests/test_backpack.py tests/test_shop.py tests/test_audit_fixes.py -k 'purchase or refund or equip or history'`
Expected: the unequip route is missing, equipped refunds do not have the required user path, and history/delete/idempotency assertions fail.

- [ ] **Step 3: Implement unequip and canonical history response.**

Add `BackpackService.unequip_item`, lock the user/item, require `status=EQUIPPED`, set `ACTIVE`, log `UsageAction.UNEQUIP`, commit and refresh. Add the route and frontend service/button. In the API response builder map `entry.action` to `action_type`; update the schema and view labels/icons.

- [ ] **Step 4: Add purchase idempotency and historical snapshots.**

Read `Idempotency-Key` with FastAPI `Header`, validate 1-128 ASCII characters, query the unique user/key row before mutating, and lock the item/user before creating the exchange. Save item name and unit price snapshots. If the unique constraint wins a race, reload and return the committed exchange rather than charging again. Preserve the existing atomic stock, coin and backpack transaction.

- [ ] **Step 5: Make refund and delete lifecycle-safe.**

Before refund, query both `ACTIVE` and `EQUIPPED` backpack rows. If any required quantity is equipped, return `ITEM_EQUIPPED` without changing exchange status. If active quantity is insufficient, return `INSUFFICIENT_REFUNDABLE_ITEMS` without partial changes. For item deletion, set `is_active=false` when any exchange, backpack or usage-history reference exists; only delete an unreferenced item. Return snapshots in exchange history after the product is archived.

- [ ] **Step 6: Update the shop/backpack UI and verify.**

Add an explicit “卸下” action, show the refund reason and retain the purchase action key across retries. Update `BackpackHistory.vue` to use `action_type`, and ensure action labels cover `add/use/equip/unequip/discard/refund`.

Run: `cd backend && pytest -q tests/test_backpack.py tests/test_shop.py tests/test_audit_fixes.py tests/test_defect_closure.py -k 'purchase or refund or equip or history or item'`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs`
Expected: all lifecycle and idempotency assertions pass.

- [ ] **Step 7: Commit the shop/backpack repair.**

```bash
git add backend/app/api/backpack.py backend/app/schemas/backpack.py backend/app/services/backpack.py backend/app/services/shop.py backend/app/api/shop.py backend/app/schemas/shop.py frontend/src/services/backpack.js frontend/src/services/shop.js frontend/src/views/Backpack.vue frontend/src/views/BackpackHistory.vue frontend/src/views/Shop.vue backend/tests/test_backpack.py backend/tests/test_shop.py backend/tests/test_audit_fixes.py backend/tests/test_defect_closure.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "fix(shop): complete backpack lifecycle and purchase idempotency"
```

### Task 9: Make note tree moves recursive, file-safe, atomic, and scope-limited

**Files:**
- Modify: `backend/app/services/note.py`
- Modify: `backend/app/repositories/note.py`
- Modify: `backend/app/models/note_node.py`
- Modify: `backend/app/api/notes.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/collaboration.py`
- Modify: `frontend/src/services/note.js`
- Modify: `frontend/src/views/NotebookFileManage.vue`
- Modify: `frontend/src/views/Notes.vue`
- Modify: `frontend/src/views/NoteEditor.vue`
- Modify: `backend/tests/test_notes.py`
- Modify: `backend/tests/test_note_sharing.py`
- Modify: `backend/tests/test_defect_closure.py`

**Interfaces:**
- Adds `NoteService.plan_tree_move(node_id, new_parent_id, new_name)` returning old/new paths for every descendant and a filesystem operation list.
- Adds `NoteService.apply_tree_move(plan)` with database and filesystem rollback on any failure.
- Ordinary API dependencies reject tokens with `scope=note_collab`; collaboration endpoints use a dedicated scoped dependency.
- Existing note IDs and content remain stable after folder rename/move.

- [ ] **Step 1: Add failing nested-tree and rollback tests.**

```python
def test_renaming_folder_updates_descendant_db_and_files(client, notebook):
    folder, child_folder, note = create_nested_note_tree(client, notebook)
    old_file = Path(note.content_path)
    response = client.put(f"/api/notes/nodes/{folder.id}", json={"name": "新目录"}, headers=notebook.headers)
    assert response.status_code == 200
    refreshed = get_node(client, note.id, notebook.headers)
    assert refreshed["path"].startswith("/新目录/")
    assert Path(refreshed["content_path"]).exists()
    assert not old_file.exists()


def test_note_tree_move_restores_db_and_files_when_rename_fails(client, notebook, monkeypatch):
    tree = create_nested_note_tree(client, notebook)
    before = snapshot_tree(tree)
    monkeypatch.setattr(Path, "rename", fail_on_second_rename)
    response = move_tree(client, tree.root.id, tree.destination.id, notebook.headers)
    assert response.status_code == 500
    assert snapshot_tree(tree) == before
```

Add a scoped-token test: a note collaboration token can use the collaboration endpoint but receives 403 from `/api/users/me` and `/api/todos`.

- [ ] **Step 2: Run the current note tests and record failures.**

Run: `cd backend && pytest -q tests/test_notes.py tests/test_note_sharing.py tests/test_defect_closure.py -k 'folder or move or scope'`
Expected: descendant paths/files remain stale, combined operations can partially persist, or scoped tokens are accepted by ordinary endpoints.

- [ ] **Step 3: Build a recursive tree-move plan.**

Use the existing node repository to load the complete descendant set. Validate same-notebook ownership, destination type, name conflicts and cycle prevention before touching disk. Compute each descendant's database `path` and `content_path` from the new ancestor path while retaining node IDs and note contents.

- [ ] **Step 4: Execute database and filesystem changes as one recoverable operation.**

Create a staging directory under the notebook's existing storage root. Move files/directories into staging names first, update database paths inside the current SQLAlchemy transaction, flush, then rename staged entries to final paths. On any exception, restore original filesystem names and call `rollback`; leave all node rows unchanged. Reuse the existing note migration lock for startup repair and the service-level lock/transaction for normal operations.

- [ ] **Step 5: Enforce collaboration token scope.**

Add a dependency that decodes the token and requires `scope == "note_collab"` plus a notebook/node authorization check. Keep `get_current_user` for normal access and explicitly reject scoped tokens there. Apply the scoped dependency only to collaboration WebSocket/HTTP routes; do not weaken normal notebook ownership checks.

- [ ] **Step 6: Update note UI state and verify.**

Keep the editor content and tree data when move/rename fails, show a retryable error, and refresh the tree only after a successful response. Add request sequence protection to node selection if the move changes the selected path.

Run: `cd backend && pytest -q tests/test_notes.py tests/test_note_sharing.py tests/test_defect_closure.py -k 'folder or move or scope'`
Run: `cd frontend && node --test src/views/defect-closure-regressions.test.mjs src/views/ui-regressions.test.mjs`
Expected: nested paths and files move together, failures restore both layers, and scoped tokens cannot call ordinary APIs.

- [ ] **Step 7: Commit the notes repair.**

```bash
git add backend/app/services/note.py backend/app/repositories/note.py backend/app/models/note_node.py backend/app/api/notes.py backend/app/api/auth.py backend/app/collaboration.py frontend/src/services/note.js frontend/src/views/NotebookFileManage.vue frontend/src/views/Notes.vue frontend/src/views/NoteEditor.vue backend/tests/test_notes.py backend/tests/test_note_sharing.py backend/tests/test_defect_closure.py frontend/src/views/defect-closure-regressions.test.mjs
git commit -m "fix(notes): make tree moves recursive and atomic"
```

### Task 10: Close project status and milestone lifecycle gaps

**Files:**
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/services/project.py`
- Modify: `backend/app/api/projects.py`
- Modify: `frontend/src/services/project.js`
- Modify: `frontend/src/views/Projects.vue`
- Modify: `frontend/src/views/ProjectDetail.vue`
- Modify: `frontend/src/utils/displayLabels.js`
- Modify: `backend/tests/test_projects.py`
- Modify: `backend/tests/test_defect_closure.py`
- Modify: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- `ProjectStatus` is the single enum with `planning`, `active`, `completed`, and `archived`.
- Adds `POST /api/projects/{project_id}/start` as an idempotent transition from `planning` to `active`; existing update rejects unknown new states.
- Phase status uses the same normalized status vocabulary or an explicit phase mapping consumed by all views.
- Existing `POST /api/projects/milestones/{milestone_id}/reach` is exposed through `projectService.reachMilestone` and the project detail UI.

- [ ] **Step 1: Add failing status and UI tests.**

```python
def test_project_start_is_idempotent(client, auth_headers, project):
    first = client.post(f"/api/projects/{project.id}/start", headers=auth_headers)
    second = client.post(f"/api/projects/{project.id}/start", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "active"


def test_project_rejects_unknown_status(client, auth_headers, project):
    response = client.put(f"/api/projects/{project.id}", headers=auth_headers, json={"status": "unknown"})
    assert response.status_code == 422
```

Add frontend source assertions for a start action, milestone reach action, and a centralized project/phase status label map.

- [ ] **Step 2: Run project tests and capture failures.**

Run: `cd backend && pytest -q tests/test_projects.py tests/test_defect_closure.py -k 'status or milestone or start'`
Run: `cd frontend && node --test src/views/ui-regressions.test.mjs`
Expected: arbitrary status is accepted or the start/reach UI path is absent.

- [ ] **Step 3: Enforce statuses and preserve legacy reads.**

Use a Pydantic enum for new project and phase updates. Add service-level transition validation so `planning -> active`, `active -> completed/archived`, and `completed -> archived` are valid; repeated target transitions return the current object. Unknown historical values are returned as `unknown` for display and excluded from active counts, but cannot be written by new requests.

- [ ] **Step 4: Add start and milestone controls.**

Add the start endpoint and service method. Add `projectService.startProject` and `reachMilestone`; update `Projects.vue` and `ProjectDetail.vue` with action locks, success messages and retryable errors. Map phase statuses through `displayLabels.js` so no raw English value is shown when a Chinese label exists.

- [ ] **Step 5: Verify and commit.**

Run: `cd backend && pytest -q tests/test_projects.py tests/test_defect_closure.py -k 'status or milestone or start'`
Run: `cd frontend && node --test src/views/ui-regressions.test.mjs src/views/defect-closure-regressions.test.mjs`
Expected: project start, status validation, phase labels and milestone reach all pass.

```bash
git add backend/app/schemas/project.py backend/app/models/project.py backend/app/services/project.py backend/app/api/projects.py frontend/src/services/project.js frontend/src/views/Projects.vue frontend/src/views/ProjectDetail.vue frontend/src/utils/displayLabels.js backend/tests/test_projects.py backend/tests/test_defect_closure.py frontend/src/views/ui-regressions.test.mjs
git commit -m "fix(projects): complete project status lifecycle"
```

### Task 11: Secure refresh tokens and avatar uploads, and serialize frontend refreshes

**Files:**
- Modify: `backend/app/services/auth.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/schemas/user.py`
- Modify: `backend/app/api/users.py`
- Modify: `frontend/src/services/auth.js`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/stores/auth.js`
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_mcp_security.py`
- Modify: `backend/tests/test_defect_closure.py`
- Modify: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- `POST /api/auth/refresh` rotates a persisted refresh token once and returns a new access/refresh pair.
- Adds `POST /api/auth/logout` to revoke the submitted refresh token; client logout still clears local state even if the request fails.
- Refresh tokens carry `jti`; only a hash is stored.
- Avatar upload accepts only files whose content signature matches the allowed extension and MIME family, with the existing size limit.
- `authStore.refreshAccessToken()` returns one shared Promise while a refresh is in flight.

- [ ] **Step 1: Add failing security and concurrency tests.**

```python
def test_refresh_token_is_single_use(client, login_payload):
    token = client.post("/api/auth/login", data=login_payload).json()["refresh_token"]
    first = client.post("/api/auth/refresh", json={"refresh_token": token})
    second = client.post("/api/auth/refresh", json={"refresh_token": token})
    assert first.status_code == 200
    assert second.status_code == 401


def test_avatar_rejects_fake_image_content(client, auth_headers):
    response = client.post(
        "/api/users/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 400
```

Add a frontend source test requiring a module-level refresh Promise and ensuring the Axios 401 interceptor awaits the same refresh operation.

- [ ] **Step 2: Run current auth tests and confirm failures.**

Run: `cd backend && pytest -q tests/test_auth.py tests/test_mcp_security.py tests/test_defect_closure.py -k 'refresh or avatar'`
Run: `cd frontend && node --test src/views/ui-regressions.test.mjs`
Expected: the old refresh token can be reused and fake image bytes are accepted; concurrent refresh source assertion fails.

- [ ] **Step 3: Implement persisted refresh-token rotation.**

Add token creation with a random `jti`, store only a SHA-256 hash, and include `user_id`, expiry and replacement metadata. On refresh, lock the token row, reject expired/revoked tokens, revoke the current row, create the replacement and commit both in one transaction. Detect a reused token and revoke the replacement chain for that user before returning 401. Add logout revocation.

- [ ] **Step 4: Serialize frontend refresh requests.**

In `auth.js`/`auth` store, keep a module-scoped `refreshPromise`; return it when present, clear it in `finally`, and only update tokens from the winning response. Ensure the Axios interceptor queues the original request behind that Promise and retries once. A failed refresh logs out once and does not recursively retry.

- [ ] **Step 5: Validate avatar content.**

Read at most the configured maximum bytes, detect PNG/JPEG/GIF/WebP signatures with a standard-library helper, require the detected format to match the allowed extension, then write the file. Reject empty, truncated and MIME-only fake images before creating a public URL. Preserve the existing filename sanitization and size limit.

- [ ] **Step 6: Run and commit.**

Run: `cd backend && pytest -q tests/test_auth.py tests/test_mcp_security.py tests/test_defect_closure.py -k 'refresh or avatar'`
Run: `cd frontend && node --test src/views/ui-regressions.test.mjs src/views/defect-closure-regressions.test.mjs`
Expected: old refresh tokens return 401 after one use, concurrent callers share one refresh, and fake images are rejected.

```bash
git add backend/app/services/auth.py backend/app/api/auth.py backend/app/schemas/user.py backend/app/api/users.py frontend/src/services/auth.js frontend/src/services/api.js frontend/src/stores/auth.js backend/tests/test_auth.py backend/tests/test_mcp_security.py backend/tests/test_defect_closure.py frontend/src/views/ui-regressions.test.mjs
git commit -m "fix(auth): rotate refresh tokens and validate avatar content"
```

### Task 12: Run full integration, migration, browser, version, and deployment gates

**Files:**
- Modify: `frontend/src/views/defect-closure-regressions.test.mjs`
- Modify: `.harness/strict-playwright-runner.mjs` and the relevant iteration contract files
- Modify: `VERSION`
- Modify: `frontend/package.json` and `frontend/package-lock.json` through `npm run sync:version`
- Modify: `android/app/build.gradle` only for the required monotonically increasing `versionCode`
- Create: `docs/superpowers/reports/2026-09-15-lifequest-defect-closure-verification.md`
- Verify: `deploy/healthcheck.sh`, deployment workflow files and live API endpoint

**Interfaces:**
- Frontend test discovery runs all `src/*/*.test.mjs` files with `npm test`.
- Browser contracts cover the user-visible flows and fail on console errors, unexpected requests, stale responses, horizontal overflow or missing retry states.
- Release metadata uses root `VERSION` as the only semantic version source.

- [ ] **Step 1: Add remaining frontend contract tests.**

Cover these exact flows in `defect-closure-regressions.test.mjs`:

1. Home loads an active habit with `is_active=true`, completes it, pauses it and resumes it.
2. Coin history sends `coin_type`, `skip`, and reads `transactions`.
3. Budget and debt forms send canonical fields and preserve forms on errors.
4. Finance edit shows update feedback and inactive-account errors are actionable.
5. Backpack history uses `action_type`, and unequip/refund controls remain consistent.
6. Folder rename/move preserves selected note state after success and preserves data after failure.
7. Project start and milestone reach use action locks and retryable errors.
8. Refresh callers share one Promise and do not loop after a 401.

- [ ] **Step 2: Run the complete backend and frontend suites before release edits.**

Run: `cd backend && pytest -q`
Run: `cd frontend && npm test`
Run: `cd frontend && npm run check:version`
Expected: zero failures. Any failure blocks version/release edits and is fixed in the owning task.

- [ ] **Step 3: Run migration and data-integrity checks.**

Run the migration suite against a legacy copy and a fresh database. Verify:

- repeated startup migrations do not change row counts after the first run;
- `total_experience` backfill matches level thresholds plus current experience;
- duplicate refresh/exchange keys are handled deterministically;
- note tree repair has a filesystem backup and restores on injected failure;
- archived products remain readable in exchange, backpack and history responses;
- old coin rows remain unchanged while display uses `type`.

Run: `cd backend && pytest -q tests/test_defect_migrations.py tests/test_notes.py -k 'migration or move'`

- [ ] **Step 4: Run strict browser contracts at all required viewports.**

Run the existing strict runner at `375x812`, `768x1024`, `1024x900`, and `1440x1000` with an authenticated fixture. Store JSON results and screenshots under the dated harness iteration directory. The run must include the live pause/resume request and record method, URL, status, response body and deployed version. A local 200 is not accepted as online evidence.

- [ ] **Step 5: Resolve the online pause failure using captured evidence.**

For the live request:

- 401: verify access-token persistence and refresh retry;
- 404: verify the deployed frontend base URL and `/api/todos` route prefix;
- 422: compare deployed schema with `HabitResponse`/pause route;
- 5xx: inspect deployed backend logs and migration state.

Only change the corresponding deployment/API configuration after the failing response identifies the layer. Repeat the same request after deployment and require 200 with `is_active` toggled and the interval persisted.

- [ ] **Step 6: Update release version and verify the production build.**

Set `VERSION` to `1.14.6`, then run:

```bash
cd frontend
npm run sync:version
npm run check:version
npm test
npm run build
```

Read the current Android `versionCode`, increment it by exactly one, keep `versionName` sourced from root `VERSION`, and run the Android metadata checks. Do not hardcode `1.14.6` in application code.

- [ ] **Step 7: Run final verification and write the report.**

Run:

```bash
cd backend && pytest -q
cd backend && python -m compileall app
cd frontend && npm test
cd frontend && npm run check:version
cd frontend && npm run build
git diff --check
```

Write `docs/superpowers/reports/2026-09-15-lifequest-defect-closure-verification.md` with exact commands, counts, migration results, browser evidence paths, online pause response, known warnings and any residual risks. Mark a defect verified only when its dynamic evidence exists.

- [ ] **Step 8: Commit the release evidence.**

```bash
git add VERSION frontend/package.json frontend/package-lock.json android/app/build.gradle frontend/src/views/defect-closure-regressions.test.mjs .harness docs/superpowers/reports/2026-09-15-lifequest-defect-closure-verification.md
git commit -m "chore: close LifeQuest defect verification"
```

### Task 13: 串行化笔记附件上传与删除

**背景：**最终复核发现，图片上传先在 API 路由写入附件文件，再调用未获取笔记本锁的 `NoteService.create_attachment`。并发删除可能在数据库记录和文件系统之间留下孤立附件。本任务是 NOTE-04 的复核跟进，不改变本次修复范围之外的架构。

**涉及文件：**
- 修改：`backend/app/api/notes.py`
- 修改：`backend/app/services/note.py`
- 修改：`backend/tests/test_notes.py`
- 如有必要，修改：`backend/tests/test_note_sharing.py`

**验收要求：**
- 图片文件写入和附件记录提交必须在与节点/笔记本删除相同的跨进程笔记本锁内完成。
- 获取锁后重新读取笔记并复核写权限；不能依赖加锁前读取的 ORM 对象。
- 删除先完成时，上传返回 404，且不留下附件记录或上传文件；上传先完成时，后续删除必须同时清理记录和文件。
- 附件写入或数据库提交失败时，回滚数据库并移除本次上传生成的文件。
- 不增加外键或数据库迁移；沿用现有笔记本锁和删除文件暂存机制。
- 使用独立进程和真实临时 SQLite/文件系统回归测试覆盖竞态顺序及失败清理。

**验证：**
- 先运行新增回归测试并确认其在旧实现上因竞态行为失败，再实现最小修复。
- 运行：`cd backend && pytest -q tests/test_notes.py tests/test_note_sharing.py`
- 最终集成时重新运行完整后端测试套件，并记录精确结果。

## Execution order and parallelism

Run Task 1 first because it defines migrations and shared regression fixtures. Then run Tasks 2 and 3 sequentially because they share habit/date semantics. Tasks 4, 5, 6 and 7 can be dispatched in parallel after Task 1, but Task 6 and Task 7 both touch finance files, so an integrator must serialize their commits or resolve only deliberate overlapping changes. Task 8 depends on the Task 4 coin direction and Task 1 exchange columns. Task 9 can run independently after Task 1. Task 10 can run independently after Task 1. Task 11 depends on the Task 1 refresh-token model. Task 12 is sequential after Tasks 2-11. Task 13 is a post-review follow-up and runs after Task 12.

Recommended execution mode: `superpowers:subagent-driven-development`, one fresh worker per task with a review after each commit. If executed inline, use `superpowers:executing-plans` and stop at every task's test/commit checkpoint.

## Self-review checklist

- [ ] Every defect range in the coverage map has a task and at least one automated assertion.
- [ ] The homepage root cause is fixed at both response serialization and frontend defensive comparison.
- [ ] Online pause failure is treated as an evidence-gathering release gate, not guessed at from local behavior.
- [ ] Financial amount direction, account state, ownership, category type, budget periods and nullable updates have separate assertions.
- [ ] Note operations cover database paths, real files, rollback and scoped authentication together.
- [ ] Note attachment uploads and destructive mutations share the notebook lock, with both process orderings covered by real filesystem/database assertions.
- [ ] New database structures use the existing startup migration path and preserve old rows.
- [ ] Version changes happen only in the final release task and start from the current root `VERSION`.
- [ ] No task depends on a vague placeholder, an unstated external feature, or an uncommitted prerequisite.
