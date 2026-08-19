# LifeQuest 稳定性与修仙内容闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复当前审查发现的通用业务缺陷和修仙模块闭环缺口，使每个可见操作都有可理解的结果、每笔资源都有可追溯来源、每个解锁条件都有真实状态机，并通过自动化与浏览器证据完成验收。

**Architecture:** 继续以 FastAPI/SQLAlchemy 作为唯一业务规则和资源结算来源，Vue 3/Pinia 只负责展示服务端状态、提交用户动作和呈现反馈。通用待办奖励、修仙资源、宗门、功法、NPC 和渡劫统一通过事务、唯一键和稳定错误码保证幂等；前端所有加载、空数据、失败、锁定、提交中和成功状态都显式建模。实现按任务拆分，每个任务先写失败测试，再完成最小实现，再进行独立评估。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Vue 3、Pinia、Element Plus、Node.js test runner、Vite、Playwright。

## Global Constraints

- 后端是修为、灵石、功德、贡献、资质、心境、功法效果、渡劫概率、库存和权限的唯一权威来源，前端不能提交最终奖励、概率、准备度或余额。
- 任何完成动作只能产生一笔对应奖励流水；重复请求必须返回已有结算或稳定的“已完成”结果，不能重复增发资源。
- 条件不满足时，只有“请求进行中”可以使用原生 `disabled`；业务锁定按钮保持可点击，通过 `aria-disabled`、锁定原因和 toast/行内提示反馈原因。
- 请求失败不得伪装成空数据；页面必须显示错误信息和重试入口，已有数据刷新失败时保留旧数据并标记刷新失败。
- 所有跨页面错误使用稳定错误码和参数，例如 `INSUFFICIENT_SPIRIT_STONES:100:50`、`SECT_TRIAL_REQUIRED`、`TRIBULATION_PREREQUISITE:habit_streak`；前端集中映射中文文案，并保留未知错误的安全 fallback。
- 待办完成必须在同一事务内结算旧奖励、修为、灵石、功德、资质、心境、贡献和对应日志；事务失败时所有余额和状态都回滚。
- 渡劫失败只扣当前小境界修为，不降低境界，不删除功法、装备、格子、宗门记录、NPC 关系或仙官职位；同一用户同一 UTC 自然日最多一次渡劫。
- 渡劫丹使用现有 `ShopItem` + `BackpackItem` 体系，不另建独立库存表；扣库存必须和写入 `TribulationAttempt`、更新 profile 在同一事务完成。
- 普通弟子按用户、宗门和人口槽位稳定生成并永久保留；重复遇见同一槽位不重复创建 NPC 或重复发放相同事件奖励。
- 功法槽位必须由 `(user_id, slot_type, slot_index)` 数据库唯一约束保护，并在购买时使用行锁或等价的原子更新；价格严格使用设计稿的 `0、100、300、800、2000、5000、12000`，之后按 `2.4` 倍递增。
- 第一阶段只实现凡界真实可玩闭环；飞升后的仙界和仙官必须有最小可玩的资源、任务、地图和渡仙劫循环，不创建只有标题和空列表的页面。
- 读取和修改文本文件使用 UTF-8；不引入与现有技术栈重复的新状态管理、请求库或图标库。
- 每个任务完成后运行该任务的目标测试、`git diff --check`，再进行独立审查；未有 evaluator 证据的项目状态只能是 `implemented`，不能标记为 `verified`。

---

## 1. 问题台账与验收范围

以下编号是本计划的唯一追踪编号。原审查记录保留在 [2026-08-18-lifequest-current-issues-audit.md](D:/codes/LifeQuest/docs/superpowers/reports/2026-08-18-lifequest-current-issues-audit.md)，本计划负责把问题转成可执行任务。

本计划整合并细化此前的通用模块审查、2026-08-17 修仙闭环计划和本轮修仙内容审查；旧计划保留作历史记录，执行顺序以本文件为准。

### 1.1 通用模块问题

| 编号 | 优先级 | 问题 | 验收结果 |
| --- | --- | --- | --- |
| G-01 | P1 | 习惯完成状态契约错误，前端使用 `is_active` 代替 `completed_today` | 今天已完成的习惯明确显示完成，重复点击得到“今日已完成”反馈且不重复领奖 |
| G-02 | P1 | 金币明细查询参数和返回字段不一致 | 筛选收入/支出、分页和总额展示与接口一致 |
| G-03 | P1 | 财务流水加载更多只传页码但后端只按 `skip` 处理 | 第 2 页不会重复第 1 页，筛选变化会清空旧列表并只接受最新响应 |
| G-04 | P1 | 签到响应缺少奖励字段，页面可能提示获得 0 金币/0 经验 | 成功响应包含实际奖励，首页和历史页显示真实奖励 |
| G-05 | P1 | 旧审查发现完成接口可重复领奖，必须保证任务、习惯、目标和子任务幂等 | 并发完成同一对象最多一笔奖励和一条流水 |
| G-06 | P1 | 子任务历史上存在 `goal`/`task` 路径和 `status`/`is_completed` 错位 | 子任务加载、创建、完成、删除都使用 Task 归属和同一字段名 |
| G-07 | P2 | Todos、Shop、Backpack 等页面使用全局操作锁，其他按钮静默 `return` | 每个可点击按钮要么执行，要么解释为什么不能执行 |
| G-08 | P2 | 大量原生 `disabled` 遮蔽业务条件，不提供原因 | 灵石不足、境界不足、已完成、未选择对象等状态都有可见反馈 |
| G-09 | P2 | Finance、Calendar、Notes、Home、Profile 失败时降级为空数据或只写控制台 | 失败态、重试、旧数据保留策略明确，不把网络错误当作“暂无数据” |
| G-10 | P2 | 笔记编辑加载失败后仍显示空编辑器 | 加载失败显示错误和重试，不允许覆盖空内容保存 |
| G-11 | P2 | 笔记工作区创建、重命名、移动缺少提交锁，查看器切换存在旧响应覆盖 | 操作不可重复提交，快速切换只接受最后一次请求 |
| G-12 | P2 | 项目详情创建、完成、保存缺少提交锁，阶段删除没有确认且可能影响任务归属 | 所有写操作有独立锁，危险删除确认并明确任务迁移/阻断策略 |
| G-13 | P2 | Header 用户菜单点击路由后冒泡，菜单可能重新打开 | 菜单项跳转后关闭且不被外层 toggle 重新打开 |
| G-14 | P2 | Notes、Finance、Stats 等搜索/筛选请求存在竞态 | 每次筛选只呈现最新响应，取消或忽略旧请求 |
| G-15 | 历史回归 | 修改用户名导致 JWT 登录态失效 | 当前 token 以稳定用户 ID 识别，改名后 `/me` 仍可访问 |
| G-16 | 历史回归 | 重复用户名或邮箱更新曾直接返回 500 | 重复字段返回稳定 4xx 和字段级提示 |
| G-17 | 历史回归 | 成就曾不会随任务完成自动解锁 | 完成任务、目标、习惯后触发对应成就，重复触发不重复发奖 |

G-15 至 G-17 当前已有回归测试或修复痕迹，实施时不直接重写；必须作为综合回归门禁复核，若测试与浏览器结果不一致，再按 Task 3 补强。

### 1.2 修仙模块问题

| 编号 | 优先级 | 问题 | 验收结果 |
| --- | --- | --- | --- |
| C-01 | P1 | 渡劫丹只参与概率，未校验库存、余额或扣除 | 预览显示拥有数量，尝试时库存不足不能提交，成功/失败都只扣实际使用数量一次 |
| C-02 | P1 | 渡劫只检查最终小境界和冷却，突破前置条件未实现 | 重要目标、习惯连续天数、星级历练、项目阶段、宗门贡献和心境等条件真实参与判定 |
| C-03 | P1 | 宗门试炼只把 `trial_confirmed` 改为 `True` | 试炼有固定内容、条件、进度、奖励、失败保留和完成幂等状态 |
| C-04 | P1 | 功德、贡献、资质、心境和修炼效率没有稳定增长路径 | 每项资源都有来源、上限/衰减、账本日志和页面变化 |
| C-05 | P1 | 学习和装备功法只写关系，不改变效率或任务收益 | 装备方案重算效果，收益结算读取服务端效率并受总上限约束 |
| C-06 | P1 | 功法格子缺少唯一约束/行锁，并发购买可能重复扣款 | 并发购买最多成功一次，余额、格子和流水一致 |
| C-07 | P2 | 高阶格子境界要求只到合体，之后重复；价格实现为 2 倍而不是 2.4 倍 | 每个格子有明确境界门槛，价格表和后续倍率与设计稿一致 |
| C-08 | P2 | 功法类型与格子类型无服务端校验，文案把 `body` 同时叫炼体和身法 | 使用 `main/auxiliary/mind/movement/body` 规范类型，类型不匹配无法装备，文案统一 |
| C-09 | P2 | 目录只有 3 部功法，辅修和新增类型没有真实内容 | 目录覆盖凡界首阶段流派，至少每种槽位有可学习、可装备、有效果的内容 |
| C-10 | P2 | NPC 人口无上限，重复遇见同一 NPC 会无限新增事件 | 每个宗门有稳定人口上限，槽位和相遇事件幂等 |
| C-11 | P2 | 宗门任务偏好、核心传承和贡献只有展示字段 | 宗门偏好影响任务收益/贡献，核心传承影响功法或成长分支，贡献可消费 |
| C-12 | P2 | 隐藏宗门始终过滤，没有现身条件和路径 | 满足条件后隐藏宗门可见，有现身事件，未满足时仍返回明确锁定原因 |
| C-13 | P2 | 地图只有 9 节点且第 2 至第 9 个节点统一筑基 | 地图按星域和项目阶段推进，每个节点有真实入口、锁定条件和完成状态 |
| C-14 | P2 | 飞升后只有 `ascended` 终点标记，没有仙界资源、仙官、任务和仙劫循环 | 飞升后进入真仙循环，仙元/仙石/仙功/官职表现能由现实行动推进 |
| C-15 | P2 | 修仙错误码没有前端中文映射，条件失败常显示“请求冲突” | 每个服务端错误码在页面近距离显示可行动的中文原因 |
| C-16 | P2 | 渡劫准备度只按最近一次习惯和难度平均计算，未体现按时/延期/契合度 | 按设计稿五项权重和任务完成质量计算，并可在 UI 逐项解释 |
| C-17 | P2 | 修仙页面条件按钮、加载失败、快速筛选和并发操作反馈不完整 | 修炼、宗门、功法、NPC、渡劫页面都具备 loading/error/locked/submitting/success/failure 状态 |

### 1.3 必须形成的业务闭环

```text
现实待办/习惯/目标/项目
  -> 一次性奖励账本
  -> 修为、灵石、功德、资质、心境、宗门贡献
  -> 小境界推进与突破前置条件
  -> 宗门试炼/地图节点/功法构筑
  -> 渡劫准备度 + 渡劫丹库存
  -> 服务端渡劫判定与失败保护
  -> 飞升后的仙元、仙石、仙功、官职循环
```

```text
宗门发现 -> 使者接触 -> 入门试炼 -> 加入宗门
  -> 宗门任务/贡献 -> 核心传承/功法效果 -> 任务结算与渡劫契合度

地图节点 -> 真实任务或项目阶段 -> 节点完成
  -> 新区域/NPC/宗门内容 -> 关系事件幂等 -> 功德或贡献奖励
```

任何一条箭头没有数据库字段、API 响应、前端反馈和测试证据，都不能标记为 `verified`。

## 2. 文件边界

执行前先按下面边界确认改动归属。若一个文件同时承担两个任务，只允许共享稳定接口，不在任务间互相改写未定义的字段。

### Backend

- `backend/app/models/`：用户、待办、财务、商城/背包、修炼、宗门、功法、NPC 的持久化字段和唯一约束。
- `backend/app/schemas/`：稳定请求/响应字段、分页结构、奖励和错误信息。
- `backend/app/services/todo.py`、`checkin.py`、`coin.py`、`finance.py`、`achievement.py`：通用业务结算与幂等。
- `backend/app/services/cultivation.py`、`content_catalog.py`：修仙规则、资源账本、内容种子、状态机和结算。
- `backend/app/services/shop.py`、`backpack.py`：渡劫丹商品、背包增减和历史记录。
- `backend/app/api/`：路由参数、异常到 HTTP 状态码的映射。
- `backend/app/main.py`、`backend/app/database.py`：现有启动迁移/兼容逻辑和索引创建。
- `backend/tests/`：接口、服务、并发、迁移、数值模拟和安全回归。

### Frontend

- `frontend/src/services/`：把 UI 参数映射成 API 参数，统一解包响应和错误对象。
- `frontend/src/utils/errorMessage.js`、`frontend/src/utils/displayLabels.js`：错误码与服务端标签集中映射。
- `frontend/src/composables/useToast.js`、`useNoteWorkspace.js`、`useNoteAutosave.js`：操作反馈、编辑锁和请求序号。
- `frontend/src/views/`：页面状态机、条件操作反馈、重试和响应竞态保护。
- `frontend/src/components/cultivation/`、`frontend/src/components/layout/`：修仙展示状态和全局菜单/导航交互。
- `frontend/src/locales/zh-CN.js`：类型、错误、资源和状态中文文案的单一前端来源。
- `frontend/src/views/*.test.mjs`、`frontend/src/composables/*.test.mjs`：Node 回归和静态契约测试。

## 3. 执行前置与严格评估

### Task 0: 建立基线、确认评估模式和完成台账

**Files:**

- Create during execution: `docs/superpowers/reports/2026-08-18-lifequest-stability-baseline.md`
- Create only after user confirms strict evaluation: `.harness/config.json`, `.harness/contract.md`, `.harness/completion-ledger.json`, `.harness/status.json`

**Interfaces:**

- Consumes: 当前分支代码、[审查报告](D:/codes/LifeQuest/docs/superpowers/reports/2026-08-18-lifequest-current-issues-audit.md)、本计划和两份修仙设计文档。
- Produces: 一份测试基线、每个 `G-*`/`C-*` 的 contract item，以及 `planned -> implementing -> implemented -> verified` 状态迁移规则。

- [ ] **Step 1: 记录可重复的基线命令**

运行：

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest -q
cd ..\frontend
node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs
npm run build
git diff --check
```

记录实际通过数、警告、缺失依赖和未认证浏览器限制；禁止把旧的 `192 passed` 或 `33 passed` 直接复制成新结果。

- [ ] **Step 2: 请求严格评估模式确认**

项目类型判定为 `web_fullstack`，推荐 `playwright` 模式，因为任务同时覆盖 API、多个受保护页面、移动端按钮反馈和动态条件状态。`.harness/` 在用户确认前不创建；确认后初始化四个 Harness 文件，并把每个台账项目绑定到本计划编号。

- [ ] **Step 3: 写入 contract 条目**

每个条目至少包含：前置数据、操作、预期 HTTP/DOM 结果、不可接受结果、自动测试命令、浏览器视口和截图/日志证据。例如：

```json
{
  "id": "C-01",
  "state": "planned",
  "precondition": "用户拥有0颗渡劫丹，已满足其他渡劫条件",
  "action": "提交pill_count=1",
  "expect": "409 TRIBULATION_PILL_INSUFFICIENT，profile与attempt均不变",
  "evidence": ["backend/tests/test_cultivation.py", "playwright:cultivation-tribulation-pill"]
}
```

- [ ] **Step 4: 验证台账流程**

执行每个任务后只允许按证据更新状态：代码和目标测试通过为 `implemented`；独立 evaluator 通过且记录命令、截图、控制台和响应证据后才为 `verified`。失败必须回到 `rework_requested` 或 `rewrite_requested`，不能以人工判断跳过。

## 4. 通用模块修复任务

### Task 1: 统一待办、签到、金币和财务接口契约

**Files:**

- Modify: `backend/app/schemas/todo.py`, `backend/app/api/todos.py`, `backend/app/services/todo.py`, `backend/app/schemas/checkin.py`, `backend/app/services/checkin.py`, `backend/app/api/checkin.py`
- Modify: `backend/app/schemas/coin.py`, `backend/app/api/coins.py`, `backend/app/services/coin.py`, `backend/app/repositories/coin_transaction.py`
- Modify: `backend/app/schemas/finance.py`, `backend/app/api/finance.py`, `backend/app/services/finance.py`, `backend/app/repositories/finance.py`
- Test: `backend/tests/test_todos.py`, `backend/tests/test_auth.py`, `backend/tests/test_finance.py`, `backend/tests/test_finance_security.py`, `backend/tests/test_regressions.py`

**Interfaces:**

- `HabitResponse.completed_today: bool`：由 `last_completed_at` 按 UTC 今日计算，不把 `is_active` 当完成状态。
- `CheckinResponse.reward_coins: int`、`reward_exp: int`：与签到事务实际写入的奖励一致。
- `GET /api/coins/history` 保留服务端 `coin_type=earn|spend`、`skip`、`limit` 兼容参数；前端服务负责把 `income|expense` 和 `page` 映射为这些参数，响应固定读取 `transactions`、`count`、`total_earned`、`total_spent`。
- `GET /api/finance/transactions` 统一返回 `{items,total,page,page_size,has_more}`；服务端接受 `page`/`page_size`，旧 `skip` 只作为兼容输入，不能同时造成重复偏移。
- 所有完成响应继续返回旧业务字段，并增加 `cultivation_reward: RewardSettlement | null`，未产生修仙奖励时明确为 `null`。

- [ ] **Step 1: 写失败契约测试**

```python
def test_habit_response_has_completed_today(client, auth_headers, habit_id):
    response = client.get("/api/todos/habits", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()[0]["completed_today"] is False

def test_checkin_response_contains_actual_reward(client, auth_headers):
    response = client.post("/api/checkin", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["reward_coins"] > 0
    assert response.json()["reward_exp"] > 0

def test_coin_history_uses_transactions_and_filter_mapping(client, auth_headers):
    response = client.get("/api/coins/history?coin_type=earn&skip=0&limit=20", headers=auth_headers)
    assert response.status_code == 200
    assert set(("transactions", "count", "total_earned", "total_spent")) <= response.json().keys()

def test_finance_page_two_has_no_page_one_duplicates(client, auth_headers):
    first = client.get("/api/finance/transactions?page=1&page_size=2", headers=auth_headers)
    second = client.get("/api/finance/transactions?page=2&page_size=2", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert {row["id"] for row in first.json()["items"]}.isdisjoint({row["id"] for row in second.json()["items"]})
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py tests/test_finance.py tests/test_regressions.py -q`。

预期：至少有一项因 `completed_today`、签到奖励字段或财务分页返回结构缺失而失败；若基线已经通过，新增测试必须证明其覆盖了原审查中的契约，而不是跳过实现。

- [ ] **Step 3: 实现服务端响应和兼容参数**

在 schema 中增加字段，在 service 层构造实际奖励后再返回；分页先规范化 `page/page_size`，再计算唯一的 `offset=(page-1)*page_size`，禁止 controller 和 repository 各自重复偏移。签到成功、重复签到和异常都返回明确状态，重复签到不能再发奖励。

- [ ] **Step 4: 运行接口回归**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py tests/test_finance.py tests/test_finance_security.py tests/test_regressions.py -q`。

预期：全部 PASS；响应字段、分页集合和签到账本数量与断言一致。

- [ ] **Step 5: 提交**

```powershell
git add backend/app backend/tests
git commit -m "fix(api): align todo checkin and finance contracts"
```

### Task 2: 封堵重复领奖并保留历史功能回归

**Files:**

- Modify: `backend/app/services/todo.py`, `backend/app/models/cultivation.py`, `backend/app/models/coin.py`, `backend/app/services/achievement.py`, `backend/app/api/todos.py`, `backend/app/services/auth.py`, `backend/app/api/auth.py`, `backend/app/services/user.py`, `backend/app/api/users.py`
- Modify: `frontend/src/services/todo.js`, `frontend/src/views/Todos.vue`, `frontend/src/views/EditProfile.vue`, `frontend/src/stores/auth.js`
- Test: `backend/tests/test_todos.py`, `backend/tests/test_auth.py`, `backend/tests/test_users.py`, `backend/tests/test_achievements.py`, `backend/tests/test_regressions.py`, `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**

- `TodoService.complete_task/complete_habit/complete_goal` 使用稳定 `source_key`，状态更新、旧奖励、修仙奖励和成就检查在同一事务中完成。
- 子任务 API 统一为 `/api/todos/subtasks/task/{task_id}`，返回 `is_completed`；前端不再构造 `/goals/...` 路径或读取 `status`。
- JWT `sub` 使用不可变用户 ID；解析旧的用户名 token 时返回 401，不抛 500。
- 用户名/邮箱唯一冲突返回 400 或 409 的稳定 detail，前端显示对应字段错误。

- [ ] **Step 1: 写并发与历史回归测试**

```python
def test_same_task_complete_only_creates_one_reward(client, auth_headers, task_id, db_session):
    from app.models.cultivation import CultivationLog
    first = client.post(f"/api/todos/tasks/{task_id}/complete", headers=auth_headers)
    second = client.post(f"/api/todos/tasks/{task_id}/complete", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert db_session.query(CultivationLog).filter_by(source_key=f"todo:task:{task_id}").count() == 1

def test_username_change_keeps_current_session(client, auth_headers):
    headers = auth_headers
    assert client.put("/api/users/me", headers=headers, json={"username": "new-name"}).status_code == 200
    assert client.get("/api/users/me", headers=headers).json()["username"] == "new-name"

def test_first_task_unlocks_achievement_once(client, auth_headers, task_id, db_session, user):
    client.post(f"/api/todos/tasks/{task_id}/complete", headers=auth_headers)
    client.post(f"/api/todos/tasks/{task_id}/complete", headers=auth_headers)
    from app.models.achievement import UserAchievement
    assert db_session.query(UserAchievement).filter_by(user_id=user.id).count() == 1
```

- [ ] **Step 2: 运行失败或覆盖缺口测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py tests/test_auth.py tests/test_users.py tests/test_achievements.py tests/test_regressions.py -q`。

预期：历史已修复项应全部 PASS；新增并发/流水断言若失败，先修复数据库唯一键或事务边界，不修改测试预期。

- [ ] **Step 3: 对齐完成状态和奖励边界**

用条件更新抢占完成状态；只有 `rowcount == 1` 的请求进入奖励结算。修仙日志、CoinTransaction、AchievementUser 和旧 User 余额共享同一个 commit。重复请求返回当前对象和已结算信息，不再重新调用奖励函数。

- [ ] **Step 4: 运行全部通用回归**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_todos.py tests/test_auth.py tests/test_users.py tests/test_achievements.py tests/test_regressions.py tests/test_task12_review_fixes.py -q`。

预期：PASS；每个完成对象最多一条奖励流水，改名后 token 继续有效，成就不重复发奖。

- [ ] **Step 5: 提交**

```powershell
git add backend/app frontend/src backend/tests
git commit -m "fix(todo): make completion rewards idempotent"
```

### Task 3: 建立全局操作反馈和条件锁定规则

**Files:**

- Modify: `frontend/src/composables/useToast.js`, `frontend/src/utils/errorMessage.js`, `frontend/src/views/Todos.vue`, `frontend/src/views/Shop.vue`, `frontend/src/views/Backpack.vue`, `frontend/src/views/Home.vue`, `frontend/src/views/Finance.vue`, `frontend/src/views/ProjectDetail.vue`
- Modify: `frontend/src/views/Techniques.vue`, `frontend/src/views/Tribulations.vue`, `frontend/src/components/cultivation/TechniqueSlotGrid.vue`, `frontend/src/components/cultivation/TribulationProbability.vue`, `frontend/src/styles/stitch-overrides.css`
- Test: `frontend/src/views/ui-regressions.test.mjs`, `frontend/src/views/cultivation-regressions.test.mjs`

**Interfaces:**

- `useToast().showError(message)` 是条件失败和请求失败的统一近距离反馈；正在提交时使用已有 loading 状态。
- 业务条件按钮采用 `:aria-disabled="blocked"` 和 `@click="explainBlocked(...)"`；只有 `busy/loading/submitting` 使用 `:disabled`。
- `getErrorMessage(error, fallback)` 优先读取 `detail`、错误码和参数，再读取 fallback，未知错误显示“操作失败，请重试”。

- [ ] **Step 1: 写静态交互契约测试**

```js
test('conditional cultivation actions expose an explanation instead of silent return', () => {
  const source = read('src/views/Techniques.vue')
  assert.match(source, /can_purchase|purchaseLockMessage/)
  assert.match(source, /aria-disabled|error\.value/)
})

test('todo and reward pages show request feedback hooks', () => {
  for (const file of ['src/views/Todos.vue', 'src/views/Shop.vue', 'src/views/Backpack.vue']) {
    const source = read(file)
    assert.match(source, /catch|showError|getErrorMessage/)
  }
})
```

- [ ] **Step 2: 运行现有前端回归并确认失败点**

运行：`cd frontend; node --test src/views/ui-regressions.test.mjs src/views/cultivation-regressions.test.mjs`。

预期：现有通过项保持通过；新增断言对没有反馈的页面先失败。

- [ ] **Step 3: 实现条件反馈**

把“灵石不足、境界不足、未选择槽位、已完成、今日已签到、试炼未完成、冷却中”转为可点击说明。按钮文案同时表达状态，例如“需要筑基”“灵石不足”“今日已完成”；提交请求只锁当前动作，并在响应后刷新服务端状态。

- [ ] **Step 4: 运行前端回归和构建**

运行：`cd frontend; node --test src/views/ui-regressions.test.mjs src/views/cultivation-regressions.test.mjs; npm run build`。

预期：Node 测试和 Vite build 均 PASS；构建警告只能记录，不能掩盖失败。

- [ ] **Step 5: 提交**

```powershell
git add frontend/src
git commit -m "fix(ui): explain blocked actions and request failures"
```

### Task 4: 治理加载失败、重试和请求竞态

**Files:**

- Modify: `frontend/src/views/Notes.vue`, `frontend/src/views/NoteEditor.vue`, `frontend/src/composables/useNoteWorkspace.js`, `frontend/src/composables/useNoteAutosave.js`
- Modify: `frontend/src/views/Finance.vue`, `frontend/src/views/FinanceTransactions.vue`, `frontend/src/views/CoinHistory.vue`, `frontend/src/views/Calendar.vue`, `frontend/src/views/Home.vue`, `frontend/src/views/Profile.vue`, `frontend/src/views/Stats.vue`
- Modify: `frontend/src/services/note.js`, `frontend/src/services/finance.js`, `frontend/src/services/stats.js`
- Test: `frontend/src/composables/useNoteAutosave.test.mjs`, `frontend/src/views/ui-regressions.test.mjs`, `frontend/src/views/sects-request-state.test.mjs`

**Interfaces:**

- 每个页面拥有 `loading`、`error`、`retry` 和必要的局部 loading；请求失败不清空旧数据，不把 `catch(() => [])` 作为业务 fallback。
- `useNoteWorkspace` 的 `requestVersion` 或 AbortController 保证查看器只接受最后一次选择；保存/重命名/移动拥有独立提交锁。
- 搜索和筛选请求使用递增序号；响应应用前比较序号，取消请求不显示错误。

- [ ] **Step 1: 写竞态与失败态测试**

```js
test('latest notes request wins', async () => {
  const state = createLatestRequestState()
  const oldRequest = state.start()
  const newRequest = state.start()
  assert.equal(state.accept(newRequest), true)
  assert.equal(state.accept(oldRequest), false)
})

test('note editor keeps an explicit load error instead of blank content', () => {
  const source = read('src/views/NoteEditor.vue')
  assert.match(source, /error|重试/)
  assert.doesNotMatch(source, /catch\s*\([^)]*\)\s*\{\s*note\.value\s*=\s*null/)
})
```

- [ ] **Step 2: 运行失败测试**

运行：`cd frontend; node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs`。

预期：旧请求覆盖、失败后空编辑器或清空列表的断言先失败，或现有实现已通过则补上缺失的页面覆盖。

- [ ] **Step 3: 实现请求状态和序号保护**

先清除旧 timer/AbortController，再递增请求序号；每个 `catch` 保存 `getErrorMessage` 结果并显示 retry；只有首次加载可以显示全屏错误，刷新失败保留旧列表。NoteEditor 在 note 读取成功前禁止保存空 payload。

- [ ] **Step 4: 运行目标测试**

运行：`cd frontend; node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs; npm run build`。

预期：PASS，且 build 不出现新增编译错误。

- [ ] **Step 5: 提交**

```powershell
git add frontend/src
git commit -m "fix(frontend): preserve request errors and latest state"
```

### Task 5: 完成项目、笔记工作区和 Header 的安全操作闭环

**Files:**

- Modify: `frontend/src/views/ProjectDetail.vue`, `frontend/src/views/Projects.vue`, `frontend/src/services/project.js`
- Modify: `frontend/src/views/NotebookFileManage.vue`, `frontend/src/views/Notes.vue`, `frontend/src/services/note.js`, `frontend/src/components/layout/Header.vue`
- Modify: `backend/app/api/projects.py`, `backend/app/services/project.py`, `backend/app/repositories/project.py`, `backend/tests/test_projects.py`, `backend/tests/test_notes.py`
- Test: `frontend/src/views/ui-regressions.test.mjs`, `backend/tests/test_projects.py`, `backend/tests/test_notes.py`

**Interfaces:**

- ProjectDetail 的 `saveEditProject`、`completeProject`、`deleteProject` 各自有 `saving/finishing/deleting` 锁；重复提交不发送第二个请求。
- 删除阶段前服务端返回任务数；如果任务数大于 0，前端确认框必须提供“迁移后删除”或阻止删除的明确结果，不能静默改变任务归属。
- Notebook create/rename/move 使用独立的 `pendingAction`，失败时保留表单和错误文本。
- Header 路由菜单项在 `@click.stop` 后关闭 dropdown；logout 不触发外层 toggle。

- [ ] **Step 1: 写危险操作和重复提交测试**

```python
def test_delete_project_phase_with_tasks_requires_explicit_policy(client, auth_headers, phase_id, task_id):
    response = client.delete(f"/api/projects/phases/{phase_id}", headers=auth_headers)
    assert response.status_code in (400, 409)
    assert "task" in response.json()["detail"].lower()
```

```js
test('header menu links stop propagation and project writes have individual locks', () => {
  assert.match(read('src/components/layout/Header.vue'), /@click\.stop/)
  const source = read('src/views/ProjectDetail.vue')
  assert.match(source, /saving|deleting|finishing/)
})
```

- [ ] **Step 2: 运行目标测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_projects.py tests/test_notes.py -q`; 再运行 `cd frontend; node --test src/views/ui-regressions.test.mjs`。

预期：新测试在策略未实现时失败，既有 notes/project 测试保持可运行。

- [ ] **Step 3: 实现服务端删除策略和前端锁**

服务端删除阶段前统计归属任务，默认返回 `PROJECT_PHASE_HAS_TASKS` 并拒绝隐式删除；如果产品已有迁移接口，必须先明确目标阶段、事务迁移任务，再删除阶段。前端把确认框结果绑定到实际请求，不使用 `window.confirm` 后无条件删除。

- [ ] **Step 4: 运行并提交**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_projects.py tests/test_notes.py -q`; `cd frontend; node --test src/views/ui-regressions.test.mjs; npm run build; git diff --check`。

```powershell
git add backend/app frontend/src backend/tests
git commit -m "fix(workflows): lock project and notebook mutations"
```

## 5. 修仙后端资源和状态机任务

### Task 6: 建立修仙资源账本和现实行动结算

**Files:**

- Modify: `backend/app/models/cultivation.py`, `backend/app/models/todo.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/cultivation.py`, `backend/app/services/todo.py`, `backend/app/services/checkin.py`
- Modify: `backend/app/api/todos.py`, `backend/app/api/cultivation.py`, `backend/app/services/content_catalog.py`, `backend/app/main.py`
- Test: `backend/tests/test_cultivation.py`, `backend/tests/test_todos.py`, `backend/tests/test_content_catalog.py`, `backend/tests/test_regressions.py`

**Interfaces:**

- `CultivationService.settle_todo_reward(user_id, source, base_exp, difficulty, quality, importance, source_key, content_star=1) -> RewardSettlement` 返回 `cultivation`、`spirit_stones`、`merit`、`aptitude_points`、`mind_state_delta`、`contribution`、`efficiency`、`log_id`、`ready_for_tribulation`。
- `CultivationLog` 的 `source_key` 唯一表示一次业务完成；日志同时记录所有资源 delta，不能只记录修为和灵石。
- 任务奖励遵循设计稿：基础值习惯 10、普通任务 15、子任务 8、目标 45、项目阶段 75、里程碑 120、境界试炼目标 180；难度系数 `0.8/1.0/1.35/1.8`，质量按时 `1.0`、提前 `1.05`、延期 `0.75`。
- 资质每日最多由前 8 个奖励任务增加；资质效率为 `min(0.60, 0.04 * sqrt(aptitude_points))`；修炼效率为境界基础速度 + 功法效果 + 资质效率。

- [ ] **Step 1: 写资源闭环和数值测试**

```python
def test_task_reward_updates_all_cultivation_resources_once(db_session, user, task):
    from app.models.cultivation import CultivationLog
    service = CultivationService(db_session)
    before = service.ensure_profile(user.id)
    before_stones = before.spirit_stones
    before_aptitude = before.aptitude_points
    result = service.settle_todo_reward(user.id, "task", 15, "medium", source_key=f"todo:task:{task.id}", content_star=2)
    profile = service.ensure_profile(user.id)
    assert result.cultivation > 0
    assert profile.spirit_stones == before_stones + result.spirit_stones
    assert profile.aptitude_points >= before_aptitude
    assert db_session.query(CultivationLog).filter_by(source_key=f"todo:task:{task.id}").count() == 1

def test_daily_aptitude_gain_stops_after_eight_reward_events(db_session, user):
    service = CultivationService(db_session)
    before = service.ensure_profile(user.id).aptitude_points
    for index in range(9):
        service.settle_todo_reward(user.id, "task", 15, "medium", source_key=f"daily:{index}", content_star=2)
    assert service.ensure_profile(user.id).aptitude_points - before <= 8 * 2
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py -q`。

预期：`RewardSettlement` 当前缺少资源字段或资源仍为 0 时失败。

- [ ] **Step 3: 实现原子结算和境界推进**

在同一事务内创建带 `source_key` 的 `CultivationLog`，计算全部 delta，更新 profile，再更新旧 User 奖励字段。按阈值循环推进小境界；达到大境界最后一层只设置 `ready_for_tribulation`，不跳过前置和渡劫。功德来自习惯/记账/NPC，贡献来自宗门任务，心境按连续习惯、笔记反思和延期质量调整。

- [ ] **Step 4: 运行目标与数值边界测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_todos.py tests/test_content_catalog.py tests/test_regressions.py -q`。

预期：PASS；重复 source key、每日第 9 个任务、跨小境界和旧奖励字段均符合契约。

- [ ] **Step 5: 提交**

```powershell
git add backend/app backend/tests
git commit -m "feat(cultivation): add resource ledger settlement"
```

### Task 7: 实现渡劫丹库存、突破前置和准备度算法

**Files:**

- Modify: `backend/app/models/shop.py`, `backend/app/models/backpack.py`, `backend/app/models/cultivation.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/shop.py`, `backend/app/services/backpack.py`, `backend/app/services/cultivation.py`, `backend/app/services/content_catalog.py`
- Modify: `backend/app/api/cultivation.py`, `backend/app/main.py`, `backend/tests/test_cultivation.py`, `backend/tests/test_shop.py`, `backend/tests/test_backpack.py`

**Interfaces:**

- `ShopItem.item_key: str | None` 为系统商品稳定键；种子商品 `tribulation-pill` 使用现有 ShopItem/BackpackItem。旧用户商品允许为空，系统商品 key 唯一。
- `TribulationPreview.owned_pills: int`、`pill_count`、`pill_bonus`、`available`、`lock_reason`、`prerequisites` 都由服务端计算；预览最多接受 `min(15, owned_pills)`。
- `CultivationService.consume_tribulation_pills(user_id, count) -> int` 在持有锁的 BackpackItem 行上原子扣减，数量不足抛出 `TRIBULATION_PILL_INSUFFICIENT`。
- 突破前置状态至少包括：炼气九层到筑基的一个重要目标、一个习惯连续 7 天、一个三星历练、心境 60；筑基圆满到金丹的一个项目阶段、一个习惯连续 14 天、一个五星历练、贡献 300；金丹圆满到元婴的宗门主线、长期目标阶段、心境 70；更高境界使用高星秘境、宗门主线和境界试炼。
- 准备度使用心境 25%、近 7 日习惯 20%、任务质量 20%、渡劫试炼 20%、功法/宗门契合 15%；质量区分按时、提前和延期；最终概率 `clamp(base + round((readiness-50)/5) + pills*5, 20, 95)`。

- [ ] **Step 1: 写库存和前置失败测试**

```python
def test_tribulation_pills_require_owned_backpack_quantity(client, auth_headers, db_session, user):
    service = CultivationService(db_session)
    service.set_realm(user.id, "qi_refining", 9, 235)
    preview = client.get("/api/cultivation/tribulation/preview?pill_count=1", headers=auth_headers)
    assert preview.status_code == 200
    assert preview.json()["owned_pills"] == 0
    result = client.post("/api/cultivation/tribulation/attempt", headers=auth_headers, json={"pill_count": 1})
    assert result.status_code == 409
    assert "TRIBULATION_PILL_INSUFFICIENT" in result.json()["detail"]

def test_tribulation_prerequisites_are_explainable(db_session, user):
    service = CultivationService(db_session)
    service.set_realm(user.id, "qi_refining", 9, 235)
    preview = service.get_tribulation_preview(user.id, 0)
    assert preview.available is False
    assert "habit_streak" in preview.prerequisites
    assert preview.lock_reason
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_shop.py tests/test_backpack.py -q`。

预期：预览缺少库存字段或空库存仍允许提交时失败。

- [ ] **Step 3: 实现商品种子和同事务扣库存**

为系统商品增加稳定 key 和幂等种子；购买沿用 ShopService 扣灵石并进入 BackpackItem。渡劫时锁定 profile、背包和当日 attempt，先重新计算 preview，校验所有前置和库存，扣除丹药，再写 attempt 和结果。任何异常都 rollback，失败也只扣已使用的丹药。

- [ ] **Step 4: 实现准备度和错误详情**

返回每个 prerequisite 的 `key/label/required/current/satisfied`，把 `ready_for_tribulation` 只作为汇总，不替代逐项条件。任务质量计算完成时间相对 deadline 的提前/按时/延期，习惯计算连续完成天数而不是一周内是否完成过一次。

- [ ] **Step 5: 运行并提交**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_shop.py tests/test_backpack.py -q; git diff --check`。

```powershell
git add backend/app backend/tests
git commit -m "fix(cultivation): enforce tribulation inventory and prerequisites"
```

### Task 8: 把宗门、试炼、隐藏宗门和地图变成真实状态机

**Files:**

- Modify: `backend/app/models/world.py`, `backend/app/models/cultivation.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/cultivation.py`, `backend/app/services/content_catalog.py`
- Modify: `backend/app/api/cultivation.py`, `backend/app/main.py`, `frontend/src/services/cultivation.js`
- Modify: `backend/tests/test_cultivation.py`, `backend/tests/test_content_catalog.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**

- `SectAccessProgress` 增加 `trial_key` 对应的任务进度、`trial_score`、`completed_at`；`trial_status` 使用 `awaiting_messenger -> awaiting_trial -> in_progress -> completed`。
- `CultivationService.update_trial_objective(user_id, sect_key, objective_key, completed=True)` 更新固定试炼目标；`CultivationService.get_sect_access(user_id, sect_key)` 返回目标快照和当前状态。
- `CultivationService.evaluate_hidden_sects(user_id)` 根据已完成事件和 profile 返回可见宗门；测试通过该接口触发现身评估，不直接修改数据库布尔值。
- `backend/tests/conftest.py::count_contribution_logs(db_session, user_id, sect_key)` 按稳定 `source_key` 统计指定宗门试炼的贡献流水，避免测试直接依赖内部 SQL 拼接。
- `complete_sect_trial` 只能在任务目标满足后完成，重复调用返回已完成状态；试炼奖励通过 `CultivationLog`/贡献账本结算一次。
- 隐藏宗门的 `visible` 由服务端根据目标 NPC 事件、心境、地图节点和前置宗门状态计算；未现身不返回可加入的完整数据，只返回可解释锁定原因。
- 世界节点至少提供 `node_key`、`region_key`、`required_realm`、`required_project_phase`、`completed`、`visible`、`lock_reason`；每个星域不是一个统一筑基门槛。

- [ ] **Step 1: 写状态机测试**

```python
def test_sect_trial_requires_objectives_and_rewards_once(db_session, user):
    service = CultivationService(db_session)
    from app.models.world import Sect
    sect = db_session.query(Sect).filter(Sect.kind == "normal").first()
    service.contact_sect_messenger(user.id, sect.sect_key)
    with pytest.raises(PermissionError, match="trial objectives"):
        service.complete_sect_trial(user.id, sect.sect_key)
    service.update_trial_objective(user.id, sect.sect_key, "three_star_expedition", completed=True)
    completed = service.complete_sect_trial(user.id, sect.sect_key)
    repeated = service.complete_sect_trial(user.id, sect.sect_key)
    assert completed.trial_status == repeated.trial_status == "completed"
    assert count_contribution_logs(db_session, user.id, sect.sect_key) == 1

def test_hidden_sect_appears_only_after_reveal_condition(db_session, user):
    service = CultivationService(db_session)
    assert service.get_sects(user.id, kind="hidden") == []
    service.update_trial_objective(user.id, "sect-1-normal-1", "anonymous-sword-path", completed=True)
    service.evaluate_hidden_sects(user.id)
    assert any(item.visible for item in service.get_sects(user.id, kind="hidden"))
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q`。

预期：当前直接把 `trial_confirmed` 改为 `True` 的实现不能满足目标条件断言。

- [ ] **Step 3: 实现宗门试炼和贡献账本**

用固定 trial definition 生成目标快照，用户完成现实任务或项目阶段时更新进度；完成时一次性发放贡献/功德/功法线索，重复请求读取已完成快照。宗门偏好参与任务星级或标签匹配，核心传承提供可学习功法和效果，退出宗门后只保留通用效果。

- [ ] **Step 4: 实现分区地图和隐藏现身**

把设计稿中的星域、城市、秘境、宗门入口和突破地点转成稳定 seed；服务端按用户 profile、项目阶段和已完成节点返回状态。隐藏宗门通过事件或试炼解锁，不在 repository 层无条件 `kind != hidden` 过滤。

- [ ] **Step 5: 运行并提交**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q; git diff --check`。

```powershell
git add backend/app backend/tests frontend/src/services/cultivation.js
git commit -m "feat(cultivation): make sect trials and world progression real"
```

### Task 9: 完成功法目录、类型规则、格子并发和装备效果

**Files:**

- Modify: `backend/app/models/technique.py`, `backend/app/services/cultivation.py`, `backend/app/services/content_catalog.py`, `backend/app/schemas/cultivation.py`, `backend/app/main.py`
- Modify: `backend/app/api/cultivation.py`, `backend/tests/test_cultivation.py`, `backend/tests/test_content_catalog.py`
- Modify: `frontend/src/views/Techniques.vue`, `frontend/src/components/cultivation/TechniqueSlotGrid.vue`, `frontend/src/services/cultivation.js`, `frontend/src/utils/displayLabels.js`, `frontend/src/locales/zh-CN.js`, `frontend/src/views/cultivation-regressions.test.mjs`
- Modify: `backend/tests/conftest.py`

**Interfaces:**

- `Technique.technique_type` 规范为 `main/auxiliary/mind/movement/body`，标签固定为“主修/辅修/心法/身法/炼体”；`Technique.effect_config` 保存结构化效果，禁止前端直接提交效果数值。
- `TechniqueSlot.slot_type` 与五类功法一一对应；`update_loadout` 校验类型、境界、拥有/学习关系、占用格数、冲突标签和格子数量后才批量修改。
- `purchase_slot(user_id, slot_type) -> SlotPurchaseResponse` 在事务内锁定 profile 和当前类型的最大 slot index，按设计价格创建唯一索引保护的下一格。
- `CultivationService.get_slot_purchase_preview(user_id, slot_type)` 返回下一格的价格、境界和余额；`CultivationService.get_equipped_effects(user_id)` 返回服务端聚合后的效果。
- `backend/tests/conftest.py::run_two_transactions(operation)` 使用两个独立 Session 和 barrier 并发调用 operation，返回带 `ok/value/error` 属性的结果列表；它只用于并发测试，不进入生产代码。
- `cultivation_efficiency = realm_base + aptitude_efficiency + min(0.80, equipped_technique_bonus)`；宗门联动效果单独返回，不绕过总上限。

- [ ] **Step 1: 写类型、价格和并发失败测试**

```python
def test_slot_price_and_realm_requirement_follow_design(db_session, user):
    service = CultivationService(db_session)
    service.set_realm(user.id, "foundation", 1, 0)
    profile = service.ensure_profile(user.id)
    profile.spirit_stones = 10000
    db_session.commit()
    assert service.purchase_slot(user.id, "main")["price"] == 100
    assert service.purchase_slot(user.id, "main")["price"] == 300
    assert service.purchase_slot(user.id, "main")["price"] == 800

def test_loadout_rejects_technique_type_mismatch(db_session, user):
    from app.models.technique import Technique
    body_technique = db_session.query(Technique).filter_by(technique_type="body").one()
    with pytest.raises(PermissionError, match="TECHNIQUE_TYPE_MISMATCH"):
        CultivationService(db_session).update_loadout(user.id, {"mind": [body_technique.id]})

def test_concurrent_slot_purchase_cannot_duplicate_index(db_session, user):
    from app.models.technique import TechniqueSlot
    results = run_two_transactions(lambda db: CultivationService(db).purchase_slot(user.id, "main"))
    assert sorted(result.value["slot_index"] for result in results if result.ok) == [0]
    assert db_session.query(TechniqueSlot).filter_by(user_id=user.id, slot_type="main", slot_index=0).count() == 1
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q`。

预期：2 倍价格、类型未校验或并发产生重复 index 时失败。

- [ ] **Step 3: 实现迁移、锁和规则**

增加结构化效果字段和 `(user_id, slot_type, slot_index)` 唯一约束；启动迁移先清理同一用户同一类型的重复 slot，保留最早记录并按 index 重新编号，再创建唯一索引。价格使用固定前七项和 `floor(previous * 2.4)`；境界要求按炼气至渡劫的 14 格规则递进。

- [ ] **Step 4: 扩充首阶段功法内容并接入结算**

至少为主修、辅修、心法、身法、炼体各提供 2 部凡界功法，给出境界、成本、占用格数、冲突标签和效果。学习扣灵石一次，重复学习幂等；装备后刷新 profile 效率，任务结算读新效率。`body` 不再同时显示为“炼体”和“身法”。

- [ ] **Step 5: 运行并提交**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q`; `cd frontend; node --test src/views/cultivation-regressions.test.mjs; npm run build`。

```powershell
git add backend/app frontend/src backend/tests
git commit -m "feat(cultivation): enforce technique slots and effects"
```

### Task 10: 固定 NPC 人口、事件幂等和宗门内容关系

**Files:**

- Modify: `backend/app/models/world.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/cultivation.py`, `backend/app/services/content_catalog.py`, `backend/app/main.py`
- Modify: `backend/app/api/cultivation.py`, `backend/tests/test_cultivation.py`, `backend/tests/test_content_catalog.py`
- Modify: `frontend/src/views/Npcs.vue`, `frontend/src/views/Sects.vue`, `frontend/src/components/cultivation/NpcTimeline.vue`, `frontend/src/services/cultivation.js`

**Interfaces:**

- `Npc` 继续使用 `(user_id, sect_id, population_index)` 唯一约束；每个星级/宗门的 `population_limit` 由 seed 明确返回，超出时返回 `NPC_POPULATION_LIMIT`。
- `CultivationService.population_limit(sect_key) -> int` 返回该宗门的固定人口上限；`CultivationService.count_npc_events(user_id, npc_id, event_key) -> int` 仅用于服务层和测试验证幂等结果。
- `meet_npc(user_id, sect_key, population_index) -> NpcSummary` 首次创建、重复读取同一 NPC；`NpcEvent` 对 `(user_id,npc_id,event_key)` 唯一，重复相遇只刷新关系，不重复发奖。
- 固定核心 NPC 使用宗门目录真实姓名、角色和传承职责，不用所有宗门共享的三个人名。
- NPC 事件奖励进入功德/贡献/心境账本，页面显示事件、奖励和下一步行动。

- [ ] **Step 1: 写人口和事件测试**

```python
def test_same_population_slot_is_stable_and_event_is_idempotent(db_session, user):
    service = CultivationService(db_session)
    first = service.meet_npc(user.id, "sect-1-normal-1", 0)
    second = service.meet_npc(user.id, "sect-1-normal-1", 0)
    assert first.id == second.id
    assert service.count_npc_events(user.id, first.id, "met") == 1

def test_npc_population_limit_is_enforced(db_session, user):
    service = CultivationService(db_session)
    for index in range(service.population_limit("sect-1-normal-1")):
        service.meet_npc(user.id, "sect-1-normal-1", index)
    with pytest.raises(PermissionError, match="NPC_POPULATION_LIMIT"):
        service.meet_npc(user.id, "sect-1-normal-1", service.population_limit("sect-1-normal-1"))
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q`。

预期：重复调用仍创建多条事件或不存在人口上限时失败。

- [ ] **Step 3: 实现稳定人口和自然日修为**

使用稳定 hash 生成姓名、初始修为和速度；访问时按缺失自然日补算一次，更新 `cultivation_updated_on`，不在每次读取时随机。重复相遇在同一事务内先查 NPC 和事件，再决定是否插入。

- [ ] **Step 4: 接入宗门核心和事件收益**

从 `SECT_CATALOG` 读取真实核心 NPC、宗门偏好、核心传承和事件；事件完成写入资源日志，宗门页/NPC 页消费同一响应，不在前端拼装虚假数据。

- [ ] **Step 5: 运行并提交**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q`; `cd frontend; npm run build`。

```powershell
git add backend/app frontend/src backend/tests
git commit -m "fix(cultivation): stabilize npc population and events"
```

### Task 11: 建立飞升后的最小仙界和仙官循环

**Files:**

- Modify: `backend/app/models/cultivation.py`, `backend/app/models/world.py`, `backend/app/schemas/cultivation.py`, `backend/app/services/cultivation.py`, `backend/app/services/content_catalog.py`
- Modify: `backend/app/api/cultivation.py`, `backend/app/main.py`, `backend/tests/test_cultivation.py`, `backend/tests/test_content_catalog.py`
- Modify: `backend/tests/conftest.py`
- Create during implementation: `frontend/src/views/Immortal.vue`, `frontend/src/views/Officials.vue`, `frontend/src/services/immortal.js`
- Modify: `frontend/src/router/index.js`, `frontend/src/components/layout/Sidebar.vue`, `frontend/src/views/Cultivation.vue`

**Interfaces:**

- 飞升成功将 profile 进入 `true_immortal`/真仙初期，保留凡界功法、宗门、NPC 和历史；overview 返回 `ascended=true` 及仙界资源。
- `CultivationProfile` 增加或等价映射 `immortal_cultivation`、`immortal_stones`、`immortal_merit`、`official_power`、`official_performance`，所有增量进入日志。
- `GET /api/cultivation/immortal`、`GET /api/cultivation/officials` 在 `ascended=false` 返回 403 `ASCENSION_REQUIRED`；飞升后返回真实地图、官职、任务和锁定条件。
- 仙界任务使用现有现实待办，仙元公式为基础任务奖励 × 难度 × 重要性 × 质量 × 2.0 × 境界倍率；仙界功法与仙官加成总和不超过 +25%。
- `backend/tests/conftest.py::ready_for_ascension_user` 构造已满足渡劫前置且处于渡劫圆满的测试用户；它只用于飞升后集成测试。

- [ ] **Step 1: 写飞升后访问与结算测试**

```python
def test_immortal_pages_are_locked_before_ascension(client, auth_headers):
    assert client.get("/api/cultivation/immortal", headers=auth_headers).status_code == 403
    assert client.get("/api/cultivation/officials", headers=auth_headers).status_code == 403

def test_ascension_preserves_mortal_progress_and_starts_immortal_loop(db_session, ready_for_ascension_user, monkeypatch):
    service = CultivationService(db_session)
    user = ready_for_ascension_user
    monkeypatch.setattr(service, "roll", lambda probability: True)
    service.attempt_tribulation(user.id, 0)
    overview = service.get_overview(user.id)
    assert overview.ascended is True
    assert service.get_immortal_overview(user.id).realm_key == "true_immortal"
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q`。

预期：当前 `ascended` 只能表示终点，或仙界路由不存在时失败。

- [ ] **Step 3: 实现仙界资源和官职状态**

增加仙界境界阈值、仙劫目标、仙石/仙功/表现变更日志和官职晋升条件；飞升时只切换领域，不清空凡界成长。仙界跨大境界继续使用服务端预览、丹药库存、冷却和失败保护。

- [ ] **Step 4: 实现前端非空页面**

Immortal 页面展示当前仙元、仙石、仙界节点、可执行的现实任务入口和锁定条件；Officials 页面展示官职、仙功、表现、任务和晋升动作。飞升前侧栏隐藏入口但直接访问得到可解释 403 页面，不出现空白页面。

- [ ] **Step 5: 运行并提交**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_content_catalog.py -q`; `cd frontend; npm run build; git diff --check`。

```powershell
git add backend/app frontend/src backend/tests
git commit -m "feat(cultivation): add the post-ascension progression loop"
```

## 6. 修仙前端状态和错误契约

### Task 12: 完成修炼、宗门、功法、NPC、地图和渡劫页面交互

**Files:**

- Modify: `frontend/src/services/cultivation.js`, `frontend/src/utils/errorMessage.js`, `frontend/src/utils/displayLabels.js`, `frontend/src/locales/zh-CN.js`, `frontend/src/stores/cultivation.js`
- Modify: `frontend/src/views/Cultivation.vue`, `frontend/src/views/World.vue`, `frontend/src/views/Sects.vue`, `frontend/src/views/Techniques.vue`, `frontend/src/views/Npcs.vue`, `frontend/src/views/Tribulations.vue`
- Modify: `frontend/src/components/cultivation/CultivationStatusBar.vue`, `RealmProgress.vue`, `ResourceSummary.vue`, `RewardToast.vue`, `TechniqueSlotGrid.vue`, `MapNode.vue`, `NpcTimeline.vue`, `TribulationProbability.vue`, `frontend/src/components/layout/Sidebar.vue`
- Test: `frontend/src/views/cultivation-regressions.test.mjs`, `frontend/src/views/sects-request-state.test.mjs`, `frontend/src/views/localization-regressions.test.mjs`

**Interfaces:**

- `cultivationService` 所有请求按 `{data, error, signal}` 约定返回，错误保留 `response.data.detail`；页面不重新猜测权限或资源余额。
- 修炼总览统一消费 `overview.today`、`recent_rewards`、`resource deltas`；待办完成后的 reward toast 显示修为、灵石、功德、贡献、资质和心境变化。
- 条件操作展示 `lock_reason`/`prerequisites`，请求中只锁当前按钮，失败提供重试，成功重新拉取 overview/library。
- Sects filters、Notes-like lists 和 Tribulations pill preview 使用请求序号/AbortController；旧响应不能覆盖当前选择。

- [ ] **Step 1: 写页面契约测试**

```js
test('tribulation page explains inventory and prerequisite locks', () => {
  const source = read('src/views/Tribulations.vue')
  assert.match(source, /owned_pills|pillCount/)
  assert.match(source, /lock_reason|prerequisite|errorMessage/)
})

test('cultivation pages expose loading, error and retry states', () => {
  for (const file of ['src/views/Cultivation.vue', 'src/views/World.vue', 'src/views/Sects.vue', 'src/views/Npcs.vue']) {
    const source = read(file)
    assert.match(source, /loading/)
    assert.match(source, /error|重试/)
  }
})

test('all cultivation type labels are consistent', () => {
  const locale = read('src/locales/zh-CN.js')
  assert.match(locale, /movement/)
  assert.match(locale, /body/)
})
```

- [ ] **Step 2: 运行失败测试**

运行：`cd frontend; node --test src/views/cultivation-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/localization-regressions.test.mjs`。

预期：缺少字段映射、错误码映射或页面 retry 时失败。

- [ ] **Step 3: 实现服务端状态优先的页面状态机**

为每个页面明确 `loading -> ready/error`、`locked -> explain`、`submitting -> success/failure` 分支。渡劫页显示基础率、五项准备度、准备度加成、丹药加成、最终率、库存和失败损失；功法页显示类型冲突、价格、境界和效果；宗门页显示试炼目标进度；地图页显示区域锁定条件；NPC 页显示真实事件和奖励。

- [ ] **Step 4: 统一错误和交互文案**

在 `errorMessage.js` 和 `zh-CN.js` 增加所有 C-01 至 C-17 相关错误码，未知码显示原始 detail 的安全中文 fallback。所有条件按钮用图标 + 文本，不能只改变颜色或只使用无提示的 `disabled`。

- [ ] **Step 5: 运行并提交**

运行：`cd frontend; node --test src/views/cultivation-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/localization-regressions.test.mjs; npm run build; git diff --check`。

```powershell
git add frontend/src
git commit -m "feat(cultivation): expose progression states and errors"
```

## 7. 数据迁移、并发和兼容性

### Task 13: 完成旧数据库迁移和跨模块并发验证

**Files:**

- Modify: `backend/app/main.py`, `backend/app/database.py`, `backend/app/models/technique.py`, `backend/app/models/shop.py`, `backend/app/models/cultivation.py`, `backend/app/models/world.py`
- Modify: `backend/tests/test_startup_config.py`, `backend/tests/test_note_migration.py`, `backend/tests/test_task13_review_fixes.py`, `backend/tests/test_cultivation.py`, `backend/tests/test_todos.py`
- Create during execution: `docs/superpowers/reports/2026-08-18-lifequest-stability-migration-report.md`

**Interfaces:**

- 启动迁移必须对 SQLite、PostgreSQL 和现有测试 double 使用安全的 `get_columns`/`NoSuchTableError` 分支；重复启动不重复添加字段、数据或索引。
- 旧 `CultivationLog.source_key is null` 数据保留；新完成事件强制生成 source key。旧 ShopItem 的 nullable `item_key` 不被错误填充成重复 key。
- 迁移前检测重复 slot/NPC/event，按稳定规则合并或重新编号并记录数量；迁移失败不启动服务。

- [ ] **Step 1: 写迁移和并发测试**

```python
def test_startup_migration_is_idempotent_and_inspector_compatible(monkeypatch):
    run_startup_migrations(monkeypatch)
    run_startup_migrations(monkeypatch)
    assert migration_columns_are_unique()

def test_concurrent_same_task_and_slot_preserve_single_ledger(db_session, user, task_id):
    results = run_concurrent_completion_and_slot_purchase(user.id, task_id)
    assert results.reward_log_count == 1
    assert results.slot_indexes == [1]
```

- [ ] **Step 2: 运行失败测试**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_startup_config.py tests/test_note_migration.py tests/test_task13_review_fixes.py tests/test_cultivation.py tests/test_todos.py -q`。

预期：至少验证当前迁移 double、SQLite lock、唯一约束和重复请求路径，而不只依赖单线程 happy path。

- [ ] **Step 3: 实现迁移和锁重试**

所有唯一索引创建前先查询并修复重复数据；SQLite 锁错误按现有重试策略重试并重新读取结果，非锁错误原样抛出。Profile、slot、source log、NPC event 和 attempt 的冲突都必须有明确的“读取胜者”路径。

- [ ] **Step 4: 运行全量后端验证并写迁移报告**

运行：`cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q`，记录通过数、失败数、警告和耗时；把迁移前后字段、索引、重复数据处理和回滚证据写入报告。

- [ ] **Step 5: 提交**

```powershell
git add backend/app backend/tests docs/superpowers/reports/2026-08-18-lifequest-stability-migration-report.md
git commit -m "fix(data): harden cultivation and reward migrations"
```

## 8. 最终验证和交付闭环

### Task 14: 用 Harness、浏览器和全量测试完成独立验收

**Files:**

- Modify after evaluator feedback: `.harness/contract.md`, `.harness/completion-ledger.json`, `.harness/status.json`
- Create: `.harness/iterations/<iteration-id>/` evaluator artifacts
- Create: `docs/superpowers/reports/2026-08-18-lifequest-stability-and-cultivation-closure-verification.md`

**Interfaces:**

- Harness evaluator 读取 contract，执行 API/Node/Playwright 检查，输出 PASS/REWORK/REWRITE 和证据路径；evaluator 不修改业务代码。
- 最终报告必须区分：自动测试、已认证浏览器操作、未验证的外部条件；没有认证会话时不能把受保护动态页面写成已手测。

- [ ] **Step 1: 运行全量自动化**

运行：

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest -q
cd ..\frontend
node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs
npm run build
git diff --check
```

预期：后端、前端 Node 测试、构建和 whitespace 检查全部 PASS；警告逐条记录，不把 warning 当 pass。

- [ ] **Step 2: 执行 Playwright 合同流程**

在 `375px`、`768px`、`1024px`、`1440px` 检查：登录、首页、待办完成反馈、习惯重复点击、签到奖励、金币/财务分页、笔记失败重试、项目危险删除、修炼总览、世界地图、宗门试炼、功法购买/装备、NPC 重复相遇、渡劫丹不足、渡劫失败保护和飞升锁定。检查 DOM 状态、网络响应、控制台错误、横向滚动和截图。

- [ ] **Step 3: 验收关键经济不变量**

使用独立测试用户验证：重复完成不增发、重复签到不增发、无丹不能用丹、丹药扣除数量正确、渡劫失败保留关系/功法/格子、格子并发不重复扣款、隐藏宗门未解锁不可加入、飞升前仙界返回 403、飞升后仙元可以增长。

- [ ] **Step 4: 处理评估结果**

PASS 的 contract item 才改为 `verified`；REWORK 修复现有实现后重跑同一流程；REWRITE 重新按 contract 设计当前 item。任何控制台异常、空白页面、无反馈按钮、旧响应覆盖新状态或账本不一致都阻止最终完成。

- [ ] **Step 5: 编写最终报告并完成 whole-branch review**

最终报告至少包含：问题编号到代码/测试/截图的映射、自动测试实际输出、浏览器视口、未验证限制、遗留 warning、迁移证据和 Harness ledger 状态。Critical/Important 问题必须为零；未达成的 item 必须保留 `rework_requested`，不能用“已有测试通过”替代浏览器或账本证据。

## 9. 完成定义

本计划只有同时满足下面条件才算完成：

1. G-01 至 G-14、C-01 至 C-17 均有实现任务、目标测试和验收证据；G-15 至 G-17 的历史修复回归全部通过。
2. 待办到资源账本、资源到账到境界推进、境界到突破前置、前置到渡劫、渡劫到飞升、飞升到仙界/仙官的每条链路都能由真实接口和数据库记录串起来。
3. 所有条件失败按钮可点击并说明原因；所有请求失败可重试；所有写操作有提交锁；所有竞态场景只接受最新响应。
4. `implemented` 和 `verified` 状态在 Harness 台账中分开，最终报告只把 evaluator 通过项标为 `verified`。
5. 未认证浏览器、缺失依赖、无法复现的动态状态和构建 warning 都在最终报告中明确标记，不作过度结论。

## 10. 执行方式

计划完成并保存到 `docs/superpowers/plans/2026-08-18-lifequest-stability-and-cultivation-closure.md`。执行时有两种方式：

1. **Subagent-Driven（推荐）**：按任务分派新 subagent，每个任务完成后进行两阶段审查和 Harness 验证，适合通用模块与修仙模块并行推进。
2. **Inline Execution**：在当前会话按任务批次执行，每完成一个批次暂停做测试、差异检查和用户复核。

开始执行前先选择其中一种方式，并按 Task 0 确认是否启用 Playwright 严格评估；在确认前不创建 `.harness/`，也不修改业务代码。
