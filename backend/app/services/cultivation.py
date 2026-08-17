import math
import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.cultivation import CultivationLog, CultivationProfile, TribulationAttempt
from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
from app.models.world import Npc, NpcEvent, Sect, SectMembership, WorldNode
from app.repositories.cultivation import CultivationRepository
from app.repositories.user import UserRepository
from app.schemas.cultivation import (
    CultivationOverview,
    NpcRelationshipResponse,
    NpcSummary,
    RewardSettlement,
    SectMembershipResponse,
    SectSummary,
    StageProgress,
    TechniqueLibraryResponse,
    TechniqueSlotResponse,
    TechniqueSummary,
    TribulationPreview,
    TribulationResult,
    WorldNodeResponse,
    WorldResponse,
)


REALM_THRESHOLDS = {
    "qi_refining": [100, 110, 120, 130, 145, 160, 180, 205, 235],
    "foundation": [500, 600, 750, 950],
    "golden_core": [1000, 1300, 1700, 2000],
    "nascent_soul": [1500, 2200, 2800, 3500],
    "spirit_transformation": [2500, 3500, 4500, 5500],
    "void_refining": [4500, 6000, 8000, 9500],
    "body_combination": [7000, 9500, 13000, 18000],
    "great_vehicle": [12000, 16000, 22000, 30000],
    "tribulation": [20000, 26000, 35000, 49000],
}

DIFFICULTY_FACTORS = {"easy": 0.8, "medium": 1.0, "hard": 1.35}


class CultivationService:
    def __init__(self, db: Session):
        self.db = db
        self.cultivation_repo = CultivationRepository(db)
        self.user_repo = UserRepository(db)

    def ensure_profile(self, user_id: UUID) -> CultivationProfile:
        profile = self.cultivation_repo.get_by_user(user_id)
        if profile is None:
            profile = self.cultivation_repo.create_default(user_id)
        return profile

    def get_overview(self, user_id: UUID) -> CultivationOverview:
        profile = self.ensure_profile(user_id)
        return CultivationOverview(
            realm_key=profile.realm_key,
            minor_stage=profile.minor_stage,
            cultivation=profile.cultivation,
            spirit_stones=profile.spirit_stones,
            merit=profile.merit,
            contribution=profile.contribution,
            mind_state=profile.mind_state,
            aptitude_points=profile.aptitude_points,
            cultivation_efficiency=profile.cultivation_efficiency,
            next_stage=self.get_next_stage(
                profile.realm_key, profile.minor_stage, profile.cultivation
            ),
            realm={"key": profile.realm_key, "minor_stage": profile.minor_stage},
        )

    @staticmethod
    def seed_world(db: Session):
        nodes = []
        for index in range(1, 10):
            key = f"mortal-domain-{index}"
            node = db.query(WorldNode).filter(WorldNode.node_key == key).first()
            if node is None:
                node = WorldNode(
                    node_key=key,
                    name=f"Mortal Domain {index}",
                    description=f"Cultivation region {index}",
                    required_realm=None if index == 1 else "foundation",
                    sort_order=index,
                    is_hidden=False,
                )
                db.add(node)
            nodes.append(node)
        db.flush()

        kinds = ["normal"] * 6 + ["special"] * 3 + ["hidden"]
        for star in range(1, 10):
            node = nodes[(star - 1) % len(nodes)]
            for ordinal, kind in enumerate(kinds, 1):
                key = f"sect-{star}-{kind}-{ordinal}"
                sect = db.query(Sect).filter(Sect.sect_key == key).first()
                if sect is None:
                    db.add(Sect(
                        sect_key=key,
                        name=f"{star}-Star {kind.title()} Sect {ordinal}",
                        star=star,
                        kind=kind,
                        task_preference=f"discipline-{ordinal}",
                        core_legacy=f"Legacy of the {star}-star sect",
                        entry_realm="foundation",
                        trial_key=f"trial-{star}-{ordinal}",
                        world_node_id=node.id,
                    ))

        techniques = [
            ("steady-breath", "Steady Breath", "mind", "qi_refining"),
            ("stone-channel", "Stone Channel", "body", "foundation"),
            ("golden-intent", "Golden Intent", "main", "golden_core"),
        ]
        for key, name, kind, realm in techniques:
            if not db.query(Technique).filter(Technique.technique_key == key).first():
                db.add(Technique(
                    technique_key=key,
                    name=name,
                    description=f"A {kind} cultivation technique.",
                    technique_type=kind,
                    required_realm=realm,
                    spirit_stone_cost=10,
                    slot_count=1,
                ))
        db.commit()

    def get_world(self, user_id: UUID) -> WorldResponse:
        self.seed_world(self.db)
        self.ensure_profile(user_id)
        nodes = self.db.query(WorldNode).order_by(WorldNode.sort_order).all()
        return WorldResponse(nodes=[WorldNodeResponse.model_validate(node) for node in nodes])

    def get_sects(self, user_id: UUID, star=None, kind=None):
        self.seed_world(self.db)
        membership = self.db.query(SectMembership).filter(
            SectMembership.user_id == user_id, SectMembership.status == "active"
        ).first()
        query = self.db.query(Sect).order_by(Sect.star, Sect.sect_key)
        if star is not None:
            query = query.filter(Sect.star == star)
        if kind is not None:
            query = query.filter(Sect.kind == kind)
        return [SectSummary(
            id=sect.id,
            sect_key=sect.sect_key,
            name=sect.name,
            star=sect.star,
            kind=sect.kind,
            task_preference=sect.task_preference,
            entry_realm=sect.entry_realm,
            world_node_key=self.db.query(WorldNode.node_key).filter(WorldNode.id == sect.world_node_id).scalar(),
            joined=bool(membership and membership.sect_id == sect.id),
        ) for sect in query.all()]

    def join_sect(self, user_id: UUID, sect_key: str) -> SectMembershipResponse:
        profile = self.ensure_profile(user_id)
        if profile.realm_key == "qi_refining":
            raise PermissionError("sect requires foundation realm")
        self.seed_world(self.db)
        sect = self.db.query(Sect).filter(Sect.sect_key == sect_key).first()
        if sect is None:
            try:
                sect = self.db.query(Sect).filter(Sect.id == UUID(sect_key)).first()
            except ValueError:
                sect = None
        if sect is None:
            raise LookupError("sect not found")
        current = self.db.query(SectMembership).filter(
            SectMembership.user_id == user_id, SectMembership.status == "active"
        ).first()
        if current and current.sect_id != sect.id:
            raise ValueError("leave current sect before joining another")
        if current is None:
            current = SectMembership(user_id=user_id, sect_id=sect.id, status="active")
            self.db.add(current)
            self.db.commit()
        return SectMembershipResponse(sect_id=sect.id, sect_key=sect.sect_key, status=current.status)

    def leave_sect(self, user_id: UUID):
        current = self.db.query(SectMembership).filter(
            SectMembership.user_id == user_id, SectMembership.status == "active"
        ).first()
        if current is None:
            return {"status": "none"}
        current.status = "left"
        current.left_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"status": "left"}

    def get_techniques(self, user_id: UUID) -> TechniqueLibraryResponse:
        self.seed_world(self.db)
        self.ensure_profile(user_id)
        learned = {row.technique_id for row in self.db.query(LearnedTechnique).filter(LearnedTechnique.user_id == user_id)}
        techniques = self.db.query(Technique).order_by(Technique.technique_key).all()
        slots = self.db.query(TechniqueSlot).filter(TechniqueSlot.user_id == user_id).order_by(TechniqueSlot.slot_type, TechniqueSlot.slot_index).all()
        loadout = {slot.slot_type: slot.technique_id for slot in slots}
        return TechniqueLibraryResponse(
            techniques=[TechniqueSummary(
                id=t.id, technique_key=t.technique_key, name=t.name,
                description=t.description, technique_type=t.technique_type,
                required_realm=t.required_realm, spirit_stone_cost=t.spirit_stone_cost,
                slot_count=t.slot_count, learned=t.id in learned,
            ) for t in techniques],
            slots=[TechniqueSlotResponse(slot_type=s.slot_type, slot_index=s.slot_index, technique_id=s.technique_id) for s in slots],
            loadout=loadout,
        )

    def purchase_slot(self, user_id: UUID, slot_type: str):
        if slot_type not in {"main", "auxiliary", "mind", "body"}:
            raise ValueError("invalid slot type")
        existing = self.db.query(TechniqueSlot).filter(
            TechniqueSlot.user_id == user_id, TechniqueSlot.slot_type == slot_type
        ).order_by(TechniqueSlot.slot_index).all()
        if not existing:
            self.db.add(TechniqueSlot(user_id=user_id, slot_type=slot_type, slot_index=0))
            self.db.commit()
        return {"slot_type": slot_type, "slot_count": max(1, len(existing))}

    def update_loadout(self, user_id: UUID, loadout):
        for slot_type, technique_id in loadout.items():
            if technique_id is None:
                continue
            slot = self.db.query(TechniqueSlot).filter(
                TechniqueSlot.user_id == user_id, TechniqueSlot.slot_type == slot_type
            ).first()
            technique = self.db.query(Technique).filter(Technique.id == technique_id).first()
            if slot is None or technique is None:
                raise LookupError("technique or slot not found")
            slot.technique_id = technique.id
        self.db.commit()
        return self.get_techniques(user_id)

    def get_npcs(self, user_id: UUID) -> NpcRelationshipResponse:
        self.seed_world(self.db)
        sects = self.db.query(Sect).all()
        for sect in sects:
            for role in ("sect master", "transmission elder", "trial envoy"):
                name = f"{sect.sect_key}-{role.replace(' ', '-') }"
                exists = self.db.query(Npc).filter(
                    Npc.user_id == user_id, Npc.sect_id == sect.id, Npc.role == role, Npc.is_core.is_(True)
                ).first()
                if exists is None:
                    self.db.add(Npc(user_id=user_id, sect_id=sect.id, name=name, role=role, description=f"Core NPC of {sect.name}", is_core=True))
        self.db.commit()
        rows = self.db.query(Npc).filter(Npc.user_id == user_id, Npc.is_core.is_(True)).order_by(Npc.name).all()
        return NpcRelationshipResponse(fixed_core=[NpcSummary.model_validate(row) for row in rows])

    def get_tribulation_preview(self, user_id: UUID, pill_count=0) -> TribulationPreview:
        profile = self.ensure_profile(user_id)
        realm_order = list(REALM_THRESHOLDS)
        index = realm_order.index(profile.realm_key)
        target = realm_order[min(index + 1, len(realm_order) - 1)]
        base = max(20, 90 - index * 10)
        readiness = float(profile.mind_state)
        readiness_bonus = round((readiness - 50) / 5, 2)
        pill_bonus = max(0, pill_count) * 5
        return TribulationPreview(
            target_realm=target,
            base_probability=base,
            readiness_score=readiness,
            readiness_breakdown={"mind_state": readiness, "habit": 0, "task_quality": 0, "trial": 0, "compatibility": 0},
            readiness_bonus=readiness_bonus,
            pill_count=max(0, pill_count),
            pill_bonus=pill_bonus,
            final_probability=max(20, min(95, base + readiness_bonus + pill_bonus)),
            failure_loss_percent=10,
        )

    def attempt_tribulation(self, user_id: UUID, pill_count: int) -> TribulationResult:
        preview = self.get_tribulation_preview(user_id, pill_count)
        profile = self.ensure_profile(user_id)
        success = random.random() * 100 < preview.final_probability
        loss = 0 if success else max(0, math.floor(profile.cultivation * preview.failure_loss_percent / 100))
        if not success:
            profile.cultivation = max(0, profile.cultivation - loss)
        else:
            profile.realm_key = preview.target_realm
            profile.minor_stage = 1
            profile.cultivation = 0
        attempt = TribulationAttempt(
            user_id=user_id, target_realm=preview.target_realm,
            base_probability=preview.base_probability, readiness_score=preview.readiness_score,
            pill_bonus=preview.pill_bonus, final_probability=preview.final_probability,
            roll=preview.final_probability if success else 100, success=success,
            cultivation_loss=loss,
        )
        self.db.add(attempt)
        self.db.commit()
        return TribulationResult(success=success, realm_key=profile.realm_key, target_realm=preview.target_realm, cultivation_loss=loss, log_id=attempt.id)

    def settle_todo_reward(
        self,
        user_id: UUID,
        source: str,
        base_exp: int,
        difficulty: str,
        quality: float = 1.0,
        importance: float = 1.0,
    ) -> RewardSettlement:
        try:
            difficulty_factor = DIFFICULTY_FACTORS[difficulty]
        except KeyError as exc:
            raise ValueError(f"Unknown difficulty: {difficulty}") from exc

        profile = self.ensure_profile(user_id)
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        cultivation = max(0, math.floor(
            base_exp
            * difficulty_factor
            * importance
            * profile.cultivation_efficiency
            * quality
        ))
        stones = max(1, math.floor(cultivation * 0.6))
        profile.cultivation += cultivation
        profile.spirit_stones += stones
        log = CultivationLog(
            user_id=user_id,
            source=source,
            cultivation_delta=cultivation,
            spirit_stones_delta=stones,
        )
        self.db.add(log)
        self.user_repo._update_experience_no_commit(user, cultivation)
        self.user_repo._update_coins_no_commit(user, stones)
        self.db.flush()
        return RewardSettlement(
            cultivation=cultivation,
            spirit_stones=stones,
            merit=0,
            efficiency=profile.cultivation_efficiency,
            log_id=log.id,
            legacy_exp=cultivation,
        )

    def get_next_stage(
        self, realm_key: str, minor_stage: int, cultivation: int
    ) -> StageProgress:
        thresholds = REALM_THRESHOLDS[realm_key]
        if realm_key == "qi_refining" and minor_stage == 1:
            current_threshold = 0
            next_threshold = 180
        else:
            index = max(0, min(minor_stage - 1, len(thresholds) - 1))
            current_threshold = 0 if index == 0 else thresholds[index - 1]
            next_threshold = thresholds[index]
        return StageProgress(
            realm_key=realm_key,
            minor_stage=minor_stage,
            cultivation=cultivation,
            current_threshold=current_threshold,
            next_threshold=next_threshold,
            remaining=max(0, next_threshold - cultivation),
        )
