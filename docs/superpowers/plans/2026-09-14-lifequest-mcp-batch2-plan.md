# LifeQuest MCP 第二批实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在第一批 MCP Token 鉴权和核心 CRUD 完成后，补齐笔记协作及修炼/仙界查询与动作工具，并保证共享权限、幂等和 JSON 返回边界与现有 API 一致。

**Architecture:** MCP 适配层继续位于 `backend/mcp_server.py`，每个工具解析当前用户、调用现有 `NoteService`、`CultivationService`、`AscensionService` 或 `ImmortalService`，再通过第一批统一序列化器返回。笔记成员权限完全由 `NoteService` 判定，修炼世界内容只读、动作保留现有每日限制和 request key，不新增第二套领域规则或系统内容删除接口。

**Tech Stack:** Python 3、FastAPI、SQLAlchemy、Pydantic、FastMCP 1.9.4、pytest。

**Spec:** `docs/superpowers/specs/2026-09-14-lifequest-mcp-design.md`

## Global Constraints

- 依赖第一批的 `_resolve_user_id(db)`、`_serialize(obj)`、Token/SSE/stdio 鉴权和安全用户序列化；没有有效用户上下文的工具必须拒绝。
- 笔记本所有者才可修改笔记本资料和成员；编辑者可写节点；查看者只能读取；不得在 MCP 层绕过 `NoteService`。
- 修炼、宗门、功法、NPC、渡劫、飞升和仙界活动全部复用现有 service 的资源扣除、每日限制、前置条件和 request key 语义。
- 系统世界、宗门和功法不提供 MCP 删除工具；第二批不新增修炼世界用户自定义 CRUD。
- 所有有副作用动作必须有成功、前置条件失败和重复 request key/重复动作测试；返回值必须可 JSON 序列化且不包含密码或 Token。
- 第一批先写失败测试，再写最小实现；每个任务目标测试通过后单独提交。
- 任何 subagent 只能使用 `gpt-5.6-luna`，不得选择其它模型。
- 保留工作区中与本计划无关的用户改动，只暂存当前任务文件；所有文本文件使用 UTF-8。

## 文件职责

- `backend/mcp_server.py`：笔记本协作与修炼/仙界 MCP 工具。
- `backend/tests/test_mcp_notes.py`：笔记成员和成员权限回归。
- `backend/tests/test_mcp_cultivation.py`：修炼、宗门、功法、NPC、渡劫和仙界 MCP 回归。
- `backend/tests/test_mcp_auth.py`：全工具注册和敏感字段序列化回归。

### 测试 fixture 约定

- `mcp_notes_db` 沿用现有 fixture，创建全部表和 owner，临时绑定 `mcp_server.SessionLocal` 与 `_auth_user_id`，yield `(db, owner)`，结束时恢复上下文并清理表。
- `mcp_cultivation_db` 创建全部表、测试用户、foundation 境界 profile 并 seed 修炼世界，临时绑定 `mcp_server.SessionLocal` 与 `_auth_user_id`，yield `(db, user)`；它不创建 `ImmortalProfile`，因此可以先验证飞升前拒绝，再由测试显式创建仙界 profile。
- 需要切换成员身份的测试直接通过 `_auth_user_id.set(user_id)` 完成，并由 fixture 在结束时恢复原 token；不通过客户端传入用户 ID。

---

### Task 1: 补齐笔记本资料和成员协作 MCP 工具

**Files:**

- Modify: `backend/mcp_server.py`
- Modify: `backend/tests/test_mcp_notes.py`

**Interfaces:**

- `update_notebook(notebook_id, name=None, description=None, icon=None)` 只允许所有者修改资料。
- `list_notebook_members(notebook_id)` 允许当前有访问权限的成员查看成员元数据。
- `add_notebook_member(notebook_id, username_or_email, role="editor")`、`update_notebook_member(notebook_id, user_id, role)`、`remove_notebook_member(notebook_id, user_id)` 只允许所有者执行。
- 成员返回沿用 `NoteService.get_notebook_members` 的 `id/user_id/username/email/role/status/created_at`，不返回用户密码、Token 或内部 ORM 对象。

- [ ] **Step 1: 写失败测试覆盖成员角色**

~~~python
import pytest
import mcp_server
from app.models.user import User


def make_user(db, username):
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="unused",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_context(user_id):
    mcp_server._auth_user_id.set(user_id)


def test_mcp_notebook_members_enforce_owner_editor_and_viewer_roles(mcp_notes_db):
    db, owner = mcp_notes_db
    notebook = mcp_server.create_notebook("Shared")
    editor = make_user(db, "mcp-editor")
    viewer = make_user(db, "mcp-viewer")

    added_editor = mcp_server.add_notebook_member(notebook["id"], editor.username, "editor")
    added_viewer = mcp_server.add_notebook_member(notebook["id"], viewer.username, "viewer")
    members = mcp_server.list_notebook_members(notebook["id"])
    assert {member["user_id"] for member in members} == {str(owner.id), str(editor.id), str(viewer.id)}

    set_context(editor.id)
    with pytest.raises(ValueError, match="Not authorized"):
        mcp_server.update_notebook_member(notebook["id"], str(viewer.id), "editor")
    note = mcp_server.create_note(notebook["id"], "Editor note", content="ok")
    assert note["name"] == "Editor note"

    set_context(viewer.id)
    with pytest.raises(ValueError, match="Not authorized"):
        mcp_server.create_folder(notebook["id"], "Viewer cannot write")
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_notes.py -q`

预期：成员工具尚未注册；现有笔记工具测试仍保持通过。

- [ ] **Step 3: 增加 notebook update 和成员工具**

导入 `NotebookUpdate`。`update_notebook` 先通过 `NoteService.get_notebook_access` 获取 access，再要求 `access["is_owner"]`，将非空字段传给 `svc.notebook_repo.update`，返回带角色和成员数量的稳定字典。

`list_notebook_members` 先 `require_notebook_access(notebook_id, uid)`，再调用 `get_notebook_members`；新增、修改、移除分别直接调用 `add_notebook_member(notebook_id, uid, identifier, role)`、`update_notebook_member(notebook_id, uid, target_user_id, role)` 和 `remove_notebook_member(notebook_id, uid, target_user_id)`。因为现有 service 的 `target_id` 是 `NotebookMember.user_id`，MCP 参数命名为 `user_id`，避免把 membership row ID 误传进去。

- [ ] **Step 4: 修正已有笔记工具的成员读取/写入边界**

保留 `verify_notebook_ownership` 的兼容名称但将读取操作允许 active member；文件夹、笔记、节点更新和删除继续经过 `_require_notebook_write`/`_require_node_write`，查看者只能读取树和笔记正文。删除 notebook 仍使用 `verify_notebook_owner`，成员不能删除共享笔记本。

- [ ] **Step 5: 增加交互和跨用户测试并运行**

覆盖 owner 修改名称、editor 修改笔记正文、viewer 读取正文但无法创建/更新/删除、owner 修改成员角色、owner 移除成员、被移除成员无法继续读取。成员列表只包含公开用户字段。

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_notes.py tests/test_note_sharing.py -q`

- [ ] **Step 6: 提交本任务**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_notes.py tests/test_note_sharing.py -q && git diff --check`

提交：`git add backend/mcp_server.py backend/tests/test_mcp_notes.py && git commit -m "feat(mcp): expose notebook collaboration tools"`

### Task 2: 暴露修炼总览、世界、宗门、试炼和功法 MCP 工具

**Files:**

- Modify: `backend/mcp_server.py`
- Create: `backend/tests/test_mcp_cultivation.py`

**Interfaces:**

- `get_cultivation_overview()` -> `CultivationOverview` JSON。
- `get_cultivation_world()` -> `WorldResponse` JSON。
- `list_sects(star=None, kind=None, task_preference=None)` -> `list[SectSummary]` JSON。
- `get_sect_access(sect_key)`、`evaluate_hidden_sects()` -> 现有 access/hidden schema JSON。
- `contact_sect_messenger(sect_key)`、`update_trial_objective(sect_key, objective_key, completed=True)`、`complete_sect_trial(sect_key)`、`join_sect(sect_key)`、`leave_sect()`。
- `complete_world_node(node_key)`。
- `get_techniques()`、`learn_technique(technique_key)`、`purchase_technique_slot(slot_type)`、`update_technique_loadout(loadout: dict)`。

- [ ] **Step 1: 写失败测试覆盖查询、前置条件和幂等**

~~~python
def test_mcp_cultivation_queries_and_sect_progression(mcp_cultivation_db):
    overview = mcp_server.get_cultivation_overview()
    assert overview["realm_key"]
    assert mcp_server.get_cultivation_world()["nodes"]
    sects = mcp_server.list_sects(star=3, kind="normal")
    assert sects

    sect_key = sects[0]["sect_key"]
    access = mcp_server.get_sect_access(sect_key)
    assert access["sect_key"] == sect_key
    with pytest.raises((PermissionError, ValueError)):
        mcp_server.join_sect(sect_key)
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_cultivation.py -q`；预期修炼工具缺失。

- [ ] **Step 3: 添加查询工具和 Pydantic 返回转换**

导入 `CultivationService` 及其已有 schemas。查询工具分别调用 `get_overview(uid)`、`get_world(uid)`、`get_sects(uid, star=..., kind=..., task_preference=...)`、`get_sect_access(uid, sect_key)`、`evaluate_hidden_sects(uid)` 和 `get_techniques(uid)`。所有结果经过第一批 `_serialize`，保证 UUID、datetime、枚举和嵌套模型可编码。

- [ ] **Step 4: 添加宗门、世界和功法动作工具**

动作适配器只解析当前用户并直接调用 service：`contact_sect_messenger`、`update_trial_objective`、`complete_sect_trial`、`join_sect`、`leave_sect`、`complete_world_node`、`learn_technique`、`purchase_slot`、`update_loadout`。loadout 原样交给 service，不在 MCP 层修改 slot assignment。

不吞掉 `PermissionError`、`LookupError`、`ValueError`；MCP 只补充稳定错误上下文，不返回用户密码、Token 或内部堆栈。

- [ ] **Step 5: 增加成功、前置失败和重复动作测试**

使用现有 cultivation 测试的 world seed/profile 辅助准备可执行宗门；测试联系使者、完成 objective、完成试炼、加入宗门的状态推进，第二次调用同一动作的结果与 service 规则一致。对境界不足、未联系使者、未完成试炼、余额不足的学习/入门动作断言失败。

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_cultivation.py tests/test_cultivation.py -q`

- [ ] **Step 6: 提交本任务**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_cultivation.py tests/test_cultivation.py -q && git diff --check`

提交：`git add backend/mcp_server.py backend/tests/test_mcp_cultivation.py && git commit -m "feat(mcp): expose cultivation and sect tools"`

### Task 3: 暴露 NPC、渡劫和飞升/仙界 MCP 工具

**Files:**

- Modify: `backend/mcp_server.py`
- Modify: `backend/tests/test_mcp_cultivation.py`

**Interfaces:**

- `list_npcs()` -> `NpcRelationshipResponse` JSON。
- `meet_npc(sect_key, population_index)` -> `NpcSummary` JSON。
- `get_tribulation_preview(pill_count=0)` -> `TribulationPreview` JSON。
- `attempt_tribulation(pill_count=0)` -> `TribulationResult` JSON。
- `ascend(request_key)` -> `AscensionResponse` JSON。
- `get_immortal_overview()` -> `ImmortalOverview` JSON。
- `run_immortal_activity(activity_id, request_key)` -> `ImmortalActivityResult` JSON。
- `advance_immortal_stage(request_key)` -> `ImmortalStageResult` JSON。
- `commission_immortal_official(official_key, request_key)` -> `ImmortalCommissionResult` JSON。

- [ ] **Step 1: 写失败测试覆盖 NPC、渡劫和仙界前置条件**

~~~python
def test_mcp_npc_and_tribulation_tools_keep_server_side_rules(mcp_cultivation_db):
    npcs = mcp_server.list_npcs()
    assert "fixed_core" in npcs
    with pytest.raises((PermissionError, ValueError)):
        mcp_server.meet_npc("sect-1-normal-1", -1)

    preview = mcp_server.get_tribulation_preview(0)
    assert "available" in preview
    if not preview["available"]:
        with pytest.raises((PermissionError, ValueError)):
            mcp_server.attempt_tribulation(0)

def test_mcp_immortal_actions_require_profile_and_replay_request(mcp_cultivation_db):
    from app.models.immortal import ImmortalProfile

    db, user = mcp_cultivation_db
    with pytest.raises(PermissionError, match="IMMORTAL_PROFILE_REQUIRED"):
        mcp_server.get_immortal_overview()
    db.add(ImmortalProfile(user_id=user.id))
    db.commit()
    first = mcp_server.run_immortal_activity("daily-cultivation", "mcp-activity-once")
    repeated = mcp_server.run_immortal_activity("daily-cultivation", "mcp-activity-once")
    assert first == repeated
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_cultivation.py -q`；预期 NPC、渡劫和仙界工具缺失。

- [ ] **Step 3: 添加 NPC 和渡劫适配器**

`list_npcs` 调用 `CultivationService.get_npcs(uid)`；`meet_npc` 调用 `meet_npc(uid, sect_key, population_index)`，人口索引由服务校验为非负整数。`get_tribulation_preview` 只传 `pill_count`，范围限制 0 至 15；`attempt_tribulation` 只传 `pill_count`，不在 MCP 或客户端计算概率、消耗药丸、失败损失或境界。

返回使用 `_serialize`，保留 service 的 `ready_for_tribulation`、lock reason、daily conflict 和资源扣除结果。

- [ ] **Step 4: 添加飞升和仙界适配器**

导入 `AscensionService`、`ImmortalService`。`ascend` 调 `AscensionService(db).ascend(uid, request_key)`；overview 调 `ImmortalService.get_overview(uid)`；activity、stage、official 分别传递 `activity_id/request_key`、`request_key` 和 `official_key/request_key`。调用前只做当前用户解析，不把 user ID 作为工具参数。

- [ ] **Step 5: 验证动作幂等和资源边界**

覆盖 NPC 重复相遇返回同一稳定对象；渡劫同一中国自然日第二次遵守 service 的 daily guard；未达境界/药丸不足/未飞升时返回前置条件错误；飞升、仙界活动、阶段推进和仙官委任使用相同 request key 重试时不重复增加资源，换用户的 request key 不会读取他人记录。

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_cultivation.py tests/test_cultivation.py tests/test_ascension.py tests/test_immortal.py -q`

- [ ] **Step 6: 提交本任务**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_cultivation.py tests/test_cultivation.py tests/test_ascension.py tests/test_immortal.py -q && git diff --check`

提交：`git add backend/mcp_server.py backend/tests/test_mcp_cultivation.py && git commit -m "feat(mcp): expose tribulation and immortal tools"`

### Task 4: 验证全工具注册、JSON 边界和第二批完成条件

**Files:**

- Modify: `backend/tests/test_mcp_auth.py`
- Modify: `backend/tests/test_mcp_cultivation.py`
- Modify: `backend/tests/test_mcp_notes.py`

**Interfaces:**

- MCP tool registry 包含第二批所有工具名，工具参数 schema 能被 FastMCP 1.9.4 注册。
- 任意查询和动作返回值可用 `json.dumps` 编码；公开用户和成员结果不含 `password_hash`、`token`、`token_hash`。

- [ ] **Step 1: 写注册和敏感字段失败测试**

~~~python
def test_mcp_registry_contains_second_batch_tools():
    names = {info.name for info in mcp_server.mcp._tool_manager.list_tools()}
    assert {
        "update_notebook", "list_notebook_members", "add_notebook_member",
        "update_notebook_member", "remove_notebook_member",
        "get_cultivation_overview", "get_cultivation_world", "list_sects",
        "get_techniques", "list_npcs", "get_tribulation_preview",
        "ascend", "get_immortal_overview", "run_immortal_activity",
        "advance_immortal_stage", "commission_immortal_official",
    } <= names
~~~

- [ ] **Step 2: 运行红灯测试**

运行：`cd backend && ./venv/bin/pytest tests/test_mcp_auth.py::test_mcp_registry_contains_second_batch_tools -q`；预期缺失工具名称。

- [ ] **Step 3: 完成 registry 和 JSON 回归**

registry 测试使用 `mcp._tool_manager.list_tools()` 同步元数据接口；代表性成功路径统一通过 `_serialize` 并用 `json.dumps` 断言可编码。对 Pydantic model、UUID、date/datetime、嵌套 list/dict 都不能直接返回 ORM 或未编码对象。

- [ ] **Step 4: 运行专项和全量测试**

依次运行：

~~~bash
cd backend && ./venv/bin/pytest tests/test_mcp_notes.py tests/test_mcp_cultivation.py tests/test_mcp_auth.py -q
cd backend && ./venv/bin/pytest -q
git diff --check
~~~

- [ ] **Step 5: 提交最终测试变更**

确认暂存区只包含三个测试文件后提交：

~~~bash
git add backend/tests/test_mcp_auth.py backend/tests/test_mcp_cultivation.py backend/tests/test_mcp_notes.py
git commit -m "test(mcp): verify collaboration and cultivation tools"
~~~
