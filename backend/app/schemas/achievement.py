from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    condition_type: Optional[str] = None
    condition_value: Optional[int] = None
    coin_reward: int = 0
    exp_reward: int = 0


class UserAchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    achievement_id: UUID
    unlocked_at: datetime
    achievement: Optional[AchievementResponse] = None
