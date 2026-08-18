from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.todo import Difficulty, TaskStatus, Frequency
from app.schemas.cultivation import RewardSettlement


# Habit schemas
class HabitCreate(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    frequency: Frequency = Frequency.DAILY
    coins_reward: int = Field(default=10, ge=0)
    exp_reward: int = Field(default=5, ge=0)


class HabitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    frequency: Optional[Frequency] = None
    coins_reward: Optional[int] = Field(default=None, ge=0)
    exp_reward: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class HabitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    difficulty: str
    frequency: str
    coins_reward: int
    exp_reward: int
    is_active: bool
    streak: int
    best_streak: int
    last_completed_at: Optional[datetime] = None
    completed_today: bool = False
    created_at: datetime
    updated_at: datetime
    cultivation_reward: Optional[RewardSettlement] = None


# Task schemas
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    coins_reward: int = Field(default=10, ge=0)
    exp_reward: int = Field(default=5, ge=0)
    deadline: Optional[datetime] = None
    project_id: Optional[UUID] = None
    phase_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    status: Optional[TaskStatus] = None
    coins_reward: Optional[int] = Field(default=None, ge=0)
    exp_reward: Optional[int] = Field(default=None, ge=0)
    deadline: Optional[datetime] = None
    project_id: Optional[UUID] = None
    phase_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    priority: Optional[str] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    difficulty: str
    status: str
    coins_reward: int
    exp_reward: int
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    project_id: Optional[UUID] = None
    phase_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    priority: str = "medium"
    sort_order: int = 0
    cultivation_reward: Optional[RewardSettlement] = None
    project_name: Optional[str] = None
    project_color: Optional[str] = None


# Goal schemas
class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    coins_reward: int = Field(default=50, ge=0)
    exp_reward: int = Field(default=25, ge=0)
    deadline: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    status: Optional[TaskStatus] = None
    coins_reward: Optional[int] = Field(default=None, ge=0)
    exp_reward: Optional[int] = Field(default=None, ge=0)
    progress: Optional[float] = None
    deadline: Optional[datetime] = None


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    difficulty: str
    status: str
    coins_reward: int
    exp_reward: int
    progress: float
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    cultivation_reward: Optional[RewardSettlement] = None


# Subtask schemas
class SubtaskCreate(BaseModel):
    task_id: UUID
    title: str


class SubtaskUpdate(BaseModel):
    title: Optional[str] = None
    is_completed: Optional[bool] = None


class SubtaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    title: str
    is_completed: bool
    created_at: datetime
