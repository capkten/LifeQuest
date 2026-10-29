# Cultivation Retreat & Random Encounter System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建融合番茄钟与修仙机缘的“闭关专注”与“奇遇机缘”系统，将现实深度工作时长转化为修为灵石并触发随机机缘事件。

**Architecture:** 后端在 FastAPI + SQLAlchemy 架构下引入 `CultivationRetreat`、`EncounterEvent`、`UserEncounterRecord` 数据模型，通过 `CultivationRetreatService` 统一管理会话状态机、时间防作弊核验与奇遇概率引擎，并打通待办自动完成与 MCP 工具；前端在 Vue 3 + Pinia 下封装 `useCultivationRetreat` 状态机，结合新中式水墨呼吸倒计时组件 `RetreatCountdownRing` 与水墨卷轴弹窗 `EncounterScrollDialog`，在首页工作台及待办列表无缝接入。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite/PostgreSQL, pytest, Vue 3, Pinia, Vite, Element Plus, Lucide Vue Next, MCP Python SDK.

**Spec:** `docs/superpowers/specs/2026-10-04-cultivation-retreat-and-encounters-design.md`

## Global Constraints

- 仓库根目录 `VERSION` 保持单源事实；发布或集成时若有版本跃迁需同步更新并校验。
- 日期时间边界与中国时区计算必须严格遵循 `backend/app/timezone.py` 和 `Asia/Shanghai` 契约。
- 业务操作遵循严格的所有权隔离：`todo_id` 必须归属当前调用用户。
- 事务一致性：闭关结算、经验提升、灵石发放、奇遇道具入库必须在单个数据库事务内原子提交。
- 单用户并发锁：任何时刻单个用户仅允许一个处于 `active` 状态的闭关会话。
- 保护工作区中既有的未跟踪文件与设计图，不清理、不暂存、不覆盖。

## Review Focus

- **时间篡改/作弊结算**：客户端上报过早或伪造流逝时间；服务端必须以 `now() - started_at` 为唯一标准，流逝时间低于计划 80% 判定为中途放弃，不触发奇遇。
- **并发重复启动**：网络抖动或双击导致连续两个 `start` 请求；数据库和接口需在同用户下互斥，返回明确 `409 Conflict`。
- **跨用户任务关联**：传入非当前用户的 `todo_id`；接口必须返回 `404` 或 `403`，禁止将他人的任务标记完成。
- **页面刷新/应用退后台后状态丢失**：前端必须支持读取 `GET /api/cultivation/retreat/active` 并在页面刷新后自动校准剩余倒计时。
- **奇遇奖励发放异常**：背包物品不存在或数据损坏时整个事务回滚，用户不会出现“修为增加了但奇遇报错导致状态悬挂”的半成功状态。

---

### Task 1: 闭关与奇遇数据模型与数据库注册

**Files:**
- Create: `backend/app/models/cultivation_retreat.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_retreat_models.py`

**Interfaces:**
- Consumes: `backend/app/models/base.py` (`Base`), `backend/app/timezone.py` (`get_china_now`)
- Produces: `CultivationRetreat`, `EncounterEvent`, `UserEncounterRecord` ORM 模型，供后续服务层与数据库初始化调用

- [ ] **Step 1: 编写数据模型与导出的失败测试**

```python
# backend/tests/test_retreat_models.py
import pytest
from backend.app.models import CultivationRetreat, EncounterEvent, UserEncounterRecord

def test_models_importable_and_schema_defined():
    assert CultivationRetreat.__tablename__ == "cultivation_retreats"
    assert EncounterEvent.__tablename__ == "encounter_events"
    assert UserEncounterRecord.__tablename__ == "user_encounter_records"
```

- [ ] **Step 2: 运行测试验证失败**

运行: `pytest backend/tests/test_retreat_models.py`  
预期: FAIL with `ImportError: cannot import name 'CultivationRetreat'`

- [ ] **Step 3: 实现 `backend/app/models/cultivation_retreat.py` 并在 `__init__.py` 中导出**

定义 `CultivationRetreat`（字段：`id`, `user_id`, `todo_id`, `target_duration`, `actual_duration`, `status`, `started_at`, `ended_at`, `exp_gained`, `coins_gained`, `encounter_id`, `encounter_result`, `created_at`）、`EncounterEvent`（字段：`id`, `title`, `story_text`, `rarity`, `min_realm_level`, `reward_type`, `reward_payload`, `weight`）、`UserEncounterRecord`。

- [ ] **Step 4: 运行测试验证通过**

运行: `pytest backend/tests/test_retreat_models.py`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/cultivation_retreat.py backend/app/models/__init__.py backend/tests/test_retreat_models.py
git commit -m "feat(cultivation): add cultivation retreat and encounter data models"
```

---

### Task 2: 奇遇事件种子库与随机事件判定引擎

**Files:**
- Create: `backend/app/services/encounter_engine.py`
- Create: `backend/app/data/seed_encounters.py`
- Test: `backend/tests/test_encounter_engine.py`

**Interfaces:**
- Consumes: `EncounterEvent`, `UserEncounterRecord`
- Produces: `EncounterEngine.roll_encounter(db, user_id, realm_level, duration_minutes, streak_days) -> Optional[EncounterEvent]`

- [ ] **Step 1: 编写概率计算与事件抽取的失败测试**

```python
# backend/tests/test_encounter_engine.py
from backend.app.services.encounter_engine import EncounterEngine, calculate_encounter_probability

def test_probability_bounds():
    assert calculate_encounter_probability(15, 0) == 0.15
    assert calculate_encounter_probability(60, 10) <= 0.60
    assert calculate_encounter_probability(0, 0) >= 0.10
```

- [ ] **Step 2: 运行测试验证失败**

运行: `pytest backend/tests/test_encounter_engine.py`  
预期: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现种子数据与 `EncounterEngine`**

在 `seed_encounters.py` 中初始化 12+ 种涵盖凡品、灵品、玄品、仙品的东方水墨修仙奇遇故事；实现 `calculate_encounter_probability` 与带权重的随机抽取算法，按境界门槛过滤。

- [ ] **Step 4: 运行测试验证通过**

运行: `pytest backend/tests/test_encounter_engine.py`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/encounter_engine.py backend/app/data/seed_encounters.py backend/tests/test_encounter_engine.py
git commit -m "feat(cultivation): implement random encounter engine and seed pool"
```

---

### Task 3: 闭关服务层 `CultivationRetreatService` 与核心规则

**Files:**
- Create: `backend/app/services/cultivation_retreat.py`
- Create: `backend/app/schemas/cultivation_retreat.py`
- Test: `backend/tests/test_retreat_service.py`

**Interfaces:**
- Consumes: `CultivationRetreat`, `EncounterEngine`, `CultivationService`, `CoinService`
- Produces: `CultivationRetreatService.start_retreat`, `.complete_retreat`, `.abort_retreat`, `.get_active_retreat`

- [ ] **Step 1: 编写闭关生命周期与时间防作弊失败测试**

```python
# backend/tests/test_retreat_service.py
def test_start_retreat_blocks_concurrent_active(db, test_user):
    # 启动一个 active 会话后，再次启动必须抛出已存在进行中会话的异常
    ...

def test_early_abort_no_encounter(db, test_user):
    # 时长不足 80% 提前出关，status 标记 aborted 且 encounter 为 None
    ...
```

- [ ] **Step 2: 运行测试验证失败**

运行: `pytest backend/tests/test_retreat_service.py`  
预期: FAIL

- [ ] **Step 3: 实现 Schema 与 `CultivationRetreatService`**

实现启动、校验并发、计算时长、经验与灵石奖励发放、奇遇联动以及事务原子提交。

- [ ] **Step 4: 运行测试验证通过**

运行: `pytest backend/tests/test_retreat_service.py`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/cultivation_retreat.py backend/app/schemas/cultivation_retreat.py backend/tests/test_retreat_service.py
git commit -m "feat(cultivation): implement cultivation retreat service with anti-cheat timing"
```

---

### Task 4: API 路由接入与待办任务联动

**Files:**
- Create: `backend/app/api/cultivation_retreat.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_retreat_api.py`

**Interfaces:**
- Consumes: `CultivationRetreatService`, `get_current_user`
- Produces: `/api/cultivation/retreat/*` HTTP REST 接口

- [ ] **Step 1: 编写 API 鉴权、跨用户隔离与关联任务一键完成的失败测试**

```python
# backend/tests/test_retreat_api.py
def test_retreat_api_rejects_foreign_todo(client, user_token, other_user_todo):
    response = client.post("/api/cultivation/retreat/start", json={"target_duration": 25, "todo_id": other_user_todo.id}, headers=user_token)
    assert response.status_code in (403, 404)
```

- [ ] **Step 2: 运行测试验证失败**

运行: `pytest backend/tests/test_retreat_api.py`  
预期: FAIL with 404 Not Found (路由尚未注册)

- [ ] **Step 3: 实现 API 路由并在 `main.py` 挂载**

注册 `POST /start`、`GET /active`、`POST /{id}/complete`、`POST /{id}/abort`、`GET /history`、`GET /encounters/catalog`。并在结算时支持 `mark_todo_complete` 联动。

- [ ] **Step 4: 运行测试验证通过**

运行: `pytest backend/tests/test_retreat_api.py`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/cultivation_retreat.py backend/app/main.py backend/tests/test_retreat_api.py
git commit -m "feat(api): expose cultivation retreat endpoints with todo linkage"
```

---

### Task 5: MCP 工具扩展与外部 AI 感知

**Files:**
- Modify: `backend/mcp_server.py`
- Test: `backend/tests/test_retreat_mcp.py`

**Interfaces:**
- Consumes: `CultivationRetreatService`, MCP Server tool registry
- Produces: MCP tools: `start_focus_session`, `get_active_focus_session`, `complete_focus_session`

- [ ] **Step 1: 编写 MCP 工具注册与调用失败测试**

```python
# backend/tests/test_retreat_mcp.py
def test_mcp_retreat_tools_registered():
    # 验证 mcp 工具列表中包含专注闭关相关工具
    ...
```

- [ ] **Step 2: 运行测试验证失败**

运行: `pytest backend/tests/test_retreat_mcp.py`  
预期: FAIL

- [ ] **Step 3: 在 `backend/mcp_server.py` 中注册工具函数**

将闭关专注的启动、查询和结算暴露为标准的 MCP Tool。

- [ ] **Step 4: 运行测试验证通过**

运行: `pytest backend/tests/test_retreat_mcp.py`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/mcp_server.py backend/tests/test_retreat_mcp.py
git commit -m "feat(mcp): register focus session and encounter tools"
```

---

### Task 6: 前端 API 通信层与 Composable 状态机

**Files:**
- Create: `frontend/src/services/cultivationRetreat.js`
- Create: `frontend/src/composables/useCultivationRetreat.js`
- Test: `frontend/src/composables/useCultivationRetreat.test.mjs`

**Interfaces:**
- Consumes: `/api/cultivation/retreat/*`
- Produces: `useCultivationRetreat()` 暴露 `activeRetreat`, `startRetreat`, `completeRetreat`, `abortRetreat`, `remainingSeconds`, `isFocusing`

- [ ] **Step 1: 编写前端倒计时与状态转换失败测试**

```javascript
// frontend/src/composables/useCultivationRetreat.test.mjs
import test from 'node:test'
import assert from 'node:assert/strict'
// 测试计时器流转与状态机重置
```

- [ ] **Step 2: 运行测试验证失败**

运行: `node --test frontend/src/composables/useCultivationRetreat.test.mjs`  
预期: FAIL

- [ ] **Step 3: 实现 Service 与 Composable**

实现带防抖和心跳保活的倒计时逻辑，支持页面加载时自动拉取活跃会话并对齐剩余秒数。

- [ ] **Step 4: 运行测试验证通过**

运行: `node --test frontend/src/composables/useCultivationRetreat.test.mjs`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/services/cultivationRetreat.js frontend/src/composables/useCultivationRetreat.js frontend/src/composables/useCultivationRetreat.test.mjs
git commit -m "feat(frontend): add cultivation retreat service and composable state machine"
```

---

### Task 7: 水墨倒计时与沉浸专注交互组件

**Files:**
- Create: `frontend/src/components/retreat/RetreatCountdownRing.vue`
- Create: `frontend/src/components/retreat/CultivationRetreatModal.vue`
- Test: `frontend/src/views/cultivation-retreat.test.mjs`

**Interfaces:**
- Consumes: `useCultivationRetreat`
- Produces: `<CultivationRetreatModal v-model="isOpen" :todo-item="selectedTodo" />`

- [ ] **Step 1: 编写组件挂载与交互断言失败测试**

```javascript
// frontend/src/views/cultivation-retreat.test.mjs
// 验证倒计时圆环参数计算与全屏切换事件
```

- [ ] **Step 2: 运行测试验证失败**

运行: `node --test frontend/src/views/cultivation-retreat.test.mjs`  
预期: FAIL

- [ ] **Step 3: 实现水墨禅意圆环计时器与全屏入定模态框**

加入微光呼吸光晕 CSS 动效、环境白噪音切换、任务关联标签与“中途出关”确认拦截。

- [ ] **Step 4: 运行测试验证通过**

运行: `node --test frontend/src/views/cultivation-retreat.test.mjs`  
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/retreat/RetreatCountdownRing.vue frontend/src/components/retreat/CultivationRetreatModal.vue frontend/src/views/cultivation-retreat.test.mjs
git commit -m "feat(ui): create zen countdown ring and immersive retreat modal"
```

---

### Task 8: 水墨卷轴奇遇弹窗与万象机缘录图鉴

**Files:**
- Create: `frontend/src/components/retreat/EncounterScrollDialog.vue`
- Create: `frontend/src/components/retreat/EncounterCatalogDrawer.vue`
- Test: 扩展 `frontend/src/views/cultivation-retreat.test.mjs`

**Interfaces:**
- Consumes: `encounter_result`, `catalog` 接口数据
- Produces: `<EncounterScrollDialog :result="encounterData" />`, `<EncounterCatalogDrawer v-model="isDrawerOpen" />`

- [ ] **Step 1: 编写奇遇数据渲染与图鉴抽屉交互测试**
- [ ] **Step 2: 运行测试验证失败**
- [ ] **Step 3: 实现水墨卷轴展开动画、印章品质高亮与机缘图鉴收集网格**
- [ ] **Step 4: 运行测试验证通过**
- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/retreat/EncounterScrollDialog.vue frontend/src/components/retreat/EncounterCatalogDrawer.vue
git commit -m "feat(ui): add ink-scroll encounter revelation dialog and catalog drawer"
```

---

### Task 9: 首页与待办页快捷入口接入

**Files:**
- Modify: `frontend/src/components/home/TodayWorkbench.vue`
- Modify: `frontend/src/views/Todos.vue`
- Test: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- Consumes: `CultivationRetreatModal`
- Produces: 首页右上角快捷“入定闭关”按钮；待办列表项“专注此项”菜单

- [ ] **Step 1: 增加首页和待办项闭关触发器的回归测试断言**
- [ ] **Step 2: 运行测试验证失败**
- [ ] **Step 3: 在 `TodayWorkbench.vue` 与 `Todos.vue` 嵌入闭关入口**
- [ ] **Step 4: 运行测试验证通过**
- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/home/TodayWorkbench.vue frontend/src/views/Todos.vue frontend/src/views/ui-regressions.test.mjs
git commit -m "feat(ui): wire retreat focus triggers into workbench and todos views"
```

---

### Task 10: 全量自动化验证与构建核查

**Files:**
- 全局验证（不增加冗余文件）

- [ ] **Step 1: 运行完整后端 pytest 套件**

运行: `cd backend && pytest`  
预期: 全部通过，0 failed

- [ ] **Step 2: 运行前端回归测试与版本校验**

运行: `cd frontend && npm run check:version && npm test`  
预期: 版本 1.14.8 一致，全部测试通过

- [ ] **Step 3: 运行前端生产环境打包**

运行: `cd frontend && npm run build`  
预期: Vite 生产构建成功 (`dist/`)

- [ ] **Step 4: 检查 git 变更状态与分支一致性**

运行: `git status` 与 `git diff --check`  
预期: 无遗留冲突标记，8 个既有未跟踪文档/图片保持原样

---

## 交付与执行建议

本实施计划包含 10 个独立且可被单测验证的任务，覆盖数据持久化、规则防作弊、机缘引擎、前端组件与全量回归。
