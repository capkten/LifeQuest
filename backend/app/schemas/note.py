from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotebookBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class NotebookCreate(NotebookBase):
    pass


class NotebookResponse(NotebookBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime


class FolderBase(BaseModel):
    name: str
    parent_id: Optional[UUID] = None


class FolderCreate(FolderBase):
    notebook_id: UUID


class FolderResponse(FolderBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    path: Optional[str] = None
    created_at: datetime


class NoteBase(BaseModel):
    title: str
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: bool = False


class NoteCreate(NoteBase):
    folder_id: UUID
    content: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: Optional[bool] = None
    content: Optional[str] = None


class NoteResponse(NoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    folder_id: UUID
    file_path: Optional[str] = None
    word_count: int
    created_at: datetime
    updated_at: datetime
