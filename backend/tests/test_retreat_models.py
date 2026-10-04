import pytest
from app.models import CultivationRetreat, EncounterEvent, UserEncounterRecord

def test_models_importable_and_schema_defined():
    assert CultivationRetreat.__tablename__ == "cultivation_retreats"
    assert EncounterEvent.__tablename__ == "encounter_events"
    assert UserEncounterRecord.__tablename__ == "user_encounter_records"

    # Verify key columns exist
    retreat_cols = {c.name for c in CultivationRetreat.__table__.columns}
    assert {"id", "user_id", "todo_id", "target_duration", "actual_duration", "status", "started_at", "ended_at", "exp_gained", "coins_gained", "encounter_id", "encounter_result"}.issubset(retreat_cols)

    event_cols = {c.name for c in EncounterEvent.__table__.columns}
    assert {"id", "title", "story_text", "rarity", "min_realm_level", "reward_type", "reward_payload", "weight"}.issubset(event_cols)

    user_record_cols = {c.name for c in UserEncounterRecord.__table__.columns}
    assert {"id", "user_id", "encounter_id", "first_unlocked_at", "unlock_count", "last_retreat_id"}.issubset(user_record_cols)
