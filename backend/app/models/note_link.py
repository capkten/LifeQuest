import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Uuid, UniqueConstraint

from app.database import Base


class TaskNoteLink(Base):
    __tablename__ = "task_note_links"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, ForeignKey("note_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("note_id", "task_id", name="uq_task_note_link"),
    )


class GoalNoteLink(Base):
    __tablename__ = "goal_note_links"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, ForeignKey("note_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Uuid, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("note_id", "goal_id", name="uq_goal_note_link"),
    )


class ProjectNoteLink(Base):
    __tablename__ = "project_note_links"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, ForeignKey("note_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("note_id", "project_id", name="uq_project_note_link"),
    )
