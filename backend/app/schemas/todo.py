from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.todo import Difficulty, TaskStatus, Frequency


# Habit schemas
class HabitCreate(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    frequency: Frequency = Frequency.DAILY
    coins_reward: int = 10
    exp_reward: int = 5


class HabitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    frequency: Optional[Frequency] = None
    coins_reward: Optional[int] = None
    exp_reward: Optional[int] = None
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
    created_at: datetime
    updated_at: datetime


# Task schemas
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    coins_reward: int = 10
    exp_reward: int = 5
    deadline: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    status: Optional[TaskStatus] = None
    coins_reward: Optional[int] = None
    exp_reward: Optional[int] = None
    deadline: Optional[datetime] = None


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


# Goal schemas
class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    coins_reward: int = 50
    exp_reward: int = 25
    deadline: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    status: Optional[TaskStatus] = None
    coins_reward: Optional[int] = None
    exp_reward: Optional[int] = None
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
