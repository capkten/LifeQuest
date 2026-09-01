import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class TaskSchedule(Base):
    __tablename__ = "task_schedules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id = Column(Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    rule_type = Column(String(16), nullable=False)
    interval = Column(Integer, nullable=False, default=1)
    weekdays_json = Column(Text, nullable=True)
    day_of_month = Column(Integer, nullable=True)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=True)
    timezone = Column(String(64), nullable=False, default="Asia/Shanghai")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    task = relationship("Task", back_populates="schedule")

    @property
    def weekdays(self):
        if not self.weekdays_json:
            return []
        try:
            value = json.loads(self.weekdays_json)
        except (TypeError, json.JSONDecodeError):
            return []
        return value if isinstance(value, list) else []

    @weekdays.setter
    def weekdays(self, value):
        self.weekdays_json = json.dumps(value or [], separators=(",", ":"))


class TaskOccurrence(Base):
    __tablename__ = "task_occurrences"
    __table_args__ = (
        UniqueConstraint("task_id", "occurrence_date", name="uq_task_occurrence_task_date"),
        UniqueConstraint("source_key", name="uq_task_occurrence_source_key"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id = Column(Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    occurrence_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    snoozed_until = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    source_key = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    task = relationship("Task", back_populates="occurrences")
