import math
from datetime import date

import pytest
from uuid import UUID, uuid4


def _register_and_login(client, username=None):
    username = username or f"cultivation-api-{uuid4().hex}"
    email = f"{uuid4().hex}@example.com"
    assert client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "testpassword123"},
    ).status_code == 200
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "testpassword123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return _register_and_login(client)


@pytest.fixture
def user(db_session):
    from app.database import Base
    from app.models.user import User
    from tests.conftest import engine as test_engine

    Base.metadata.create_all(bind=test_engine)
    user = User(
        username=f"cultivation-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _prepare_npc_meeting(service, user_id):
    from app.models.world import SectAccessProgress

    service.seed_world(service.db)
    service.set_realm(user_id, "foundation", 1, 0)
    sect = service._get_sect("sect-1-normal-1")
    access = service.db.query(SectAccessProgress).filter_by(user_id=user_id, sect_id=sect.id).first()
    if access is None:
        service.db.add(SectAccessProgress(user_id=user_id, sect_id=sect.id, messenger_contacted=True))
        service.db.commit()


def test_cultivation_tables_are_registered(db_session):
    from app.models.cultivation import CultivationProfile, CultivationLog
    from app.models.technique import TechniqueSlot

    assert CultivationProfile.__tablename__ == "cultivation_profiles"
    assert CultivationLog.__tablename__ == "cultivation_logs"
    assert TechniqueSlot.__tablename__ == "technique_slots"


def test_concurrent_first_profile_creation_keeps_one_profile(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models.user import User
    from app.services.cultivation import CultivationService

    concurrent_engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent-profile.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=concurrent_engine)
    Sessions = sessionmaker(autocommit=False, autoflush=False, bind=concurrent_engine)
    setup = Sessions()
    try:
        user = User(
            username=f"profile-race-{uuid4().hex}",
            email=f"{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        user_id = user.id
    finally:
        setup.close()

    barrier = Barrier(2)

    def create_profile():
        session = Sessions()
        try:
            barrier.wait()
            profile = CultivationService(session).ensure_profile(user_id)
            session.commit()
            return profile.id
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            profile_ids = list(executor.map(lambda _index: create_profile(), range(2)))
        verify = Sessions()
        try:
            from app.models.cultivation import CultivationProfile

            assert profile_ids[0] == profile_ids[1]
            assert verify.query(CultivationProfile).filter_by(user_id=user_id).count() == 1
        finally:
            verify.close()
    finally:
        concurrent_engine.dispose()


def test_concurrent_todo_settlement_with_same_source_key_is_applied_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models.cultivation import CultivationLog, CultivationProfile
    from app.models.user import User
    from app.services.cultivation import CultivationService

    concurrent_engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent-settlement.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=concurrent_engine)
    Sessions = sessionmaker(autocommit=False, autoflush=False, bind=concurrent_engine)
    setup = Sessions()
    try:
        user = User(
            username=f"settlement-race-{uuid4().hex}",
            email=f"{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        user_id = user.id
        CultivationService(setup).ensure_profile(user_id)
        setup.commit()
    finally:
        setup.close()

    barrier = Barrier(2)
    source_key = "todo:task:concurrent-settlement"

    def settle():
        session = Sessions()
        try:
            barrier.wait()
            result = CultivationService(session).settle_todo_reward(
                user_id, "task", 100, "medium", source_key=source_key
            )
            session.commit()
            return result
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: settle(), range(2)))
        verify = Sessions()
        try:
            profile = verify.query(CultivationProfile).filter_by(user_id=user_id).one()
            logs = verify.query(CultivationLog).filter_by(source_key=source_key).all()

            assert results[0].log_id == results[1].log_id
            assert len(logs) == 1
            assert profile.cultivation == 100
            assert profile.spirit_stones == 60
        finally:
            verify.close()
    finally:
        concurrent_engine.dispose()


def test_user_can_learn_realm_eligible_technique_and_repeat_is_idempotent(client, auth_headers, db_session, user):
    from app.models.cultivation import CultivationProfile
    from app.models.technique import LearnedTechnique
    from app.services.cultivation import CultivationService

    auth_user_id = UUID(client.get("/api/users/me", headers=auth_headers).json()["id"])
    service = CultivationService(db_session)
    service.seed_world(db_session)
    service.set_realm(auth_user_id, "qi_refining", 1, 0)
    profile = db_session.query(CultivationProfile).filter_by(user_id=auth_user_id).one()
    profile.spirit_stones = 20
    db_session.commit()

    response = client.post("/api/cultivation/techniques/steady-breath/learn", headers=auth_headers)
    repeated = client.post("/api/cultivation/techniques/steady-breath/learn", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["learned"] is True
    assert repeated.status_code == 200
    assert repeated.json()["learned"] is True
    assert repeated.json()["id"] == response.json()["id"]
    db_session.expire_all()
    assert db_session.query(LearnedTechnique).filter_by(user_id=auth_user_id).count() == 1
    assert db_session.query(CultivationProfile).filter_by(user_id=auth_user_id).one().spirit_stones == 10


def test_learning_rejects_realm_and_spirit_stone_gates(client, auth_headers, db_session, user):
    from app.models.cultivation import CultivationProfile
    from app.services.cultivation import CultivationService

    auth_user_id = UUID(client.get("/api/users/me", headers=auth_headers).json()["id"])
    service = CultivationService(db_session)
    service.seed_world(db_session)
    service.set_realm(auth_user_id, "qi_refining", 1, 0)
    profile = db_session.query(CultivationProfile).filter_by(user_id=auth_user_id).one()
    profile.spirit_stones = 0
    db_session.commit()

    insufficient = client.post("/api/cultivation/techniques/steady-breath/learn", headers=auth_headers)
    locked = client.post("/api/cultivation/techniques/stone-channel/learn", headers=auth_headers)

    assert insufficient.status_code == 409
    assert "SPIRIT_STONES" in insufficient.json()["detail"]
    assert locked.status_code == 409
    assert "REALM" in locked.json()["detail"]


def test_tribulation_preview_exposes_lock_reason_for_non_final_stage_and_cooldown(db_session, user):
    from app.models.cultivation import CultivationProfile, TribulationAttempt
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.minor_stage = 1
    profile.cultivation = 0
    db_session.commit()
    locked = service.get_tribulation_preview(user.id)
    assert locked.available is False
    assert locked.lock_reason == "FINAL_MINOR_STAGE_REQUIRED"

    db_session.add(TribulationAttempt(
        user_id=user.id, target_realm="foundation", base_probability=90,
        readiness_score=50, final_probability=90, roll=1, success=False,
        attempted_date=service._utc_today(),
    ))
    db_session.commit()
    cooldown = service.get_tribulation_preview(user.id)
    assert cooldown.available is False
    assert cooldown.lock_reason == "TRIBULATION_COOLDOWN_ACTIVE"


def test_ascended_tribulation_preview_has_terminal_lock_reason(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.set_realm(user.id, "ascended", 1, 0)
    preview = service.get_tribulation_preview(user.id)

    assert preview.available is False
    assert preview.lock_reason == "ASCENDED"


def test_npc_user_id_is_non_nullable():
    from app.models.world import Npc

    assert Npc.__table__.c.user_id.nullable is False


def test_meeting_same_disciple_is_permanent_and_stable(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    _prepare_npc_meeting(service, user.id)
    first = service.meet_npc(user.id, "sect-1-normal-1", 7)
    second = service.meet_npc(user.id, "sect-1-normal-1", 7)

    assert first.id == second.id
    assert first.name == second.name
    assert first.population_index == 7
    assert first.is_generated is True


def test_npc_cultivation_updates_once_per_natural_day(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    _prepare_npc_meeting(service, user.id)
    npc = service.meet_npc(user.id, "sect-1-normal-1", 2)
    before = npc.cultivation

    service.refresh_npc_cultivation(npc, date(2026, 8, 17))
    after = npc.cultivation
    service.refresh_npc_cultivation(npc, date(2026, 8, 17))

    assert after >= before
    assert npc.cultivation == after
    assert npc.cultivation_updated_on == date(2026, 8, 17)


def test_npc_cultivation_uses_utc_day_across_midnight_and_is_idempotent(db_session, user, monkeypatch):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    _prepare_npc_meeting(service, user.id)
    utc_days = iter((date(2026, 8, 17), date(2026, 8, 18), date(2026, 8, 18)))
    monkeypatch.setattr(service, "_utc_today", lambda: next(utc_days))
    npc = service.meet_npc(user.id, "sect-1-normal-1", 4)
    before = npc.cultivation

    service.refresh_npc_cultivation(npc)
    after_crossing_utc_day = npc.cultivation
    service.refresh_npc_cultivation(npc)

    assert after_crossing_utc_day > before
    assert npc.cultivation == after_crossing_utc_day
    assert npc.cultivation_updated_on == date(2026, 8, 18)


def test_npc_population_is_stable_but_isolated_between_users(db_session, user):
    from app.models.user import User
    from app.services.cultivation import CultivationService

    other = User(username=f"other-{uuid4().hex}", email=f"{uuid4().hex}@example.com", password_hash="hashed")
    db_session.add(other)
    db_session.commit()
    service = CultivationService(db_session)
    _prepare_npc_meeting(service, user.id)
    _prepare_npc_meeting(service, other.id)

    first = service.meet_npc(user.id, "sect-1-normal-1", 3)
    second = service.meet_npc(other.id, "sect-1-normal-1", 3)

    assert first.id != second.id
    assert first.name == second.name
    assert service.get_npcs(user.id).recently_met[0].id == first.id
    assert service.get_npcs(other.id).recently_met[0].id == second.id


def test_mortal_npcs_return_core_and_recent_disciples_without_ascended_data(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    _prepare_npc_meeting(service, user.id)
    response = service.get_npcs(user.id)

    assert len(response.fixed_core) == 0
    assert response.recently_met == []
    disciple = service.meet_npc(user.id, "sect-1-normal-1", 1)
    response = service.get_npcs(user.id)
    assert [item.id for item in response.recently_met] == [disciple.id]


def test_npc_events_and_relationships_are_strictly_user_scoped(db_session, user):
    from app.models.user import User
    from app.models.world import NpcEvent
    from app.services.cultivation import CultivationService

    other = User(username=f"other-events-{uuid4().hex}", email=f"{uuid4().hex}@example.com", password_hash="hashed")
    db_session.add(other)
    db_session.commit()
    service = CultivationService(db_session)
    _prepare_npc_meeting(service, user.id)
    _prepare_npc_meeting(service, other.id)
    own_npc = service.meet_npc(user.id, "sect-1-normal-1", 11)
    other_npc = service.meet_npc(other.id, "sect-1-normal-1", 11)
    db_session.add(NpcEvent(user_id=user.id, npc_id=other_npc.id, event_key="forged", summary="must not leak"))
    db_session.add(NpcEvent(user_id=other.id, npc_id=own_npc.id, event_key="other-user", summary="must not leak"))
    db_session.commit()

    response = service.get_npcs(user.id)

    assert [item.id for item in response.recently_met] == [own_npc.id]
    assert response.events
    assert all(event.npc_id == own_npc.id for event in response.events)
    assert all(event.event_key != "forged" for event in response.events)


def test_concurrent_meet_npc_with_independent_sessions_returns_one_npc(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models.user import User
    from app.models.world import SectAccessProgress
    from app.services.cultivation import CultivationService

    concurrent_engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent-meet.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=concurrent_engine)
    Sessions = sessionmaker(autocommit=False, autoflush=False, bind=concurrent_engine)
    setup = Sessions()
    try:
        user = User(
            username=f"concurrent-{uuid4().hex}",
            email=f"{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        setup.refresh(user)
        service = CultivationService(setup)
        service.seed_world(setup)
        service.ensure_profile(user.id)
        service.set_realm(user.id, "foundation", 1, 0)
        sect = service._get_sect("sect-1-normal-1")
        setup.add(SectAccessProgress(user_id=user.id, sect_id=sect.id, messenger_contacted=True))
        setup.commit()
        user_id = user.id
    finally:
        setup.close()

    barrier = Barrier(2)

    def meet_in_own_session():
        session = Sessions()
        try:
            barrier.wait()
            return CultivationService(session).meet_npc(user_id, "sect-1-normal-1", 12)
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: meet_in_own_session(), range(2)))
        assert results[0].id == results[1].id
        verify = Sessions()
        try:
            from app.models.world import Npc, NpcEvent

            assert verify.query(Npc).filter_by(user_id=user_id, population_index=12).count() == 1
            assert verify.query(NpcEvent).filter_by(user_id=user_id).count() == 2
        finally:
            verify.close()
    finally:
        concurrent_engine.dispose()


def test_meet_npc_requires_visible_contacted_sect_and_stable_api_errors(client, auth_headers, db_session):
    from app.models.world import Sect
    from app.services.cultivation import CultivationService

    current_user = client.get("/api/users/me", headers=auth_headers).json()
    service = CultivationService(db_session)
    service.set_realm(UUID(current_user["id"]), "foundation", 1, 0)

    db_session.add(Sect(
        sect_key="hidden-review-sect",
        name="Hidden Review Sect",
        star=1,
        kind="hidden",
        entry_realm="qi_refining",
    ))
    db_session.commit()

    missing = client.post(
        "/api/cultivation/npcs/meet",
        json={"sect_key": "missing-review-sect", "population_index": 0},
        headers=auth_headers,
    )
    hidden = client.post(
        "/api/cultivation/npcs/meet",
        json={"sect_key": "hidden-review-sect", "population_index": 0},
        headers=auth_headers,
    )
    uncontacted = client.post(
        "/api/cultivation/npcs/meet",
        json={"sect_key": "sect-1-normal-1", "population_index": 0},
        headers=auth_headers,
    )

    assert missing.status_code == 404
    assert hidden.status_code == 409
    assert uncontacted.status_code == 409
    assert "messenger contact required" in uncontacted.json()["detail"]


def test_npc_event_response_uses_explicit_schema(db_session, user):
    from typing import get_args

    from app.schemas.cultivation import NpcEventSummary, NpcRelationshipResponse

    assert set(NpcEventSummary.model_fields) == {"event_id", "npc_id", "event_key", "summary", "created_at"}
    assert get_args(NpcRelationshipResponse.model_fields["events"].annotation) == (NpcEventSummary,)


def test_npc_migration_moves_events_before_deleting_duplicate_npcs(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text

    from app import main as main_module
    from app.database import Base

    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'duplicate-npcs.sqlite'}")
    Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
    with legacy_engine.begin() as connection:
        connection.execute(text("DROP TABLE npcs"))
        connection.execute(text(
            "CREATE TABLE npcs ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, sect_id VARCHAR(36), "
            "name VARCHAR(100) NOT NULL, role VARCHAR(64), description TEXT, "
            "is_core BOOLEAN NOT NULL DEFAULT 0, population_index INTEGER, "
            "is_generated BOOLEAN NOT NULL DEFAULT 1, cultivation INTEGER NOT NULL DEFAULT 0, "
            "cultivation_updated_on DATE, cultivation_locked BOOLEAN NOT NULL DEFAULT 0)"
        ))
        connection.execute(text(
            "INSERT INTO npcs (id, user_id, sect_id, name, population_index) VALUES "
            "('a-keeper', 'user', 'sect', 'Keeper', 4), ('b-duplicate', 'user', 'sect', 'Duplicate', 4)"
        ))
        connection.execute(text(
            "INSERT INTO npc_events (id, user_id, npc_id, event_key, summary, created_at) VALUES "
            "('event-keeper', 'user', 'a-keeper', 'met', 'keeper event', '2026-08-17 00:00:00'), "
            "('event-duplicate', 'user', 'b-duplicate', 'met', 'duplicate event', '2026-08-17 00:00:01')"
        ))
    with legacy_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1

    monkeypatch.setattr(main_module, "engine", legacy_engine)
    main_module._migrate_columns()
    main_module._migrate_columns()

    with legacy_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, npc_id FROM npc_events ORDER BY id"
        )).fetchall()
        npcs = connection.execute(text("SELECT id FROM npcs")).fetchall()
    assert rows == [("event-duplicate", "a-keeper"), ("event-keeper", "a-keeper")]
    assert npcs == [("a-keeper",)]
    legacy_engine.dispose()


def test_meet_npc_api_creates_a_user_scoped_event(client, auth_headers, db_session):
    from uuid import UUID

    from app.services.cultivation import CultivationService

    current_user = client.get("/api/users/me", headers=auth_headers).json()
    _prepare_npc_meeting(CultivationService(db_session), UUID(current_user["id"]))
    response = client.post(
        "/api/cultivation/npcs/meet",
        json={"sect_key": "sect-1-normal-1", "population_index": 13},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["population_index"] == 13
    timeline = client.get("/api/cultivation/npcs", headers=auth_headers)
    assert timeline.status_code == 200
    assert timeline.json()["events"]


def test_npc_startup_migration_adds_legacy_columns_and_reuses_unique_index(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text

    from app import main as main_module
    from app.database import Base

    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-npcs.sqlite'}")
    Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(text("DROP TABLE npcs"))
        connection.execute(text(
            "CREATE TABLE npcs ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, sect_id VARCHAR(36), "
            "name VARCHAR(100) NOT NULL, role VARCHAR(64), description TEXT, "
            "is_core BOOLEAN NOT NULL DEFAULT 0)"
        ))

    monkeypatch.setattr(main_module, "engine", legacy_engine)
    main_module._migrate_columns()
    main_module._migrate_columns()

    inspector = inspect(legacy_engine)
    columns = {column["name"] for column in inspector.get_columns("npcs")}
    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("npcs")
        if index["name"] == "uq_npc_user_sect_population"
    }
    assert {"population_index", "is_generated", "cultivation", "cultivation_updated_on", "cultivation_locked"} <= columns
    assert indexes["uq_npc_user_sect_population"]["unique"]
    assert len(inspector.get_indexes("npcs")) == len({index["name"] for index in inspector.get_indexes("npcs")})
    legacy_engine.dispose()


def test_reward_uses_difficulty_and_never_writes_negative_resources(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    result = service.settle_todo_reward(user.id, "task", 25, "hard", quality=0.8)

    assert result.cultivation == 28
    assert result.spirit_stones == 16
    assert result.cultivation >= 0


def test_reward_applies_explicit_importance_to_formula(db_session, user):
    from app.services.cultivation import CultivationService

    result = CultivationService(db_session).settle_todo_reward(
        user.id, "task", 10, "medium", importance=1.3
    )

    assert result.cultivation == 13
    assert result.spirit_stones == 7


def test_reward_rejects_unknown_difficulty(db_session, user):
    from app.services.cultivation import CultivationService

    with pytest.raises(ValueError, match="Unknown difficulty"):
        CultivationService(db_session).settle_todo_reward(
            user.id, "task", 10, "impossible"
        )


def test_stage_progress_reports_next_threshold(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.ensure_profile(user.id)
    progress = service.get_next_stage("qi_refining", 1, 128)

    assert progress.current_threshold == 0
    assert progress.next_threshold == 180
    assert progress.remaining == 52


def test_overview_returns_profile_resources_and_stage_progress(db_session, user):
    from app.schemas.cultivation import CultivationOverview
    from app.services.cultivation import CultivationService

    overview = CultivationService(db_session).get_overview(user.id)

    assert isinstance(overview, CultivationOverview)
    assert overview.realm_key == "qi_refining"
    assert overview.minor_stage == 1
    assert overview.cultivation == 0
    assert overview.next_stage.next_threshold == 180
    assert overview.today == []
    assert overview.recent_rewards == []


def test_overview_returns_today_and_recent_rewards_for_only_current_user(db_session, user):
    from datetime import datetime, timezone

    from app.models.cultivation import CultivationLog
    from app.models.todo import Task
    from app.models.user import User
    from app.services.cultivation import CultivationService

    other = User(
        username=f"overview-other-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    db_session.add(other)
    db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add_all([
        Task(user_id=user.id, title="Own task", status="pending", deadline=now),
        Task(user_id=other.id, title="Other task", status="pending", deadline=now),
        CultivationLog(user_id=user.id, source="task", cultivation_delta=12, spirit_stones_delta=7),
        CultivationLog(user_id=other.id, source="task", cultivation_delta=99, spirit_stones_delta=99),
    ])
    db_session.commit()

    overview = CultivationService(db_session).get_overview(user.id)

    assert [item["title"] for item in overview.today] == ["Own task"]
    assert [item["cultivation"] for item in overview.recent_rewards] == [12]


def test_settlement_advances_minor_stage_but_does_not_bypass_tribulation(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.set_realm(user.id, "qi_refining", 1, 179)

    settlement = service.settle_todo_reward(user.id, "task", 10, "hard")

    profile = service.ensure_profile(user.id)
    assert settlement.cultivation == 14
    assert profile.minor_stage == 2
    assert profile.realm_key == "qi_refining"
    assert settlement.ready_for_tribulation is False


def test_settlement_marks_final_stage_ready_without_changing_realm(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.set_realm(user.id, "qi_refining", 9, 234)

    settlement = service.settle_todo_reward(user.id, "task", 1, "hard")

    profile = service.ensure_profile(user.id)
    assert profile.realm_key == "qi_refining"
    assert profile.minor_stage == 9
    assert profile.cultivation == 235
    assert settlement.ready_for_tribulation is True


def test_overview_creates_profile_for_current_user(client, auth_headers):
    response = client.get("/api/cultivation/overview", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["realm"]["key"] == "qi_refining"


def test_cultivation_api_returns_labels_without_removing_keys(client, auth_headers):
    response = client.get("/api/cultivation/sects?star=1", headers=auth_headers)

    assert response.status_code == 200
    item = response.json()[0]
    assert item["kind"] == "normal"
    assert item["kind_label"] == "普通宗门"
    assert item["entry_realm"] == "foundation"
    assert item["entry_realm_label"] == "筑基期"
    assert item["task_preference"] == "discipline-1"
    assert item["task_preference_label"] == "纪律修行"


def test_cultivation_api_returns_technique_and_overview_labels(client, auth_headers):
    overview = client.get("/api/cultivation/overview", headers=auth_headers)
    techniques = client.get("/api/cultivation/techniques", headers=auth_headers)

    assert overview.status_code == 200
    assert overview.json()["realm_key"] == "qi_refining"
    assert overview.json()["realm_label"] == "炼气期"
    assert techniques.status_code == 200
    technique = next(
        item for item in techniques.json()["techniques"]
        if item["technique_key"] == "steady-breath"
    )
    assert technique["technique_type"] == "mind"
    assert technique["technique_type_label"] == "心法"
    assert technique["required_realm"] == "qi_refining"
    assert technique["required_realm_label"] == "炼气期"


def test_cultivation_routes_require_authentication(client):
    response = client.get("/api/cultivation/overview")

    assert response.status_code == 401


def test_cultivation_seed_is_idempotent(client, auth_headers):
    first = client.get("/api/cultivation/sects", headers=auth_headers)
    second = client.get("/api/cultivation/sects", headers=auth_headers)

    assert first.status_code == second.status_code == 200
    assert len(first.json()) == len(second.json()) == 81


def test_sect_join_is_locked_before_foundation(client, auth_headers):
    response = client.post(
        "/api/cultivation/sects/sect-1-normal-1/join",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "sect requires foundation realm"


def test_mortal_npcs_expose_only_the_mortal_population(client, auth_headers):
    world = client.get("/api/cultivation/world", headers=auth_headers)
    npcs = client.get("/api/cultivation/npcs", headers=auth_headers)

    assert world.status_code == 200
    assert len(world.json()["nodes"]) >= 9
    assert npcs.status_code == 200
    assert npcs.json()["fixed_core"] == []
    assert npcs.json()["recently_met"] == []


def test_ascended_user_can_load_fixed_npcs_without_changing_data_boundary(db_session, user):
    from app.services.cultivation import CultivationService
    from app.models.cultivation import CultivationProfile
    from app.models.world import Npc

    service = CultivationService(db_session)
    service.set_realm(user.id, "ascended", 1, 0)

    response = service.get_npcs(user.id)

    assert len(response.fixed_core) == 270
    assert db_session.query(Npc).filter(Npc.user_id == user.id, Npc.is_core.is_(True)).count() == 270
    db_session.query(Npc).filter(Npc.user_id == user.id).delete(synchronize_session=False)
    db_session.query(CultivationProfile).filter(CultivationProfile.user_id == user.id).delete(synchronize_session=False)
    db_session.commit()


def test_technique_slot_purchase_progresses_indices_and_charges_profile(client, auth_headers):
    from app.database import Base
    from tests.conftest import TestingSessionLocal
    from app.models.cultivation import CultivationProfile

    first = client.post(
        "/api/cultivation/technique-slots/purchase",
        json={"slot_type": "main"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert first.json()["slot_index"] == 0
    assert first.json()["slot_count"] == 1
    assert first.json()["price"] == 0

    db = TestingSessionLocal()
    try:
        profile = db.query(CultivationProfile).one()
        profile.spirit_stones = 500
        profile.realm_key = "golden_core"
        db.commit()
    finally:
        db.close()

    purchase = client.post(
        "/api/cultivation/technique-slots/purchase",
        json={"slot_type": "main"},
        headers=auth_headers,
    )
    repeat = client.post(
        "/api/cultivation/technique-slots/purchase",
        json={"slot_type": "main"},
        headers=auth_headers,
    )

    assert purchase.status_code == repeat.status_code == 200
    assert purchase.json()["slot_index"] == 1
    assert purchase.json()["slot_count"] == 2
    assert purchase.json()["price"] == 100
    assert purchase.json()["balance"] == 400
    assert repeat.json()["slot_index"] == 2
    assert repeat.json()["slot_count"] == 3
    assert repeat.json()["price"] == 300
    assert repeat.json()["balance"] == 100


def test_purchase_slot_rejects_insufficient_stones_with_stable_error(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.ensure_profile(user.id).realm_key = "foundation"
    service.purchase_slot(user.id, "main")
    with pytest.raises(PermissionError, match="INSUFFICIENT_SPIRIT_STONES"):
        service.purchase_slot(user.id, "main")


def test_tribulation_attempt_rejects_server_controlled_fields(client, auth_headers):
    response = client.post(
        "/api/cultivation/tribulation/attempt",
        json={"pill_count": 0, "final_probability": 99},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_tribulation_attempt_rejects_negative_pill_count(client, auth_headers):
    response = client.post(
        "/api/cultivation/tribulation/attempt",
        json={"pill_count": -1},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_fresh_profile_cannot_attempt_tribulation_and_is_unchanged(db_session, user, monkeypatch):
    from app.models.cultivation import TribulationAttempt
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    monkeypatch.setattr("app.services.cultivation.random.random", lambda: 0.0)

    with pytest.raises(PermissionError, match="tribulation requires final minor stage"):
        service.attempt_tribulation(user.id, 0)

    db_session.refresh(profile)
    assert (profile.realm_key, profile.minor_stage, profile.cultivation) == ("qi_refining", 1, 0)
    assert db_session.query(TribulationAttempt).filter_by(user_id=user.id).count() == 0


def test_tribulation_persists_the_actual_random_roll_and_keeps_failure_loss(db_session, user, monkeypatch):
    from app.models.cultivation import TribulationAttempt
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.minor_stage = 9
    profile.cultivation = 235
    monkeypatch.setattr("app.services.cultivation.random.random", lambda: 0.999)

    result = service.attempt_tribulation(user.id, 0)
    attempt = db_session.query(TribulationAttempt).filter_by(user_id=user.id).one()

    assert result.success is False
    assert attempt.roll == 99.9
    assert attempt.roll != attempt.final_probability
    assert result.cultivation_loss == math.floor(235 * 0.1)


def test_tribulation_probability_is_clamped_and_public(db_session, user):
    from app.services.cultivation import CultivationService

    preview = CultivationService(db_session).get_tribulation_preview(user.id)

    assert 20 <= preview.final_probability <= 95
    assert preview.base_probability >= 20
    assert set(preview.readiness_breakdown) == {
        "mind_state", "habit", "task_quality", "trial", "compatibility"
    }


def test_great_vehicle_to_tribulation_uses_25_percent_base_rate(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "great_vehicle"
    profile.minor_stage = 4
    profile.cultivation = 30000

    preview = service.get_tribulation_preview(user.id)

    assert preview.target_realm == "tribulation"
    assert preview.base_probability == 25
    assert preview.failure_loss_percent == 25


def test_tribulation_to_ascension_has_explicit_terminal_target(db_session, user, monkeypatch):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "tribulation"
    profile.minor_stage = 4
    profile.cultivation = 49000
    monkeypatch.setattr(service, "roll", lambda probability: True)

    preview = service.get_tribulation_preview(user.id)
    result = service.attempt_tribulation(user.id, 0)

    assert preview.target_realm == "ascension"
    assert preview.base_probability == 20
    assert result.realm_key == "ascended"
    assert result.target_realm == "ascension"
    assert result.terminal is True


def test_failed_final_tribulation_is_not_marked_as_completed(db_session, user, monkeypatch):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "tribulation"
    profile.minor_stage = 4
    profile.cultivation = 49000
    monkeypatch.setattr(service, "roll", lambda probability: False)

    result = service.attempt_tribulation(user.id, 0)

    assert result.success is False
    assert result.realm_key == "tribulation"
    assert result.terminal is False


def test_readiness_normalizes_naive_habit_time_and_derives_trial_and_compatibility(db_session, user):
    from datetime import datetime, timedelta, timezone
    from app.models.technique import LearnedTechnique, Technique
    from app.models.todo import Habit
    from app.models.world import Sect, SectAccessProgress, SectMembership
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    habit = Habit(user_id=user.id, title="Daily", last_completed_at=datetime.now() - timedelta(days=1))
    db_session.add(habit)
    service.seed_world(db_session)
    sect = db_session.query(Sect).first()
    db_session.add_all([
        SectMembership(user_id=user.id, sect_id=sect.id),
        SectAccessProgress(user_id=user.id, sect_id=sect.id, trial_confirmed=True),
    ])
    technique = db_session.query(Technique).first()
    db_session.add(LearnedTechnique(user_id=user.id, technique_id=technique.id))
    db_session.commit()

    breakdown = service.get_tribulation_preview(user.id).readiness_breakdown

    assert breakdown["habit"] == 100
    assert breakdown["trial"] == 100
    assert breakdown["compatibility"] == 100


def test_concurrent_tribulation_attempts_allow_only_one_daily_attempt(db_session, user, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from tests.conftest import TestingSessionLocal
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.minor_stage = 4
    profile.cultivation = 950
    db_session.commit()
    user_id = user.id
    monkeypatch.setattr(CultivationService, "roll", lambda self, probability: True)

    def attempt():
        session = TestingSessionLocal()
        try:
            return CultivationService(session).attempt_tribulation(user_id, 0)
        except Exception as exc:
            return exc
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt(), range(2)))

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, PermissionError) for result in results) == 1


def test_tribulation_attempts_have_database_unique_user_day_constraint():
    from app.models.cultivation import TribulationAttempt

    columns = {column.name for column in TribulationAttempt.__table__.columns}
    constraints = [
        {column.name for column in constraint.columns}
        for constraint in TribulationAttempt.__table__.constraints
        if hasattr(constraint, "columns")
    ]

    assert "attempted_date" in columns
    assert {"user_id", "attempted_date"} in constraints


def test_ascended_profile_remains_valid_for_progression_endpoints(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.set_realm(user.id, "ascended", 1, 0)

    overview = service.get_overview(user.id)
    techniques = service.get_techniques(user.id)
    sects = service.get_sects(user.id)
    world = service.get_world(user.id)
    slot = service.purchase_slot(user.id, "main")

    assert overview.realm_key == "ascended"
    assert techniques.next_slot_purchases["main"].realm_confirmed is True
    assert len(sects) == 81
    assert len(world.nodes) >= 9
    assert slot["slot_index"] == 0


def test_overview_exposes_explicit_ascended_state(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    mortal = service.get_overview(user.id)
    service.set_realm(user.id, "ascended", 1, 0)
    ascended = service.get_overview(user.id)

    assert mortal.ascended is False
    assert ascended.realm_key == "ascended"
    assert ascended.ascended is True


def test_non_daily_integrity_error_is_not_reported_as_cooldown(db_session, user, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.minor_stage = 4
    profile.cultivation = 950
    db_session.commit()
    monkeypatch.setattr(service, "roll", lambda probability: True)
    original_commit = db_session.commit

    def raise_other_integrity_error():
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed: unrelated_table.key"))

    monkeypatch.setattr(db_session, "commit", raise_other_integrity_error)
    with pytest.raises(IntegrityError, match="unrelated_table.key"):
        service.attempt_tribulation(user.id, 0)
    monkeypatch.setattr(db_session, "commit", original_commit)


def test_similar_daily_fields_without_unique_error_are_not_reported_as_cooldown(db_session, user, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.minor_stage = 4
    profile.cultivation = 950
    db_session.commit()
    monkeypatch.setattr(service, "roll", lambda probability: True)
    original_commit = db_session.commit

    def raise_similar_non_unique_error():
        raise IntegrityError(
            "INSERT", {},
            Exception("CHECK constraint failed: tribulation_attempts.user_id, attempted_date"),
        )

    monkeypatch.setattr(db_session, "commit", raise_similar_non_unique_error)
    with pytest.raises(IntegrityError, match="CHECK constraint failed"):
        service.attempt_tribulation(user.id, 0)
    monkeypatch.setattr(db_session, "commit", original_commit)


def test_failed_tribulation_keeps_realm_and_techniques(db_session, user, monkeypatch):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.minor_stage = 4
    profile.cultivation = 950
    monkeypatch.setattr(service, "roll", lambda probability: False)

    result = service.attempt_tribulation(user.id, 0)

    assert result.success is False
    assert result.realm_key == "foundation"
    assert result.lost_realm is False
    assert result.lost_techniques is False
    assert result.cultivation_loss == 95
    assert result.cooldown_until is not None


def test_tribulation_cooldown_blocks_second_attempt_same_day(db_session, user, monkeypatch):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.minor_stage = 4
    profile.cultivation = 950
    monkeypatch.setattr(service, "roll", lambda probability: True)

    first = service.attempt_tribulation(user.id, 0)
    preview = service.get_tribulation_preview(user.id)

    assert first.cooldown_until is not None
    assert preview.cooldown_until == first.cooldown_until
    with pytest.raises(PermissionError, match="tribulation cooldown"):
        service.attempt_tribulation(user.id, 0)


def test_tribulation_persists_the_roll_used_for_the_decision(db_session, user, monkeypatch):
    from app.models.cultivation import TribulationAttempt
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.minor_stage = 4
    profile.cultivation = 950
    rolls = iter([0.91])
    monkeypatch.setattr("app.services.cultivation.random.random", lambda: next(rolls))

    result = service.attempt_tribulation(user.id, 0)
    attempt = db_session.query(TribulationAttempt).filter_by(user_id=user.id).one()

    assert result.success is False
    assert attempt.roll == 91.0


def test_sect_listing_hides_hidden_sects_and_uses_star_entry_realms(db_session, user):
    from collections import Counter
    from app.models.world import Sect

    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    sects = service.get_sects(user.id)
    all_sects = db_session.query(Sect).all()
    counts = Counter((sect.star, sect.kind) for sect in all_sects)

    assert len(sects) == 81
    assert all(sect.kind != "hidden" for sect in sects)
    for star in range(1, 10):
        assert counts[(star, "normal")] == 6
        assert counts[(star, "special")] == 3
        assert counts[(star, "hidden")] == 1
    expected = {
        1: "foundation", 2: "golden_core", 3: "nascent_soul",
        4: "spirit_transformation", 5: "void_refining",
        6: "body_combination", 7: "great_vehicle", 8: "tribulation", 9: "tribulation",
    }
    assert {sect.star: sect.entry_realm for sect in all_sects if sect.kind == "normal"} == expected


def test_sect_join_rejects_hidden_and_lower_realm_with_stable_locks(db_session, user):
    from app.models.world import Sect
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    hidden = db_session.query(Sect).filter_by(star=1, kind="hidden").one()
    star_two = db_session.query(Sect).filter_by(star=2, kind="normal").first()

    with pytest.raises(PermissionError, match="sect is locked"):
        service.join_sect(user.id, hidden.sect_key)
    with pytest.raises(PermissionError, match="sect requires golden_core realm"):
        service.join_sect(user.id, star_two.sect_key)


def test_sect_listing_and_join_share_realm_eligibility_rule(db_session, user):
    from app.models.world import Sect
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    sect = db_session.query(Sect).filter_by(star=1, kind="normal").first()

    profile.realm_key = "qi_refining"
    locked = next(item for item in service.get_sects(user.id) if item.id == sect.id)
    assert locked.visible is True
    assert locked.realm_confirmed is False
    assert locked.can_join is False
    with pytest.raises(PermissionError, match="sect requires foundation realm"):
        service.join_sect(user.id, sect.sect_key)

    profile.realm_key = "foundation"
    eligible = next(item for item in service.get_sects(user.id) if item.id == sect.id)
    assert eligible.realm_confirmed is True
    assert eligible.can_join is False
    service.contact_sect_messenger(user.id, sect.sect_key)
    service.complete_sect_trial(user.id, sect.sect_key)
    assert service.join_sect(user.id, sect.sect_key).status == "active"


def test_sect_prerequisites_are_persisted_and_required_in_order(db_session, user):
    from app.models.world import Sect, SectAccessProgress
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    sect = db_session.query(Sect).filter_by(star=1, kind="normal").first()

    initial = next(item for item in service.get_sects(user.id) if item.id == sect.id)
    assert initial.can_join is False
    assert initial.realm_confirmed is True
    assert initial.messenger_contacted is False
    assert initial.trial_confirmed is False
    assert initial.trial_status == "awaiting_messenger"

    with pytest.raises(PermissionError, match="messenger contact required"):
        service.join_sect(user.id, sect.sect_key)
    with pytest.raises(PermissionError, match="messenger contact required"):
        service.complete_sect_trial(user.id, sect.sect_key)

    contacted = service.contact_sect_messenger(user.id, sect.sect_key)
    assert contacted.messenger_contacted is True
    assert contacted.trial_confirmed is False
    assert contacted.trial_status == "awaiting_trial"

    completed = service.complete_sect_trial(user.id, sect.sect_key)
    assert completed.messenger_contacted is True
    assert completed.trial_confirmed is True
    assert completed.trial_status == "completed"
    assert completed.can_join is True
    assert db_session.query(SectAccessProgress).filter_by(user_id=user.id, sect_id=sect.id).one()


def test_sect_prerequisite_endpoints_and_join_bypass_rejection(client, auth_headers):
    from tests.conftest import TestingSessionLocal
    from app.models.cultivation import CultivationProfile
    from app.services.auth import decode_access_token
    from uuid import UUID

    db = TestingSessionLocal()
    try:
        user_id = UUID(decode_access_token(auth_headers["Authorization"].split(" ", 1)[1])["sub"])
        profile = db.query(CultivationProfile).filter_by(user_id=user_id).first()
        if profile is None:
            profile = CultivationProfile(user_id=user_id)
            db.add(profile)
        profile.realm_key = "foundation"
        db.commit()
    finally:
        db.close()

    listing = client.get("/api/cultivation/sects", headers=auth_headers)
    sect = next(item for item in listing.json() if item["star"] == 1 and item["kind"] == "normal")
    path = f"/api/cultivation/sects/{sect['sect_key']}"

    assert client.post(f"{path}/join", headers=auth_headers).status_code == 409
    contact = client.post(f"{path}/messenger/contact", headers=auth_headers)
    assert contact.status_code == 200
    assert contact.json()["messenger_contacted"] is True
    assert contact.json()["trial_confirmed"] is False
    assert contact.json()["trial_status"] == "awaiting_trial"

    trial = client.post(f"{path}/trial/complete", headers=auth_headers)
    assert trial.status_code == 200
    assert trial.json()["trial_confirmed"] is True
    assert trial.json()["can_join"] is True


def test_hidden_sect_prerequisites_are_unavailable(client, auth_headers):
    path = "/api/cultivation/sects/sect-1-hidden-10"

    assert client.post(f"{path}/messenger/contact", headers=auth_headers).status_code == 409
    assert client.post(f"{path}/trial/complete", headers=auth_headers).status_code == 409
    assert client.post(f"{path}/join", headers=auth_headers).status_code == 409


def test_technique_library_exposes_authoritative_next_slot_previews(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    profile.spirit_stones = 500

    response = service.get_techniques(user.id)

    assert response.spirit_stones == 500
    preview = response.next_slot_purchases["main"]
    assert preview.next_slot_index == 0
    assert preview.price == 0
    assert preview.required_realm == "qi_refining"
    assert preview.post_purchase_balance == 500
    assert preview.can_purchase is True


def test_update_loadout_requires_owned_learned_technique_and_realm(db_session, user):
    from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
    from app.services.cultivation import CultivationService

    other = type(user)(username=f"other-{uuid4().hex}", email=f"{uuid4().hex}@example.com", password_hash="hashed")
    db_session.add(other)
    db_session.commit()
    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    slot = TechniqueSlot(user_id=user.id, slot_type="main", slot_index=0)
    db_session.add(slot)
    technique = db_session.query(Technique).filter_by(technique_key="stone-channel").one()
    high_technique = db_session.query(Technique).filter_by(technique_key="golden-intent").one()
    db_session.add(LearnedTechnique(user_id=other.id, technique_id=technique.id))
    db_session.add(LearnedTechnique(user_id=user.id, technique_id=high_technique.id))
    db_session.commit()

    with pytest.raises(LookupError, match="technique not learned"):
        service.update_loadout(user.id, {"main": technique.id})
    with pytest.raises(PermissionError, match="technique requires golden_core realm"):
        service.update_loadout(user.id, {"main": high_technique.id})
    assert slot.technique_id is None


def test_update_loadout_rejects_multi_slot_conflict_and_returns_all_assignments(db_session, user):
    from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    service.ensure_profile(user.id).realm_key = "foundation"
    db_session.add_all([
        TechniqueSlot(user_id=user.id, slot_type="main", slot_index=0),
        TechniqueSlot(user_id=user.id, slot_type="main", slot_index=1),
        TechniqueSlot(user_id=user.id, slot_type="auxiliary", slot_index=0),
    ])
    technique = db_session.query(Technique).filter_by(technique_key="stone-channel").one()
    technique.slot_count = 2
    db_session.add(LearnedTechnique(user_id=user.id, technique_id=technique.id))
    db_session.commit()

    response = service.update_loadout(user.id, {"main": [technique.id, technique.id]})
    assert response.slot_assignments["main"] == [technique.id, technique.id]

    with pytest.raises(ValueError, match="SLOT_CONFLICT"):
        service.update_loadout(user.id, {"main": [technique.id, technique.id], "auxiliary": [technique.id]})


def test_update_loadout_rejects_multi_slot_technique_spanning_categories_before_mutation(db_session, user):
    from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    service.ensure_profile(user.id).realm_key = "foundation"
    main_slots = [
        TechniqueSlot(user_id=user.id, slot_type="main", slot_index=0),
    ]
    auxiliary_slots = [
        TechniqueSlot(user_id=user.id, slot_type="auxiliary", slot_index=0),
        TechniqueSlot(user_id=user.id, slot_type="auxiliary", slot_index=1),
    ]
    db_session.add_all(main_slots + auxiliary_slots)
    technique = db_session.query(Technique).filter_by(technique_key="stone-channel").one()
    technique.slot_count = 2
    db_session.add(LearnedTechnique(user_id=user.id, technique_id=technique.id))
    db_session.commit()

    with pytest.raises(ValueError, match="SLOT_CONFLICT:CATEGORY"):
        service.update_loadout(
            user.id,
            {"main": [technique.id], "auxiliary": [None, technique.id]},
        )

    db_session.expire_all()
    assert db_session.query(TechniqueSlot).filter_by(user_id=user.id, slot_type="main").one().technique_id is None
    assert all(slot.technique_id is None for slot in db_session.query(TechniqueSlot).filter_by(user_id=user.id, slot_type="auxiliary").all())


def test_sect_join_accepts_seeded_sect_uuid_after_unlock(db_session, user):
    from app.models.world import Sect
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    sect = db_session.query(Sect).first()

    service.contact_sect_messenger(user.id, sect.sect_key)
    service.complete_sect_trial(user.id, sect.sect_key)
    membership = service.join_sect(user.id, str(sect.id))

    assert membership.sect_id == sect.id
