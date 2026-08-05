# backend/app/schemas/note.py
from datetime import datetime
from typing import Optional, List
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


class NoteDetailResponse(NodeResponse):
    content: Optional[str] = None


def node_to_response(node) -> NodeResponse:
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
        last_opened_at=node.last_opened_at,
        notebook_name=getattr(notebook, "name", None),
    )


class TreeResponse(BaseModel):
    id: UUID
    name: str
    type: str
    parent_id: Optional[UUID] = None
    children: List["TreeResponse"] = []


TreeResponse.model_rebuild()
