from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class StageProgress(BaseModel):
    realm_key: str
    minor_stage: int
    cultivation: int
    current_threshold: int
    next_threshold: Optional[int] = None
    remaining: int


class RewardSettlement(BaseModel):
    _already_settled: bool = PrivateAttr(default=False)
    _legacy_level: int = PrivateAttr(default=1)
    _legacy_experience: int = PrivateAttr(default=0)

    cultivation: int
    spirit_stones: int
    merit: int
    aptitude_points: int
    mind_state_delta: int
    contribution: int
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
    realm_label: str
    next_stage: StageProgress
    realm: Optional[Dict[str, Any]] = None
    today: List[Dict[str, Any]] = Field(default_factory=list)
    recent_rewards: List[Dict[str, Any]] = Field(default_factory=list)


class ResourceState(BaseModel):
    """Authoritative mortal resources used by cultivation and tribulation."""

    merit: int = 0
    aptitude_points: int = 0
    mind_state: int = 50
    contribution: int = 0
    tribulation_pills: int = 0

    @property
    def aptitude(self) -> int:
        return self.aptitude_points

    @property
    def pill_inventory(self) -> int:
        return self.tribulation_pills


class SettlementResult(BaseModel):
    amount: int
    remaining_pills: int
    source_key: Optional[str] = None
    already_settled: bool = False
    settlement_id: Optional[UUID] = None

    @property
    def consumed(self) -> int:
        return self.amount


class WorldNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    node_key: str
    name: str
    description: Optional[str] = None
    required_realm: Optional[str] = None
    region_key: str = "mortal"
    required_project_phase: int = 0
    sort_order: int
    is_hidden: bool
    completed: bool = False
    visible: bool = True
    lock_reason: Optional[str] = None


class WorldResponse(BaseModel):
    nodes: List[WorldNodeResponse]


class SectAccessResponse(BaseModel):
    sect_key: str
    status: str
    objectives: Dict[str, Any] = Field(default_factory=dict)
    score: int = 0
    messenger_contacted: bool = False
    trial_confirmed: bool = False
    completed_at: Optional[datetime] = None


class HiddenSectSummary(BaseModel):
    sect_key: str
    name: Optional[str] = None
    star: int
    kind: str = "hidden"
    visible: bool = False
    can_join: bool = False
    lock_reason: Optional[str] = None
    missing_conditions: List[str] = Field(default_factory=list)


class SectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sect_key: str
    name: str
    star: int
    kind: str
    kind_label: str
    task_preference: Optional[str] = None
    task_preference_label: Optional[str] = None
    entry_realm: Optional[str] = None
    entry_realm_label: Optional[str] = None
    world_node_key: Optional[str] = None
    core_legacy: Optional[str] = None
    joined: bool = False
    visible: bool = True
    can_join: bool = False
    realm_confirmed: bool = False
    messenger_contacted: bool = False
    trial_confirmed: bool = False
    trial_status: str = "awaiting"
    lock_reason: Optional[str] = None
    missing_conditions: List[str] = Field(default_factory=list)


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
    technique_type_label: str
    required_realm: Optional[str] = None
    required_realm_label: Optional[str] = None
    spirit_stone_cost: int
    slot_count: int
    effect_config: Dict[str, Any] = Field(default_factory=dict)
    conflict_tags: List[str] = Field(default_factory=list)
    learned: bool = False
    realm_confirmed: bool = True


class LearnedTechniqueResponse(BaseModel):
    id: UUID
    technique_key: str
    learned: bool = True
    learned_at: datetime
    level: int = 1


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


class TrialObjectiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: bool = True


class NpcEventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: UUID
    npc_id: UUID
    event_key: str
    summary: Optional[str] = None
    created_at: datetime


class NpcRelationshipResponse(BaseModel):
    fixed_core: List[NpcSummary]
    recently_met: List[NpcSummary] = Field(default_factory=list)
    events: List[NpcEventSummary] = Field(default_factory=list)


class TribulationAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pill_count: int = Field(default=0, ge=0)


class TribulationPrerequisite(BaseModel):
    key: str
    label: str
    required: Any
    current: Any
    satisfied: bool


class TribulationPreview(BaseModel):
    target_realm: str
    base_probability: float
    readiness_score: float
    readiness_breakdown: Dict[str, float]
    readiness_bonus: float
    pill_count: int
    owned_pills: int = 0
    pill_bonus: float
    final_probability: float
    failure_loss_percent: float
    failure_loss: int = 0
    cooldown_until: Optional[datetime] = None
    terminal: bool = False
    available: bool = True
    lock_reason: Optional[str] = None
    prerequisites: List[TribulationPrerequisite] = Field(default_factory=list)


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
