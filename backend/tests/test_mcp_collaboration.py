from uuid import uuid4

import pytest

from app.database import Base
from app.models.user import User
from app.schemas.note import NotebookCreate
from app.services.note import NoteService
import mcp_server


def test_notebook_metadata_and_member_role_boundaries(db_session):
    from app.mcp.collaboration import register
    Base.metadata.create_all(db_session.bind)
    users = [User(username=uuid4().hex, email=f"{uuid4().hex}@example.com", password_hash="hashed") for _ in range(3)]
    db_session.add_all(users)
    db_session.commit()
    owner, editor, outsider = users
    notebook = NoteService(db_session).create_notebook(owner.id, NotebookCreate(name="Notebook"))
    notebook_id = str(notebook.id)
    owner_id, editor_id, outsider_id = (user.id for user in users)
    editor_name, outsider_name = editor.username, outsider.username
    actor = [owner_id]
    registry = {}
    class Registry:
        def tool(self):
            def add(fn):
                registry[fn.__name__] = fn
                return fn
            return add
    register(Registry(), lambda db: actor[0], mcp_server._serialize, lambda: db_session)
    try:
        assert registry["update_notebook"](notebook_id, name="Updated")["name"] == "Updated"
        with pytest.raises(ValueError, match="Cannot set and clear"):
            registry["update_notebook"](notebook_id, description="new", clear_description=True)
        assert registry["update_notebook"](notebook_id, clear_description=True)["description"] is None
        member = registry["add_notebook_member"](notebook_id, editor_name)
        assert member["role"] == "editor"
        assert "password_hash" not in member
        from app.schemas.note import NotebookUpdate
        from uuid import UUID
        with pytest.raises(PermissionError):
            NoteService(db_session).update_notebook(UUID(notebook_id), editor_id, NotebookUpdate(name="Denied"))
        actor[0] = editor_id
        assert len(registry["list_notebook_members"](notebook_id)) == 2
        for name, args in (("update_notebook", (notebook_id,)), ("add_notebook_member", (notebook_id, outsider_name)), ("update_notebook_member", (notebook_id, str(editor_id), "viewer")), ("remove_notebook_member", (notebook_id, str(editor_id)))):
            with pytest.raises(PermissionError):
                registry[name](*args)
        actor[0] = outsider_id
        with pytest.raises(PermissionError):
            registry["list_notebook_members"](notebook_id)
        actor[0] = owner_id
        assert registry["update_notebook_member"](notebook_id, str(editor_id), "viewer")["role"] == "viewer"
        with pytest.raises(ValueError):
            registry["update_notebook_member"](notebook_id, str(editor_id), "owner")
        assert registry["remove_notebook_member"](notebook_id, str(editor_id)) == {"status": "ok"}
        assert len(registry["list_notebook_members"](notebook_id)) == 1
    finally:
        db_session.rollback()
        Base.metadata.drop_all(db_session.bind)
