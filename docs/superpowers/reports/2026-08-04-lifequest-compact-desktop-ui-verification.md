# LifeQuest 紧凑桌面端 UI 验证记录

日期：2026-08-04

## 已完成

- 采用 A 方案：固定侧边栏、居中内容区、Home 宽屏双栏工作区。
- 桌面侧边栏从 260px 收敛到 232px，内部用户摘要和导航间距同步压缩。
- 桌面内容区铺满侧边栏以外的工作区，移除共享壳层的全局 `max-width` 限制。
- Home 在 1200px 以上将欢迎区横跨全宽，今日任务与最近任务放主列，最近目标放辅助列。
- Todos、Shop、Projects 的桌面外层间距和卡片密度已收敛；Profile 移除重复的英雄统计卡。
- 375px 以下保持单栏布局和底部导航，不改移动端业务结构。
- 字体仍通过 `--font-family` / `--font-family-display` 变量控制，具体字体选择留待下一轮。
- 统一主题升级为 `DM Sans` 正文与 `Space Grotesk` 标题，配色采用深蓝文字、青蓝主色和绿色行动色。
- Shop 增加分类筛选、四列桌面商品栅格、绿色购买 CTA 和无结果状态。
- 桌面端多个页面外层 padding/max-width 统一由共享壳层控制，避免页面之间出现不同的左右留白。
- Login/Register 同步科技生活背景和表单视觉。

## 验证结果

- `cd frontend; npm run build`：通过。
- 构建仍有既有大 chunk warning，未新增模板或编译错误。
- 浏览器登录页：实时 DOM 和计算样式确认新主题变量、20px 登录卡片圆角和新阴影已生效。
- 代码范围：`App.vue`、`AppLayout.vue`、`Sidebar.vue`、`Home.vue` 及本次设计/计划/报告文档。

## 收尾复核

- 当前代码已明确采用 `DM Sans` 正文与 `Space Grotesk` 标题，设计系统主文档已同步到实际 token。
- `cd frontend; npm run build`：通过；仅保留既有大 chunk warning，主 JS 约 1.49 MB、gzip 约 498 KB，作为后续性能任务。
- `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q`：`73 passed`，约 96 秒。此前 120 秒工具超时属于执行上限过短，不是测试卡死。
- `git diff --check`：通过。
- 真实页面验收需在本地服务启动后完成；登录页可直接查看，业务页需要登录账号。
