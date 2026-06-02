# LifeQuest 当前问题清单

> 说明：以下问题基于当前仓库代码审计、后端 `pytest`、前端构建和 Playwright 端到端验证结果整理。

## 测试范围
- 后端：鉴权、待办、笔记、商城、背包、成就、用户资料
- 前端：登录、注册、首页、待办、笔记、商城、背包、个人资料
- 浏览器：真实页面主流程与关键异常路径

## 当前问题

### 1. 高：完成接口可重复领奖，缺少幂等保护
- 现象：同一条习惯、任务或目标的完成接口被重复调用时，金币和经验会再次增加。
- 影响：用户可以通过重复请求刷资源，破坏经济系统一致性。
- 证据文件：
  - [`backend/app/services/todo.py`](D:/codes/LifeQuest/backend/app/services/todo.py#L86)
  - [`backend/app/services/todo.py`](D:/codes/LifeQuest/backend/app/services/todo.py#L115)
  - [`backend/app/services/todo.py`](D:/codes/LifeQuest/backend/app/services/todo.py#L143)
  - [`backend/app/api/todos.py`](D:/codes/LifeQuest/backend/app/api/todos.py#L85)
  - [`backend/app/api/todos.py`](D:/codes/LifeQuest/backend/app/api/todos.py#L151)
  - [`backend/app/api/todos.py`](D:/codes/LifeQuest/backend/app/api/todos.py#L217)

### 2. 高：子任务功能前后端接口不一致，页面不可用
- 现象：前端按“goal 子任务”调用接口，但后端实际提供的是“task 子任务”接口；前端还按 `status` 渲染，后端返回的是 `is_completed`。
- 影响：待办页中的子任务区域无法正常加载、完成或展示状态。
- 证据文件：
  - [`frontend/src/services/todo.js`](D:/codes/LifeQuest/frontend/src/services/todo.js#L154)
  - [`frontend/src/services/todo.js`](D:/codes/LifeQuest/frontend/src/services/todo.js#L165)
  - [`frontend/src/services/todo.js`](D:/codes/LifeQuest/frontend/src/services/todo.js#L175)
  - [`frontend/src/views/Todos.vue`](D:/codes/LifeQuest/frontend/src/views/Todos.vue#L326)
  - [`frontend/src/views/Todos.vue`](D:/codes/LifeQuest/frontend/src/views/Todos.vue#L330)
  - [`frontend/src/views/Todos.vue`](D:/codes/LifeQuest/frontend/src/views/Todos.vue#L901)
  - [`backend/app/api/todos.py`](D:/codes/LifeQuest/backend/app/api/todos.py#L229)
  - [`backend/app/schemas/todo.py`](D:/codes/LifeQuest/backend/app/schemas/todo.py#L134)

### 3. 高：修改用户名会导致登录态失效
- 现象：资料页修改用户名后会回到登录状态。
- 原因：JWT 的 `sub` 使用的是用户名，用户名一改，旧 token 立即无法解析当前用户。
- 影响：用户名编辑功能实际上不可用。
- 证据文件：
  - [`backend/app/api/auth.py`](D:/codes/LifeQuest/backend/app/api/auth.py#L17)
  - [`backend/app/api/auth.py`](D:/codes/LifeQuest/backend/app/api/auth.py#L26)
  - [`backend/app/api/auth.py`](D:/codes/LifeQuest/backend/app/api/auth.py#L58)
  - [`frontend/src/views/EditProfile.vue`](D:/codes/LifeQuest/frontend/src/views/EditProfile.vue#L135)
  - [`frontend/src/views/EditProfile.vue`](D:/codes/LifeQuest/frontend/src/views/EditProfile.vue#L156)

### 4. 中高：重复用户名或邮箱更新返回 500
- 现象：更新个人资料时，如果用户名或邮箱与其他用户重复，接口直接抛 500。
- 影响：前端只能看到服务端异常，无法得到明确的字段级错误提示。
- 证据文件：
  - [`backend/app/api/users.py`](D:/codes/LifeQuest/backend/app/api/users.py#L21)
  - [`backend/app/services/user.py`](D:/codes/LifeQuest/backend/app/services/user.py#L17)
  - [`backend/app/services/user.py`](D:/codes/LifeQuest/backend/app/services/user.py#L42)
  - [`backend/app/repositories/base.py`](D:/codes/LifeQuest/backend/app/repositories/base.py#L26)
  - [`backend/app/models/user.py`](D:/codes/LifeQuest/backend/app/models/user.py#L13)

### 5. 中：成就不会随业务完成自动解锁
- 现象：完成任务后，`/api/achievements/me` 仍然为空，成就不会自动发放。
- 影响：个人资料中的成就区域长期无数据，成就系统无法按设计工作。
- 证据文件：
  - [`backend/app/services/achievement.py`](D:/codes/LifeQuest/backend/app/services/achievement.py#L69)
  - [`backend/app/main.py`](D:/codes/LifeQuest/backend/app/main.py#L22)
  - [`backend/app/api/achievements.py`](D:/codes/LifeQuest/backend/app/api/achievements.py#L16)

## 结论
- 当前最优先处理的是“重复完成重复领奖”和“子任务接口不一致”。
- 其余问题会直接影响资料编辑和成就展示，属于可见功能缺陷。
