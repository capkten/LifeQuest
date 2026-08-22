# LifeQuest 交互与修炼界问题收口设计

日期：2026-08-22  
分支：`codex/notebook-write-race-closure`  
执行模型：`gpt-5.6luna`

## 目标

收口认证反馈、笔记本和笔记预览布局、修炼界业务交互、商城布局与中文文案问题，使所有关键写操作都有明确的成功、失败、加载、锁定和重试反馈，同时修复修炼待办无法完成和 NPC 请求冲突等真实业务链路问题。

## 已确认的交互原则

- 业务条件不足的按钮保持可点击；点击后弹出原因和下一步，不在页面上长期堆叠大段锁定文案。
- 登录、注册和普通操作结果使用 Toast；确认、表单、较长业务原因和可重试操作使用 Dialog。
- 请求处理中只禁用当前操作按钮，防止重复提交；业务锁定不使用原生 `disabled`。
- 所有机器错误码和稳定枚举通过中文映射展示，未知枚举使用中文兜底，不渲染英文 key。
- 弹框必须支持标题、描述、确认中状态、失败信息、重试、关闭、ESC 和焦点回收。
- 响应式验收覆盖 375x812、768x1024、1024x900、1440x1000，不允许横向溢出。

## 设计范围

### 1. 认证和共享反馈

登录失败时在登录卡片区域和 Toast 中显示明确错误；保留输入内容并允许重试。注册成功显示成功提示并继续既有跳转，注册失败保留表单并显示中文错误。请求中显示按钮 loading，重复点击不会产生重复请求。

复用现有 `useToast`、Element Plus `ElMessage` 和 `ElMessageBox`，不新增 `useFeedback` 或 `BaseDialog.vue`。只有当现有能力无法覆盖具体场景时，才在页面内增加最小弹框状态；避免引入第二套反馈基础设施。

### 2. 笔记本和笔记预览

笔记本文件树的五个操作按钮默认透明隐藏，不占用文件名布局空间；行悬停或 `:focus-within` 时显示，且不改变行高和文字位置。移动端没有 hover 时使用紧凑操作区，保证按钮可达且不覆盖名称。按钮必须带中文 `aria-label`。

`NoteViewer.vue` 正文容器增加统一内边距、标题和元信息留白、可读行高，并限制代码块、表格、图片的最大宽度。移动端使用更紧凑但仍明显的内边距。

### 3. 修炼、宗门、功法、NPC 和渡劫

所有业务锁定按钮保持可点击，点击后使用现有 Toast 或 Element Plus 弹框显示当前操作、后端权威原因和下一步。成功后显示 Toast 并刷新权威数据，失败后保留上下文并允许重试。

修炼待办使用现有 Todo 完成接口和奖励结算路径，完成后刷新待办、凡界资源、修为和飞升后的仙元/仙石转换，重复点击只结算一次。

宗门的加入、联系使者、参与试炼使用弹框；试炼弹框展示目标、进度、缺少条件和提交结果。功法购买使用确认弹框，展示格类型、价格、灵石余额、购买后余额、境界要求和失败原因；成功关闭并刷新，失败保留并允许重试。

NPC 遇见使用弹框，展示宗门和人口槽位。后端冲突转换为人口槽位占用、已遇见、冷却中、人口上限或状态不允许等可理解文案。渡劫使用确认弹框，展示渡劫丹、风险、失败损失、冷却和前置条件；成功、失败和冷却结果均保持可读。

### 4. 商城

推荐标识不再使用覆盖商品图标的定位方式，商品图标、推荐标签、标题和操作按钮使用稳定布局层。移动端使用纵向布局。`consumable`、`gear`、`collectible` 等内部枚举通过统一中文标签映射展示，未知类型显示“其他”。

## 代码边界

- 共享反馈：复用 `frontend/src/composables/useToast.js`、Element Plus `ElMessage`/`ElMessageBox` 和 `frontend/src/utils/errorMessage.js`。
- 认证：`frontend/src/views/Login.vue`、`frontend/src/views/Register.vue`、`frontend/src/services/auth.js`、认证回归测试。
- 笔记：`frontend/src/views/NotebookFileManage.vue`、`frontend/src/components/notes/NoteViewer.vue`、相关 UI 回归测试。
- 修炼：`frontend/src/views/Cultivation.vue`、`frontend/src/views/Sects.vue`、`frontend/src/views/Techniques.vue`、`frontend/src/views/Npcs.vue`、`frontend/src/views/Tribulations.vue`、`frontend/src/services/cultivation.js`、`backend/app/services/todo.py`、相关 API 和测试。
- 商城：`frontend/src/views/Shop.vue`、`frontend/src/utils/displayLabels.js`、商城/背包回归测试。
- 验收：后端全量 pytest、前端 Node 回归、生产构建和四视口手动/浏览器验收。

## 错误处理与数据流

页面操作先设置本地 pending 状态，再调用现有 service。服务端返回的错误保留原始 code/detail，由 `getErrorMessage` 和共享反馈层转换为中文。成功响应中的资源、状态和奖励 delta 为唯一权威来源，页面不得自行推导业务结果。失败时不清空当前上下文；重试沿用当前表单或弹框数据。

## 测试策略

- 先为每个问题添加失败回归测试，再实现最小改动。
- 前端测试覆盖 Toast/Dialog 可见性、pending 锁、失败保留、重试、键盘焦点、hover/focus 布局和中文枚举。
- 后端测试覆盖修炼待办完成、奖励幂等、NPC 冲突映射所需的稳定错误、现有宗门/功法/渡劫接口回归。
- 构建前运行全量相关 Node 测试；构建后运行生产构建和 `git diff --check`。
- 浏览器验收记录四视口的关键操作、错误提示、控制台错误、网络失败和横向溢出；未执行的浏览器场景不得标记为 verified。

## 非目标

- 不替换现有认证、Todo、修炼和奖励 API 的总体架构。
- 不新增重复的反馈基础设施，不重写 Element Plus 或现有主题系统。
- 不把业务锁定改成永久禁用按钮。
- 不修改用户级 npm 配置或提交任何密钥。
