from uuid import uuid4

import pytest

import mcp_server
from app.models.note import Notebook
from app.models.note_node import NoteNode
from app.models.user import User
from app.schemas.note import NotebookCreate, NoteCreate
from app.services.note import NoteService


@pytest.fixture
def mcp_notes_db(db_session, monkeypatch):
    from app.database import Base

    Base.metadata.create_all(bind=db_session.bind)
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(mcp_server, "_db_initialized", True)
    user = User(
        username=f"mcp-notes-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    token = mcp_server._auth_user_id.set(user.id)
    try:
        yield db_session, user
    finally:
        mcp_server._auth_user_id.reset(token)
        db_session.rollback()
        Base.metadata.drop_all(bind=db_session.bind)


def test_mcp_can_manage_notebook_tree_and_note_lifecycle(mcp_notes_db):
    db, user = mcp_notes_db

    created_notebook = mcp_server.create_notebook(
        "AI Notes", description="MCP notebook", icon="book"
    )
    notebook_id = created_notebook["id"]
    assert [item["id"] for item in mcp_server.list_notebooks()] == [notebook_id]

    folder = mcp_server.create_folder(notebook_id, "Projects")
    note = mcp_server.create_note(
        notebook_id,
        "Roadmap",
        content="# Roadmap",
        parent_id=folder["id"],
        tags="work, planning",
    )
    assert note["content"] == "# Roadmap"
    assert note["path"] == "/Projects/Roadmap.md"

    children = mcp_server.list_note_children(notebook_id, folder["id"])
    assert [child["id"] for child in children] == [note["id"]]
    tree = mcp_server.get_notebook_tree(notebook_id)
    assert tree[0]["children"][0]["id"] == note["id"]

    updated = mcp_server.update_note(note["id"], content="# Updated", is_pinned=True)
    assert updated["content"] == "# Updated"
    assert updated["is_pinned"] is True

    renamed = mcp_server.rename_or_move_node(note["id"], name="Plan")
    assert renamed["name"] == "Plan"
    opened = mcp_server.mark_note_opened(note["id"])
    assert opened["last_opened_at"] is not None
    assert mcp_server.list_recent_notes(limit=1)[0]["id"] == note["id"]
    assert mcp_server.discover_notes(pinned=True)[0]["id"] == note["id"]
    assert mcp_server.search_notes("Plan")[0]["id"] == note["id"]

    moved_root = mcp_server.rename_or_move_node(note["id"], move_to_root=True)
    assert moved_root["parent_id"] is None
    assert moved_root["path"] == "/Plan.md"
    assert mcp_server.delete_node(folder["id"])["status"] == "ok"
    assert mcp_server.get_notebook_tree(notebook_id)[0]["id"] == note["id"]
    assert mcp_server.delete_notebook(notebook_id)["status"] == "ok"
    assert mcp_server.list_notebooks() == []


def test_mcp_note_tools_reject_other_users_resources(mcp_notes_db):
    db, owner = mcp_notes_db
    service = NoteService(db)
    notebook = service.create_notebook(owner.id, NotebookCreate(name="Private"))
    note = service.create_note(
        notebook.id, owner.id, NoteCreate(title="Secret", content="hidden")
    )
    other_user = User(
        username=f"other-{uuid4().hex[:8]}",
        email=f"other-{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db.add(other_user)
    db.commit()
    mcp_server._auth_user_id.set(other_user.id)

    with pytest.raises(ValueError, match="not found"):
        mcp_server.get_note(str(note.id))
    with pytest.raises(ValueError, match="not found"):
        mcp_server.get_notebook_tree(str(notebook.id))
