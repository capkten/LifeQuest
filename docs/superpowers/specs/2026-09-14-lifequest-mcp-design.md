# LifeQuest MCP 能力补齐与 Token 鉴权设计

## 1. 目标

补齐 LifeQuest MCP 与现有业务 API 之间的关键能力差距，使 AI 客户端可以在权限边界内完成待办、财务、项目和笔记的常用新增、查询、修改、完成和删除操作，并可以使用不包含账号密码的个人访问令牌连接 MCP。

本设计还收口当前已发现的 MCP 安全问题：用户信息序列化泄露 `password_hash`、无凭据的服务账号回退、仅支持会话内密码登录，以及 MCP 流水默认日期未遵循 `Asia/Shanghai`。

## 2. 当前基线与问题

当前 `backend/mcp_server.py` 暴露 45 个工具，已经覆盖部分待办、财务、项目和笔记操作，但能力不对称：

| 领域 | 当前已有 | 当前缺口 |
| --- | --- | --- |
| 待办 | 任务/习惯创建、修改、完成；目标查询/修改 | 目标创建/完成/删除，任务/习惯删除，子任务，习惯暂停/恢复/请假/补记/历史，工作台操作，完整计划字段 |
| 财务 | 概览、账户查询/修改、流水新增/查询/修改、转账、预算/债务修改 | 账户、分类、预算、定期流水、债务的新增/删除，流水删除，定期流水触发，债务还款 |
| 项目 | 项目查询/详情/修改，阶段/里程碑修改，项目任务新增 | 项目新增/删除/完成，阶段和里程碑新增/删除/完成，项目任务查询和移动 |
| 笔记 | 笔记本、目录、笔记常规 CRUD 与检索 | 笔记本修改，成员查询/新增/修改/移除 |
| 修炼与仙界 | 无 MCP 工具 | 现有修炼、宗门、功法、NPC、渡劫、飞升和仙界活动 API 全部缺少 MCP 适配 |

当前高风险问题：

1. `_serialize(User)` 会包含数据库字段 `password_hash`，因此 `login` 和 `get_profile` 可能向 MCP 客户端返回密码哈希。
2. 仅配置 `LIFEQUEST_MCP_SERVICE_USER_ID` 时，任何能访问 MCP SSE 的客户端都可以直接获得该用户上下文，没有任何凭据校验。
3. MCP 认证没有独立的过期、撤销和跨传输方式；密码被作为工具参数传递，不适合长期配置。
4. `create_transaction` 在没有传入日期时使用服务器 `date.today()`，与业务规定的中国日期口径不一致。
5. 部分已有创建工具没有暴露业务 schema 已支持的字段，导致 AI 创建的数据无法表达实际 UI/API 能力。

## 3. 范围与分批

为了让每批都能独立测试和回滚，实施拆为两个相关但可独立验收的子项目。

### 第一批：鉴权基础与核心业务 CRUD

- 新增 MCP 个人访问令牌的创建、查看元数据和撤销 API。
- 支持 SSE 请求头、stdio 环境变量和兼容性 Token 登录。
- 修复用户公开信息序列化和无凭据服务账号回退。
- 补齐待办、财务、项目的常用 CRUD 和动作工具。
- 统一 MCP 输入日期、权限错误和删除结果。

第一批只复用现有领域服务和 schema，不新增业务规则。删除语义沿用服务层：账户为停用，项目会解除当前用户任务关联，带任务的阶段拒绝删除，其他资源按现有服务行为删除并保持事务回滚。

### 第二批：笔记协作与修炼/仙界适配

- 补齐笔记本资料和成员管理工具。
- 暴露现有修炼、世界、宗门、功法、NPC、渡劫、飞升和仙界活动 API 的 MCP 适配。
- 为所有有副作用的动作保留已有服务层的幂等键和错误规则。

第二批不新增修炼世界的用户自定义 CRUD。系统世界、宗门和功法是服务端内容，MCP 只提供查询和既有动作。

## 4. Token 鉴权方案

### 4.1 个人访问令牌

新增 `MCPAccessToken` 模型，表名为 `mcp_access_tokens`，字段固定为：

- `id`：UUID 主键。
- `user_id`：用户外键和索引。
- `name`：用户可识别的令牌名称。
- `token_prefix`：用于列表和日志识别的短前缀，不包含完整令牌。
- `token_hash`：完整令牌的 SHA-256 哈希，唯一且不可逆。
- `created_at`、`last_used_at`、`expires_at`、`revoked_at`：生命周期字段。

令牌格式使用 `lq_mcp_` 前缀加密码学随机值。默认有效期 90 天，创建时允许设置 1 至 365 天，不提供无限期令牌。明文令牌只在创建响应中返回一次，列表、日志和撤销响应均不得返回明文。

新增认证 API：

- `POST /api/auth/mcp-tokens`：使用现有 Web JWT 创建令牌，返回一次性明文令牌和元数据。
- `GET /api/auth/mcp-tokens`：列出当前用户令牌的元数据。
- `DELETE /api/auth/mcp-tokens/{token_id}`：撤销当前用户令牌；重复撤销保持幂等，不影响其他用户。

令牌创建仍需要用户在 Web/API 侧已有的登录态，但 MCP 客户端后续只使用 Token，不保存或传递账号密码。这满足 MCP 连接不依赖账号密码，同时避免在 MCP 中实现一套重复的密码管理流程。

### 4.1.1 页面创建与管理

在现有 `frontend/src/views/Profile.vue` 的个人设置区域增加“MCP 访问令牌”管理区，使用当前 Web JWT 调用上述 API：

- 页面加载令牌元数据列表，展示名称、`token_prefix`、创建时间、过期时间、最近使用时间和已撤销状态；不展示完整 Token。
- 创建表单只要求令牌名称和有效期，名称必填，默认 90 天，前端限制与后端一致为 1 至 365 天；提交期间禁用重复提交并显示明确的失败反馈。
- 创建成功后打开一次性结果区域，显示完整明文 Token、过期时间和可复制按钮，同时给出 SSE `Authorization`、stdio `LIFEQUEST_MCP_TOKEN` 的最小配置提示。
- 明文 Token 仅保存在当前组件的短暂内存状态中；关闭结果区域、离开页面或刷新后不得从 API、`localStorage`、Pinia、URL 或普通日志中恢复。
- 复制成功显示成功反馈；浏览器剪贴板不可用或复制失败时，显示明确的失败反馈，并保留 Token 的一次性结果区域供用户手动复制。
- 撤销操作需要二次确认，具有进行中、成功和失败状态；撤销成功后刷新列表。已撤销令牌不提供再次启用入口。
- 页面在桌面和移动端均保持可操作，不产生横向溢出；令牌文本使用可横向查看或换行的稳定容器，不撑大页面布局。

前端新增 `frontend/src/services/mcpToken.js` 作为 API 封装，Profile 页面只负责状态、表单和交互反馈。页面复用现有 `useToast`、`getErrorMessage`、dialog 和 axios 认证拦截器，不自行读取或管理 Web JWT。

### 4.2 MCP 连接方式

支持三种连接方式，优先级如下：

1. SSE/HTTP 请求携带 `Authorization: Bearer <lq_mcp_token>`。
2. stdio 进程设置 `LIFEQUEST_MCP_TOKEN=<lq_mcp_token>`。
3. 对不支持自定义请求头的客户端，调用 `login_with_token(token)` 完成一次会话绑定；工具响应不得回显 Token。请求头和环境变量方式是推荐方式，因为 Token 不会进入工具参数记录。

MCP 进程增加轻量 ASGI 鉴权中间件，包裹 FastMCP 的 SSE 应用，校验请求头中的 Token 并设置当前请求用户上下文。`_resolve_user_id()` 同时支持环境变量和工具登录，以兼容 stdio 与直接单元测试调用。

当前 `LIFEQUEST_MCP_SERVICE_USER_ID` 不再单独授予权限。若仍配置但没有有效 Token，MCP 必须拒绝请求并返回配置错误；服务账号场景改为使用 `LIFEQUEST_MCP_TOKEN`，Token 解析出的用户必须与可选的服务账号 ID 一致。

### 4.3 会话绑定与错误处理

- 首次通过 Token 或密码认证的 MCP 会话绑定到一个用户。
- 后续请求若携带不同用户的 Token，拒绝请求，不允许通过重新登录切换用户。
- 缺少认证时仍允许调用 `login` 以保持兼容，但所有业务工具继续拒绝未认证请求。
- Token 不存在、已过期或已撤销统一返回未认证错误，不泄露 Token 是否曾经存在。
- 认证失败不记录完整 Token，不在响应中返回用户对象或敏感字段。
- 业务资源跨用户访问继续由领域服务校验；MCP 适配层不使用客户端提供的用户 ID。

FastMCP 版本为 `1.9.4`，本轮不接入其 OAuth Authorization Server。该版本的 OAuth 需要完整的授权码 Provider、回调和存储实现，超出当前个人 Token 目标；保留未来升级为 OAuth/设备授权的扩展点。

## 5. MCP 能力设计

所有新增工具都先解析当前用户，再创建短生命周期数据库会话，调用对应领域服务，最后使用统一序列化器返回 JSON 安全结果。适配层不得绕过服务层直接修改余额、奖励、文件或修炼状态。

### 5.1 待办与工作台

保留现有工具并扩展创建参数：

- `create_task` 增加 `phase_id`、`milestone_id`、`start_date` 和 `priority`。
- `create_habit` 和 `update_habit` 增加 `weekdays`、`weekly_target`。
- `complete_habit` 支持打卡备注。

新增工具：

- `create_goal`、`complete_goal`、`delete_goal`、`delete_task`、`delete_habit`。
- `get_habit_history`、`get_habit_pause_intervals`、`get_habit_leave_intervals`。
- `pause_habit`、`resume_habit`、`create_habit_leave`、`delete_habit_leave`、`backfill_habit`。
- `create_subtask`、`list_subtasks`、`update_subtask`、`complete_subtask`、`delete_subtask`。
- `get_workbench`、`update_daily_focus`、`create_quick_task`。
- `complete_goal` 与所有完成动作返回领域服务实际结算结果，不由 MCP 自行计算奖励。

快速任务仍使用现有 `request_id` 幂等规则；普通任务、目标和习惯创建沿用当前 API 行为，不在本轮凭空引入另一套重复判重协议。

### 5.2 财务

新增工具：

- `create_account`、`delete_account`。
- `list_categories`、`create_category`、`delete_category`。
- `delete_transaction`。
- `list_budgets`、`create_budget`、`delete_budget`。
- `list_recurring_transactions`、`create_recurring_transaction`、`trigger_recurring_transaction`、`delete_recurring_transaction`。
- `list_debts`、`create_debt`、`delete_debt`、`add_debt_payment`。

现有 `list_transactions` 增加账户、分类、分页和日期范围参数；`create_transaction` 的默认日期改用 `app.timezone.today()`。金额继续交给现有 Pydantic schema 和 `FinanceService` 使用 Decimal/原子余额逻辑校验。

所有财务删除工具先确认当前用户资源，再调用服务层。交易删除必须反向结算账户余额；账户删除沿用停用语义；系统分类拒绝删除。

### 5.3 项目

新增工具：

- `create_project`、`delete_project`、`complete_project`。
- `create_project_phase`、`delete_project_phase`。
- `create_project_milestone`、`delete_project_milestone`、`reach_project_milestone`。
- `list_project_tasks`、`move_project_task`。

现有阶段、里程碑和项目任务工具统一使用项目归属和层级校验。移动任务使用服务层的未设置哨兵，明确区分“字段未改变”和“移动到根/清空关联”，不得因为省略参数而意外清空关联。

### 5.4 笔记协作

新增工具：

- `update_notebook`。
- `list_notebook_members`、`add_notebook_member`、`update_notebook_member`、`remove_notebook_member`。

笔记本所有者才可修改笔记本信息和成员；编辑者可写节点；查看者只能读取。删除笔记本仍为所有者操作。成员工具返回已有服务层的角色和状态信息，但不得返回密码或 Token。

### 5.5 修炼与仙界

第二批按现有 API 一一提供查询和动作工具：

- 修炼总览、世界、宗门列表、宗门权限、隐藏宗门评估。
- 联系宗门使者、完成试炼目标/试炼、加入/离开宗门。
- 功法库、学习功法、购买功法槽位、更新功法配置。
- NPC 列表和相遇。
- 渡劫预览和尝试。
- 飞升、仙界总览、仙界活动、境界提升和仙官委任。

所有动作直接调用 `CultivationService`、`AscensionService` 或 `ImmortalService`，保留现有 request key、每日限制、资源扣除和错误码语义。系统内容不提供 MCP 删除操作。

## 6. 数据流与模块边界

```text
Web JWT
  -> /api/auth/mcp-tokens
  -> 明文 Token 仅返回一次
  -> SSE Authorization / stdio LIFEQUEST_MCP_TOKEN / login_with_token
  -> MCP 鉴权上下文
  -> _resolve_user_id()
  -> 领域 Service + ownership checks
  -> _serialize_public_result()
```

文件职责：

- `backend/app/models/mcp_access_token.py`：Token 表结构。
- `backend/app/schemas/mcp_access_token.py`：创建、列表和一次性返回 schema。
- `backend/app/services/mcp_access_token.py`：生成、哈希、查验、更新使用时间和撤销。
- `backend/app/api/auth.py`：Token 管理 API，继续使用现有 JWT 保护。
- `backend/mcp_server.py`：传输鉴权包装、用户解析、安全用户序列化和各领域 MCP 适配。
- `frontend/src/services/mcpToken.js`：Token 管理 API 的前端封装。
- `frontend/src/views/Profile.vue`：Token 列表、创建表单、一次性明文展示、复制和撤销交互。
- `backend/app/models/__init__.py`：注册新模型，使现有启动建表/迁移机制发现新表。
- `backend/tests/test_mcp_auth.py`：Token 生命周期、敏感字段和会话绑定。
- `backend/tests/test_mcp_crud.py`：第一批跨领域 MCP 生命周期与跨用户权限。
- `backend/tests/test_mcp_cultivation.py`：第二批修炼和仙界适配。
- `frontend/src/views/ui-regressions.test.mjs` 或对应的前端测试文件：Token 管理区的关键交互和无敏感持久化回归。
- `docs/API.md`、`.env.example`：Token 创建、连接配置和安全说明。

不新增第二套用户表、密码表或独立 MCP 数据库。MCP 和 FastAPI 继续共享当前数据库与领域服务。

## 7. 错误、事务与返回约定

- 资源不存在和跨用户资源统一按不可访问资源处理，不泄露资源所有者。
- 所有写工具让服务层抛出既有错误；MCP 只补充稳定、可读的工具错误上下文。
- 删除工具成功返回 `{\"status\": \"ok\", \"id\": \"...\", \"message\": \"...\"}`，实际删除语义由服务层决定。
- 创建、修改、完成、删除和 Token 撤销失败后不得返回成功对象；数据库会话必须回滚并关闭。
- 用户返回使用公开字段白名单或 `UserResponse`，绝不调用包含 `password_hash` 的通用 ORM 序列化。
- 日期输入按工具声明使用 ISO 8601；需要业务日期的默认值统一走 `Asia/Shanghai`。
- Token、密码和完整认证请求头不得写入日志或错误响应。

## 8. 测试与验收

第一批必须先写失败测试，再实现：

1. Token 创建只返回一次明文，数据库只保存哈希；列表不返回明文；过期/撤销 Token 拒绝；重复撤销幂等。
2. SSE Authorization 和 stdio 环境变量能解析到正确用户；会话不能切换用户；无 Token 的旧密码登录仍可用。
3. `login` 和 `get_profile` 返回结果不含 `password_hash`。
4. 页面可以加载 Token 元数据、创建指定有效期的 Token，并在创建响应中显示一次明文；刷新或重新加载后页面和列表都不再显示明文。
5. 页面复制成功和失败均有反馈；撤销需要确认，撤销成功后列表状态更新，重复撤销不会破坏页面状态。
6. Token 页面在移动端和桌面端无横向溢出，API 错误可读且表单不会因失败丢失用户输入。
7. 待办、财务、项目新增/修改/完成/删除完整生命周期通过；跨用户读写和删除均被拒绝。
8. 财务交易删除恢复余额，账户停用，项目/阶段/里程碑删除遵守现有冲突语义。
9. MCP 默认财务日期在 UTC 与中国日期不同的边界上仍为中国当天。

第二批必须覆盖：

1. 笔记本成员角色权限和成员移除；共享笔记只允许对应角色执行写操作。
2. 修炼和仙界每个 MCP 动作至少有成功、前置条件失败、重复 request key 三类断言。
3. 所有 MCP 工具列表可成功注册，返回值可以 JSON 序列化，且不包含敏感字段。

最终验证顺序：MCP 专项测试、后端全量 `pytest`、`git diff --check`、前端 `npm run check:version` 和 `npm run build`。本轮不自动提交或推送；发布前若确认是用户可见版本变更，再按根目录 `VERSION` 规则递增并同步前端版本。

## 9. 非目标

- 不替换现有 FastAPI JWT 登录体系。
- 不在本轮实现完整 OAuth 授权码/设备授权服务器。
- 不改变普通 Web API 的资源模型、奖励规则、删除规则和 `Asia/Shanghai` 日期规则。
- 不把 MCP 适配层扩展成第二套业务服务，不直接操作余额、奖励、笔记文件或修炼数据库记录。
- 不实现路线图中尚未完成的笔记回收站、版本历史、导入导出等独立 FEAT，除非它们已有对应 API。
