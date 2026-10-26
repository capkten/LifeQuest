"""Notebook metadata and membership tools, enforcing existing service permissions."""
from typing import Literal, Optional
from uuid import UUID

from app.schemas.note import NotebookMemberCreate, NotebookMemberUpdate, NotebookUpdate
from app.services.note import NoteService


def register(mcp, resolve_user_id, serialize, session_factory):
    @mcp.tool()
    def update_notebook(notebook_id: str, name: Optional[str] = None,
                        description: Optional[str] = None, icon: Optional[str] = None,
                        clear_description: bool = False, clear_icon: bool = False) -> dict:
        """Update notebook metadata as owner; explicit clear flags erase optional fields."""
        with session_factory() as db:
            user_id = resolve_user_id(db)
            service = NoteService(db)
            if (clear_description and description is not None) or (clear_icon and icon is not None):
                raise ValueError("Cannot set and clear the same field")
            values = {key: value for key, value in
                      {"name": name, "description": description, "icon": icon}.items()
                      if value is not None}
            if clear_description:
                values["description"] = None
            if clear_icon:
                values["icon"] = None
            payload = NotebookUpdate(**values)
            return serialize(service.update_notebook(UUID(notebook_id), user_id, payload))

    @mcp.tool()
    def list_notebook_members(notebook_id: str) -> list[dict]:
        """List public member profiles for a notebook accessible to the current user."""
        with session_factory() as db:
            user_id = resolve_user_id(db)
            return serialize(NoteService(db).get_notebook_members(UUID(notebook_id), user_id))

    @mcp.tool()
    def add_notebook_member(notebook_id: str, username_or_email: str,
                            role: Literal["editor", "viewer"] = "editor") -> dict:
        """As notebook owner, grant an existing user editor or viewer access."""
        payload = NotebookMemberCreate(username_or_email=username_or_email, role=role)
        with session_factory() as db:
            user_id = resolve_user_id(db)
            return serialize(NoteService(db).add_notebook_member(
                UUID(notebook_id), user_id, payload.username_or_email, payload.role))

    @mcp.tool()
    def update_notebook_member(notebook_id: str, member_user_id: str,
                               role: Literal["editor", "viewer"]) -> dict:
        """As notebook owner, change a member role using the member's user_id."""
        payload = NotebookMemberUpdate(role=role)
        with session_factory() as db:
            user_id = resolve_user_id(db)
            return serialize(NoteService(db).update_notebook_member(
                UUID(notebook_id), user_id, UUID(member_user_id), payload.role))

    @mcp.tool()
    def remove_notebook_member(notebook_id: str, member_user_id: str) -> dict:
        """As notebook owner, revoke a member's access using their user_id."""
        with session_factory() as db:
            user_id = resolve_user_id(db)
            NoteService(db).remove_notebook_member(UUID(notebook_id), user_id, UUID(member_user_id))
            return {"status": "ok"}
