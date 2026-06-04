from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    checkin_date: date
    streak: int
    created_at: datetime


class CheckinStatusResponse(BaseModel):
    checked_in: bool
    streak: int
    reward_coins: int
    reward_exp: int
