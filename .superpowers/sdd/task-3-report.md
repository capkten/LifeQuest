# Task 3 Report

## Status

DONE_WITH_CONCERNS

Task 3 的 API 中文展示字段、NPC/event 系统展示文案和动态系统流水文案已实现。实现 commit：`9804c22` (`feat(localization): expose chinese api labels`)。

## 改动文件

- `backend/app/schemas/cultivation.py`
  - `SectSummary` 新增 `kind_label`、`entry_realm_label`、`task_preference_label`。
  - `TechniqueSummary` 新增 `technique_type_label`、`required_realm_label`。
  - `CultivationOverview` 新增 `realm_label`。
- `backend/app/services/cultivation.py`
  - 从 `content_catalog.py` 构造宗门、功法和境界 label；未知值回退 raw key。
  - 总览 recent rewards 增加中文修炼日志展示描述。
  - 系统生成 NPC 描述和 event summary 在 API 边界中文化，保留 `event_key`。
- `backend/app/api/cultivation.py`
  - 为 overview、sects、techniques、npcs 路由补充响应类型契约。
- `backend/app/services/checkin.py`
  - 签到金币流水改为中文系统模板。
- `backend/app/services/coin.py`
  - 空描述的系统金币流水使用中文 source 模板；历史精确匹配旧系统 `Reward from <source>` 时只在展示副本中中文化，不写回数据库。
  - 非匹配描述保持原样。
- `backend/app/services/achievement.py`
  - 成就金币流水改为中文，并修复 commit/non-commit 两种 repository 参数契约。
- `backend/tests/test_cultivation.py`
  - 新增 API raw key 保留及宗门、功法、境界 label 契约测试。
- `backend/tests/test_content_localization.py`
  - 新增 NPC/event API 边界展示测试，以及签到、成就、修炼日志、金币历史和用户描述保护测试。

`backend/app/services/title.py` 和 `backend/app/services/finance.py` 已审查，默认称号描述和系统财务分类均已是中文，因此保持不动。未修改前端、数据库模型、数据库字段、API 路径、主外键、事件码或历史关系。

## 兼容性与用户内容保护

- 所有 raw 字段继续返回：`kind`、`entry_realm`、`task_preference`、`technique_type`、`required_realm`、`realm_key` 和 `event_key` 未被 label 替换。
- label 由既有 `content_catalog.py` 的 `REALM_LABELS`、`SECT_CATALOG`、`TECHNIQUE_CATALOG`、`NPC_ROLE_LABELS` 和 `EVENT_SUMMARY_LABELS` 构造；缺少映射时仅回退 raw key，不引入 i18n 或依赖。
- NPC 仅对 `is_generated=True` 的系统记录构造中文描述；用户 NPC 直接返回数据库原 description。event summary 只对系统生成 NPC 使用 event catalog，event_key 始终保留。
- 用户提供的任务、笔记、财务描述、自定义 NPC 描述和非系统金币描述不被翻译或覆盖。
- `CultivationLog` 没有 description 数据库字段，因此修炼日志中文描述只在 `CultivationOverview.recent_rewards` 展示边界生成，没有 schema migration 或字段变更。

## TDD 证据

### RED

先加入 API label 和动态文案失败测试，再运行 brief 指定的 focused API 测试：

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_cultivation.py::test_cultivation_api_returns_labels_without_removing_keys -q
```

结果：`1 failed`，失败原因为响应缺少 `kind_label`，即目标 API 契约尚未实现。

动态文案 RED：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py::test_generated_system_text_is_chinese_and_user_coin_text_is_preserved tests/test_content_localization.py::test_generated_npc_and_event_text_is_localized_at_api_boundary -q
```

结果：`2 failed`；签到流水仍为 `Daily check-in (streak: 1)`，NPC 描述仍为旧英文模板，event summary 仍未在 API 边界本地化。

### GREEN

brief 指定回归命令：

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py tests/test_cultivation.py tests/test_todos.py -q
```

结果：`92 passed, 1 failed`。唯一失败为已有日期敏感测试 `test_npc_cultivation_updates_once_per_natural_day`：当前系统日期为 `2026-08-18`，测试固定断言 `2026-08-17`；失败点不在本次改动路径。

排除该已知环境冲突后的指定回归命令：

```powershell
pytest tests/test_content_localization.py tests/test_cultivation.py tests/test_todos.py -q -k "not test_npc_cultivation_updates_once_per_natural_day"
```

结果：`92 passed, 1 deselected, 85 warnings in 35.80s`。

额外成就/回归检查：

```powershell
pytest tests/test_achievements.py tests/test_regressions.py -q
```

结果：`3 passed, 21 warnings in 2.51s`。

提交前检查：

```powershell
cd D:\codes\LifeQuest\backend
python -m compileall -q app
cd D:\codes\LifeQuest
git diff --check
```

两条命令均退出码 `0`，无输出。测试警告为既有 FastAPI/Starlette/httpx 生命周期或 jose datetime 弃用警告。

## Commit

- 实现 commit：`9804c22` — `feat(localization): expose chinese api labels`
- 本报告作为独立文档提交，commit hash 将在本次报告提交后记录。

## Concerns

- brief 指定的未过滤测试命令仍受已有日期硬编码测试影响，当前证据为 `92 passed, 1 failed`；本次没有修改该无关测试或 NPC 日期逻辑。
- 当前金币历史兼容展示只能识别精确的旧系统模板 `Reward from <source>`。同样精确的用户自定义文本在现有 schema 缺少系统身份字段时无法与历史系统记录区分；其他用户文本均保持原样。后续若需要完全可判定保护，应增加独立系统流水身份字段，但本任务明确禁止数据库字段变更。

## Review-fix 追加（2026-08-18）

已修复独立审查指出的 Important 问题和 Minor 测试缺口：

- `TodoService._update_rewards` 真实持久化路径改为 canonical 中文 source label，并保留现有 `source`；同时把已有 `source_key` 写入既有 `source_id` 字段，确保新 Todo 系统流水可被保守识别。
- `CoinService` 不再按 description 单字段翻译。只有 `type=earn`、`source` 为 task/habit/goal，且既有 `source_id` 符合 `todo:<source>:<key>` 的系统流水才会把 legacy `Reward from <source>` 转为中文展示。无 `source_id` 的用户自定义同文案保持原样。
- `finance.py` transfer 无用户描述时改为中文 `转账：<from> -> <to>`，用户自定义 description 原样保留。
- source label 统一由 `content_catalog.py` 提供，并保留 `COIN_SOURCE_LABELS`、`CULTIVATION_SOURCE_LABELS` 兼容导出；`coin.py` 和 `cultivation.py` 不再维护重复字典。
- 新增真实 HTTP JSON 回归，验证 cultivation raw key 与中文 label、Todo 动态 coin description/source_id、NPC `event_key` 与既有 event 字段共存；新增未知 label raw-key fallback 和 Finance 默认/自定义描述测试。

### Review-fix TDD

RED：新增/调整的 4 个 focused 测试首次运行结果为 `4 failed`，失败分别复现 legacy 用户同文案误翻译、Todo HTTP 流水仍为英文且 `source_id` 为空、Finance transfer 默认英文、未知 realm label fallback 异常。

GREEN：focused 回归结果为 `4 passed, 14 warnings`。

指定 Task 3 回归命令：

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py tests/test_cultivation.py tests/test_todos.py -q
```

实际结果：`95 passed, 1 failed, 92 warnings in 40.12s`。唯一失败是既有 `test_npc_cultivation_updates_once_per_natural_day` 将日期硬编码为 `2026-08-17`，当前运行日期为 `2026-08-18`，与本次修改无关。

排除该既有日期冲突后的实际结果：`95 passed, 1 deselected, 92 warnings in 38.77s`。

```powershell
python -m compileall -q app
git diff --check
```

两条命令均退出码 `0`，无输出。

### Review-fix Commit

- `bcbe619` — `fix(localization): close task 3 review gaps`

### Review-fix Concerns

- 现有 schema 没有独立 system ownership 字段，因此无法证明一个用户伪造的、同时具备合法 `source/type/source_id` 形状的完整 legacy 流水不是系统流水；实现采取保守策略，仅识别稳定 Todo source key，未匹配者原样返回。要完全消除该歧义需要新增系统身份字段，本任务未改数据库 schema。
- 指定未过滤回归仍包含上述日期敏感测试失败；新增与本次修复相关的测试均通过。

## P1 review follow-up: Todo reward source_id length

Status: fixed in `ec36cb4` (`fix(todos): keep reward source ids within limit`).

The Todo reward coin `source_id` now uses compact, type-distinct IDs that fit the existing `String(36)` column: `t:` for tasks, `h:` plus `YYYYMMDD` for habits, and `g:` for goals, each using URL-safe UUID encoding. The longest generated value is 33 characters. Existing cultivation source keys, API field shape, source labels, and legacy `todo:<source>:` coin-history localization remain unchanged. Coin history localization also recognizes the new compact IDs for all three Todo sources.

Regression coverage verifies all three real reward writes stay within the column limit and remain type-distinct, plus all three compact IDs display as `任务奖励`、`习惯奖励`、and `目标奖励`.

Verification evidence:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_content_localization.py tests/test_todos.py -q
# 31 passed, 63 existing warnings
python -m compileall -q app
# exit code 0
git diff --check
# exit code 0
```

The report-only follow-up does not change implementation files or database schema.
