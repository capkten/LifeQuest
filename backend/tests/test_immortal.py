import pytest

from app.models.immortal import ImmortalActivityRecord, ImmortalOfficialCommission, ImmortalProfile
from app.services.immortal import ImmortalService
from app.database import Base
from tests.conftest import engine


def _schema():
    Base.metadata.create_all(bind=engine)


def test_pre_ascension_immortal_overview_is_denied(db_session):
    _schema()
    from app.models.user import User
    user = User(username="immortal-denied", email="immortal-denied@example.com", password_hash="x")
    db_session.add(user); db_session.commit()
    with pytest.raises(PermissionError, match="IMMORTAL_PROFILE_REQUIRED"):
        ImmortalService(db_session).get_overview(user.id)


def test_activity_awards_once_for_duplicate_request(db_session):
    _schema()
    from app.models.user import User
    user = User(username="immortal-activity", email="immortal-activity@example.com", password_hash="x")
    db_session.add(user); db_session.commit()
    db_session.add(ImmortalProfile(user_id=user.id)); db_session.commit()
    service = ImmortalService(db_session)
    first = service.run_activity(user.id, "daily-cultivation", "activity-once")
    repeated = service.run_activity(user.id, "daily-cultivation", "activity-once")
    profile = db_session.query(ImmortalProfile).filter_by(user_id=user.id).one()
    assert first == repeated
    assert profile.essence == 5
    assert db_session.query(ImmortalActivityRecord).filter_by(user_id=user.id).count() == 1


def test_overview_exposes_progression_surfaces_and_stage_advancement_is_idempotent(db_session):
    _schema()
    from app.models.user import User
    user = User(username="immortal-overview", email="immortal-overview@example.com", password_hash="x")
    db_session.add(user); db_session.commit()
    db_session.add(ImmortalProfile(user_id=user.id, essence=50)); db_session.commit()
    service = ImmortalService(db_session)
    overview = service.get_overview(user.id)
    assert overview["regions"] and overview["officials"] and overview["activities"] and overview["stage_goals"]
    first = service.advance_stage(user.id, "stage-once")
    repeated = service.advance_stage(user.id, "stage-once")
    assert first == repeated
    assert db_session.query(ImmortalProfile).filter_by(user_id=user.id).one().stage == 2


def test_official_commission_awards_once_for_request(db_session):
    _schema()
    from app.models.user import User
    user = User(username="immortal-official", email="immortal-official@example.com", password_hash="x")
    db_session.add(user); db_session.commit()
    db_session.add(ImmortalProfile(user_id=user.id)); db_session.commit()
    service = ImmortalService(db_session)
    first = service.commission(user.id, "gatekeeper", "commission-once")
    repeated = service.commission(user.id, "gatekeeper", "commission-once")
    assert first == repeated
    assert db_session.query(ImmortalOfficialCommission).filter_by(user_id=user.id).count() == 1
