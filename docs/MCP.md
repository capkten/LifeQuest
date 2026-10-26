# LifeQuest MCP：能力审计与连接说明

本次按 `backend/app/api/` 当前路由、`backend/mcp_server.py` 及 `backend/app/mcp/` 的实际工具注册审计。当前注册 **173 个工具**：原有 98 个（包含原有 4 个专注工具），本次新增 75 个（`daily.py` 34 个、`collaboration.py` 5 个、`progression.py` 24 个、`execution.py` 8 个、`retreat.py` 2 个、`management.py` 2 个）。计数来自临时目录中隔离 SQLite 配置下导入服务器后读取 `mcp._tool_manager.list_tools()`，未连接真实用户数据库、未调用业务工具。

这里描述的是现有业务操作的覆盖范围，不代表全部 HTTP 接口和所有参数逐项一一对应。工具复用现有业务 Service；权限、奖励、库存、余额、修炼前置条件和幂等处理仍由业务层执行。日期使用各业务的既有规则；习惯完成和补签采用 `Asia/Shanghai` 自然日，同一习惯同一天最多一次完成。

## 业务映射

下表中的路径省略 `/api` 前缀。工具参数及枚举以客户端 `tools/list` 返回的 JSON Schema 为准。

| 领域 / API | 可用 MCP 工具及对应操作 |
| --- | --- |
| 日常任务、目标、子任务：`/todos/tasks`、`/todos/goals`、`/todos/subtasks` | `create_task`、`list_tasks`、`get_task`、`update_task`、`complete_task`、`delete_task`；`create_goal`、`list_goals`、`get_goal`、`update_goal`、`complete_goal`、`delete_goal`；`create_subtask`、`list_subtasks`、`get_subtask`、`update_subtask`、`complete_subtask`、`delete_subtask`。查询详情、创建、修改、完成、删除均可用；周期任务使用 schedule 字段和 occurrence_date 管理单次发生记录。 |
| 任务计划：`/todos/tasks/{id}/snooze`、`/todos/tasks/{id}/schedule` | `snooze_task`、`reschedule_task`；既有 `create_task`、`update_task` 支持 schedule，`list_tasks` 可读取计划信息，`complete_task` 支持 occurrence_date。周期任务按发生日期结算，不能将一次发生记录的完成误当成全部周期完成。 |
| 习惯：`/todos/habits` 及 history、pause/leave intervals、completions | `create_habit`、`list_habits`、`get_habit`、`update_habit`、`complete_habit`、`delete_habit`、`get_habit_history`、`get_habit_pause_intervals`、`get_habit_leave_intervals`、`pause_habit`、`resume_habit`、`create_habit_leave`、`delete_habit_leave`、`backfill_habit`。 |
| 工作台：`/todos/workbench`、`/todos/workbench/focus`、`/todos/workbench/tasks`、`/todos/daily` | `get_workbench`、`update_daily_focus`、`create_quick_task`、`get_daily_summary`。重点任务更新携带读取所得日期与 revision，避免覆盖他人的并发修改。 |
| 复盘和统计：`/review/weekly`、`/stats/overview`、`/stats/tasks`、`/stats/habits`、`/stats/coins`、`/stats/level` | `get_weekly_review`（可选周一日期）、`get_stats`、`get_task_trends`、`get_habit_stats`、`get_coin_trends`、`get_level_progress`。提供真实周复盘、统计与趋势；文字复盘可存为笔记。 |
| 今日行动中心：`/action-center/today` | `get_action_center`，可读取今天或指定中国日期的执行建议，不会自动完成任务。 |
| 金币商城：`/shop/items`、`/shop/exchange`、`/shop/exchange/history`、`/shop/exchange/{id}` 及 refund | `list_shop_items`、`get_shop_item`、`create_shop_item`、`update_shop_item`、`delete_shop_item`、`purchase_shop_item`、`list_shop_exchanges`、`get_shop_exchange`、`refund_shop_exchange`。系统商品和他人商品的修改限制沿用 Service。 |
| 金币流水：`/coins/history`、`/coins/totals` | `get_coin_history`、`get_coin_totals`。当前余额还可由 `get_profile` 读取。没有任意增减金币工具。 |
| 背包：`/backpack/items` 及 use/equip/unequip/discard、`/backpack/history` | `list_backpack_items`、`get_backpack_item`、`use_backpack_item`、`equip_backpack_item`、`unequip_backpack_item`、`discard_backpack_item`、`get_backpack_history`。单件详情是对拥有物的额外查询适配。 |
| 项目：`/projects`、详情、complete、phases、milestones、tasks、move | `create_project`、`list_projects`、`get_project_detail`、`update_project`、`delete_project`、`complete_project`；`create_project_phase`、`update_project_phase`、`delete_project_phase`；`create_project_milestone`、`update_project_milestone`、`delete_project_milestone`、`reach_project_milestone`；`create_project_task`、`list_project_tasks`、`move_project_task`。项目任务的普通更新和完成使用日常任务工具。`start_project` 调用项目启动 Service，状态更新也可通过 `update_project` 进入现有状态规则。 |
| 笔记：`/notes/notebooks`、tree、children、folders、notes、nodes、search、recent、discover、open、笔记详情/更新 | `list_notebooks`、`create_notebook`、`update_notebook`、`delete_notebook`、`get_notebook_tree`、`list_note_children`、`create_folder`、`create_note`、`rename_or_move_node`、`delete_node`、`list_recent_notes`、`discover_notes`、`mark_note_opened`、`search_notes`、`get_note`、`update_note`。笔记本元数据可从列表读取，没有单独 `get_notebook` 工具。 |
| 笔记业务关联：`/notes/{id}/links` 及任务、目标、项目的 notes 接口 | `list_note_links`、`list_target_notes`、`create_note_link`、`delete_note_link`；kind 限 task、goal、project。写入要求笔记可写且业务目标属于当前用户；查询沿用双方访问权限。 |
| 笔记本成员：`/notes/notebooks/{id}/members` | `list_notebook_members`、`add_notebook_member`、`update_notebook_member`、`remove_notebook_member`。仅所有者可修改笔记本资料、删除笔记本和管理成员；editor 可写笔记，viewer 可读。成员修改参数 `member_user_id` 指成员的用户 UUID。 |
| 修炼：`/cultivation/overview`、world、sects、access、messenger、trial、hidden、techniques、slots、loadout、npcs、tribulation | `get_cultivation_overview`、`get_cultivation_world`、`list_sects`、`get_sect_access`、`evaluate_hidden_sects`、`contact_sect_messenger`、`update_trial_objective`、`complete_sect_trial`、`join_sect`、`leave_sect`、`complete_world_node`、`get_techniques`、`learn_technique`、`purchase_technique_slot`、`update_technique_loadout`、`list_npcs`、`meet_npc`、`get_tribulation_preview`、`attempt_tribulation`。装备映射接受 JSON UUID 字符串，服务校验学习资格、境界和槽位。没有管理员 `set_realm` 工具。 |
| 飞升及仙界：`/immortal/ascend`、overview、activities/run、stage/advance、officials/commission | `ascend`、`get_immortal_overview`、`run_immortal_activity`、`advance_immortal_stage`、`commission_immortal_official`。操作要求满足现有飞升/阶段条件，保留 request_key。 |
| 闭关专注和奇遇：`/cultivation/retreat/start`、active、complete、abort、history、encounters/catalog | 保留 `start_focus_session`、`get_active_focus_session`、`complete_focus_session`、`abort_focus_session`；新增 `get_focus_session_history`、`get_encounter_catalog`。奇遇目录带当前用户解锁记录。时长由服务器计时，客户端不能传入结算奖励或强制奇遇参数。 |
| 财务：`/finance/dashboard`、accounts、categories、transactions、transfer、budgets、recurring、debts、payments | `finance_dashboard`；`list_accounts`、`create_account`、`update_account`、`delete_account`、`transfer`；`list_categories`、`create_category`、`delete_category`；`list_transactions`、`create_transaction`、`update_transaction`、`delete_transaction`；`list_budgets`、`create_budget`、`update_budget`、`delete_budget`；`list_recurring_transactions`、`create_recurring_transaction`、`trigger_recurring_transaction`、`delete_recurring_transaction`；`list_debts`、`create_debt`、`update_debt`、`delete_debt`、`add_debt_payment`。`update_recurring_transaction` 对应 REST 的 `PUT /finance/recurring/{id}`，使用 changes 对象传入需要修改的字段。 |
| 日历：`/calendar/events`、`/calendar/day/{date}` | `get_calendar_events`、`get_calendar_day`。 |
| 签到：`/checkin`、`/checkin/status` | `daily_checkin`、`get_checkin_status`。 |
| 称号：`/titles`、`/titles/me`、`/titles/activate` | `list_titles`、`get_user_titles`、`activate_title`。 |
| 成就：`/achievements`、`/achievements/me` | `list_achievements`、`get_user_achievements`。 |
| 用户资料和兼容认证 | `get_profile` 返回公开资料模型；`login_with_token` 和旧 `login` 保留兼容。凭据不包含在公开用户返回中。 |

## 连接与认证

推荐远程客户端使用 **Streamable HTTP**。FastAPI 对外入口为 `/mcp/http`；MCP 子进程内部入口为 `/http`。带尾斜杠的路径同样由代理接受。远程客户端必须在每个 HTTP 请求中发送：

```text
Authorization: Bearer <LifeQuest MCP access token>
```

这里需要通过 LifeQuest 已有 MCP Token 管理接口创建的 Token，不是普通登录 JWT。Token 权限等于该用户通过现有 Service 可执行的业务权限，目前没有每个工具的细粒度权限范围；`LIFEQUEST_MCP_SERVICE_USER_ID` 只是用户绑定限制，不是只读权限。Token 管理仍使用登录后的网页或 `/api/auth/mcp-tokens`：创建、查看元数据、撤销；创建响应只应保存到客户端的凭据配置中。工具不会替用户签发新 Token。

从 `backend/` 启动本地远程服务：

```bash
python mcp_server.py --transport streamable-http --host 127.0.0.1 --port 3001
```

`--transport streamable-http` 和兼容的 `--transport sse` 都启动组合 HTTP 应用，同时提供 `/http`、旧 `/sse` 和 `/messages/`。FastAPI 通过 `/mcp/http`、`/mcp/sse`、`/mcp/messages` 代理这些入口。代理要求 MCP 进程已启动；`MCP_PORT` 默认 `3001`，`MCP_AUTOSTART=true` 可启用既有子进程自动启动。生产部署和网络配置不属于本次实现验证范围。

`/http` 的初始化、查询工具、调用工具、会话请求及删除会话均要求有效 Bearer；会话 ID 不能替代 Token。Token 的过期、撤销及可选服务账号约束在后续业务调用中重新验证，会话不能切换到另一个用户。`LIFEQUEST_MCP_SERVICE_USER_ID` 如有配置，会额外限制凭据对应的用户。

旧 SSE 保留无请求头建立连接后调用 `login_with_token` 或 `login` 的兼容流程。匿名 SSE 的消息会话 URL 在登录后承担访问该会话的凭据作用，应像密码一样保密；新客户端应使用 Streamable HTTP。使用 Bearer 建立的 SSE 会话，其后续消息也必须携带匹配用户的 Bearer。远程请求不会使用服务器进程的环境 Token 代替客户端认证。

stdio 继续支持：

```bash
python mcp_server.py --transport stdio
```

将 `LIFEQUEST_MCP_TOKEN` 放在本地客户端的环境配置或秘密存储中，或使用 `login_with_token`。环境 Token 仅用于本地 stdio 路径。所有旧工具名称保留；新工具通过相同 `tools/list` 发现。

## 写入、重试与一致性

- 先读对象及当前状态，再使用返回的真实 ID 写入。普通业务工具自动解析当前认证用户，不接受指定任意业务用户的参数；成员管理需要目标成员标识，并受所有者权限限制。
- 购买使用 `purchase_shop_item(item_id, idempotency_key, quantity)`。网络中断重试时保留同一个 key 和同一购买内容；新的购买才生成新的 key。退款使用已拥有的 exchange_id，仍受库存、物品使用状态等规则约束。
- `ascend`、`run_immortal_activity`、`advance_immortal_stage`、`commission_immortal_official` 的 `request_key` 应在同一次操作重试时保持一致。飞升的已占用全局 key 不会返回其他用户的记录。不同动作不要复用同一个业务请求 key。
- 任务、目标、习惯和项目完成的奖励由既有完成 Service 结算；不要通过客户端计算奖励后再额外创建金币或经验。习惯的当天完成与补签共享中国日期边界及唯一性规则。
- 渡劫先调用 `get_tribulation_preview` 了解条件和药丸消耗；`attempt_tribulation` 可能失败并损失修为。功法槽位购买、商品购买、背包使用/丢弃及退款都会改变资源。
- 闭关完成要求服务器实际经过目标时长的 80%；1 分钟目标也不会立即获得全额奖励。不满完整 1 分钟的提前结算奖励为 0；有实际完整分钟的提前结算保留既有部分经验规则。状态领取与奖励在同一事务完成，并发或重复结算不会重复发奖。绑定任务选择同时完成时调用正常 TodoService，任务奖励与闭关奖励分别结算并一起提交；失败时一起回滚。金币累计收入及等级更新使用现有奖励辅助方法。
- 普通财务记账、转账和还款没有统一的客户端请求 key。对结果不明确的超时，先查询流水和余额，确认是否已执行再决定重试。定期流水同一业务日期的触发沿用服务自身幂等处理。
- 笔记更新可携带 `base_revision`（读取所得的 `content_revision`）使用既有修订冲突保护；为兼容旧客户端，省略时仍沿用旧更新行为。工作台重点任务使用 revision。冲突后重新读取并处理差异。笔记本元数据的 `clear_description`、`clear_icon` 明确清空字段，不能同时设置同一字段的新值。

## 保留的 API 能力与边界

以下能力继续通过现有网页/API 使用：账号注册、普通 JWT 登录/刷新/登出与账号设置、头像上传、MCP Token 创建/列表/撤销；笔记图片二进制上传、附件下载、协作 ticket 签发与 WebSocket 实时协作。MCP 支持笔记正文和笔记本成员操作，不作为二进制文件或实时编辑传输。

单个笔记本详情没有独立同名工具，可通过笔记本列表获得相关业务信息。部分旧工具的可选字段表达方式与 REST 不完全相同，客户端应遵循实际 Schema，不能假设任意 REST 参数都可以原样透传。管理员调境界、直接改余额、强制奇遇、绕过试炼或为其他用户执行日常操作均未提供。也未将客户端离线同步、生产发布或管理员运维转换为 MCP 业务工具。

工具注册、权限、读写、奖励和重试测试使用隔离数据库及临时笔记目录；远程测试覆盖实际 MCP 初始化、工具列表/调用与鉴权边界。这里不声明生产已部署，也不以工具数量替代业务验证。
