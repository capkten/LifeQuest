# Task 2 Report: 中文种子数据和数据库幂等回填

## 状态

`DONE_WITH_CONCERNS`

## 文件改动

- `backend/app/services/content_localization.py`
  - 新增 `ContentLocalizationService.backfill_system_content()`。
  - 新增不可变的 `ContentBackfillSummary`，提供 `world_nodes`、`sects`、`techniques`、`npcs`、`events` 五个整数计数。
  - 按稳定世界节点、宗门和功法 key 回填中文系统字段。
  - 仅回填 `is_generated=True` 且角色/宗门关系可确认的生成 NPC；固定核心 NPC 按既有 `is_core`、角色和宗门关系定位。
  - 事件仅处理已知系统 `event_key` 或精确旧模板 `Met ordinary disciple`，不触碰用户 NPC 及其事件。
  - 重复执行不新增行，第二次回填的变更计数为零，并保留主键、外键和历史关联。
- `backend/app/services/cultivation.py`
  - `_seed_world_once()` 改为从 `content_catalog.py` 创建新世界节点、宗门和功法，不再生成英文模板。
  - 普通弟子描述和相遇事件改用目录中的中文模板。
- `backend/app/main.py`
  - 在现有 seed 异常日志和数据库 session 边界内按要求调用：`CultivationService.seed_world(db)`，再调用 `ContentLocalizationService.backfill_system_content(db)`。
- `backend/tests/test_content_localization.py`
  - 新增隔离 SQLite 测试，覆盖旧数据回填、用户内容保护、幂等、关系保留、固定核心 NPC、空库和 fresh seed。

`backend/app/services/content_catalog.py` 是 Task 1 已提交文件，本任务未修改。

## 保护用户内容的策略

- 世界节点、宗门和功法只通过其稳定唯一 key 定位；不修改主键、外键或历史关联。
- 生成 NPC 必须满足 `is_generated=True`，并且角色和宗门关系可识别；固定核心 NPC 必须满足既有核心标志、已知角色和宗门关系。
- 事件必须关联生成 NPC，且命中已知系统事件 key 或精确旧英文模板。
- 用户自建 NPC 使用 `is_generated=False`，其名称、角色、描述及关联事件保持不变。
- 回填不创建缺失记录；空库调用安全无副作用。

## TDD 证据

### RED

先新增测试后运行 brief 指定命令：

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py::test_backfill_updates_known_system_rows_without_overwriting_user_content -q
```

结果：`1 failed, 7 warnings`。失败原因是预期的 `ModuleNotFoundError: No module named 'app.services.content_localization'`。

### GREEN

实现后运行：

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py -q
```

结果：`5 passed, 7 warnings`。

```powershell
pytest tests/test_content_catalog.py tests/test_content_localization.py -q
```

结果：`8 passed, 7 warnings`。

brief 要求的聚焦命令：

```powershell
pytest tests/test_content_localization.py tests/test_cultivation.py -q
```

结果：`69 passed, 1 failed, 39 warnings`。唯一失败为既有日期敏感测试 `test_npc_cultivation_updates_once_per_natural_day`：测试固定刷新日期为 `2026-08-17`，运行环境日期为 `2026-08-18`，现有 `refresh_npc_cultivation()` 按 `today <= cultivation_updated_on` 保持 `2026-08-18`，与本次本地化改动无关。

排除该已知环境日期冲突后重新运行：

```powershell
pytest tests/test_content_localization.py tests/test_cultivation.py -q -k "not test_npc_cultivation_updates_once_per_natural_day"
```

结果：`69 passed, 1 deselected, 39 warnings`。

其他验证：

```powershell
python -m compileall -q app/services/content_localization.py app/services/cultivation.py app/main.py
git diff --check
```

结果：两条命令均退出码 `0`，无输出。

## Commit

`7cb8a2c` — `fix(localization): backfill chinese system content`

## Concerns

- brief 指定聚焦套件仍有一个既有日期敏感测试在当前日期下失败；本任务未修改该行为或测试，避免扩大范围。
- 测试输出包含现有 FastAPI/Starlette 和 jose 弃用警告；未修改无关配置。
