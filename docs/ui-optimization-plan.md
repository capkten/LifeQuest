# LifeQuest UI 优化方案（讨论稿）

> 结论先行：这个项目的 UI 不是"没人管"，而是**管得太分散**。外壳（布局、变量、Element Plus 覆盖）做得比一般项目细致，真正拖后腿的是三件事：
> 1. 每个页面自己写一套 CSS，导致同类组件在不同页面长得不一样；
> 2. 移动端只有"768 以下收成单列"这一档兜底，没有中间梯度；
> 3. Android 壳几乎没有原生适配（返回键、状态栏、按压反馈），跑起来像网页嵌在壳里。
>
> 所以建议的顺序是：**先修地基（低成本、立刻能感知）→ 再统一移动端 → 最后才是视觉换皮**。不建议一上来重做视觉。

---

## 一、现状盘点

| 层级 | 现状 | 问题 |
| --- | --- | --- |
| 样式来源 | `App.vue` 全局约 100 个 CSS 变量 + Element Plus 覆盖；`styles/stitch-overrides.css` 589 行；每个视图一份 scoped CSS | 三套体系并存，同名概念（卡片/按钮/标签）在三个地方各自定义 |
| 视图体量 | `Todos.vue` 3653 行、`ProjectDetail.vue` 约 2960 行、`Shop.vue` 约 2200 行、`Profile.vue` 2092 行 | 单文件里模板/逻辑/样式全混在一起，改一处样式要滚 3000 行 |
| 响应式 | 只有 `767/768` 和 `1199/1200` 两档断点；全站 43 处 `@media (max-width: 767px)` | 小屏 360px、大屏平板竖屏、横屏都没有专门处理 |
| 图标 | 手写 inline SVG（大头）+ Element Plus icons（全局注册）+ lucide（只用于商城）+ emoji（🧘🔒📜🎯💎🎁📌） | 四套图标语言并存，尺寸/线宽不统一，emoji 还依赖系统字体 |
| 导航 | 桌面侧栏 25 个入口分 4 组；移动端底部 5 个 tab + 汉堡抽屉装其余全部 | 30+ 路由只有 5 个能一键到达；`/projects`、`/finance`、`/stats`、`/profile` 等页面在移动端**没有任何 tab 高亮**，用户不知道自己在哪 |
| 反馈 | 全站 `:active` 按压态只有 3 处（`Home`/`ProjectDetail`/`EncounterScrollDialog`），同时 `App.vue` 全局关掉了 `-webkit-tap-highlight-color` | 移动端点任何东西都"没反应"，这是手感最差的一点 |
| 加载/空/错 | 每页各自一套 `.loading-state` / `.empty-state` / `.error-state` | 同一种状态在不同页面长得不一样 |

---

## 二、实测发现（Playwright 基线，375×812 / 768×1024）

用真实数据（7 个任务 / 3 个习惯 / 2 个项目 / 9 笔账）跑了 10 个页面 × 2 个视口，实测确认的问题：

| # | 页面 | 现象 | 实测数据 | 根因 |
| --- | --- | --- | --- | --- |
| A | 待办 | **卡片标题竖排成一字一行**，「晨间拉伸 10 分钟」占 8 行 | 卡片 311px，`.todo-card-header` 网格算出 `80px 194px`；标题实际渲染宽度 **30px**、字号 18px、高度 164px | 标题/操作双列布局中，右侧 4 个 44px 按钮吃掉 194px，标题列仅剩 80px；叠加 `overflow-wrap: anywhere` 逐字断行 |
| B | 全站 | **底部导航同时高亮两个 tab** | `/todos` 下 `to="/"` 与 `to="/todos"` 都带 `bottom-nav-item--active`；`/shop`、`/notes`、`/cultivation` 同样 | `<router-link to="/">` 用的是默认包含匹配，父级 `/` 记录对任何子路由都成立，需改 `exact-active-class` 或按 route name 判定 |
| C | 8 个页面 | **页头标题显示 "LifeQuest"** | `/stats` 实测 `.page-title` 文本为 `LifeQuest` | `AppLayout.vue` 的 `pageTitle` 映射缺 `Finance*` / `Stats` / `Projects` / `ProjectDetail` / `EditProfile` / `CoinHistory` / `ExchangeHistory` / `BackpackHistory` / `Immortal*` |
| D | 统计 | **图表横向溢出，y 轴刻度被裁到视口外** | `.chart-body` clientWidth **309** / scrollWidth **544**；`.bar-chart-bars` 因 `min-width: 520px` 撑开 | 图表被硬编码成桌面宽度，塞进 309px 容器后只能横向滚 |
| E | 平板 | 侧栏折叠后品牌名被裁成 "LifeQues" | 768px 下侧栏 72px 宽 | 折叠态仍渲染完整 "LifeQuest" 文本，应换成图形标记 |
| F | 商城 | 页头挤压：钱包胶囊压住「1 件奖励可兑换」，折成两行；搜索框 placeholder 被截 | — | 标题行用了固定双列，未做窄屏重排 |

> 截图基线在 `frontend/.harness/shots/`（已 gitignore），修复后可用同一脚本重跑做前后对比。

---

## 三、问题清单（按影响排序）

### P0 — 确定是 bug / 白花成本，改了立刻见效

| # | 问题 | 证据 | 影响 |
| --- | --- | --- | --- |
| 1 | **四个字体家族全在下载但全没用上** | `frontend/index.html:8-10` 拉 Cinzel + Plus Jakarta Sans；`App.vue:11` 又 `@import` DM Sans + Space Grotesk；但 `App.vue:55-56` 的 `--font-family` 以 `-apple-system/SF Pro/Inter` 开头，永远轮不到后面 | 多 4 个跨域请求；国内 Android WebView 拉 `fonts.googleapis.com` 可能超时，直接拖慢首屏 |
| 2 | **安全区变量恒为 0** | `index.html:6` 的 viewport 缺 `viewport-fit=cover`，但 `App.vue:93-94` 定义并到处使用 `env(safe-area-inset-*)` | 刘海屏顶部被状态栏压住、底部 Tab 与手势条重叠 |
| 3 | **Android 返回键 = 直接退出应用** | 装了 `@capacitor/app` 但只用于更新检查（`composables/useAppUpdate.js`），全项目无 `backButton` 监听 | 在 30 多个页面里按返回键，期望"回上一页"却直接退到桌面，应用端体感最差的一项 |
| 4 | **原生主题与 Web 主题打架** | `android/.../values/styles.xml:12` 的 `AppTheme.NoActionBar` 继承 `Theme.AppCompat.DayNight.NoActionBar` | 系统开深色模式时，启动页/转场是暗的，Web 内容却纯白，有闪白 |
| 5 | **键盘会盖住底部输入** | `AndroidManifest.xml` 的 activity 未声明 `windowSoftInputMode`；页面普遍用 `100dvh` + 固定底栏 | 表单页（待办新建、记账、笔记）弹出键盘时按钮被顶出视口 |

### P1 — 一致性 / 手感

| # | 问题 | 建议 |
| --- | --- | --- |
| 6 | 全站几乎没有按压反馈 | 统一 `.pressable:active { transform: scale(.98); }` + 去掉"hover 当 active 用"（`AppLayout.vue:287-292` 底部 Tab 就是把 `:hover` 和 `--active` 写在同一选择器） |
| 7 | 移动端底部导航信息架构失衡 | 5 个 tab 只覆盖 5 个页面，其余全靠抽屉。建议改成按使用频率的 5 个（首页/待办/记账/笔记/我的），把商城、背包、修炼收进"我的"或长按菜单；同时给非 tab 页面一个明确的"当前所属域"高亮 |
| 8 | 每页一套 loading/empty/error | 抽 `<AppState>` 三态组件，全站替换，顺便统一文案与重试按钮位置 |
| 9 | 移动端卡片密度不一致 | 待办卡片标题在移动端是 18px，其他页面 14-16px；圆角 12/14/16/22/26 混用（`Profile.vue:2022` 甚至是 22px） |
| 10 | 无 `theme-color`、无 `color-scheme` | 加 meta，Android 状态栏与浏览器地址栏颜色才能对上 |
| 11 | `100dvh` 与内部滚动容器并存 | `.app-content` 自己是 `overflow-y: auto`（`AppLayout.vue:172`），移动端又整体防滚，容易出现"滚到一半卡住"；建议移动端改为 body 滚动 + sticky 顶栏 |

### P2 — 视觉方向（要不要做，见第四节）

| # | 问题 |
| --- | --- |
| 12 | 视觉气质与产品定位脱节：产品是"修行/境界/宗门/背包/商城"的 RPG 化个人成长系统，但界面是标准浅色 SaaS 后台（slate 灰 + 天蓝、直角卡片、数据面板） |
| 13 | "stitch" 命名残留（`stitch-overrides.css`、`.stitch-pill`、`.stitch-progress`）是上一轮设计工具留下的痕迹，语义已经丢失 |

---

## 四、分期方案

### 阶段 0 — 地基修复（预估 1 人天，收益最高）

先吃掉实测确认的 A/B/C/D 四个硬缺陷 + 五个环境问题，都是局部改动、无重构：

| 项 | 改哪 | 怎么改 |
| --- | --- | --- |
| A 待办标题竖排 | `views/Todos.vue` 的 `.todo-card-header` / `.todo-card-actions` | 移动端把操作按钮从右侧列移到标题下方一行，或收成一个「⋯」菜单；`overflow-wrap: anywhere` → `break-word` |
| B 底部导航双高亮 | `components/layout/AppLayout.vue` | `active-class` 改 `exact-active-class`，或按 `route.name` 计算高亮并给非 tab 页映射到所属域 |
| C 页头标题丢失 | `AppLayout.vue` 的 `pageTitle` 映射 | 补齐 8 个缺失路由；后续把标题下沉到路由 `meta.title`，避免再漏 |
| D 统计图表溢出 | `views/Stats.vue` | 去掉图表 `min-width: 520px`，改为按容器宽度重算柱宽；y 轴刻度留在容器内 |
| E 平板品牌截断 | `Sidebar.vue` | 折叠态改渲染图形标记（"LQ" 或 logo 图标），不渲染完整文本 |
| F 商城页头挤压 | `views/Shop.vue` | 窄屏标题行改单列，钱包胶囊下移 |
| 1 字体白加载 | `index.html`、`App.vue` | 删 Google Fonts 与 `@import`，`--font-family` 收敛为系统字体栈 |
| 2 安全区失效 | `index.html` | viewport 加 `viewport-fit=cover`，补 `theme-color`、`color-scheme: light` |
| 3 Android 返回键 | 新增 `composables/useAndroidBackButton.js` | `App.addListener('backButton')`：先关弹层，否则 `router.back()`，首页才退出 |
| 4 原生主题打架 | `android/.../values/styles.xml` | `DayNight` → `Theme.AppCompat.Light.NoActionBar`；状态栏配色跟随主题 |
| 5 键盘遮挡 | `AndroidManifest.xml` | activity 补 `android:windowSoftInputMode="adjustResize"` |

**验收**：`npm run build` 通过；重跑 `frontend/.harness/shoot.mjs`，A 标题恢复单行、B 只有一个 tab 高亮、C 页头标题正确、D 无横向溢出；无外网字体请求。

### 阶段 1 — 移动端体验归一（预估 2-3 人天）

1. **断点体系**：定义 `360 / 480 / 768 / 1024 / 1280` 五档，用容器查询或 `clamp()` 替代大部分整数断点；把 43 处零散 media query 收敛成 `styles/responsive.css` 里的少数几条。
2. **触摸层**：全站统一 44px 最小可点区域（已有 `--touch-target-min` 变量但没贯彻）、`.pressable` 按压态、去掉 hover-as-active。
3. **状态组件**：`components/ui/AppState.vue`（loading / empty / error + 重试），替换各页重复实现。
4. **底部导航重构**：5 个高频 tab + 明确的"其它"入口；非 tab 页面有域高亮。
5. **表单页专项**：待办新建、记账、笔记编辑三个最高频表单做移动端专项（键盘避让、按钮吸底、输入框 16px 防 iOS 缩放）。

**验收**：375px 与 768px 下无横向滚动；抽 5 个核心页用 Playwright 截图对比改动前后。

### 阶段 2 — 设计系统归一（预估 3-5 人天，可选）

1. 建立 `src/components/ui/`：`AppButton` / `AppCard` / `AppField` / `AppSheet` / `AppTabs` / `AppList` / `AppBadge`，样式只从这里出。
2. 用阶段 1 的断点与组件，逐页把 scoped CSS 削薄（先削 `Todos.vue`、`ProjectDetail.vue`、`Shop.vue` 这三个巨无霸）。
3. 图标收敛到一套（建议统一用已装的 `lucide-vue-next`，移除 emoji 图标与手写 SVG）。

> ⚠️ **注意**：`frontend/src/views/ui-regressions.test.mjs` 里有大量断言直接匹配 CSS 字符串（如 `.todo-card-title` 的字号、`.shop-search` 的 44px 高度、`NoteTree` 的移动端菜单结构）。阶段 2 的任何样式归一都会撞上这些测试，**必须同步更新测试**，把它们从"匹配 CSS 文本"改成"匹配行为/类名契约"。

### 阶段 3 — 视觉主题（预估 3-5 人天，需先定方向）

见第四节选项。

---

## 五、已确认的方向

| 决策项 | 结论 |
| --- | --- |
| 视觉方向 | **B. 轻量主题化** —— 保留浅色底，靠配色/圆角/字体/激励动效做出"修行"气质，不做深色 RPG 重做 |
| 主攻端 | **浏览器移动端 + APK 一起**（同一套 Web 代码，基础修复两头都吃到，验收标准分开） |
| 导航 | **允许改信息架构**，底部 tab 按使用频率重排，低频域收进二级入口 |
| 验证方式 | **切到 danger-full-access**，由我启动 dev server + Playwright 截 375px / 768px 图做前后对比 |

> 当前会话仍是 workspace-write，`pwsh` 因 `SetNamedSecurityInfoW ... grantWrite` 失败、`win_bash` 需 danger-full-access，**无法执行 npm / vite / build**。阶段 0 的改动虽然小，但没有 `npm run build` 兜底不应合并，所以开关没切过来之前只做方案、不动代码。

### 方向 B 的具体含义（避免歧义）

不是换掉现在的配色，而是在现有 `--color-primary`（天蓝 `#0284C7`）体系上做四件事：

1. **加一层"修行"色**：保留天蓝作主色（已达 4.5:1 对比度），引入金 `--color-gold #F59E0B` 作成就/境界专用色，青色 `--color-accent` 作修为进度色——语义分离，而非重新配色。
2. **圆角收敛**：现在 12/14/16/22/26px 混用，统一到 `--radius-card: 16px` / `--radius-control: 12px` / `--radius-pill: 999px` 三档。
3. **字体分层**：正文系统字体栈（去掉外网字体），数字/等级/境界这类"数值展示"用 `font-variant-numeric: tabular-nums` + 更重的字重做出仪表感。
4. **激励动效**：签到/升级/完成任务时给 150-300ms 的数值弹跳或进度条填充，统一走 `prefers-reduced-motion` 降级。

---

## 六、建议的落地顺序

```
阶段 0（地基）  →  阶段 1（移动端）  →  [截图复盘]  →  阶段 2（系统化）  →  阶段 3（主题）
       0.5d              2-3d                              3-5d              3-5d
```

阶段 0 单独就能发布一次，风险极低；阶段 1 完成后移动端体感会有明显跃迁；阶段 2/3 视你对"长期可维护"和"视觉辨识度"的取舍再定。

---

## 七、本轮已交付（阶段 0 + 阶段 1 主体）

### 已改文件

| 文件 | 改动 |
| --- | --- |
| `frontend/index.html` | 删掉 Google Fonts 两个 `<link>`；viewport 补 `viewport-fit=cover`；新增 `theme-color`（`#F8FAFC`）与 `color-scheme: light` |
| `frontend/src/App.vue` | 删 `@import` 外网字体；`--font-family` 收敛为系统字体栈并补 CJK 字体；新增 `--radius-card/-control/-pill`；新增全局按压态（`scale(.97)`，`:where()` 低优先级，触屏设备才加 transition）；移动端表单控件字号提到 16px 防缩放 |
| `frontend/src/router/index.js` | 所有路由补 `meta.title`，页面标题从路由声明，不再是布局里手写易漏的映射表 |
| `frontend/src/components/layout/AppLayout.vue` | 底部导航重排为 **首页 / 待办 / 记账 / 笔记 / 我的**；改用 `activeTab` + `aria-current` 判定，消除「`/` 前缀匹配导致双高亮」；`pageTitle` 改读 `route.meta.title`；底部 tab 的 `:hover` 与 active 拆开，不再把 hover 当按压；接入 Android 返回键 |
| `frontend/src/components/layout/Sidebar.vue` | 折叠态品牌渲染 `LQ`，不再把 "LifeQuest" 裁成 "LifeQues" |
| `frontend/src/views/Todos.vue` | 移动端 `.todo-card-header` 改单列，操作按钮下移到独立一行；标题恢复单行，不再一字一行 |
| `frontend/src/views/Stats.vue` | `.bar-chart` 加 `position: relative`（y 轴定位基准）+ 左内边距；移动端去掉 `min-width: 520px`，柱状图按容器宽度自适应 |
| `frontend/src/views/Shop.vue` | 移动端页头标题块独占一行，钱包胶囊下移右对齐；「N 件奖励可兑换」不再折行 |
| `frontend/src/composables/useAndroidBackButton.js` | 新增：优先关闭最上层弹层（Element Plus 与手写 `@keydown.esc` 弹层都覆盖），其次 `router.back()`，首页才 `App.exitApp()` |
| `frontend/android/app/src/main/res/values/styles.xml` | `DayNight` → `Theme.AppCompat.Light.NoActionBar`；补状态栏/导航栏颜色与亮色图标 |
| `frontend/android/app/src/main/AndroidManifest.xml` | activity 补 `android:windowSoftInputMode="adjustResize"` |
| `frontend/src/views/review-regressions.test.mjs` | 周复盘可达性断言从"布局里的字面量映射"改为"路由 meta + 布局读 meta" |

### 验证结果

- `cd frontend && npm run build`：通过
- `cd frontend && npm test`：247 项，246 通过 / 1 跳过（跳过项为原有），0 失败
- Playwright 复跑 10 页 × 2 视口（375/768）：无横向溢出（`scrollWidth == innerWidth`）、无 console 报错；底部导航在 `/todos`、`/finance`、`/notes`、`/profile` 各自只亮一个 tab
- 截图基线：`frontend/.harness/shots/`（`*.png` 与脚本已 gitignore）

### 本轮没做（需要下一轮）

| 项 | 原因 |
| --- | --- |
| `AppState` 三态统一组件 | 各页空态都带业务 CTA（如商城「创建商品」、记账「去记账」），统一前要先定义插槽结构，草率抽会丢功能 |
| 43 处散落 media query 的全量收敛 | 与 `ui-regressions.test.mjs` 里匹配 CSS 文本的断言强耦合，必须和阶段 2 的组件化一起做 |
| 登录/注册页的移动端布局 | 手机端登录卡片下方仍有约 300px 空白、768px 下产品介绍块被隐藏，属视觉重排，留给方向 B 的视觉阶段 |
| 商城页头「商城」与页面内「商城」标题重复 | 信息层级问题，需要和整体页头规范一起定 |
| 表单页吸底按钮、键盘高度变量 | `adjustResize` 已解决"被键盘盖住"，吸底按钮属于交互重排 |

---

## 八、第二轮（TDD）：设计系统组件库

严格先写测试再实现：`frontend/src/components/ui-system.test.mjs` 先红（9 项全失败），再逐个组件做到绿，最后加"落地断言"防止组件写完却没人用。

### 新增组件（`frontend/src/components/ui/`）

| 组件 | 契约 |
| --- | --- |
| `AppState.vue` | 三态（loading / empty / error）统一表面；error 自动切 `role="alert"`，loading 带 `aria-busy`；`#actions` 插槽保留各页业务 CTA，`#icon` 可覆盖图标 |
| `AppButton.vue` | `variant`（primary / secondary / ghost / danger）、`size`、`block`、`loading`；`min-height: var(--touch-target-min)`，loading 时 `aria-busy` |
| `AppCard.vue` | 统一 `--radius-card` 表面，`interactive` 才给 hover 反馈 |
| `AppBadge.vue` | `tone` 映射到既有色板，`gold` 专门留给成就/境界 |
| `AppField.vue` | label 的 `for` 与控件 `id` 强绑定，hint/error 通过 `aria-describedby` 关联，错误态 `role="alert"` |
| `AppSheet.vue` | `Teleport` 到 body，移动端底部抽屉 / 桌面居中；Esc 与遮罩关闭，`pending` 时拒绝关闭 |
| `AppTabs.vue` | 真 `role="tablist"` / `role="tab"` + `aria-selected`，支持计数徽标 |
| `AppList.vue` | `ul` 语义 + `dense` 紧凑模式，替代各页重复的列表脚手架 |

### 已落地替换

| 页面 | 改动 |
| --- | --- |
| `Shop.vue` | 分类条 → `AppTabs`；商品标签 → `AppBadge`；加载/错误/两种空态 → `AppState`（空态 CTA 走 `#actions` 插槽）；删除本页重复的 `.loading-state` / `.error-state` / `.empty-*` / `.shop-category` 样式 |
| `Projects.vue` | 加载态、错误态（含重试）、空态（含"新建项目"）→ `AppState` + `AppButton`；删除重复状态样式 |
| `Backpack.vue` | 同上（空态 CTA 为"前往商城"）；移动端分类 tab 收紧间距，不再横向溢出 |
| `Finance.vue` | 加载/错误首屏态 → `AppState` + `AppButton`；内联错误条保留（它是"有旧数据时"的降级提示） |
| `Stats.vue` | 加载/错误首屏态 → `AppState` + `AppButton`；顺带修掉重复预留底部导航高度导致的整页空白 |
| `home/TodayWorkbench.vue` | 移动端页头动作按钮（闭关专注 / 刷新）换行，不再被挤出屏幕 |

### 第二轮验证

- `node --test src/components/ui-system.test.mjs`：13 项全绿（含 5 项"组件必须被真实使用"的落地断言）
- `npm run build`：通过
- `npm test`：260 项，259 通过 / 1 跳过 / 0 失败
- Playwright 复跑 11 页 × 2 视口：**无横向溢出**（探针已排除滚动容器内的预期溢出）

### 图标去 emoji（第二轮内完成）

7 个文件、9 处 emoji 图标全部换成 `lucide-vue-next`，并补了对应尺寸样式：

| 位置 | 原 | 现 |
| --- | --- | --- |
| 待办 / 今日工作台的「闭关专注」 | 🧘 | `Sparkles` |
| 待办卡片操作区的闭关按钮 | 🧘 | `Sparkles` |
| 笔记已置顶标记 | 📌 | `Pin` |
| 闭关弹窗的典籍入口 / 绑定事项 | 📜 / 🎯 | `ScrollText` / `Target` |
| 奇遇目录锁定态 | 🔒 | `Lock` |
| 奇遇奖励条 | ✨ / 💎 / 🎁 | `Sparkles` / `Gem` / `Gift` |
| 商城「精选推荐」 | ✨ | `Sparkles` |

对应测试 `interface icons come from the lucide set instead of emoji glyphs` 会拦住回退。

## 九、第三轮（TDD）：组件接入页面 + 方向 B 视觉层

`frontend/src/views/design-system-adoption.test.mjs` 先红 8 项，实现后全绿。

| 项 | 结果 |
| --- | --- |
| 商城新建/编辑弹窗 | 换成 `AppSheet`（移动端贴底抽屉、桌面居中）+ `AppField`（label/for/id 绑定、hint 关联）+ `AppButton`（新增 `nativeType`，用 `form` 属性关联提交） |
| 商城商品网格 | `div` 列表 → `AppList`（`ul`/`li` 语义） |
| 首页快捷行动 | `section` → `AppCard`，删除页面里重复的卡片外壳样式 |
| 数字仪表感 | `App.vue` 新增 `.metric-figure`（`tabular-nums`），Home 四项指标、Stats 概览、Profile 等级/金币/经验统一使用 |
| 金色成就语义 | `.profile-title-badge` 从蓝色渐变改为金色语义（`--color-gold` + 半透明底 + 描边） |
| 激励动效 | 新增 `composables/useValuePulse.js`：金币上涨时短暂高亮，只在上涨时触发，`prefers-reduced-motion` 下完全静默 |
| 登录/注册页 | 去掉 `margin-top: 8vh` 的顶对齐，改为垂直居中（实测卡片 180–632px，上下等距） |
| 商城页头 | 删除与顶栏重复的「商城」标题，改为一行元信息 |
| 圆角收敛 | 全局 28 处 `14px`、6 处 `22px`、12 处 `999px` 全部换成 `--radius-card` / `--radius-pill` 语义 token |

### 顺带修掉的两个实测缺陷

1. **抽屉表单溢出**：图标选择器的网格项默认 `min-width: auto`，把整张表单撑到 594px（视口 375px），输入框全部溢出屏幕。补 `min-width: 0` 并让网格 `auto-fill` 后回到 327px。
2. **移动端双倍留白**：页面根节点各自加 `var(--spacing-md)`，叠加 shell 的 `--page-padding-x`，在 375px 上形成 32px 双侧留白。改为由 shell 独占留白后，实测卡片左边缘从 32px 回到 16px，**每页内容宽度增加 32px（约 5%）**。这一处重置同时替代了十几个页面里各自的车轱辘 padding。

### 第三轮验证

- `node --test src/views/design-system-adoption.test.mjs`：8 项全绿
- `npm run build`：通过
- `npm test`：268 项，267 通过 / 1 跳过 / 0 失败
- Playwright 9 页 × 2 视口：无横向溢出；抽屉、登录页、商城页头、个人页金色称号均已截图确认

### 剩余（可选，无视觉影响）

| 项 | 说明 |
| --- | --- |
| 13 个次级页面的状态块仍是旧标记 | 记账子页、历史页、笔记编辑等仍写 `class="loading-state/error-state/empty-state"`。这些类的外观本就由 `stitch-overrides.css` 统一，迁移到 `AppState` 只是代码洁癖、像素零差异，因此没有为「看起来全改完」而强行改动 |
| 各页空态文案 | 空态带各自的业务引导（去商城、去记账…），结构已由 `AppState` 的 `#actions` 插槽承载，文案保持页面自述 |

## 十、第四轮（TDD）：收尾与最终验收

| 项 | 结果 |
| --- | --- |
| 页面根残留 padding | 18 个文件里 page-root 的 `padding*` 声明全部移除，留白只由 shell 提供；新增测试 `page roots own no gutter and never reserve the bottom navigation twice` 扫描全部 `.vue`，防止回潮 |
| 底部导航重复预留 | Calendar / Finance 及其子页、CoinHistory、ProjectDetail 等 9 处 `padding-bottom: calc(... + var(--bottom-nav-height))` 清除，移动端底部不再多出一大块空白 |
| 高频表单吸底 | 待办与记账的新建/编辑弹窗在手机端 `.dialog-actions` 改为 `position: sticky; bottom: 0`，键盘弹出时提交按钮仍可见（`AppSheet` 的页脚本来就在滚动区之外） |
| 分段控件过宽 | `AppTabs` 改为 `inline-flex` + `flex: 0 1 auto`，两个分类时不撑满桌面宽度 |
| 价格换行 | 商品价格 `white-space: nowrap`，桌面四列时「100 金币」不再断成两行 |
| 行尾符污染 | 用脚本批量改写时误把 29 个文件转成 CRLF，导致 diff 虚增、并有按 `\n` 匹配的测试失败；已全部归一回 LF |

### 最终验收

| 检查 | 结果 |
| --- | --- |
| `npm run build` | 通过 |
| `npm test` | **270 项，269 通过 / 1 跳过（原有）/ 0 失败** |
| Playwright 11 页 × 3 视口（375 / 768 / 1280） | 33 组全部无横向溢出、无 console 报错、底部导航每个页面只亮一个 tab |
| 视觉抽查 | 待办卡片标题单行、统计图表归位、商城抽屉与分段控件、登录页居中、个人页金色称号、桌面侧栏 |

### 明确不做

- 深色模式：方向 B 已确认保持浅色单主题。

