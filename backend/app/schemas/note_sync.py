from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SyncManifestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: UUID
    parent_id: Optional[UUID] = None
    node_type: Literal["folder", "note"]
    name: str
    path: str
    content_revision: Optional[int] = None
    content_hash: Optional[str] = None
    updated_at: datetime


class SyncManifestResponse(BaseModel):
    notebook_id: UUID
    revision: int
    items: List[SyncManifestItem]


class SyncChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    node_id: Optional[UUID] = None
    operation: Literal["create", "update", "move", "delete"]
    node_type: Literal["folder", "note"]
    path: str
    parent_id: Optional[UUID] = None
    content_revision: Optional[int] = None
    content_hash: Optional[str] = None
    created_at: datetime


class SyncChangesResponse(BaseModel):
    notebook_id: UUID
    cursor: int
    changes: List[SyncChangeResponse]
    has_more: bool


class SyncContentRequest(BaseModel):
    node_ids: List[UUID] = Field(default_factory=list, max_length=200)


class SyncContentResponse(BaseModel):
    notebook_id: UUID
    contents: Dict[str, str]


class SyncOperationRequest(BaseModel):
    client_operation_id: str = Field(min_length=1, max_length=160)
    kind: Literal["create_folder", "create_note", "update_note", "move_node", "delete_node"]
    node_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, max_length=200)
    path: Optional[str] = Field(default=None, max_length=1000)
    content: Optional[str] = Field(default=None, max_length=5 * 1024 * 1024)
    summary: Optional[str] = Field(default=None, max_length=5000)
    tags: Optional[str] = Field(default=None, max_length=500)
    base_revision: Optional[int] = Field(default=None, ge=1)
    base_hash: Optional[str] = Field(default=None, min_length=64, max_length=64)
    local_path: Optional[str] = Field(default=None, max_length=1000)


class SyncApplyRequest(BaseModel):
    operations: List[SyncOperationRequest] = Field(default_factory=list, max_length=200)


class SyncApplyResult(BaseModel):
    client_operation_id: str
    status: Literal["applied", "already_applied", "conflict", "rejected"]
    node: Optional[SyncManifestItem] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    conflict_id: Optional[UUID] = None


class SyncApplyResponse(BaseModel):
    notebook_id: UUID
    revision: int
    results: List[SyncApplyResult]


class SyncConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    node_id: Optional[UUID] = None
    local_path: str
    base_hash: Optional[str] = None
    remote_revision: Optional[int] = None
    conflict_artifact_path: Optional[str] = None
    status: str
    resolution: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class SyncConflictResolveRequest(BaseModel):
    resolution: Literal["keep_local", "keep_remote", "merged_content"]
    content: Optional[str] = Field(default=None, max_length=5 * 1024 * 1024)
    base_revision: Optional[int] = Field(default=None, ge=1)


class SyncConflictListResponse(BaseModel):
    notebook_id: UUID
    conflicts: List[SyncConflictResponse]
