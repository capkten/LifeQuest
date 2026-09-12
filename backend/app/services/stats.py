from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import List
from uuid import UUID

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.models.todo import Task, TaskStatus, Habit
from app.models.checkin import DailyCheckin
from app.models.coin_transaction import CoinTransaction, CoinType
from app.models.user import User
from app.models.habit_completion import HabitCompletion
from app.timezone import local_date, day_start_utc


def _get_required_exp(level: int) -> int:
    return int(100 * (1.5 ** (level - 1)))


class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, user_id: UUID) -> dict:
        total_tasks_completed = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
        ).count()

        total_habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
        ).count()

        # Current streak: max streak among active habits
        max_streak = self.db.query(func.max(Habit.streak)).filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
        ).scalar() or 0

        user = self.db.query(User).filter(User.id == user_id).first()

        days_active = self.db.query(func.count(func.distinct(DailyCheckin.checkin_date))).filter(
            DailyCheckin.user_id == user_id,
        ).scalar() or 0

        return {
            "total_tasks_completed": total_tasks_completed,
            "total_habits": total_habits,
            "current_streak": max_streak,
            "total_coins_earned": user.total_coins_earned if user else 0,
            "total_exp": user.experience if user else 0,
            "current_level": user.level if user else 1,
            "days_active": days_active,
        }

    def _periods(self, period: str) -> list:
        current = local_date(datetime.now(timezone.utc))
        if period == "year":
            month_index = current.year * 12 + current.month - 1
            starts = [date(index // 12, index % 12 + 1, 1) for index in range(month_index - 11, month_index + 2)]
        else:
            days = 7 if period == "week" else 30
            starts = [current - timedelta(days=days - 1 - offset) for offset in range(days + 1)]
        return [(start.strftime("%Y-%m") if period == "year" else start.isoformat(),
                 day_start_utc(start), day_start_utc(end)) for start, end in zip(starts, starts[1:])]

    def _aggregate(self, timestamp, value, filters: list, periods: list) -> dict:
        bucket = case(*[(and_(timestamp >= start, timestamp < end), label) for label, start, end in periods])
        rows = self.db.query(bucket.label("period"), value.label("value")).filter(
            *filters, timestamp >= periods[0][1], timestamp < periods[-1][2],
        ).group_by(bucket).all()
        return {row.period: row.value for row in rows}

    def get_task_trends(self, user_id: UUID, period: str = "week") -> List[dict]:
        periods = self._periods(period)
        completed = self._aggregate(Task.completed_at, func.count(), [
            Task.user_id == user_id, Task.status == TaskStatus.COMPLETED,
        ], periods)
        created = self._aggregate(Task.created_at, func.count(), [Task.user_id == user_id], periods)
        return [{"date": label, "completed": completed.get(label, 0), "created": created.get(label, 0)}
                for label, start, end in periods]

    def get_habit_stats(self, user_id: UUID, period: str = "week") -> List[dict]:
        periods = self._periods("week" if period == "week" else "month")
        first_day, last_day = local_date(periods[0][1]), local_date(periods[-1][2])
        completions = set(self.db.query(HabitCompletion.habit_id, HabitCompletion.completed_on).filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.completed_on >= first_day,
            HabitCompletion.completed_on < last_day,
        ).all())
        habits = self.db.query(Habit).filter(Habit.user_id == user_id).all()
        completed = Counter(completed_on.isoformat() for habit_id, completed_on in completions)
        total = sum(habit.is_active for habit in habits)
        return [{"date": label, "total": total, "completed": completed.get(label, 0)}
                for label, start, end in periods]

    def get_coin_trends(self, user_id: UUID, period: str = "month") -> List[dict]:
        periods = self._periods(period)
        earned = self._aggregate(CoinTransaction.created_at, func.sum(CoinTransaction.amount), [
            CoinTransaction.user_id == user_id, CoinTransaction.type == CoinType.EARN,
        ], periods)
        spent = self._aggregate(CoinTransaction.created_at, func.sum(CoinTransaction.amount), [
            CoinTransaction.user_id == user_id, CoinTransaction.type == CoinType.SPEND,
        ], periods)
        return [{"date": label, "earned": earned.get(label, 0), "spent": spent.get(label, 0)}
                for label, start, end in periods]

    def get_level_progress(self, user_id: UUID) -> dict:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"current_level": 1, "current_exp": 0, "required_exp": 100, "exp_percent": 0}

        required = _get_required_exp(user.level)
        percent = round((user.experience / required) * 100, 1) if required > 0 else 0

        return {
            "current_level": user.level,
            "current_exp": user.experience,
            "required_exp": required,
            "exp_percent": percent,
        }
