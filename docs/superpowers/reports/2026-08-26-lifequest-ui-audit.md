# LifeQuest UI 审查记录

日期：2026-08-26  
范围：现有前端 UI 的 PC / 平板 / 移动端体验、视觉层级、组件一致性、响应式行为  
审查方式：静态代码审查 + Playwright 构造数据渲染验证  
状态：仅记录问题，本次未修改产品代码

## 审查结论

当前结论：❌ NOT READY

仍有 1 项发布阻塞级问题（弹窗焦点管理），另有 4 项本迭代问题。构建可以通过，但构建通过不代表键盘可达性和移动端遮挡问题已解决。

## 验证记录

- `cd frontend && npm run build`：通过。
- 登录页在 1440×900、1024×768、390×844 下渲染成功，无横向溢出。
- 首页使用构造认证状态和 API 返回数据，在 1440×900、390×844 下渲染成功，无横向溢出。
- 390px 首页截图确认固定底部导航覆盖“今日任务”内容区域。
- 代码检查确认 Notes 的新建/删除弹窗焦点处理不一致。
- 代码检查确认搜索结果和笔记本卡片使用 `div[role="button"]`，仅绑定 Enter。

## Findings

### ⛔ P0 / release-blocker：弹窗焦点管理不完整

证据：

- `frontend/src/views/Notes.vue:193-205`：新建弹窗有初始输入框聚焦，但关闭时没有恢复到触发按钮。
- `frontend/src/views/Notes.vue:249-263`：删除确认弹窗没有 `aria-labelledby`、Tab 焦点循环、Esc 关闭或关闭按钮。
- `frontend/src/views/Notes.vue:310-317`：只监听 `showDialog`，删除弹窗没有同等焦点逻辑。

影响：键盘用户打开并关闭弹窗后可能丢失原位置；删除弹窗打开后焦点可能落在文档主体，读屏用户难以确认当前上下文。该问题位于已认证应用的核心操作路径，按焦点锁定/恢复规则列为发布阻塞。

建议：统一抽取可复用 Dialog 行为；打开时将焦点移入，Tab 只在弹窗内循环，Esc 按产品规则关闭，关闭后恢复触发按钮焦点；所有弹窗补齐唯一标题关联。

### ⚠️ P1 / fix-this-sprint：移动端固定底部导航遮挡内容

证据：

- `frontend/src/components/layout/AppLayout.vue:218-236`：底部导航为 `position: fixed`，内容区仅设置底部 padding。
- 构造数据渲染：390×844 首页截图中，底部导航覆盖“今日任务”卡片中部内容；导航上缘没有明确滚动边界或遮挡提示。

影响：用户滚动首页时可能看不到被固定导航覆盖的任务内容或操作反馈。

建议：将底部安全区统一纳入内容滚动容器的有效 inset，并验证首屏、中段和最后一项内容均可完整滚过导航；同时检查弹窗和 toast 与底部导航的 z-index 关系。

### ⚠️ P1 / fix-this-sprint：卡片交互使用非语义按钮

证据：

- `frontend/src/views/Notes.vue:81-89`：搜索结果使用 `div role="button"`，仅处理 Enter。
- `frontend/src/views/Notes.vue:158-162`：笔记本卡片使用 `div role="button"`，仅处理 Enter。

影响：Space 键行为缺失，语义和键盘行为依赖手工补齐；后续增加焦点、禁用或加载状态时容易与真实按钮不一致。

建议：改为真实 `<button>` 或 `<router-link>`；若必须保留容器交互，至少补齐 Space、焦点样式和明确的可访问名称。

### ⚠️ P1 / fix-this-sprint：弹窗关闭按钮小于移动端触控目标

证据：

- `frontend/src/views/Notes.vue:924-936`：`.dialog-close` 为 32×32px。
- 同类实现还存在于 `Finance.vue:1053-1068`、`Todos.vue:2352-2371` 等页面。
- 项目全局已定义 `--touch-target-min: 44px`，但该类按钮未使用。

影响：移动端关闭弹窗容易误触，尤其是在确认、编辑和删除操作连续出现时。

建议：统一关闭按钮最小宽高为 44px，并保留足够的相邻控件间距。

### 📋 P2 / backlog：样式覆盖层和页面局部样式并存

证据：

- `frontend/src/App.vue:242-317`：全局选择器统一覆盖大量卡片、状态和焦点样式。
- `frontend/src/styles/stitch-overrides.css:334-422`：再次覆盖按钮、tabs、卡片、表单和 focus 样式。
- 多个页面继续保留同类 `.dialog-close`、`.btn-primary`、`.empty-state` 的局部定义。

影响：当前视觉方向基本统一，但后续调整 token 或组件状态时容易产生级联覆盖和跨页面差异。

建议：后续修复时优先建立共享 Button / Dialog / EmptyState 组件或集中样式入口，再逐步删除重复局部规则；不建议仅继续添加更高优先级覆盖。

## PC 与移动端观察

### PC / 平板

- 1440px：侧栏、顶部栏、首页 hero 与双栏内容层级清晰；首页无横向溢出。
- 1024px：侧栏折叠策略有效；但统计、财务、笔记等高密度页面仍应使用真实长文本和真实列表继续检查。
- 首页空状态高度偏大，空数据下主内容区出现较多留白；属于体验优化项，不作为本轮阻塞问题。

### 移动端

- 390px 登录页和首页无横向溢出。
- 首页 hero、签到按钮和指标区能够收缩到窄屏布局。
- 固定底部导航遮挡中段内容，是移动端最明显的问题。
- 笔记筛选栏在窄屏会换行，功能可用但会拉长首屏滚动距离。

## 视觉层级与组件一致性

- 统一 token、DM Sans 正文、Space Grotesk 标题和蓝绿主色已经形成稳定视觉方向。
- 首页/登录页的品牌表达强于业务内页；业务页主要依赖白卡片和边框区分层级，长期可考虑减少卡片堆叠。
- 弹窗行为、关闭按钮尺寸、空状态 CTA 和焦点管理尚未形成统一组件契约。
- 首页“今天没有待办事项”只有文案，没有直接创建任务 CTA；列为后续空状态体验改进，不升级为阻塞问题。

## 本轮未判定为问题的项目

- 登录页和首页三种主要视口均无横向溢出；因此未报告通用 overflow 问题。
- 全局存在 `:focus-visible` 样式，且多数主要按钮达到 44px；因此未报告“所有交互控件缺少焦点样式”。
- 多数数据页面已有 loading / empty / error 分支；因此未将整个项目判定为 happy-path-only。
- `prefers-reduced-motion` 已在全局和部分页面处理；因此未报告完全缺失动效降级。

## 延后到其他工具

- WCAG 规则、颜色对比度、ARIA 完整性：建议运行 axe-core / eslint-plugin-jsx-a11y。
- CWV、CLS、LCP、INP：建议运行 Lighthouse / web-vitals。
- 全路由像素级差异：建议运行 Playwright screenshots 或 Chromatic。
- 真实端到端业务流程：建议补充 Playwright / Cypress 已认证流程。

## 建议修复顺序

1. 统一所有弹窗的焦点进入、焦点陷阱、Esc 关闭和关闭后恢复。
2. 修复移动底部导航的内容安全区和滚动遮挡。
3. 将笔记交互卡片替换为语义按钮或链接。
4. 统一关闭按钮和其他图标按钮的 44px 触控尺寸。
5. 收敛全局覆盖与页面局部样式，减少级联依赖。

## 移动端专项审查：iOS / Android / 移动网页

审查依据：`Mobile App Design Standards`，重点检查平台导航约定、触控目标、安全区、输入法适配、系统返回和可访问性。项目使用 Vue + Capacitor，因此同时适用 WebView 原生容器和移动浏览器约束。

### iOS

#### ⚠️ P1：关闭按钮和弹窗行为不符合稳定的 iOS 触控/返回预期

- iOS 触控目标最低为 44×44pt；当前多个 `.dialog-close` 仍为 32×32px，详见上方 P1 finding。
- 弹窗普遍使用居中网页 Dialog，而不是针对移动任务采用带明确取消/完成动作的 sheet 或全屏表单。
- 新建与删除弹窗的焦点进入、退出和恢复不一致；在 VoiceOver 场景下尤其容易丢失上下文。

调整建议：移动端优先采用接近 iOS page sheet 的结构；顶部提供明确的取消/完成动作；关闭后恢复触发控件；删除操作使用具体动词和明确的取消路径。

#### ⚠️ P1：未覆盖 iOS 动态字体和键盘可见区

证据：

- `frontend/src/App.vue:55-60` 使用固定 CSS 字号 token，没有发现针对系统较大字体的布局策略。
- `frontend/src/views/NoteEditor.vue:287`、`frontend/src/views/NoteEditor.vue:330` 使用 `100vh` 计算编辑器高度。
- `frontend/src/views/Calendar.vue:750` 使用 `calc(100vh - 180px)` 限制移动内容高度。

影响：iPhone 开启较大文字或软键盘后，标题、保存操作和编辑区域可能被压缩或遮挡。移动 WebView 不会自动获得原生 Dynamic Type 的布局适配。

调整建议：正文和重要操作至少保持 16px；支持浏览器文字放大与内容换行；可视区域高度改用 `100dvh` / `visualViewport` 方案，并在真机上验证键盘弹出、横竖屏和安全区。

#### 📋 P2：缺少可选的 iOS 操作反馈

任务完成、签到、删除确认等关键动作目前只有视觉 toast，没有 Capacitor Haptics 反馈。不是功能阻塞，但可在高频完成操作中增加轻量成功/错误反馈，并尊重系统静音和辅助功能设置。

### Android

#### 📋 P2：Android 返回行为没有显式产品级处理，需在真机确认

证据：

- `frontend/android/app/src/main/java/com/lifequest/app/MainActivity.java` 只注册插件和处理生命周期，没有 `BackButton` / `OnBackPressedDispatcher` 处理。
- `frontend/src/main.js` 没有 Capacitor App `backButton` 监听。
- 应用存在多层嵌套路由，如 `/notes/:notebookId/view/:noteId`、`/projects/:id` 和多个弹窗状态。

风险：Android 系统返回键在编辑页、详情页、弹窗打开状态下可能无法按用户预期逐层返回；在某些 WebView 状态下可能直接退出或跳回错误层级。当前属于需真机确认的高风险交互，不应以浏览器 history 行为代替验证；在获得真机证据前不计入已确认的发布阻塞数。

调整建议：统一定义返回优先级：先关闭弹窗/抽屉，其次返回上一层路由，最后才退出应用；在 Capacitor `App.addListener('backButton', ...)` 或 Android 返回分发器中实现，并覆盖未保存笔记编辑状态。

#### ⚠️ P1：触控目标按 44px 设计，低于 Android 48dp 标准

证据：

- `frontend/src/App.vue:88`：`--touch-target-min` 为 44px。
- `frontend/src/components/layout/AppLayout.vue:251-252`：移动底部导航项最小尺寸为 44×44px。
- `frontend/src/views/Notes.vue:924-936` 以及多个页面的关闭按钮为 32×32px。

影响：Android 设备上图标按钮和底部导航更容易误触，尤其是删除、关闭等相邻操作。

调整建议：原生 Android 目标最小采用 48×48dp；网页端可维持 44px 的 WCAG 下限，但 Capacitor 构建应使用 48px 触控区域和至少 8px 间距。

#### ⚠️ P1：Android TalkBack 的动态反馈和语义交互仍不统一

- Notes 的搜索结果和笔记本卡片使用 `div role="button"`，只处理 Enter，没有 Space 行为；在 TalkBack/键盘辅助场景下不如原生 button 稳定。
- toast 和部分操作反馈虽有 `role`，但不同页面实现不一致，需确认 TalkBack 是否能在动作完成后及时获得结果。
- 关闭/确认弹窗的标题关联不完整，删除笔记本弹窗尤其明显。

调整建议：使用原生 `<button>` / `<a>` 语义，给动态结果和操作结果统一 live region；删除和保存等动作在 TalkBack 下应能读出对象名称、状态和结果。

### 移动网页 / PWA 浏览器

#### ⛔ P0：固定底部导航会覆盖可滚动内容

这与上一节移动端 finding 相同，在 390×844 构造数据渲染中已确认。移动浏览器还会叠加地址栏收缩、底部手势条和浏览器 safe-area，当前仅靠固定 padding 不足以证明内容始终可见。

调整建议：以 `env(safe-area-inset-bottom)` 和实际导航高度共同计算滚动容器的底部 inset，验证最后一项内容、toast、弹窗操作区和输入法展开状态。

#### ⚠️ P1：`100vh` 不适合作为移动浏览器可视高度的唯一依据

证据：

- `frontend/src/App.vue:107`、`frontend/src/components/layout/AppLayout.vue:147` 使用 `100vh`。
- `frontend/src/views/NoteEditor.vue:287`、`frontend/src/views/NoteEditor.vue:330` 使用 `100vh`。
- `frontend/src/views/Calendar.vue:750` 和 `frontend/src/views/NotebookFileManage.vue:690` 使用 `100vh` 计算内容区域。

影响：Safari/Chrome 移动地址栏展开或收起时，固定高度区域可能产生底部空白、内容被截断或操作按钮被键盘盖住。

调整建议：优先使用 `100dvh`；对需要兼容旧浏览器的区域采用 `min-height: 100vh; min-height: 100dvh`，并对编辑器、弹窗、底部导航分别做可视区验证。

#### ⚠️ P1：移动端文字层级有低于建议下限的字号

证据：

- `frontend/src/views/Login.vue:187`、`:272` 使用 10px。
- `frontend/src/views/Login.vue:281` 使用 11px。
- `frontend/src/components/layout/AppLayout.vue:257`：底部导航标签为 10px。
- `frontend/src/views/Calendar.vue:737` 使用 9px。

影响：在小屏、高亮环境和浏览器文字缩放下，状态、导航和日历信息难以阅读。移动标准建议正文 16px，标签不低于 11-12pt；Android/浏览器文字放大时也应保持可读和不重叠。

调整建议：把 9/10px 限制在非关键装饰性文字；导航、状态、日期和操作提示提升到至少 11-12px，正文维持 16px，并测试系统字体放大 200%。

#### 📋 P2：移动网页未提供明确的安装态/离线态策略

当前页面有网络错误重试，但未发现针对 PWA 安装态、断网缓存、重新连接或离线编辑的统一策略。若产品定位仍是移动网页，这属于后续能力规划；若主推 Capacitor，则应优先完善原生返回、键盘和安全区，而不是先做 PWA 壳层。

## 平台专项验证边界

- 已完成：源码证据检查、移动网页 390px 构造数据渲染、横向溢出检查、底部导航覆盖检查。
- 尚未完成：iPhone Safari 真机/模拟器 VoiceOver、Android 真机/模拟器 TalkBack、Android 系统返回键、iOS 动态字体、软键盘弹出后的编辑器和弹窗。
- 因此 Android 返回键问题记录为高风险待真机确认；其余已有源码或网页渲染证据的问题可直接进入修复队列。
