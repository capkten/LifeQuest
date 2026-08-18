# Task 4 Report

## Status

DONE_WITH_CONCERNS

Task 4 已完成：统一错误转换器已接入 API 响应 toast、所有当前直接读取后端 `detail` 的页面/组件，并补齐错误映射回归覆盖。未引入新依赖，API 路径、请求行为、认证刷新流程和中文 UI 文案保持不变。

## Files

- `frontend/src/utils/errorMessage.js`
  - 增加 400、403、404、409、422、500 状态兜底。
  - 保留已中文 detail，翻译 `Task not found` 与 `SLOT_CONFLICT:DUPLICATE_TECHNIQUE` 等已知英文/机器码。
  - 统一处理对象 detail、网络错误和最终 fallback。
- `frontend/src/services/api.js`
  - 400、404、409、422、500、网络错误 toast 统一调用 `getErrorMessage(error)`。
  - 保留请求拦截器、响应刷新、认证失效处理和 API 路径。
- `frontend/src/views/localization-regressions.test.mjs`
  - 新增状态码兜底、未知错误 fallback、API 接入和页面 raw-detail 禁用断言。
- `frontend/src/views/cultivation-regressions.test.mjs`
  - 将与 Task 4 目标冲突的旧 `Techniques.vue` raw-detail 断言改为 `getErrorMessage` 接入断言。
- `frontend/src/views/Home.vue`
- `frontend/src/views/Todos.vue`
- `frontend/src/views/Backpack.vue`
- `frontend/src/views/Finance.vue`
- `frontend/src/views/FinanceAccounts.vue`
- `frontend/src/views/FinanceTransactions.vue`
- `frontend/src/views/FinanceDebts.vue`
- `frontend/src/views/FinanceBudgets.vue`
- `frontend/src/views/Projects.vue`
- `frontend/src/views/ProjectDetail.vue`
- `frontend/src/views/Notes.vue`
- `frontend/src/views/EditProfile.vue`
- `frontend/src/views/Profile.vue`
- `frontend/src/views/NotebookFileManage.vue`
- `frontend/src/views/Sects.vue`
- `frontend/src/views/Techniques.vue`
- `frontend/src/views/Shop.vue`
- `frontend/src/views/Login.vue`
- `frontend/src/views/Register.vue`
- `frontend/src/components/notes/NoteViewer.vue`
- `frontend/src/components/cultivation/TribulationProbability.vue`

所有页面/组件中的直接 `response?.data?.detail` 使用均已移除，转换器自身保留该读取作为唯一边界入口。

## TDD

### RED

先扩展 `localization-regressions.test.mjs`，覆盖无 detail 的 400、404、409、422、500、503 fallback，以及 API/页面共享转换器契约，然后运行：

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
```

结果：`31 passed, 2 failed`。失败分别为状态码错误仍返回 `操作失败，请重试。`，以及 `api.js` 未调用 `getErrorMessage`；失败原因与待实现行为一致。

### GREEN

实现转换器和页面/API 接入后，运行同一命令：

```text
ℹ tests 33
ℹ pass 33
ℹ fail 0
```

关键映射已验证：

- `Task not found` -> `任务不存在。`
- `SLOT_CONFLICT:DUPLICATE_TECHNIQUE` -> `同一功法不能重复配置。`
- 已中文 detail 原样保留。
- 无 response 网络错误 -> `网络连接失败，请检查网络。`
- 未知错误 -> `操作失败，请重试。`

## Verification

指定回归命令：通过，`33/33`。

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
```

生产构建：退出码 `0`，Vite 完成构建。

```powershell
cd frontend
npm run build
```

差异检查：退出码 `0`，无输出。

```powershell
git diff --check
```

## Commit

`81bc432 fix(localization): translate api errors and labels`

## Concerns

- `npm run build` 仍输出已有 npm `always-auth` 配置弃用提示、`@vueuse/core` 的两个 Rollup `#__PURE__` 注释提示，以及主 chunk 超过 500 kB 的 warning；均未导致构建失败。
- Task 4 要求的 `gpt-5.6-luna` 未暴露在当前 Codex 工作区的模型切换接口中，无法从工具侧切换。
- 工作树中仍保留用户已有的 `frontend/components.d.ts` 修改，以及 `.agents/`、`.claude/skills/`、`.codex/`、计划文档和 `frontend/vite-check.log` 未跟踪项；本任务未修改、未提交这些无关内容。
