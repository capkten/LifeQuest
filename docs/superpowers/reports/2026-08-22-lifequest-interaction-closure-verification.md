# LifeQuest 交互收口验证报告

日期：2026-08-22  
分支：`codex/notebook-write-race-closure`

## 已完成实现

- 认证错误映射补齐宗门、NPC 锁定、冷却和容量等稳定 detail。
- 登录和注册失败增加表单内联错误区域，错误密码、重复用户名和重复邮箱均显示明确中文原因。
- 笔记本移动端五个操作收敛为紧凑菜单，桌面 hover/focus 行为保留；笔记预览补齐响应式内边距。
- 修炼总览支持按 `kind` 完成 habit/task/goal，使用独立 pending 锁、奖励结算和权威刷新。
- 宗门锁定改为点击反馈，NPC 相遇增加成功/失败反馈，渡劫增加确认弹框。
- 功法购买迁移为失败可重试的确认弹框，商城分类使用统一中文标签，推荐卡预留稳定布局空间。

## 自动化证据

- 后端定向：`pytest tests/test_auth.py tests/test_todos.py tests/test_cultivation.py tests/test_task8_sect_world.py -q`，120 passed。
- 后端全量复跑：`pytest -q`，307 passed，0 failed。
- 前端交互及既有回归：107 passed；本轮修改后的 UI/修炼定向组合测试：74 passed。
- 前端构建：`npm run build`，成功。
- `git diff --check`：通过。
- 部署健康检查：`GET http://127.0.0.1:8001/api/health` 返回 `200 {"status":"ok"}`。

## 浏览器证据

使用临时认证用户、Vite `3001` 和后端 `8001` 执行了 8 个认证路由在 4 个视口的检查，共 32 个组合：

- 视口：`375x812`、`768x1024`、`1024x900`、`1440x1000`。
- 路由：修炼、宗门、NPC、渡劫、功法、商城、笔记、仙界地图。
- 控制台错误：0。
- 横向溢出：0。
- 结果：`.harness/iterations/2026-08-22-interaction-closure/browser-results.json`。
- 截图：同目录下按视口和路由保存。

## 尚未覆盖

新用户没有预置业务数据，因此本轮浏览器检查未实际触发以下具体业务动作：笔记五项菜单操作、修炼待办完成、宗门试炼提交、NPC 成功相遇、渡劫确认提交、功法购买失败重试。

仓库仍没有 `.harness/strict-playwright-runner.mjs` 和认证 fixture，无法执行计划要求的完整 strict browser contract。上述动作不能标记为 `verified`，后续需要补充可重复的业务 fixture 后再验收。

构建非阻塞警告仍存在：用户级 npm `always-auth`、VueUse Rollup PURE 注释，以及 `element-plus` chunk 超过 500 kB。
