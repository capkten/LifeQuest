# Task 5 Report

## Status

DONE_WITH_CONCERNS

Task 5 已完成：修仙组件、修仙页面和公共布局中的用户可见英文已替换为中文；realm、resource、sect、technique、NPC、status 展示均优先读取服务端 `*_label`，再回退到前端 `displayLabels.js`。未修改 component props、API 字段、stable keys、CSS class names、事件名或既有交互行为，未引入新依赖。

## Scope

- 修仙组件：`CultivationStatusBar`、`RealmProgress`、`ResourceSummary`、`RewardToast`、`TechniqueSlotGrid`、`NpcTimeline`、`MapNode`、`TribulationProbability`。
- 修仙页面：`Cultivation`、`World`、`Sects`、`Techniques`、`Npcs`、`Tribulations`。
- 公共布局：`AppLayout`、`Header`、`Sidebar`。
- 共享标签：补充格子、NPC 角色、事件摘要和节点状态的中文 fallback；补充 `mind_state` 资源标签。
- 回归测试：新增静态英文 UI literal 禁止断言、中文状态/fallback 断言和服务端 label 优先断言；同步更新已过时的 cultivation 回归期望。

## TDD Evidence

### RED

先在 `localization-regressions.test.mjs` 增加修仙组件/页面/布局的静态回归断言，生产代码尚未替换。运行 focused tests 后得到预期失败：

- `cultivation surfaces keep Chinese fallback and state copy` 命中 `Cultivation data could not be loaded.` 等已知英文文案。
- `cultivation pages prefer server labels before shared display labels` 命中页面尚未使用 `realm_label` 等服务端 label/fallback 链路。

RED 结果：`38 passed, 2 failed`；失败原因是待实现行为缺失，不是测试语法或运行环境错误。

### GREEN

完成组件、页面、布局和共享标签替换后，更新与旧英文 fallback 冲突的 cultivation 回归断言，运行同一 focused 命令：

```text
ℹ tests 40
ℹ pass 40
ℹ fail 0
```

## Verification

Focused regression tests：通过，`40/40`。

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
```

Production build：退出码 `0`，Vite 构建完成。

```powershell
cd frontend
npm run build
```

差异检查：退出码 `0`，无输出。

```powershell
git diff --check
```

## Commit

`38af9e7 fix(localization): translate cultivation interface`

## Concerns

- `npm run build` 仍输出已有的 npm `always-auth` 配置弃用提示、`@vueuse/core` 的两个 Rollup `#__PURE__` 注释提示，以及主 chunk 超过 500 kB 的 warning；均未导致构建失败。
- 当前 Codex 工作区没有模型切换接口，无法从工具侧切换或验证用户要求的 `gpt-5.6-luna`。
- 工作区仍保留用户已有的 `frontend/components.d.ts` 修改，以及 `.agents/`、`.claude/skills/`、`.codex/`、计划文档和 `frontend/vite-check.log` 未跟踪项；本任务未修改、未提交这些内容。

## Review Fix

### Status

PASS_WITH_CONCERNS

独立审查指出的 Important 已修复：未知 realm、sect、technique、task preference、status、resource、slot、NPC role、event summary 和 tribulation lock reason 不再原样展示 raw key；新增 `lock_reason_label` 服务端 label 优先链路；NPC/event 展示保留 server label 和用户可读摘要；`Npcs.vue` 与 `Tribulations.vue` 的英文眉题已替换为中文。未修改 API/DB key、props、CSS class、事件名或交互。

回归测试已改为扫描 Vue `<template>` 文本节点中的裸英文，并按文件逐条断言 server `*_label` 优先；未知 key、空值和 lock reason 泄漏均有断言。

### TDD Evidence

RED：先更新测试后运行 focused suite，得到 `37 passed, 3 failed`。失败分别命中未知 `future_stable_key` 泄漏、`Npcs.vue` 的 `RELATIONSHIPS` 裸文本，以及缺失的逐文件 label 链路。

GREEN：实现 helper、NPC/event/lock_reason 展示回退和中文眉题后，focused suite 为 `40 passed, 0 failed`。

### Verification

```text
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
40 passed, 0 failed

npm run build
exit code 0; Vite built 1963 modules

git diff --check
exit code 0; no output
```

### Commits

- Implementation and tests: `9126488 fix(localization): hide unknown cultivation keys`
- Report update: recorded in the subsequent report commit.

### Concerns

- 构建保留已有 npm `always-auth` 配置弃用提示、`@vueuse/core` 的两个 Rollup `#__PURE__` 注释提示，以及主 chunk 超过 500 kB 的 warning；均未导致构建失败。
- 当前 Codex 工作区没有模型切换接口，无法从工具侧切换或验证用户要求的 `gpt-5.6-luna`。
- 用户已有的 `frontend/components.d.ts` 修改，以及 `.agents/`、`.claude/skills/`、`.codex/`、计划文档和 `frontend/vite-check.log` 未跟踪项未纳入本次提交。

## Final Review Fix

### Status

PASS_WITH_CONCERNS

修复未知 server `*_label` 直出 raw key：新增共享 `isTrustedLabel` / `labelFromServer` helper。只有含中文的本地化 server label 才能覆盖前端 fallback；空值、raw stable key 和非本地化未知值统一回退到对应 `displayLabels.js` 中文提示。已覆盖 Cultivation、Sidebar、Sects、Techniques、Npcs、NpcTimeline、TribulationProbability，以及相关 World、Tribulations 和 cultivation 子组件。未修改后端 raw-key 兼容、API、DB、props、stable keys、CSS class 或事件名。

新增对象级回归测试，覆盖未知 realm、sect、technique、task preference、status、resource、slot、NPC、event、lock reason label；独立断言 Sidebar 使用 shared server-label 链路，并保留已知中文 server label 优先行为。

### TDD Evidence

RED：先加入对象级 raw-label 测试和 Sidebar 独立链路断言，在 helper 尚未实现时运行 focused suite，得到 `28 passed, 1 failed`；失败为缺少 `isTrustedLabel` 导出，属于待实现行为缺失。

GREEN：实现 shared helper 并替换所有 cultivation server-label 直出链路；focused suite 为 `42 passed, 0 failed`。

### Verification

```text
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
42 passed, 0 failed

npm run build
exit code 0; Vite built 1963 modules

git diff --check
exit code 0; no output

raw *_label shortcut scan
NO_RAW_LABEL_SHORTCUTS
```

### Commit

`6d6c79d58d15f5e682025d4128dc796e73fe74fa fix(localization): sanitize server cultivation labels`

### Concerns

- `npm run build` 保留已有 npm `always-auth` 配置弃用提示、`@vueuse/core` 的两个 Rollup `#__PURE__` 注释提示，以及主 chunk 超过 500 kB 的 warning；均未导致构建失败。
- 当前 Codex 工作区没有模型切换接口，无法从工具侧切换或验证用户要求的 `gpt-5.6-luna`。
- 用户已有的 `frontend/components.d.ts` 修改，以及 `.agents/`、`.claude/skills/`、`.codex/`、计划文档和 `frontend/vite-check.log` 未纳入本次提交。

## Current Task 5 Execution

本次执行在既有修仙中文化基础上补齐了两条资源标签链路：`Cultivation.vue` 的顶层资源投影保留服务器 `*_label` 字段，`Sidebar.vue` 的灵石名称优先使用 `spirit_stones_label`，无可信服务器中文标签时回退 `displayLabels.js`。同时新增了对应静态回归断言。

TDD 记录：先加入 `cultivation resource projections preserve server labels` 断言，focused localization test 得到 `24 passed, 1 failed`；实现最小修改后，brief 指定测试为 `57 passed, 0 failed`。

本次指定验证结果：

```text
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
57 passed, 0 failed

npm run build
exit code 0; Vite built 1963 modules

git diff --check
exit code 0; no output
```

Task 5 修改范围和最终工作区的 `git diff --check` 均通过。未修改或暂存 Task 4 文件；`localization-regressions.test.mjs` 的差异仅为本次新增断言，没有覆盖既有测试内容。
