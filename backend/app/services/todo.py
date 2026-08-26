import base64
import threading
from functools import wraps
from datetime import date, datetime, timezone
from typing import List
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import or_, update
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
from app.services.content_catalog import (
    CULTIVATION_REWARD_BASES,
    QUALITY_FACTORS,
    TODO_SOURCE_PREFIXES,
    source_label,
)
from app.services.title import TitleService
from app.services.cultivation import CultivationService


_TODO_COMPLETION_LOCK = threading.Lock()
_APP_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _completion_guard(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        with _TODO_COMPLETION_LOCK:
            return method(self, *args, **kwargs)

    return guarded


class TodoService:
    TASK_IMPORTANCE = {
        "low": 0.8,
        "medium": 1.0,
        "high": 1.3,
        "urgent": 1.6,
    }

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
        self.cultivation_service = CultivationService(db)

    @staticmethod
    def _local_date(value: datetime) -> date:
        """Return the calendar date in the app's user-facing timezone."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(_APP_TIMEZONE).date()

    @classmethod
    def _today(cls) -> date:
        return cls._local_date(datetime.now(timezone.utc))

    @classmethod
    def _today_start_utc(cls) -> datetime:
        local_now = datetime.now(timezone.utc).astimezone(_APP_TIMEZONE)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_start.astimezone(timezone.utc)

    @staticmethod
    def _set_completed_today(habit: Habit) -> Habit:
        if habit.last_completed_at is None:
            habit.completed_today = False
            return habit

        completed_at = habit.last_completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        else:
            completed_at = completed_at.astimezone(timezone.utc)
        habit.completed_today = TodoService._local_date(completed_at) == TodoService._today()
        return habit

    @staticmethod
    def _coin_source_id(source: str, entity_id: UUID, completed_on: date = None) -> str:
        source_value = getattr(source, "value", source)
        compact_uuid = base64.urlsafe_b64encode(entity_id.bytes).decode("ascii").rstrip("=")
        source_id = f"{TODO_SOURCE_PREFIXES[source_value]}:{compact_uuid}"
        if source_value == "habit":
            source_id = f"{source_id}:{completed_on:%Y%m%d}"
        return source_id

    @staticmethod
    def _completion_quality(deadline, completed_at: datetime) -> float:
        if deadline is None:
            return 1.0
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        else:
            deadline = deadline.astimezone(timezone.utc)
        if completed_at < deadline:
            return QUALITY_FACTORS["early"]
        if completed_at > deadline:
            return QUALITY_FACTORS["delayed"]
        return QUALITY_FACTORS["on_time"]

    # --- Ownership verification (returns object or raises HTTPException) ---
    def get_habit_for_user(self, habit_id: UUID, user_id: UUID) -> Habit:
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None:
            raise HTTPException(status_code=404, detail="Habit not found")
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return self._set_completed_today(habit)

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
        return self._set_completed_today(self.habit_repo.create(data))

    def get_habits(self, user_id: UUID) -> List[Habit]:
        return [self._set_completed_today(habit) for habit in self.habit_repo.get_by_user(user_id)]

    def update_habit(self, habit: Habit, habit_in: HabitUpdate) -> Habit:
        update_data = habit_in.model_dump(exclude_unset=True)
        return self._set_completed_today(self.habit_repo.update(habit, update_data))

    def delete_habit(self, habit_id: UUID) -> bool:
        return self.habit_repo.delete(habit_id)

    @_completion_guard
    def complete_habit(self, habit: Habit, user_id: UUID) -> Habit:
        """Mark habit as completed for today, incrementing streak and awarding rewards."""
        now = datetime.now(timezone.utc)
        day_start = self._today_start_utc()
        completed_on = self._local_date(now)
        changed = self.db.execute(update(Habit).where(
            Habit.id == habit.id, Habit.user_id == user_id,
            or_(Habit.last_completed_at.is_(None), Habit.last_completed_at < day_start),
        ).values(last_completed_at=now, streak=Habit.streak + 1).execution_options(
            synchronize_session=False
        )).rowcount
        if not changed:
            self.db.refresh(habit)
            return self._set_completed_today(habit)
        self.db.execute(update(Habit).where(
            Habit.id == habit.id, Habit.streak > Habit.best_streak
        ).values(best_streak=Habit.streak).execution_options(synchronize_session=False))

        user = self.user_repo.get_by_id(user_id)
        settlement = None
        if user:
            settlement = self._update_rewards(
                user, habit.coins_reward, habit.exp_reward, CoinSource.HABIT,
                habit.difficulty, source_key=f"todo:habit:{habit.id}:{completed_on.isoformat()}",
                coin_source_id=self._coin_source_id(CoinSource.HABIT, habit.id, completed_on),
                cultivation_base_exp=CULTIVATION_REWARD_BASES["habit"],
            )
            self._check_achievements(user)
            self.db.commit()

        self.habit_repo.db.refresh(habit)
        habit.cultivation_reward = settlement
        return self._set_completed_today(habit)

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

    @_completion_guard
    def complete_task(self, task: Task, user_id: UUID) -> Task:
        """Complete a task and award coins and experience to the user."""
        now = datetime.now(timezone.utc)
        changed = self.db.execute(update(Task).where(
            Task.id == task.id, Task.user_id == user_id, Task.status != TaskStatus.COMPLETED
        ).values(status=TaskStatus.COMPLETED, completed_at=now)).rowcount
        if not changed:
            self.db.refresh(task)
            return task

        user = self.user_repo.get_by_id(user_id)
        settlement = None
        if user:
            settlement = self._update_rewards(
                user,
                task.coins_reward,
                task.exp_reward,
                CoinSource.TASK,
                task.difficulty,
                importance=self.TASK_IMPORTANCE.get(task.priority, 1.0),
                source_key=f"todo:task:{task.id}",
                coin_source_id=self._coin_source_id(CoinSource.TASK, task.id),
                cultivation_base_exp=CULTIVATION_REWARD_BASES["task"],
                quality=self._completion_quality(task.deadline, now),
            )
            self._check_achievements(user)
            self.db.commit()

        self.task_repo.db.refresh(task)
        task.cultivation_reward = settlement
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

    @_completion_guard
    def complete_goal(self, goal: Goal, user_id: UUID) -> Goal:
        """Complete a goal and award coins and experience to the user."""
        now = datetime.now(timezone.utc)
        changed = self.db.execute(update(Goal).where(
            Goal.id == goal.id, Goal.user_id == user_id, Goal.status != TaskStatus.COMPLETED
        ).values(status=TaskStatus.COMPLETED, progress=GOAL_COMPLETED_PROGRESS)).rowcount
        if not changed:
            self.db.refresh(goal)
            return goal

        user = self.user_repo.get_by_id(user_id)
        settlement = None
        if user:
            settlement = self._update_rewards(
                user, goal.coins_reward, goal.exp_reward, CoinSource.GOAL,
                goal.difficulty, source_key=f"todo:goal:{goal.id}",
                coin_source_id=self._coin_source_id(CoinSource.GOAL, goal.id),
                cultivation_base_exp=CULTIVATION_REWARD_BASES["goal"],
                quality=self._completion_quality(goal.deadline, now),
            )
            self._check_achievements(user)
            self.db.commit()

        self.goal_repo.db.refresh(goal)
        goal.cultivation_reward = settlement
        return goal

    def _update_rewards(
        self,
        user,
        coins: int,
        exp: int,
        source: str,
        difficulty: str = "medium",
        importance: float = 1.0,
        quality: float = 1.0,
        cultivation_base_exp: int | None = None,
        source_key: str | None = None,
        coin_source_id: str | None = None,
    ):
        """Update user coins and experience in a single transaction."""
        settlement = self.cultivation_service.settle_todo_reward(
            user.id,
            source,
            cultivation_base_exp if cultivation_base_exp is not None else exp,
            difficulty,
            quality=quality,
            importance=importance,
            source_key=source_key,
            apply_legacy_user_rewards=False,
        )
        if settlement._already_settled:
            return settlement

        self.user_repo._update_coins_no_commit(user, coins)
        self.user_repo._update_experience_no_commit(user, exp)
        self.coin_repo._create_no_commit(
            {
                "user_id": user.id,
                "amount": coins,
                "type": CoinType.EARN,
                "source": source,
                "source_id": coin_source_id,
                "description": f"{source_label(source)}奖励",
            }
        )
        return settlement

    def _check_achievements(self, user) -> None:
        """Check and unlock achievements based on current user state."""
        from sqlalchemy import func

        self.db.flush()
        uid = user.id
        # task_count: count completed tasks
        completed_tasks = self.task_repo.db.query(Task).filter(
            Task.user_id == uid, Task.status == TaskStatus.COMPLETED
        ).count()
        self.achievement_service.check_and_unlock(uid, "task_count", completed_tasks, commit=False)

        # habit_streak: best streak across all habits
        max_streak = self.habit_repo.db.query(func.max(Habit.best_streak)).filter(
            Habit.user_id == uid
        ).scalar() or 0
        self.achievement_service.check_and_unlock(uid, "habit_streak", max_streak, commit=False)

        # level
        self.achievement_service.check_and_unlock(uid, "level", user.level, commit=False)

        # coins_earned: use persisted cumulative counter
        self.achievement_service.check_and_unlock(uid, "coins_earned", user.total_coins_earned, commit=False)

        # goal_count: count completed goals
        completed_goals = self.goal_repo.db.query(Goal).filter(
            Goal.user_id == uid, Goal.status == TaskStatus.COMPLETED
        ).count()
        self.achievement_service.check_and_unlock(uid, "goal_count", completed_goals, commit=False)

        # Check titles based on level
        self.title_service.check_and_unlock(uid, "level", user.level)

    # --- Daily summary ---
    def get_daily_summary(self, user_id: UUID) -> dict:
        """Get today's tasks overview: habits due today, tasks due today, active goals."""
        today = self._today()

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

    @_completion_guard
    def complete_subtask(self, subtask: Subtask, user_id: UUID) -> Subtask:
        if not subtask.is_completed:
            subtask.is_completed = True
        settlement = self.cultivation_service.settle_todo_reward(
            user_id,
            "subtask",
            CULTIVATION_REWARD_BASES["subtask"],
            "medium",
            source_key=f"todo:subtask:{subtask.id}",
        )
        subtask.cultivation_reward = settlement
        self.db.commit()
        self.db.refresh(subtask)
        subtask.cultivation_reward = settlement
        return subtask
