from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.habit_completion import HabitCompletion
from app.models.todo import Habit
from app.repositories.user import UserRepository
from app.timezone import local_date


def record_completion(
    db: Session,
    habit: Habit,
    completed_at: datetime,
    note: str = None,
    is_makeup: bool = False,
) -> HabitCompletion:
    completed_on = local_date(completed_at)
    existing = db.query(HabitCompletion).filter_by(
        habit_id=habit.id, completed_on=completed_on,
    ).first()
    if existing:
        if note is not None:
            existing.note = note
        return existing
    if completed_at.tzinfo is not None:
        completed_at = completed_at.astimezone(timezone.utc).replace(tzinfo=None)
    completion = HabitCompletion(
        habit_id=habit.id, user_id=habit.user_id,
        completed_on=completed_on, completed_at=completed_at,
        note=note,
        is_makeup=is_makeup,
    )
    db.add(completion)
    db.flush()
    return completion


def backfill_latest_completions(db: Session) -> None:
    habits = db.query(Habit).filter(Habit.last_completed_at.isnot(None)).order_by(Habit.user_id, Habit.id).all()
    for habit in habits:
        UserRepository(db).lock(habit.user_id)
        db.refresh(habit)
        if habit.last_completed_at:
            record_completion(db, habit, habit.last_completed_at)
    db.commit()
