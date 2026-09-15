import base64
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import update
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
    HabitCompletionCreate,
    HabitBackfillCreate,
    HabitLeaveCreate,
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
from app.timezone import local_date, day_start_utc, as_utc
from app.services.transaction import rollback_on_error
from app.services.habit_schedule import (
    is_due,
    is_excused_on,
    is_excluded_on,
    is_paused_on,
    month_has_active_schedule,
    month_period,
    previous_scheduled_date,
    week_has_active_schedule,
    week_start,
)
from app.services.habit_metrics import (
    calculate_habit_metrics,
    count_valid_completions,
    valid_completion_dates,
    weekly_target_progress,
)
from app.models.habit_completion import HabitCompletion
from app.models.habit_pause import HabitPauseInterval
from app.models.habit_leave import HabitLeaveInterval


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
        return local_date(value)

    @classmethod
    def _today(cls) -> date:
        return cls._local_date(datetime.now(timezone.utc))

    @classmethod
    def _today_start_utc(cls) -> datetime:
        return day_start_utc(cls._today())

    def _habit_pause_intervals(self, habit: Habit):
        return self.db.query(HabitPauseInterval).filter(
            HabitPauseInterval.habit_id == habit.id,
            HabitPauseInterval.user_id == habit.user_id,
        ).order_by(HabitPauseInterval.paused_on.asc(), HabitPauseInterval.created_at.asc()).all()

    def _habit_leave_intervals(self, habit: Habit):
        return self.db.query(HabitLeaveInterval).filter(
            HabitLeaveInterval.habit_id == habit.id,
            HabitLeaveInterval.user_id == habit.user_id,
        ).order_by(HabitLeaveInterval.leave_on.asc(), HabitLeaveInterval.created_at.asc()).all()

    def _completion_dates(self, habit: Habit) -> set[date]:
        records = self.db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.user_id == habit.user_id,
        ).all()
        return {record.completed_on for record in records}

    def _habit_metrics(self, habit: Habit, today: date, pause_intervals, leave_intervals):
        completion_dates = self._completion_dates(habit)
        created_on = self._local_date(habit.created_at) if habit.created_at else today
        return calculate_habit_metrics(
            habit,
            completion_dates,
            created_on,
            today,
            pause_intervals,
            leave_intervals,
            as_of=today,
        )

    def _set_completed_today(self, habit: Habit) -> Habit:
        today = self._today()
        pause_intervals = self._habit_pause_intervals(habit)
        leave_intervals = self._habit_leave_intervals(habit)
        habit.pause_intervals = pause_intervals
        habit.leave_intervals = leave_intervals
        habit.paused_today = not habit.is_active or is_paused_on(pause_intervals, today)
        habit.excused_today = is_excused_on(leave_intervals, today)
        habit.scheduled_today = is_due(habit, today) and not habit.paused_today and not habit.excused_today
        completion_dates = self._completion_dates(habit)
        habit.weekly_completed = 0
        habit.weekly_remaining = 0
        if habit.frequency == "weekly_target" and habit.weekly_target:
            habit.weekly_completed, habit.weekly_remaining = weekly_target_progress(
                habit, completion_dates, today, pause_intervals, leave_intervals,
            )
        metrics = self._habit_metrics(habit, today, pause_intervals, leave_intervals)
        habit.total_completed = metrics.total_completed
        habit.scheduled_count = metrics.scheduled_count
        habit.completed_count = metrics.completed_count
        habit.completion_rate = metrics.completion_rate
        habit.completed_today = today in valid_completion_dates(
            habit,
            completion_dates,
            pause_intervals,
            leave_intervals,
            as_of=today,
        )
        return habit

    def _weekly_completion_count(self, habit_id: UUID, target_date: date) -> int:
        current_week = week_start(target_date)
        return self._weekly_completion_count_for_week(habit_id, current_week, target_date)

    def _weekly_completion_count_for_week(
        self,
        habit_id: UUID,
        current_week: date,
        target_date: date = None,
    ) -> int:
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None:
            return 0
        period_end = min(current_week + timedelta(days=6), self._today())
        return count_valid_completions(
            habit,
            self._completion_dates(habit),
            current_week,
            period_end,
            self._habit_pause_intervals(habit),
            self._habit_leave_intervals(habit),
        )

    def _recalculate_habit_streak(self, habit: Habit, pause_intervals, leave_intervals) -> None:
        records = self.db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.user_id == habit.user_id,
        ).order_by(HabitCompletion.completed_on.asc()).all()
        reset_on = habit.streak_reset_on
        recorded_dates = {
            record.completed_on
            for record in records
        }
        completion_dates = valid_completion_dates(
            habit,
            recorded_dates,
            pause_intervals,
            leave_intervals,
            as_of=self._today(),
        )
        if reset_on is not None:
            completion_dates = {
                completed_on for completed_on in completion_dates if completed_on > reset_on
            }

        if habit.frequency in {"daily", "weekdays"}:
            valid_dates = {
                completed_on
                for completed_on in completion_dates
                if is_due(habit, completed_on)
                and not is_excluded_on(completed_on, pause_intervals, leave_intervals)
            }
            current_streak = 0
            best_streak = 0
            for completed_on in sorted(valid_dates):
                previous = previous_scheduled_date(
                    habit, completed_on, pause_intervals, leave_intervals,
                )
                current_streak = current_streak + 1 if previous in valid_dates else 1
                best_streak = max(best_streak, current_streak)
        elif habit.frequency == "weekly_target" and habit.weekly_target:
            counts = {}
            for completed_on in completion_dates:
                period = week_start(completed_on)
                counts[period] = counts.get(period, 0) + 1
            completed_periods = {
                period for period, count in counts.items()
                if count >= habit.weekly_target
                and week_has_active_schedule(habit, period, pause_intervals, leave_intervals)
            }
            current_streak = 0
            best_streak = 0
            lower_period = min(completed_periods) if completed_periods else None
            for period in sorted(completed_periods):
                previous = period - timedelta(days=7)
                while lower_period is not None and previous >= lower_period and not week_has_active_schedule(
                    habit, previous, pause_intervals, leave_intervals,
                ):
                    previous -= timedelta(days=7)
                current_streak = current_streak + 1 if (
                    lower_period is not None
                    and previous >= lower_period
                    and previous in completed_periods
                ) else 1
                best_streak = max(best_streak, current_streak)
        else:
            period_for = week_start if habit.frequency == "weekly" else month_period
            periods = {
                period_for(completed_on)
                for completed_on in completion_dates
            }
            current_streak = 0
            best_streak = 0
            lower_period = min(periods) if periods else None
            for period in sorted(periods):
                if habit.frequency == "weekly":
                    previous = period - timedelta(days=7)
                    while lower_period is not None and previous >= lower_period and not week_has_active_schedule(
                        habit, previous, pause_intervals, leave_intervals,
                    ):
                        previous -= timedelta(days=7)
                else:
                    previous = period - 1
                    while lower_period is not None and previous >= lower_period and not month_has_active_schedule(
                        habit, previous, pause_intervals, leave_intervals,
                    ):
                        previous -= 1
                current_streak = current_streak + 1 if (
                    lower_period is not None
                    and previous >= lower_period
                    and previous in periods
                ) else 1
                best_streak = max(best_streak, current_streak)

        if completion_dates:
            habit.streak = current_streak
            habit.best_streak = max(habit.best_streak or 0, best_streak, current_streak)
            latest_date = max(completion_dates)
            latest_record = next(
                (record for record in reversed(records) if record.completed_on == latest_date),
                None,
            )
            if latest_record and (
                habit.last_completed_at is None
                or self._local_date(habit.last_completed_at) <= latest_date
            ):
                habit.last_completed_at = latest_record.completed_at
        else:
            habit.streak = 0
        self.db.flush()

    def get_pause_intervals(self, habit_id: UUID, user_id: UUID):
        self.get_habit_for_user(habit_id, user_id)
        return self.db.query(HabitPauseInterval).filter(
            HabitPauseInterval.habit_id == habit_id,
            HabitPauseInterval.user_id == user_id,
        ).order_by(HabitPauseInterval.paused_on.asc(), HabitPauseInterval.created_at.asc()).all()

    def get_leave_intervals(self, habit_id: UUID, user_id: UUID):
        self.get_habit_for_user(habit_id, user_id)
        return self.db.query(HabitLeaveInterval).filter(
            HabitLeaveInterval.habit_id == habit_id,
            HabitLeaveInterval.user_id == user_id,
        ).order_by(HabitLeaveInterval.leave_on.asc(), HabitLeaveInterval.created_at.asc()).all()

    def _pause_habit_locked(self, habit: Habit, today: date) -> None:
        open_interval = self.db.query(HabitPauseInterval).filter(
            HabitPauseInterval.habit_id == habit.id,
            HabitPauseInterval.user_id == habit.user_id,
            HabitPauseInterval.resumed_on.is_(None),
        ).order_by(HabitPauseInterval.paused_on.desc()).first()
        if open_interval is None:
            self.db.add(HabitPauseInterval(
                habit_id=habit.id,
                user_id=habit.user_id,
                paused_on=today,
            ))
        habit.is_active = False

    def _resume_habit_locked(self, habit: Habit, today: date) -> None:
        open_interval = self.db.query(HabitPauseInterval).filter(
            HabitPauseInterval.habit_id == habit.id,
            HabitPauseInterval.user_id == habit.user_id,
            HabitPauseInterval.resumed_on.is_(None),
        ).order_by(HabitPauseInterval.paused_on.desc()).first()
        if open_interval is not None:
            open_interval.resumed_on = today
        habit.is_active = True

    @rollback_on_error
    def pause_habit(self, habit: Habit, user_id: UUID) -> Habit:
        today = self._today()
        self.user_repo.lock(user_id)
        self.db.refresh(habit)
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        self._pause_habit_locked(habit, today)
        self.db.commit()
        self.db.refresh(habit)
        return self._set_completed_today(habit)

    @rollback_on_error
    def resume_habit(self, habit: Habit, user_id: UUID) -> Habit:
        today = self._today()
        self.user_repo.lock(user_id)
        self.db.refresh(habit)
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        self._resume_habit_locked(habit, today)
        self.db.commit()
        self.db.refresh(habit)
        return self._set_completed_today(habit)

    @rollback_on_error
    def create_habit_leave(self, habit: Habit, user_id: UUID, leave_in: HabitLeaveCreate) -> Habit:
        today = self._today()
        self.user_repo.lock(user_id)
        self.db.refresh(habit)
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if leave_in.leave_on < today:
            raise HTTPException(status_code=422, detail="请假开始日期不能早于今天")
        overlap = self.db.query(HabitLeaveInterval.id).filter(
            HabitLeaveInterval.habit_id == habit.id,
            HabitLeaveInterval.user_id == user_id,
            HabitLeaveInterval.leave_on < leave_in.return_on,
            HabitLeaveInterval.return_on > leave_in.leave_on,
        ).first()
        if overlap:
            raise HTTPException(status_code=409, detail="请假区间与已有记录重叠")
        self.db.add(HabitLeaveInterval(
            habit_id=habit.id,
            user_id=user_id,
            leave_on=leave_in.leave_on,
            return_on=leave_in.return_on,
            reason=leave_in.reason,
        ))
        self.db.commit()
        self.db.refresh(habit)
        return self._set_completed_today(habit)

    @rollback_on_error
    def delete_habit_leave(self, habit: Habit, leave_id: UUID, user_id: UUID) -> Habit:
        self.user_repo.lock(user_id)
        self.db.refresh(habit)
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        leave = self.db.query(HabitLeaveInterval).filter(
            HabitLeaveInterval.id == leave_id,
            HabitLeaveInterval.habit_id == habit.id,
            HabitLeaveInterval.user_id == user_id,
        ).first()
        if leave is None:
            raise HTTPException(status_code=404, detail="请假记录不存在")
        self.db.delete(leave)
        self.db.commit()
        self.db.refresh(habit)
        return self._set_completed_today(habit)

    @rollback_on_error
    def backfill_habit(self, habit: Habit, user_id: UUID, completion_in: HabitBackfillCreate) -> Habit:
        today = self._today()
        completed_on = completion_in.completed_on
        self.user_repo.lock(user_id)
        self.db.refresh(habit)
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if completed_on >= today:
            raise HTTPException(status_code=422, detail="补记日期必须早于今天")
        if completed_on < today - timedelta(days=90):
            raise HTTPException(status_code=422, detail="补记最多支持最近 90 天")
        created_on = self._local_date(habit.created_at) if habit.created_at else today
        if completed_on < created_on:
            raise HTTPException(status_code=422, detail="补记日期不能早于习惯创建日期")
        if not is_due(habit, completed_on):
            raise HTTPException(status_code=409, detail="补记日期不是该习惯的计划日")
        pause_intervals = self._habit_pause_intervals(habit)
        leave_intervals = self._habit_leave_intervals(habit)
        if is_excluded_on(completed_on, pause_intervals, leave_intervals):
            raise HTTPException(status_code=409, detail="补记日期处于暂停或请假区间")

        existing = self.db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.user_id == user_id,
            HabitCompletion.completed_on == completed_on,
        ).first()
        if existing is not None:
            if completion_in.note:
                existing.note = completion_in.note
        else:
            if (
                habit.frequency == "weekly_target"
                and self._weekly_completion_count(habit.id, completed_on) >= habit.weekly_target
            ):
                raise HTTPException(status_code=409, detail="本周已完成目标次数")
            completed_at = day_start_utc(completed_on) + timedelta(hours=12)
            from app.services.habit_history import record_completion
            record_completion(
                self.db,
                habit,
                completed_at,
                note=completion_in.note,
                is_makeup=True,
            )
        self._recalculate_habit_streak(habit, pause_intervals, leave_intervals)
        self.db.commit()
        self.db.refresh(habit)
        return self._set_completed_today(habit)

    def get_habit_history(
        self,
        habit_id: UUID,
        user_id: UUID,
        start_on: Optional[date] = None,
        end_on: Optional[date] = None,
    ) -> dict:
        habit = self.get_habit_for_user(habit_id, user_id)
        today = self._today()
        end_on = end_on or today
        created_on = self._local_date(habit.created_at) if habit.created_at else end_on
        start_on = start_on or max(created_on, end_on - timedelta(days=83))
        if start_on > end_on:
            raise HTTPException(status_code=422, detail="历史开始日期不能晚于结束日期")
        if end_on > today:
            raise HTTPException(status_code=422, detail="历史结束日期不能晚于今天")
        if (end_on - start_on).days > 365:
            raise HTTPException(status_code=422, detail="历史查询最多支持 366 天")

        pause_intervals = self._habit_pause_intervals(habit)
        leave_intervals = self._habit_leave_intervals(habit)
        records = self.db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.user_id == user_id,
        ).all()
        completion_dates = {record.completed_on for record in records}
        records_by_date = {
            record.completed_on: record
            for record in records
            if start_on <= record.completed_on <= end_on
        }
        valid_dates = valid_completion_dates(
            habit,
            completion_dates,
            pause_intervals,
            leave_intervals,
            as_of=end_on,
        )
        days = []
        cursor = start_on
        while cursor <= end_on:
            paused = is_paused_on(pause_intervals, cursor)
            excused = is_excused_on(leave_intervals, cursor)
            scheduled = cursor >= created_on and is_due(habit, cursor) and not paused and not excused
            record = records_by_date.get(cursor) if cursor in valid_dates else None
            days.append({
                "date": cursor,
                "scheduled": scheduled,
                "completed": record is not None,
                "paused": paused,
                "excused": excused,
                "completion_id": record.id if record else None,
                "completed_at": record.completed_at if record else None,
                "note": record.note if record else None,
                "is_makeup": bool(record.is_makeup) if record else False,
            })
            cursor += timedelta(days=1)

        metrics = calculate_habit_metrics(
            habit,
            completion_dates,
            start_on,
            end_on,
            pause_intervals,
            leave_intervals,
        )
        return {
            "habit_id": habit.id,
            "start_on": start_on,
            "end_on": end_on,
            "total_completed": metrics.total_completed,
            "scheduled_count": metrics.scheduled_count,
            "completed_count": metrics.completed_count,
            "completion_rate": metrics.completion_rate,
            "days": days,
        }

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

    @rollback_on_error
    def update_habit(self, habit: Habit, habit_in: HabitUpdate) -> Habit:
        self.user_repo.lock(habit.user_id)
        self.db.refresh(habit)
        update_data = habit_in.model_dump(exclude_unset=True)
        old_frequency = habit.frequency
        old_weekdays = habit.weekdays
        old_weekly_target = habit.weekly_target
        desired_active = update_data.pop("is_active", None)
        frequency = update_data.get("frequency", habit.frequency)
        weekdays = update_data.get("weekdays", habit.weekdays)
        weekly_target = update_data.get("weekly_target", habit.weekly_target)
        if frequency is None or (frequency == "weekdays" and not weekdays):
            raise HTTPException(status_code=422, detail="指定日期习惯至少需要一天")
        if frequency != "weekdays":
            if update_data.get("weekdays") is not None:
                raise HTTPException(status_code=422, detail="仅指定日期习惯可设置执行日期")
            update_data["weekdays"] = None
            habit.weekdays = None
        if frequency == "weekly_target" and weekly_target is None:
            raise HTTPException(status_code=422, detail="每周目标习惯需要设置完成次数")
        if frequency != "weekly_target":
            if update_data.get("weekly_target") is not None:
                raise HTTPException(status_code=422, detail="仅每周目标习惯可设置完成次数")
            update_data["weekly_target"] = None
            habit.weekly_target = None
        if (
            frequency != old_frequency
            or weekdays != old_weekdays
            or weekly_target != old_weekly_target
        ):
            today = self._today()
            completed_today = self.db.query(HabitCompletion.id).filter(
                HabitCompletion.habit_id == habit.id,
                HabitCompletion.user_id == habit.user_id,
                HabitCompletion.completed_on == today,
            ).first() is not None
            reset_on = today if completed_today else today - timedelta(days=1)
            update_data["streak"] = 0
            update_data["streak_reset_on"] = reset_on
            habit.streak_reset_on = reset_on
        if desired_active is False:
            self._pause_habit_locked(habit, self._today())
        elif desired_active is True:
            self._resume_habit_locked(habit, self._today())
        return self._set_completed_today(self.habit_repo.update(habit, update_data))

    def delete_habit(self, habit_id: UUID) -> bool:
        return self.habit_repo.delete(habit_id)

    @rollback_on_error
    def complete_habit(
        self,
        habit: Habit,
        user_id: UUID,
        completion_in: Optional[HabitCompletionCreate] = None,
    ) -> Habit:
        """Mark habit as completed for today, incrementing streak and awarding rewards."""
        now = datetime.now(timezone.utc)
        completed_on = self._local_date(now)
        self.user_repo.lock(user_id)
        self.db.refresh(habit)
        if habit.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        from app.services.habit_history import record_completion
        if not habit.is_active:
            raise HTTPException(status_code=409, detail="习惯已暂停")
        if not is_due(habit, completed_on):
            raise HTTPException(status_code=409, detail="今天不是该习惯的计划日")
        pause_intervals = self._habit_pause_intervals(habit)
        leave_intervals = self._habit_leave_intervals(habit)
        if is_excluded_on(completed_on, pause_intervals, leave_intervals):
            raise HTTPException(status_code=409, detail="今天处于暂停或请假区间")
        existing = self.db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.user_id == user_id,
            HabitCompletion.completed_on == completed_on,
        ).first()
        if existing is not None:
            if completion_in is not None and completion_in.note:
                existing.note = completion_in.note
            self.db.commit()
            return self._set_completed_today(habit)
        weekly_target = habit.weekly_target if habit.frequency == "weekly_target" else None
        if weekly_target is not None and self._weekly_completion_count(habit.id, completed_on) >= weekly_target:
            raise HTTPException(status_code=409, detail="本周已完成目标次数")
        record_completion(
            self.db,
            habit,
            now,
            note=completion_in.note if completion_in is not None else None,
        )
        self._recalculate_habit_streak(habit, pause_intervals, leave_intervals)

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
    def _validate_task_links(self, user_id: UUID, data: dict) -> None:
        from app.services.project import ProjectService

        project_id = data.get("project_id")
        service = ProjectService(self.db)
        if project_id is not None:
            service.get_project_for_user_locked(project_id, user_id)
        for field, getter in (
            ("phase_id", service.get_phase_for_project),
            ("milestone_id", service.get_milestone_for_project),
        ):
            if data.get(field) is not None:
                if project_id is None:
                    raise HTTPException(status_code=400, detail="Task association requires a project")
                if field == "phase_id":
                    getter(data[field], project_id, for_update=True)
                else:
                    service.get_milestone_for_project_locked(data[field], project_id)

    @rollback_on_error
    def create_task(self, user_id: UUID, task_in: TaskCreate) -> Task:
        self.user_repo.lock(user_id)
        data = task_in.model_dump()
        data["user_id"] = user_id
        self._validate_task_links(user_id, data)
        return self.task_repo.create(data)

    def get_tasks(self, user_id: UUID) -> List[Task]:
        return self.task_repo.get_by_user(user_id)

    def get_tasks_by_project(self, project_id: UUID, user_id: UUID) -> List[Task]:
        return self.db.query(Task).filter(
            Task.user_id == user_id, Task.project_id == project_id
        ).all()

    @rollback_on_error
    def update_task(self, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)
        self.user_repo.lock(task.user_id)
        self.db.refresh(task)
        if "project_id" in update_data and update_data["project_id"] != task.project_id:
            update_data.setdefault("phase_id", None)
            update_data.setdefault("milestone_id", None)
        links = {field: update_data.get(field, getattr(task, field)) for field in ("project_id", "phase_id", "milestone_id")}
        self._validate_task_links(task.user_id, links)
        status = update_data.pop("status", None)
        nullable = {"project_id", "phase_id", "milestone_id", "deadline", "start_date", "description"}
        for field, value in update_data.items():
            if value is not None or field in nullable:
                setattr(task, field, value)
        self.db.flush()
        if status == TaskStatus.COMPLETED:
            task = self.complete_task(task, task.user_id)
        elif status is not None:
            task.status = status
            task.completed_at = None
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: UUID) -> bool:
        return self.task_repo.delete(task_id)

    @rollback_on_error
    def complete_task(self, task: Task, user_id: UUID) -> Task:
        """Complete a task and award coins and experience to the user."""
        now = datetime.now(timezone.utc)
        self.user_repo.lock(user_id)
        self.db.refresh(task)
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        changed = self.db.execute(update(Task).where(
            Task.id == task.id,
            Task.user_id == user_id,
            Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
        ).values(status=TaskStatus.COMPLETED, completed_at=now)).rowcount
        if not changed:
            self.db.refresh(task)
            if task.status == TaskStatus.CANCELLED:
                raise HTTPException(status_code=409, detail="已取消的任务不能完成")
            if task.status != TaskStatus.COMPLETED:
                raise HTTPException(status_code=409, detail="当前任务状态不能完成")
            self.db.commit()
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

    @rollback_on_error
    def complete_goal(self, goal: Goal, user_id: UUID) -> Goal:
        """Complete a goal and award coins and experience to the user."""
        now = datetime.now(timezone.utc)
        self.user_repo.lock(user_id)
        self.db.refresh(goal)
        if goal.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        changed = self.db.execute(update(Goal).where(
            Goal.id == goal.id,
            Goal.user_id == user_id,
            Goal.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
        ).values(status=TaskStatus.COMPLETED, progress=GOAL_COMPLETED_PROGRESS)).rowcount
        if not changed:
            self.db.refresh(goal)
            if goal.status == TaskStatus.CANCELLED:
                raise HTTPException(status_code=409, detail="已取消的目标不能完成")
            if goal.status != TaskStatus.COMPLETED:
                raise HTTPException(status_code=409, detail="当前目标状态不能完成")
            self.db.commit()
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
        self.title_service.check_and_unlock(uid, "level", user.level, commit=False)

    # --- Daily summary ---
    @staticmethod
    def _habit_daily_payload(habit: Habit) -> dict:
        return {
            "id": habit.id,
            "title": habit.title,
            "difficulty": habit.difficulty,
            "completed_today": habit.completed_today,
            "streak": habit.streak,
            "coins_reward": habit.coins_reward,
            "exp_reward": habit.exp_reward,
            "frequency": habit.frequency,
            "weekly_target": habit.weekly_target,
            "weekly_completed": habit.weekly_completed,
            "weekly_remaining": habit.weekly_remaining,
            "total_completed": habit.total_completed,
            "scheduled_count": habit.scheduled_count,
            "completed_count": habit.completed_count,
            "completion_rate": habit.completion_rate,
            "is_active": habit.is_active,
            "paused_today": habit.paused_today,
            "pause_intervals": habit.pause_intervals,
            "scheduled_today": habit.scheduled_today,
            "excused_today": habit.excused_today,
            "leave_intervals": habit.leave_intervals,
        }

    def get_daily_summary(self, user_id: UUID) -> dict:
        """Get today's tasks overview: habits due today, tasks due today, active goals."""
        today = self._today()

        # 1. Active habits due today
        habits = self.habit_repo.get_active_by_user(user_id)
        daily_habits = []
        for h in habits:
            self._set_completed_today(h)
            if h.scheduled_today:
                daily_habits.append(self._habit_daily_payload(h))

        # 2. Tasks with deadline today (or overdue and still pending)
        pending_tasks = self.task_repo.get_by_status(user_id, "pending")
        in_progress_tasks = self.task_repo.get_by_status(user_id, "in_progress")
        due_tasks = [
            t
            for t in (pending_tasks + in_progress_tasks)
            if t.deadline and self._local_date(t.deadline) <= today
        ]

        # 3. Active goals (in_progress)
        active_goals = self.goal_repo.get_by_status(user_id, "in_progress")

        return {
            "habits": daily_habits,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "difficulty": t.difficulty,
                    "status": t.status,
                    "deadline": as_utc(t.deadline).isoformat() if t.deadline else None,
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
                    "deadline": as_utc(g.deadline).isoformat() if g.deadline else None,
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
                    if h["completed_today"]
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

    @rollback_on_error
    def complete_subtask(self, subtask: Subtask, user_id: UUID) -> Subtask:
        self.user_repo.lock(user_id)
        self.db.refresh(subtask)
        self.get_task_for_user(subtask.task_id, user_id)
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
