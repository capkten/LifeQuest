# LifeQuest Defect Closure Design

**Date:** 2026-09-15
**Status:** Approved for implementation planning
**Scope:** The complete defect list in the 2026-09-15 audit attachment

## Goal

修复本次审计中确认的全部缺陷，使习惯、财务、商城、背包、项目、笔记、时间边界、统计和认证在后端、前端及数据层使用一致的业务规则。修复必须保留既有用户数据，关键写操作必须具备事务性和幂等性，并为每个缺陷提供可重复的自动化验收证据。

## Scope

本次包含以下 44 个缺陷项：

| 区域 | 缺陷编号 | 范围 |
| --- | --- | --- |
| 习惯与统计 | HAB-01 至 HAB-08 | 首页日报字段、暂停线上验收、日历历史、日历状态、每周目标统计、目标奖励、目标进度、日报与待办一致性 |
| 财务 | FIN-01 至 FIN-17 | 金币历史、商城消费方向、预算字段/周期/统计、流水关联名称、借贷契约/筛选/还款、编辑提示、周期流水、账户状态、分类校验、可选字段清空 |
| 商城与背包 | SHOP-01 至 SHOP-05 | 背包历史字段、卸下装备、装备退款、商品引用、购买幂等 |
| 项目 | PROJ-01 至 PROJ-04 | 项目开始入口、状态枚举、阶段状态、里程碑达成入口 |
| 笔记 | NOTE-01 至 NOTE-04 | 目录递归路径、真实文件移动、协作票据 scope、组合操作原子性 |
| 时间与统计 | TIME-01、TIME-02、STAT-01 | 签到日期、修仙每日边界、累计经验 |
| 认证与资料 | AUTH-01 至 AUTH-03 | Refresh Token 轮换、前端刷新并发、真实图片校验 |

不包含现有路线图中的新增功能，例如周期复盘、笔记回收站、财务导入导出和新的仙界玩法。既有已修复缺陷不回退，也不进行与上述问题无关的页面重构。

## Product invariants

### Data safety

- 不物理删除业务历史。商品删除改为归档或保留历史引用所需的快照信息。
- 笔记路径修复在执行前创建可恢复备份或暂存副本；无法可靠推断的旧路径进入报告，不自动覆盖。
- 迁移必须可重复执行，并使用当前项目 `backend/app/main.py` 的启动迁移模式；不得引入第二套迁移入口。

### Time

- 数据库时间戳继续以 UTC 存储。
- 业务日期统一由 `backend/app/timezone.py` 转换到 `Asia/Shanghai`。
- 习惯完成、签到、暂停/恢复、日历、统计和修仙每日限制使用同一中国本地日期。
- 同一用户、同一习惯、同一中国日期最多一条有效完成记录。

### State and rewards

- 服务端是暂停、计划日、完成、账户可用性、项目状态、预算统计和奖励的唯一权威来源。
- 所有完成入口调用同一结算路径；重复请求不能重复发放金币、经验或修仙奖励。
- UI 只能把页面字段映射为 API DTO，不能把缺失字段解释为业务状态。

### Finance

- 账户余额、金币账本、库存、背包和流水的相关写入在同一事务内完成。
- 金额计算使用 `Decimal`；财务 API 的金额保留两位小数。
- 金币交易的 `amount` 表示非负金额，`type` (`earn` 或 `spend`) 表示方向。前端根据 `type` 显示正负，不再根据金额正负猜测方向。这样可以兼容既有商城消费记录，不需要无依据地重写历史金额。
- 停用账户不能被用于新流水、转账或周期流水；重新激活账户本身仍然允许。

### Notes and security

- 笔记节点的数据库 `path`、`content_path` 和磁盘文件必须描述同一个目录树。
- 目录改名/移动的数据库更新和文件移动必须整体成功或整体恢复。
- `note_collab` 票据只能用于明确允许的笔记协作接口，不能作为普通登录票据。
- Refresh Token 必须可轮换、可撤销、可检测重放。
- 上传文件必须校验真实文件签名、大小和允许格式，而不只依赖客户端 MIME。

## Repair architecture

本次采用现有分层的最小修复：

```text
Vue views/stores
        |
frontend service DTO mapping
        |
FastAPI routes + Pydantic schemas
        |
domain services (rules, transactions, permissions)
        |
repositories/models + startup migrations
```

- API 层负责认证、输入解析、响应模型和稳定错误码。
- Service 层负责归属校验、状态转换、奖励、余额和文件事务。
- Repository 层只提供查询、锁和持久化原语，不在前端复制业务规则。
- 对重复的手工响应组装，只增加局部 serializer/builder；不把所有服务重写成新的框架。
- 继续使用现有 `rollback_on_error`、`app.timezone`、SQLAlchemy 事务和启动迁移机制。

## Canonical contracts

### Habit and daily summary

`GET /api/todos/daily` 的每个习惯对象必须至少包含：

```json
{
  "id": "uuid",
  "completed_today": false,
  "is_active": true,
  "paused_today": false,
  "scheduled_today": true,
  "excused_today": false,
  "weekly_target": null,
  "weekly_completed": 0,
  "weekly_remaining": 0,
  "pause_intervals": [],
  "leave_intervals": []
}
```

日报、习惯列表、暂停、恢复和完成响应共用服务端状态计算。首页和待办页只依据明确的布尔值展示状态。

### Coin history

规范查询参数为 `coin_type=earn|spend`、`source`、`start_date`、`end_date`、`skip`、`limit`。响应使用 `transactions`、`total_earned`、`total_spent` 和 `count`。前端页面选项 `收入/支出` 映射到 `earn/spend`，分页通过 `skip` 计算。

### Finance

- 流水响应包含 `account_name` 和 `category_name`。
- 预算响应包含 `spent_amount`、`remaining_amount`、`progress` 和 `category_name`；统计使用预算周期和 `start_date`。
- 借贷请求和响应使用 `creditor`、`type=borrow|lend`、`amount`、`remaining`、`status`；新建借贷默认 `remaining=amount`，除非用户明确输入更小的值。
- 借贷响应包含还款列表或明确的 `payments` 字段。
- 借贷列表筛选使用 `status`；借入/借出筛选在前端映射为后端可识别的类型条件。

旧客户端请求字段在服务边界短期兼容并立即归一化；新前端只发送规范字段。规范响应优先返回规范字段，只有不会产生歧义的旧别名才暂时保留。

### Shop and backpack

- 背包历史规范字段为 `action_type`。
- 购买请求携带 `Idempotency-Key`；服务端以用户和 key 建立唯一约束并返回第一次成功结果。
- 装备、卸下、使用、丢弃和退款返回更新后的背包状态。
- 商品历史保留商品名称、价格和必要快照，不能依赖已删除的商品行。

### Projects

项目状态规范为 `planning`、`active`、`completed`、`archived`。创建后仍默认为 `planning`，项目页提供开始操作，将状态改为 `active`；里程碑详情提供 `/reach` 操作。未知历史状态不参与统计，并由前端显示可识别的兼容标签；新请求拒绝未知值。

### Authentication

- JWT refresh payload 包含唯一 `jti`；数据库保存 refresh token 哈希、用户、过期时间、撤销时间和替换 token。
- `/api/auth/refresh` 对当前 token 执行一次性轮换；旧 token 重放返回 401 并撤销相关 token 链。
- 前端刷新使用共享 Promise 锁，同一时刻只有一个刷新请求。
- 头像上传先读取文件头确认真实格式，再保存到非可执行的公开静态目录。

## Data migration and compatibility

1. 在启动迁移中创建 refresh token 表、购买幂等字段/唯一索引和商品历史快照字段；新鲜数据库由 `Base.metadata.create_all` 创建，旧数据库由幂等迁移补齐。
2. 建立迁移前后的结构检查和回滚测试。发现重复唯一键时保留最早成功记录，并把被合并记录写入迁移日志，不静默丢弃业务事实。
3. 对笔记目录执行锁定、扫描、暂存移动、数据库提交和最终替换；任何阶段失败都恢复数据库和文件。
4. 对旧金币记录以 `type` 为方向来源，不批量重写金额；对旧借贷缺失的 `remaining` 使用原 `amount`，并记录修复数量。
5. 对项目未知历史状态只做兼容读取和统计隔离；不在没有证据时把它们强行改成已完成或进行中。

## Workstreams and dependencies

| Workstream | 内容 | 依赖 |
| --- | --- | --- |
| A | 共享时间、习惯日报、目标、日历、统计 | 无 |
| B | 金币和财务契约、账户状态、预算、借贷、周期流水 | A 的日期辅助仅用于日期字段 |
| C | 商城、背包和商品历史 | B 的金币账本契约 |
| D | 笔记路径、文件事务和协作 scope | 迁移锁与测试隔离 |
| E | 项目状态、认证刷新和头像 | 共享错误与前端请求状态 |
| F | 全量集成、浏览器、迁移和线上验收 | A-E 全部完成 |

每个工作流结束时必须有独立测试和提交；F 只能在 A-E 的接口评审完成后执行。

## Error and UI behavior

- 受影响的写接口使用现有 HTTP 状态语义，并在 `detail` 中提供稳定 `code`、用户消息和必要参数。
- 可重试错误保留表单和现有列表；冲突、权限和余额错误不自动重试。
- 写操作使用请求级 action lock；业务条件不满足时按钮保持可解释，不用静默 `return` 隐藏原因。
- 列表刷新失败保留旧数据并显示重试入口；不能用空数组覆盖已加载数据。
- 成功消息只能在服务端成功响应后显示；奖励刷新失败要明确告诉用户“操作已保存”，避免重复提交。

## Verification strategy

- 后端先添加失败测试，再实现；覆盖单用户、跨用户、重复请求、并发会话、迁移和文件失败回滚。
- 前端服务测试验证请求参数、响应字段、筛选、分页、操作锁和失败状态；`npm test` 必须自动发现所有测试。
- 浏览器合同覆盖桌面和移动视口，至少验证首页完成习惯、暂停/恢复、财务创建/筛选/编辑、借贷还款、商城购买/退款、笔记目录移动和项目里程碑。
- 线上暂停问题必须记录真实 URL、HTTP 状态、响应体、部署版本和 API 健康状态；本地 200 不能替代线上证据。
- 完成前运行后端全量测试、前端全量测试、版本检查、生产构建、Python 编译、迁移回滚、`git diff --check` 和 HTTP 健康检查。

## Completion criteria

只有同时满足以下条件才算全部修复：

1. HAB、FIN、SHOP、PROJ、NOTE、TIME、STAT、AUTH 的全部缺陷编号都有对应修复提交和测试。
2. 所有前后端契约测试通过，旧客户端兼容行为有明确测试。
3. 关键写操作的幂等、并发和事务回滚测试通过。
4. 笔记目录和数据库路径在真实临时文件目录中移动后仍可打开，失败可恢复。
5. 中国时间跨日场景下签到、习惯、日历、统计和修仙限制结果一致。
6. 线上暂停/恢复接口和部署版本通过真实请求验收。
7. 根目录 `VERSION`、前端同步版本、构建和发布工作流符合仓库规则。
