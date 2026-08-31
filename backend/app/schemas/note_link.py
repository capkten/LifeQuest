from typing import Literal
from uuid import UUID

from pydantic import BaseModel


LinkKind = Literal["task", "goal", "project"]


class NoteLinkCreate(BaseModel):
    kind: LinkKind
    target_id: UUID


class TargetNoteLinkCreate(BaseModel):
    note_id: UUID


class NoteLinkSummary(BaseModel):
    kind: Literal["note", "task", "goal", "project"]
    id: UUID
    title: str
    url: str
