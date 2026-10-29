# LifeQuest Full Closure 计划审查与修正报告

日期：2026-08-22
范围：`docs/superpowers/plans/2026-08-22-lifequest-full-closure.md` 与 `docs/superpowers/specs/2026-08-22-lifequest-full-closure-design.md` 的合理性审查，以及据此进行的计划修正。
状态：审查完成，修正已落盘。

## 审查结论

总体判断：需求设计合理、任务结构清晰、依赖和并行划分正确，可以执行。但原计划存在 4 处与代码库现状不符的假设和 2 个未定义的引用（G-11/G-12/G-13 合同缺失），会导致执行时重复开发或无法验收。本次已全部修正。

## 与现状不符的假设（已修正）

1. `settle_todo_reward` 已存在且幂等（`backend/app/services/cultivation.py`，`source_key` + `IntegrityError` 重试）。原计划 Task 6 将其视为“新增”并要求返回两套 delta；实际差距只是给 `RewardSettlement`（`backend/app/schemas/cultivation.py`）增加仙元/仙石字段。→ 计划已改为“在既有结算上扩展，保持不双结”。
2. `ASCENDED_REALM_KEY`（实际值 `"n"`）已存在并已接入 `ascended` 语义、渡劫 terminal lock 和“飞升后凡界待办不改凡界修为”测试（`backend/tests/test_todos.py::test_n_todo_completion_keeps_rewards_and_does_not_progress_mortal_stage`）。→ 计划 Task 11/12 已明确复用既有 `"n"` 入口，新 `ImmortalProfile` 作为结算记录而非替代境界。
3. 宗门试炼、隐藏宗门、世界节点、NPC 唯一性和固定核心人物已实现（`backend/app/models/world.py` + `backend/app/services/cultivation.py`）。原 Task 7–9 标题为“实现状态机”，会误导为从零开发。→ 已改为“Close and verify（补齐缺口 + 验证）”，commit 文案同步调整。
4. 迁移体系无 Alembic，使用 `create_all` + `main.py` 启动时手工迁移。原 Task 10 要求“回滚快照测试”与现状能力不匹配。→ 已改为“适配 SQLite 手工迁移的幂等预检 + 失败恢复”。

## 新增合同定义

原计划引用了 G-11/G-12/G-13 但没有行为定义，会造成无法断言。本次在计划文档的 Task 1/2/3 中补入明确合同：

- **Contract G-11（笔记本写竞态闭环）**：重复点击不产生重复请求；乱序 rename/move 时最终树以最后一次操作结果为准；失败保留对话框 + 重试；快速切换仅接受最新选择。
- **Contract G-12（项目详情写/删竞态闭环）**：save/phase/project-delete 独立锁；有任务阶段删除返回稳定 409 `PROJECT_PHASE_HAS_TASKS` 且任务归属不变；项目删除需确认且只发一次 DELETE；保存失败保留编辑上下文并可重试。
- **Contract G-13（Header 菜单冒泡闭环）**：导航后菜单关闭且不再弹开；空白点击关闭、头像再点重开；四视口无横向溢出与控制台错误。

## 台账同步

`.harness/completion-ledger.json`：

- G-11：保持 `implemented`，补充合同定义证据，注明缺浏览器证据。
- G-12：由 `planned` 更新为 `implemented`（`delete_phase` 409 阻断与前端锁已存在），注明缺前端确认对话框与浏览器证据。
- G-13：保持 `planned`，补充合同定义，注明 Header 冒泡行为尚未核实。

## 基线事实（已写入计划文档）

计划文档新增 `## Baseline (verified 2026-08-22)` 一节，列出上述既有能力与文件，要求所有任务在此基线上“补齐缺口并保持向后兼容”，每个任务开始前先跑既有相关测试。

## 执行注意事项

- Task 1 的真实缺口是“选择/查看器切换的代际保护”（`useNoteWorkspace.selectNote` 不触发请求代际），不是重写整个 composable。
- Task 2 的前端缺口是阶段/项目删除**确认对话框**和失败保留对话框；后端 409 阻断已存在，不要重复实现。
- Task 7–9 应先跑既有 `test_task8_sect_world.py` 等测试确认基线，再做增量。
- Task 10 不要引入 Alembic，沿用 `create_all` + 手工迁移的既有模式。
- Task 14 的 strict runner 应先按本合同文件定义断言步骤，再实现 Playwright 流程。