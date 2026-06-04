from datetime import date, datetime, timezone
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
from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.coin_transaction import CoinTransactionRepository
from app.services.achievement import AchievementService
from app.services.title import TitleService


class TodoService:
    def __init__(self, db: Session):
        self.db = db
        self.habit_repo = HabitRepository(db)
        self.task_repo = TaskRepository(db)
        self.goal_repo = GoalRepository(db)
        self.subtask_repo = SubtaskRepository(db)
        self.user_repo = UserRepository(db)
        self.coin_repo = CoinTransactionRepository(db)
        self.achievement_service = AchievementService(db)
        self.title_service = TitleService(db)

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
        # Idempotency: block repeated completion on the same UTC day
        now = datetime.now(timezone.utc)
        if habit.last_completed_at and habit.last_completed_at.date() == now.date():
            return habit

        habit.streak += 1
        if habit.streak > habit.best_streak:
            habit.best_streak = habit.streak
        habit.last_completed_at = now

        user = self.user_repo.get_by_id(user_id)
        if user:
            self._update_rewards(user, habit.coins_reward, habit.exp_reward, CoinSource.HABIT)
            self._check_achievements(user)

        self.habit_repo.db.refresh(habit)
        return habit

    # --- Task operations ---
    def create_task(self, user_id: UUID, task_in: TaskCreate) -> Task:
        data = task_in.model_dump()
        data["user_id"] = user_id
        return self.task_repo.create(data)

    def get_tasks(self, user_id: UUID) -> List[Task]:
        return self.task_repo.get_by_user(user_id)

    def get_tasks_by_project(self, project_id: UUID, user_id: UUID) -> List[Task]:
        return self.db.query(Task).filter(
            Task.user_id == user_id, Task.project_id == project_id
        ).all()

    def update_task(self, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)
        return self.task_repo.update(task, update_data)

    def delete_task(self, task_id: UUID) -> bool:
        return self.task_repo.delete(task_id)

    def complete_task(self, task: Task, user_id: UUID) -> Task:
        """Complete a task and award coins and experience to the user."""
        if task.status == TaskStatus.COMPLETED:
            return task
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)

        user = self.user_repo.get_by_id(user_id)
        if user:
            self._update_rewards(user, task.coins_reward, task.exp_reward, CoinSource.TASK)
            self._check_achievements(user)

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
        if goal.status == TaskStatus.COMPLETED:
            return goal
        goal.status = TaskStatus.COMPLETED
        goal.progress = GOAL_COMPLETED_PROGRESS

        user = self.user_repo.get_by_id(user_id)
        if user:
            self._update_rewards(user, goal.coins_reward, goal.exp_reward, CoinSource.GOAL)
            self._check_achievements(user)

        self.goal_repo.db.refresh(goal)
        return goal

    def _update_rewards(self, user, coins: int, exp: int, source: str) -> None:
        """Update user coins and experience in a single transaction."""
        self.user_repo._update_coins_no_commit(user, coins)
        self.user_repo._update_experience_no_commit(user, exp)
        self.task_repo.db.commit()
        # Record coin transaction
        self.coin_repo.create_transaction(
            user_id=user.id,
            amount=coins,
            coin_type=CoinType.EARN,
            source=source,
            description=f"Reward from {source}",
        )

    def _check_achievements(self, user) -> None:
        """Check and unlock achievements based on current user state."""
        from sqlalchemy import func

        uid = user.id
        # task_count: count completed tasks
        completed_tasks = self.task_repo.db.query(Task).filter(
            Task.user_id == uid, Task.status == TaskStatus.COMPLETED
        ).count()
        self.achievement_service.check_and_unlock(uid, "task_count", completed_tasks)

        # habit_streak: best streak across all habits
        max_streak = self.habit_repo.db.query(func.max(Habit.best_streak)).filter(
            Habit.user_id == uid
        ).scalar() or 0
        self.achievement_service.check_and_unlock(uid, "habit_streak", max_streak)

        # level
        self.achievement_service.check_and_unlock(uid, "level", user.level)

        # coins_earned: use persisted cumulative counter
        self.achievement_service.check_and_unlock(uid, "coins_earned", user.total_coins_earned)

        # goal_count: count completed goals
        completed_goals = self.goal_repo.db.query(Goal).filter(
            Goal.user_id == uid, Goal.status == TaskStatus.COMPLETED
        ).count()
        self.achievement_service.check_and_unlock(uid, "goal_count", completed_goals)

        # Check titles based on level
        self.title_service.check_and_unlock(uid, "level", user.level)

    # --- Daily summary ---
    def get_daily_summary(self, user_id: UUID) -> dict:
        """Get today's tasks overview: habits due today, tasks due today, active goals."""
        today = date.today()

        # 1. Active habits due today
        habits = self.habit_repo.get_active_by_user(user_id)
        daily_habits = []
        for h in habits:
            if h.frequency == "daily":
                daily_habits.append(h)
            elif h.frequency == "weekly" and today.weekday() == 0:  # Monday
                daily_habits.append(h)
            elif h.frequency == "monthly" and today.day == 1:
                daily_habits.append(h)

        # 2. Tasks with deadline today (or overdue and still pending)
        pending_tasks = self.task_repo.get_by_status(user_id, "pending")
        in_progress_tasks = self.task_repo.get_by_status(user_id, "in_progress")
        due_tasks = [
            t
            for t in (pending_tasks + in_progress_tasks)
            if t.deadline and t.deadline.date() <= today
        ]

        # 3. Active goals (in_progress)
        active_goals = self.goal_repo.get_by_status(user_id, "in_progress")

        return {
            "habits": [
                {
                    "id": h.id,
                    "title": h.title,
                    "difficulty": h.difficulty,
                    "completed_today": h.last_completed_at
                    and h.last_completed_at.date() == today,
                    "streak": h.streak,
                    "coins_reward": h.coins_reward,
                    "exp_reward": h.exp_reward,
                }
                for h in daily_habits
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "difficulty": t.difficulty,
                    "status": t.status,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "coins_reward": t.coins_reward,
                    "exp_reward": t.exp_reward,
                }
                for t in due_tasks
            ],
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "difficulty": g.difficulty,
                    "progress": g.progress,
                    "deadline": g.deadline.isoformat() if g.deadline else None,
                    "coins_reward": g.coins_reward,
                    "exp_reward": g.exp_reward,
                }
                for g in active_goals
            ],
            "summary": {
                "total_habits": len(daily_habits),
                "completed_habits": sum(
                    1
                    for h in daily_habits
                    if h.last_completed_at and h.last_completed_at.date() == today
                ),
                "due_tasks": len(due_tasks),
                "active_goals": len(active_goals),
            },
        }

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
