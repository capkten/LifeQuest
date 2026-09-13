import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, UniqueConstraint, Uuid

from app.database import Base


class DailyFocusPlan(Base):
    __tablename__ = "daily_focus_plans"
    __table_args__ = (UniqueConstraint("user_id", "plan_date", name="uq_daily_focus_user_date"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    plan_date = Column(Date, nullable=False)
    task_ids = Column(JSON, nullable=False, default=list)
    revision = Column(Integer, nullable=False, default=1)


class WorkbenchTaskRequest(Base):
    __tablename__ = "workbench_task_requests"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_workbench_task_request"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    request_id = Column(Uuid, nullable=False)
    task_id = Column(Uuid, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
