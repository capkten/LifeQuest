import math
import random
import time
import threading
import json
from contextlib import nullcontext
from hashlib import sha256
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.models.cultivation import CultivationLog, CultivationProfile, TribulationAttempt
from app.models.backpack import TribulationPillSettlement
from app.models.immortal import CrossRealmSettlement, ImmortalProfile
from app.models.project import Project, ProjectPhase, PhaseStatus
from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
from app.models.todo import Goal, Habit, Task, TaskStatus
from app.services.backpack import BackpackService
from app.models.user import User
from app.models.world import Npc, NpcEvent, Sect, SectAccessProgress, SectMembership, WorldNode, WorldNodeProgress
from app.repositories.cultivation import CultivationRepository
from app.repositories.user import UserRepository
from app.services.content_catalog import (
    CULTIVATION_RESOURCE_RULES,
    DIFFICULTY_FACTORS,
    EVENT_SUMMARY_LABELS,
    NPC_ROLE_LABELS,
    REALM_LABELS,
    SECT_CATALOG,
    source_label,
    TECHNIQUE_CATALOG,
    TECHNIQUE_EFFICIENCY_BONUSES,
    WORLD_NODE_CATALOG,
    HIDDEN_SECT_REVEAL_CATALOG,
    SECT_TRIAL_CATALOG,
)
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
    TribulationPrerequisite,
    TribulationPreview,
    TribulationResult,
    WorldNodeResponse,
    WorldResponse,
    SectAccessResponse,
    HiddenSectSummary,
    ResourceState,
    SettlementResult,
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
SOURCE_KEY_RETRY_COUNT = 3
SOURCE_KEY_RETRY_DELAY_SECONDS = 0.05
TRIBULATION_RETRY_COUNT = 5
TRIBULATION_RETRY_DELAY_SECONDS = 0.05
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

SLOT_TYPES = ("main", "auxiliary", "mind", "movement", "body")
SLOT_PRICES = [0, 100, 300, 800, 2000, 5000, 12000]
SLOT_REALMS = [
    "qi_refining", "foundation", "golden_core", "nascent_soul",
    "spirit_transformation", "void_refining", "body_combination",
    "great_vehicle", "tribulation", "tribulation", "tribulation",
    "tribulation", "tribulation", "tribulation",
]
_TRIBULATION_PROCESS_LOCK = threading.Lock()


def _catalog_label(catalog, raw_value, label_field):
    if raw_value is None:
        return None
    for content in catalog.values():
        if content.get(label_field.replace("_label", "")) == raw_value:
            return content.get(label_field, raw_value)
    return raw_value


def _realm_label(realm_key):
    if realm_key is None:
        return None
    return REALM_LABELS.get(realm_key, realm_key)


def _cultivation_log_description(source, cultivation, spirit_stones):
    return f"完成{source_label(source)}，获得{cultivation}点修为和{spirit_stones}枚灵石。"


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

    def get_resource_state(self, user_id: UUID) -> ResourceState:
        """Return the current authoritative mortal resource balances."""
        profile = self.ensure_profile(user_id)
        return ResourceState(
            merit=profile.merit,
            aptitude_points=profile.aptitude_points,
            mind_state=profile.mind_state,
            contribution=profile.contribution,
            tribulation_pills=self._owned_tribulation_pills(user_id),
        )

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
                "description": _cultivation_log_description(
                    log.source, log.cultivation_delta, log.spirit_stones_delta
                ),
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
            realm_label=_realm_label(profile.realm_key),
            next_stage=progress,
            realm={"key": profile.realm_key, "minor_stage": profile.minor_stage},
            today=today,
            recent_rewards=recent_rewards,
        )

    @staticmethod
    def seed_world(db: Session):
        for attempt in range(3):
            try:
                return CultivationService._seed_world_once(db)
            except (IntegrityError, OperationalError) as exc:
                if isinstance(exc, OperationalError) and not CultivationService._is_database_lock_error(exc):
                    raise
                db.rollback()
                if attempt == 2:
                    raise
                time.sleep(SOURCE_KEY_RETRY_DELAY_SECONDS)

    @staticmethod
    def _seed_world_once(db: Session):
        nodes = []
        for index, (key, content) in enumerate(WORLD_NODE_CATALOG.items(), 1):
            node = db.query(WorldNode).filter(WorldNode.node_key == key).first()
            if node is None:
                node = WorldNode(
                    node_key=key,
                    name=content["name"],
                    description=content["description"],
                    required_realm=content["required_realm"],
                    region_key=content.get("region_key", "mortal"),
                    required_project_phase=content.get("required_project_phase", 0),
                    sort_order=index,
                    is_hidden=False,
                    completed=False,
                    visible=True,
                )
                db.add(node)
            else:
                node.name = content["name"]
                node.description = content["description"]
                node.required_realm = content["required_realm"]
                node.region_key = content.get("region_key", "mortal")
                node.required_project_phase = content.get("required_project_phase", 0)
            nodes.append(node)
        db.flush()

        nodes_by_key = {node.node_key: node for node in nodes}
        for key, content in SECT_CATALOG.items():
            sect = db.query(Sect).filter(Sect.sect_key == key).first()
            if sect is None:
                star = int(key.split("-", 2)[1])
                sect = Sect(
                    sect_key=key,
                    name=content["name"],
                    star=star,
                    kind=content["kind"],
                    task_preference=content["task_preference"],
                    core_legacy=content["core_legacy"],
                    entry_realm=content["entry_realm"],
                    trial_key=content["trial_key"],
                    world_node_id=nodes_by_key[content["world_node_key"]].id,
                )
                db.add(sect)
            sect.entry_realm = content["entry_realm"]

        for key, content in TECHNIQUE_CATALOG.items():
            technique = db.query(Technique).filter(Technique.technique_key == key).first()
            if technique is None:
                technique = Technique(
                    technique_key=key,
                    name=content["name"],
                    description=content["description"],
                    technique_type=content["technique_type"],
                    required_realm=content["required_realm"],
                    spirit_stone_cost=content["spirit_stone_cost"],
                    slot_count=content["slot_count"],
                    effect_config=json.dumps(content.get("effect_config", {}), ensure_ascii=False, sort_keys=True),
                    conflict_tags=json.dumps(content.get("conflict_tags", []), ensure_ascii=False, sort_keys=True),
                )
                db.add(technique)
            else:
                technique.name = content["name"]
                technique.description = content["description"]
                technique.technique_type = content["technique_type"]
                technique.required_realm = content["required_realm"]
                technique.spirit_stone_cost = content["spirit_stone_cost"]
                technique.slot_count = content["slot_count"]
                technique.effect_config = json.dumps(
                    content.get("effect_config", {}), ensure_ascii=False, sort_keys=True
                )
                technique.conflict_tags = json.dumps(
                    content.get("conflict_tags", []), ensure_ascii=False, sort_keys=True
                )
        db.commit()

    def get_world(self, user_id: UUID) -> WorldResponse:
        self.seed_world(self.db)
        profile = self.ensure_profile(user_id)
        nodes = self.db.query(WorldNode).order_by(WorldNode.sort_order).all()
        completed_ids = {
            row.node_id for row in self.db.query(WorldNodeProgress).filter_by(
                user_id=user_id, completed=True
            ).all()
        }
        visible_nodes = []
        completed_count = len(completed_ids)
        for index, node in enumerate(nodes):
            completed = node.id in completed_ids
            visible = self._world_node_visible(profile, node, nodes, completed_ids, completed_count)
            lock_reason = None if visible else self._world_node_lock_reason(profile, node, nodes, completed_ids)
            visible_nodes.append(WorldNodeResponse(
                node_key=node.node_key,
                name=node.name,
                description=node.description,
                required_realm=node.required_realm,
                region_key=node.region_key,
                required_project_phase=node.required_project_phase,
                sort_order=node.sort_order,
                is_hidden=node.is_hidden,
                completed=completed,
                visible=visible,
                lock_reason=lock_reason,
            ))
        return WorldResponse(nodes=visible_nodes)

    def get_sects(self, user_id: UUID, star=None, kind=None, task_preference=None):
        self.seed_world(self.db)
        membership = self.db.query(SectMembership).filter(
            SectMembership.user_id == user_id, SectMembership.status == "active"
        ).first()
        profile = self.ensure_profile(user_id)
        query = self.db.query(Sect).order_by(Sect.star, Sect.sect_key)
        if kind != "hidden":
            query = query.filter(Sect.kind != "hidden")
        if star is not None:
            query = query.filter(Sect.star == star)
        if kind is not None:
            query = query.filter(Sect.kind == kind)
        if task_preference is not None:
            query = query.filter(Sect.task_preference == task_preference)
        summaries = []
        hidden_evaluation = {
            item["sect_key"]: item for item in self.evaluate_hidden_sects(user_id)
        } if kind == "hidden" else {}
        for sect in query.all():
            summary = self._sect_summary(user_id, profile, sect, membership)
            if sect.kind == "hidden" and sect.sect_key in hidden_evaluation:
                evaluation = hidden_evaluation[sect.sect_key]
                summary = summary.model_copy(update={
                    "visible": evaluation["visible"],
                    "can_join": evaluation["can_join"],
                    "lock_reason": evaluation["lock_reason"],
                    "missing_conditions": evaluation["missing_conditions"],
                    "name": sect.name if evaluation["visible"] else "未显现宗门",
                    "core_legacy": sect.core_legacy if evaluation["visible"] else None,
                })
            summaries.append(summary)
        return summaries

    @staticmethod
    def _trial_template():
        return json.loads(json.dumps(SECT_TRIAL_CATALOG["default"], ensure_ascii=False))

    def _initialize_trial_snapshot(self, access: SectAccessProgress):
        if access.objective_snapshot:
            return
        template = self._trial_template()
        access.objective_snapshot = json.dumps(template, ensure_ascii=False, sort_keys=True)
        access.objective_progress = json.dumps(
            {key: False for key in template}, ensure_ascii=False, sort_keys=True
        )

    def _trial_objectives(self, access: SectAccessProgress):
        self._initialize_trial_snapshot(access)
        definitions = json.loads(access.objective_snapshot or "{}")
        progress = json.loads(access.objective_progress or "{}")
        return {
            key: {
                **definition,
                "completed": bool(progress.get(key, False)),
            }
            for key, definition in definitions.items()
        }

    def get_sect_access(self, user_id: UUID, sect_key: str) -> SectAccessResponse:
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        access = self.db.query(SectAccessProgress).filter_by(
            user_id=user_id, sect_id=sect.id
        ).first()
        if access is None:
            return SectAccessResponse(sect_key=sect.sect_key, status="awaiting_messenger")
        if access.trial_confirmed:
            access.trial_status = "completed"
        objectives = self._trial_objectives(access)
        return SectAccessResponse(
            sect_key=sect.sect_key,
            status=access.trial_status or (
                "completed" if access.trial_confirmed else
                "awaiting_trial" if access.messenger_contacted else "awaiting_messenger"
            ),
            objectives=objectives,
            score=access.trial_score or 0,
            messenger_contacted=bool(access.messenger_contacted),
            trial_confirmed=bool(access.trial_confirmed),
            completed_at=access.completed_at,
        )

    def update_trial_objective(
        self, user_id: UUID, sect_key: str, objective_key: str, completed: bool = True
    ) -> SectAccessResponse:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        self._require_sect_realm(profile, sect, user_id)
        access = self._get_or_create_sect_access(user_id, sect.id)
        if not access.messenger_contacted:
            raise PermissionError("TRIAL_MESSENGER_REQUIRED:messenger contact required before trial")
        objectives = self._trial_objectives(access)
        if objective_key not in objectives:
            raise LookupError(f"TRIAL_OBJECTIVE_NOT_FOUND:{objective_key}")
        progress = json.loads(access.objective_progress or "{}")
        progress[objective_key] = bool(completed)
        access.objective_progress = json.dumps(progress, ensure_ascii=False, sort_keys=True)
        if not access.trial_confirmed:
            access.trial_status = "in_progress"
        self.db.commit()
        return self.get_sect_access(user_id, sect_key)

    def _trial_score(self, profile: CultivationProfile, sect: Sect) -> int:
        preference_bonus = 10 if sect.task_preference == f"discipline-{sect.star}" else 0
        return min(100, 70 + min(20, profile.contribution // 25) + preference_bonus)

    def get_sect_effects(self, user_id: UUID) -> dict:
        membership = self.db.query(SectMembership).filter_by(
            user_id=user_id, status="active"
        ).first()
        if membership is None:
            return {
                "sect_key": None,
                "task_preference": None,
                "core_legacy": None,
                "efficiency_bonus": 0.0,
                "contribution_bonus": 0,
            }
        sect = self.db.query(Sect).filter(Sect.id == membership.sect_id).one()
        profile = self.ensure_profile(user_id)
        access = self.db.query(SectAccessProgress).filter_by(
            user_id=user_id, sect_id=sect.id
        ).first()
        return {
            "sect_key": sect.sect_key,
            "task_preference": sect.task_preference,
            "core_legacy": sect.core_legacy,
            "efficiency_bonus": 0.05,
            "contribution_bonus": min(20, profile.contribution // 25),
            "trial_score": access.trial_score if access else 0,
        }

    def evaluate_hidden_sects(self, user_id: UUID):
        self.seed_world(self.db)
        profile = self.ensure_profile(user_id)
        results = []
        for sect in self.db.query(Sect).filter(Sect.kind == "hidden").order_by(Sect.star, Sect.sect_key):
            condition = HIDDEN_SECT_REVEAL_CATALOG.get(sect.sect_key, {
                "required_npc_event": "met",
                "required_mind_state": 70,
                "required_world_node": f"mortal-domain-{sect.star}",
                "required_sect": f"sect-{sect.star}-normal-1",
            })
            missing = []
            event_exists = self.db.query(NpcEvent.id).join(
                Npc, Npc.id == NpcEvent.npc_id
            ).filter(
                NpcEvent.user_id == user_id,
                Npc.user_id == user_id,
                Npc.sect_id == self._get_sect(condition["required_sect"]).id,
                NpcEvent.event_key == condition["required_npc_event"],
            ).first() is not None
            if not event_exists:
                missing.append("npc_event")
            if profile.mind_state < condition["required_mind_state"]:
                missing.append("mind_state")
            node = self.db.query(WorldNode).filter_by(
                node_key=condition["required_world_node"]
            ).one_or_none()
            completed_node = node is not None and self.db.query(WorldNodeProgress).filter_by(
                user_id=user_id, node_id=node.id, completed=True
            ).first() is not None
            if not completed_node:
                missing.append("world_node")
            prerequisite = self._get_sect(condition["required_sect"])
            prerequisite_complete = self.db.query(SectAccessProgress).filter_by(
                user_id=user_id, sect_id=prerequisite.id, trial_confirmed=True
            ).first() is not None
            if not prerequisite_complete:
                missing.append("prerequisite_sect")
            visible = not missing
            hidden_access = self.db.query(SectAccessProgress).filter_by(
                user_id=user_id, sect_id=sect.id, trial_confirmed=True
            ).first()
            results.append({
                "sect_key": sect.sect_key,
                "name": sect.name if visible else None,
                "star": sect.star,
                "kind": sect.kind,
                "visible": visible,
                "can_join": visible and bool(hidden_access) and self._realm_at_least(profile.realm_key, sect.entry_realm or SECT_ENTRY_REALMS[sect.star]),
                "lock_reason": None if visible else f"HIDDEN_SECT_LOCKED:{','.join(missing)}",
                "missing_conditions": missing,
            })
        return results

    def _world_node_lock_reason(self, profile, node, nodes, completed_ids):
        if node.required_realm and not self._realm_at_least(profile.realm_key, node.required_realm):
            return f"WORLD_NODE_REALM_REQUIRED:{node.required_realm}"
        previous = next((item for item in nodes if item.sort_order == node.sort_order - 1), None)
        if previous is not None and previous.id not in completed_ids:
            return f"WORLD_NODE_PREVIOUS_REQUIRED:{previous.node_key}"
        if node.required_project_phase:
            phases = self.db.query(ProjectPhase).join(Project).filter(
                Project.user_id == profile.user_id,
                ProjectPhase.status == PhaseStatus.COMPLETED,
            ).count()
            if phases < node.required_project_phase:
                return f"WORLD_NODE_PROJECT_PHASE_REQUIRED:{node.required_project_phase}"
        return None

    def _world_node_visible(self, profile, node, nodes, completed_ids, completed_count):
        return node.id in completed_ids or self._world_node_lock_reason(
            profile, node, nodes, completed_ids
        ) is None

    def complete_world_node(self, user_id: UUID, node_key: str) -> WorldNodeResponse:
        self.seed_world(self.db)
        profile = self.ensure_profile(user_id)
        node = self.db.query(WorldNode).filter_by(node_key=node_key).one_or_none()
        if node is None:
            raise LookupError("WORLD_NODE_NOT_FOUND")
        nodes = self.db.query(WorldNode).order_by(WorldNode.sort_order).all()
        completed_ids = {
            row.node_id for row in self.db.query(WorldNodeProgress).filter_by(
                user_id=user_id, completed=True
            ).all()
        }
        if node.id not in completed_ids and self._world_node_lock_reason(profile, node, nodes, completed_ids):
            raise PermissionError(self._world_node_lock_reason(profile, node, nodes, completed_ids))
        progress = self.db.query(WorldNodeProgress).filter_by(
            user_id=user_id, node_id=node.id
        ).one_or_none()
        if progress is None:
            progress = WorldNodeProgress(user_id=user_id, node_id=node.id, completed=True, completed_at=datetime.now(timezone.utc))
            self.db.add(progress)
        else:
            progress.completed = True
            progress.completed_at = progress.completed_at or datetime.now(timezone.utc)
        self.db.commit()
        return next(item for item in self.get_world(user_id).nodes if item.node_key == node_key)

    def contact_sect_messenger(self, user_id: UUID, sect_key: str) -> SectSummary:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        self._require_sect_realm(profile, sect, user_id)
        access = self._get_or_create_sect_access(user_id, sect.id)
        access.messenger_contacted = True
        if not access.trial_confirmed:
            access.trial_status = "awaiting_trial"
            self._initialize_trial_snapshot(access)
        self.db.commit()
        return self._sect_summary(user_id, profile, sect)

    def complete_sect_trial(self, user_id: UUID, sect_key: str) -> SectSummary:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        self._require_sect_realm(profile, sect, user_id)
        access = self._get_or_create_sect_access(user_id, sect.id)
        if access.trial_confirmed:
            access.trial_status = "completed"
            self.db.commit()
            return self._sect_summary(user_id, profile, sect)
        if not access.messenger_contacted:
            raise PermissionError("TRIAL_MESSENGER_REQUIRED:messenger contact required before trial")
        objectives = self._trial_objectives(access)
        unmet = [
            key for key, objective in objectives.items()
            if objective.get("required", True) and not objective.get("completed", False)
        ]
        if unmet:
            access.trial_status = "in_progress"
            self.db.commit()
            raise PermissionError(f"TRIAL_OBJECTIVE_UNMET:{','.join(unmet)}")
        access.trial_status = "in_progress"
        access.trial_score = self._trial_score(profile, sect)
        settlement = self.settle_todo_reward(
            user_id,
            "trial_objective",
            180,
            "medium",
            source_key=f"sect-trial:{user_id}:{sect.sect_key}",
            content_star=max(1, min(5, sect.star)),
        )
        access.trial_confirmed = True
        access.trial_status = "completed"
        access.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        return self._sect_summary(user_id, profile, sect)

    def join_sect(self, user_id: UUID, sect_key: str) -> SectMembershipResponse:
        profile = self.ensure_profile(user_id)
        self.seed_world(self.db)
        sect = self._get_sect(sect_key)
        eligibility = self._sect_eligibility(profile, sect, user_id)
        if not eligibility["visible"]:
            raise PermissionError("sect is locked")
        self._require_sect_realm(profile, sect, user_id)
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
                technique_type_label=(
                    TECHNIQUE_CATALOG.get(t.technique_key, {}).get(
                        "technique_type_label"
                    )
                    if TECHNIQUE_CATALOG.get(t.technique_key, {}).get("technique_type")
                    == t.technique_type
                    else _catalog_label(TECHNIQUE_CATALOG, t.technique_type, "technique_type_label")
                ),
                required_realm=t.required_realm, spirit_stone_cost=t.spirit_stone_cost,
                required_realm_label=_realm_label(t.required_realm),
                slot_count=t.slot_count,
                effect_config=self._technique_effect_config(t),
                conflict_tags=sorted(self._technique_conflict_tags(t)),
                learned=t.id in learned,
                realm_confirmed=not t.required_realm or self._realm_at_least(profile.realm_key, t.required_realm),
            ) for t in techniques],
            slots=[TechniqueSlotResponse(slot_type=s.slot_type, slot_index=s.slot_index, technique_id=s.technique_id) for s in slots],
            loadout=loadout,
            slot_assignments=slot_assignments,
            spirit_stones=profile.spirit_stones,
            next_slot_purchases={
                slot_type: self._slot_purchase_preview(profile, slot_type, len([slot for slot in slots if slot.slot_type == slot_type]))
                for slot_type in SLOT_TYPES
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

    @staticmethod
    def _slot_price(slot_index: int) -> int:
        if slot_index < len(SLOT_PRICES):
            return SLOT_PRICES[slot_index]
        return math.floor(SLOT_PRICES[-1] * (2.4 ** (slot_index - len(SLOT_PRICES) + 1)))

    def purchase_slot(self, user_id: UUID, slot_type: str):
        if slot_type not in SLOT_TYPES:
            raise ValueError("INVALID_SLOT_TYPE")
        # Capture pending caller changes before any lookup can autoflush them.
        session_had_pending_work = bool(self.db.new or self.db.dirty or self.db.deleted)
        is_sqlite = self.db.get_bind().dialect.name == "sqlite"
        profile = self.cultivation_repo.get_by_user(user_id)
        if profile is None:
            profile = self.ensure_profile(user_id)
            self.db.commit()
            profile = self.cultivation_repo.get_by_user(user_id)

        if session_had_pending_work:
            self.db.flush()
        existing = self.db.query(TechniqueSlot).filter(
            TechniqueSlot.user_id == user_id, TechniqueSlot.slot_type == slot_type
        ).order_by(TechniqueSlot.slot_index).all()
        next_index = len(existing)

        # A clean session can reset its read snapshot before taking the
        # profile write lock. Concurrent callers that observed the same slot
        # count then cannot silently advance to a second purchase.
        if not session_had_pending_work:
            self.db.rollback()
            if is_sqlite:
                self.db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        self.db.execute(update(CultivationProfile).where(
            CultivationProfile.user_id == user_id
        ).values(spirit_stones=CultivationProfile.spirit_stones))
        self.db.expire_all()
        profile = self.cultivation_repo.get_by_user(user_id)
        current_slots = self.db.query(TechniqueSlot).filter(
            TechniqueSlot.user_id == user_id, TechniqueSlot.slot_type == slot_type
        ).order_by(TechniqueSlot.slot_index).all()
        if len(current_slots) != next_index:
            self.db.rollback()
            raise PermissionError("SLOT_PURCHASE_CONFLICT:slot state changed, refresh and retry")

        required_realm = SLOT_REALMS[min(next_index, len(SLOT_REALMS) - 1)]
        if not self._realm_at_least(profile.realm_key, required_realm):
            self.db.rollback()
            raise PermissionError(f"SLOT_REALM_REQUIRED:{required_realm}")
        price = self._slot_price(next_index)
        if profile.spirit_stones < price:
            self.db.rollback()
            raise PermissionError(f"INSUFFICIENT_SPIRIT_STONES:{price}:{profile.spirit_stones}")
        profile.spirit_stones -= price
        self.db.add(TechniqueSlot(user_id=user_id, slot_type=slot_type, slot_index=next_index))
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise PermissionError("SLOT_PURCHASE_CONFLICT:slot state changed, refresh and retry") from exc
        return {"slot_type": slot_type, "slot_index": next_index, "slot_count": next_index + 1, "price": price, "balance": profile.spirit_stones, "required_realm": required_realm}

    def update_loadout(self, user_id: UUID, loadout):
        profile = self.ensure_profile(user_id)
        updates = []
        occupied = {}
        for slot_type, technique_id in loadout.items():
            if slot_type not in SLOT_TYPES:
                raise ValueError("INVALID_SLOT_TYPE")
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
                if technique.technique_type != slot_type:
                    raise PermissionError(
                        f"TECHNIQUE_TYPE_MISMATCH:{technique.technique_type}:{slot_type}"
                    )
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
        self.db.flush()
        profile.cultivation_efficiency = self._calculate_efficiency(profile, user_id)
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
        if access.trial_confirmed:
            access.trial_status = "completed"
        elif access.messenger_contacted and not access.trial_status:
            access.trial_status = "awaiting_trial"
        return access

    def _require_sect_realm(self, profile: CultivationProfile, sect: Sect, user_id=None):
        if sect.kind == "hidden" and (user_id is None or not any(
            item["sect_key"] == sect.sect_key and item["visible"]
            for item in self.evaluate_hidden_sects(user_id)
        )):
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
            kind_label=(
                SECT_CATALOG.get(sect.sect_key, {}).get("kind_label")
                if SECT_CATALOG.get(sect.sect_key, {}).get("kind") == sect.kind
                else _catalog_label(SECT_CATALOG, sect.kind, "kind_label")
            ),
            task_preference=sect.task_preference,
            task_preference_label=(
                SECT_CATALOG.get(sect.sect_key, {}).get("task_preference_label")
                if SECT_CATALOG.get(sect.sect_key, {}).get("task_preference") == sect.task_preference
                else _catalog_label(SECT_CATALOG, sect.task_preference, "task_preference_label")
            ),
            entry_realm=sect.entry_realm,
            entry_realm_label=_realm_label(sect.entry_realm),
            world_node_key=self.db.query(WorldNode.node_key).filter(WorldNode.id == sect.world_node_id).scalar(),
            core_legacy=sect.core_legacy,
            joined=bool(membership and membership.sect_id == sect.id),
            **self._sect_eligibility(profile, sect, user_id),
        )

    def _sect_eligibility(self, profile: CultivationProfile, sect: Sect, user_id=None):
        visible = sect.kind != "hidden"
        hidden_evaluation = None
        if sect.kind == "hidden" and user_id is not None:
            hidden_evaluation = next(
                (item for item in self.evaluate_hidden_sects(user_id)
                 if item["sect_key"] == sect.sect_key),
                None,
            )
            visible = bool(hidden_evaluation and hidden_evaluation["visible"])
        required_realm = sect.entry_realm or SECT_ENTRY_REALMS[sect.star]
        realm_confirmed = visible and self._realm_at_least(profile.realm_key, required_realm)
        access = None
        if user_id is not None:
            access = self.db.query(SectAccessProgress).filter_by(user_id=user_id, sect_id=sect.id).first()
        messenger_contacted = bool(access and access.messenger_contacted)
        trial_confirmed = bool(access and access.trial_confirmed)
        trial_status = (
            access.trial_status if access and access.trial_status else
            "completed" if trial_confirmed else
            "awaiting_trial" if messenger_contacted else "awaiting_messenger"
        )
        return {
            "visible": visible,
            "can_join": realm_confirmed and messenger_contacted and trial_confirmed,
            "realm_confirmed": realm_confirmed,
            "messenger_contacted": messenger_contacted,
            "trial_confirmed": trial_confirmed,
            "trial_status": trial_status,
            "lock_reason": hidden_evaluation.get("lock_reason") if hidden_evaluation else None,
            "missing_conditions": hidden_evaluation.get("missing_conditions", []) if hidden_evaluation else [],
        }

    def _slot_purchase_preview(self, profile: CultivationProfile, slot_type: str, next_index: int):
        required_realm = SLOT_REALMS[min(next_index, len(SLOT_REALMS) - 1)]
        price = self._slot_price(next_index)
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
                summary=EVENT_SUMMARY_LABELS.get(event.event_key, "未知事件"),
                created_at=event.created_at,
            ))
            if npc.id in seen:
                continue
            self.refresh_npc_cultivation(npc)
            recent.append(npc)
            seen.add(npc.id)
        return NpcRelationshipResponse(
            fixed_core=[self._npc_summary(row) for row in fixed_core],
            recently_met=[self._npc_summary(row) for row in recent],
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
                description=f"{sect.name}的{NPC_ROLE_LABELS['ordinary disciple']}。",
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

        self.db.add(NpcEvent(
            user_id=user_id,
            npc_id=npc.id,
            event_key="met",
            summary=EVENT_SUMMARY_LABELS["met"],
        ))
        self.db.commit()
        self.db.refresh(npc)
        return self._npc_summary(npc)

    def _npc_summary(self, npc: Npc) -> NpcSummary:
        summary = NpcSummary.model_validate(npc)
        if not npc.is_generated:
            return summary
        sect = self.db.query(Sect).filter(Sect.id == npc.sect_id).first()
        sect_name = (
            SECT_CATALOG.get(sect.sect_key, {}).get("name", sect.name)
            if sect is not None
            else None
        )
        if sect_name is None:
            return summary
        if npc.is_core:
            description = f"{sect_name}的固定核心人物。"
        else:
            role_label = NPC_ROLE_LABELS.get(npc.role, "未知身份")
            description = (
                f"{sect_name}的{role_label}。"
                if role_label
                else npc.description
            )
        return summary.model_copy(update={"description": description})

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
                    Npc.role == role, Npc.name == name,
                    Npc.is_core.is_(True), Npc.is_generated.is_(True),
                ).first()
                if exists is None:
                    self.db.add(Npc(
                        user_id=user_id, sect_id=sect.id, name=name, role=role,
                        description=f"{sect.name}的固定核心人物。", is_core=True,
                        is_generated=True, cultivation_locked=True,
                    ))
        self.db.commit()
        return self.db.query(Npc).filter(
            Npc.user_id == user_id,
            Npc.is_core.is_(True),
            Npc.is_generated.is_(True),
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
        owned_pills = self._owned_tribulation_pills(user_id)
        requested_pills = self._bounded_tribulation_pill_count(pill_count)
        if profile.realm_key == ASCENDED_REALM_KEY:
            return TribulationPreview(
                target_realm=ASCENDED_REALM_KEY,
                base_probability=0,
                readiness_score=0,
                readiness_breakdown={key: 0 for key in ("mind_state", "habit", "task_quality", "trial", "compatibility")},
                readiness_bonus=0,
                pill_count=0,
                owned_pills=owned_pills,
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
        readiness = self.calculate_preparation_score(readiness_breakdown)
        readiness_bonus = round((readiness - 50) / 5)
        bounded_pills = min(15, owned_pills, requested_pills)
        pill_bonus = bounded_pills * 5
        cooldown_until = self._cooldown_until(user_id)
        final_stage = self._is_final_minor_stage(profile)
        prerequisites = self._tribulation_prerequisites(profile)
        first_missing = next((item.key for item in prerequisites if not item.satisfied), None)
        lock_reason = (
            "TRIBULATION_COOLDOWN_ACTIVE" if cooldown_until is not None
            else "FINAL_MINOR_STAGE_REQUIRED" if not final_stage
            else f"TRIBULATION_PILL_INSUFFICIENT:{requested_pills}:{owned_pills}" if requested_pills > owned_pills
            else f"TRIBULATION_PREREQUISITE:{first_missing}" if first_missing
            else None
        )
        return TribulationPreview(
            target_realm=target,
            base_probability=base,
            readiness_score=readiness,
            readiness_breakdown=readiness_breakdown,
            readiness_bonus=readiness_bonus,
            pill_count=bounded_pills,
            owned_pills=owned_pills,
            pill_bonus=pill_bonus,
            final_probability=max(20, min(95, base + readiness_bonus + pill_bonus)),
            failure_loss_percent=failure_loss_percent,
            failure_loss=math.floor(REALM_THRESHOLDS[profile.realm_key][-1] * failure_loss_percent / 100),
            cooldown_until=cooldown_until,
            available=lock_reason is None,
            lock_reason=lock_reason,
            prerequisites=prerequisites,
        )

    @staticmethod
    def calculate_preparation_score(snapshot: dict[str, float]) -> float:
        weights = {
            "mind_state": 0.25,
            "habit": 0.20,
            "task_quality": 0.20,
            "trial": 0.20,
            "compatibility": 0.15,
        }
        return round(sum(float(snapshot.get(key, 0)) * weight for key, weight in weights.items()), 2)

    def attempt_tribulation(self, user_id: UUID, pill_count: int) -> TribulationResult:
        with _TRIBULATION_PROCESS_LOCK:
            for attempt in range(TRIBULATION_RETRY_COUNT):
                try:
                    return self._attempt_tribulation(user_id, pill_count)
                except OperationalError as exc:
                    if not self._is_database_lock_error(exc):
                        raise
                    self.db.rollback()
                    if self._has_attempt_today(user_id):
                        raise PermissionError(
                            self._tribulation_lock_message("TRIBULATION_COOLDOWN_ACTIVE")
                        ) from exc
                    if attempt == TRIBULATION_RETRY_COUNT - 1:
                        raise
                    time.sleep(TRIBULATION_RETRY_DELAY_SECONDS)
                except PermissionError:
                    # Validation failures happen before any state mutation;
                    # preserve a newly-created profile for callers that want
                    # to inspect it after a locked attempt.
                    raise
                except Exception:
                    self.db.rollback()
                    raise
        raise RuntimeError("tribulation retry loop exhausted")

    def _attempt_tribulation(self, user_id: UUID, pill_count: int) -> TribulationResult:
        profile = self.db.query(CultivationProfile).with_for_update().filter_by(user_id=user_id).one_or_none()
        if profile is None:
            profile = self.ensure_profile(user_id)
        requested_pills = self._bounded_tribulation_pill_count(pill_count)
        preview = self.get_tribulation_preview(user_id, requested_pills)
        if not preview.available:
            raise PermissionError(self._tribulation_lock_message(preview.lock_reason))
        if preview.pill_count:
            self.consume_tribulation_pills(
                user_id,
                preview.pill_count,
                source_key=self._tribulation_pill_source_key(user_id),
                commit=False,
            )
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
                raise PermissionError(
                    self._tribulation_lock_message("TRIBULATION_COOLDOWN_ACTIVE")
                ) from exc
            raise
        return TribulationResult(success=success, realm_key=profile.realm_key, target_realm=preview.target_realm, cultivation_loss=loss, log_id=attempt_id, cooldown_until=self._cooldown_until(user_id), terminal=success and preview.target_realm == "ascension")

    def _tribulation_pill_source_key(self, user_id: UUID) -> str:
        """Return the retry-stable key for this user's daily pill settlement."""
        return f"tribulation:{user_id}:{self._utc_today()}"

    def consume_tribulation_pills(
        self,
        user_id: UUID,
        amount: int | None = None,
        source_key: str | None = None,
        *,
        count: int | None = None,
        commit: bool = True,
    ) -> SettlementResult:
        """Consume pills atomically under a required idempotency key.

        ``count`` and the default commit behavior preserve the older service
        call shape; tribulation attempts pass ``commit=False`` so their pill
        deduction remains in the attempt's transaction.
        """
        if amount is None:
            amount = count if count is not None else 0
        elif count is not None and int(amount) != int(count):
            raise ValueError("amount and count must match")
        try:
            amount = int(amount)
        except (TypeError, ValueError) as exc:
            raise ValueError("TRIBULATION_PILL_AMOUNT_INVALID") from exc
        if amount < 0:
            raise ValueError("TRIBULATION_PILL_AMOUNT_INVALID")

        if not isinstance(source_key, str) or not source_key.strip():
            raise ValueError("source_key must be non-empty")
        normalized_source_key = source_key.strip()
        existing = self.db.query(TribulationPillSettlement).filter_by(
            source_key=normalized_source_key
        ).one_or_none()
        if existing is not None:
            if existing.user_id != user_id:
                raise ValueError("TRIBULATION_PILL_SOURCE_KEY_CONFLICT")
            return SettlementResult(
                amount=existing.amount,
                remaining_pills=existing.remaining_pills,
                source_key=existing.source_key,
                already_settled=True,
                settlement_id=existing.id,
            )

        if amount == 0:
            return SettlementResult(
                amount=0,
                remaining_pills=self._owned_tribulation_pills(user_id),
                source_key=normalized_source_key,
            )

        try:
            transaction_context = self.db.begin_nested() if commit else nullcontext()
            with transaction_context:
                existing = self.db.query(TribulationPillSettlement).filter_by(
                    source_key=normalized_source_key
                ).with_for_update().one_or_none()
                if existing is not None:
                    if existing.user_id != user_id:
                        raise ValueError("TRIBULATION_PILL_SOURCE_KEY_CONFLICT")
                    return SettlementResult(
                        amount=existing.amount,
                        remaining_pills=existing.remaining_pills,
                        source_key=existing.source_key,
                        already_settled=True,
                        settlement_id=existing.id,
                    )

                BackpackService(self.db).consume_by_key(
                    user_id, "tribulation-pill", amount
                )
                remaining_pills = self._owned_tribulation_pills(user_id)
                settlement = TribulationPillSettlement(
                    user_id=user_id,
                    source_key=normalized_source_key,
                    amount=amount,
                    remaining_pills=remaining_pills,
                )
                self.db.add(settlement)
                self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(TribulationPillSettlement).filter_by(
                source_key=normalized_source_key, user_id=user_id
            ).one_or_none()
            if existing is not None:
                return SettlementResult(
                    amount=existing.amount,
                    remaining_pills=existing.remaining_pills,
                    source_key=existing.source_key,
                    already_settled=True,
                    settlement_id=existing.id,
                )
            raise

        if commit:
            self.db.commit()
        return SettlementResult(
            amount=amount,
            remaining_pills=remaining_pills,
            source_key=normalized_source_key,
            settlement_id=settlement.id,
        )

    @staticmethod
    def _bounded_tribulation_pill_count(value: int) -> int:
        try:
            requested = int(value or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("TRIBULATION_PILL_COUNT_INVALID") from exc
        return max(0, min(15, requested))

    @staticmethod
    def _tribulation_lock_message(lock_reason: str | None) -> str:
        compatibility_messages = {
            "FINAL_MINOR_STAGE_REQUIRED": "tribulation requires final minor stage threshold",
            "TRIBULATION_COOLDOWN_ACTIVE": "tribulation cooldown active",
            "ASCENDED": "tribulation already complete",
        }
        if lock_reason in compatibility_messages:
            return f"{lock_reason}: {compatibility_messages[lock_reason]}"
        return lock_reason or "TRIBULATION_LOCKED"

    def roll(self, probability: float):
        roll = random.random() * 100
        self._last_roll = roll
        return roll < probability

    def _readiness_breakdown(self, profile: CultivationProfile):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        habits = self.db.query(Habit).filter(Habit.user_id == profile.user_id, Habit.is_active.is_(True)).all()
        recent_tasks = self.db.query(Task).filter(Task.user_id == profile.user_id, Task.completed_at >= week_ago).all()
        habit_score = 50.0 if not habits else round(
            min(100, max((habit.streak or 0) for habit in habits) / 7 * 100), 2
        )
        task_score = 50.0 if not recent_tasks else round(
            sum(self._task_quality_score(task) for task in recent_tasks) / len(recent_tasks), 2
        )
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
    def _task_quality_score(task: Task) -> float:
        if task.deadline is None or task.completed_at is None:
            return 70.0
        completed_at = CultivationService._as_utc(task.completed_at)
        deadline = CultivationService._as_utc(task.deadline)
        if completed_at < deadline:
            return 100.0
        if completed_at == deadline:
            return 80.0
        return 50.0

    def _owned_tribulation_pills(self, user_id: UUID) -> int:
        return sum(
            item.quantity
            for item in BackpackService(self.db).get_items_by_key(
                user_id, "tribulation-pill"
            )
        )

    def _tribulation_prerequisites(self, profile: CultivationProfile):
        def item(key, label, required, current):
            return TribulationPrerequisite(
                key=key,
                label=label,
                required=required,
                current=current,
                satisfied=current >= required,
            )

        if profile.realm_key == "qi_refining":
            important_goal = self.db.query(Goal).filter(
                Goal.user_id == profile.user_id,
                Goal.status == TaskStatus.COMPLETED,
                Goal.progress >= 100,
                Goal.difficulty.in_(("hard", "very_hard")),
            ).count()
            habit_streak = max(
                [habit.streak or 0 for habit in self.db.query(Habit).filter(
                    Habit.user_id == profile.user_id,
                    Habit.is_active.is_(True),
                ).all()] or [0]
            )
            trial_star = self._highest_completed_trial_star(profile.user_id)
            return [
                item("important_goal", "重要目标", 1, important_goal),
                item("habit_streak", "连续习惯天数", 7, habit_streak),
                item("trial_star", "历练星级", 3, trial_star),
                item("mind_state", "心境", 60, profile.mind_state),
            ]

        if profile.realm_key == "foundation":
            phase_count = self.db.query(ProjectPhase).join(
                Project, Project.id == ProjectPhase.project_id
            ).filter(
                Project.user_id == profile.user_id,
                ProjectPhase.status == PhaseStatus.COMPLETED,
            ).count()
            habit_streak = max(
                [habit.streak or 0 for habit in self.db.query(Habit).filter(
                    Habit.user_id == profile.user_id,
                    Habit.is_active.is_(True),
                ).all()] or [0]
            )
            return [
                item("project_phase", "已完成项目阶段", 1, phase_count),
                item("habit_streak", "连续习惯天数", 14, habit_streak),
                item("trial_star", "历练星级", 5, self._highest_completed_trial_star(profile.user_id)),
                item("contribution", "宗门贡献", 300, profile.contribution),
            ]

        if profile.realm_key == "golden_core":
            highest_trial_star = self._highest_completed_trial_star(profile.user_id)
            sect_mainline = self._completed_sect_mainline(profile)
            long_term_goal = self.db.query(Goal).filter(
                Goal.user_id == profile.user_id,
                Goal.difficulty == "very_hard",
                Goal.progress >= 50,
                Goal.status != TaskStatus.CANCELLED,
            ).count()
            return [
                item("sect_mainline", "宗门主线", 1, sect_mainline),
                item("long_term_goal_stage", "长期目标阶段", 1, long_term_goal),
                item("high_star_trial", "高星历练", 7, highest_trial_star),
                item("realm_objective", "境界试炼目标", 1, self._completed_realm_objectives(profile)),
                item("mind_state", "心境", 70, profile.mind_state),
            ]

        highest_trial_star = self._highest_completed_trial_star(profile.user_id)
        sect_mainline = self._completed_sect_mainline(profile)
        long_term_goal = self.db.query(Goal).filter(
            Goal.user_id == profile.user_id,
            Goal.difficulty == "very_hard",
            Goal.progress >= 50,
            Goal.status != TaskStatus.CANCELLED,
        ).count()
        return [
            item("sect_mainline", "宗门主线", 1, sect_mainline),
            item("long_term_goal_stage", "长期目标阶段", 1, long_term_goal),
            item("high_star_trial", "高星历练", 7, highest_trial_star),
            item("realm_objective", "境界试炼目标", 1, self._completed_realm_objectives(profile)),
        ]

    @staticmethod
    def _next_tribulation_target(realm_key: str) -> str:
        index = REALM_ORDER.index(realm_key)
        return "ascension" if realm_key == "tribulation" else REALM_ORDER[index + 1]

    def _completed_sect_mainline(self, profile: CultivationProfile) -> int:
        required_star = 5 if profile.realm_key == "golden_core" else 7
        completed = self.db.query(SectAccessProgress).join(
            Sect, Sect.id == SectAccessProgress.sect_id
        ).join(
            SectMembership,
            (SectMembership.sect_id == Sect.id)
            & (SectMembership.user_id == profile.user_id),
        ).filter(
            SectAccessProgress.user_id == profile.user_id,
            SectAccessProgress.trial_confirmed.is_(True),
            SectMembership.status == "active",
            Sect.star >= required_star,
            Sect.trial_key.is_not(None),
        ).first()
        return int(completed is not None)

    def _realm_objective_source_keys(self, profile: CultivationProfile) -> tuple[str, ...]:
        target = self._next_tribulation_target(profile.realm_key)
        return (
            f"realm-objective:{target}",
            f"realm-objective:{profile.realm_key}:{target}",
            f"realm-objective:{target}:{profile.user_id}",
            f"realm-objective:{profile.realm_key}:{target}:{profile.user_id}",
        )

    def _completed_realm_objectives(self, profile: CultivationProfile) -> int:
        return self.db.query(CultivationLog).filter(
            CultivationLog.user_id == profile.user_id,
            CultivationLog.source == "trial_objective",
            CultivationLog.source_key.in_(self._realm_objective_source_keys(profile)),
        ).count()

    def _highest_completed_trial_star(self, user_id: UUID) -> int:
        value = self.db.query(Sect.star).join(
            SectAccessProgress, SectAccessProgress.sect_id == Sect.id
        ).filter(
            SectAccessProgress.user_id == user_id,
            SectAccessProgress.trial_confirmed.is_(True),
        ).order_by(Sect.star.desc()).first()
        return int(value[0]) if value else 0

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
    def _is_source_key_lock_error(exc: OperationalError) -> bool:
        original = getattr(exc, "orig", None)
        error_text = str(original or exc).lower()
        return any(
            marker in error_text
            for marker in (
                "database is locked",
                "database table is locked",
                "database schema is locked",
            )
        )

    @staticmethod
    def _is_database_lock_error(exc: OperationalError) -> bool:
        original = getattr(exc, "orig", None)
        error_text = str(original or exc).lower()
        return "database" in error_text and "locked" in error_text

    def _has_attempt_today(self, user_id: UUID) -> bool:
        return self.db.query(TribulationAttempt.id).filter(
            TribulationAttempt.user_id == user_id,
            TribulationAttempt.attempted_date == self._utc_today(),
        ).first() is not None

    @staticmethod
    def _realm_at_least(current_realm: str, required_realm: str) -> bool:
        if current_realm not in REALM_ORDER or required_realm not in REALM_ORDER:
            return False
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

    @staticmethod
    def _source_value(source: str) -> str:
        return getattr(source, "value", source)

    def _equipped_technique_bonus(self, user_id: UUID) -> float:
        return self.get_equipped_effects(user_id)["efficiency_bonus"]

    @staticmethod
    def _technique_effect_config(technique: Technique) -> dict:
        try:
            value = json.loads(technique.effect_config or "{}")
        except (TypeError, json.JSONDecodeError):
            value = {}
        if not isinstance(value, dict):
            return {}
        return value

    @staticmethod
    def _technique_conflict_tags(technique: Technique) -> set[str]:
        try:
            value = json.loads(technique.conflict_tags or "[]")
        except (TypeError, json.JSONDecodeError):
            value = []
        return set(value) if isinstance(value, list) else set()

    def get_equipped_effects(self, user_id: UUID) -> dict:
        rows = self.db.query(Technique, TechniqueSlot).join(
            TechniqueSlot, TechniqueSlot.technique_id == Technique.id
        ).filter(
            TechniqueSlot.user_id == user_id,
            TechniqueSlot.technique_id.is_not(None),
        ).all()
        learned_ids = {
            row.technique_id
            for row in self.db.query(LearnedTechnique).filter(
                LearnedTechnique.user_id == user_id
            ).all()
        }
        seen = set()
        effects = []
        bonus = 0.0
        for technique, slot in rows:
            if technique.id in seen or technique.id not in learned_ids:
                continue
            seen.add(technique.id)
            config = self._technique_effect_config(technique)
            technique_bonus = float(config.get(
                "efficiency_bonus",
                TECHNIQUE_EFFICIENCY_BONUSES.get(technique.technique_key, 0.0),
            ))
            bonus += technique_bonus
            effects.append({
                "technique_key": technique.technique_key,
                "slot_type": slot.slot_type,
                "efficiency_bonus": technique_bonus,
                "conflict_tags": sorted(self._technique_conflict_tags(technique)),
            })
        return {
            "efficiency_bonus": min(0.80, round(bonus, 4)),
            "techniques": effects,
        }

    def _calculate_efficiency(self, profile: CultivationProfile, user_id: UUID) -> float:
        aptitude_efficiency = min(0.60, 0.04 * math.sqrt(max(0, profile.aptitude_points)))
        technique_bonus = self._equipped_technique_bonus(user_id)
        sect_bonus = self.get_sect_effects(user_id).get("efficiency_bonus", 0.0)
        # Realm base is intentionally explicit even while all mortal realms
        # share 1.0; future realms can change without changing settlement math.
        realm_base = 1.0
        return round(realm_base + technique_bonus + aptitude_efficiency + sect_bonus, 4)

    def _daily_reward_event_count(self, user_id: UUID) -> int:
        start = datetime.combine(self._utc_today(), datetime.min.time(), tzinfo=timezone.utc)
        return self.db.query(CultivationLog.id).filter(
            CultivationLog.user_id == user_id,
            CultivationLog.created_at >= start,
        ).count()

    @staticmethod
    def _resource_deltas(source: str, content_star: int, quality: float, aptitude_allowed: bool):
        source_value = CultivationService._source_value(source)
        rule = CULTIVATION_RESOURCE_RULES.get(
            source_value,
            {"merit": 0, "contribution": 0, "mind_state_delta": 0},
        )
        star = max(1, min(5, int(content_star or 1)))
        merit = rule["merit"] * star
        contribution = rule["contribution"] * star
        mind_state_delta = rule["mind_state_delta"] * star
        if quality < 1.0 and mind_state_delta == 0:
            mind_state_delta = -1
        aptitude_points = star if aptitude_allowed else 0
        return merit, contribution, mind_state_delta, aptitude_points

    def settle_todo_reward(
        self,
        user_id: UUID,
        source: str,
        base_exp: int,
        difficulty: str,
        quality: float = 1.0,
        importance: float = 1.0,
        source_key: str | None = None,
        content_star: int = 1,
        apply_legacy_user_rewards: bool = True,
    ) -> RewardSettlement:
        if not source_key:
            return self._settle_todo_reward_in_session(
                user_id,
                source,
                base_exp,
                difficulty,
                quality,
                importance,
                None,
                content_star,
                apply_legacy_user_rewards,
            )
        for attempt in range(SOURCE_KEY_RETRY_COUNT):
            try:
                return self._settle_todo_reward_in_session(
                    user_id,
                    source,
                    base_exp,
                    difficulty,
                    quality,
                    importance,
                    source_key,
                    content_star,
                    apply_legacy_user_rewards,
                )
            except IntegrityError:
                self.db.expire_all()
                existing_log = self.db.query(CultivationLog).filter(
                    CultivationLog.source_key == source_key,
                    CultivationLog.user_id == user_id,
                ).one_or_none()
                if existing_log is None:
                    raise
                return self._settlement_from_existing_log(existing_log, user_id)
            except OperationalError as exc:
                if not self._is_source_key_lock_error(exc):
                    raise
                # The nested claim savepoint is already rolled back. Keep the
                # caller's todo transaction and use a fresh session only to see
                # whether another session committed this source key.
                self.db.expire_all()
                if attempt == SOURCE_KEY_RETRY_COUNT - 1:
                    existing_log = self._source_key_log_from_short_session(
                        source_key, user_id
                    )
                    if existing_log is not None:
                        return self._settlement_from_existing_log(existing_log, user_id)
                    raise
                time.sleep(SOURCE_KEY_RETRY_DELAY_SECONDS)
                existing_log = self._source_key_log_from_short_session(
                    source_key, user_id
                )
                if existing_log is not None:
                    return self._settlement_from_existing_log(existing_log, user_id)

        raise RuntimeError("source-key settlement retry loop exhausted")

    def _settle_todo_reward_in_session(
        self,
        user_id: UUID,
        source: str,
        base_exp: int,
        difficulty: str,
        quality: float,
        importance: float,
        source_key: str | None,
        content_star: int,
        apply_legacy_user_rewards: bool,
    ) -> RewardSettlement:
        try:
            difficulty_factor = DIFFICULTY_FACTORS[difficulty]
        except KeyError as exc:
            raise ValueError(f"Unknown difficulty: {difficulty}") from exc

        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        with (self.db.begin_nested() if source_key else nullcontext()):
            # Acquire both rows as writes, then refresh the ORM object. The
            # caller may have loaded User before another session committed.
            # SQLite serializes these writes; the outer retry handles a busy
            # snapshot while other dialects use their normal row locks.
            self.db.execute(update(CultivationProfile).where(
                CultivationProfile.user_id == user_id
            ).values(cultivation=CultivationProfile.cultivation))
            self.db.execute(update(User).where(User.id == user_id).values(
                level=User.level,
                experience=User.experience,
                coins=User.coins,
                total_coins_earned=User.total_coins_earned,
            ))
            self.db.refresh(user)
            legacy_level = user.level
            legacy_experience = user.experience
            profile = self.ensure_profile(user_id)
            if source_key:
                existing_log = self.db.query(CultivationLog).filter(
                    CultivationLog.source_key == source_key,
                    CultivationLog.user_id == user_id,
                ).one_or_none()
                if existing_log is not None:
                    return self._settlement_from_existing_log(existing_log, user_id)
            previous_efficiency = self._calculate_efficiency(profile, user_id)
            aptitude_allowed = self._daily_reward_event_count(user_id) < 8
            merit, contribution, mind_state_delta, aptitude_points = self._resource_deltas(
                source, content_star, quality, aptitude_allowed
            )
            cultivation = max(0, math.floor(
                base_exp
                * difficulty_factor
                * importance
                * previous_efficiency
                * quality
            ))
            stones = max(1, math.floor(cultivation * 0.6))
            log = CultivationLog(
                user_id=user_id,
                source=source,
                source_key=source_key,
                cultivation_delta=cultivation,
                spirit_stones_delta=stones,
                merit_delta=merit,
                contribution_delta=contribution,
                aptitude_points_delta=aptitude_points,
                mind_state_delta=mind_state_delta,
            )
            # Claim the source key before changing balances. A competing
            # session loses on the unique key and returns the committed log.
            self.db.add(log)
            self.db.flush()
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
            profile.merit += merit
            profile.contribution += contribution
            profile.aptitude_points += aptitude_points
            profile.mind_state = max(0, min(100, profile.mind_state + mind_state_delta))
            profile.cultivation_efficiency = self._calculate_efficiency(profile, user_id)
            log.efficiency_delta = round(
                profile.cultivation_efficiency - previous_efficiency, 4
            )
            log.efficiency = profile.cultivation_efficiency
            log.ready_for_tribulation = ready_for_tribulation

            essence = 0
            immortal_stones = 0
            if profile.realm_key == ASCENDED_REALM_KEY and source_key:
                essence = cultivation
                immortal_stones = stones
                immortal_profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none()
                if immortal_profile is not None:
                    immortal_profile.essence += essence
                    immortal_profile.immortal_stones += immortal_stones
                    self.db.add(CrossRealmSettlement(
                        user_id=user_id,
                        source_key=source_key,
                        request_key=f"cross-realm:{user_id}:{source_key}",
                        essence_delta=essence,
                        immortal_stones_delta=immortal_stones,
                    ))

            if apply_legacy_user_rewards:
                # Keep legacy user rewards in the same write transaction as
                # the cultivation log so independent sessions cannot
                # overwrite them.
                self.user_repo._update_experience_no_commit(user, cultivation)
                self.user_repo._update_coins_no_commit(user, stones)

        settlement = RewardSettlement(
            cultivation=cultivation,
            spirit_stones=stones,
            merit=merit,
            aptitude_points=aptitude_points,
            mind_state_delta=mind_state_delta,
            contribution=contribution,
            efficiency=profile.cultivation_efficiency,
            log_id=log.id,
            legacy_exp=cultivation,
            ready_for_tribulation=ready_for_tribulation,
            essence=essence,
            immortal_stones=immortal_stones,
        )
        settlement._legacy_level = legacy_level
        settlement._legacy_experience = legacy_experience
        return settlement

    def _source_key_log_from_short_session(
        self, source_key: str, user_id: UUID
    ) -> CultivationLog | None:
        short_session_factory = sessionmaker(
            bind=self.db.get_bind(),
            autocommit=False,
            autoflush=False,
        )
        short_session = short_session_factory()
        try:
            try:
                return short_session.query(CultivationLog).filter(
                    CultivationLog.source_key == source_key,
                    CultivationLog.user_id == user_id,
                ).one_or_none()
            except OperationalError as exc:
                if self._is_source_key_lock_error(exc):
                    return None
                raise
        finally:
            short_session.close()

    def _settlement_from_existing_log(
        self, log: CultivationLog, user_id: UUID
    ) -> RewardSettlement:
        profile = self.cultivation_repo.get_by_user(user_id)
        settlement = RewardSettlement(
            cultivation=log.cultivation_delta,
            spirit_stones=log.spirit_stones_delta,
            merit=log.merit_delta,
            aptitude_points=getattr(log, "aptitude_points_delta", 0) or 0,
            mind_state_delta=getattr(log, "mind_state_delta", 0) or 0,
            contribution=log.contribution_delta,
            efficiency=(
                log.efficiency
                if getattr(log, "efficiency", None) is not None
                else (profile.cultivation_efficiency if profile else 1.0)
            ),
            log_id=log.id,
            legacy_exp=log.cultivation_delta,
            ready_for_tribulation=bool(getattr(log, "ready_for_tribulation", False)),
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
