from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImmortalOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    realm_key: str
    stage: int
    essence: int
    immortal_stones: int
    regions: list[dict] = Field(default_factory=list)
    officials: list[dict] = Field(default_factory=list)
    activities: list[dict] = Field(default_factory=list)
    stage_goals: list[dict] = Field(default_factory=list)


class AscensionRequest(BaseModel):
    request_key: str = Field(min_length=1, max_length=128)


class AscensionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    request_key: str
    source_key: str
    created_at: datetime


class ImmortalActivityRequest(BaseModel):
    activity_id: str = Field(min_length=1, max_length=64)
    request_key: str = Field(min_length=1, max_length=128)


class ImmortalActivityResult(BaseModel):
    activity_id: str
    request_key: str
    essence_delta: int
    immortal_stones_delta: int
    essence: int
    immortal_stones: int


class ImmortalStageResult(BaseModel):
    stage: int
    advanced: bool
    required_essence: int


class ImmortalCommissionRequest(BaseModel):
    official_key: str = Field(min_length=1, max_length=64)
    request_key: str = Field(min_length=1, max_length=128)


class ImmortalCommissionResult(BaseModel):
    official_key: str
    request_key: str
    essence_delta: int
    immortal_stones_delta: int
    essence: int
    immortal_stones: int
