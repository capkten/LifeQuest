"""Idempotent localization migration for system-generated cultivation content."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.cultivation import CultivationProfile
from app.models.technique import Technique
from app.models.world import Npc, NpcEvent, Sect, WorldNode
from app.services.content_catalog import (
    EVENT_SUMMARY_LABELS,
    NPC_ROLE_LABELS,
    SECT_CATALOG,
    TECHNIQUE_CATALOG,
    WORLD_NODE_CATALOG,
)


FIXED_CORE_NPC_NAMES = {
    "sect master": "玄衡宗主",
    "transmission elder": "传法长老",
    "trial envoy": "入门使者",
}
FIXED_CORE_ROLES = tuple(FIXED_CORE_NPC_NAMES)


@dataclass(frozen=True)
class ContentBackfillSummary:
    world_nodes: int = 0
    sects: int = 0
    techniques: int = 0
    npcs: int = 0
    events: int = 0


class ContentLocalizationService:
    @staticmethod
    def _set_if_changed(record, field, value):
        if getattr(record, field) == value:
            return False
        setattr(record, field, value)
        return True

    @staticmethod
    def _legacy_sect_name(sect: Sect) -> str | None:
        if sect.sect_key not in SECT_CATALOG:
            return None
        ordinal = sect.sect_key.rsplit("-", 1)[-1]
        return f"{sect.star}-Star {sect.kind.title()} Sect {ordinal}"

    @staticmethod
    def _is_fixed_core_name_match(npc: Npc) -> bool:
        expected_name = FIXED_CORE_NPC_NAMES.get(npc.role)
        return expected_name is not None and npc.name == expected_name

    @staticmethod
    def backfill_system_content(db: Session) -> ContentBackfillSummary:
        counts = {
            "world_nodes": 0,
            "sects": 0,
            "techniques": 0,
            "npcs": 0,
            "events": 0,
        }

        sects = db.query(Sect).all()
        sects_by_id = {sect.id: sect for sect in sects}
        legacy_sect_names = {
            sect.id: ContentLocalizationService._legacy_sect_name(sect)
            for sect in sects
        }

        # The old implementation used is_generated=False for fixed cores, so
        # only a complete, ascended-user core set is trusted as legacy system data.
        legacy_core_candidates = {}
        for npc in db.query(Npc).filter(
            Npc.is_core.is_(True),
            Npc.is_generated.is_(False),
            Npc.sect_id.is_not(None),
            Npc.role.in_(FIXED_CORE_ROLES),
            Npc.population_index.is_(None),
            Npc.cultivation_locked.is_(True),
        ).all():
            sect = sects_by_id.get(npc.sect_id)
            legacy_sect_name = legacy_sect_names.get(npc.sect_id)
            if (
                sect is None
                or legacy_sect_name is None
                or npc.description != f"{legacy_sect_name}的固定核心人物。"
            ):
                continue
            key = (npc.user_id, npc.sect_id)
            legacy_core_candidates.setdefault(key, {}).setdefault(npc.role, []).append(npc)

        ascended_user_ids = {
            profile.user_id
            for profile in db.query(CultivationProfile).filter(
                CultivationProfile.realm_key == "ascended"
            ).all()
        }

        for node_key, content in WORLD_NODE_CATALOG.items():
            node = db.query(WorldNode).filter(WorldNode.node_key == node_key).first()
            if node is None:
                continue
            changed = False
            for field in ("name", "description", "required_realm"):
                changed = ContentLocalizationService._set_if_changed(node, field, content[field]) or changed
            counts["world_nodes"] += int(changed)

        for sect_key, content in SECT_CATALOG.items():
            sect = db.query(Sect).filter(Sect.sect_key == sect_key).first()
            if sect is None:
                continue
            changed = False
            for field in ("name", "kind", "task_preference", "core_legacy", "entry_realm", "trial_key"):
                changed = ContentLocalizationService._set_if_changed(sect, field, content[field]) or changed
            counts["sects"] += int(changed)

        for technique_key, content in TECHNIQUE_CATALOG.items():
            technique = db.query(Technique).filter(Technique.technique_key == technique_key).first()
            if technique is None:
                continue
            changed = False
            for field in (
                "name",
                "description",
                "technique_type",
                "required_realm",
                "spirit_stone_cost",
                "slot_count",
            ):
                changed = ContentLocalizationService._set_if_changed(technique, field, content[field]) or changed
            counts["techniques"] += int(changed)

        generated_roles = tuple(NPC_ROLE_LABELS)
        generated_npcs = db.query(Npc).filter(
            Npc.is_generated.is_(True),
            Npc.is_core.is_(False),
            Npc.sect_id.is_not(None),
            Npc.role.in_(generated_roles),
        ).all()
        for npc in generated_npcs:
            sect = sects_by_id.get(npc.sect_id)
            if sect is None:
                continue
            role_label = NPC_ROLE_LABELS[npc.role]
            if ContentLocalizationService._set_if_changed(
                npc, "description", f"{sect.name}的{role_label}。"
            ):
                counts["npcs"] += 1

        fixed_npcs = db.query(Npc).filter(
            Npc.is_core.is_(True),
            Npc.is_generated.is_(True),
            Npc.sect_id.is_not(None),
            Npc.role.in_(FIXED_CORE_ROLES),
            Npc.population_index.is_(None),
            Npc.cultivation_locked.is_(True),
        ).all()
        for npc in fixed_npcs:
            sect = sects_by_id.get(npc.sect_id)
            if (
                sect is None
                or sect.sect_key not in SECT_CATALOG
                or not ContentLocalizationService._is_fixed_core_name_match(npc)
            ):
                continue
            changed = ContentLocalizationService._set_if_changed(
                npc, "description", f"{sect.name}的固定核心人物。"
            )
            if changed:
                counts["npcs"] += 1

        for (user_id, sect_id), candidates_by_role in legacy_core_candidates.items():
            if user_id not in ascended_user_ids or set(candidates_by_role) != set(FIXED_CORE_ROLES):
                continue
            if any(len(candidates_by_role[role]) != 1 for role in FIXED_CORE_ROLES):
                continue
            sect = sects_by_id[sect_id]
            if any(
                not ContentLocalizationService._is_fixed_core_name_match(candidates_by_role[role][0])
                for role in FIXED_CORE_ROLES
            ):
                continue
            for role in FIXED_CORE_ROLES:
                npc = candidates_by_role[role][0]
                changed = ContentLocalizationService._set_if_changed(
                    npc, "description", f"{sect.name}的固定核心人物。"
                )
                changed = ContentLocalizationService._set_if_changed(
                    npc, "is_generated", True
                ) or changed
                if changed:
                    counts["npcs"] += 1

        # Historical cores become event targets in this same session.
        db.flush()

        old_event_summary = "Met ordinary disciple"
        events = db.query(NpcEvent).join(Npc, Npc.id == NpcEvent.npc_id).filter(
            Npc.is_generated.is_(True),
        ).all()
        for event in events:
            if event.event_key in EVENT_SUMMARY_LABELS:
                localized_summary = EVENT_SUMMARY_LABELS[event.event_key]
            elif event.summary == old_event_summary:
                localized_summary = EVENT_SUMMARY_LABELS["met"]
            else:
                continue
            if ContentLocalizationService._set_if_changed(event, "summary", localized_summary):
                counts["events"] += 1

        db.commit()
        return ContentBackfillSummary(**counts)
