# Merge origin/main Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 将本地 main 与 origin/main 的分叉历史安全合并，保留本地 UI、日程、笔记同步和周复盘功能，吸收远端功能及稳定性修复，并把项目版本推进到 1.14.8。

**Architecture:** 在以本地 main 为起点的隔离集成分支中合并 origin/main，按数据契约、后端服务、前端交互和发布元数据分组解决冲突。远端在并发控制、用户隔离、中国时区日期边界、习惯历史和完整工作台方面的修复作为行为基准；本地独有 UI 和功能作为必须保留的产品能力，通过兼容 API 与单一页面工作流接入，避免整文件选择 ours/theirs。

**Tech Stack:** Git merge/worktree、FastAPI、SQLAlchemy、Pydantic、pytest、Vue 3、Vite、npm、Capacitor/Android、GitHub Actions。

## Global Constraints

- 项目版本唯一来源为仓库根目录的 VERSION 文件。
- 本次目标版本为 1.14.8：以远端较新的 1.14.7 为基准加 1；先更新 VERSION，再运行 cd frontend && npm run sync:version 同步前端版本。
- 提交版本变更前运行 cd frontend && npm run check:version 和 npm run build。
- Android versionName 必须读取根目录 VERSION；本次版本将进入 Android 发布工作流，因此 versionCode 从远端的 22 增至 23。
- 保留当前工作区 8 个既有未跟踪文件，不清理、不覆盖、不暂存：docs/superpowers/plans/2026-08-31-lifequest-product-roadmap.md、docs/superpowers/plans/2026-08-31-windows-note-sync.md、docs/superpowers/reports/2026-08-22-lifequest-plan-review-and-corrections.md、frontend/shop-mobile-final.png、frontend/todos-mobile-final.png、home-mobile-v1.png、notes-dialog-mobile-v1.png、notes-mobile-v1.png。
- 不以整文件覆盖的方式丢弃任一分支独有功能；不在集成验证完成前推送或发布。

---

## 基线与范围

截至 2026-10-04 的只读检查结果：

- 当前分支：main，本地提交 6bdfa0a；本地比远端领先 12 个提交。
- 远端跟踪分支：origin/main，提交 018b47e；本地落后 86 个提交。
- 共同基点：a7d4964。计划是把远端合并进本地演进，不重写任一侧提交历史。
- 本地版本为 1.8.10，远端为 1.14.7，本次目标为 1.14.8。
- Android 远端基线 versionCode 为 22；由于版本变更会进入 Android 发布流程，本计划目标为 23。
- git merge-tree HEAD origin/main 预演得到 20 个冲突路径，当前工作区没有进行中的合并。

### 预期冲突路径

1. .github/workflows/deploy.yml
2. VERSION
3. backend/app/api/notes.py
4. backend/app/api/todos.py
5. backend/app/models/__init__.py
6. backend/app/models/habit_completion.py
7. backend/app/schemas/todo.py
8. backend/app/services/calendar.py
9. backend/app/services/note.py
10. backend/app/services/project.py
11. backend/app/services/todo.py
12. backend/mcp_server.py
13. backend/tests/test_calendar_stats.py
14. frontend/android/app/build.gradle
15. frontend/components.d.ts
16. frontend/package-lock.json
17. frontend/package.json
18. frontend/src/views/Home.vue
19. frontend/src/views/ProjectDetail.vue
20. frontend/src/views/Todos.vue

### 两边需要保留的产品能力

| 区域 | 本地 main 的能力 | origin/main 的能力 | 合并方向 |
|---|---|---|---|
| 全局 UI | Apple/Notion 风格改版，导航、排版、卡片、商城和移动端细节 | 远端主要改动集中在各功能页，没有改本地全局 App.vue 和布局改版 | 保留本地设计系统，在页面整合远端功能时沿用本地视觉规范 |
| 首页 | TodayActionCenter 汇总逾期、今日任务、习惯和日程 | TodayWorkbench 支持今日重点前三项、快速建任务和任务分组 | 首页只保留一个主任务工作流，融合重点/快速创建与本地分类汇总，不重复渲染两套列表 |
| 待办/习惯 | 任务重复排程、延期、习惯完成和日程联动 | 指定星期、每周目标、暂停/请假、历史弹窗、完整工作台契约 | 同一待办页保留本地排程，同时合入远端习惯状态与历史能力 |
| 笔记 | NoteSync 文件夹同步、笔记关联任务/项目 | 笔记树操作锁、原子移动/删除、上传与删除并发保护 | 保留本地 API、模型和 UI；把远端并发保护放入共享服务路径 |
| 项目 | 项目详情中的关联笔记面板 | 项目状态生命周期、请求状态和异步操作保护 | 页面合并本地关联笔记与远端生命周期及状态保护 |
| 商城和账户 | 商城图标库与 UI 重做 | 购买幂等性、账户/财务/MCP 访问令牌等远端改进 | 保留本地视觉和图标；远端服务端校验、鉴权和并发修复全部保留 |

### 文件改动地图

- 版本与发布：.github/workflows/deploy.yml、VERSION、frontend/package.json、frontend/package-lock.json、frontend/components.d.ts、frontend/android/app/build.gradle。另外核对并保留本地桌面发布工作流与远端 Android 发布工作流。
- 习惯、待办与日历：backend/app/api/todos.py、backend/app/models/__init__.py、backend/app/models/habit_completion.py、backend/app/schemas/todo.py、backend/app/services/calendar.py、backend/app/services/todo.py、backend/tests/test_calendar_stats.py。同时核对自动合并的 backend/app/models/todo.py 和远端 workbench API/service/schema。
- 笔记与 MCP：backend/app/api/notes.py、backend/app/services/note.py、backend/mcp_server.py；保留本地 note_sync、note_link 模型/API/service/schema、对应前端服务和回归测试。
- 项目详情：backend/app/services/project.py、frontend/src/views/ProjectDetail.vue，并核对自动合并的项目 API、模型和服务响应。
- 前端首页和待办：frontend/src/views/Home.vue、frontend/src/views/Todos.vue；同时核对本地 TodayActionCenter.vue、useActionCenter.js、task_schedule、WeeklyReview.vue，以及远端 TodayWorkbench.vue、WorkbenchTaskRow.vue、useDailyWorkbench.js、HabitHistoryDialog.vue。
- 其余改动：完整保留两边非冲突提交，包括远端认证/财务/背包/MCP/中国时区修复，以及本地桌面端、NoteSync、关联笔记、任务排程和周复盘；逐项检查自动合并结果，不能只处理 20 个冲突块就结束。

## Task 1: 建立隔离集成分支并记录合并基线

**Files:**
- 不改动产品文件；在独立 worktree 中操作。

- [x] 使用 superpowers:using-git-worktrees 创建从本地 main（当前 6bdfa0a）出发的隔离 worktree，集成分支名使用 codex/merge-origin-main。
- [x] 在原工作区确认 8 个既有未跟踪文件仍在原位；不要把它们复制到集成分支或放入暂存区。
- [x] 在隔离 worktree 刷新远端引用并记录状态：

    git fetch origin
    git status --short --branch
    git rev-parse HEAD origin/main
    git merge-base HEAD origin/main

  预期：集成分支起于本地 main；远端提交若已变化则以刷新后的 origin/main 为准，重新计算冲突预演。原工作区文件仍未改动。

- [x] 执行可检查的合并，不立即提交：

    git merge --no-commit --no-ff origin/main
    git diff --name-only --diff-filter=U

  预期：进入合并状态；未解决路径与本计划基线清单一致，若远端变化导致清单变化则先更新本计划中的冲突范围再继续。

## Task 2: 先定版本与发布元数据

**Files:**
- Modify: VERSION
- Modify: frontend/package.json
- Modify: frontend/package-lock.json
- Modify: frontend/android/app/build.gradle
- Modify: frontend/components.d.ts
- Modify: .github/workflows/deploy.yml
- Inspect: .github/workflows/android-release.yml、.github/workflows/desktop-release.yml

- [x] 先将冲突中的根 VERSION 定为 1.14.8。
- [x] 合并 frontend/package.json 时同时保留远端 test 脚本（node --test src/*/*.test.mjs）与本地 lucide-vue-next 依赖；保留两边其余依赖和版本同步脚本。
- [x] 将 Android versionCode 设为 23，并保留 versionName appVersion 从根目录 VERSION 读取的实现。
- [x] 将部署工作流的触发条件和部署步骤按两边现有部署配置逐段比较后合并；确认 .github/workflows/android-release.yml 和 .github/workflows/desktop-release.yml 都仍在，且没有丢失任何一边的发布任务。
- [x] 在 frontend/ 目录运行 npm run sync:version；再运行 npm install --package-lock-only 更新锁文件，确保保留双方依赖而不进行无关升级。
- [x] 通过 npm run check:version 验证根版本、前端 manifest/lockfile 与 Android 动态版本读取关系；若 components.d.ts 仍有冲突，依据最终保留的自动导入组件重新生成或合并声明。

预期：根版本、前端版本、锁文件一致为 1.14.8；Android versionName 仍引用根版本，versionCode 为 23；远端测试脚本、本地图标依赖和双方发布工作流均保留。

## Task 3: 统一习惯完成记录模型与历史保留语义

**Files:**
- Modify: backend/app/models/habit_completion.py
- Modify: backend/app/models/__init__.py
- Inspect: habit_completion 全部读写处、启动兼容迁移和远端 habit history/leave/pause 模型与测试
- Test: backend/tests/test_habit_schedule.py、backend/tests/test_todos.py

- [x] 检查 habit_completion 的所有读写位置和当前数据库兼容迁移；把 completed_on、completed_date、user_id、删除习惯后的历史保留策略列成字段映射，再编辑模型和调用端。
- [x] 以远端 completed_on 和按用户归属的历史记录语义作为统一存储契约；删除习惯时保留完成历史。需要兼容本地调用时在 schema/service 边界转换，不新增会级联删除历史的路径。
- [x] 确认 backend/app/models/__init__.py 导出模型，应用启动时建表/迁移会应用正确 schema，旧数据库中的打卡行不会丢失或重复生成。
- [x] 在 backend/ 目录运行习惯记录聚焦测试：

    pytest tests/test_habit_schedule.py tests/test_todos.py

  预期：测试通过；删除习惯后历史保留，同一用户同一 China-local 日期不能重复完成。

## Task 4: 合并待办、任务排程与每日工作台契约

**Files:**
- Modify: backend/app/models/todo.py
- Modify: backend/app/schemas/todo.py
- Modify: backend/app/api/todos.py
- Modify: backend/app/services/todo.py
- Preserve: backend/app/models/task_schedule.py、backend/app/services/task_schedule.py、backend/app/schemas/task_schedule.py、backend/app/services/action_center.py 和相关路由
- Preserve: 远端 workbench、habit schedule、habit history、habit pause/leave 相关模型/API/service/schema/测试

- [x] 合并 todo schema/API/service 时保留本地重复排程、延期和日程联动，同时保留远端指定星期、每周目标、暂停/请假、历史和每日 workbench 契约。
- [x] 核对任务 occurrences、任务本体与习惯打卡的 API 字段和状态转换；每个字段同时检查 backend schema、frontend service/composable 调用，防止一次用户动作重复写入任务和习惯记录。
- [x] 为本地排程和远端计划工作流各保留一组回归测试，覆盖重复任务延期、指定星期匹配、每周目标、暂停/请假恢复、今日重点和快速建任务。
- [x] 在 backend/ 目录运行：

    pytest tests/test_task_schedule.py tests/test_daily_workbench.py tests/test_habit_schedule.py tests/test_todos.py

  预期：本地排程与远端习惯计划各自遵守原有 API 契约，可以同时出现在每日工作台而不互相覆盖。

## Task 5: 合并日历统计与 China-local 日期边界

**Files:**
- Modify: backend/app/services/calendar.py
- Modify: backend/tests/test_calendar_stats.py
- Inspect: backend/app/services/action_center.py、backend/app/services/review.py、backend/app/timezone.py

- [x] 采用远端统一的 Asia/Shanghai 日期边界和习惯统计逻辑，同时保留本地排程项目和周复盘所需日历条目。
- [x] 确保完成检查、写入、统计使用同一 China-local 日期；保留相交周区间内的历史数据和按任务创建时间限定的 occurrences。
- [x] 更新日历统计回归测试覆盖午夜边界、周范围交集、每日习惯完成、习惯历史保留、本地排程显示和周复盘范围。
- [x] 在 backend/ 目录运行：

    pytest tests/test_calendar_stats.py tests/test_daily_workbench.py tests/test_task_schedule.py

  预期：日历、工作台和周复盘针对同一用户和日期返回一致的习惯、任务和排程统计。

## Task 6: 合并笔记服务、同步与关联功能

**Files:**
- Modify: backend/app/api/notes.py
- Modify: backend/app/services/note.py
- Preserve: backend/app/api/note_sync.py、backend/app/api/notes.py 中的 NoteLink 路由、backend/app/api/projects.py 和 backend/app/api/todos.py 中的关联查询/操作
- Preserve: backend/app/models/note_sync.py、backend/app/models/note_link.py、backend/app/schemas/note_sync.py、backend/app/schemas/note_link.py、backend/app/services/note_link.py
- Preserve: backend/tests/test_note_sync.py、backend/tests/test_note_sync_api.py、backend/tests/test_note_links.py
- Merge with remote tests: backend/tests/test_notes.py、backend/tests/test_note_sharing.py

- [x] 从 backend/app/main.py、路由注册表和前端 service 确认 NoteSync 与笔记关联路由仍已注册；模型导出与启动建表逻辑能发现本地新增模型。
- [x] 在共享笔记 service 中保留远端的文件树递归移动、事务原子性、所有者校验、所有修改操作锁，以及附件上传/删除互斥保护；本地 NoteSync 同步和关联笔记 API 继续调用这些服务，不绕开锁直接改文件或节点。
- [x] 合并 notes.py 时保持远端鉴权/所有权边界和现有远端 API 契约，同时注册本地 NoteSync、关联对象能力，不删除既有文件同步入口。
- [x] 确认同步和关联行为不会绕过共享 service 锁，单个笔记的同步、移动、删除和附件变更不能互相覆盖。
- [x] 在 backend/ 目录运行笔记聚焦测试：

    cd backend
    pytest tests/test_notes.py tests/test_note_sharing.py tests/test_note_sync.py tests/test_note_sync_api.py tests/test_note_links.py

  预期：笔记同步/关联仍可用；递归移动和附件并发回归通过；笔记读写受所有者约束。

## Task 7: 合并 MCP 工具并保留统一鉴权

**Files:**
- Modify: backend/mcp_server.py
- Inspect: backend/app/services/mcp_access_token.py、backend/app/api/auth.py、backend/app/main.py
- Test: backend/tests/test_mcp_auth.py、backend/tests/test_mcp_crud.py、backend/tests/test_mcp_security.py

- [x] 检查 mcp_server.py 的工具注册、认证上下文、用户/项目/笔记所有权；远端 MCP 访问令牌、财务、项目、待办和习惯工具全部保留。
- [x] 将本地新增工具接入同一认证和所有权边界；未认证调用、跨用户资源 ID 和已撤销令牌均须拒绝。
- [x] 在 backend/ 目录运行：

    pytest tests/test_mcp_auth.py tests/test_mcp_crud.py tests/test_mcp_security.py

  预期：远端 MCP 能力均注册成功，本地工具遵循同一认证与资源归属规则。

## Task 8: 合并项目生命周期与关联笔记详情面板

**Files:**
- Modify: backend/app/services/project.py
- Inspect: backend/app/api/projects.py、backend/app/models/project.py、backend/app/schemas/project.py
- Modify: frontend/src/views/ProjectDetail.vue
- Preserve: 自动合并的远端项目生命周期测试和本地笔记关联测试

- [x] 先确认项目状态变更、归档/完成等生命周期方法的服务端行为、响应字段和授权检查，沿用远端防止异步重复操作的状态语义。
- [x] 将本地关联笔记列表与增加/解除关联交互嵌入详情页，保留本地 Apple/Notion 样式；请求中、失败和空数据状态沿用远端详情页的明确状态处理，避免重复提交和过期响应覆盖新状态。
- [x] 核对项目详情的任务、日程、笔记关联与状态操作共用的 project ID 和 API 响应模型；不得改变已有项目/任务数据归属。
- [x] 在 backend/ 目录运行：

    pytest tests/test_projects.py tests/test_note_links.py

  并在前端回归测试中覆盖关联笔记加载、添加/解除、请求失败和快速重复点击。

预期：远端项目生命周期能力和本地关联笔记功能可在同一详情页使用，重复点击不会造成重复关联或错误状态回滚。

## Task 9: 合并首页工作台，同时保留本地 UI

**Files:**
- Modify: frontend/src/views/Home.vue
- Inspect: frontend/src/components/home/TodayActionCenter.vue、frontend/src/components/home/TodayWorkbench.vue、frontend/src/components/home/WorkbenchTaskRow.vue
- Inspect: frontend/src/composables/useActionCenter.js、frontend/src/composables/useDailyWorkbench.js、frontend/src/services/todo.js、frontend/src/services/actionCenter.js
- Test: frontend/src/views/action-center-regressions.test.mjs、frontend/src/composables/useDailyWorkbench.test.mjs

- [x] 首页保留一个主任务列表和一套数据刷新入口：纳入本地逾期/今日任务/习惯/日程汇总，并接入远端今日重点前三项、快速建任务与任务分组；不要同时独立渲染 TodayActionCenter 和 TodayWorkbench 的重复任务列表。
- [x] 首页组件沿用本地全局颜色、字体、间距、卡片、导航和移动端规则；保留远端优先级/快速创建交互，不用远端默认样式回退覆盖本地主题。
- [x] 增加首页无重复任务和快速创建后列表更新的回归用例，并保留本地 action-center 与远端 daily-workbench 测试。
- [x] 运行 cd frontend && npm test。

预期：桌面与移动端仍呈现本地设计系统；首页没有重复任务；工作台重点、分组和快捷创建可用。

## Task 10: 合并待办页、任务排程和习惯管理

**Files:**
- Modify: frontend/src/views/Todos.vue
- Inspect: frontend/src/components/HabitHistoryDialog.vue、frontend/src/services/todo.js、frontend/src/services/actionCenter.js
- Preserve: 本地任务 schedule 交互与远端 HabitHistoryDialog 和 habit schedule 测试

- [x] 待办页保留本地重复任务、延期和任务排程交互；接入远端按星期计划、每周目标、暂停/请假、习惯历史弹窗与 workbench API 状态。
- [x] 清楚区分任务完成和习惯打卡，避免一个用户动作对两个实体双写；错误、空状态和加载状态不显示为已完成。
- [x] 核对前端 completed_on 日期、周计划、暂停状态、历史记录和任务 schedule 字段与 backend schema 完全一致。
- [x] 在 Task 9 已运行的 frontend npm test 基础上，修复本视图新增或受影响的回归用例后再次运行 npm test。

预期：用户可在同一待办流程管理重复任务与习惯计划，但两类记录保持不同状态和历史。

## Task 11: 审核非冲突文件，确保双方独有改动没有在自动合并中丢失

**Files:**
- Inspect all paths in git diff --name-only a7d4964..HEAD and git diff --name-only a7d4964..origin/main.
- Focus: .github/workflows/android-release.yml、.github/workflows/desktop-release.yml、backend/app/api/auth.py、backend/app/api/finance.py、backend/app/services/auth.py、backend/app/services/finance.py、backend/app/services/habit_metrics.py、backend/app/services/habit_schedule.py、backend/app/services/daily_workbench.py、frontend/src/App.vue、frontend/src/components/layout/、frontend/src/components/notes/、frontend/src/views/Calendar.vue、frontend/src/views/Finance.vue、frontend/src/views/NoteSync.vue、frontend/src/views/WeeklyReview.vue、frontend/src/views/Shop.vue、frontend/src/utils/shopIcons.js、desktop/。

- [x] 将两侧从共同基点新增或修改的路径分为“保留本地”“保留远端”“自动合并后复核”三组，并确认本地独有的 NoteSync、NoteLink、task schedule、weekly review、desktop release、设计系统均存在于合并结果。
- [x] 确认远端新增或重构的认证令牌轮换、头像输入限制、用户隔离、财务精度/账户状态、商城购买幂等、Android 更新进度、MCP 工具和 China timezone 日期逻辑均未被本地旧文件覆盖。
- [x] 检查所有迁移/兼容代码与启动流程：旧 SQLite 数据可启动；新模型被注册；删除/历史留存语义有测试；新 API 默认不改变现有用户数据。
- [x] 查看 git diff --check，逐个检查 20 个合并文件和自动合并的核心文件，确认没有冲突标记、意外删文件或大段格式化噪音。

预期：冲突路径全部解决，双方独有功能清单都能在合并后的代码、注册入口或测试中定位到。

## Task 12: 完整验证并提交本地集成结果

**Files:**
- Validate the merged repository; do not modify unrelated runtime data or the 8 original untracked files.

- [x] 在集成 worktree 运行完整后端测试：

    cd backend
    pytest

  预期：完整后端测试通过；失败时先按失败所属服务修复并重跑对应聚焦测试，再重跑完整套件。

- [x] 在 frontend/ 运行版本一致性、前端回归和生产构建：

    npm run check:version
    npm test
    npm run build

  预期：check:version 成功；Node 测试全部通过；Vite 生产构建成功。构建会执行 prebuild，结束后再次确认 VERSION、package.json 和 lockfile 仍为 1.14.8。

- [x] 手动检查首页、待办、项目详情、商城和笔记页的桌面与窄屏布局；特别确认首页无重复任务、关联笔记可见、任务排程入口保留、远端习惯历史/暂停交互仍可访问。
- [x] 若 Android 发布包在本次集成中生成，确认 APK/AAB 的 versionName 为 1.14.8、versionCode 为 23，且发布工作流最终状态为 success；若推送到 main，核实 Test and Deploy 与 Build Android Release 两个工作流最终均为 success，而非只确认已触发。
- [x] 复核 git status --short：集成 worktree 只包含本次合并和版本相关的变更；原工作区的 8 个未跟踪文件仍未被暂存或修改。
- [x] 所有验证通过后，在 codex/merge-origin-main 创建合并提交，提交说明使用 merge: integrate origin/main with local UI and note features。推送和正式发布另行由用户决定。

## 完成判定

- origin/main 的 86 个远端提交和本地 12 个领先提交均保留在合并历史中。
- 20 个预期冲突均按功能契约解决，且没有冲突标记。
- 版本为 1.14.8；前端版本元数据同步；Android 版本名从根 VERSION 读取，版本码为 23。
- 本地设计系统、首页汇总、待办排程、NoteSync、笔记关联、周复盘和桌面功能仍存在；远端安全、并发、财务、习惯、MCP、workbench 和发布改进仍存在。
- 后端测试、前端测试、版本检查、前端构建均通过；移动端关键页面完成目视复核。

---

## 执行记录与验证总结 (2026-10-04)

- **合并分支与提交:**
  - 隔离 worktree: `codex/merge-origin-main` -> fast-forward 合并到主工作区 `main`。
  - 合并提交哈希: `815857b` (`merge: integrate origin/main with local UI and note features`)。
- **版本与元数据:**
  - 仓库根目录 `VERSION`: `1.14.8`。
  - Android `versionCode`: `23` (`frontend/android/app/build.gradle`)。
  - 前端与桌面端元数据已通过 `sync-version.mjs` 同步并完成校验。
- **全量测试与构建:**
  - 后端 pytest: 645 通过，10 跳过，0 失败（全套测试套件退出码 0）。
  - 前端 npm test: 237 通过，1 跳过（Windows WSL bash 平台特性），0 失败。
  - 前端版本校验 `npm run check:version`: 退出码 0。
  - 前端生产构建 `npm run build`: Vite 生产构建成功 (`built in 17.87s`)。
- **保护文件约束:**
  - 8 个既有未跟踪/文档文件严格保持原位且未被污染或暂存。

