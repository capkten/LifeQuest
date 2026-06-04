from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.todo import Task, TaskStatus, Habit
from app.models.checkin import DailyCheckin
from app.models.coin_transaction import CoinTransaction, CoinType
from app.models.user import User


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

    def get_task_trends(self, user_id: UUID, period: str = "week") -> List[dict]:
        now = datetime.now(timezone.utc)
        if period == "week":
            start = now - timedelta(days=6)
            group_expr = func.date(Task.completed_at)
        elif period == "month":
            start = now - timedelta(days=29)
            group_expr = func.date(Task.completed_at)
        else:  # year
            start = now - timedelta(days=364)
            group_expr = func.strftime("%Y-%m", Task.completed_at)

        # Completed tasks grouped by date
        completed_rows = (
            self.db.query(
                group_expr.label("date"),
                func.count().label("count"),
            )
            .filter(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= start,
            )
            .group_by("date")
            .all()
        )

        # Created tasks grouped by date
        if period == "year":
            created_group = func.strftime("%Y-%m", Task.created_at)
        else:
            created_group = func.date(Task.created_at)

        created_rows = (
            self.db.query(
                created_group.label("date"),
                func.count().label("count"),
            )
            .filter(
                Task.user_id == user_id,
                Task.created_at >= start,
            )
            .group_by("date")
            .all()
        )

        completed_map = {str(r.date): r.count for r in completed_rows}
        created_map = {str(r.date): r.count for r in created_rows}

        if period == "year":
            # Generate month labels
            result = []
            for i in range(12):
                dt = now - timedelta(days=29 * (11 - i))
                key = dt.strftime("%Y-%m")
                result.append({
                    "date": key,
                    "completed": completed_map.get(key, 0),
                    "created": created_map.get(key, 0),
                })
            return result
        else:
            days = 7 if period == "week" else 30
            result = []
            for i in range(days):
                dt = (now - timedelta(days=days - 1 - i)).date()
                key = str(dt)
                result.append({
                    "date": key,
                    "completed": completed_map.get(key, 0),
                    "created": created_map.get(key, 0),
                })
            return result

    def get_habit_stats(self, user_id: UUID, period: str = "week") -> List[dict]:
        now = datetime.now(timezone.utc)
        days = 7 if period == "week" else 30
        start = now - timedelta(days=days - 1)

        total_habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
        ).count()

        # Count habit completions per day via last_completed_at
        rows = (
            self.db.query(
                func.date(Habit.last_completed_at).label("date"),
                func.count().label("completed"),
            )
            .filter(
                Habit.user_id == user_id,
                Habit.is_active == True,
                Habit.last_completed_at >= start,
            )
            .group_by("date")
            .all()
        )

        completed_map = {str(r.date): r.completed for r in rows}

        result = []
        for i in range(days):
            dt = (now - timedelta(days=days - 1 - i)).date()
            key = str(dt)
            result.append({
                "date": key,
                "total": total_habits,
                "completed": completed_map.get(key, 0),
            })
        return result

    def get_coin_trends(self, user_id: UUID, period: str = "month") -> List[dict]:
        now = datetime.now(timezone.utc)
        if period == "week":
            days = 7
            start = now - timedelta(days=6)
            group_expr = func.date(CoinTransaction.created_at)
        elif period == "month":
            days = 30
            start = now - timedelta(days=29)
            group_expr = func.date(CoinTransaction.created_at)
        else:  # year
            days = 365
            start = now - timedelta(days=364)
            group_expr = func.strftime("%Y-%m", CoinTransaction.created_at)

        earned_rows = (
            self.db.query(
                group_expr.label("date"),
                func.coalesce(func.sum(CoinTransaction.amount), 0).label("amount"),
            )
            .filter(
                CoinTransaction.user_id == user_id,
                CoinTransaction.type == CoinType.EARN,
                CoinTransaction.created_at >= start,
            )
            .group_by("date")
            .all()
        )

        spent_rows = (
            self.db.query(
                group_expr.label("date"),
                func.coalesce(func.sum(CoinTransaction.amount), 0).label("amount"),
            )
            .filter(
                CoinTransaction.user_id == user_id,
                CoinTransaction.type == CoinType.SPEND,
                CoinTransaction.created_at >= start,
            )
            .group_by("date")
            .all()
        )

        earned_map = {str(r.date): r.amount for r in earned_rows}
        spent_map = {str(r.date): r.amount for r in spent_rows}

        if period == "year":
            result = []
            for i in range(12):
                dt = now - timedelta(days=29 * (11 - i))
                key = dt.strftime("%Y-%m")
                result.append({
                    "date": key,
                    "earned": earned_map.get(key, 0),
                    "spent": spent_map.get(key, 0),
                })
            return result
        else:
            result = []
            for i in range(days):
                dt = (now - timedelta(days=days - 1 - i)).date()
                key = str(dt)
                result.append({
                    "date": key,
                    "earned": earned_map.get(key, 0),
                    "spent": spent_map.get(key, 0),
                })
            return result

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
