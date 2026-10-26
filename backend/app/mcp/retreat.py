"""Read adapters for existing focus sessions and encounter collection."""
from app.services.cultivation_retreat import CultivationRetreatService


def register(mcp, resolve_user_id, serialize, session_factory):
    tools = {}

    def tool(fn):
        tools[fn.__name__] = fn
        return mcp.tool()(fn)

    @tool
    def get_focus_session_history(limit: int = 20, offset: int = 0) -> list[dict]:
        """Read owned focus session history, including settled rewards; limit 1..100."""
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1..100 and offset nonnegative")
        with session_factory() as db:
            user_id = resolve_user_id(db)
            return serialize(CultivationRetreatService.get_history(db, user_id, limit, offset))

    @tool
    def get_encounter_catalog() -> list[dict]:
        """Read encounter stories and the authenticated user's unlock counts."""
        with session_factory() as db:
            user_id = resolve_user_id(db)
            return serialize(CultivationRetreatService.get_catalog(db, user_id))

    return tools
