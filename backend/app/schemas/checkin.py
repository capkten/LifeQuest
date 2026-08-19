from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.cultivation import RewardSettlement


class CheckinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    checkin_date: date
    streak: int
    created_at: datetime
    reward_coins: int
    reward_exp: int
    cultivation_reward: Optional[RewardSettlement] = None


class CheckinStatusResponse(BaseModel):
    checked_in: bool
    streak: int
    reward_coins: int
    reward_exp: int
