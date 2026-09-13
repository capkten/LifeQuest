import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Uuid, Index

from app.database import Base


class HabitPauseInterval(Base):
    """A China-local date interval during which a habit is paused."""

    __tablename__ = "habit_pause_intervals"
    __table_args__ = (
        Index("ix_habit_pause_interval_habit_dates", "habit_id", "paused_on", "resumed_on"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    habit_id = Column(Uuid, nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    paused_on = Column(Date, nullable=False)
    resumed_on = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
