# Task 8 宗门与世界推进设计

## 目标

把修仙模块的宗门试炼、隐藏宗门和世界推进从展示数据升级为可持久化、可解释、可幂等的服务端状态机，同时保持 Task 5-7 的资源结算、渡劫前置条件和 API 兼容。

## 设计

`SectAccessProgress` 保存一次宗门入门试炼的固定 objective snapshot、逐项 progress、score、状态和完成时间。状态严格按 `awaiting_messenger -> awaiting_trial -> in_progress -> completed` 迁移；完成接口只在 snapshot 中所有目标达到要求后成功，奖励使用稳定 source key 写入一条修仙账本，重复调用返回原结果。

隐藏宗门由 `evaluate_hidden_sects(user_id)` 计算。结果分为锁定摘要和已揭示数据，锁定结果包含缺失条件，不写入用户可伪造的开关；NPC 事件、心境、世界节点和前置宗门状态共同决定揭示。宗门偏好影响匹配任务的服务端奖励，核心传承影响效率，贡献影响试炼评分或可加入结果。

世界节点使用稳定 `node_key`、`region_key`、`required_realm`、`required_project_phase`、`completed`、`visible` 和 `lock_reason`。节点完成由服务端判定并推进同区域下一个节点，区域和项目阶段共同组成解锁条件，保留旧字段读取兼容。

并发钱包写入继续使用现有事务和幂等账本约束；不同 source key 的并发奖励必须累加为 40 coins、40 total_coins_earned、30 experience，不得以最后提交者覆盖。

## 错误与兼容

错误使用稳定前缀，例如 `TRIAL_MESSENGER_REQUIRED`、`TRIAL_OBJECTIVE_UNMET`、`HIDDEN_SECT_LOCKED` 和 `WORLD_NODE_LOCKED`，详细条件随错误返回。旧的 messenger、trial、join API 保留，旧字段从新状态计算。旧数据库缺少新增列时由启动迁移补齐。

## 验证

先运行 Task 8 定向 RED 测试并记录预期失败，再逐组实现并运行 GREEN；最后运行现有修仙/内容/回归测试、完整 `pytest -q`、`python -m compileall -q app` 和 `git diff --check`。本 Task 不使用 Playwright 作为证据。
