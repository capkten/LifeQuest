import math

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
    assert len(first.json()) == len(second.json()) == 81


def test_sect_join_is_locked_before_foundation(client, auth_headers):
    response = client.post(
        "/api/cultivation/sects/sect-1-normal-1/join",
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
    monkeypatch.setattr(CultivationService, "roll", lambda self, probability: True)

    def attempt():
        session = TestingSessionLocal()
        try:
            return CultivationService(session).attempt_tribulation(user.id, 0)
        except Exception as exc:
            return exc
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt(), range(2)))

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, PermissionError) for result in results) == 1


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
