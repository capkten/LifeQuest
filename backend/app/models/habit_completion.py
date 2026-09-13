import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, UniqueConstraint, Uuid

from app.database import Base


class HabitCompletion(Base):
    """Historical facts retain their habit identifier after a habit is deleted."""

    __tablename__ = "habit_completions"
    __table_args__ = (UniqueConstraint("habit_id", "completed_on", name="uq_habit_completion_day"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    habit_id = Column(Uuid, nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    completed_on = Column(Date, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=False)
    note = Column(String(500), nullable=True)
    is_makeup = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
