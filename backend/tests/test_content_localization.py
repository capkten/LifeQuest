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


def test_backfill_migrates_real_legacy_fixed_core_template_before_sect_rename(isolated_db):
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
    sect.name = "1-Star Normal Sect 1"
    CultivationService(isolated_db).set_realm(user.id, "ascended", 1, 0)
    legacy_description = f"{sect.name}的固定核心人物。"
    cores = [
        Npc(
            user_id=user.id,
            sect_id=sect.id,
            name=name,
            role=role,
            description=legacy_description,
            is_core=True,
            is_generated=False,
            cultivation_locked=True,
        )
        for role, name in (
            ("sect master", "玄衡宗主"),
            ("transmission elder", "传法长老"),
            ("trial envoy", "入门使者"),
        )
    ]
    isolated_db.add_all(cores)
    isolated_db.flush()
    isolated_db.add(NpcEvent(
        user_id=user.id,
        npc_id=cores[0].id,
        event_key="met",
        summary="Met ordinary disciple",
    ))
    isolated_db.commit()

    summary = ContentLocalizationService.backfill_system_content(isolated_db)

    isolated_db.expire_all()
    refreshed = isolated_db.query(Npc).filter_by(id=cores[0].id).one()
    assert refreshed.description == "赤霞门的固定核心人物。"
    assert refreshed.name == "玄衡宗主"
    assert refreshed.role == "sect master"
    assert refreshed.sect_id == sect.id
    assert summary.npcs == 3
    assert isolated_db.query(Sect).filter_by(id=sect.id).one().name == "赤霞门"
    event = isolated_db.query(NpcEvent).filter_by(npc_id=cores[0].id).one()
    assert event.user_id == user.id
    assert event.summary == "与普通弟子相遇"


def test_backfill_skips_complete_legacy_shape_without_ascended_proof(isolated_db):
    from app.services.content_localization import ContentLocalizationService
    from app.services.cultivation import CultivationService

    user = User(
        username=f"forged-core-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    isolated_db.add(user)
    isolated_db.commit()

    CultivationService.seed_world(isolated_db)
    sect = isolated_db.query(Sect).filter_by(sect_key="sect-1-normal-1").one()
    sect.name = "1-Star Normal Sect 1"
    cores = [
        Npc(
            user_id=user.id,
            sect_id=sect.id,
            name=name,
            role=role,
            description=f"{sect.name}的固定核心人物。",
            is_core=True,
            is_generated=False,
            cultivation_locked=True,
        )
        for role, name in (
            ("sect master", "玄衡宗主"),
            ("transmission elder", "传法长老"),
            ("trial envoy", "入门使者"),
        )
    ]
    isolated_db.add_all(cores)
    isolated_db.commit()

    ContentLocalizationService.backfill_system_content(isolated_db)

    assert isolated_db.query(Npc).filter(
        Npc.user_id == user.id,
        Npc.is_core.is_(True),
        Npc.is_generated.is_(False),
    ).count() == 3
    assert all(npc.description == "1-Star Normal Sect 1的固定核心人物。" for npc in cores)


def test_backfill_skips_ambiguous_legacy_fixed_core_set(isolated_db):
    from app.services.content_localization import ContentLocalizationService
    from app.services.cultivation import CultivationService

    user = User(
        username=f"ambiguous-core-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    isolated_db.add(user)
    isolated_db.commit()

    CultivationService.seed_world(isolated_db)
    sect = isolated_db.query(Sect).filter_by(sect_key="sect-1-normal-1").one()
    sect.name = "1-Star Normal Sect 1"
    CultivationService(isolated_db).set_realm(user.id, "ascended", 1, 0)
    cores = [
        Npc(
            user_id=user.id,
            sect_id=sect.id,
            name="玄衡宗主（自建）",
            role="sect master",
            description=f"{sect.name}的固定核心人物。",
            is_core=True,
            is_generated=False,
            cultivation_locked=True,
        ),
        Npc(
            user_id=user.id,
            sect_id=sect.id,
            name="玄衡宗主",
            role="sect master",
            description=f"{sect.name}的固定核心人物。",
            is_core=True,
            is_generated=False,
            cultivation_locked=True,
        ),
        Npc(
            user_id=user.id,
            sect_id=sect.id,
            name="传法长老",
            role="transmission elder",
            description=f"{sect.name}的固定核心人物。",
            is_core=True,
            is_generated=False,
            cultivation_locked=True,
        ),
        Npc(
            user_id=user.id,
            sect_id=sect.id,
            name="入门使者",
            role="trial envoy",
            description=f"{sect.name}的固定核心人物。",
            is_core=True,
            is_generated=False,
            cultivation_locked=True,
        ),
    ]
    isolated_db.add_all(cores)
    isolated_db.commit()

    ContentLocalizationService.backfill_system_content(isolated_db)

    assert isolated_db.query(Npc).filter(
        Npc.user_id == user.id,
        Npc.is_core.is_(True),
        Npc.is_generated.is_(False),
    ).count() == 4
    assert all(npc.description == "1-Star Normal Sect 1的固定核心人物。" for npc in cores)


def test_backfill_does_not_match_user_core_npc_with_similar_flags(isolated_db):
    from app.services.content_localization import ContentLocalizationService
    from app.services.cultivation import CultivationService

    user = User(
        username=f"core-collision-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    isolated_db.add(user)
    isolated_db.commit()

    CultivationService.seed_world(isolated_db)
    sect = isolated_db.query(Sect).filter_by(sect_key="sect-1-normal-1").one()
    sect.name = "1-Star Normal Sect 1"
    user_npc = Npc(
        user_id=user.id,
        sect_id=sect.id,
        name="自建宗主",
        role="sect master",
        description="用户保留的核心 NPC 描述",
        is_core=True,
        is_generated=False,
        cultivation=731,
        cultivation_locked=False,
    )
    same_name_user_npc = Npc(
        user_id=user.id,
        sect_id=sect.id,
        name="玄衡宗主",
        role="sect master",
        description="A fixed core character.",
        is_core=True,
        is_generated=False,
        cultivation=732,
        cultivation_locked=True,
    )
    isolated_db.add_all([user_npc, same_name_user_npc])
    isolated_db.flush()
    isolated_db.add(NpcEvent(
        user_id=user.id,
        npc_id=same_name_user_npc.id,
        event_key="custom-core-event",
        summary="用户自定义核心事件",
    ))
    isolated_db.commit()

    ContentLocalizationService.backfill_system_content(isolated_db)

    isolated_db.expire_all()
    refreshed = isolated_db.query(Npc).filter_by(id=user_npc.id).one()
    assert refreshed.name == "自建宗主"
    assert refreshed.role == "sect master"
    assert refreshed.description == "用户保留的核心 NPC 描述"
    assert refreshed.sect_id == sect.id
    assert refreshed.is_core is True
    assert refreshed.is_generated is False
    assert refreshed.cultivation == 731
    assert refreshed.cultivation_locked is False
    same_name_refreshed = isolated_db.query(Npc).filter_by(id=same_name_user_npc.id).one()
    assert same_name_refreshed.name == "玄衡宗主"
    assert same_name_refreshed.description == "A fixed core character."
    assert same_name_refreshed.sect_id == sect.id
    assert same_name_refreshed.cultivation == 732
    event = isolated_db.query(NpcEvent).filter_by(npc_id=same_name_user_npc.id).one()
    assert event.user_id == user.id
    assert event.summary == "用户自定义核心事件"


def test_new_fixed_core_npcs_use_system_generation_identity(isolated_db):
    from app.services.cultivation import CultivationService

    user = User(
        username=f"new-core-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    isolated_db.add(user)
    isolated_db.commit()

    service = CultivationService(isolated_db)
    service.set_realm(user.id, "ascended", 1, 0)
    response = service.get_npcs(user.id)

    assert len(response.fixed_core) == 270
    assert isolated_db.query(Npc).filter(
        Npc.user_id == user.id,
        Npc.is_core.is_(True),
        Npc.is_generated.is_(False),
    ).count() == 0


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


def test_repeated_seed_and_backfill_preserve_rows_relationships_and_existing_fields(legacy_content):
    from app.services.content_localization import ContentLocalizationService
    from app.services.cultivation import CultivationService

    db, user, node, sect, technique, generated_npc, user_npc = legacy_content
    CultivationService.seed_world(db)
    ContentLocalizationService.backfill_system_content(db)

    counts = {
        "world_nodes": db.query(WorldNode).count(),
        "sects": db.query(Sect).count(),
        "techniques": db.query(Technique).count(),
        "npcs": db.query(Npc).count(),
        "events": db.query(NpcEvent).count(),
    }
    snapshot = {
        "node": (node.id, node.name, node.description, node.required_realm, node.sort_order, node.is_hidden),
        "sect": (sect.id, sect.name, sect.world_node_id, sect.entry_realm),
        "technique": (technique.id, technique.name, technique.description),
        "generated_npc": (generated_npc.id, generated_npc.user_id, generated_npc.sect_id, generated_npc.name, generated_npc.description),
        "user_npc": (user_npc.id, user_npc.user_id, user_npc.sect_id, user_npc.name, user_npc.role, user_npc.description),
        "events": [
            (event.id, event.user_id, event.npc_id, event.event_key, event.summary)
            for event in db.query(NpcEvent).order_by(NpcEvent.id).all()
        ],
    }

    CultivationService.seed_world(db)
    second = ContentLocalizationService.backfill_system_content(db)

    assert second.world_nodes == 0
    assert second.sects == 0
    assert second.techniques == 0
    assert second.npcs == 0
    assert second.events == 0
    assert {
        "world_nodes": db.query(WorldNode).count(),
        "sects": db.query(Sect).count(),
        "techniques": db.query(Technique).count(),
        "npcs": db.query(Npc).count(),
        "events": db.query(NpcEvent).count(),
    } == counts
    refreshed_node = db.query(WorldNode).filter_by(id=node.id).one()
    assert (
        refreshed_node.id,
        refreshed_node.name,
        refreshed_node.description,
        refreshed_node.required_realm,
        refreshed_node.sort_order,
        refreshed_node.is_hidden,
    ) == snapshot["node"]
    assert (sect.id, sect.name, sect.world_node_id, sect.entry_realm) == snapshot["sect"]
    assert (technique.id, technique.name, technique.description) == snapshot["technique"]
    assert (generated_npc.id, generated_npc.user_id, generated_npc.sect_id, generated_npc.name, generated_npc.description) == snapshot["generated_npc"]
    assert (user_npc.id, user_npc.user_id, user_npc.sect_id, user_npc.name, user_npc.role, user_npc.description) == snapshot["user_npc"]
    assert [
        (event.id, event.user_id, event.npc_id, event.event_key, event.summary)
        for event in db.query(NpcEvent).order_by(NpcEvent.id).all()
    ] == snapshot["events"]


def test_seed_then_backfill_is_safe_for_an_empty_database(isolated_db):
    from app.services.content_localization import ContentLocalizationService
    from app.services.cultivation import CultivationService

    CultivationService.seed_world(isolated_db)
    first = ContentLocalizationService.backfill_system_content(isolated_db)
    CultivationService.seed_world(isolated_db)
    second = ContentLocalizationService.backfill_system_content(isolated_db)

    assert first == second
    assert first.world_nodes == 0
    assert first.sects == 0
    assert first.techniques == 0
    assert first.npcs == 0
    assert first.events == 0
    assert isolated_db.query(WorldNode).count() == 9
    assert isolated_db.query(Sect).count() == 90
    assert isolated_db.query(Technique).count() == 3


def test_startup_runs_localization_after_seed_and_closes_session(monkeypatch):
    from app import main
    from app.services.achievement import AchievementService
    from app.services.content_localization import ContentLocalizationService
    from app.services.cultivation import CultivationService
    from app.services.finance import FinanceService
    from app.services.title import TitleService

    calls = []

    class FakeSession:
        def close(self):
            calls.append("close")

    monkeypatch.setattr(main, "_migrate_columns", lambda: calls.append("columns"))
    monkeypatch.setattr(main, "_migrate_note_data", lambda: calls.append("notes"))
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(AchievementService, "seed_achievements", lambda self: calls.append("achievements"))
    monkeypatch.setattr(TitleService, "seed_titles", lambda self: calls.append("titles"))
    monkeypatch.setattr(FinanceService, "seed_categories", lambda db: calls.append("finance"))
    monkeypatch.setattr(CultivationService, "seed_world", lambda db: calls.append("seed"))
    monkeypatch.setattr(ContentLocalizationService, "backfill_system_content", lambda db: calls.append("backfill"))

    main.startup_event()

    assert calls == [
        "columns",
        "notes",
        "achievements",
        "titles",
        "finance",
        "seed",
        "backfill",
        "close",
    ]
