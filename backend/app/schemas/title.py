from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TitleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    unlock_condition_type: Optional[str] = None
    unlock_condition_value: Optional[int] = None


class UserTitleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[TitleResponse] = None
    unlocked_at: datetime


class TitleActivateRequest(BaseModel):
    title_id: int
