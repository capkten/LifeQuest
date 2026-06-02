import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text, Float, Uuid
from sqlalchemy.orm import relationship

from app.database import Base

GOAL_COMPLETED_PROGRESS = 100.0


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Frequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty = Column(String(20), default=Difficulty.MEDIUM)
    frequency = Column(String(20), default=Frequency.DAILY)
    coins_reward = Column(Integer, default=10)
    exp_reward = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    last_completed_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty = Column(String(20), default=Difficulty.MEDIUM)
    status = Column(String(20), default=TaskStatus.PENDING)
    coins_reward = Column(Integer, default=10)
    exp_reward = Column(Integer, default=5)
    deadline = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    subtasks = relationship("Subtask", back_populates="task", cascade="all, delete-orphan")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty = Column(String(20), default=Difficulty.MEDIUM)
    status = Column(String(20), default=TaskStatus.IN_PROGRESS)
    coins_reward = Column(Integer, default=50)
    exp_reward = Column(Integer, default=25)
    progress = Column(Float, default=0.0)
    deadline = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False)
    title = Column(String(200), nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="subtasks")
