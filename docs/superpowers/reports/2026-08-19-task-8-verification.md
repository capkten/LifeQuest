# Task 8 验证报告

日期：2026-08-19

## 实现范围

- `SectAccessProgress` 支持 `awaiting_messenger -> awaiting_trial -> in_progress -> completed`，保存 objective snapshot、progress、score 和完成时间。
- 新增 `get_sect_access`、`update_trial_objective`，试炼完成校验目标并使用用户/宗门稳定 source key 幂等发放奖励。
- 新增隐藏宗门条件评估：NPC 事件、心境、世界节点和前置宗门；锁定结果返回缺失条件，揭示后才允许进入后续流程。
- 宗门偏好、核心传承和贡献通过服务端 `get_sect_effects` 与效率计算生效。
- 世界节点增加区域、项目阶段、完成、可见和锁定原因；按用户节点进度完成并解锁后继节点。
- 新增 API 和前端 service wrapper，保留已有宗门、试炼、世界 API 字段兼容。
- 修复修仙页面的静默锁定：宗门、试炼和地图按钮保留可操作反馈，锁定原因以可读提示呈现；宗门页面展示试炼目标、支持逐项更新和提交；地图页面使用服务端完成状态并刷新后续节点。
- 严格 Playwright runner 新增宗门锁定反馈、地图节点锁定/完成、完整试炼目标流程，覆盖 4 个要求视口。
- 新增启动迁移，支持旧数据库逐列补齐和 `world_node_progress` 表初始化。
- 保留并验证并发钱包累计不变量。

## TDD 证据

- RED：Task 8 初始测试因缺少 `get_sect_access`、`update_trial_objective`、`evaluate_hidden_sects` 和世界节点扩展字段失败。
- GREEN：`pytest -q tests/test_task8_sect_world.py`：`7 passed`。
- 兼容修复后：`pytest -q tests/test_task8_sect_world.py tests/test_cultivation.py tests/test_content_catalog.py`：`90 passed, 0 failed`；新增回归确认地图完成不会伪造项目阶段。

## 最终验证

| 检查 | 结果 |
|---|---|
| Task 8 + 修仙 + 内容定向测试 | `90 passed, 0 failed`，50 warnings |
| 并发钱包专项 | `1 passed, 0 failed`；验收值 `40 coins / 40 total_coins_earned / 30 experience` |
| 完整后端套件 | `268 passed, 0 failed`，481 warnings，164.36s |
| Python 编译 | `python -m compileall -q app` 退出码 0 |
| 差异检查 | `git diff --check` 退出码 0，无输出 |
| 前端生产构建 | 成功，`1963 modules transformed`，15.85s |
| 前端回归测试 | `92 passed, 0 failed` |
| 严格 Playwright | `24/24 passed`；`gpt-5.6-luna`；视口 `375x812`、`768x1024`、`1024x900`、`1440x1000` |

警告来自现有 FastAPI/Starlette、JWT `utcnow()`、npm 配置、Rollup 注释和大 chunk，不是测试失败。

## 未执行项与剩余风险

- Playwright 结果：`.harness/iterations/2026-08-19T05-45-02.733Z/strict-results.json`；`24/24 passed`，包含真实 API 锁定/完成流程和受控完整试炼流程。预期的 503/404 重试场景产生的控制台错误已被 runner 分类为预期错误，`unexpectedConsoleErrors=0`、请求失败 `0`、横向溢出 `0`。
- 后端仍有 481 个既有弃用警告，前端构建仍有 npm 配置、Rollup 注释和大 chunk 警告；均未导致测试或构建失败。
- `.harness/completion-ledger.json` 未修改。

## 后续并发回归修复

在 2026-08-19 的全量复验中发现一个真实的并发缺陷：两个独立会话使用不同
`source_key` 同时结算时，ORM 的读改写会让后提交会话覆盖前一笔用户金币、累计金币和经验。
修复后，用户仓储使用数据库表达式原子累加；修为结算与同一事务内的用户更新保持一致；Todo 和签到
明确关闭修为结算对旧版金币/经验的隐式写入，再分别原子累计各自的历史奖励，避免旧快照覆盖并保持原有奖励语义。

专项回归连续运行 10 次全部通过；受影响测试集 `114 passed`；后端全量 `268 passed, 0 failed`。

最新严格 Playwright：`24/24 passed`，视口 `375x812`、`768x1024`、`1024x900`、`1440x1000`，
`unexpectedConsoleErrors=0`、请求失败 `0`，证据文件为
`.harness/iterations/2026-08-19T06-47-00.063Z/strict-results.json`。
此前一次失败仅为 Vite 样式模块请求的 `net::ERR_NO_BUFFER_SPACE`，重跑后消失，未复现业务断言失败。
