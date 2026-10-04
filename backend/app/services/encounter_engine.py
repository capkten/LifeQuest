import random
from typing import Optional

from sqlalchemy.orm import Session

from app.data.seed_encounters import DEFAULT_ENCOUNTERS
from app.models.cultivation_retreat import EncounterEvent


def calculate_encounter_probability(duration_minutes: int, streak_days: int) -> float:
    """
    Calculate probability of triggering a random encounter:
    Base: 0.15
    Duration: +0.05 per 15 full minutes
    Streak: +0.01 per day (max 0.10)
    Bounded within [0.10, 0.60]
    """
    base = 0.15
    dur = max(0, duration_minutes)
    stk = max(0, streak_days)

    duration_bonus = (dur // 15) * 0.05
    streak_bonus = min(0.10, stk * 0.01)

    prob = base + duration_bonus + streak_bonus
    prob = max(0.10, min(0.60, prob))
    return round(prob, 2)


class EncounterEngine:
    @staticmethod
    def seed_events(db: Session) -> None:
        """Seed default encounter events if not already present."""
        existing_ids = {e.id for e in db.query(EncounterEvent.id).all()}
        new_events = []
        for item in DEFAULT_ENCOUNTERS:
            if item["id"] not in existing_ids:
                new_events.append(EncounterEvent(**item))

        if new_events:
            db.add_all(new_events)
            db.commit()

    @staticmethod
    def roll_encounter(
        db: Session,
        user_id: Optional[str],
        realm_level: int = 1,
        duration_minutes: int = 25,
        streak_days: int = 0,
        force_hit: bool = False,
    ) -> Optional[EncounterEvent]:
        """
        Determine if a random encounter occurs and pick an eligible event.
        Filters by min_realm_level and picks by weighted random choice.
        """
        prob = calculate_encounter_probability(duration_minutes, streak_days)
        hit = force_hit or (random.random() <= prob)
        if not hit:
            return None

        candidates = (
            db.query(EncounterEvent)
            .filter(EncounterEvent.min_realm_level <= max(1, realm_level))
            .all()
        )
        if not candidates:
            return None

        weights = [max(1, c.weight) for c in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]
