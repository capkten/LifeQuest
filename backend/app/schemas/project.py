from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Project schemas
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#0EA5E9"
    icon: str = "folder"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    color: str
    icon: str
    status: str
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    # Computed fields (will be added by service)
    total_tasks: int = 0
    completed_tasks: int = 0
    progress: float = 0.0


# Phase schemas
class PhaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class PhaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class PhaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


# Milestone schemas
class MilestoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    sort_order: int = 0


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    sort_order: Optional[int] = None


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    due_date: Optional[date]
    status: str
    reached_at: Optional[datetime]
    sort_order: int
    created_at: datetime


# Project detail (with phases, milestones, tasks)
class ProjectDetailResponse(ProjectResponse):
    phases: List[PhaseResponse] = []
    milestones: List[MilestoneResponse] = []
