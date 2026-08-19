# Task 13 Report

## Scope

仅实现 Task 13，未处理 Task 14。保留了工作树中原有的 `frontend/components.d.ts`、`.agents/`、`.claude/skills/`、`.codex/`、`docs/superpowers/plans/2026-08-17-lifequest-cultivation-closure.md` 和 `frontend/vite-check.log`，这些未纳入本次提交。

## TDD Red

先新增并发 profile、同一 source key 结算、overview 用户隔离和 Sects 旧响应回归测试，再执行：

```text
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py tests/test_notes.py -q
```

结果：`3 failed, 104 passed, 175 warnings`。新增 profile 测试因 `UNIQUE constraint failed: cultivation_profiles.user_id` 失败；新增 settlement 测试因 SQLite `database is locked` 失败；既有 `test_concurrent_tribulation_attempts_allow_only_one_daily_attempt` 得到 1 个成功结果和 1 个非 `PermissionError` 异常。

前端 RED 命令：

```text
cd frontend; node --test src/views/cultivation-regressions.test.mjs
```

结果：`27 pass, 1 fail`；Sects.vue 不包含请求序号或旧响应丢弃逻辑。

## Implementation

- profile 首次创建使用 SQLite/PostgreSQL upsert、MySQL INSERT IGNORE，其他方言使用 savepoint + 唯一冲突重读；SQLite engine timeout 调整为 30 秒。
- todo source key 结算先锁定 profile 行并抢占唯一日志 key，再修改修为/灵石/legacy 余额；竞争会话返回已提交日志，不重复结算。
- tribulation 使用数据库日期唯一约束作为最终仲裁，并对 SQLite 锁进行有界重试；既有并发测试改为在线程间传递稳定 UUID，避免跨线程访问过期 ORM User 对象造成 `ObjectDeletedError`。
- 启动迁移按 SQLAlchemy dialect 处理日期回填，并在已有 unique constraint/index 时跳过冗余创建；NPC、learned technique、technique key、sect key 的旧记录清理和重复迁移路径可重复执行。
- overview 返回当前用户的 today 和 recent_rewards；Sects 使用 request sequence 丢弃旧筛选响应及旧错误/loading 状态。

## Verification

目标回归：

```text
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

结果：`65 passed, 39 warnings`。

后端全量：

```text
cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

结果：`188 passed, 403 warnings in 97.79s`。

前端全量静态测试：

```text
cd frontend; rg --files -g "*.test.mjs" | ForEach-Object { node --test $_ }
```

结果：`2 + 28 + 1 = 31 passed, 0 failed`。

前端构建：

```text
cd frontend; npm run build
```

结果：Vite `✓ built in 11.69s`，退出码 0。输出包含既有 npm `always-auth` 配置警告、Rollup PURE 注释警告和大 chunk 警告，未导致失败。

差异检查：

```text
git diff --check
```

结果：无输出，退出码 0。

## Commits

- 实现提交：`431800b` (`fix(cultivation): harden persistence and overview data`)
- 报告首次纳入版本控制的提交：`0a8de07` (`docs(task-13): record verification report`)

## Task 13 Closure Follow-up (2026-08-18)

本次追加修复保留了工作区已有改动，未纳入 `frontend/components.d.ts`、`.agents/`、`.claude/skills/`、`.codex/`、既有计划文件和 `frontend/vite-check.log`。

### TDD Red/GREEN

- 新增两个独立 SQLite session、不同 `source_key` 的完整 wallet/profile/log/transaction 并发测试。红灯时 legacy `coins`、`total_coins_earned`、`experience` 只保留一份；修复后 Task 13 测试通过。
- 新增带 technique、learned technique、slot、sect access、membership、NPC/event 引用的 legacy migration 测试。红灯时迁移在重复引用/唯一约束处失败；修复后通过。
- 新增 SQLite 同名非唯一 source-key 索引、重复 settlement 保留最新行、MySQL/MSSQL drop syntax 测试。红灯时普通索引被保留且 helper 不存在；修复后通过。
- 新增真实 deferred Promise 乱序、stale error/loading 不回写测试。红灯时 sequencer 模块不存在；修复后通过。

### Implementation

- 奖励结算在同一事务中实际写锁并刷新 `User` 与 cultivation profile，SQLite 锁错误沿用有界重试；Todo legacy level/experience 基线取自锁定后的状态，避免不同 source key 覆盖钱包、经验和 coin transaction。
- technique/sect key 迁移先合并 learned/access/membership 引用，重挂 slot/NPC/event，合并状态后删除重复行，再创建唯一保护；重复迁移保持幂等。
- 唯一索引迁移实时检查 inspector，发现同名非唯一索引时按 SQLite/PostgreSQL、MySQL/MariaDB、MSSQL 方言删除并重建；cultivation logs 在建唯一索引前按最新 `created_at` 保留 settlement。
- Sects 使用 `createSequencedRequest` 统一成功、错误和 loading 的最新请求判断，避免旧 promise 回写。

### Verification

- Task 13 tests: `4 passed`。
- Related backend regression tests (`test_task13_review_fixes.py`, `test_task12_review_fixes.py`, `test_cultivation.py`, `test_todos.py`): `92 passed`。
- Frontend full Node regression tests: `33 passed, 0 failed`。
- `npm run build`: exit code `0`; only existing npm config, Rollup annotation, and large-chunk warnings were emitted.
- Backend full `pytest -q`: intentionally interrupted at the user's request after roughly 75% progress; output had reached `FFFFF` before interruption and pytest did not emit a final failure summary. This run is not green and its five observed failures are not diagnosed in this report.
- `git diff --check`: run after the report update; result recorded with the commit verification below.
