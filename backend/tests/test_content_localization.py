from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.technique import Technique
from app.models.user import User
from app.models.world import Npc, NpcEvent, Sect, WorldNode


@pytest.fixture
def isolated_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'content-localization.sqlite'}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def legacy_content(isolated_db):
    user = User(
        username=f"localization-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    isolated_db.add(user)
    isolated_db.flush()

    node = WorldNode(
        node_key="mortal-domain-1",
        name="Mortal Domain 1",
        description="Cultivation region 1",
        required_realm=None,
        sort_order=1,
        is_hidden=False,
    )
    isolated_db.add(node)
    isolated_db.flush()
    sect = Sect(
        sect_key="sect-1-normal-1",
        name="1-Star Normal Sect 1",
        star=1,
        kind="normal",
        task_preference="discipline-1",
        core_legacy="Legacy of the 1-star sect",
        entry_realm="foundation",
        trial_key="trial-1-1",
        world_node_id=node.id,
    )
    technique = Technique(
        technique_key="steady-breath",
        name="Steady Breath",
        description="A mind cultivation technique.",
        technique_type="mind",
        required_realm="qi_refining",
        spirit_stone_cost=10,
        slot_count=1,
    )
    isolated_db.add_all([sect, technique])
    isolated_db.flush()

    generated_npc = Npc(
        user_id=user.id,
        sect_id=sect.id,
        name="沈清衡",
        role="ordinary disciple",
        description=f"A disciple of {sect.name}.",
        is_core=False,
        population_index=1,
        is_generated=True,
        cultivation=20,
        cultivation_locked=False,
    )
    user_npc = Npc(
        user_id=user.id,
        sect_id=sect.id,
        name="我的NPC",
        role="custom guide",
        description="用户自定义描述",
        is_core=False,
        population_index=None,
        is_generated=False,
        cultivation=0,
        cultivation_locked=False,
    )
    isolated_db.add_all([generated_npc, user_npc])
    isolated_db.flush()
    isolated_db.add_all([
        NpcEvent(
            user_id=user.id,
            npc_id=generated_npc.id,
            event_key="met",
            summary="Met ordinary disciple",
        ),
        NpcEvent(
            user_id=user.id,
            npc_id=user_npc.id,
            event_key="met",
            summary="用户自定义事件",
        ),
    ])
    isolated_db.commit()
    return isolated_db, user, node, sect, technique, generated_npc, user_npc


def test_backfill_updates_known_system_rows_without_overwriting_user_content(legacy_content):
    from app.services.content_localization import ContentLocalizationService

    db, user, node, sect, technique, generated_npc, user_npc = legacy_content
    summary = ContentLocalizationService.backfill_system_content(db)

    db.expire_all()
    assert db.query(WorldNode).filter_by(node_key="mortal-domain-1").one().name == "青云凡域"
    assert db.query(Technique).filter_by(technique_key="steady-breath").one().name == "凝息诀"
    assert db.query(Npc).filter_by(id=generated_npc.id).one().description == "赤霞门的普通弟子。"
    assert db.query(Npc).filter_by(id=user_npc.id).one().description == "用户自定义描述"
    assert db.query(NpcEvent).filter_by(npc_id=generated_npc.id, event_key="met").one().summary == "与普通弟子相遇"
    assert db.query(NpcEvent).filter_by(npc_id=user_npc.id, event_key="met").one().summary == "用户自定义事件"
    assert summary.world_nodes >= 1


def test_backfill_is_idempotent_and_preserves_system_relationships(legacy_content):
    from app.services.content_localization import ContentLocalizationService

    db, user, node, sect, technique, generated_npc, user_npc = legacy_content
    original_ids = {
        "node": node.id,
        "sect": sect.id,
        "technique": technique.id,
        "npc": generated_npc.id,
        "npc_sect": generated_npc.sect_id,
    }

    first = ContentLocalizationService.backfill_system_content(db)
    second = ContentLocalizationService.backfill_system_content(db)

    assert first.world_nodes == 1
    assert first.sects == 1
    assert first.techniques == 1
    assert first.npcs == 1
    assert first.events == 1
    assert second == type(first)(world_nodes=0, sects=0, techniques=0, npcs=0, events=0)
    assert db.query(WorldNode).count() == 1
    assert db.query(Sect).count() == 1
    assert db.query(Technique).count() == 1
    assert db.query(Npc).count() == 2
    assert db.query(NpcEvent).count() == 2
    assert db.query(WorldNode).one().id == original_ids["node"]
    assert db.query(Sect).one().id == original_ids["sect"]
    assert db.query(Technique).one().id == original_ids["technique"]
    assert db.query(Npc).filter_by(id=original_ids["npc"]).one().sect_id == original_ids["npc_sect"]


def test_backfill_updates_fixed_core_npcs_by_role_without_replacing_their_relation(isolated_db):
    from app.services.content_localization import ContentLocalizationService

    user = User(
        username=f"core-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    isolated_db.add(user)
    isolated_db.commit()
    from app.services.cultivation import CultivationService

    CultivationService.seed_world(isolated_db)
    sect = isolated_db.query(Sect).filter_by(sect_key="sect-1-normal-1").one()
    core = Npc(
        user_id=user.id,
        sect_id=sect.id,
        name="既有核心 NPC",
        role="sect master",
        description="A fixed core character.",
        is_core=True,
        is_generated=False,
        cultivation_locked=True,
    )
    isolated_db.add(core)
    isolated_db.commit()

    summary = ContentLocalizationService.backfill_system_content(isolated_db)

    isolated_db.expire_all()
    refreshed = isolated_db.query(Npc).filter_by(id=core.id).one()
    assert refreshed.description == "赤霞门的固定核心人物。"
    assert refreshed.name == "既有核心 NPC"
    assert refreshed.role == "sect master"
    assert refreshed.sect_id == sect.id
    assert summary.npcs == 1


def test_backfill_is_safe_for_an_empty_database(isolated_db):
    from app.services.content_localization import ContentBackfillSummary, ContentLocalizationService

    assert ContentLocalizationService.backfill_system_content(isolated_db) == ContentBackfillSummary(
        world_nodes=0,
        sects=0,
        techniques=0,
        npcs=0,
        events=0,
    )


def test_seed_world_uses_chinese_catalog_for_fresh_database(isolated_db):
    from app.services.cultivation import CultivationService

    CultivationService.seed_world(isolated_db)

    assert isolated_db.query(WorldNode).filter_by(node_key="mortal-domain-1").one().name == "青云凡域"
    assert isolated_db.query(Sect).filter_by(sect_key="sect-1-normal-1").one().name == "赤霞门"
    assert isolated_db.query(Technique).filter_by(technique_key="steady-breath").one().name == "凝息诀"
    assert isolated_db.query(WorldNode).count() == 9
    assert isolated_db.query(Sect).count() == 90
    assert isolated_db.query(Technique).count() == 3
