from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StageProgress(BaseModel):
    realm_key: str
    minor_stage: int
    cultivation: int
    current_threshold: int
    next_threshold: Optional[int] = None
    remaining: int


class RewardSettlement(BaseModel):
    cultivation: int
    spirit_stones: int
    merit: int
    efficiency: float
    log_id: UUID
    legacy_exp: int


class CultivationOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    realm_key: str
    minor_stage: int
    cultivation: int
    spirit_stones: int
    merit: int
    contribution: int
    mind_state: int
    aptitude_points: int
    cultivation_efficiency: float
    next_stage: StageProgress
