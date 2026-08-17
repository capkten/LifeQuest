import pytest
from uuid import uuid4


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


def test_cultivation_tables_are_registered(db_session):
    from app.models.cultivation import CultivationProfile, CultivationLog
    from app.models.technique import TechniqueSlot

    assert CultivationProfile.__tablename__ == "cultivation_profiles"
    assert CultivationLog.__tablename__ == "cultivation_logs"
    assert TechniqueSlot.__tablename__ == "technique_slots"


def test_npc_user_id_is_non_nullable():
    from app.models.world import Npc

    assert Npc.__table__.c.user_id.nullable is False


def test_reward_uses_difficulty_and_never_writes_negative_resources(db_session, user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    result = service.settle_todo_reward(user.id, "task", 25, "hard", quality=0.8)

    assert result.cultivation == 27
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


def test_overview_creates_profile_for_current_user(client, auth_headers):
    response = client.get("/api/cultivation/overview", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["realm"]["key"] == "qi_refining"


def test_cultivation_routes_require_authentication(client):
    response = client.get("/api/cultivation/overview")

    assert response.status_code == 401


def test_cultivation_seed_is_idempotent(client, auth_headers):
    first = client.get("/api/cultivation/sects", headers=auth_headers)
    second = client.get("/api/cultivation/sects", headers=auth_headers)

    assert first.status_code == second.status_code == 200
    assert len(first.json()) == len(second.json()) == 90


def test_sect_join_is_locked_before_foundation(client, auth_headers):
    response = client.post(
        "/api/cultivation/sects/sect-1-1-ordinary-1/join",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "sect requires foundation realm"


def test_world_and_fixed_npcs_are_available(client, auth_headers):
    world = client.get("/api/cultivation/world", headers=auth_headers)
    npcs = client.get("/api/cultivation/npcs", headers=auth_headers)

    assert world.status_code == npcs.status_code == 200
    assert len(world.json()["nodes"]) >= 9
    assert len(npcs.json()["fixed_core"]) == 270


def test_technique_slot_purchase_and_loadout_are_idempotent(client, auth_headers):
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
    assert purchase.json()["slot_count"] == repeat.json()["slot_count"]


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


def test_sect_join_accepts_seeded_sect_uuid_after_unlock(db_session, user):
    from app.models.world import Sect
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    sect = db_session.query(Sect).first()

    membership = service.join_sect(user.id, str(sect.id))

    assert membership.sect_id == sect.id
