# LifeQuest 修仙成长层实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 LifeQuest 待办工作台上实现第一阶段凡界修仙成长闭环，让现实待办结算修为、灵石和修炼日志，并提供修炼总览、散修地图、宗门、功法格子、NPC 关系和渡劫预览。

**Architecture:** 后端新增独立 cultivation 领域，负责境界、资源、地图、宗门、功法、NPC 和渡劫规则；现有待办完成服务通过同一数据库事务调用修炼结算，前端不重算概率或奖励。前端新增 Pinia 修炼 store、按页面职责拆分的 cultivation 组件和页面，继续复用 Vue Router、Element Plus、蓝白工作台样式与移动端导航。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Vue 3、Pinia、Vue Router、Element Plus、Vite、Node test runner。

## Global Constraints

- 保留现有 Vue 3 + Element Plus 工作台，不引入第二套 UI 组件或图标体系。
- 修仙信息作为现有待办、习惯、项目和笔记之上的成长层，首页和待办仍以现实行动为主。
- 继续使用浅色蓝白视觉基线：主色 #0EA5E9，正文 #16324F，正文 DM Sans，标题和数字 Space Grotesk。
- 不使用大面积渐变、发光边框、独立装饰球、星空背景或暗黑 RPG 主题。
- 所有触控目标最小 44px，图标按钮有 aria-label，陌生图标提供 tooltip。
- 颜色不作为唯一状态指示；锁定、风险、成功和失败必须同时有文字、图标或边框。
- 验证视口为 375px、768px、1024px、1440px，页面不得产生横向滚动。
- 渡劫最终概率只能由后端计算，前端只提交使用的丹药数量。
- 渡劫失败只损失当前小境界修为，不降低境界，不删除功法、装备、格子、宗门记录或 NPC 关系。
- 第一期只实现凡界核心 UI；飞升台、仙界地图、仙籍、官署和仙官任务保留接口边界，不添加空页面入口。
- 保留现有 User.level、User.experience 和 User.coins 的兼容读取；新修炼资料建立后作为修仙领域权威来源。
- 新文件使用 UTF-8；代码匹配现有 Python 4 空格和 Vue script setup 风格。

---

## 文件边界

**后端领域与 API**

- Create: backend/app/models/cultivation.py - 用户修炼档案、资源、修炼日志和渡劫尝试。
- Create: backend/app/models/world.py - 世界节点、宗门、宗门成员关系、NPC 和 NPC 事件。
- Create: backend/app/models/technique.py - 功法、功法学习记录、格子和当前配置。
- Create: backend/app/schemas/cultivation.py - 概览、地图、宗门、功法、NPC、渡劫 DTO。
- Create: backend/app/repositories/cultivation.py - 用户隔离查询和领域持久化。
- Create: backend/app/services/cultivation.py - 修为结算、境界、地图、宗门、功法和渡劫规则。
- Create: backend/app/api/cultivation.py - /api/cultivation/* 路由。
- Modify: backend/app/models/__init__.py、backend/app/main.py - 注册模型、router 和种子。
- Modify: backend/app/services/todo.py、backend/app/schemas/todo.py - 接入修炼奖励且保留旧奖励字段。
- Create: backend/tests/test_cultivation.py；Modify: backend/tests/test_todos.py。

**前端状态与页面**

- Create: frontend/src/services/cultivation.js、frontend/src/stores/cultivation.js。
- Create: frontend/src/components/cultivation/CultivationStatusBar.vue、RealmProgress.vue、ResourceSummary.vue、RewardToast.vue、TribulationProbability.vue、TechniqueSlotGrid.vue、MapNode.vue、NpcTimeline.vue。
- Create: frontend/src/views/Cultivation.vue、World.vue、Sects.vue、Techniques.vue、Npcs.vue、Tribulations.vue。
- Modify: frontend/src/router/index.js、frontend/src/components/layout/Sidebar.vue、frontend/src/components/layout/AppLayout.vue、frontend/src/views/Home.vue、frontend/src/views/Todos.vue、frontend/src/styles/stitch-overrides.css。
- Create: frontend/src/views/cultivation-regressions.test.mjs。

---

### Task 1: 建立修炼领域模型、常量和用户档案

**Files:**

- Create: backend/app/models/cultivation.py
- Create: backend/app/models/world.py
- Create: backend/app/models/technique.py
- Modify: backend/app/models/__init__.py、backend/app/main.py
- Test: backend/tests/test_cultivation.py

**Interfaces:**

- CultivationService.ensure_profile(user_id: UUID) -> CultivationProfile。
- CultivationProfile.realm_key、minor_stage、cultivation、spirit_stones、merit、contribution、mind_state、aptitude_points、cultivation_efficiency。
- TribulationAttempt 保存 base_probability、readiness_score、pill_bonus、final_probability、roll、success、cultivation_loss、attempted_at。

- [ ] **Step 1: 写模型注册失败测试**

~~~python
def test_cultivation_tables_are_registered(db_session):
    from app.models.cultivation import CultivationProfile, CultivationLog
    from app.models.technique import TechniqueSlot

    assert CultivationProfile.__tablename__ == "cultivation_profiles"
    assert CultivationLog.__tablename__ == "cultivation_logs"
    assert TechniqueSlot.__tablename__ == "technique_slots"
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_cultivation_tables_are_registered -q

预期：失败，因为新模型模块不存在。

- [ ] **Step 3: 实现最小模型**

使用 UUID 外键关联 users.id，新增 CultivationProfile、CultivationLog、TribulationAttempt、WorldNode、Sect、SectMembership、Npc、NpcEvent、Technique、TechniqueSlot、LearnedTechnique。每张用户数据表都必须有 user_id 或可追溯的用户关系。

~~~python
class CultivationProfile(Base):
    __tablename__ = "cultivation_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    realm_key = Column(String(32), nullable=False, default="qi_refining")
    minor_stage = Column(Integer, nullable=False, default=1)
    cultivation = Column(Integer, nullable=False, default=0)
    spirit_stones = Column(Integer, nullable=False, default=0)
    merit = Column(Integer, nullable=False, default=0)
    contribution = Column(Integer, nullable=False, default=0)
    mind_state = Column(Integer, nullable=False, default=50)
    aptitude_points = Column(Integer, nullable=False, default=0)
    cultivation_efficiency = Column(Float, nullable=False, default=1.0)
~~~

- [ ] **Step 4: 注册模型并运行测试**

在 backend/app/models/__init__.py 导入三个新模块；执行 pytest tests/test_cultivation.py -q，预期模型注册和内存数据库建表通过。

- [ ] **Step 5: 提交**

~~~bash
git add backend/app/models backend/app/main.py backend/tests/test_cultivation.py
git commit -m "feat(cultivation): add cultivation domain models"
~~~

### Task 2: 实现修为、资源和境界计算服务

**Files:**

- Create: backend/app/schemas/cultivation.py
- Create: backend/app/repositories/cultivation.py
- Create: backend/app/services/cultivation.py
- Modify: backend/app/services/todo.py
- Test: backend/tests/test_cultivation.py、backend/tests/test_todos.py

**Interfaces:**

- CultivationService.get_overview(user_id: UUID) -> CultivationOverview。
- CultivationService.settle_todo_reward(user_id: UUID, source: str, base_exp: int, difficulty: str, quality: float = 1.0) -> RewardSettlement。
- CultivationService.get_next_stage(realm_key: str, minor_stage: int, cultivation: int) -> StageProgress。
- RewardSettlement 返回 cultivation、spirit_stones、merit、efficiency、log_id 和 legacy_exp。

- [ ] **Step 1: 写境界和奖励失败测试**

~~~python
def test_reward_uses_difficulty_and_never_writes_negative_resources(db_session, user):
    service = CultivationService(db_session)
    result = service.settle_todo_reward(user.id, "task", 25, "hard", quality=0.8)

    assert result.cultivation == 28
    assert result.spirit_stones == 16
    assert result.cultivation >= 0

def test_stage_progress_reports_next_threshold(db_session, user):
    service = CultivationService(db_session)
    service.ensure_profile(user.id)
    progress = service.get_next_stage("qi_refining", 1, 128)

    assert progress.current_threshold == 0
    assert progress.next_threshold == 180
    assert progress.remaining == 52
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q

预期：失败，因为 service 和 DTO 尚未定义。

- [ ] **Step 3: 实现确定性的结算服务**

按世界规格使用 修为奖励 = floor(基础值 × 难度系数 × 重要性系数 × 修炼效率 × 完成质量)。第一阶段难度系数为 easy 0.8、medium 1.0、hard 1.4，普通任务灵石比例为 0.6，使用 max(1, floor(cultivation * 0.6)) 计算灵石。结算在当前 session 中写入 profile 和 log，并同步更新旧 User.experience、User.coins；不在 service 中调用随机数。

~~~python
def settle_todo_reward(self, user_id, source, base_exp, difficulty, quality=1.0):
    profile = self.ensure_profile(user_id)
    factors = {"easy": 0.8, "medium": 1.0, "hard": 1.4}
    cultivation = max(0, math.floor(
        base_exp * factors[difficulty] * profile.cultivation_efficiency * quality
    ))
    stones = max(1, math.floor(cultivation * 0.6))
    profile.cultivation += cultivation
    profile.spirit_stones += stones
    log = CultivationLog(
        user_id=user_id,
        source=source,
        cultivation_delta=cultivation,
        spirit_stones_delta=stones,
    )
    self.db.add(log)
    self.user_repo._update_experience_no_commit(user, cultivation)
    self.user_repo._update_coins_no_commit(user, stones)
    self.db.flush()
    return RewardSettlement(
        cultivation=cultivation,
        spirit_stones=stones,
        merit=0,
        efficiency=profile.cultivation_efficiency,
        log_id=log.id,
        legacy_exp=cultivation,
    )
~~~

- [ ] **Step 4: 接入待办完成事务并运行回归测试**

在 TodoService._update_rewards 中调用 settle_todo_reward，保留现有 coin transaction 和 achievement 检查；同一次 completion 不得重复生成 CultivationLog。执行 pytest tests/test_cultivation.py tests/test_todos.py -q，预期通过。

- [ ] **Step 5: 提交**

~~~bash
git add backend/app/schemas/cultivation.py backend/app/repositories/cultivation.py backend/app/services/cultivation.py backend/app/services/todo.py backend/tests/test_cultivation.py backend/tests/test_todos.py
git commit -m "feat(cultivation): settle todo rewards into cultivation"
~~~

### Task 3: 暴露修炼概览、地图、宗门、功法、NPC 和渡劫 API

**Files:**

- Create: backend/app/api/cultivation.py
- Modify: backend/app/main.py
- Test: backend/tests/test_cultivation.py

**Interfaces:**

- GET /api/cultivation/overview -> CultivationOverview。
- GET /api/cultivation/world -> WorldResponse。
- GET /api/cultivation/sects?star=&kind= -> list[SectSummary]。
- POST /api/cultivation/sects/{sect_id}/join、POST /api/cultivation/sects/leave。
- GET /api/cultivation/techniques -> TechniqueLibraryResponse。
- POST /api/cultivation/technique-slots/purchase、PUT /api/cultivation/loadout。
- GET /api/cultivation/npcs -> NpcRelationshipResponse。
- GET /api/cultivation/tribulation/preview -> TribulationPreview。
- POST /api/cultivation/tribulation/attempt -> TribulationResult。

- [ ] **Step 1: 写 API 权限、解锁和幂等测试**

~~~python
def test_overview_creates_profile_for_current_user(client, auth_headers):
    response = client.get("/api/cultivation/overview", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["realm"]["key"] == "qi_refining"

def test_sect_join_is_locked_before_foundation(client, auth_headers):
    response = client.post(
        "/api/cultivation/sects/sect-one/join",
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "sect requires foundation realm"

# Define auth_headers in this test module with the existing register/login
# pattern from backend/tests/test_users.py; the fixture is intentionally local
# because the shared conftest.py does not provide authenticated headers.
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q

预期：路由不存在或返回未定义响应。

- [ ] **Step 3: 实现路由和 DTO**

所有 handler 使用 get_current_user 和 get_db；路由只做参数解析、调用 service 和映射响应。attempt 只接收 { "pill_count": int }，不接收最终概率、骰值、准备度或损失值。未解锁资源返回稳定 409；其他用户资源返回 404，不能泄露对象存在性。

~~~python
@router.post("/tribulation/attempt", response_model=TribulationResult)
def attempt_tribulation(
    payload: TribulationAttemptRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    return CultivationService(db).attempt_tribulation(
        current_user.id,
        payload.pill_count,
    )
~~~

- [ ] **Step 4: 种子 90 个宗门、世界节点和固定 NPC 并运行测试**

启动种子写入 9 星 × 6 普通、3 特殊、1 隐藏的 90 个宗门；每个宗门写入 3 个固定核心 NPC。普通弟子不在启动时批量插入，首次遇见时按用户、区域和弟子槽位稳定生成并永久保存。执行 pytest tests/test_cultivation.py -q，预期 API、种子、权限和幂等测试通过。

- [ ] **Step 5: 提交**

~~~bash
git add backend/app/api/cultivation.py backend/app/main.py backend/tests/test_cultivation.py
git commit -m "feat(cultivation): expose world and progression api"
~~~

### Task 4: 建立前端修炼 service、Pinia store 和共享组件

**Files:**

- Create: frontend/src/services/cultivation.js
- Create: frontend/src/stores/cultivation.js
- Create: frontend/src/components/cultivation/CultivationStatusBar.vue、RealmProgress.vue、ResourceSummary.vue、RewardToast.vue、TribulationProbability.vue、TechniqueSlotGrid.vue、MapNode.vue、NpcTimeline.vue
- Modify: frontend/src/styles/stitch-overrides.css
- Test: frontend/src/views/cultivation-regressions.test.mjs

**Interfaces:**

- cultivationService 提供 getOverview、getWorld、getSects、joinSect、leaveSect、getTechniques、purchaseSlot、updateLoadout、getNpcs、getTribulationPreview、attemptTribulation。
- useCultivationStore 暴露 overview、loading、error、loadOverview、refresh、applySettlement。
- TribulationProbability props 为 preview，emit 为 attempt；状态组件只展示服务器数据。

- [ ] **Step 1: 写前端 API 和无障碍契约测试**

~~~js
test("cultivation service keeps endpoint paths in one module", async () => {
  const source = await readFile(
    new URL("../services/cultivation.js", import.meta.url),
    "utf8",
  );
  assert.match(source, /\/api\/cultivation\/overview/);
  assert.match(source, /\/api\/cultivation\/tribulation\/preview/);
  assert.doesNotMatch(source, /final_probability|roll/);
});
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd frontend; node --test src/views/cultivation-regressions.test.mjs

预期：失败，因为 service 和组件尚未创建。

- [ ] **Step 3: 实现 service 和 store**

复用 frontend/src/services/api.js 的 axios 实例；store 只保存服务器响应和请求状态，不在前端重算境界、奖励或渡劫概率。

~~~js
export const cultivationService = {
  getOverview: () => api.get("/api/cultivation/overview"),
  getWorld: () => api.get("/api/cultivation/world"),
  getSects: (params) => api.get("/api/cultivation/sects", { params }),
  getTribulationPreview: () =>
    api.get("/api/cultivation/tribulation/preview"),
  attemptTribulation: (payload) =>
    api.post("/api/cultivation/tribulation/attempt", payload),
};
~~~

- [ ] **Step 4: 实现稳定尺寸组件并运行测试**

TechniqueSlotGrid 和概率块采用固定 min-height、aspect-ratio 或稳定 grid track；加载时保留同等尺寸骨架；错误状态使用 role=alert 和重试按钮；prefers-reduced-motion 下只移除动画。执行 node --test src/views/cultivation-regressions.test.mjs，预期通过。

- [ ] **Step 5: 提交**

~~~bash
git add frontend/src/services/cultivation.js frontend/src/stores/cultivation.js frontend/src/components/cultivation frontend/src/styles/stitch-overrides.css frontend/src/views/cultivation-regressions.test.mjs
git commit -m "feat(frontend): add cultivation state and shared ui"
~~~

### Task 5: 接入全局导航、首页和待办奖励反馈

**Files:**

- Modify: frontend/src/router/index.js
- Modify: frontend/src/components/layout/Sidebar.vue、frontend/src/components/layout/AppLayout.vue
- Modify: frontend/src/views/Home.vue、frontend/src/views/Todos.vue、frontend/src/composables/useUserStats.js
- Test: frontend/src/views/cultivation-regressions.test.mjs

**Interfaces:**

- Routes: /cultivation、/world、/sects、/techniques、/npcs、/tribulations，均挂在现有认证布局下。
- Todo completion 调用现有完成 endpoint，再调用 cultivationStore.applySettlement(response.cultivation_reward) 或 refresh()。
- cultivation 数据不存在时，sidebar 继续显示 level 和 EXP；成功加载后显示境界、修为进度和灵石。

- [ ] **Step 1: 写导航和旧奖励兼容测试**

~~~js
test("router includes authenticated cultivation routes", async () => {
  const source = await readFile(new URL("../router/index.js", import.meta.url), "utf8");
  assert.match(source, /path: ['\"]cultivation['\"]/);
  assert.match(source, /path: ['\"]tribulations['\"]/);
});

test("todo page keeps the legacy reward fallback", async () => {
  const source = await readFile(new URL("./Todos.vue", import.meta.url), "utf8");
  assert.match(source, /coins_reward/);
  assert.match(source, /exp_reward/);
  assert.match(source, /cultivation|修为/);
});
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd frontend; node --test src/views/cultivation-regressions.test.mjs，预期路由和新文案断言失败。

- [ ] **Step 3: 增加路由和导航**

Sidebar 增加 CULTIVATION 分组；移动端第五入口改为 /cultivation 并显示“修炼”；仙界和仙官在 overview 未返回 ascended=true 时不渲染入口。解锁条件由 API 状态返回。

- [ ] **Step 4: 接入首页和待办 settlement**

首页增加单行 CultivationStatusBar；待办完成后先更新任务，再行内显示 +修为、+灵石并刷新 store，不使用全屏弹窗。请求超过 300ms 才显示 loading；失败 toast 使用 role=alert 和重试。旧 response 没有 cultivation_reward 时继续显示 exp_reward 和 coins_reward。

- [ ] **Step 5: 运行测试并提交**

执行 node --test src/views/cultivation-regressions.test.mjs; npm run build，预期静态测试和生产构建通过，然后提交：

~~~bash
git add frontend/src/router/index.js frontend/src/components/layout frontend/src/views/Home.vue frontend/src/views/Todos.vue frontend/src/composables/useUserStats.js frontend/src/views/cultivation-regressions.test.mjs
git commit -m "feat(frontend): connect cultivation to daily workflow"
~~~

### Task 6: 实现修炼总览、世界地图和 NPC 关系页

**Files:**

- Create: frontend/src/views/Cultivation.vue、frontend/src/views/World.vue、frontend/src/views/Npcs.vue
- Create: frontend/src/components/cultivation/MapNode.vue、frontend/src/components/cultivation/NpcTimeline.vue
- Test: frontend/src/views/cultivation-regressions.test.mjs

**Interfaces:**

- Cultivation.vue 消费 overview.realm、overview.resources、overview.today、overview.recent_rewards。
- World.vue 消费 WorldResponse.nodes，并按选中节点展示详情。
- Npcs.vue 消费 fixed_core、recently_met、events。

- [ ] **Step 1: 写页面状态测试**

~~~js
test("world page has lock and selection semantics", async () => {
  const source = await readFile(new URL("./World.vue", import.meta.url), "utf8");
  assert.match(source, /锁定|解锁条件/);
  assert.match(source, /aria-selected|aria-expanded/);
  assert.match(source, /MapNode/);
});
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd frontend; node --test src/views/cultivation-regressions.test.mjs，预期新页面断言失败。

- [ ] **Step 3: 实现总览页**

桌面采用 minmax(0, 7fr) minmax(280px, 5fr)，移动端改单列；首屏只保留一个主要行动按钮。加载、错误、空状态和锁定状态都使用固定区域；资源颜色遵循语义色但同时显示名称和数值。

- [ ] **Step 4: 实现地图和 NPC 页**

地图桌面左节点右详情，移动端节点列表点击展开详情；节点以文字状态、图标和边框区分当前、可进入、完成和锁定。NPC 页只展示固定核心 NPC、已遇见 NPC 和人口统计；每日修为更新作为时间线事件显示。

- [ ] **Step 5: 运行测试并提交**

执行 node --test src/views/cultivation-regressions.test.mjs; npm run build，预期通过后提交：

~~~bash
git add frontend/src/views/Cultivation.vue frontend/src/views/World.vue frontend/src/views/Npcs.vue frontend/src/components/cultivation/MapNode.vue frontend/src/components/cultivation/NpcTimeline.vue frontend/src/views/cultivation-regressions.test.mjs
git commit -m "feat(frontend): add cultivation overview world and npc pages"
~~~

### Task 7: 实现宗门选择和功法格子配置页

**Files:**

- Create: frontend/src/views/Sects.vue、frontend/src/views/Techniques.vue
- Create: frontend/src/components/cultivation/TechniqueSlotGrid.vue
- Modify: frontend/src/services/cultivation.js
- Test: frontend/src/views/cultivation-regressions.test.mjs

**Interfaces:**

- Sect filters: { star: number | null, kind: normal | special | hidden | null, task_preference: string | null }。
- Sects.vue 只有在服务器确认境界、使者接触和试炼条件后调用 joinSect(sectId)。
- Techniques.vue 调用 purchaseSlot() 和 updateLoadout({ main, auxiliary, mind, body })；成功后用服务器返回的 loadout 替换本地状态。

- [ ] **Step 1: 写筛选、价格和冲突状态测试**

~~~js
test("sect page exposes comparison filters", async () => {
  const source = await readFile(new URL("./Sects.vue", import.meta.url), "utf8");
  assert.match(source, /星级/);
  assert.match(source, /特殊|隐藏/);
  assert.match(source, /比较/);
});

test("technique page shows price and conflict without relying on color", async () => {
  const source = await readFile(new URL("./Techniques.vue", import.meta.url), "utf8");
  assert.match(source, /需要境界/);
  assert.match(source, /灵石/);
  assert.match(source, /冲突/);
  assert.match(source, /TechniqueSlotGrid/);
});
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd frontend; node --test src/views/cultivation-regressions.test.mjs，预期页面文件不存在。

- [ ] **Step 3: 实现宗门比较页**

用紧凑列表显示宗门名称、星级、类型、核心传承、三名固定 NPC、任务偏好、入门境界和试炼条件；特殊宗门使用左色条加传承图标，隐藏宗门只在 API 返回 visible=true 后显示。加入操作显示服务器错误，不在前端直接修改 membership。

- [ ] **Step 4: 实现功法格子页**

固定展示主修、辅修、心法、身法格子；购买确认区展示目标格子、境界限制、灵石价格和购买后余额。格子价格沿用第 2 格 100、第 3 格 300、第 4 格 800、第 5 格 2000、第 6 格 5000、第 7 格 12000，之后由 API 返回递增价格；高级功法占用多格时不改变布局，冲突同时显示图标、文字和边框。

- [ ] **Step 5: 运行测试并提交**

执行 node --test src/views/cultivation-regressions.test.mjs; npm run build，预期通过后提交：

~~~bash
git add frontend/src/views/Sects.vue frontend/src/views/Techniques.vue frontend/src/components/cultivation/TechniqueSlotGrid.vue frontend/src/services/cultivation.js frontend/src/views/cultivation-regressions.test.mjs
git commit -m "feat(frontend): add sect and technique progression ui"
~~~

### Task 8: 实现突破试炼和渡劫透明预览

**Files:**

- Create: frontend/src/views/Tribulations.vue
- Modify: frontend/src/components/cultivation/TribulationProbability.vue、frontend/src/services/cultivation.js、backend/app/services/cultivation.py
- Test: backend/tests/test_cultivation.py、frontend/src/views/cultivation-regressions.test.mjs

**Interfaces:**

- TribulationPreview 必须包含 base_probability、readiness_score、readiness_breakdown、readiness_bonus、pill_count、pill_bonus、final_probability、failure_loss_percent、cooldown_until。
- attemptTribulation({ pill_count }) 返回 success、目标境界、失败损失、结果日志和下一次可尝试时间。

- [ ] **Step 1: 写后端概率和失败损失测试**

~~~python
def test_tribulation_probability_is_clamped_and_public(db_session, user):
    service = CultivationService(db_session)
    preview = service.get_tribulation_preview(user.id)

    assert 20 <= preview.final_probability <= 95
    assert preview.base_probability >= 20
    assert set(preview.readiness_breakdown) == {
        "mind_state", "habit", "task_quality", "trial", "compatibility"
    }

def test_failed_tribulation_keeps_realm_and_techniques(db_session, user, monkeypatch):
    service = CultivationService(db_session)
    service.set_realm(user.id, "foundation", 4, 900)
    monkeypatch.setattr(service, "roll", lambda probability: False)
    result = service.attempt_tribulation(user.id, 0)

    assert result.success is False
    assert result.realm_key == "foundation"
    assert result.lost_realm is False
    assert result.lost_techniques is False
~~~

- [ ] **Step 2: 运行测试确认失败**

运行：cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q，预期概率和失败损失测试失败。

- [ ] **Step 3: 完成后端渡劫规则**

基础概率按目标境界使用世界规格；准备度按五项贡献计算；准备度加成 = round((准备度 - 50) / 5)；渡劫丹每颗 +5 个百分点；最终值 clamp 到 20 至 95。每个用户每天最多一次尝试；成功进入下一大境界初期，失败只扣当前小境界修为且不低于零。

- [ ] **Step 4: 实现前端渡劫页和透明度测试**

按风险到操作顺序展示当前境界、失败损失、五项准备度、基础概率、丹药加成、最终概率和冷却。主操作写“开始渡劫”，提交中禁用并显示 loading；成功、失败和冷却都保留结果。执行 node --test src/views/cultivation-regressions.test.mjs，预期通过。

- [ ] **Step 5: 提交**

~~~bash
git add frontend/src/views/Tribulations.vue frontend/src/components/cultivation/TribulationProbability.vue frontend/src/services/cultivation.js backend/app/services/cultivation.py backend/tests/test_cultivation.py frontend/src/views/cultivation-regressions.test.mjs
git commit -m "feat(cultivation): add transparent tribulation flow"
~~~

### Task 9: 全量验证、响应式检查和实现报告

**Files:**

- Create: docs/superpowers/reports/2026-08-17-lifequest-cultivation-ui-verification.md
- Modify only when verification finds a concrete defect: files from Tasks 1-8

- [ ] **Step 1: 运行后端完整测试**

运行：cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q。预期现有测试和新增 cultivation 测试全部通过；失败时修复具体回归，不跳过测试。

- [ ] **Step 2: 运行前端静态测试和生产构建**

运行：cd frontend; node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/cultivation-regressions.test.mjs; npm run build。预期测试通过、Vite 构建成功；记录已有 bundle warning。

- [ ] **Step 3: 启动前后端并检查四种视口**

运行后端：cd backend; uvicorn app.main:app --reload。另一个终端运行前端：cd frontend; npm run dev -- --host 127.0.0.1。检查 375px、768px、1024px、1440px 下的首页、待办、修炼总览、地图、宗门、功法、NPC 和渡劫页。

检查无横向滚动、底部导航不遮挡内容、状态条不跳动、锁定/错误/空/加载/成功/失败/冷却均可见、键盘 focus 可见、概率和奖励文字不截断。

- [ ] **Step 4: 编写验证报告**

报告记录实际命令、通过数量、四种视口、已知限制和未进入第一阶段的仙界/仙官入口；未手工验证的浏览器行为不得写成已验证。

- [ ] **Step 5: 检查差异并提交**

运行：git diff --check; git status --short。确认 .agents/、.claude/skills/、.codex/ 和 frontend/vite-check.log 不在暂存区后提交：

~~~bash
git add docs/superpowers/reports/2026-08-17-lifequest-cultivation-ui-verification.md
git commit -m "test: verify cultivation progression ui"
~~~

## 验收映射

- 现实待办仍是首页和待办的主要操作，完成后能看到修为和灵石：Tasks 2、5。
- 境界、资源、日志和下一步目标可扫描：Tasks 2、4、6。
- 筑基前散修地图、筑基后多宗门选择、90 个宗门和固定核心 NPC：Tasks 1、3、6、7。
- 功法永久学习、格子购买、境界限制、冲突和退出后的通用效果：Tasks 1、3、7。
- 普通弟子按需生成并永久存在，每日修为按自然日补算：Tasks 1、3、6。
- 渡劫准备度、概率组成、丹药加成、20% 至 95% 限制和失败损失：Tasks 3、8。
- 加载、错误、空、锁定、操作中、成功、失败和冷却状态：Tasks 4、6、7、8、9。
- 仙界和仙官不在第一阶段提前显示，但后端 schema 保留可扩展的 realm/resource 边界：Tasks 1、2、3、9。

## 计划自检

- 已覆盖 UI 规格的视觉基线、导航、首页/待办反馈、总览、地图、宗门、功法、NPC、渡劫、状态、响应式和可访问性要求。
- 已覆盖世界规格的凡界第一阶段数据、结算公式、格子价格、宗门数量、NPC 永久化、每日修为更新和渡劫规则。
- 已完成计划内容审查，所有实现步骤都包含具体文件、接口、命令或验收条件。
- 所有跨任务接口均在前置任务中定义；前端不接收或重算后端私有的骰值和最终概率。
- 第一阶段按任务提交，每个任务都有独立测试命令和预期结果。
