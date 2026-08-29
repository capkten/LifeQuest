# backend/app/schemas/note.py
from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Notebook schemas (unchanged) ---

class NotebookBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class NotebookCreate(NotebookBase):
    pass


class NotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class NotebookResponse(NotebookBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    role: str = "owner"
    is_owner: bool = True
    member_count: int = 1


class NotebookMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: str
    email: str
    role: str
    status: str
    created_at: datetime


class NotebookMemberCreate(BaseModel):
    username_or_email: str
    role: Literal["editor", "viewer"] = "editor"


class NotebookMemberUpdate(BaseModel):
    role: Literal["editor", "viewer"]


class CollaborationTicketResponse(BaseModel):
    ticket: str
    expires_in: int
    can_edit: bool = True


# --- NoteNode schemas ---

class FolderCreate(BaseModel):
    parent_id: Optional[UUID] = None
    name: str


class NoteCreate(BaseModel):
    parent_id: Optional[UUID] = None
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[UUID] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: Optional[bool] = None
    base_revision: Optional[int] = None


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    parent_id: Optional[UUID] = None
    type: str
    name: str
    path: str
    content_path: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: bool = False
    word_count: int = 0
    created_at: datetime
    updated_at: datetime
    last_opened_at: Optional[datetime] = None
    notebook_name: Optional[str] = None
    content_revision: int = 1
    updated_by: Optional[UUID] = None
    permission_role: str = "owner"
    can_edit: bool = True


class NoteDetailResponse(NodeResponse):
    content: Optional[str] = None


def node_to_response(node, permission_role: str = "owner") -> NodeResponse:
    """Map a NoteNode ORM object to a response with explicit notebook metadata."""
    notebook = getattr(node, "notebook", None)
    return NodeResponse(
        id=node.id,
        notebook_id=node.notebook_id,
        parent_id=node.parent_id,
        type=node.type,
        name=node.name,
        path=node.path,
        content_path=node.content_path,
        summary=node.summary,
        tags=node.tags,
        is_pinned=node.is_pinned,
        word_count=node.word_count,
        created_at=node.created_at,
        updated_at=node.updated_at,
        last_opened_at=getattr(node, "_viewer_last_opened_at", node.last_opened_at),
        notebook_name=getattr(notebook, "name", None),
        content_revision=getattr(node, "content_revision", 1) or 1,
        updated_by=getattr(node, "updated_by", None),
        permission_role=permission_role,
        can_edit=permission_role in {"owner", "editor"},
    )


class TreeResponse(BaseModel):
    id: UUID
    name: str
    type: str
    parent_id: Optional[UUID] = None
    children: List["TreeResponse"] = []


TreeResponse.model_rebuild()
