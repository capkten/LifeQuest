import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    __table_args__ = (
        UniqueConstraint("habit_id", "completed_date", name="uq_habit_completion_habit_date"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    habit_id = Column(Uuid, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_date = Column(Date, nullable=False)
    completed_at = Column(DateTime, nullable=False, default=utc_now)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    habit = relationship("Habit", back_populates="completions")
