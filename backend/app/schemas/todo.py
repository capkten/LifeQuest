from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.todo import Difficulty, TaskStatus, Frequency
from app.schemas.cultivation import RewardSettlement
from app.timezone import as_utc


class TodoSchema(BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def normalize_datetimes(cls, value):
        return as_utc(value) if isinstance(value, datetime) else value


# Habit schemas
class HabitScheduleSchema(TodoSchema):
    weekdays: Optional[List[int]] = None
    weekly_target: Optional[int] = Field(default=None, ge=1, le=7)

    @field_validator("weekdays", mode="before")
    @classmethod
    def validate_weekdays(cls, value):
        if value is None:
            return value
        if not isinstance(value, list) or not value or any(type(day) is not int or not 0 <= day <= 6 for day in value):
            raise ValueError("请选择星期一至星期日，至少一天")
        if len(set(value)) != len(value):
            raise ValueError("执行日期不能重复")
        return sorted(value)


class HabitPauseIntervalResponse(TodoSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    habit_id: UUID
    user_id: UUID
    paused_on: date
    resumed_on: Optional[date] = None
    created_at: datetime


class HabitLeaveCreate(TodoSchema):
    leave_on: date
    return_on: date
    reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        if value is None or not isinstance(value, str):
            return value
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_range(self):
        if self.return_on <= self.leave_on:
            raise ValueError("恢复日期必须晚于请假开始日期")
        return self


class HabitLeaveIntervalResponse(TodoSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    habit_id: UUID
    user_id: UUID
    leave_on: date
    return_on: date
    reason: Optional[str] = None
    created_at: datetime


class HabitCompletionCreate(TodoSchema):
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value):
        if value is None or not isinstance(value, str):
            return value
        value = value.strip()
        return value or None


class HabitBackfillCreate(HabitCompletionCreate):
    completed_on: date


class HabitHistoryDay(TodoSchema):
    date: date
    scheduled: bool
    completed: bool
    paused: bool = False
    excused: bool = False
    completion_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    note: Optional[str] = None
    is_makeup: bool = False


class HabitHistoryResponse(TodoSchema):
    habit_id: UUID
    start_on: date
    end_on: date
    total_completed: int
    scheduled_count: int
    completed_count: int
    completion_rate: float
    days: List[HabitHistoryDay]


class HabitCreate(HabitScheduleSchema):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    frequency: Frequency = Frequency.DAILY
    coins_reward: int = Field(default=10, ge=0)
    exp_reward: int = Field(default=5, ge=0)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.frequency == Frequency.WEEKDAYS and not self.weekdays:
            raise ValueError("指定日期习惯至少需要一天")
        if self.frequency != Frequency.WEEKDAYS and self.weekdays is not None:
            raise ValueError("仅指定日期习惯可设置执行日期")
        if self.frequency == Frequency.WEEKLY_TARGET and self.weekly_target is None:
            raise ValueError("每周目标习惯需要设置完成次数")
        if self.frequency != Frequency.WEEKLY_TARGET and self.weekly_target is not None:
            raise ValueError("仅每周目标习惯可设置完成次数")
        return self


class HabitUpdate(HabitScheduleSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    frequency: Optional[Frequency] = None
    coins_reward: Optional[int] = Field(default=None, ge=0)
    exp_reward: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class HabitDailySummary(TodoSchema):
    id: UUID
    title: str
    difficulty: str
    completed_today: bool
    streak: int
    coins_reward: int
    exp_reward: int
    frequency: str
    weekly_target: Optional[int] = None
    weekly_completed: int = 0
    weekly_remaining: int = 0
    total_completed: int = 0
    scheduled_count: int = 0
    completed_count: int = 0
    completion_rate: float = 0.0
    is_active: bool
    paused_today: bool
    pause_intervals: List[HabitPauseIntervalResponse] = Field(default_factory=list)
    scheduled_today: bool
    excused_today: bool
    leave_intervals: List[HabitLeaveIntervalResponse] = Field(default_factory=list)


class HabitResponse(TodoSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    difficulty: str
    frequency: str
    weekdays: Optional[List[int]] = None
    scheduled_today: bool = True
    paused_today: bool = False
    pause_intervals: List[HabitPauseIntervalResponse] = Field(default_factory=list)
    excused_today: bool = False
    leave_intervals: List[HabitLeaveIntervalResponse] = Field(default_factory=list)
    weekly_target: Optional[int] = None
    weekly_completed: int = 0
    weekly_remaining: int = 0
    total_completed: int = 0
    scheduled_count: int = 0
    completed_count: int = 0
    completion_rate: float = 0.0
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
class TaskCreate(TodoSchema):
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


class TaskUpdate(TodoSchema):
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


class TaskResponse(TodoSchema):
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
class GoalCreate(TodoSchema):
    title: str
    description: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    coins_reward: int = Field(default=50, ge=0)
    exp_reward: int = Field(default=25, ge=0)
    deadline: Optional[datetime] = None


class GoalUpdate(TodoSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    status: Optional[TaskStatus] = None
    coins_reward: Optional[int] = Field(default=None, ge=0)
    exp_reward: Optional[int] = Field(default=None, ge=0)
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    deadline: Optional[datetime] = None


class GoalResponse(TodoSchema):
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


class DailySummaryResponse(TodoSchema):
    habits: List[HabitDailySummary]
    tasks: List[dict]
    goals: List[dict]
    summary: dict


# Subtask schemas
class SubtaskCreate(TodoSchema):
    task_id: UUID
    title: str


class SubtaskUpdate(TodoSchema):
    title: Optional[str] = None
    is_completed: Optional[bool] = None


class SubtaskResponse(TodoSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    title: str
    is_completed: bool
    created_at: datetime
    cultivation_reward: Optional[RewardSettlement] = None
