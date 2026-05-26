from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.todo import Habit, Task, Goal, Subtask, TaskStatus, GOAL_COMPLETED_PROGRESS
from app.repositories.todo import (
    HabitRepository,
    TaskRepository,
    GoalRepository,
    SubtaskRepository,
)
from app.repositories.user import UserRepository
from app.schemas.todo import (
    HabitCreate,
    HabitUpdate,
    TaskCreate,
    TaskUpdate,
    GoalCreate,
    GoalUpdate,
    SubtaskCreate,
    SubtaskUpdate,
)


class TodoService:
    def __init__(self, db: Session):
        self.habit_repo = HabitRepository(db)
        self.task_repo = TaskRepository(db)
        self.goal_repo = GoalRepository(db)
        self.subtask_repo = SubtaskRepository(db)
        self.user_repo = UserRepository(db)

    # --- Ownership verification (returns object or raises HTTPException) ---
    def get_habit_for_user(self, habit_id: UUID, user_id: UUID) -> Habit:
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None:
            raise HTTPException(status_code=404, detail="Habit not found")
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return habit

    def get_task_for_user(self, task_id: UUID, user_id: UUID) -> Task:
        task = self.task_repo.get_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return task

    def get_goal_for_user(self, goal_id: UUID, user_id: UUID) -> Goal:
        goal = self.goal_repo.get_by_id(goal_id)
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found")
        if goal.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return goal

    def get_subtask_for_user(self, subtask_id: UUID, user_id: UUID) -> Subtask:
        subtask = self.subtask_repo.get_by_id(subtask_id)
        if subtask is None:
            raise HTTPException(status_code=404, detail="Subtask not found")
        task = self.task_repo.get_by_id(subtask.task_id)
        if task is None or task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return subtask

    # --- Habit operations ---
    def create_habit(self, user_id: UUID, habit_in: HabitCreate) -> Habit:
        data = habit_in.model_dump()
        data["user_id"] = user_id
        return self.habit_repo.create(data)

    def get_habits(self, user_id: UUID) -> List[Habit]:
        return self.habit_repo.get_by_user(user_id)

    def update_habit(self, habit: Habit, habit_in: HabitUpdate) -> Habit:
        update_data = habit_in.model_dump(exclude_unset=True)
        return self.habit_repo.update(habit, update_data)

    def delete_habit(self, habit_id: UUID) -> bool:
        return self.habit_repo.delete(habit_id)

    def complete_habit(self, habit: Habit, user_id: UUID) -> Habit:
        """Mark habit as completed for today, incrementing streak and awarding rewards."""
        habit.streak += 1
        if habit.streak > habit.best_streak:
            habit.best_streak = habit.streak

        user = self.user_repo.get_by_id(user_id)
        if user:
            self._update_rewards(user, habit.coins_reward, habit.exp_reward)

        self.habit_repo.db.refresh(habit)
        return habit

    # --- Task operations ---
    def create_task(self, user_id: UUID, task_in: TaskCreate) -> Task:
        data = task_in.model_dump()
        data["user_id"] = user_id
        return self.task_repo.create(data)

    def get_tasks(self, user_id: UUID) -> List[Task]:
        return self.task_repo.get_by_user(user_id)

    def update_task(self, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)
        return self.task_repo.update(task, update_data)

    def delete_task(self, task_id: UUID) -> bool:
        return self.task_repo.delete(task_id)

    def complete_task(self, task: Task, user_id: UUID) -> Task:
        """Complete a task and award coins and experience to the user."""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)

        user = self.user_repo.get_by_id(user_id)
        if user:
            self._update_rewards(user, task.coins_reward, task.exp_reward)

        self.task_repo.db.refresh(task)
        return task

    # --- Goal operations ---
    def create_goal(self, user_id: UUID, goal_in: GoalCreate) -> Goal:
        data = goal_in.model_dump()
        data["user_id"] = user_id
        return self.goal_repo.create(data)

    def get_goals(self, user_id: UUID) -> List[Goal]:
        return self.goal_repo.get_by_user(user_id)

    def update_goal(self, goal: Goal, goal_in: GoalUpdate) -> Goal:
        update_data = goal_in.model_dump(exclude_unset=True)
        return self.goal_repo.update(goal, update_data)

    def delete_goal(self, goal_id: UUID) -> bool:
        return self.goal_repo.delete(goal_id)

    def complete_goal(self, goal: Goal, user_id: UUID) -> Goal:
        """Complete a goal and award coins and experience to the user."""
        goal.status = TaskStatus.COMPLETED
        goal.progress = GOAL_COMPLETED_PROGRESS

        user = self.user_repo.get_by_id(user_id)
        if user:
            self._update_rewards(user, goal.coins_reward, goal.exp_reward)

        self.goal_repo.db.refresh(goal)
        return goal

    def _update_rewards(self, user, coins: int, exp: int) -> None:
        """Update user coins and experience in a single transaction."""
        self.user_repo._update_coins_no_commit(user, coins)
        self.user_repo._update_experience_no_commit(user, exp)
        self.task_repo.db.commit()

    # --- Subtask operations ---
    def create_subtask(self, subtask_in: SubtaskCreate) -> Subtask:
        data = subtask_in.model_dump()
        return self.subtask_repo.create(data)

    def get_subtasks(self, task_id: UUID) -> List[Subtask]:
        return self.subtask_repo.get_by_task(task_id)

    def update_subtask(self, subtask: Subtask, subtask_in: SubtaskUpdate) -> Subtask:
        update_data = subtask_in.model_dump(exclude_unset=True)
        return self.subtask_repo.update(subtask, update_data)

    def delete_subtask(self, subtask_id: UUID) -> bool:
        return self.subtask_repo.delete(subtask_id)
