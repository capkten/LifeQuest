from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.cultivation import CultivationProfile
from app.models.technique import LearnedTechnique, Technique, TechniqueSlot
from app.models.user import User
from app.services.cultivation import CultivationService


@pytest.fixture
def user(db_session):
    Base.metadata.create_all(bind=db_session.bind)
    user = User(
        username=f"technique-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_technique_catalog_covers_all_slot_types_with_multiple_options(db_session, user):
    service = CultivationService(db_session)
    service.seed_world(db_session)

    techniques = db_session.query(Technique).all()
    by_type = {}
    for technique in techniques:
        by_type.setdefault(technique.technique_type, []).append(technique)

    assert set(by_type) == {"main", "auxiliary", "mind", "movement", "body"}
    assert all(len(options) >= 2 for options in by_type.values())
    assert all(technique.effect_config for technique in techniques)


def test_slot_price_uses_fixed_schedule_then_two_point_four_multiplier(db_session, user):
    service = CultivationService(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "ascended"
    profile.spirit_stones = 100_000
    db_session.commit()

    prices = [service.purchase_slot(user.id, "main")["price"] for _ in range(8)]

    assert prices == [0, 100, 300, 800, 2000, 5000, 12000, 28800]


def test_loadout_rejects_technique_type_mismatch(db_session, user):
    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.ensure_profile(user.id)
    profile.realm_key = "foundation"
    slot = TechniqueSlot(user_id=user.id, slot_type="mind", slot_index=0)
    technique = db_session.query(Technique).filter_by(technique_type="body").first()
    db_session.add(slot)
    db_session.add(LearnedTechnique(user_id=user.id, technique_id=technique.id))
    db_session.commit()

    with pytest.raises(PermissionError, match="TECHNIQUE_TYPE_MISMATCH"):
        service.update_loadout(user.id, {"mind": technique.id})


def test_concurrent_slot_purchase_cannot_duplicate_index(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'technique-slot-race.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=engine)
    Sessions = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    setup = Sessions()
    try:
        user = User(
            username=f"technique-race-{uuid4().hex}",
            email=f"{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        CultivationService(setup).ensure_profile(user.id)
        profile = setup.query(CultivationProfile).filter_by(user_id=user.id).one()
        profile.realm_key = "ascended"
        profile.spirit_stones = 1000
        setup.commit()
        user_id = user.id
    finally:
        setup.close()

    barrier = Barrier(2)

    def purchase():
        session = Sessions()
        try:
            barrier.wait(timeout=5)
            return CultivationService(session).purchase_slot(user_id, "main")
        except Exception as exc:
            return exc
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: purchase(), range(2)))

        successes = [result for result in results if isinstance(result, dict)]
        verify = Sessions()
        try:
            assert len(successes) == 1
            assert successes[0]["slot_index"] == 0
            assert verify.query(TechniqueSlot).filter_by(
                user_id=user_id, slot_type="main", slot_index=0
            ).count() == 1
        finally:
            verify.close()
    finally:
        engine.dispose()
