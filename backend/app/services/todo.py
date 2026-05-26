from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.todo import Habit, Task, Goal, Subtask
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

    # --- Ownership verification ---
    def verify_habit_ownership(self, habit_id: UUID, user_id: UUID) -> bool:
        habit = self.habit_repo.get_by_id(habit_id)
        return habit is not None and habit.user_id == user_id

    def verify_task_ownership(self, task_id: UUID, user_id: UUID) -> bool:
        task = self.task_repo.get_by_id(task_id)
        return task is not None and task.user_id == user_id

    def verify_goal_ownership(self, goal_id: UUID, user_id: UUID) -> bool:
        goal = self.goal_repo.get_by_id(goal_id)
        return goal is not None and goal.user_id == user_id

    def verify_subtask_ownership(self, subtask_id: UUID, user_id: UUID) -> bool:
        subtask = self.subtask_repo.get_by_id(subtask_id)
        if subtask is None:
            return False
        task = self.task_repo.get_by_id(subtask.task_id)
        return task is not None and task.user_id == user_id

    # --- Habit operations ---
    def create_habit(self, user_id: UUID, habit_in: HabitCreate) -> Habit:
        data = habit_in.model_dump()
        data["user_id"] = user_id
        return self.habit_repo.create(data)

    def get_habits(self, user_id: UUID) -> List[Habit]:
        return self.habit_repo.get_by_user(user_id)

    def get_habit(self, habit_id: UUID) -> Optional[Habit]:
        return self.habit_repo.get_by_id(habit_id)

    def update_habit(self, habit: Habit, habit_in: HabitUpdate) -> Habit:
        update_data = habit_in.model_dump(exclude_unset=True)
        return self.habit_repo.update(habit, update_data)

    def delete_habit(self, habit_id: UUID) -> bool:
        return self.habit_repo.delete(habit_id)

    def complete_habit(self, habit: Habit) -> Habit:
        """Mark habit as completed for today, incrementing streak."""
        habit.streak += 1
        if habit.streak > habit.best_streak:
            habit.best_streak = habit.streak
        self.habit_repo.db.commit()
        self.habit_repo.db.refresh(habit)
        return habit

    # --- Task operations ---
    def create_task(self, user_id: UUID, task_in: TaskCreate) -> Task:
        data = task_in.model_dump()
        data["user_id"] = user_id
        return self.task_repo.create(data)

    def get_tasks(self, user_id: UUID) -> List[Task]:
        return self.task_repo.get_by_user(user_id)

    def get_task(self, task_id: UUID) -> Optional[Task]:
        return self.task_repo.get_by_id(task_id)

    def update_task(self, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)
        return self.task_repo.update(task, update_data)

    def delete_task(self, task_id: UUID) -> bool:
        return self.task_repo.delete(task_id)

    def complete_task(self, task: Task, user_id: UUID) -> Task:
        """Complete a task and award coins and experience to the user."""
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        self.task_repo.db.commit()

        user = self.user_repo.get_by_id(user_id)
        if user:
            self.user_repo.update_coins(user, task.coins_reward)
            self.user_repo.update_experience(user, task.exp_reward)

        self.task_repo.db.refresh(task)
        return task

    # --- Goal operations ---
    def create_goal(self, user_id: UUID, goal_in: GoalCreate) -> Goal:
        data = goal_in.model_dump()
        data["user_id"] = user_id
        return self.goal_repo.create(data)

    def get_goals(self, user_id: UUID) -> List[Goal]:
        return self.goal_repo.get_by_user(user_id)

    def get_goal(self, goal_id: UUID) -> Optional[Goal]:
        return self.goal_repo.get_by_id(goal_id)

    def update_goal(self, goal: Goal, goal_in: GoalUpdate) -> Goal:
        update_data = goal_in.model_dump(exclude_unset=True)
        return self.goal_repo.update(goal, update_data)

    def delete_goal(self, goal_id: UUID) -> bool:
        return self.goal_repo.delete(goal_id)

    def complete_goal(self, goal: Goal, user_id: UUID) -> Goal:
        """Complete a goal and award coins and experience to the user."""
        goal.status = "completed"
        goal.progress = 100.0
        self.goal_repo.db.commit()

        user = self.user_repo.get_by_id(user_id)
        if user:
            self.user_repo.update_coins(user, goal.coins_reward)
            self.user_repo.update_experience(user, goal.exp_reward)

        self.goal_repo.db.refresh(goal)
        return goal

    # --- Subtask operations ---
    def create_subtask(self, subtask_in: SubtaskCreate) -> Subtask:
        data = subtask_in.model_dump()
        return self.subtask_repo.create(data)

    def get_subtasks(self, task_id: UUID) -> List[Subtask]:
        return self.subtask_repo.get_by_task(task_id)

    def get_subtask(self, subtask_id: UUID) -> Optional[Subtask]:
        return self.subtask_repo.get_by_id(subtask_id)

    def update_subtask(self, subtask: Subtask, subtask_in: SubtaskUpdate) -> Subtask:
        update_data = subtask_in.model_dump(exclude_unset=True)
        return self.subtask_repo.update(subtask, update_data)

    def delete_subtask(self, subtask_id: UUID) -> bool:
        return self.subtask_repo.delete(subtask_id)
