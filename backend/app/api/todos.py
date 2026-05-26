from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from app.services.todo import TodoService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/todos", tags=["todos"])


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
    if not service.verify_habit_ownership(habit_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    habit = service.get_habit(habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.put("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: UUID,
    habit_in: HabitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_habit_ownership(habit_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    habit = service.get_habit(habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return service.update_habit(habit, habit_in)


@router.delete("/habits/{habit_id}")
def delete_habit(
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_habit_ownership(habit_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    habit = service.get_habit(habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    service.delete_habit(habit_id)
    return {"message": "Habit deleted"}


@router.post("/habits/{habit_id}/complete", response_model=HabitResponse)
def complete_habit(
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_habit_ownership(habit_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    habit = service.get_habit(habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return service.complete_habit(habit)


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    return service.get_tasks(current_user.id)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_task_ownership(task_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_task_ownership(task_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.update_task(task, task_in)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_task_ownership(task_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    service.delete_task(task_id)
    return {"message": "Task deleted"}


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_task_ownership(task_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.complete_task(task, current_user.id)


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
    if not service.verify_goal_ownership(goal_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    goal = service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: UUID,
    goal_in: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_goal_ownership(goal_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    goal = service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return service.update_goal(goal, goal_in)


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_goal_ownership(goal_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    goal = service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    service.delete_goal(goal_id)
    return {"message": "Goal deleted"}


@router.post("/goals/{goal_id}/complete", response_model=GoalResponse)
def complete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_goal_ownership(goal_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    goal = service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return service.complete_goal(goal, current_user.id)


# --- Subtask endpoints ---

@router.post("/subtasks", response_model=SubtaskResponse)
def create_subtask(
    subtask_in: SubtaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_task_ownership(subtask_in.task_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return service.create_subtask(subtask_in)


@router.get("/subtasks/task/{task_id}", response_model=List[SubtaskResponse])
def get_subtasks_by_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_task_ownership(task_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return service.get_subtasks(task_id)


@router.get("/subtasks/{subtask_id}", response_model=SubtaskResponse)
def get_subtask(
    subtask_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_subtask_ownership(subtask_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    subtask = service.get_subtask(subtask_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask


@router.put("/subtasks/{subtask_id}", response_model=SubtaskResponse)
def update_subtask(
    subtask_id: UUID,
    subtask_in: SubtaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_subtask_ownership(subtask_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    subtask = service.get_subtask(subtask_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return service.update_subtask(subtask, subtask_in)


@router.delete("/subtasks/{subtask_id}")
def delete_subtask(
    subtask_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TodoService(db)
    if not service.verify_subtask_ownership(subtask_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    subtask = service.get_subtask(subtask_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    service.delete_subtask(subtask_id)
    return {"message": "Subtask deleted"}
