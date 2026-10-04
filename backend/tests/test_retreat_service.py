import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException

from app.models import CultivationRetreat, Task, CultivationProfile
from app.services.cultivation_retreat import CultivationRetreatService
from app.services.encounter_engine import EncounterEngine

def utc_now():
    return datetime.now(timezone.utc)

def test_retreat_lifecycle_and_conflict(client, db_session, user):
    EncounterEngine.seed_events(db_session)

    # 1. Start retreat
    retreat = CultivationRetreatService.start_retreat(
        db=db_session,
        user_id=user.id,
        target_duration=25,
    )
    assert retreat is not None
    assert retreat.status == "active"
    assert retreat.target_duration == 25

    # 2. Starting another retreat while active must raise 409
    with pytest.raises(HTTPException) as exc_info:
        CultivationRetreatService.start_retreat(
            db=db_session,
            user_id=user.id,
            target_duration=15,
        )
    assert exc_info.value.status_code == 409

    # 3. Query active retreat
    active = CultivationRetreatService.get_active_retreat(db_session, user.id)
    assert active is not None
    assert active.id == retreat.id

    # 4. Abort retreat
    aborted = CultivationRetreatService.abort_retreat(db_session, user.id, retreat.id)
    assert aborted.status == "aborted"
    assert aborted.ended_at is not None

    # No more active retreat
    assert CultivationRetreatService.get_active_retreat(db_session, user.id) is None


def test_retreat_completion_and_anti_cheat(client, db_session, user):
    EncounterEngine.seed_events(db_session)

    # Start 25 minute retreat
    retreat = CultivationRetreatService.start_retreat(
        db=db_session,
        user_id=user.id,
        target_duration=25,
    )

    # Case A: Too early (< 80% of target duration, e.g. 5 minutes in)
    # Mock started_at to be only 5 minutes ago
    retreat.started_at = utc_now() - timedelta(minutes=5)
    db_session.commit()

    completed_early = CultivationRetreatService.complete_retreat(
        db=db_session,
        user_id=user.id,
        retreat_id=retreat.id,
    )
    # Must be marked aborted due to insufficient duration (< 80%)
    assert completed_early.status == "aborted"
    assert completed_early.encounter_id is None

    # Case B: Sufficient duration (e.g. 26 minutes in)
    retreat2 = CultivationRetreatService.start_retreat(
        db=db_session,
        user_id=user.id,
        target_duration=25,
    )
    retreat2.started_at = utc_now() - timedelta(minutes=26)
    db_session.commit()

    completed_ok = CultivationRetreatService.complete_retreat(
        db=db_session,
        user_id=user.id,
        retreat_id=retreat2.id,
        force_encounter=True,
    )
    assert completed_ok.status == "completed"
    assert completed_ok.exp_gained >= 250
    assert completed_ok.coins_gained >= 125
    assert completed_ok.encounter_id is not None
    assert completed_ok.encounter_result is not None
