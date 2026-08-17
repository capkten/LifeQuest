import pytest
from uuid import uuid4


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

    assert result.cultivation == 28
    assert result.spirit_stones == 16
    assert result.cultivation >= 0


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
