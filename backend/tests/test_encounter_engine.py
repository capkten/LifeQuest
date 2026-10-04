import pytest
from app.services.encounter_engine import EncounterEngine, calculate_encounter_probability
from app.models import EncounterEvent, UserEncounterRecord

def test_probability_calculation():
    # Base 0.15 + (15 // 15 * 0.05) + 0 = 0.20
    assert calculate_encounter_probability(15, 0) == 0.20
    # 0 duration: 0.15 base -> bounded >= 0.10
    assert calculate_encounter_probability(0, 0) == 0.15
    # Max duration and max streak: capped at 0.60
    assert calculate_encounter_probability(120, 30) == 0.60
    # Negative streak or invalid duration handled gracefully
    assert 0.10 <= calculate_encounter_probability(-10, -5) <= 0.60

def test_seed_events_and_roll(client, db_session):
    EncounterEngine.seed_events(db_session)
    events = db_session.query(EncounterEvent).all()
    assert len(events) >= 8

    # Roll with 100% force mock (prob=1.0)
    event = EncounterEngine.roll_encounter(db_session, user_id=None, realm_level=1, duration_minutes=60, streak_days=5, force_hit=True)
    assert event is not None
    assert event.min_realm_level <= 1

    # High realm requirement event should not be returned for realm_level=1
    high_tier_events = [e for e in events if e.min_realm_level > 1]
    if high_tier_events:
        for _ in range(20):
            ev = EncounterEngine.roll_encounter(db_session, user_id=None, realm_level=1, duration_minutes=60, streak_days=5, force_hit=True)
            assert ev.min_realm_level <= 1
