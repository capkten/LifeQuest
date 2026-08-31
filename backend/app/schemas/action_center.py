from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


ActionKind = Literal["task", "habit", "goal"]
ActionType = Literal["complete", "open"]


class ActionItem(BaseModel):
    kind: ActionKind
    id: UUID
    title: str
    action: ActionType
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    difficulty: Optional[str] = None
    priority: Optional[str] = None
    progress: Optional[float] = None
    streak: Optional[int] = None
    completed: bool = False
    overdue: bool = False
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    project_color: Optional[str] = None
    occurrence_date: Optional[date] = None
    occurrence_status: Optional[str] = None
    snoozed_until: Optional[datetime] = None


class ActionSections(BaseModel):
    overdue: List[ActionItem]
    today: List[ActionItem]
    habits: List[ActionItem]
    calendar: List[ActionItem]


class ActionSummary(BaseModel):
    open_count: int
    overdue_count: int
    completed_count: int
    habit_due_count: int
    habit_completed_count: int


class TodayActionCenter(BaseModel):
    date: date
    timezone: str
    summary: ActionSummary
    sections: ActionSections
    next_action: Optional[ActionItem] = None
