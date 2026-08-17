from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    ready_for_tribulation: bool = False


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
    ascended: bool = False
    next_stage: StageProgress
    realm: Optional[Dict[str, Any]] = None
    today: List[Dict[str, Any]] = Field(default_factory=list)
    recent_rewards: List[Dict[str, Any]] = Field(default_factory=list)


class WorldNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    node_key: str
    name: str
    description: Optional[str] = None
    required_realm: Optional[str] = None
    sort_order: int
    is_hidden: bool


class WorldResponse(BaseModel):
    nodes: List[WorldNodeResponse]


class SectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sect_key: str
    name: str
    star: int
    kind: str
    task_preference: Optional[str] = None
    entry_realm: Optional[str] = None
    world_node_key: Optional[str] = None
    core_legacy: Optional[str] = None
    joined: bool = False
    visible: bool = True
    can_join: bool = False
    realm_confirmed: bool = False
    messenger_contacted: bool = False
    trial_confirmed: bool = False
    trial_status: str = "awaiting"


class SectMembershipResponse(BaseModel):
    sect_id: UUID
    sect_key: str
    status: str


class TechniqueSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    technique_key: str
    name: str
    description: Optional[str] = None
    technique_type: str
    required_realm: Optional[str] = None
    spirit_stone_cost: int
    slot_count: int
    learned: bool = False
    realm_confirmed: bool = True


class TechniqueSlotResponse(BaseModel):
    slot_type: str
    slot_index: int
    technique_id: Optional[UUID] = None


class TechniqueSlotPurchasePreview(BaseModel):
    next_slot_index: int
    price: int
    required_realm: str
    post_purchase_balance: int
    realm_confirmed: bool
    can_purchase: bool


class TechniqueLibraryResponse(BaseModel):
    techniques: List[TechniqueSummary]
    slots: List[TechniqueSlotResponse]
    loadout: Dict[str, Any]
    slot_assignments: Dict[str, List[Optional[UUID]]] = Field(default_factory=dict)
    spirit_stones: int
    next_slot_purchases: Dict[str, TechniqueSlotPurchasePreview]


class TechniqueSlotPurchaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot_type: str


class LoadoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loadout: Dict[str, Any]


class NpcSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sect_id: Optional[UUID] = None
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    is_core: bool
    population_index: Optional[int] = None
    is_generated: bool = False
    cultivation: int = 0
    cultivation_updated_on: Optional[date] = None
    cultivation_locked: bool = False


class NpcMeetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sect_key: str = Field(min_length=1)
    population_index: int = Field(ge=0)


class NpcRelationshipResponse(BaseModel):
    fixed_core: List[NpcSummary]
    recently_met: List[NpcSummary] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)


class TribulationAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pill_count: int = Field(default=0, ge=0)


class TribulationPreview(BaseModel):
    target_realm: str
    base_probability: float
    readiness_score: float
    readiness_breakdown: Dict[str, float]
    readiness_bonus: float
    pill_count: int
    pill_bonus: float
    final_probability: float
    failure_loss_percent: float
    failure_loss: int = 0
    cooldown_until: Optional[datetime] = None
    terminal: bool = False
    available: bool = True


class TribulationResult(BaseModel):
    success: bool
    realm_key: str
    target_realm: str
    cultivation_loss: int
    lost_realm: bool = False
    lost_techniques: bool = False
    log_id: Optional[UUID] = None
    cooldown_until: Optional[datetime] = None
    terminal: bool = False
