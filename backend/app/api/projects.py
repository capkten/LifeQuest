from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    PhaseCreate,
    PhaseUpdate,
    PhaseResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
)
from app.schemas.todo import TaskCreate, TaskResponse
from app.services.project import ProjectService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _project_to_response(stats: dict) -> dict:
    """Flatten service stats dict into a ProjectResponse-compatible dict."""
    p = stats["project"]
    return {
        "id": p.id,
        "user_id": p.user_id,
        "name": p.name,
        "description": p.description,
        "color": p.color,
        "icon": p.icon,
        "status": p.status,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "total_tasks": stats["total_tasks"],
        "completed_tasks": stats["completed_tasks"],
        "progress": stats["progress"],
    }


# --- Project CRUD ---

@router.get("", response_model=List[ProjectResponse])
def get_projects(
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    results = service.get_projects(current_user.id, status)
    return [_project_to_response(r) for r in results]


@router.post("", response_model=ProjectResponse)
def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    result = service.create_project(current_user.id, data)
    return _project_to_response(result)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project_detail(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    detail = service.get_project_detail(project_id, current_user.id)
    p = detail["project"]
    return {
        "id": p.id,
        "user_id": p.user_id,
        "name": p.name,
        "description": p.description,
        "color": p.color,
        "icon": p.icon,
        "status": p.status,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "total_tasks": detail["total_tasks"],
        "completed_tasks": detail["completed_tasks"],
        "progress": detail["progress"],
        "phases": detail["phases"],
        "milestones": detail["milestones"],
    }


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_for_user(project_id, current_user.id)
    updated = service.update_project(project, data)
    stats = service._compute_project_stats(updated)
    return _project_to_response(stats)


@router.delete("/{project_id}")
def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_for_user(project_id, current_user.id)
    service.delete_project(project)
    return {"message": "Project deleted"}


@router.post("/{project_id}/complete", response_model=ProjectResponse)
def complete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_for_user(project_id, current_user.id)
    completed = service.complete_project(project)
    stats = service._compute_project_stats(completed)
    return _project_to_response(stats)


# --- Phase CRUD ---

@router.post("/{project_id}/phases", response_model=PhaseResponse)
def create_phase(
    project_id: UUID,
    data: PhaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    service.get_project_for_user(project_id, current_user.id)
    return service.create_phase(project_id, data)


@router.put("/phases/{phase_id}", response_model=PhaseResponse)
def update_phase(
    phase_id: UUID,
    data: PhaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    phase = service.phase_repo.get_by_id(phase_id)
    if phase is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Phase not found")
    service.get_project_for_user(phase.project_id, current_user.id)
    return service.update_phase(phase, data)


@router.delete("/phases/{phase_id}")
def delete_phase(
    phase_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    phase = service.phase_repo.get_by_id(phase_id)
    if phase is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Phase not found")
    service.get_project_for_user(phase.project_id, current_user.id)
    service.delete_phase(phase)
    return {"message": "Phase deleted"}


# --- Milestone CRUD ---

@router.post("/{project_id}/milestones", response_model=MilestoneResponse)
def create_milestone(
    project_id: UUID,
    data: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    service.get_project_for_user(project_id, current_user.id)
    return service.create_milestone(project_id, data)


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(
    milestone_id: UUID,
    data: MilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    milestone = service.milestone_repo.get_by_id(milestone_id)
    if milestone is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Milestone not found")
    service.get_project_for_user(milestone.project_id, current_user.id)
    return service.update_milestone(milestone, data)


@router.delete("/milestones/{milestone_id}")
def delete_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    milestone = service.milestone_repo.get_by_id(milestone_id)
    if milestone is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Milestone not found")
    service.get_project_for_user(milestone.project_id, current_user.id)
    service.delete_milestone(milestone)
    return {"message": "Milestone deleted"}


@router.post("/milestones/{milestone_id}/reach", response_model=MilestoneResponse)
def reach_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    milestone = service.milestone_repo.get_by_id(milestone_id)
    if milestone is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Milestone not found")
    service.get_project_for_user(milestone.project_id, current_user.id)
    return service.reach_milestone(milestone)


# --- Tasks under project ---

@router.post("/{project_id}/tasks", response_model=TaskResponse)
def create_project_task(
    project_id: UUID,
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    service.get_project_for_user(project_id, current_user.id)
    return service.create_project_task(current_user.id, project_id, data)


@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
def get_project_tasks(
    project_id: UUID,
    phase_id: Optional[UUID] = Query(None),
    milestone_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    service.get_project_for_user(project_id, current_user.id)
    tasks = service.get_project_tasks(project_id, phase_id, milestone_id)
    # Populate project_name and project_color
    result = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        if t.project:
            resp.project_name = t.project.name
            resp.project_color = t.project.color
        result.append(resp)
    return result


class MoveTaskRequest(BaseModel):
    project_id: Optional[UUID] = None
    phase_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None


@router.put("/tasks/{task_id}/move", response_model=TaskResponse)
def move_task(
    task_id: UUID,
    body: MoveTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    from app.services.todo import TodoService
    todo_service = TodoService(db)
    task = todo_service.get_task_for_user(task_id, current_user.id)
    return service.move_task(task, body.project_id, body.phase_id, body.milestone_id)
