from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.todo import (
    HabitCreate,
    HabitUpdate,
    HabitResponse,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    SubtaskCreate,
    SubtaskUpdate,
    SubtaskResponse,
)
from app.schemas.task_schedule import (
    TaskScheduleStateResponse,
    TaskSnoozeRequest,
    TaskRescheduleRequest,
)
from app.schemas.note_link import NoteLinkSummary, TargetNoteLinkCreate
from app.services.todo import TodoService
from app.services.note_link import NoteLinkService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/todos", tags=["todos"])


# --- Daily summary endpoint ---

@router.get("/daily", response_model=dict)
def get_daily_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_daily_summary(current_user.id)


# --- Habit endpoints ---

@router.post("/habits", response_model=HabitResponse)
def create_habit(
    habit_in: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.create_habit(current_user.id, habit_in)


@router.get("/habits", response_model=List[HabitResponse])
def get_habits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_habits(current_user.id)


@router.get("/habits/{habit_id}", response_model=HabitResponse)
def get_habit(
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_habit_for_user(habit_id, current_user.id)


@router.put("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: UUID,
    habit_in: HabitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    habit = service.get_habit_for_user(habit_id, current_user.id)
    return service.update_habit(habit, habit_in)


@router.delete("/habits/{habit_id}")
def delete_habit(
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    service.get_habit_for_user(habit_id, current_user.id)
    service.delete_habit(habit_id)
    return {"message": "Habit deleted"}


@router.post("/habits/{habit_id}/complete", response_model=HabitResponse)
def complete_habit(
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    habit = service.get_habit_for_user(habit_id, current_user.id)
    return service.complete_habit(habit, current_user.id)


# --- Task endpoints ---

@router.post("/tasks", response_model=TaskResponse)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.create_task(current_user.id, task_in)


@router.get("/tasks", response_model=List[TaskResponse])
def get_tasks(
    project_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if project_id:
        tasks = service.get_tasks_by_project(project_id, current_user.id)
    else:
        tasks = service.get_tasks(current_user.id)
    # Populate project_name and project_color from relationship
    result = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        if t.project:
            resp.project_name = t.project.name
            resp.project_color = t.project.color
        result.append(resp)
    return result


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_task_for_user(task_id, current_user.id)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    task = service.get_task_for_user(task_id, current_user.id)
    return service.update_task(task, task_in)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    service.get_task_for_user(task_id, current_user.id)
    service.delete_task(task_id)
    return {"message": "Task deleted"}


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: UUID,
    occurrence_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    task = service.get_task_for_user(task_id, current_user.id)
    return service.complete_task(task, current_user.id, occurrence_date)


@router.post("/tasks/{task_id}/snooze", response_model=TaskScheduleStateResponse)
def snooze_task(
    task_id: UUID,
    body: TaskSnoozeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    task = service.get_task_for_user(task_id, current_user.id)
    return service.schedule_service.snooze(task, body.until, body.occurrence_date)


@router.patch("/tasks/{task_id}/schedule", response_model=TaskScheduleStateResponse)
def reschedule_task(
    task_id: UUID,
    body: TaskRescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    task = service.get_task_for_user(task_id, current_user.id)
    return service.schedule_service.reschedule(
        task,
        deadline=body.deadline,
        occurrence_date=body.occurrence_date,
        new_occurrence_date=body.new_occurrence_date,
    )


# --- Goal endpoints ---

@router.post("/goals", response_model=GoalResponse)
def create_goal(
    goal_in: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.create_goal(current_user.id, goal_in)


@router.get("/goals", response_model=List[GoalResponse])
def get_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_goals(current_user.id)


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_goal_for_user(goal_id, current_user.id)


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: UUID,
    goal_in: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    goal = service.get_goal_for_user(goal_id, current_user.id)
    return service.update_goal(goal, goal_in)


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    service.get_goal_for_user(goal_id, current_user.id)
    service.delete_goal(goal_id)
    return {"message": "Goal deleted"}


@router.post("/goals/{goal_id}/complete", response_model=GoalResponse)
def complete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    goal = service.get_goal_for_user(goal_id, current_user.id)
    return service.complete_goal(goal, current_user.id)


# --- Explicit note links ---

@router.get("/tasks/{task_id}/notes", response_model=List[NoteLinkSummary])
def get_task_notes(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return NoteLinkService(db).list_for_target("task", task_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/tasks/{task_id}/notes", response_model=NoteLinkSummary)
def link_task_note(
    task_id: UUID,
    body: TargetNoteLinkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return NoteLinkService(db).link_target("task", task_id, body.note_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        detail = str(exc)
        if detail == "LINK_ALREADY_EXISTS":
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=404 if detail in {"TARGET_NOT_FOUND", "NOTE_REQUIRED"} else 400, detail=detail)


@router.delete("/tasks/{task_id}/notes/{note_id}")
def unlink_task_note(
    task_id: UUID,
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        NoteLinkService(db).unlink_target("task", task_id, note_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) in {"LINK_NOT_FOUND", "TARGET_NOT_FOUND", "NOTE_REQUIRED"} else 400, detail=str(exc))
    return {"message": "Link removed"}


@router.get("/goals/{goal_id}/notes", response_model=List[NoteLinkSummary])
def get_goal_notes(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return NoteLinkService(db).list_for_target("goal", goal_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/goals/{goal_id}/notes", response_model=NoteLinkSummary)
def link_goal_note(
    goal_id: UUID,
    body: TargetNoteLinkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return NoteLinkService(db).link_target("goal", goal_id, body.note_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        detail = str(exc)
        if detail == "LINK_ALREADY_EXISTS":
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=404 if detail in {"TARGET_NOT_FOUND", "NOTE_REQUIRED"} else 400, detail=detail)


@router.delete("/goals/{goal_id}/notes/{note_id}")
def unlink_goal_note(
    goal_id: UUID,
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        NoteLinkService(db).unlink_target("goal", goal_id, note_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) in {"LINK_NOT_FOUND", "TARGET_NOT_FOUND", "NOTE_REQUIRED"} else 400, detail=str(exc))
    return {"message": "Link removed"}


# --- Subtask endpoints ---

@router.post("/subtasks", response_model=SubtaskResponse)
def create_subtask(
    subtask_in: SubtaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    service.get_task_for_user(subtask_in.task_id, current_user.id)
    return service.create_subtask(subtask_in)


@router.get("/subtasks/task/{task_id}", response_model=List[SubtaskResponse])
def get_subtasks_by_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    service.get_task_for_user(task_id, current_user.id)
    return service.get_subtasks(task_id)


@router.get("/subtasks/{subtask_id}", response_model=SubtaskResponse)
def get_subtask(
    subtask_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_subtask_for_user(subtask_id, current_user.id)


@router.put("/subtasks/{subtask_id}", response_model=SubtaskResponse)
def update_subtask(
    subtask_id: UUID,
    subtask_in: SubtaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    subtask = service.get_subtask_for_user(subtask_id, current_user.id)
    if subtask_in.is_completed is True:
        return service.complete_subtask(subtask, current_user.id)
    return service.update_subtask(subtask, subtask_in)


@router.post("/subtasks/{subtask_id}/complete", response_model=SubtaskResponse)
def complete_subtask(
    subtask_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    subtask = service.get_subtask_for_user(subtask_id, current_user.id)
    return service.complete_subtask(subtask, current_user.id)


@router.delete("/subtasks/{subtask_id}")
def delete_subtask(
    subtask_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    service.get_subtask_for_user(subtask_id, current_user.id)
    service.delete_subtask(subtask_id)
    return {"message": "Subtask deleted"}
