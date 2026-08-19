# LifeQuest 修仙闭环硬化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复最终分支审查发现的闭环缺口，使现实待办能够真实推动境界、奖励、宗门、功法、NPC 和渡劫流程。

**Architecture:** 继续使用现有 FastAPI、SQLAlchemy、Vue 3、Pinia 和 Element Plus。后端负责修为状态推进、奖励响应、NPC 稳定人口、功法学习、幂等和迁移；前端只消费服务端状态。每个任务在独立提交后进行独立审查。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Vue 3、Pinia、Node test runner、Vite。

## Global Constraints

- 渡劫最终概率、准备度、失败损失和随机 roll 只能由后端计算；前端只提交 `pill_count`。
- 待办完成必须在同一事务中结算修为、灵石、旧奖励字段和修炼日志；同一完成事件不可重复结算。
- 失败只损失当前小境界修为，不降低境界，不删除功法、装备、格子、宗门记录或 NPC 关系。
- 普通弟子按宗门和人口槽位稳定生成并永久保留；修为按自然日补算，不在每次读取时重新随机。
- 凡界地图对散修可见；仙界/仙官入口只在服务端返回 `ascended=true` 后出现。
- 保留 `.agents/`、`.claude/skills/`、`.codex/`、`frontend/vite-check.log`、`frontend/components.d.ts` 等用户文件，不将其加入提交。

---

### Task 10: 打通境界推进、奖励响应和凡界地图

**Files:**

- Modify: `backend/app/services/cultivation.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/todo.py`, `backend/app/schemas/todo.py`, `backend/app/api/todos.py`, `frontend/src/views/Todos.vue`, `frontend/src/components/layout/Sidebar.vue`, `frontend/src/views/World.vue`。
- Test: `backend/tests/test_cultivation.py`, `backend/tests/test_todos.py`, `frontend/src/views/cultivation-regressions.test.mjs`。

**Interfaces:**

- `CultivationService.settle_todo_reward(...)` 必须返回新的 `RewardSettlement`，并在跨过当前小境界阈值时推进 `minor_stage`；跨过大境界阈值时保留“待渡劫”状态，不绕过渡劫。
- 完成任务、习惯和目标的 response 都包含可选 `cultivation_reward: RewardSettlement`。
- `CultivationOverview` 增加 `today` 和 `recent_rewards`，缺失时返回空数组而不是 `null`。

- [ ] **Step 1: 写失败测试**

```python
def test_todo_completion_returns_cultivation_reward(client, auth_headers, task_id):
    response = client.post(f"/api/todos/tasks/{task_id}/complete", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["cultivation_reward"]["cultivation"] > 0
    assert response.json()["cultivation_reward"]["spirit_stones"] > 0

def test_settlement_advances_minor_stage_but_does_not_bypass_tribulation(db_session, user):
    service = CultivationService(db_session)
    service.set_realm(user.id, "qi_refining", 1, 179)
    service.settle_todo_reward(user.id, "task", 10, "hard")
    profile = service.ensure_profile(user.id)
    assert profile.minor_stage == 2

def test_world_is_mortal_map_for_unascended_user(client, auth_headers):
    response = client.get("/api/cultivation/world", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["nodes"]
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q`。预期 response 缺少 `cultivation_reward` 或小境界仍为 1。

- [ ] **Step 3: 实现最小后端闭环**

将 `DIFFICULTY_FACTORS["hard"]` 固定为 `1.4`。在奖励事务中按当前阈值循环推进小境界；只有奖励结算跨过阈值时推进，进入大境界末期后设置 `ready_for_tribulation=true`，不直接修改 `realm_key`。把 `RewardSettlement` 映射到 Task/Habit/Goal response，并从 `CultivationLog` 查询最近奖励、从待办服务查询今日行动。

- [ ] **Step 4: 实现前端和回归**

待办完成响应优先显示 `cultivation_reward`，旧响应继续 fallback；侧边栏和地图显示“凡界地图”，散修可进入 `/world`。增加 response 字段和地图导航静态测试。

- [ ] **Step 5: 运行并提交**

运行后端目标测试、前端回归、`npm run build` 和 `git diff --check`，提交：`feat(cultivation): complete progression reward loop`。

### Task 11: 持久化普通弟子和自然日修为

**Files:**

- Modify: `backend/app/models/world.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/cultivation.py`, `backend/app/api/cultivation.py`, `frontend/src/views/Npcs.vue`, `frontend/src/views/Sects.vue`。
- Test: `backend/tests/test_cultivation.py`。

**Interfaces:**

- `Npc` 增加 `population_index`、`is_generated`、`cultivation`、`cultivation_updated_on`、`cultivation_locked`，并以 `sect_id + population_index` 唯一约束稳定标识普通弟子。
- `CultivationService.meet_npc(user_id, sect_key, population_index) -> NpcSummary` 首次创建并永久保存普通弟子。
- `CultivationService.refresh_npc_cultivation(npc, today)` 只按缺失自然日补算一次。
- `GET /api/cultivation/npcs` 返回固定核心 NPC 和最近遇见的普通弟子；接口不为未 ascended 用户暴露仙官数据，但凡界普通弟子属于可访问的人口域。

- [ ] **Step 1: 写失败测试**

```python
def test_meeting_same_disciple_is_permanent_and_stable(db_session, user):
    service = CultivationService(db_session)
    first = service.meet_npc(user.id, "sect-1-normal-1", 7)
    second = service.meet_npc(user.id, "sect-1-normal-1", 7)
    assert first.id == second.id
    assert first.name == second.name

def test_npc_cultivation_updates_once_per_natural_day(db_session, user):
    service = CultivationService(db_session)
    npc = service.meet_npc(user.id, "sect-1-normal-1", 2)
    before = npc.cultivation
    service.refresh_npc_cultivation(npc, date(2026, 8, 17))
    after = npc.cultivation
    service.refresh_npc_cultivation(npc, date(2026, 8, 17))
    assert after >= before
    assert npc.cultivation == after
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_meeting_same_disciple_is_permanent_and_stable -q`。预期 `meet_npc` 未定义。

- [ ] **Step 3: 实现模型、稳定种子和服务**

使用 `sect_id + population_index` 唯一约束；姓名、性格和初始修为由稳定 hash 生成。普通弟子访问先查询再创建，创建后永不删除；自然日差值乘以 NPC 日修炼速度补算，`cultivation_updated_on` 更新为当前日期。

- [ ] **Step 4: 暴露 NPC 和宗门核心数据**

普通弟子出现在 NPC 关系页和已接触宗门的 NPC 区域；宗门摘要只消费真实服务器数据，不再拼接虚假 NPC 名称。增加跨用户隔离和重复遇见测试。

- [ ] **Step 5: 运行并提交**

运行全部 cultivation tests、`pytest tests/test_todos.py -q`、前端回归和构建，提交：`feat(cultivation): persist ordinary disciple population`。

### Task 12: 功法学习入口、渡劫锁定和幂等完成

**Files:**

- Modify: `backend/app/models/cultivation.py`, `backend/app/models/technique.py`, `backend/app/services/cultivation.py`, `backend/app/api/cultivation.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/todo.py`, `frontend/src/views/Techniques.vue`, `frontend/src/components/cultivation/TribulationProbability.vue`。
- Test: `backend/tests/test_cultivation.py`, `backend/tests/test_todos.py`, `frontend/src/views/cultivation-regressions.test.mjs`。

**Interfaces:**

- `POST /api/cultivation/techniques/{technique_key}/learn` 只允许满足境界和灵石条件的用户，写入 `LearnedTechnique` 并扣除功法灵石成本；重复学习幂等返回当前记录。
- `TribulationPreview.available` 在非当前小境界最终阈值、冷却或 `ascended` 终点时为 `false`，并返回 `lock_reason`。
- `CultivationLog` 增加可选 `source_key` 唯一完成事件键；待办完成传入稳定 todo id，重复并发请求最多产生一条日志和一份奖励。

- [ ] **Step 1: 写失败测试**

```python
def test_user_can_learn_realm_eligible_technique(client, auth_headers, db_session, user):
    service = CultivationService(db_session)
    service.set_realm(user.id, "qi_refining", 1, 0)
    response = client.post("/api/cultivation/techniques/steady-breath/learn", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["learned"] is True

def test_tribulation_preview_locks_non_final_minor_stage(db_session, user):
    service = CultivationService(db_session)
    preview = service.get_tribulation_preview(user.id)
    assert preview.available is False
    assert preview.lock_reason
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q`。预期学习路由和 `lock_reason` 未定义。

- [ ] **Step 3: 实现服务端规则**

学习接口验证用户、境界、余额和重复记录；功法配置只接受已学习记录。渡劫预览在锁定时仍展示服务器计算的门槛信息，但不能提交；前端按钮禁用并显示锁定原因。为待办完成事件建立唯一键并用条件更新/事务冲突处理保证并发幂等。

- [ ] **Step 4: 前端状态和错误文案**

功法库对未学习功法展示“学习”操作；渡劫概率块在 `available=false` 时显示原因，不显示可执行成功率按钮。错误优先显示 `response.data.detail`。

- [ ] **Step 5: 运行并提交**

运行后端全量、前端回归和构建，提交：`feat(cultivation): close learning and tribulation gates`。

### Task 13: 并发、迁移和总览数据硬化

**Files:**

- Modify: `backend/app/main.py`, `backend/app/database.py`, `backend/app/repositories/cultivation.py`, `backend/app/services/cultivation.py`, `backend/app/schemas/cultivation.py`, `frontend/src/views/Sects.vue`。
- Test: `backend/tests/test_cultivation.py`, `backend/tests/test_notes.py`, `frontend/src/views/cultivation-regressions.test.mjs`。

- [ ] **Step 1: 写失败测试**

覆盖：两个请求首次创建 profile 只保留一条；两个进程完成同一待办只产生一份 `CultivationLog`；SQLite 旧记录清理后唯一索引可重复迁移；总览返回今日行动和最近奖励；宗门筛选快速变化只接受最新响应。

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_notes.py -q`。记录每个新测试的预期失败原因。

- [ ] **Step 3: 实现事务和迁移**

首次 profile 使用数据库 upsert/唯一冲突重读；待办完成使用条件更新或行锁并以 `source_key` 约束日志；迁移使用 SQLAlchemy 方言分支处理 SQLite、PostgreSQL、MySQL 和 MSSQL 的日期回填及索引创建。宗门筛选采用请求序号或 AbortController。

- [ ] **Step 4: 运行并提交**

执行后端全量、前端全量静态测试、构建和 `git diff --check`，提交：`fix(cultivation): harden persistence and overview data`。

### Task 14: 全量验证和最终审查

**Files:**

- Create: `docs/superpowers/reports/2026-08-17-lifequest-cultivation-closure-verification.md`。

- [ ] **Step 1: 运行后端和前端全量测试**

运行 `pytest -q`、三组 Node 测试、`npm run build`，记录实际通过数和 warning。

- [ ] **Step 2: 运行浏览器检查**

检查 375px、768px、1024px、1440px 的首页、待办、修炼、地图、宗门、功法、NPC、渡劫；记录未手测的动态状态，不将静态断言写成视觉结果。

- [ ] **Step 3: 编写报告、检查差异并提交**

只提交验证报告和必要的生产修复；保留用户未跟踪文件。完成后进行 whole-branch review，Critical/Important 必须清零。
