import uuid
from datetime import datetime, date, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


PhaseStatus = ProjectStatus


def normalize_project_status(value) -> str:
    value = value.value if isinstance(value, Enum) else value
    return value if value in {status.value for status in ProjectStatus} else "unknown"


def normalize_phase_status(value) -> str:
    value = value.value if isinstance(value, Enum) else value
    return {
        "pending": ProjectStatus.PLANNING.value,
        "in_progress": ProjectStatus.ACTIVE.value,
        "planning": ProjectStatus.PLANNING.value,
        "active": ProjectStatus.ACTIVE.value,
        "completed": ProjectStatus.COMPLETED.value,
        "archived": ProjectStatus.ARCHIVED.value,
    }.get(value, "unknown")


class ProjectPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    REACHED = "reached"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="#0EA5E9")
    icon = Column(String(50), default="folder")
    status = Column(String(20), default=ProjectStatus.PLANNING)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="projects")
    phases = relationship("ProjectPhase", back_populates="project", cascade="all, delete-orphan", order_by="ProjectPhase.sort_order")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan", order_by="ProjectMilestone.sort_order")
    tasks = relationship("Task", back_populates="project")


class ProjectPhase(Base):
    __tablename__ = "project_phases"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=ProjectStatus.PLANNING)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="phases")
    tasks = relationship("Task", back_populates="phase")


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default=MilestoneStatus.PENDING)
    reached_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone")
