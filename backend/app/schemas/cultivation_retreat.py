from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    target_duration: int
    actual_duration: int
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    exp_gained: int
    coins_gained: int
    encounter_id: Optional[str] = None
    encounter_result: Optional[Dict[str, Any]] = None
    created_at: datetime


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
