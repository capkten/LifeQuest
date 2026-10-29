# 逐页审计进度

用 `frontend/.harness/audit.mjs` 自动体检（横向溢出 / console 报错 / 触摸目标 / 字号），再由人工逐张看 375px 截图。

| 页面 | 路由 | 状态 | 备注 |
| --- | --- | --- | --- |
| 首页 | `home` | ✅ 已审 | 卡片层级、脉冲动效正常 |
| 待办 | `todos` | ✅ 已审 | 标题竖排已修 |
| 周复盘 | `review` | ✅ 已审 | 头部导语成立 |
| 修炼 | `cultivation` | ✅ 已审 | kicker+导语成立 |
| 凡界 | `world` | ⏳ 待审 |  |
| 宗门 | `sects` | ✅ 已审 | 无需改动 |
| 功法 | `techniques` | ✅ 已审 | 格子与列表正常 |
| 人物关系 | `npcs` | ✅ 已审 | 无需改动 |
| 渡劫 | `tribulations` | ⏳ 待审 |  |
| 商城 | `shop` | ✅ 已审 | 页头/抽屉/分段控件正常 |
| 兑换历史 | `exchange-history` | ⏳ 待审 |  |
| 背包 | `backpack` | ✅ 已审 | 空态组件正常 |
| 使用历史 | `backpack-history` | ⏳ 待审 |  |
| 个人 | `profile` | ✅ 已审 | 金色称号正常 |
| 编辑资料 | `edit-profile` | ⏳ 待审 |  |
| 金币记录 | `coin-history` | ✅ 已审已修 | 筛选按钮挤成两行 → 一行 |
| 项目列表 | `projects` | ✅ 已审 | 无需改动 |
| 项目详情 | `project-detail` | ✅ 已审已修 | 四个按钮竖排 → 2×2 网格 |
| 日历 | `calendar` | ✅ 已审已修 | 月份导航与今天并到一行 |
| 统计 | `stats` | ✅ 已审 | 坐标轴 8px 字号待定 |
| 记账 | `finance` | ✅ 已审 | 导语+按钮成立 |
| 账户 | `finance-accounts` | 🟡 已修待复看 | 返回键与导语对齐 |
| 账目明细 | `finance-transactions` | ✅ 已审 | 返回键已在前 |
| 预算 | `finance-budgets` | ✅ 已审已修 | 返回键与导语同一行 |
| 债务 | `finance-debts` | 🟡 已修待复看 | 返回键与导语对齐 |
| 笔记列表 | `notes` | ⏳ 待审 |  |
| 笔记本工作区 | `notebook-workspace` | ✅ 已审已修 | 目录开关改成带文字胶囊 |
| 笔记查看 | `note-viewer` | ⏳ 待审 |  |
| 笔记编辑 | `note-editor` | ✅ 已审已修 | 头部/字段/关联表单整体重排 |
| 文件夹同步 | `note-sync` | ⏳ 待审 |  |
| 登录 | `login` | ✅ 已审 | 垂直居中 |
| 注册 | `register` | ⏳ 待审 |  |
| OAuth 授权 | `oauth` | ⏳ 待审 | 需未登录+授权参数才能打开 |

进度：已审 21 / 待审 10 / 已修待复看 2，共 33 页。