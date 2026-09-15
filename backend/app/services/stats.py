from collections import Counter, defaultdict
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
from app.models.habit_leave import HabitLeaveInterval
from app.models.habit_pause import HabitPauseInterval
from app.services.habit_metrics import valid_completion_dates
from app.services.habit_schedule import (
    is_due,
    is_excluded_on,
    week_has_active_schedule,
    week_start,
)
from app.timezone import local_date, day_start_utc, today as china_today


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
            "total_exp": user.total_experience if user else 0,
            "current_level": user.level if user else 1,
            "days_active": days_active,
        }

    def _periods(self, period: str) -> list:
        current = china_today()
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
        first_day = date.fromisoformat(periods[0][0])
        last_day = date.fromisoformat(periods[-1][0])
        today = china_today()
        completion_rows = self.db.query(HabitCompletion.habit_id, HabitCompletion.completed_on).filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.completed_on >= first_day,
            HabitCompletion.completed_on <= min(last_day, today),
        ).all()
        habits = self.db.query(Habit).filter(Habit.user_id == user_id).all()
        habits_by_id = {habit.id: habit for habit in habits}
        pause_by_habit = defaultdict(list)
        for interval in self.db.query(HabitPauseInterval).filter(
            HabitPauseInterval.user_id == user_id,
        ).all():
            pause_by_habit[interval.habit_id].append(interval)
        leave_by_habit = defaultdict(list)
        for interval in self.db.query(HabitLeaveInterval).filter(
            HabitLeaveInterval.user_id == user_id,
        ).all():
            leave_by_habit[interval.habit_id].append(interval)

        dates_by_habit = defaultdict(set)
        for habit_id, completed_on in completion_rows:
            dates_by_habit[habit_id].add(completed_on)

        completed = Counter()
        weekly_completed = defaultdict(Counter)
        for habit_id, completion_dates in dates_by_habit.items():
            habit = habits_by_id.get(habit_id)
            if habit is None:
                # Deleted habits retain their completion facts but no longer have
                # schedule metadata with which to invalidate an old record.
                valid_dates = {
                    completed_on for completed_on in completion_dates if completed_on <= today
                }
            else:
                valid_dates = valid_completion_dates(
                    habit,
                    completion_dates,
                    pause_by_habit[habit_id],
                    leave_by_habit[habit_id],
                    as_of=today,
                )
            if habit is not None and habit.frequency == "weekly_target" and habit.weekly_target:
                for completed_on in valid_dates:
                    if first_day <= completed_on <= last_day:
                        week_bucket = week_start(completed_on)
                        bucket = max(week_bucket, first_day)
                        weekly_completed[bucket.isoformat()][habit_id] += 1
            else:
                for completed_on in valid_dates:
                    if first_day <= completed_on <= last_day:
                        completed[completed_on.isoformat()] += 1

        for bucket, habit_counts in weekly_completed.items():
            for habit_id, count in habit_counts.items():
                target = habits_by_id[habit_id].weekly_target
                completed[bucket] += min(count, target)

        scheduled = Counter()
        period_end = min(last_day, today)
        for habit in habits:
            created_on = local_date(habit.created_at) if habit.created_at else first_day
            if habit.frequency == "weekly_target" and habit.weekly_target:
                current_week = week_start(first_day)
                while current_week <= period_end:
                    bucket = max(current_week, first_day)
                    if week_has_active_schedule(
                        habit,
                        current_week,
                        pause_by_habit[habit.id],
                        leave_by_habit[habit.id],
                    ) and bucket <= last_day:
                        scheduled[bucket.isoformat()] += habit.weekly_target
                    current_week += timedelta(days=7)
                continue
            target = first_day
            while target <= period_end:
                if (
                    target >= created_on
                    and is_due(habit, target)
                    and not is_excluded_on(
                        target,
                        pause_by_habit[habit.id],
                        leave_by_habit[habit.id],
                    )
                ):
                    scheduled[target.isoformat()] += 1
                target += timedelta(days=1)

        return [{"date": label, "total": scheduled.get(label, 0), "completed": completed.get(label, 0)}
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
