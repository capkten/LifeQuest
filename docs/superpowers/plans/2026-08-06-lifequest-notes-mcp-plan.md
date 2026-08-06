# LifeQuest Notes MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the complete conventional notes workflow through authenticated LifeQuest MCP tools.

**Architecture:** Extend `backend/mcp_server.py` with thin MCP adapters that resolve the authenticated user, validate ownership, call `NoteService`, and serialize results. Add focused tests in `backend/tests/test_mcp_notes.py`; no schema, database, or frontend changes are needed.

**Tech Stack:** Python 3, FastAPI project services, SQLAlchemy, Pydantic, FastMCP, pytest.

## Global Constraints

- Reuse `NoteService`; MCP adapters must not access note files directly.
- Every tool must call `_resolve_user_id(db)` before accessing user data.
- Keep UUID/date conversion through the existing `_serialize` helper.
- Preserve existing untracked user files and avoid unrelated formatting.
- Read and write text files as UTF-8.

---

### Task 1: Add failing MCP notes workflow tests

**Files:**
- Create: `backend/tests/test_mcp_notes.py`
- Inspect: `backend/tests/conftest.py`, `backend/tests/test_notes.py`, `backend/mcp_server.py`

**Interfaces:**
- Consumes: existing `mcp_server` functions and `NoteService` behavior.
- Produces: regression coverage for notebook listing, tree browsing, CRUD, move, discovery, and ownership.

- [ ] **Step 1: Write tests** for direct MCP functions using the existing test database fixture. Set `_auth_user_id` to a fixture user, create notebooks/notes through `NoteService`, and assert the new tools return expected serialized data.
- [ ] **Step 2: Run the focused tests** with `cd backend; pytest tests/test_mcp_notes.py -q`.
- [ ] **Step 3: Confirm initial failures** identify each missing MCP function rather than service defects.

### Task 2: Implement notebook and directory MCP tools

**Files:**
- Modify: `backend/mcp_server.py` near the existing notes section.
- Test: `backend/tests/test_mcp_notes.py`

**Interfaces:**
- Produces `list_notebooks()`, `create_notebook(name, description=None, icon=None)`, `delete_notebook(notebook_id)`, `get_notebook_tree(notebook_id)`, `list_note_children(notebook_id, parent_id=None)`, and `create_folder(notebook_id, name, parent_id=None)`.

- [ ] **Step 1: Add ownership-aware notebook tools** using `NoteService.get_notebooks`, `create_notebook`, and notebook repository lookup/delete.
- [ ] **Step 2: Add tree/children tools** after validating notebook ownership; build tree using the same nested shape as the REST endpoint.
- [ ] **Step 3: Add folder creation** using `FolderCreate`, returning `_serialize(node)` and preserving service errors.
- [ ] **Step 4: Run `cd backend; pytest tests/test_mcp_notes.py -q`** and verify directory tests pass.

### Task 3: Implement note CRUD and node movement MCP tools

**Files:**
- Modify: `backend/mcp_server.py` near the existing notes section.
- Test: `backend/tests/test_mcp_notes.py`

**Interfaces:**
- Produces `create_note(notebook_id, title, content=None, parent_id=None, summary=None, tags=None)`, `rename_or_move_node(node_id, name=None, parent_id=None)`, and `delete_node(node_id)`.

- [ ] **Step 1: Add `create_note`** with `NoteCreate`, notebook ownership validation, and serialized metadata plus content.
- [ ] **Step 2: Add `rename_or_move_node`** with a sentinel or explicit `move` handling so omitted `parent_id` does not accidentally move a node to root; call `rename_node` and `move_node` in one transaction-compatible flow.
- [ ] **Step 3: Add `delete_node`** after node ownership validation and return `{"status": "ok", "message": "Node deleted"}`.
- [ ] **Step 4: Run focused CRUD and ownership tests** and verify cross-user resources raise the expected error.

### Task 4: Implement note discovery MCP tools and verify the full suite

**Files:**
- Modify: `backend/mcp_server.py`.
- Test: `backend/tests/test_mcp_notes.py`.

**Interfaces:**
- Produces `list_recent_notes(limit=8)`, `discover_notes(sort="last_opened", notebook_id=None, tag=None, pinned=None, updated_after=None, updated_before=None, limit=50)`, and `mark_note_opened(note_id)`.

- [ ] **Step 1: Add recent/discover adapters** with the same limits and sort values as the REST API.
- [ ] **Step 2: Add `mark_note_opened`** with ownership validation and serialized response.
- [ ] **Step 3: Run `cd backend; pytest tests/test_mcp_notes.py -q`**.
- [ ] **Step 4: Run `cd backend; pytest -q`** and address only regressions caused by this change.
- [ ] **Step 5: Inspect `git diff` and commit with `feat(mcp): expose conventional note tools`**.
