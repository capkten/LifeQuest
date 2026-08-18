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

## Review Fix: Visible Page Catches

本次 review-fix 仅处理页面 catch 的统一错误转换器接入，未进行 Task 5/6 静态文案重构：

- Home、Backpack、Finance、FinanceAccounts、FinanceTransactions、FinanceDebts、FinanceBudgets、Projects、ProjectDetail、Shop 的可见加载错误状态改为 `getErrorMessage(error)` 路径。
- Notes 的两个可见 catch（加载笔记本、删除笔记本）改为使用捕获错误转换后的提示。
- EditProfile 的头像上传失败提示改为使用捕获错误转换后的 toast。
- 新增页面级静态回归断言，逐个检查目标页面 catch 中的可见 `error` 赋值、`showError` 和 `alert` 是否调用对应 caught error 的 `getErrorMessage`；全局 raw `detail` 扫描确认仅保留 converter 边界入口。

### TDD and Verification

新增断言后的 RED 结果：`33 passed, 1 failed`，失败命中 `Backpack.vue` 的固定 catch 提示。

修复后的回归结果：

```text
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
ℹ tests 34
ℹ pass 34
ℹ fail 0
```

```text
npm run build
exit code: 0
```

```text
git diff --check
exit code: 0, no output
```

### Review-Fix Commit

`5838c09dbad5eec7ccd52cc5bae796f5ac008034 fix(task-4): route page errors through shared converter`

## Review-Fix Round 2: Eager Visible Error Conversion

本轮严格限定为 brief 要求的两项 Important，未进行 Task 5/6 静态文案工作：

- `Sects.vue`、`Techniques.vue` 和 `NotebookFileManage.vue` 的可见错误状态在 catch/错误回调边界直接调用 `getErrorMessage(caughtError)`，移除 raw error 到 computed 的延迟转换。
- `localization-regressions.test.mjs` 使用目标页面清单覆盖 Todos、Profile、NotebookFileManage、Sects、Techniques、Login、Register，以及 Home、Backpack、Finance 系列、Notes、Projects、EditProfile、Shop 等既有页面；仅扫描可见错误 sink，静默 best-effort catch 不计入。

### TDD and Verification

扩展断言后的 RED 结果：`34 passed, 1 failed`，失败命中 `NotebookFileManage.vue` 可见 workspace catch 的 raw error。

修复后的指定回归命令：`35/35` 通过。

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
```

```text
ℹ tests 35
ℹ pass 35
ℹ fail 0
```

生产构建退出码 `0`。仍有已有 npm `always-auth` 配置弃用、`@vueuse/core` 两个 Rollup `#__PURE__` 注释和主 chunk 超过 500 kB 的 warnings，未阻断构建。

```powershell
cd frontend
npm run build
```

`git diff --check` 退出码 `0`，无输出。

```powershell
git diff --check
```

### Commit

`f37842b fix(task-4): eagerly translate visible page errors`

### Concerns

- 当前工作区未提供 `gpt-5.6-luna` 的模型切换接口，无法从工具侧验证或切换该模型。
- 用户既有的 `frontend/components.d.ts` 修改，以及 `.agents/`、`.claude/skills/`、`.codex/`、计划文档和 `frontend/vite-check.log` 未跟踪项仍保留，未纳入本轮提交。
