import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, String, Uuid

from app.database import Base


class HabitLeaveInterval(Base):
    __tablename__ = "habit_leave_intervals"
    __table_args__ = (
        Index("ix_habit_leave_interval_habit_dates", "habit_id", "leave_on", "return_on"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    habit_id = Column(Uuid, nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    leave_on = Column(Date, nullable=False)
    return_on = Column(Date, nullable=False)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
