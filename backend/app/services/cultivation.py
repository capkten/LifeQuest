import math
import random
import threading
from contextlib import nullcontext
from hashlib import sha256
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cultivation import CultivationLog, CultivationProfile, TribulationAttempt
from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
from app.models.todo import Habit, Task
from app.models.world import Npc, NpcEvent, Sect, SectAccessProgress, SectMembership, WorldNode
from app.repositories.cultivation import CultivationRepository
from app.repositories.user import UserRepository
from app.schemas.cultivation import (
    CultivationOverview,
    NpcEventSummary,
    NpcRelationshipResponse,
    NpcSummary,
    RewardSettlement,
    SectMembershipResponse,
    SectSummary,
    StageProgress,
    TechniqueLibraryResponse,
    TechniqueSlotResponse,
    TechniqueSlotPurchasePreview,
    TechniqueSummary,
    LearnedTechniqueResponse,
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

REALM_ORDER = list(REALM_THRESHOLDS) + ["ascended"]
TRIBULATION_RULES = {
    ("qi_refining", "foundation"): (90, 10),
    ("foundation", "golden_core"): (80, 10),
    ("golden_core", "nascent_soul"): (70, 12),
    ("nascent_soul", "spirit_transformation"): (60, 15),
    ("spirit_transformation", "void_refining"): (50, 18),
    ("void_refining", "body_combination"): (40, 20),
    ("body_combination", "great_vehicle"): (30, 22),
    ("great_vehicle", "tribulation"): (25, 25),
    ("tribulation", "ascension"): (20, 25),
}
ASCENDED_REALM_KEY = "ascended"
SECT_ENTRY_REALMS = {
    1: "foundation",
    2: "golden_core",
    3: "nascent_soul",
    4: "spirit_transformation",
    5: "void_refining",
    6: "body_combination",
    7: "great_vehicle",
    8: "tribulation",
    9: "tribulation",
}

DIFFICULTY_FACTORS = {"easy": 0.8, "medium": 1.0, "hard": 1.4}
SLOT_PRICES = [0, 100, 300, 800, 2000, 5000, 12000]
SLOT_REALMS = ["qi_refining", "foundation", "golden_core", "nascent_soul", "spirit_transformation", "void_refining", "body_combination"]
_TRIBULATION_PROCESS_LOCK = threading.Lock()


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
        progress = StageProgress(
            realm_key=profile.realm_key,
            minor_stage=profile.minor_stage,
            cultivation=profile.cultivation,
            current_threshold=0,
            next_threshold=None,
            remaining=0,
        ) if profile.realm_key == ASCENDED_REALM_KEY else self.get_next_stage(profile.realm_key, profile.minor_stage, profile.cultivation)
        from app.services.todo import TodoService

        daily = TodoService(self.db).get_daily_summary(user_id)
        today = [
            {**item, "kind": kind}
            for kind in ("habits", "tasks", "goals")
            for item in daily.get(kind, [])
        ]
        recent_rewards = [
            {
                "id": log.id,
                "source": log.source,
                "cultivation": log.cultivation_delta,
                "spirit_stones": log.spirit_stones_delta,
                "merit": log.merit_delta,
                "created_at": log.created_at,
            }
            for log in self.db.query(CultivationLog)
            .filter(CultivationLog.user_id == user_id)
            .order_by(CultivationLog.created_at.desc())
            .limit(10)
            .all()
        ]
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
            ascended=profile.realm_key == ASCENDED_REALM_KEY,
            next_stage=progress,
            realm={"key": profile.realm_key, "minor_stage": profile.minor_stage},
            today=today,
            recent_rewards=recent_rewards,
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
                    sect = Sect(
                        sect_key=key,
                        name=f"{star}-Star {kind.title()} Sect {ordinal}",
                        star=star,
                        kind=kind,
                        task_preference=f"discipline-{ordinal}",
                        core_legacy=f"Legacy of the {star}-star sect",
                        entry_realm=SECT_ENTRY_REALMS[star],
                        trial_key=f"trial-{star}-{ordinal}",
                        world_node_id=node.id,
                    )
                    db.add(sect)
                sect.entry_realm = SECT_ENTRY_REALMS[star]

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

    def get_sects(self, user_id: UUID, star=None, kind=None, task_preference=None):
        self.seed_world(self.db)
        membership = self.db.query(SectMembership).filter(
            SectMembership.user_id == user_id, SectMembership.status == "active"
        ).first()
        profile = self.ensure_profile(user_id)
        query = self.db.query(Sect).filter(Sect.kind != "hidden").order_by(Sect.star, Sect.sect_key)
        if star is not None:
            query = query.filter(Sect.star == star)
        if kind is not None:
            query = query.filter(Sect.kind == kind)
        if task_preference is not None:
            query = query.filter(Sect.task_preference == task_preference)
        summaries = []
        for sect in query.all():
            summaries.append(self._sect_summary(user_id, profile, sect, membership))
        return summaries

    def contact_sect_messenger(self, user_id: UUID, sect_key: str) -> SectSummary:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        self._require_sect_realm(profile, sect)
        access = self._get_or_create_sect_access(user_id, sect.id)
        access.messenger_contacted = True
        self.db.commit()
        return self._sect_summary(user_id, profile, sect)

    def complete_sect_trial(self, user_id: UUID, sect_key: str) -> SectSummary:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        self._require_sect_realm(profile, sect)
        access = self._get_or_create_sect_access(user_id, sect.id)
        if not access.messenger_contacted:
            raise PermissionError("messenger contact required before trial")
        access.trial_confirmed = True
        self.db.commit()
        return self._sect_summary(user_id, profile, sect)

    def join_sect(self, user_id: UUID, sect_key: str) -> SectMembershipResponse:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        eligibility = self._sect_eligibility(profile, sect, user_id)
        if not eligibility["visible"]:
            raise PermissionError("sect is locked")
        self._require_sect_realm(profile, sect)
        if not eligibility["messenger_contacted"]:
            raise PermissionError("messenger contact required before trial")
        if not eligibility["trial_confirmed"]:
            raise PermissionError("sect trial required")
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
        profile = self.ensure_profile(user_id)
        learned = {row.technique_id for row in self.db.query(LearnedTechnique).filter(LearnedTechnique.user_id == user_id)}
        techniques = self.db.query(Technique).order_by(Technique.technique_key).all()
        slots = self.db.query(TechniqueSlot).filter(TechniqueSlot.user_id == user_id).order_by(TechniqueSlot.slot_type, TechniqueSlot.slot_index).all()
        loadout = {}
        slot_assignments = {}
        for slot in slots:
            loadout.setdefault(slot.slot_type, slot.technique_id)
            slot_assignments.setdefault(slot.slot_type, []).append(slot.technique_id)
        return TechniqueLibraryResponse(
            techniques=[TechniqueSummary(
                id=t.id, technique_key=t.technique_key, name=t.name,
                description=t.description, technique_type=t.technique_type,
                required_realm=t.required_realm, spirit_stone_cost=t.spirit_stone_cost,
                slot_count=t.slot_count, learned=t.id in learned,
                realm_confirmed=not t.required_realm or self._realm_at_least(profile.realm_key, t.required_realm),
            ) for t in techniques],
            slots=[TechniqueSlotResponse(slot_type=s.slot_type, slot_index=s.slot_index, technique_id=s.technique_id) for s in slots],
            loadout=loadout,
            slot_assignments=slot_assignments,
            spirit_stones=profile.spirit_stones,
            next_slot_purchases={
                slot_type: self._slot_purchase_preview(profile, slot_type, len([slot for slot in slots if slot.slot_type == slot_type]))
                for slot_type in ("main", "auxiliary", "mind", "body")
            },
        )

    def learn_technique(self, user_id: UUID, technique_key: str) -> LearnedTechniqueResponse:
        self.seed_world(self.db)
        profile = self.ensure_profile(user_id)
        technique = self.db.query(Technique).filter(Technique.technique_key == technique_key).one_or_none()
        if technique is None:
            raise LookupError("TECHNIQUE_NOT_FOUND:technique not found")
        existing = self.db.query(LearnedTechnique).filter_by(
            user_id=user_id, technique_id=technique.id
        ).one_or_none()
        if existing is not None:
            return LearnedTechniqueResponse(
                id=existing.id, technique_key=technique.technique_key,
                learned_at=existing.learned_at, level=existing.level,
            )
        if technique.required_realm and not self._realm_at_least(profile.realm_key, technique.required_realm):
            raise PermissionError(f"TECHNIQUE_REALM_REQUIRED:{technique.required_realm}")
        if profile.spirit_stones < technique.spirit_stone_cost:
            raise PermissionError(
                f"INSUFFICIENT_SPIRIT_STONES:{technique.spirit_stone_cost}:{profile.spirit_stones}"
            )
        profile.spirit_stones -= technique.spirit_stone_cost
        learned = LearnedTechnique(user_id=user_id, technique_id=technique.id)
        self.db.add(learned)
        try:
            self.db.flush()
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(LearnedTechnique).filter_by(
                user_id=user_id, technique_id=technique.id
            ).one()
            return LearnedTechniqueResponse(
                id=existing.id, technique_key=technique.technique_key,
                learned_at=existing.learned_at, level=existing.level,
            )
        return LearnedTechniqueResponse(
            id=learned.id, technique_key=technique.technique_key,
            learned_at=learned.learned_at, level=learned.level,
        )

    def purchase_slot(self, user_id: UUID, slot_type: str):
        if slot_type not in {"main", "auxiliary", "mind", "body"}:
            raise ValueError("INVALID_SLOT_TYPE")
        profile = self.ensure_profile(user_id)
        existing = self.db.query(TechniqueSlot).filter(
            TechniqueSlot.user_id == user_id, TechniqueSlot.slot_type == slot_type
        ).order_by(TechniqueSlot.slot_index).all()
        next_index = len(existing)
        required_realm = SLOT_REALMS[min(next_index, len(SLOT_REALMS) - 1)]
        if not self._realm_at_least(profile.realm_key, required_realm):
            raise PermissionError(f"SLOT_REALM_REQUIRED:{required_realm}")
        price = SLOT_PRICES[next_index] if next_index < len(SLOT_PRICES) else SLOT_PRICES[-1] * (2 ** (next_index - len(SLOT_PRICES) + 1))
        if profile.spirit_stones < price:
            raise PermissionError(f"INSUFFICIENT_SPIRIT_STONES:{price}:{profile.spirit_stones}")
        profile.spirit_stones -= price
        self.db.add(TechniqueSlot(user_id=user_id, slot_type=slot_type, slot_index=next_index))
        self.db.commit()
        return {"slot_type": slot_type, "slot_index": next_index, "slot_count": next_index + 1, "price": price, "balance": profile.spirit_stones, "required_realm": required_realm}

    def update_loadout(self, user_id: UUID, loadout):
        profile = self.ensure_profile(user_id)
        updates = []
        occupied = {}
        for slot_type, technique_id in loadout.items():
            ids = technique_id if isinstance(technique_id, list) else [technique_id]
            slots = self.db.query(TechniqueSlot).filter(
                TechniqueSlot.user_id == user_id, TechniqueSlot.slot_type == slot_type
            ).order_by(TechniqueSlot.slot_index).all()
            if len(ids) > len(slots):
                raise LookupError("SLOT_NOT_PURCHASED:slot not purchased")
            for index, value in enumerate(ids):
                if value is None:
                    continue
                slot = slots[index]
                technique = self.db.query(Technique).filter(Technique.id == value).first()
                if technique is None:
                    raise LookupError("TECHNIQUE_NOT_FOUND:technique or slot not found")
                learned = self.db.query(LearnedTechnique).filter(
                    LearnedTechnique.user_id == user_id,
                    LearnedTechnique.technique_id == technique.id,
                ).first()
                if learned is None:
                    raise LookupError("TECHNIQUE_NOT_LEARNED:technique not learned")
                if technique.required_realm and not self._realm_at_least(profile.realm_key, technique.required_realm):
                    raise PermissionError(f"TECHNIQUE_REALM_REQUIRED:technique requires {technique.required_realm} realm")
                occupied.setdefault(technique.id, []).append((slot_type, index))
                updates.append((slot, technique.id))
        for technique_id, locations in occupied.items():
            technique = self.db.query(Technique).filter(Technique.id == technique_id).one()
            if len(locations) > 1 and technique.slot_count <= 1:
                raise ValueError("SLOT_CONFLICT:DUPLICATE_TECHNIQUE")
            if len(locations) != technique.slot_count:
                raise ValueError("SLOT_CONFLICT:OCCUPANCY")
            slot_types = {slot_type for slot_type, _ in locations}
            if len(slot_types) != 1:
                raise ValueError("SLOT_CONFLICT:CATEGORY")
            indexes = sorted(slot_index for _, slot_index in locations)
            if indexes != list(range(indexes[0], indexes[0] + technique.slot_count)):
                raise ValueError("SLOT_CONFLICT:NON_CONTIGUOUS")
        for slot, technique_id in updates:
            slot.technique_id = technique_id
        self.db.commit()
        return self.get_techniques(user_id)

    def _get_sect(self, sect_key: str) -> Sect:
        sect = self.db.query(Sect).filter(Sect.sect_key == sect_key).first()
        if sect is None:
            try:
                sect = self.db.query(Sect).filter(Sect.id == UUID(sect_key)).first()
            except ValueError:
                sect = None
        if sect is None:
            raise LookupError("sect not found")
        return sect

    def _get_or_create_sect_access(self, user_id: UUID, sect_id: UUID) -> SectAccessProgress:
        access = self.db.query(SectAccessProgress).filter_by(user_id=user_id, sect_id=sect_id).first()
        if access is None:
            access = SectAccessProgress(user_id=user_id, sect_id=sect_id)
            self.db.add(access)
            self.db.flush()
        return access

    def _require_sect_realm(self, profile: CultivationProfile, sect: Sect):
        if sect.kind == "hidden":
            raise PermissionError("sect is locked")
        if not self._realm_at_least(profile.realm_key, sect.entry_realm or SECT_ENTRY_REALMS[sect.star]):
            required_realm = sect.entry_realm or SECT_ENTRY_REALMS[sect.star]
            raise PermissionError(f"sect requires {required_realm} realm")

    def _sect_summary(self, user_id, profile, sect, membership=None):
        if membership is None:
            membership = self.db.query(SectMembership).filter(
                SectMembership.user_id == user_id, SectMembership.status == "active"
            ).first()
        return SectSummary(
            id=sect.id,
            sect_key=sect.sect_key,
            name=sect.name,
            star=sect.star,
            kind=sect.kind,
            task_preference=sect.task_preference,
            entry_realm=sect.entry_realm,
            world_node_key=self.db.query(WorldNode.node_key).filter(WorldNode.id == sect.world_node_id).scalar(),
            core_legacy=sect.core_legacy,
            joined=bool(membership and membership.sect_id == sect.id),
            **self._sect_eligibility(profile, sect, user_id),
        )

    def _sect_eligibility(self, profile: CultivationProfile, sect: Sect, user_id=None):
        visible = sect.kind != "hidden"
        required_realm = sect.entry_realm or SECT_ENTRY_REALMS[sect.star]
        realm_confirmed = visible and self._realm_at_least(profile.realm_key, required_realm)
        access = None
        if user_id is not None:
            access = self.db.query(SectAccessProgress).filter_by(user_id=user_id, sect_id=sect.id).first()
        messenger_contacted = bool(access and access.messenger_contacted)
        trial_confirmed = bool(access and access.trial_confirmed)
        return {
            "visible": visible,
            "can_join": realm_confirmed and messenger_contacted and trial_confirmed,
            "realm_confirmed": realm_confirmed,
            "messenger_contacted": messenger_contacted,
            "trial_confirmed": trial_confirmed,
            "trial_status": "completed" if trial_confirmed else "awaiting_trial" if messenger_contacted else "awaiting_messenger",
        }

    def _slot_purchase_preview(self, profile: CultivationProfile, slot_type: str, next_index: int):
        required_realm = SLOT_REALMS[min(next_index, len(SLOT_REALMS) - 1)]
        price = SLOT_PRICES[next_index] if next_index < len(SLOT_PRICES) else SLOT_PRICES[-1] * (2 ** (next_index - len(SLOT_PRICES) + 1))
        realm_confirmed = self._realm_at_least(profile.realm_key, required_realm)
        return TechniqueSlotPurchasePreview(
            next_slot_index=next_index,
            price=price,
            required_realm=required_realm,
            post_purchase_balance=profile.spirit_stones - price,
            realm_confirmed=realm_confirmed,
            can_purchase=realm_confirmed and profile.spirit_stones >= price,
        )

    def get_npcs(self, user_id: UUID) -> NpcRelationshipResponse:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        fixed_core = self._ensure_fixed_core_npcs(user_id) if profile.realm_key == ASCENDED_REALM_KEY else []
        event_rows = self.db.query(NpcEvent, Npc).join(
            Npc, Npc.id == NpcEvent.npc_id
        ).filter(
            NpcEvent.user_id == user_id,
            Npc.user_id == user_id,
            Npc.is_generated.is_(True),
        ).order_by(NpcEvent.created_at.desc()).limit(20).all()
        recent = []
        seen = set()
        events = []
        for event, npc in event_rows:
            events.append(NpcEventSummary(
                event_id=event.id,
                npc_id=npc.id,
                event_key=event.event_key,
                summary=event.summary,
                created_at=event.created_at,
            ))
            if npc.id in seen:
                continue
            self.refresh_npc_cultivation(npc)
            recent.append(npc)
            seen.add(npc.id)
        return NpcRelationshipResponse(
            fixed_core=[NpcSummary.model_validate(row) for row in fixed_core],
            recently_met=[NpcSummary.model_validate(row) for row in recent],
            events=events,
        )

    def meet_npc(self, user_id: UUID, sect_key: str, population_index: int) -> NpcSummary:
        if population_index < 0:
            raise ValueError("population_index must be non-negative")
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        profile = self.ensure_profile(user_id)
        eligibility = self._sect_eligibility(profile, sect, user_id)
        if not eligibility["visible"]:
            raise PermissionError("sect is locked")
        if not eligibility["realm_confirmed"]:
            required_realm = sect.entry_realm or SECT_ENTRY_REALMS[sect.star]
            raise PermissionError(f"sect requires {required_realm} realm")
        if not eligibility["messenger_contacted"]:
            raise PermissionError("messenger contact required before meeting NPC")
        for _attempt in range(2):
            npc = self.db.query(Npc).filter(
                Npc.user_id == user_id,
                Npc.sect_id == sect.id,
                Npc.population_index == population_index,
            ).first()
            if npc is not None:
                break

            seed = self._npc_seed(str(sect.id), population_index)
            npc = Npc(
                user_id=user_id,
                sect_id=sect.id,
                name=self._ordinary_npc_name(seed),
                role="ordinary disciple",
                description=f"A disciple of {sect.name}.",
                is_core=False,
                population_index=population_index,
                is_generated=True,
                cultivation=20 + seed % 81,
                cultivation_updated_on=self._utc_today(),
                cultivation_locked=False,
            )
            self.db.add(npc)
            try:
                self.db.flush()
            except IntegrityError:
                self.db.rollback()
                continue
            break
        else:
            raise RuntimeError("NPC creation conflict could not be resolved")

        self.db.add(NpcEvent(user_id=user_id, npc_id=npc.id, event_key="met", summary="Met ordinary disciple"))
        self.db.commit()
        self.db.refresh(npc)
        return NpcSummary.model_validate(npc)

    def refresh_npc_cultivation(self, npc: Npc, today: date = None) -> Npc:
        today = today or self._utc_today()
        if npc.cultivation_locked or npc.cultivation_updated_on is None or today <= npc.cultivation_updated_on:
            return npc
        days = (today - npc.cultivation_updated_on).days
        seed = self._npc_seed(str(npc.sect_id), npc.population_index or 0)
        npc.cultivation += days * (1 + seed % 10)
        npc.cultivation_updated_on = today
        self.db.commit()
        return npc

    @staticmethod
    def _utc_today() -> date:
        return datetime.now(timezone.utc).date()

    def _ensure_fixed_core_npcs(self, user_id: UUID):
        roles = (("sect master", "玄衡宗主"), ("transmission elder", "传法长老"), ("trial envoy", "入门使者"))
        for sect in self.db.query(Sect).all():
            for role, name in roles:
                exists = self.db.query(Npc).filter(
                    Npc.user_id == user_id, Npc.sect_id == sect.id,
                    Npc.role == role, Npc.is_core.is_(True),
                ).first()
                if exists is None:
                    self.db.add(Npc(
                        user_id=user_id, sect_id=sect.id, name=name, role=role,
                        description=f"{sect.name}的固定核心人物。", is_core=True,
                        is_generated=False, cultivation_locked=True,
                    ))
        self.db.commit()
        return self.db.query(Npc).filter(
            Npc.user_id == user_id, Npc.is_core.is_(True)
        ).order_by(Npc.name).all()

    @staticmethod
    def _npc_seed(sect_key: str, population_index: int) -> int:
        return int.from_bytes(sha256(f"{sect_key}:{population_index}".encode("utf-8")).digest()[:8], "big")

    @staticmethod
    def _ordinary_npc_name(seed: int) -> str:
        surnames = ("沈", "顾", "陆", "叶", "苏", "宁", "萧", "秦")
        given = ("清衡", "知远", "景行", "云舟", "若木", "闻道", "怀瑾", "明川")
        return f"{surnames[seed % len(surnames)]}{given[(seed // len(surnames)) % len(given)]}"

    def set_realm(self, user_id: UUID, realm_key: str, minor_stage: int, cultivation: int):
        profile = self.ensure_profile(user_id)
        if realm_key not in REALM_ORDER:
            raise ValueError("Unknown realm")
        profile.realm_key = realm_key
        profile.minor_stage = minor_stage
        profile.cultivation = max(0, cultivation)
        self.db.commit()
        return profile

    def get_tribulation_preview(self, user_id: UUID, pill_count=0) -> TribulationPreview:
        profile = self.ensure_profile(user_id)
        if profile.realm_key == ASCENDED_REALM_KEY:
            return TribulationPreview(
                target_realm=ASCENDED_REALM_KEY,
                base_probability=0,
                readiness_score=0,
                readiness_breakdown={key: 0 for key in ("mind_state", "habit", "task_quality", "trial", "compatibility")},
                readiness_bonus=0,
                pill_count=0,
                pill_bonus=0,
                final_probability=0,
                failure_loss_percent=0,
                failure_loss=0,
                terminal=True,
                available=False,
                lock_reason="ASCENDED",
            )
        index = REALM_ORDER.index(profile.realm_key)
        target = "ascension" if profile.realm_key == "tribulation" else REALM_ORDER[index + 1]
        base, failure_loss_percent = TRIBULATION_RULES[(profile.realm_key, target)]
        readiness_breakdown = self._readiness_breakdown(profile)
        readiness = round(
            readiness_breakdown["mind_state"] * 0.25
            + readiness_breakdown["habit"] * 0.20
            + readiness_breakdown["task_quality"] * 0.20
            + readiness_breakdown["trial"] * 0.20
            + readiness_breakdown["compatibility"] * 0.15,
            2,
        )
        readiness_bonus = round((readiness - 50) / 5)
        bounded_pills = min(15, max(0, int(pill_count or 0)))
        pill_bonus = bounded_pills * 5
        cooldown_until = self._cooldown_until(user_id)
        final_stage = self._is_final_minor_stage(profile)
        lock_reason = (
            "TRIBULATION_COOLDOWN_ACTIVE" if cooldown_until is not None
            else "FINAL_MINOR_STAGE_REQUIRED" if not final_stage
            else None
        )
        return TribulationPreview(
            target_realm=target,
            base_probability=base,
            readiness_score=readiness,
            readiness_breakdown=readiness_breakdown,
            readiness_bonus=readiness_bonus,
            pill_count=bounded_pills,
            pill_bonus=pill_bonus,
            final_probability=max(20, min(95, base + readiness_bonus + pill_bonus)),
            failure_loss_percent=failure_loss_percent,
            failure_loss=math.floor(REALM_THRESHOLDS[profile.realm_key][-1] * failure_loss_percent / 100),
            cooldown_until=cooldown_until,
            available=lock_reason is None,
            lock_reason=lock_reason,
        )

    def attempt_tribulation(self, user_id: UUID, pill_count: int) -> TribulationResult:
        with _TRIBULATION_PROCESS_LOCK:
            return self._attempt_tribulation(user_id, pill_count)

    def _attempt_tribulation(self, user_id: UUID, pill_count: int) -> TribulationResult:
        profile = self.db.query(CultivationProfile).with_for_update().filter_by(user_id=user_id).one_or_none()
        if profile is None:
            profile = self.ensure_profile(user_id)
        preview = self.get_tribulation_preview(user_id, pill_count)
        if preview.terminal:
            raise PermissionError("tribulation already complete")
        if preview.cooldown_until is not None:
            raise PermissionError("tribulation cooldown active")
        if not self._is_final_minor_stage(profile):
            raise PermissionError("tribulation requires final minor stage threshold")
        success = self.roll(preview.final_probability)
        roll = getattr(self, "_last_roll", None)
        if roll is None:
            roll = random.random() * 100
        threshold = REALM_THRESHOLDS[profile.realm_key][-1]
        loss = 0 if success else max(0, math.floor(threshold * preview.failure_loss_percent / 100))
        if not success:
            profile.cultivation = max(0, profile.cultivation - loss)
        else:
            profile.realm_key = ASCENDED_REALM_KEY if preview.target_realm == "ascension" else preview.target_realm
            profile.minor_stage = 1
            profile.cultivation = 0
        attempt = TribulationAttempt(
            user_id=user_id, target_realm=preview.target_realm,
            base_probability=preview.base_probability, readiness_score=preview.readiness_score,
            pill_bonus=preview.pill_bonus, final_probability=preview.final_probability,
            roll=roll, success=success,
            cultivation_loss=loss,
            attempted_date=self._utc_today(),
        )
        self.db.add(attempt)
        try:
            self.db.flush()
            attempt_id = attempt.id
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if self._is_daily_attempt_conflict(exc):
                raise PermissionError("tribulation cooldown active") from exc
            raise
        return TribulationResult(success=success, realm_key=profile.realm_key, target_realm=preview.target_realm, cultivation_loss=loss, log_id=attempt_id, cooldown_until=self._cooldown_until(user_id), terminal=success and preview.target_realm == "ascension")

    def roll(self, probability: float):
        roll = random.random() * 100
        self._last_roll = roll
        return roll < probability

    def _readiness_breakdown(self, profile: CultivationProfile):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        habits = self.db.query(Habit).filter(Habit.user_id == profile.user_id, Habit.is_active.is_(True)).all()
        recent_tasks = self.db.query(Task).filter(Task.user_id == profile.user_id, Task.completed_at >= week_ago).all()
        habit_score = 50.0 if not habits else round(sum(1 for habit in habits if habit.last_completed_at and self._as_utc(habit.last_completed_at) >= week_ago) / len(habits) * 100, 2)
        task_weights = {"easy": 60, "medium": 80, "hard": 100}
        task_score = 50.0 if not recent_tasks else round(sum(task_weights.get(task.difficulty, 80) for task in recent_tasks) / len(recent_tasks), 2)
        trial_score = 100.0 if self.db.query(SectAccessProgress).filter(SectAccessProgress.user_id == profile.user_id, SectAccessProgress.trial_confirmed.is_(True)).count() else 0.0
        has_membership = self.db.query(SectMembership).filter(SectMembership.user_id == profile.user_id, SectMembership.status == "active").count() > 0
        has_technique = self.db.query(LearnedTechnique).filter(LearnedTechnique.user_id == profile.user_id).count() > 0
        compatibility_score = 100.0 if has_membership and has_technique else 60.0 if has_membership or has_technique else 0.0
        return {
            "mind_state": max(0, min(100, float(profile.mind_state))),
            "habit": habit_score,
            "task_quality": task_score,
            "trial": trial_score,
            "compatibility": compatibility_score,
        }

    @staticmethod
    def _as_utc(value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _cooldown_until(self, user_id: UUID):
        last_attempt = self.db.query(TribulationAttempt).filter_by(user_id=user_id, attempted_date=self._utc_today()).order_by(TribulationAttempt.attempted_at.desc()).first()
        if last_attempt is None:
            return None
        attempted_at = last_attempt.attempted_at
        if attempted_at.tzinfo is None:
            attempted_at = attempted_at.replace(tzinfo=timezone.utc)
        next_day = (attempted_at + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_day if next_day > datetime.now(timezone.utc) else None

    @staticmethod
    def _utc_today():
        return datetime.now(timezone.utc).date()

    @staticmethod
    def _is_daily_attempt_conflict(exc: IntegrityError) -> bool:
        original = getattr(exc, "orig", None)
        diagnostic = getattr(original, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", "")
        if constraint_name == "uq_tribulation_attempt_user_day":
            return True
        error_text = str(original or exc).lower()
        normalized = " ".join(error_text.split())
        return normalized.endswith(
            "unique constraint failed: tribulation_attempts.user_id, "
            "tribulation_attempts.attempted_date"
        )

    @staticmethod
    def _realm_at_least(current_realm: str, required_realm: str) -> bool:
        return REALM_ORDER.index(current_realm) >= REALM_ORDER.index(required_realm)

    @classmethod
    def _is_final_minor_stage(cls, profile: CultivationProfile) -> bool:
        if profile.realm_key == ASCENDED_REALM_KEY:
            return True
        thresholds = REALM_THRESHOLDS[profile.realm_key]
        return profile.minor_stage == len(thresholds) and profile.cultivation >= thresholds[-1]

    @classmethod
    def _realm_meets_entry(cls, profile: CultivationProfile, star: int, required_realm: str) -> bool:
        if not cls._realm_at_least(profile.realm_key, required_realm):
            return False
        return star != 9 or cls._is_final_minor_stage(profile)

    def settle_todo_reward(
        self,
        user_id: UUID,
        source: str,
        base_exp: int,
        difficulty: str,
        quality: float = 1.0,
        importance: float = 1.0,
        source_key: str | None = None,
    ) -> RewardSettlement:
        try:
            difficulty_factor = DIFFICULTY_FACTORS[difficulty]
        except KeyError as exc:
            raise ValueError(f"Unknown difficulty: {difficulty}") from exc

        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        if source_key:
            existing_log = self.db.query(CultivationLog).filter(
                CultivationLog.source_key == source_key,
                CultivationLog.user_id == user_id,
            ).one_or_none()
            if existing_log is not None:
                return self._settlement_from_existing_log(existing_log, user_id)
        try:
            # A source-key savepoint contains both the unique claim and all
            # cultivation mutations, so a losing concurrent session rolls back
            # without leaving a partial reward behind.
            with (self.db.begin_nested() if source_key else nullcontext()):
                profile = self.ensure_profile(user_id)
                cultivation = max(0, math.floor(
                    base_exp
                    * difficulty_factor
                    * importance
                    * profile.cultivation_efficiency
                    * quality
                ))
                stones = max(1, math.floor(cultivation * 0.6))
                profile.cultivation += cultivation
                if profile.realm_key != ASCENDED_REALM_KEY:
                    while profile.minor_stage < len(REALM_THRESHOLDS[profile.realm_key]):
                        next_threshold = self.get_next_stage(
                            profile.realm_key, profile.minor_stage, profile.cultivation
                        ).next_threshold
                        if next_threshold is None or profile.cultivation < next_threshold:
                            break
                        profile.cultivation -= next_threshold
                        profile.minor_stage += 1
                        if profile.minor_stage == len(REALM_THRESHOLDS[profile.realm_key]):
                            profile.cultivation += next_threshold
                            break
                ready_for_tribulation = (
                    profile.realm_key != ASCENDED_REALM_KEY
                    and self._is_final_minor_stage(profile)
                )
                profile.spirit_stones += stones
                log = CultivationLog(
                    user_id=user_id,
                    source=source,
                    source_key=source_key,
                    cultivation_delta=cultivation,
                    spirit_stones_delta=stones,
                )
                self.db.add(log)
                self.db.flush()
        except IntegrityError:
            existing_log = self.db.query(CultivationLog).filter(
                CultivationLog.source_key == source_key,
                CultivationLog.user_id == user_id,
            ).one_or_none()
            if existing_log is None:
                raise
            return self._settlement_from_existing_log(existing_log, user_id)

        self.user_repo._update_experience_no_commit(user, cultivation)
        self.user_repo._update_coins_no_commit(user, stones)
        return RewardSettlement(
            cultivation=cultivation,
            spirit_stones=stones,
            merit=0,
            efficiency=profile.cultivation_efficiency,
            log_id=log.id,
            legacy_exp=cultivation,
            ready_for_tribulation=ready_for_tribulation,
        )

    def _settlement_from_existing_log(
        self, log: CultivationLog, user_id: UUID
    ) -> RewardSettlement:
        profile = self.cultivation_repo.get_by_user(user_id)
        settlement = RewardSettlement(
            cultivation=log.cultivation_delta,
            spirit_stones=log.spirit_stones_delta,
            merit=log.merit_delta,
            efficiency=profile.cultivation_efficiency if profile else 1.0,
            log_id=log.id,
            legacy_exp=log.cultivation_delta,
            ready_for_tribulation=bool(
                profile
                and profile.realm_key != ASCENDED_REALM_KEY
                and self._is_final_minor_stage(profile)
            ),
        )
        settlement._already_settled = True
        return settlement

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
