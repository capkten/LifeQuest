# LifeQuest MCP 第一批实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现可由页面创建和撤销的个人 MCP 访问令牌，并补齐待办、财务、项目三大领域的 MCP 核心新增、修改、完成和删除能力。

**Architecture:** 在现有 FastAPI、SQLAlchemy 和 JWT 体系上新增 `MCPAccessToken` 模型、Token service 和受 JWT 保护的管理 API。MCP 继续复用现有领域 service，通过 SSE `Authorization`、stdio 环境变量或兼容性工具登录解析用户；Profile 页面只调用 Token 管理 API，明文令牌只在创建成功后的组件内存中存在一次。所有领域写操作集中在 `backend/mcp_server.py` 的薄适配器中，不直接改数据库余额、奖励或业务状态。

**Tech Stack:** Python 3、FastAPI、SQLAlchemy、Pydantic、FastMCP 1.9.4、pytest、Vue 3、axios、Node test runner、Vite。

**Spec:** `docs/superpowers/specs/2026-09-14-lifequest-mcp-design.md`

## Global Constraints

- Token 使用 `lq_mcp_` 前缀加密码学随机值；默认有效期 90 天，允许 1 至 365 天，不提供无限期令牌。
- Token 数据库存储 SHA-256 哈希、短前缀和生命周期元数据；明文只在创建响应中返回一次，列表、日志和撤销响应不得返回明文。
- SSE 使用 `Authorization: Bearer <lq_mcp_token>`，stdio 使用 `LIFEQUEST_MCP_TOKEN`，兼容性入口为 `login_with_token(token)`。
- `LIFEQUEST_MCP_SERVICE_USER_ID` 单独配置不再授予权限；如果配置，必须与有效 Token 解析出的用户一致。
- 用户返回使用公开字段白名单或 `UserResponse`，绝不返回 `password_hash`。
- MCP 日期输入使用 ISO 8601；业务默认日期使用 `Asia/Shanghai` 的 `app.timezone.today()`。
- 复用现有领域 service、schema、事务和权限规则，不新增第二套业务数据库或用户体系。
- 第一批先写失败测试，再写最小实现；每个任务在目标测试通过后单独提交。
- 任何 subagent 只能使用 `gpt-5.6-luna`，不得选择其它模型。
- 除非明确是发布版本变更，不修改根目录 `VERSION`；本计划不升级版本。
- 保留工作区中与本计划无关的用户改动，只暂存当前任务文件；所有文本文件使用 UTF-8。

## 文件职责

- `backend/app/models/mcp_access_token.py`：Token 表结构和生命周期字段。
- `backend/app/schemas/mcp_access_token.py`：创建请求、列表元数据和一次性创建响应。
- `backend/app/services/mcp_access_token.py`：生成随机值、哈希查验、更新时间、撤销和用户边界。
- `backend/app/api/auth.py`：用现有 Web JWT 保护 Token 创建、列表和撤销 API。
- `backend/app/models/__init__.py`：注册新模型，使启动时 `Base.metadata.create_all` 发现新表。
- `backend/mcp_server.py`：MCP 认证上下文、SSE 包装、公开用户序列化以及待办/财务/项目适配器。
- `frontend/src/services/mcpToken.js`：Profile 页面使用的 Token API 封装。
- `frontend/src/views/Profile.vue`：Token 列表、创建表单、一次性展示、复制和撤销。
- `backend/tests/test_mcp_auth.py`：Token 生命周期、Web API、传输认证和敏感字段测试。
- `backend/tests/test_mcp_security.py`：更新旧的服务账号和会话绑定断言。
- `backend/tests/test_mcp_crud.py`：待办、财务、项目完整生命周期和跨用户隔离。
- `frontend/src/views/ui-regressions.test.mjs`：Profile Token 区域的静态回归测试。
- `docs/API.md`、`.env.example`：用户配置和连接示例。

### 测试 fixture 约定

- `mcp_crud_db` fixture 创建全部数据库表和一个测试用户，临时将 `mcp_server.SessionLocal` 指向该测试会话并绑定 `_auth_user_id`，yield `(db, user)`，测试结束时恢复认证上下文并清理表。
- 财务余额断言通过 `mcp_server.list_accounts()` 查询当前用户账户，不在测试中依赖未定义的辅助函数或直接修改余额。
- `mcp_notes_db` 沿用现有笔记测试 fixture 的 `(db, user)` 返回值和认证上下文约定；Task 2 的认证示例自行创建所需用户，避免依赖测试执行顺序。

---

### Task 1: 建立 MCP Token 模型、服务和管理 API

**Files:**

- Create: `backend/app/models/mcp_access_token.py`
- Create: `backend/app/schemas/mcp_access_token.py`
- Create: `backend/app/services/mcp_access_token.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/api/auth.py`
- Create: `backend/tests/test_mcp_auth.py`

**Interfaces:**

- `MCPAccessTokenService(db).create_token(user_id: UUID, data: MCPAccessTokenCreate) -> tuple[MCPAccessToken, str]` 返回 ORM 记录和仅本次可见的明文 Token。
- `MCPAccessTokenService(db).list_tokens(user_id: UUID) -> list[dict]` 只返回元数据，包含 `id/name/token_prefix/created_at/last_used_at/expires_at/revoked_at/status`。
- `MCPAccessTokenService(db).authenticate(raw_token: str) -> Optional[UUID]` 对无效、过期、撤销或格式错误 Token 统一返回 `None`，有效 Token 更新 `last_used_at` 后返回 `user_id`。
- `MCPAccessTokenService(db).revoke(token_id: UUID, user_id: UUID) -> dict` 只处理当前用户 Token；已撤销重复调用保持幂等，其他用户和不存在记录统一按不可访问处理。
- `POST /api/auth/mcp-tokens` 接收 `{name, expires_in_days}`，响应是元数据加 `token`；`GET` 返回元数据数组；`DELETE` 返回撤销后的元数据。

- [ ] **Step 1: 写失败测试**

~~~python
from app.models.mcp_access_token import MCPAccessToken

def test_mcp_token_is_returned_once_and_only_hash_is_persisted(client, db_session):
    client.post(
        "/api/auth/register",
        json={"username": "token-owner", "email": "token-owner@example.com", "password": "testpassword123"},
    )
    jwt_token = client.post(
        "/api/auth/login",
        data={"username": "token-owner", "password": "testpassword123"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post(
        "/api/auth/mcp-tokens",
        json={"name": "Claude Desktop", "expires_in_days": 30},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token"].startswith("lq_mcp_")
    assert payload["status"] == "active"

    stored = db_session.query(MCPAccessToken).filter_by(id=payload["id"]).one()
    assert stored.token_hash != payload["token"]
    assert len(stored.token_hash) == 64

    listed = client.get("/api/auth/mcp-tokens", headers=headers)
    assert "token" not in listed.json()[0]
    assert "token_hash" not in listed.json()[0]
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_auth.py::test_mcp_token_is_returned_once_and_only_hash_is_persisted -q`

预期：因模型、service 和路由不存在而失败。

- [ ] **Step 3: 添加模型和 schema**

建立 `mcp_access_tokens` 表，字段为 `id`、`user_id`、`name`、`token_prefix`、唯一 `token_hash`、`created_at`、`last_used_at`、`expires_at` 和 `revoked_at`。创建 schema 限制名称 1 至 100 个字符、有效期 1 至 365 天，默认 90 天；元数据 schema 显式声明 `status`，创建响应单独增加 `token`。

在 `backend/app/models/__init__.py` 导入新模型并加入 `__all__`，使现有 FastAPI 和 MCP 的 `Base.metadata.create_all` 都能建表。

- [ ] **Step 4: 实现 service**

用 `secrets.token_urlsafe(32)` 生成随机值，完整 Token 为 `lq_mcp_` 加随机值；用 `hashlib.sha256(raw.encode("utf-8")).hexdigest()` 保存哈希，前 16 个字符作为列表前缀。所有时间使用 UTC；比较 SQLite 返回的 naive datetime 前按 UTC 解释。

`authenticate` 只按哈希查询，有效记录更新 `last_used_at` 并提交；过期或撤销返回 `None`。`revoke` 按 `id + user_id` 查询，找不到抛出不可访问错误，已撤销记录直接返回原元数据。

- [ ] **Step 5: 接入 JWT 路由**

在 `backend/app/api/auth.py` 用现有 `get_current_user`、`get_db` 增加三个函数式路由。创建路由返回一次性 Token，列表和删除路由只返回 `MCPAccessTokenMetadata`；非法 UUID 由 FastAPI 返回 422，跨用户删除返回 404。

- [ ] **Step 6: 验证生命周期和提交**

补充过期、撤销、重复撤销、名称/有效期边界和跨用户删除测试，确认列表/撤销没有 `token`、`token_hash`。运行 `cd backend && ./venv/bin/pytest tests/test_mcp_auth.py -q && git diff --check`，提交：

~~~bash
git add backend/app/models/mcp_access_token.py backend/app/schemas/mcp_access_token.py backend/app/services/mcp_access_token.py backend/app/models/__init__.py backend/app/api/auth.py backend/tests/test_mcp_auth.py
git commit -m "feat(auth): add MCP access token lifecycle"
~~~

### Task 2: 接入 MCP Token 鉴权、公开序列化和传输包装

**Files:**

- Modify: `backend/mcp_server.py`
- Modify: `backend/tests/test_mcp_security.py`
- Modify: `backend/tests/test_mcp_auth.py`

**Interfaces:**

- `_serialize(obj)` 支持 ORM、日期、UUID、dict/list 和 Pydantic `model_dump(mode="json")`。
- `_serialize_public_user(user) -> dict` 只返回 `UserResponse` 公开字段。
- `login_with_token(token: str) -> Any` 绑定当前 MCP 会话，响应不得回显 Token。
- `MCPTokenAuthMiddleware(app)` 校验 SSE Bearer header；无 header 仍允许兼容性 `login`，业务工具拒绝未认证调用。
- `_resolve_user_id(db)` 解析 session、context-local token 和 `LIFEQUEST_MCP_TOKEN`，并校验可选 service user ID。

- [ ] **Step 1: 更新旧测试并写失败测试**

~~~python
from app.models.user import User


def test_service_user_id_without_token_is_rejected(db_session, monkeypatch):
    user = User(
        username="mcp-service-user",
        email="mcp-service-user@example.com",
        password_hash="unused",
    )
    db_session.add(user)
    db_session.commit()
    monkeypatch.setenv("LIFEQUEST_MCP_SERVICE_USER_ID", str(user.id))
    monkeypatch.delenv("LIFEQUEST_MCP_TOKEN", raising=False)
    mcp_server._auth_user_id.set(None)
    with pytest.raises(RuntimeError, match="Token"):
        mcp_server._resolve_user_id(db_session)

def test_login_and_profile_never_return_password_hash(db_session):
    from app.services.auth import get_password_hash

    user = User(
        username="mcp-safe-profile",
        email="mcp-safe-profile@example.com",
        password_hash=get_password_hash("correct-password"),
    )
    db_session.add(user)
    db_session.commit()
    result = mcp_server.login("mcp-safe-profile", "correct-password")
    profile = mcp_server.get_profile()
    assert "password_hash" not in result["user"]
    assert "password_hash" not in profile
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_security.py tests/test_mcp_auth.py -q`

预期：旧 service-account 断言和通用 ORM 序列化断言失败。

- [ ] **Step 3: 修复序列化和会话绑定**

在 `_serialize` 增加 Pydantic 分支并递归处理；用户响应使用 `UserResponse.model_validate(user).model_dump(mode="json")` 或同等公开白名单。`_set_authenticated_user` 在同一 `request_ctx.session` 已绑定其它用户时抛出会话切换错误；密码登录保留兼容但不返回敏感字段。

- [ ] **Step 4: 实现三种 Token 入口**

`login_with_token` 调 Token service 后调用会话绑定。`_resolve_user_id` 不再读取 `LIFEQUEST_USER_ID` 或单独的 `LIFEQUEST_MCP_SERVICE_USER_ID`；仅当请求/上下文已认证或 `LIFEQUEST_MCP_TOKEN` 有效时返回用户。service ID 若存在必须与 Token 用户一致，否则返回配置错误。

- [ ] **Step 5: 包装 FastMCP SSE**

ASGI middleware 从大小写不敏感的 `authorization` header 接受严格 `Bearer <token>`；无 header 放行以兼容密码登录，带无效 header 返回 401 和 `WWW-Authenticate: Bearer`，响应不得包含 Token。有效 header 以独立数据库会话校验，将 user ID 放入 contextvar，执行内层 app 后在 `finally` reset。

FastMCP 1.9.4 的 SSE 分支使用 `mcp.sse_app()` 加 middleware 后交给 `uvicorn.Server`；stdio 继续使用 `mcp.run(transport="stdio")`。

- [ ] **Step 6: 验证传输边界和提交**

用 Starlette 简单内层 app 测试有效/无效 Bearer、无 header、`LIFEQUEST_MCP_TOKEN`、过期/撤销 Token 和会话不能切换。运行：

~~~bash
cd backend && ./venv/bin/pytest tests/test_mcp_auth.py tests/test_mcp_security.py -q
git diff --check
git add backend/mcp_server.py backend/tests/test_mcp_auth.py backend/tests/test_mcp_security.py
git commit -m "feat(mcp): authenticate SSE and stdio with access tokens"
~~~

### Task 3: 补齐待办、习惯、子任务和工作台 MCP 工具

**Files:**

- Modify: `backend/mcp_server.py`
- Create: `backend/tests/test_mcp_crud.py`

**Interfaces:**

- 新增 `create_goal`、`complete_goal`、`delete_goal`、`delete_task`、`delete_habit`。
- 新增 `get_habit_history`、`get_habit_pause_intervals`、`get_habit_leave_intervals`、`pause_habit`、`resume_habit`、`create_habit_leave`、`delete_habit_leave`、`backfill_habit`。
- 新增 `create_subtask`、`list_subtasks`、`update_subtask`、`complete_subtask`、`delete_subtask`。
- 新增 `get_workbench`、`update_daily_focus`、`create_quick_task`。
- 扩展任务的 `phase_id`、`milestone_id`、`start_date`、`priority`；扩展习惯的 `weekdays`、`weekly_target` 和完成备注。

- [ ] **Step 1: 写失败测试**

~~~python
from uuid import uuid4


def test_mcp_todo_tools_cover_lifecycle(mcp_crud_db):
    goal = mcp_server.create_goal("年度目标", difficulty="hard")
    assert mcp_server.complete_goal(goal["id"])["status"] == "completed"

    task = mcp_server.create_task("主任务", priority="high")
    subtask = mcp_server.create_subtask(task["id"], "子任务")
    assert mcp_server.complete_subtask(subtask["id"])["is_completed"] is True
    assert mcp_server.delete_subtask(subtask["id"])["status"] == "ok"

    habit = mcp_server.create_habit("指定日期习惯", frequency="weekdays", weekdays=[0, 2, 4])
    assert mcp_server.pause_habit(habit["id"])["is_active"] is False
    assert mcp_server.resume_habit(habit["id"])["is_active"] is True

    workbench = mcp_server.get_workbench()
    quick = mcp_server.create_quick_task("快速任务", schedule="unscheduled", request_id=str(uuid4()))
    assert quick["title"] == "快速任务"
    assert mcp_server.update_daily_focus(
        workbench["date"], workbench["revision"], [task["id"]]
    )["focus_tasks"]
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_crud.py -q`；预期在缺失工具处失败。

- [ ] **Step 3: 映射现有 schema/service**

导入 `GoalCreate`、`HabitCompletionCreate`、`HabitBackfillCreate`、`HabitLeaveCreate`、`SubtaskCreate`、`SubtaskUpdate`、`DailyFocusUpdate`、`QuickTaskCreate`。每个工具先解析 `_resolve_user_id(db)`，再通过 `TodoService` 或 `DailyWorkbenchService` 校验和执行，最后 `_serialize`，并在 `finally` 关闭数据库会话。

完成动作只返回 service 的真实奖励结果；删除先用 `get_*_for_user` 验权，成功统一返回 status/id/message。

- [ ] **Step 4: 映射习惯、子任务和工作台字段**

日期使用 `date.fromisoformat`，时间使用 `datetime.fromisoformat`。习惯请假/补记/备注分别构造对应 schema；子任务创建前验证父任务归属；工作台重点使用 revision，快速任务使用现有 request_id 幂等规则，不新增重复去重协议。

- [ ] **Step 5: 补充权限/幂等测试并提交**

切换第二用户后读取、完成、删除第一个用户资源必须失败；同一快速任务 request 重试必须返回同一任务 ID，payload 不同必须冲突。运行：

~~~bash
cd backend && ./venv/bin/pytest tests/test_mcp_crud.py tests/test_mcp_notes.py -q
git diff --check
git add backend/mcp_server.py backend/tests/test_mcp_crud.py
git commit -m "feat(mcp): complete todo and workbench tools"
~~~

### Task 4: 补齐财务新增、删除、筛选和债务还款 MCP 工具

**Files:**

- Modify: `backend/mcp_server.py`
- Modify: `backend/tests/test_mcp_crud.py`

**Interfaces:**

- 新增 `create_account`、`delete_account`、`list_categories`、`create_category`、`delete_category`、`delete_transaction`。
- 新增 `list_budgets`、`create_budget`、`delete_budget`。
- 新增 `list_recurring_transactions`、`create_recurring_transaction`、`trigger_recurring_transaction`、`delete_recurring_transaction`。
- 新增 `list_debts`、`create_debt`、`delete_debt`、`add_debt_payment`。
- `list_transactions` 支持 `page/page_size/account_id/category_id/type/start_date/end_date`；`create_transaction` 支持分类、转入账户和中国日期默认值。

- [ ] **Step 1: 写失败测试**

~~~python
def test_mcp_finance_delete_reverses_balance_and_pays_debt(mcp_crud_db):
    account = mcp_server.create_account("现金", type="cash", balance=1000)
    category = mcp_server.create_category("餐饮", type="expense")
    transaction = mcp_server.create_transaction(
        account["id"], "expense", 120,
        category_id=category["id"], description="午餐",
    )
    assert next(
        item["balance"] for item in mcp_server.list_accounts()
        if item["id"] == account["id"]
    ) == 880
    assert mcp_server.delete_transaction(transaction["id"])["status"] == "ok"
    assert next(
        item["balance"] for item in mcp_server.list_accounts()
        if item["id"] == account["id"]
    ) == 1000

    debt = mcp_server.create_debt(
        creditor="银行", type="loan", amount=500, remaining=500,
    )
    payment = mcp_server.add_debt_payment(
        debt["id"], 100, description="首期", date_str="2026-09-14",
    )
    assert payment["amount"] == 100
    assert mcp_server.list_debts()[0]["remaining"] == 400
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_crud.py -q`；预期财务工具缺失。

- [ ] **Step 3: 映射 schema/service 和删除语义**

导入 `CategoryCreate`、`BudgetCreate`、`RecurringCreate`、`DebtCreate`、`DebtPaymentCreate`。金额和枚举交给 Pydantic；删除交易必须调用 `FinanceService.delete_transaction` 反向结算，账户删除保留停用语义，系统分类由 service 拒绝。

- [ ] **Step 4: 扩展交易与定期流水**

列表把分页、账户、分类、类型、日期范围传入 `FinanceService.get_transactions`；创建缺省日期调用 `app.timezone.today()`，不得调用 `date.today()`。定期触发先验权，债务还款只调用 `add_payment`，不在 MCP 改余额或 remaining。

- [ ] **Step 5: 补充过滤、跨用户和时区测试并提交**

测试系统分类删除失败、跨用户资源不可见、交易删除恢复余额、分页元数据正确；在 UTC/中国日期不同边界断言默认日期为中国当天。运行：

~~~bash
cd backend && ./venv/bin/pytest tests/test_mcp_crud.py -q
git diff --check
git add backend/mcp_server.py backend/tests/test_mcp_crud.py
git commit -m "feat(mcp): complete finance lifecycle tools"
~~~

### Task 5: 补齐项目、阶段、里程碑和项目任务 MCP 工具

**Files:**

- Modify: `backend/mcp_server.py`
- Modify: `backend/tests/test_mcp_crud.py`

**Interfaces:**

- 新增 `create_project`、`delete_project`、`complete_project`。
- 新增 `create_project_phase`、`delete_project_phase`。
- 新增 `create_project_milestone`、`delete_project_milestone`、`reach_project_milestone`。
- 新增 `list_project_tasks`、`move_project_task`。
- 移动参数省略表示“不改变”；使用 `clear_project`、`clear_phase`、`clear_milestone` 显式清空关联。

- [ ] **Step 1: 写失败测试**

~~~python
def test_mcp_project_move_has_explicit_clear_semantics(mcp_crud_db):
    project = mcp_server.create_project("MCP 项目")
    phase = mcp_server.create_project_phase(project["id"], "阶段")
    milestone = mcp_server.create_project_milestone(project["id"], "里程碑")
    task = mcp_server.create_project_task(
        project["id"], "项目任务",
        phase_id=phase["id"], milestone_id=milestone["id"],
    )
    moved = mcp_server.move_project_task(task["id"], clear_milestone=True)
    assert moved["phase_id"] == phase["id"]
    assert moved["milestone_id"] is None
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_crud.py -q`；预期项目工具缺失。

- [ ] **Step 3: 映射项目 service**

导入 `ProjectCreate`、`PhaseCreate`、`MilestoneCreate`。项目创建和完成使用与 REST `_project_to_response` 相同的统计字段；层级对象先校验所属项目再增删改；保留 service 对带任务阶段的删除冲突。

- [ ] **Step 4: 实现查询和移动**

项目任务查询支持 phase/milestone 过滤。移动先使用 `TodoService.get_task_for_user`，只把实际变化的字段传给 `ProjectService.move_task`；非空 ID 转 UUID，clear 标记传 `None`，省略字段不传。项目任务创建暴露 phase、milestone、start_date、priority 并继续走 TodoService 链接校验。

- [ ] **Step 5: 补充跨层级/跨用户测试并提交**

测试不同项目层级不可交叉挂接、带任务阶段不能删除、没有移动参数不会清空关联、跨用户详情和移动失败。运行：

~~~bash
cd backend && ./venv/bin/pytest tests/test_mcp_crud.py tests/test_projects.py -q
git diff --check
git add backend/mcp_server.py backend/tests/test_mcp_crud.py
git commit -m "feat(mcp): complete project lifecycle tools"
~~~

### Task 6: 在 Profile 页面创建、复制和撤销 MCP Token

**Files:**

- Create: `frontend/src/services/mcpToken.js`
- Modify: `frontend/src/views/Profile.vue`
- Modify: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**

- `mcpTokenService.listTokens()` 调用 `GET /auth/mcp-tokens`；`createToken({name, expires_in_days})` 调用 `POST`；`revokeToken(tokenId)` 调用 `DELETE`。
- Profile 内存状态包含 `mcpTokens`、`mcpTokensLoading`、`mcpTokensError`、`mcpTokenForm`、`mcpTokenCreating`、`newMcpToken`、`revokeTarget`、`mcpTokenRevoking`；不新增 localStorage/Pinia Token 状态。

- [ ] **Step 1: 写前端失败回归测试**

~~~javascript
test('profile exposes one-time MCP token management', async () => {
  const [profile, service] = await Promise.all([
    readFile(new URL('./Profile.vue', viewsDirectory), 'utf8'),
    readFile(new URL('../services/mcpToken.js', import.meta.url), 'utf8'),
  ])
  assert.match(service, /get.*auth\\/mcp-tokens/)
  assert.match(service, /post.*auth\\/mcp-tokens/)
  assert.match(service, /delete/)
  assert.match(service, /tokenId/)
  assert.match(profile, /mcpTokenService/)
  assert.match(profile, /newMcpToken/)
  assert.match(profile, /navigator\\.clipboard\\.writeText/)
  assert.match(profile, /LIFEQUEST_MCP_TOKEN/)
  assert.match(profile, /revokeTarget/)
  assert.doesNotMatch(profile, /localStorage\\.(getItem|setItem).*mcp/i)
})
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd frontend && npm test -- --test-name-pattern="one-time MCP token management"`；预期服务文件和 Profile 区域缺失。

- [ ] **Step 3: 增加前端 service**

创建 `mcpTokenService`，请求复用现有 `frontend/src/services/api.js` JWT interceptor；列表请求传 `skipErrorToast: true`，创建/撤销不记录响应内容，统一返回 `response.data`。

- [ ] **Step 4: 增加页面交互**

在 Profile 增加 Token 元数据列表和创建表单。默认有效期 90 天，前端限制 1 至 365；列表失败只更新独立错误状态，不清空 Profile 其它数据。创建成功将完整 `token` 仅放入 `newMcpToken`，展示过期时间、复制按钮、SSE/stdio 最小配置提示，并刷新元数据列表。

复制使用 `navigator.clipboard.writeText`；成功 toast，失败 toast 且保留一次性结果区供手动复制。关闭结果区清除内存 Token。撤销使用现有 dialog，确认后禁用按钮、刷新列表；已撤销/过期只读。不得写入 URL、localStorage、Pinia、表单历史或 console。

- [ ] **Step 5: 增加响应式和状态测试**

使用现有 `surface-card`、`dialog-overlay`、`useToast`、`getErrorMessage`；Token 文本使用 `overflow-wrap: anywhere` 和 `min-width: 0`，移动端表单堆叠，错误使用 `role="alert"`，请求期间按钮禁用。运行：

~~~bash
cd frontend && npm test -- --test-name-pattern="profile|MCP token"
cd frontend && npm run check:version
cd frontend && npm run build
~~~

- [ ] **Step 6: 提交本任务**

运行 `git diff --check`，提交：

~~~bash
git add frontend/src/services/mcpToken.js frontend/src/views/Profile.vue frontend/src/views/ui-regressions.test.mjs
git commit -m "feat(profile): manage MCP access tokens"
~~~

### Task 7: 补充连接文档并完成第一批验收

**Files:**

- Modify: `docs/API.md`
- Modify: `.env.example`
- Modify: `backend/tests/test_mcp_auth.py`
- Modify: `backend/tests/test_mcp_crud.py`

**Interfaces:**

- 文档说明页面路径、一次性展示规则、SSE `Authorization`、stdio `LIFEQUEST_MCP_TOKEN` 和撤销方式。
- `.env.example` 只说明 `LIFEQUEST_MCP_TOKEN` 和可选一致性校验 ID，不含真实 Token。

- [ ] **Step 1: 写文档回归断言**

~~~python
def test_mcp_documentation_describes_token_configuration():
    from pathlib import Path

    api_doc = Path("docs/API.md").read_text(encoding="utf-8")
    env_doc = Path(".env.example").read_text(encoding="utf-8")
    assert "/api/auth/mcp-tokens" in api_doc
    assert "Authorization: Bearer" in api_doc
    assert "LIFEQUEST_MCP_TOKEN" in api_doc
    assert "LIFEQUEST_MCP_TOKEN" in env_doc
    assert "<lq_mcp_token>" in api_doc
~~~

- [ ] **Step 2: 更新文档示例**

在 `docs/API.md` 增加 Token API 字段、页面一次性复制说明、SSE/stdio 配置样例；明确完整 Token 关闭窗口后无法恢复。将 `.env.example` 中 service ID 注释改为仅与有效 Token 做一致性校验，追加空的 `LIFEQUEST_MCP_TOKEN=` 注释。

- [ ] **Step 3: 运行第一批和全量验证**

依次运行：

~~~bash
cd backend && ./venv/bin/pytest tests/test_mcp_auth.py tests/test_mcp_security.py tests/test_mcp_crud.py -q
cd backend && ./venv/bin/pytest -q
cd frontend && npm test
cd frontend && npm run check:version
cd frontend && npm run build
git diff --check
~~~

- [ ] **Step 4: 提交文档**

确认暂存区没有数据库、上传文件、真实 Token 或无关用户文件后提交：

~~~bash
git add docs/API.md .env.example backend/tests/test_mcp_auth.py backend/tests/test_mcp_crud.py
git commit -m "docs(mcp): document token connection setup"
~~~
