# LifeQuest Stitch UI Verification

日期：2026-08-05

## 本轮已落地

- 同步 Stitch 的冷色调设计 token：蓝青主色、深蓝文字、绿色成功态、DM Sans/Space Grotesk 字体。
- 共享桌面侧栏、平板折叠侧栏和移动底部导航完成第一轮视觉对齐。
- Home 增加进度 Hero、经验进度、快速行动、习惯进度环，并继续使用真实 API 数据。
- Todos 增加当前列表进度摘要，保留原有习惯、任务、目标、子任务和弹窗行为。
- Projects、Shop、Finance 的主卡片圆角、层级和悬浮状态接入共享 Stitch 视觉系统。
- Projects 增加项目概览 Hero，Finance 增加无账户时的可操作空状态。
- Profile、Notes、Login 等页面继续沿用现有真实业务模板，通过共享 token 保持统一视觉，避免复制 Stitch 静态演示数据。

## 验证结果

- `cd frontend; npm run build`：通过。
- `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q`：`73 passed`。
- `git diff --check`：通过。
- 浏览器 375px：Home、Todos、Projects、Shop、Profile、Finance、Notes 均无横向溢出，移动底部导航存在。
- 浏览器 1440px：Home、Todos 无横向溢出，桌面侧栏存在，首页双栏结构生效。
- 浏览器 1280px：Projects、Shop、Profile、Finance 页面已逐页查看，侧栏、卡片层级和空状态正常。
- 首页和 Todos 的 DOM 中确认了进度 Hero、快速行动、习惯进度、列表进度等新结构。

## 后续深度还原

- 用真实有数据账号逐页对比 Stitch 的数据填充态：Shop 商品图、Profile 成就/背包、Finance 图表/流水。
- 继续细化 Notes、Calendar、Stats 等 Stitch 没有直接参考页面的空状态和数据态。
- 处理主 JS bundle 约 1.49 MB 的拆包性能问题。

## 继续实现（2026-08-05）

- Todos、Projects、ProjectDetail 完成 Stitch 任务/项目层级、项目概览、阶段/里程碑和移动端布局；补充项目卡键盘访问、任务完成计数保护与 Gantt 内部滚动。
- Profile、EditProfile、BackpackHistory、ExchangeHistory 完成资料/奖励历史的汇总卡、时间线和响应式视觉整理；Shop 与 Backpack 保留原有业务模板并继续使用共享视觉 token。
- Finance Accounts、Transactions、Budgets、Debts、Calendar、Stats、CoinHistory 接入共享卡片/摘要/空状态层级；交易转账补充客户端转入账户校验，筛选控件补充可访问名称。
- Notes、NotebookFileManage、NoteEditor、Login、Register 补充 Stitch 间距、安全区、触控目标和表单标签，不改动原有 API、路由和认证/编辑流程。
- 本轮新增审查修复：ProjectDetail 完成计数避免重复递增；Finance 和 Project 交互控件统一至少 44px；移动端 Gantt 保持容器内滚动；项目卡支持键盘操作。

## 本轮验证

- `cd frontend; npm run build`：通过。
- `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q`：`73 passed`。
- `git diff --check`：通过。
- 构建仍提示主入口 JS 约 1.49 MB，拆包性能优化尚未处理。

## 尚未完成

- 尚未重新完成所有页面在 375px、768px、1024px、1440px 的浏览器逐页复核；尤其需要检查 Finance 弹窗焦点回收、ProjectDetail Gantt 和真实数据填充态。
- Shop/Backpack 的真实商品与库存数据态仍需对照 Stitch 深化。

## 继续细化（2026-08-05 第二轮）

- Shop 增加钱包/金币摘要、推荐奖励层级、长文本卡片和移动端操作区；Backpack 增加真实库存、装备数量、筛选摘要和分类空状态。
- Finance 总览及 Accounts、Transactions、Budgets、Debts 进一步细化摘要卡、交易卡、弹窗滚动、窄屏堆叠、焦点态和安全区。
- ProjectDetail 进一步处理 Gantt 内部滚动、阶段键盘访问、任务卡换行、焦点态、44px 操作目标和底部导航避让。
- Calendar、Stats、CoinHistory 接入统一的 Stitch 卡片、筛选激活态、触控尺寸和移动端底部导航避让。
- 本轮主工作区再次执行 `cd frontend; npm run build`：通过；`git diff --check`：通过。

当前剩余主要是浏览器真实登录数据态的四尺寸逐页复核，以及主 bundle 拆分性能优化。
