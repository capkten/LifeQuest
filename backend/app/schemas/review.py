from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WeeklyReviewSummary(BaseModel):
    completed_count: int = 0
    open_count: int = 0
    overdue_count: int = 0
    habit_due_count: int = 0
    habit_completed_count: int = 0


class WeeklyReviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    url: str
    kind: str
    status: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None
    occurrence_date: Optional[date] = None


class HabitStreakChange(BaseModel):
    id: UUID
    title: str
    due_count: int
    completed_count: int
    streak_before: int
    streak_after: int
    delta: int


class WeeklyReviewRewards(BaseModel):
    coins_earned: int = 0
    coins_spent: int = 0
    coins_delta: int = 0
    experience: int = 0
    cultivation: int = 0
    spirit_stones: int = 0


class WeeklyReviewSuggestion(BaseModel):
    title: str
    reason: str
    url: str


class WeeklyReviewResponse(BaseModel):
    week_start: date
    week_end: date
    timezone: str
    summary: WeeklyReviewSummary
    habit_streak_changes: List[HabitStreakChange]
    rewards: WeeklyReviewRewards
    unfinished_high_priority: List[WeeklyReviewItem]
    projects_without_next_action: List[WeeklyReviewItem]
    notes: List[WeeklyReviewItem]
    suggestions: List[WeeklyReviewSuggestion]
