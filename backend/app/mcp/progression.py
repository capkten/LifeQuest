"""MCP progression adapters; all progression and rewards remain in domain services."""
from typing import Optional

from app.services.cultivation import CultivationService
from app.services.ascension import AscensionService
from app.services.immortal import ImmortalService
from app.schemas.cultivation import NpcMeetRequest, TribulationAttemptRequest
from app.schemas.immortal import AscensionRequest, ImmortalActivityRequest, ImmortalCommissionRequest


def register(mcp, resolve_user_id, serialize, session_factory):
    def call(service, method, *args, **kwargs):
        with session_factory() as db:
            user_id = resolve_user_id(db)
            return serialize(getattr(service(db), method)(user_id, *args, **kwargs))

    @mcp.tool()
    def get_cultivation_overview() -> dict:
        """Get overview for the authenticated user through the cultivation service."""
        return call(CultivationService, "get_overview")

    @mcp.tool()
    def get_cultivation_world() -> dict:
        """Get world for the authenticated user through the cultivation service."""
        return call(CultivationService, "get_world")

    @mcp.tool()
    def list_sects(star: Optional[int] = None, kind: Optional[str] = None, task_preference: Optional[str] = None) -> list[dict]:
        """Get sects for the authenticated user through the cultivation service."""
        if star is not None and not 1 <= star <= 9:
            raise ValueError("star must be between 1 and 9")
        return call(CultivationService, "get_sects", star=star, kind=kind, task_preference=task_preference)

    @mcp.tool()
    def join_sect(sect_key: str) -> dict:
        """Join sect for the authenticated user through the cultivation service."""
        return call(CultivationService, "join_sect", sect_key)

    @mcp.tool()
    def leave_sect() -> dict:
        """Leave sect for the authenticated user through the cultivation service."""
        return call(CultivationService, "leave_sect")

    @mcp.tool()
    def contact_sect_messenger(sect_key: str) -> dict:
        """Contact sect messenger for the authenticated user through the cultivation service."""
        return call(CultivationService, "contact_sect_messenger", sect_key)

    @mcp.tool()
    def complete_sect_trial(sect_key: str) -> dict:
        """Complete sect trial for the authenticated user through the cultivation service."""
        return call(CultivationService, "complete_sect_trial", sect_key)

    @mcp.tool()
    def get_sect_access(sect_key: str) -> dict:
        """Get sect access for the authenticated user through the cultivation service."""
        return call(CultivationService, "get_sect_access", sect_key)

    @mcp.tool()
    def update_trial_objective(sect_key: str, objective_key: str, completed: bool = True) -> dict:
        """Update trial objective for the authenticated user through the cultivation service."""
        return call(CultivationService, "update_trial_objective", sect_key, objective_key, completed)

    @mcp.tool()
    def evaluate_hidden_sects() -> list[dict]:
        """Evaluate hidden sects for the authenticated user through the cultivation service."""
        return call(CultivationService, "evaluate_hidden_sects")

    @mcp.tool()
    def complete_world_node(node_key: str) -> dict:
        """Complete world node for the authenticated user through the cultivation service."""
        return call(CultivationService, "complete_world_node", node_key)

    @mcp.tool()
    def get_techniques() -> dict:
        """Get techniques for the authenticated user through the cultivation service."""
        return call(CultivationService, "get_techniques")

    @mcp.tool()
    def learn_technique(technique_key: str) -> dict:
        """Learn technique for the authenticated user through the cultivation service."""
        return call(CultivationService, "learn_technique", technique_key)

    @mcp.tool()
    def purchase_technique_slot(slot_type: str) -> dict:
        """Purchase slot for the authenticated user through the cultivation service."""
        return call(CultivationService, "purchase_slot", slot_type)

    @mcp.tool()
    def update_technique_loadout(loadout: dict) -> dict:
        """Update loadout for the authenticated user through the cultivation service."""
        return call(CultivationService, "update_loadout", loadout)

    @mcp.tool()
    def list_npcs() -> dict:
        """Get npcs for the authenticated user through the cultivation service."""
        return call(CultivationService, "get_npcs")

    @mcp.tool()
    def meet_npc(sect_key: str, population_index: int) -> dict:
        """Meet a sect NPC at the specified nonnegative population index."""
        payload = NpcMeetRequest(sect_key=sect_key, population_index=population_index)
        return call(CultivationService, "meet_npc", payload.sect_key, payload.population_index)

    @mcp.tool()
    def get_tribulation_preview(pill_count: int = 0) -> dict:
        """Preview breakthrough prerequisites, probability, cost and cooldown."""
        payload = TribulationAttemptRequest(pill_count=pill_count)
        if payload.pill_count > 15:
            raise ValueError("pill_count must be between 0 and 15")
        return call(CultivationService, "get_tribulation_preview", payload.pill_count)

    @mcp.tool()
    def attempt_tribulation(pill_count: int = 0) -> dict:
        """Attempt a breakthrough, consuming pills; failure can lose cultivation."""
        payload = TribulationAttemptRequest(pill_count=pill_count)
        return call(CultivationService, "attempt_tribulation", payload.pill_count)

    @mcp.tool()
    def ascend(request_key: str) -> dict:
        """Ascend when prerequisites hold; reuse request_key to safely retry."""
        payload = AscensionRequest(request_key=request_key)
        return call(AscensionService, "ascend", payload.request_key)

    @mcp.tool()
    def get_immortal_overview() -> dict:
        """Read the authenticated user's immortal regions, activities and goals."""
        return call(ImmortalService, "get_overview")

    @mcp.tool()
    def run_immortal_activity(activity_id: str, request_key: str) -> dict:
        """Run an immortal activity; reuse request_key to prevent duplicate rewards."""
        payload = ImmortalActivityRequest(activity_id=activity_id, request_key=request_key)
        return call(ImmortalService, "run_activity", payload.activity_id, payload.request_key)

    @mcp.tool()
    def advance_immortal_stage(request_key: str) -> dict:
        """Advance an immortal stage when goals hold; reuse request_key on retries."""
        payload = AscensionRequest(request_key=request_key)
        return call(ImmortalService, "advance_stage", payload.request_key)

    @mcp.tool()
    def commission_immortal_official(official_key: str, request_key: str) -> dict:
        """Commission an official; reuse request_key to avoid duplicate costs/rewards."""
        payload = ImmortalCommissionRequest(official_key=official_key, request_key=request_key)
        return call(ImmortalService, "commission", payload.official_key, payload.request_key)
