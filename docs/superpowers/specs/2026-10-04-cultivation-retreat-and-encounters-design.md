# LifeQuest 闭关专注（番茄钟）与奇遇机缘系统设计

**日期：** 2026-10-04  
**当前版本：** `1.14.8`  
**状态：** 概念设计已获准，进入架构设计规格书阶段，尚未进入代码实现

---

## 1. 目标与背景

LifeQuest 目前具有双层产品结构：
- 底层是现实效能系统（待办、习惯、任务排程、项目、财务、笔记）；
- 表层是东方修仙体系（境界、宗门、功法、渡劫、商城与背包）。

然而在现实任务与修仙反馈之间，存在一个关键缺失环节：**缺乏对现实中“深度专注时间（Focus Time）”的正向激励**。现实中的打卡仅记录“做完与否”，缺乏工作与学习过程中的沉浸感；同时，长期机械打卡容易让用户产生疲惫感。

**核心目标：**
1. **构建“闭关专注（Retreat / Focus Mode）”机制**：将现实番茄钟/深度工作时长与修仙修行深度绑定。深度入定时间越长，收获修为、灵石与心境越丰厚；
2. **构建“奇遇机缘（Random Encounter）”系统**：在成功完成闭关专注、达到里程碑或保持连击时，以概率骰子触发动态剧情与随机机缘（修为顿悟、灵丹妙药、限时 Buff、图鉴收集），打破机械打卡的单调感；
3. **保持现实效能与修仙的轻量融合**：允许在入定时绑定具体待办任务或项目，闭关完成后一键结算任务状态；
4. **扩展 MCP 智能生态**：为外部 AI 客户端（Cursor、Claude 等）暴露专注会话与奇遇数据读取与管理工具。

---

## 2. 范围界定

### 2.1 包含范围 (In Scope)

1. **闭关专注会话生命周期管理**：
   - 启动会话、倒计时与心流状态、提前出关（中断）、圆满出关（结算）；
   - 服务端真实有效时间校验，防挂机作弊；
   - 关联现实待办任务（可选项）及出关后的一键任务完成联动。
2. **修行收益计算模型**：
   - 基础时长收益（15 / 25 / 45 / 60 分钟等级与自由时长）；
   - 结合境界等级、心境加成与 Streak 连击倍率的修为与灵石发放；
   - 计入角色修为升级与境界突破体系。
3. **奇遇机缘事件引擎 (Encounter Engine)**：
   - 奇遇事件模板库（凡品、灵品、玄品、仙品四阶）；
   - 综合概率判定公式（基础概率 + 时长加成 + 连击加成）；
   - 奖励结算管线（即时数值、背包道具发放、临时状态 Buff）；
   - “万象机缘录”图鉴收集统计。
4. **前端沉浸体验 (UI/UX)**：
   - 首页 `TodayWorkbench` 与任务卡片快速发起闭关；
   - 深色禅意全屏/弹窗入定界面（新中式水墨呼吸动效、白噪音与提示引言）；
   - 出关结算卡片与水墨卷轴式奇遇揭示动效；
   - 移动端 (Capacitor) 屏幕常亮与振动反馈支持。
5. **MCP 工具扩展**：
   - `start_cultivation_retreat`、`complete_cultivation_retreat`、`get_cultivation_retreat_status`、`list_encounters_catalog`。
6. **自动化回归与安全测试**：
   - 用户隔离、多并发会话防重、时间作弊拦截、事务原子性与奖励结算测试。

### 2.2 不包含范围 (Out of Scope)

- 联网多人组队双修或宗门联机闭关（保留为单人纯净体验）。
- 复杂的外部白噪音音源下载库（首期内置极简纯 CSS 呼吸动画与可选预设白噪音音频）。
- 自动化应用黑名单/强制作弊锁屏（优先保证轻量自律，不做侵入式系统级锁屏）。

---

## 3. 业务不变量与核心契约

### 3.1 闭关会话约束 (Retreat Invariants)

1. **单用户单会话不变量**：
   - 同一用户在任意时刻最多只能有一个处于 `active` 状态的闭关会话。
   - 尝试在已有进行中会话时启动新会话，服务端必须拒绝并返回明确的 `409 Conflict` 错误及当前未完结会话信息。
2. **时间真实性不变量**：
   - 闭关收益必须由服务端计算，以服务端记录的 `started_at` 与当前服务器时间 `now()` 为准。
   - 实际流逝时间若小于计划时长的 **80%**，判定为“提前出关（aborted）”，仅发放极微量基础安慰奖励，且**绝对不触发奇遇判定**。
3. **任务关联安全性**：
   - 若关联了 `todo_id`，该任务的 `user_id` 必须严格等于当前请求用户；禁止绑定其他用户的任务。
   - 闭关结束并勾选完成任务时，必须通过标准的 `TodoService.complete_todo` 执行，保证任务打卡历史、积分和日历统计正常触发。

### 3.2 奇遇机缘判定与奖励不变量 (Encounter Invariants)

1. **概率上下限约束**：
   - 基础奇遇概率为 `15%`；
   - 每累计 15 分钟专注增加 `5%` 概率；
   - 连续打卡/闭关天数（Streak）每天增加 `1%` 概率（上限 `10%`）；
   - 单次闭关触发奇遇的最终概率上限锁定为 **60%**，下限为 **10%**。
2. **品质分级与境界门槛**：
   - 凡品（Common）：全境界可用；
   - 灵品（Rare）：练气/筑基及以上；
   - 玄品（Epic）：金丹及以上；
   - 仙品（Legendary）：元婴及以上；
   - 未达到境界要求的奇遇事件不会进入当前判定池。
3. **奖励发放原子性**：
   - 闭关结算、境界修为更新、灵石到账、背包物品掉落必须在同一个数据库事务内完成；若任一步骤异常则全部回滚，防止凭空刷经验或物品。

---

## 4. 数据模型与存储契约

在 `backend/app/models/cultivation_retreat.py`（并在 `backend/app/models/__init__.py` 中导出）定义如下模型：

### 4.1 实体模型

#### 1. `CultivationRetreat`（闭关专注记录）
```python
class CultivationRetreat(Base):
    __tablename__ = "cultivation_retreats"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    todo_id = Column(String(36), ForeignKey("todos.id", ondelete="SET NULL"), nullable=True)

    target_duration = Column(Integer, nullable=False)        # 计划时长 (分钟: 15, 25, 45, 60 等)
    actual_duration = Column(Integer, default=0)            # 实际有效时长 (分钟)
    status = Column(String(20), default="active", nullable=False)  # active, completed, aborted

    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    exp_gained = Column(Integer, default=0, nullable=False)
    coins_gained = Column(Integer, default=0, nullable=False)

    encounter_id = Column(String(50), nullable=True)        # 若触发奇遇，记录事件 ID
    encounter_result = Column(JSON, nullable=True)          # 奇遇详细结算快照 (标题, 剧情, 额外奖励)

    created_at = Column(DateTime, default=get_china_now)
```

#### 2. `EncounterEvent`（奇遇事件库）
```python
class EncounterEvent(Base):
    __tablename__ = "encounter_events"

    id = Column(String(50), primary_key=True)               # 语义化唯一标示，如 enc_epiphany_01
    title = Column(String(100), nullable=False)             # 奇遇标题
    story_text = Column(Text, nullable=False)               # 水墨剧情文案
    rarity = Column(String(20), default="common")           # common, rare, epic, legendary
    min_realm_level = Column(Integer, default=1)            # 所需最低境界序号 (1: 练气, 2: 筑基...)
    
    reward_type = Column(String(30), nullable=False)        # exp, coins, item, buff
    reward_payload = Column(JSON, nullable=False)           # 奖励数据参数配置 (如 {"coins": 100, "item_id": "xxx"})
    weight = Column(Integer, default=100)                   # 权重 (用于同稀有度下轮盘抽奖)
```

#### 3. `UserEncounterRecord`（用户奇遇收集图鉴）
```python
class UserEncounterRecord(Base):
    __tablename__ = "user_encounter_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(50), ForeignKey("encounter_events.id"), nullable=False, index=True)
    
    first_unlocked_at = Column(DateTime, default=get_china_now)
    unlock_count = Column(Integer, default=1)
    last_retreat_id = Column(String(36), nullable=True)
```

---

## 5. 服务层与 API 契约

### 5.1 服务层接口 (`CultivationRetreatService`)

1. `start_retreat(user_id: str, target_duration: int, todo_id: Optional[str] = None) -> CultivationRetreat`
   - 校验当前用户是否存在 `status == 'active'` 的记录；
   - 校验 `todo_id` 归属；
   - 创建新会话并写入当前时间 `started_at`。
2. `complete_retreat(user_id: str, retreat_id: str, mark_todo_complete: bool = False) -> RetreatSummaryResponse`
   - 计算时长 `duration = (now - started_at).total_seconds() / 60`；
   - 满足有效比例时：计算基础修为与灵石，进入奇遇骰子流程；
   - 若命中奇遇：匹配合法候选池按权重抽取，更新 `UserEncounterRecord`，发放奇遇专属奖励；
   - 事务提交并同步角色境界经验。
3. `abort_retreat(user_id: str, retreat_id: str) -> CultivationRetreat`
   - 标记为 `aborted`，记录中断时间，不结算奇遇。
4. `get_active_retreat(user_id: str) -> Optional[CultivationRetreat]`
   - 获取用户当前正在进行中的闭关会话（用于页面刷新后恢复计时状态）。

### 5.2 API 路由表 (`/api/cultivation/retreat`)

| 方法 | 路径 | 鉴权 | 描述 |
|---|---|---|---|
| `POST` | `/api/cultivation/retreat/start` | Bearer Token | 发起闭关专注 |
| `GET` | `/api/cultivation/retreat/active` | Bearer Token | 查询当前进行中的闭关会话 |
| `POST` | `/api/cultivation/retreat/{id}/complete` | Bearer Token | 倒计时结束，圆满出关结算 |
| `POST` | `/api/cultivation/retreat/{id}/abort` | Bearer Token | 中途放弃闭关 |
| `GET` | `/api/cultivation/retreat/history` | Bearer Token | 获取专注记录与历史统计 |
| `GET` | `/api/cultivation/encounters/catalog` | Bearer Token | 获取奇遇图鉴收集进度 |

---

## 6. 前端架构与交互设计 (UI/UX)

### 6.1 组件划分

```
frontend/src/
  ├── components/
  │   └── retreat/
  │       ├── CultivationRetreatModal.vue    # 核心入定专注模态框（含全屏切换）
  │       ├── RetreatCountdownRing.vue      # 水墨呼吸光晕圆环计时器
  │       ├── EncounterScrollDialog.vue     # 水墨卷轴奇遇揭示弹窗
  │       └── EncounterCatalogDrawer.vue    # 万象机缘录图鉴收集抽屉
  ├── composables/
  │   └── useCultivationRetreat.js          # 会话状态机、定时器、背景保活与事件总线
  └── services/
      └── cultivationRetreat.js             # API 通信层
```

### 6.2 交互规范与视觉设计

1. **水墨禅意倒计时 (`RetreatCountdownRing.vue`)**：
   - 核心色盘：玄黑背景 (`#0b0d10`)、玉石青 (`#10b981` / `#059669`)、古法琥珀金 (`#f59e0b` / `#d97706`)、素宣白 (`#f8fafc`)；
   - 环形进度条伴随 4 秒周期的微弱呼吸晕影动效（阴阳流转）；
   - 中央大字展示剩余时间（如 `24:59`），下方呈现当前专注任务标签与道家警句。
2. **移动端适配与保活 (Capacitor)**：
   - 进入全屏专注时，通过 Capacitor KeepAwake 插件请求常亮屏幕；
   - 退出或结算时恢复系统息屏设置。
3. **奇遇卷轴揭示 (`EncounterScrollDialog.vue`)**：
   - 结算时若命中奇遇，主界面变暗，自上而下展开水墨画卷轴动效；
   - 浮现印章品质标签（【灵品·丹道机缘】/【玄品·残篇顿悟】），呈现小篆文字与精美图标；
   - 提供“收入囊中 / 载入道典”动作按钮。

---

## 7. MCP 工具集成设计

在 `backend/mcp_server.py` 补充如下工具：

1. `start_focus_session(target_duration: int, todo_id: Optional[str] = None)`
   - 允许外部 AI 助手在辅助用户工作时直接开启闭关倒计时。
2. `get_active_focus_session()`
   - 允许 AI 查询用户是否正在入定闭关中，以及当前进度。
3. `complete_focus_session(retreat_id: str, mark_todo_complete: bool = False)`
   - 允许用户在对话中告知 AI“工作完成了”，由 AI 代为结算并告知获得了什么奇遇。
4. `get_encounters_codex()`
   - 查询用户已收集的奇遇图鉴列表与未解锁概况。

---

## 8. 验收标准与测试矩阵

### 8.1 单元与集成测试 (Backend Pytest)

- **`test_retreat_lifecycle.py`**：
  - 测试正常开启、计时与圆满完成流程；
  - 测试重复开启 `409` 冲突校验；
  - 测试提前中断与未满 80% 时长惩罚机制；
  - 测试关联任务自动完成与非本人任务跨权拒绝；
- **`test_encounter_engine.py`**：
  - 测试各时长与连击天数下的概率分布；
  - 测试境界过滤门槛（低境界无法触发高境界奇遇）；
  - 测试奖励事务回滚安全性。

### 8.2 前端测试 (Node Test)

- **`cultivation-retreat.test.mjs`**：
  - 测试计时器状态转换（idle -> running -> paused -> completed/aborted）；
  - 测试页面刷新时 active 会话自动恢复恢复逻辑；
  - 测试奇遇弹窗数据注入与关闭后事件冒泡。

---

## 9. 演进下一步

本规范经审批后，将调用 `writing-plans` 技能生成详细的任务清单实施计划（`docs/superpowers/plans/2026-10-04-cultivation-retreat-and-encounters.md`），划分出前后端、测试及 MCP 的渐进式交付批次。
