# Task 1 Report: 中文内容目录和展示契约

## 改动文件

- `backend/app/services/content_catalog.py`
  - 新增 9 个世界节点、90 个宗门、3 个初始功法的中文目录。
  - 新增境界、NPC 角色和系统事件摘要标签。
- `backend/tests/test_content_catalog.py`
  - 覆盖 brief 指定的世界节点与功法断言，以及目录 key 完整性和中文内容断言。
- `frontend/src/locales/zh-CN.js`
  - 新增境界、宗门类型、功法/格子类型、任务偏好、状态、资源、NPC、事件和错误中文字典。
- `frontend/src/utils/displayLabels.js`
  - 新增 brief 指定的 6 个稳定 key 展示函数及中文空值回退。
- `frontend/src/utils/errorMessage.js`
  - 新增统一错误 detail、机器码、中文 detail 和网络错误转换契约。
- `frontend/src/views/localization-regressions.test.mjs`
  - 覆盖展示标签、未知值回退、错误对象、机器码和网络错误。
- `.superpowers/sdd/task-1-report.md`
  - 本交付报告。

## 设计决策

- 保留现有 API 路径、数据库字段、内部 key、稳定事件码、主键和外键；目录只提供中文系统内容和展示标签。
- 宗门 key 按现有生成规则覆盖每星 6 个 `normal`、3 个 `special` 和 1 个 `hidden`，总计 90 个；世界节点和功法 key 与现有服务保持一致。
- 使用世界规格中的九星宗门中文名称和核心传承；stable realm、kind、task preference、technique type 等值仍作为逻辑值保留。
- 前端仅使用 ES module 常量和函数，没有新增 i18n 依赖。`labelRealm` 和 `getErrorMessage` 遵循 brief 的精确回退顺序；无响应但有 request 时返回网络错误提示。
- 用户创建内容未被读取、改写或覆盖；本 Task 只建立目录和展示/错误契约，不处理后续种子回填、API 字段或页面替换。

## TDD 证据

### RED

先新增测试并运行：

```text
backend: 2 failed, ModuleNotFoundError: No module named 'app.services.content_catalog'
frontend: ERR_MODULE_NOT_FOUND for src/utils/displayLabels.js
```

失败原因均为 brief 要求的实现尚不存在。

### GREEN

实现后运行：

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_catalog.py -q
```

结果：`2 passed, 7 warnings in 0.04s`。警告为现有 FastAPI/Starlette 弃用提示。

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs
```

结果：`3 passed, 0 failed`。

```powershell
npm run build
```

结果：成功；`1960 modules transformed`，Vite 生产构建完成。

## Commit

`4d3f723`

提交信息：`feat(localization): add chinese content dictionaries`

## 遗留顾虑

- 聚焦后端测试仍输出 7 条现有框架弃用警告；未修改无关配置。
- 前端构建输出现有 npm `always-auth` 配置警告、Rollup 注释警告和大于 500 kB chunk 提示；构建本身成功。
- 按 Task 1 范围未运行后端全量测试，也未处理后续任务的数据库回填、API label 字段接线或页面文案替换。
