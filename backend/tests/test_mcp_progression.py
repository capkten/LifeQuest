from uuid import uuid4

import pytest

from app.database import Base
from app.models.user import User
from app.services.cultivation import CultivationService
import mcp_server


@pytest.fixture
def tools(db_session):
    from app.mcp.progression import register
    Base.metadata.create_all(db_session.bind)
    user = User(username=uuid4().hex, email=f"{uuid4().hex}@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.commit()
    registry = {}
    class Registry:
        def tool(self):
            def add(fn):
                registry[fn.__name__] = fn
                return fn
            return add
    user_id = user.id
    register(Registry(), lambda db: user_id, mcp_server._serialize, lambda: db_session)
    from types import SimpleNamespace
    yield registry, db_session, SimpleNamespace(id=user_id)
    db_session.rollback()
    Base.metadata.drop_all(db_session.bind)


def test_progression_registry_and_real_preconditions(tools):
    registry, db, user = tools
    assert len(registry) == 24
    assert "set_realm" not in registry
    overview = registry["get_cultivation_overview"]()
    assert overview["realm_key"]
    assert registry["get_cultivation_world"]()
    assert registry["get_techniques"]()
    with pytest.raises(PermissionError):
        registry["get_immortal_overview"]()
    with pytest.raises(PermissionError):
        registry["ascend"]("test-ascend")
    with pytest.raises(Exception):
        registry["attempt_tribulation"]()


def test_progression_validates_request_keys_and_pills(tools):
    registry, _, _ = tools
    for name in ("ascend", "advance_immortal_stage"):
        with pytest.raises(ValueError):
            registry[name]("")
    with pytest.raises(ValueError):
        registry["get_tribulation_preview"](-1)
    with pytest.raises(ValueError):
        registry["meet_npc"]("sect", -1)


def test_immortal_success_and_request_replay(tools):
    from app.models.immortal import ImmortalActivityRecord, ImmortalOfficialCommission, ImmortalProfile
    registry, db, user = tools
    db.add(ImmortalProfile(user_id=user.id, essence=50))
    db.commit()
    for name, args in (("run_immortal_activity", ("daily-cultivation", "activity-once")),
                       ("commission_immortal_official", ("gatekeeper", "official-once")),
                       ("advance_immortal_stage", ("stage-once",))):
        first = registry[name](*args)
        assert registry[name](*args) == first
    assert db.query(ImmortalActivityRecord).filter_by(user_id=user.id).count() == 1
    assert db.query(ImmortalOfficialCommission).filter_by(user_id=user.id).count() == 1
    assert registry["get_immortal_overview"]()["stage"] == 2


def test_ascension_replay_cannot_read_another_users_record(tools):
    from app.models.cultivation import CultivationProfile
    registry, db, user = tools
    db.add(CultivationProfile(user_id=user.id, realm_key="ascended"))
    db.commit()
    first = registry["ascend"]("global-key")
    assert registry["ascend"]("global-key") == first
    other = User(username=uuid4().hex, email=f"{uuid4().hex}@example.com", password_hash="hashed")
    db.add(other)
    db.commit()
    from app.services.ascension import AscensionService
    with pytest.raises(ValueError, match="REQUEST_KEY_UNAVAILABLE"):
        AscensionService(db).ascend(other.id, "global-key")


def test_sect_and_npc_progression_use_real_service_rules(tools):
    registry, db, user = tools
    from app.models.world import Sect
    service = CultivationService(db)
    service.seed_world(db)
    sect = db.query(Sect).filter_by(star=1, kind="normal").first()
    key = sect.sect_key
    with pytest.raises(PermissionError):
        registry["join_sect"](key)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    db.commit()
    registry["contact_sect_messenger"](key)
    registry["update_trial_objective"](key, "three_star_expedition")
    registry["complete_sect_trial"](key)
    assert registry["join_sect"](key)["status"] == "active"
    first = registry["meet_npc"](key, 0)
    assert registry["meet_npc"](key, 0)["id"] == first["id"]
    assert registry["list_npcs"]()["recently_met"]
    assert registry["leave_sect"]()


def test_modules_register_real_fastmcp_json_schemas():
    from mcp.server.fastmcp import FastMCP
    from app.mcp.progression import register
    from app.mcp.collaboration import register as register_collaboration
    server = FastMCP("progression-test")
    register(server, lambda db: None, mcp_server._serialize, lambda: None)
    register_collaboration(server, lambda db: None, mcp_server._serialize, lambda: None)
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    assert len(tools) == 29
    assert tools["ascend"].parameters["required"] == ["request_key"]
    assert tools["add_notebook_member"].parameters["properties"]["role"]["enum"] == ["editor", "viewer"]
    for tool in tools.values():
        assert "user_id" not in tool.parameters.get("properties", {})


def test_json_loadout_uuid_strings_are_accepted_and_validated(tools):
    from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
    registry, db, user = tools
    service = CultivationService(db)
    service.seed_world(db)
    service.ensure_profile(user.id).realm_key = "foundation"
    technique = db.query(Technique).filter_by(technique_key="sword-heart").one()
    technique_id = str(technique.id)
    db.add_all([TechniqueSlot(user_id=user.id, slot_type="main", slot_index=0),
                LearnedTechnique(user_id=user.id, technique_id=technique.id)])
    db.commit()
    result = registry["update_technique_loadout"]({"main": technique_id})
    assert result["slot_assignments"]["main"] == [technique_id]
    # The REST request model sends the same string values to the shared service.
    from app.schemas.cultivation import LoadoutRequest
    payload = LoadoutRequest(loadout={"main": [technique_id]})
    assert str(service.update_loadout(user.id, payload.loadout).slot_assignments["main"][0]) == technique_id
    with pytest.raises(ValueError, match="INVALID_TECHNIQUE_ID"):
        registry["update_technique_loadout"]({"main": "invalid"})
    with pytest.raises(ValueError, match="INVALID_SLOT_TYPE"):
        registry["update_technique_loadout"]({"invalid": technique_id})
