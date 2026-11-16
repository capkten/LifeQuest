from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.timezone import as_utc


class BaseRetreatSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RetreatStartRequest(BaseModel):
    target_duration: int = Field(default=25, ge=1, le=240, description="Target duration in minutes")
    todo_id: Optional[UUID] = Field(default=None, description="Optional bound task ID")


class RetreatCompleteRequest(BaseModel):
    mark_todo_complete: bool = Field(default=False, description="Whether to mark the bound task as completed")


class RetreatResponse(BaseRetreatSchema):
    id: UUID
    user_id: UUID
    todo_id: Optional[UUID] = None
    todo_title: Optional[str] = None
    companion_snapshot: Optional[Dict[str, str]] = None
    mark_todo_complete: bool = False
    target_duration: int
    actual_duration: int
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    exp_gained: int
    coins_gained: int
    rule_version: Optional[str] = None
    qi_gained: Optional[int] = None
    settlement_id: Optional[UUID] = None
    settlement_result: Optional[Dict[str, Any]] = None
    return_summary: Optional[Dict[str, Any]] = None
    encounter_id: Optional[str] = None
    encounter_result: Optional[Dict[str, Any]] = None
    created_at: datetime

    @field_validator('started_at', 'ended_at', 'created_at')
    @classmethod
    def utc_timestamps(cls, value):
        return as_utc(value) if value is not None else None


class EncounterCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    story_text: str
    rarity: str
    min_realm_level: int
    reward_type: str
    unlocked: bool = False
    unlock_count: int = 0
    first_unlocked_at: Optional[datetime] = None
