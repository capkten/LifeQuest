from app.models.cultivation import CultivationProfile
from app.models.immortal import ImmortalProfile
from app.models.user import User
from app.services.ascension import AscensionService
from uuid import uuid4
from app.database import Base
from tests.conftest import engine


def _user(db_session):
    suffix = uuid4().hex
    user = User(username=f"ascension-{suffix}", email=f"{suffix}@example.com", password_hash="test")
    db_session.add(user)
    db_session.commit()
    return user


def _prepare_schema():
    Base.metadata.create_all(bind=engine)


def test_ascension_requires_terminal_mortal_realm(db_session):
    _prepare_schema()
    user = _user(db_session)
    with __import__('pytest').raises(PermissionError, match="ASCENSION_NOT_READY"):
        AscensionService(db_session).ascend(user.id, "ascend-not-ready")


def test_ascension_creates_one_immortal_profile_and_replays_request(db_session):
    _prepare_schema()
    user = _user(db_session)
    profile = CultivationProfile(user_id=user.id, realm_key="n", minor_stage=1)
    db_session.add(profile)
    db_session.commit()

    service = AscensionService(db_session)
    first = service.ascend(user.id, "ascend-once")
    repeated = service.ascend(user.id, "ascend-once")

    assert first.id == repeated.id
    assert db_session.query(ImmortalProfile).filter_by(user_id=user.id).count() == 1


def test_cross_realm_settlement_is_idempotent(db_session):
    _prepare_schema()
    user = _user(db_session)
    db_session.add(ImmortalProfile(user_id=user.id))
    db_session.commit()
    service = AscensionService(db_session)

    first = service.settle_mortal_todo_after_ascension(user.id, "todo:1", 12, 7)
    repeated = service.settle_mortal_todo_after_ascension(user.id, "todo:1", 99, 99)
    profile = db_session.query(ImmortalProfile).filter_by(user_id=user.id).one()

    assert first.id == repeated.id
    assert profile.essence == 12
    assert profile.immortal_stones == 7
