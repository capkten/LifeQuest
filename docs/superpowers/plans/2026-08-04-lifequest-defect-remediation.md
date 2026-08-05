# LifeQuest 缺陷修复与发布加固实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复当前已验证的功能、数据一致性、权限、MCP、部署和测试缺陷，使 LifeQuest 达到可重复验证、可安全部署的状态。

**Architecture:** 保留现有 FastAPI + SQLAlchemy + SQLite、Vue 3 + Vite + Capacitor 和 MCP SSE 结构。按边界拆分修复：schema/service 负责业务规则，API/service 共同负责资源归属，迁移集中处理，MCP 生命周期与 API worker 解耦。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite, pytest, Vue 3, Vite, Capacitor, Docker Compose, nginx, supervisor, MCP SSE。

## Global Constraints

- 所有文本文件使用 UTF-8 编码。
- 所有业务修复先写回归测试，再修改实现。
- 所有跨用户资源必须在服务端验证归属。
- 不改变现有成功响应字段；错误使用明确的 4xx 响应。
- 不提交 `.env`、数据库、上传文件、构建产物和运行时缓存。
- 最终验收必须包含后端测试、前端构建、Docker 健康检查和移动端响应式检查。

## 当前基线

- 后端：57 个测试中 56 个通过、1 个失败，失败为 `test_complete_goal_awards_rewards`。
- 前端：`npm run build` 通过，但存在大 chunk 警告。
- 部署风险：笔记迁移报 DateTime 类型错误；Docker healthcheck 使用 GET 登录接口；生产多 worker 会重复启动 MCP。
- 工作区有未跟踪的 `.agents/`、`.claude/skills/`、`.codex/` 和文档，修复过程中不得误删。

---

### Task 1: 建立回归基线

**Files:** Create `backend/tests/test_regressions.py`; modify `backend/tests/conftest.py` only when a shared fixture is required.

- [x] 复制目标完成场景，分别读取基础奖励、成就奖励、金币流水和重复完成结果。
- [x] 运行 `cd D:\codes\LifeQuest\backend; pytest -q`，记录失败测试和启动迁移错误。
- [ ] 提交：`git add backend/tests/test_regressions.py; git commit -m "test: capture current defect regressions"`。

---

### Task 2: 统一奖励规则和输入校验

**Files:** `backend/app/services/todo.py`、`backend/app/services/achievement.py`、`backend/app/schemas/todo.py`、`backend/app/schemas/shop.py`、`backend/tests/test_todos.py`、`backend/tests/test_shop.py`。

- [x] 测试首个目标完成：目标基础奖励 100、`goal_count` 成就奖励 50，最终增加 150，且流水来源可区分。
- [x] 测试任务、习惯、目标重复完成不重复发奖；负奖励和负商品价格返回 422；库存允许 `-1`，拒绝小于 `-1`。
- [x] 用 `Field(ge=0)` 约束奖励和商品价格；完成逻辑先判断完成状态，再在同一事务内写基础奖励、成就奖励和流水。
- [x] 运行 `cd D:\codes\LifeQuest\backend; pytest tests/test_todos.py tests/test_shop.py tests/test_regressions.py -q`。
- [ ] 提交：`git add backend/app backend/tests; git commit -m "fix: make reward rules and validation consistent"`。

---

### Task 3: 修复财务金额和资源归属

**Files:** `backend/app/schemas/finance.py`、`backend/app/api/finance.py`、`backend/app/services/finance.py`、`backend/tests/test_finance.py`、Create `backend/tests/test_finance_security.py`。

- [x] 测试交易、转账、预算、定期交易、债务和还款的 0、负数及超过本金场景，返回 422 或明确 400。
- [x] 创建两个用户，验证用户 A 不能修改用户 B 的账户、交易、分类、预算、债务和转账目标，且余额不变。
- [x] 金额使用 `Field(gt=0)`；校验 `0 <= remaining <= amount`；更新交易时重新验证新账户和转账目标；分类、预算、债务验证当前用户归属。
- [x] 余额变更、交易写入和经验/成就处理使用单一事务，异常执行 rollback。
- [x] 运行专项财务测试；未执行提交（当前任务禁止自动 commit）。

---

### Task 4: 修复项目和笔记节点归属

**Files:** `backend/app/api/projects.py`、`backend/app/services/project.py`、`backend/app/api/notes.py`、`backend/app/services/note.py`、`backend/tests/test_projects.py`、`backend/tests/test_notes.py`。

- [x] 测试两个用户的项目、阶段和里程碑，禁止任务跨用户、阶段跨项目、里程碑跨项目绑定。
- [x] 测试笔记从子目录移动到 `parent_id=null`，确认数据库父节点、展示路径和 Markdown 路径一致。
- [x] 在 `create_project_task` 和 `move_task` 中验证目标项目归属及阶段/里程碑归属；`NodeUpdate` 区分字段未提供和字段值为 null。
- [x] 运行项目和笔记专项测试；未执行提交（当前任务禁止自动 commit）。

---

### Task 5: 修复笔记迁移和文件数据库一致性

**Files:** `backend/app/services/note.py`、`backend/app/main.py`、`backend/tests/test_notes.py`、Create `backend/tests/test_note_migration.py`。

- [x] 构造旧表数据，验证 ISO 字符串和 Python datetime 都能迁移为合法 `datetime`，不再产生 SQLite DateTime 错误。
- [x] 模拟文件移动失败，验证事务回滚、旧表保留、节点不指向不存在的新路径。
- [x] 增加统一时间解析；先验证/移动文件，成功后提交节点；旧表只在全部成功后删除。
- [x] 创建/更新笔记使用临时文件替换，文件失败时回滚数据库，避免节点和 Markdown 分离。
- [x] 运行笔记专项测试和后端全量测试；未执行提交（当前任务禁止自动 commit）。

---

### Task 6: 修复 MCP 鉴权和进程生命周期

**Files:** `backend/mcp_server.py`、`backend/app/main.py`、`deploy/supervisord.conf`、`deploy/deploy-server.sh`、`.claude/mcp.json`、Create `backend/tests/test_mcp_security.py`。

- [x] 测试未 login、未设置受控服务账号时，MCP 读写工具都拒绝请求；两个用户会话不能串数据。
- [x] 移除 `_resolve_user_id` 回退数据库第一个用户的行为，只允许认证会话或显式受控服务账号。
- [x] API startup 默认不为 worker 创建 MCP 子进程；MCP 由 supervisor 单独启动一个实例；代理不可用时返回 503 并关闭客户端。
- [x] 运行 MCP 专项测试；未执行提交（当前任务禁止自动 commit）。

---

### Task 7: 修复 Docker 健康检查、持久化和启动错误

**Files:** `docker-compose.yml`、`Dockerfile`、`deploy/entrypoint.sh`、`backend/app/main.py`、Create `deploy/healthcheck.sh` 和 `backend/tests/test_startup_config.py`。

- [x] 增加无认证 `GET /api/health`，正常返回 `{"status":"ok"}`；数据库不可用时返回非 200。
- [x] 将 compose healthcheck 从登录接口改为 `/api/health`。
- [x] 确认数据库、上传和笔记目录均位于 `/app/data`；迁移、种子数据和目录创建失败时不能静默宣称服务正常。
- [ ] 运行 `cd D:\codes\LifeQuest; docker compose build; docker compose up -d; docker compose ps; curl.exe -i http://localhost/api/health; docker compose logs --no-color lifequest`。
- [ ] 预期容器 healthy、无 MCP 端口冲突和迁移异常；提交 `fix: harden production health checks and persistence`。

---

### Task 8: 清理异常吞噬并补齐后端测试

**Files:** `backend/app/services/finance.py`、`backend/app/services/shop.py`、`backend/app/services/project.py`、`backend/app/main.py`、`backend/mcp_server.py`；Create `backend/tests/test_error_paths.py`、`backend/tests/test_calendar_stats.py`、`backend/tests/test_debts_recurring.py`。

- [x] 模拟错误路径并确认主事务不假装成功，旁路失败记录日志。
- [x] 将关键异常路径改为 rollback/日志或明确业务错误；未发现仍有 `except Exception: pass`。
- [x] 补充日历、统计、债务、定期交易、项目 CRUD 和 MCP 的当前用户过滤、日期边界、重复触发和越权测试。
- [ ] 覆盖率命令在本环境 120 秒上限内未完成；全量功能测试 `73 passed`。

---

### Task 9: 完成前端响应式和 token 刷新回归

**Files:** `frontend/src/services/api.js` 及实际复现缺陷的 `frontend/src/views/*`；更新 `docs/superpowers/plans/2026-06-08-lifequest-h5-responsive-redesign.md`；Create `docs/superpowers/reports/2026-08-04-lifequest-defect-verification.md`。

- [x] 运行前端生产构建并完成开发服务器浏览器检查。
- [x] 在 375px、768px、1024px、1440px 检查 Home、Todos、Shop、Profile、Notes、Finance、Projects：无横向滚动、底部导航不遮挡，桌面侧边栏正常。
- [x] 模拟 access token 过期和并发 401；refresh 失败时清理两个 token 并回登录页。
- [x] 已将浏览器断点和结果记录到验收报告；未执行提交（当前任务禁止自动 commit）。

---

### Task 10: 全量验收和发布门禁

**Files:** 更新 `docs/API.md`、`.env.example` 和 `docs/superpowers/reports/2026-08-04-lifequest-defect-verification.md`（仅在行为/配置确实变化时）。

- [x] 后端运行全量 `pytest -q`，`73 passed` 且无迁移异常。
- [x] 前端运行 `npm run build`，构建成功；chunk warning 作为性能项记录。
- [ ] Docker 运行 `cd D:\codes\LifeQuest; docker compose up -d --build; docker compose ps; docker compose logs --no-color --tail=200 lifequest`，服务必须 healthy。
- [x] 运行 `git status --short`、`git diff --check`；已删除测试覆盖率和临时日志产物，保留用户已有 agent 目录和文档。
- [x] 使用 `superpowers:requesting-code-review` 做人工 diff 审查，使用 `superpowers:verification-before-completion` 重新执行后端专项、全量和前端构建验证。

## 执行顺序

```text
Task 1 -> Task 2 / Task 3 / Task 4 / Task 5
Task 5 -> Task 7
Task 6、Task 8、Task 9 可并行
Task 10 最后执行
```

每个 Task 单独提交并运行专项测试。只有后端全通过、前端构建通过、Docker healthy、MCP 未认证拒绝、跨用户测试通过、响应式检查完成且工作区无敏感文件时，才标记为可发布。
