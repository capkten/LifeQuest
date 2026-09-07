import json
from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from threading import Lock
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.task_schedule import TaskOccurrence, TaskSchedule
from app.models.todo import Task, TaskStatus
from app.schemas.task_schedule import (
    TaskScheduleCreate,
    TaskScheduleStateResponse,
)


_MATERIALIZE_LOCK = Lock()


class TaskScheduleService:
    APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
    TIMEZONE_NAME = "Asia/Shanghai"

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def _local_date(cls, value: Optional[datetime]) -> Optional[date]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(cls.APP_TIMEZONE).date()

    @classmethod
    def _now_utc(cls) -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _today(cls) -> date:
        return cls._now_utc().astimezone(cls.APP_TIMEZONE).date()

    @classmethod
    def _aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _error(status_code: int, code: str, message: str) -> HTTPException:
        return HTTPException(
            status_code=status_code,
            detail={"code": code, "message": message},
        )

    @classmethod
    def _default_start_date(cls, task: Task) -> date:
        return cls._local_date(task.deadline) or cls._today()

    @classmethod
    def _normalized_schedule_values(cls, task: Task, data: TaskScheduleCreate) -> dict:
        starts_on = data.starts_on or cls._default_start_date(task)
        weekdays = list(data.weekdays or [])
        if data.rule_type == "weekly" and not weekdays:
            weekdays = [starts_on.weekday()]
        day_of_month = data.day_of_month
        if data.rule_type == "monthly" and day_of_month is None:
            day_of_month = starts_on.day
        return {
            "rule_type": data.rule_type,
            "interval": data.interval,
            "weekdays_json": json.dumps(weekdays, separators=(",", ":")),
            "day_of_month": day_of_month,
            "starts_on": starts_on,
            "ends_on": data.ends_on,
            "timezone": data.timezone,
            "is_active": data.is_active,
        }

    def create_for_task(self, task: Task, data: TaskScheduleCreate) -> TaskSchedule:
        schedule = TaskSchedule(task_id=task.id, **self._normalized_schedule_values(task, data))
        self.db.add(schedule)
        self.db.flush()
        return schedule

    def replace_for_task(self, task: Task, data: Optional[TaskScheduleCreate]) -> Optional[TaskSchedule]:
        schedule = task.schedule
        if data is None:
            if schedule is not None:
                self.db.delete(schedule)
                self.db.flush()
            return None

        values = self._normalized_schedule_values(task, data)
        if schedule is None:
            schedule = self.create_for_task(task, data)
        else:
            for key, value in values.items():
                setattr(schedule, key, value)
            self.db.flush()
        return schedule

    @classmethod
    def _matches(cls, schedule: TaskSchedule, target_date: date) -> bool:
        if target_date < schedule.starts_on:
            return False
        if schedule.ends_on and target_date > schedule.ends_on:
            return False

        interval = max(1, schedule.interval or 1)
        if schedule.rule_type == "daily":
            return (target_date - schedule.starts_on).days % interval == 0

        if schedule.rule_type == "weekly":
            if target_date.weekday() not in schedule.weekdays:
                return False
            weeks = (target_date - schedule.starts_on).days // 7
            return weeks % interval == 0

        if schedule.rule_type == "monthly":
            if target_date.day != schedule.day_of_month:
                return False
            months = (
                (target_date.year - schedule.starts_on.year) * 12
                + target_date.month
                - schedule.starts_on.month
            )
            return months >= 0 and months % interval == 0

        return False

    @classmethod
    def iter_occurrence_dates(cls, schedule: TaskSchedule, target_date: date):
        current = schedule.starts_on
        while current <= target_date:
            if cls._matches(schedule, current):
                yield current
            current += timedelta(days=1)

    def materialize_task_until(
        self,
        task: Task,
        target_date: date,
        *,
        commit: bool = False,
    ) -> list[TaskOccurrence]:
        schedule = task.schedule
        if schedule is None or not schedule.is_active:
            return []

        with _MATERIALIZE_LOCK:
            all_occurrences = self.db.query(TaskOccurrence).filter(
                TaskOccurrence.task_id == task.id,
            ).all()
            existing = {
                occurrence.occurrence_date: occurrence
                for occurrence in all_occurrences
                if occurrence.occurrence_date <= target_date
            }
            existing_source_keys = {occurrence.source_key for occurrence in all_occurrences}
            for occurrence_date in self.iter_occurrence_dates(schedule, target_date):
                source_key = f"task:{task.id}:{occurrence_date.isoformat()}"
                if occurrence_date in existing or source_key in existing_source_keys:
                    continue
                occurrence = TaskOccurrence(
                    task_id=task.id,
                    occurrence_date=occurrence_date,
                    source_key=source_key,
                )
                self.db.add(occurrence)
                existing[occurrence_date] = occurrence
                existing_source_keys.add(source_key)
            self.db.flush()
            if commit:
                self.db.commit()

        return [existing[key] for key in sorted(existing)]

    def get_occurrences_for_range(
        self,
        task: Task,
        start_date: date,
        end_date: date,
    ) -> list[TaskOccurrence]:
        """Read scheduled occurrences without changing the session or database."""
        if start_date > end_date:
            return []

        with self.db.no_autoflush:
            persisted = self.db.query(TaskOccurrence).filter(
                TaskOccurrence.task_id == task.id,
                TaskOccurrence.occurrence_date >= start_date,
                TaskOccurrence.occurrence_date <= end_date,
            ).order_by(TaskOccurrence.occurrence_date.asc()).all()

            schedule = task.schedule
            if schedule is None or not schedule.is_active:
                return persisted

            # A moved occurrence keeps its original source key. Read all keys
            # so its original scheduled date is not reconstructed in this range.
            source_keys = {
                source_key
                for (source_key,) in self.db.query(TaskOccurrence.source_key).filter(
                    TaskOccurrence.task_id == task.id,
                ).all()
            }
            existing_dates = {occurrence.occurrence_date for occurrence in persisted}
            for occurrence_date in self.iter_occurrence_dates_between(
                schedule, start_date, end_date
            ):
                source_key = f"task:{task.id}:{occurrence_date.isoformat()}"
                if occurrence_date in existing_dates or source_key in source_keys:
                    continue
                persisted.append(TaskOccurrence(
                    task_id=task.id,
                    occurrence_date=occurrence_date,
                    status=TaskStatus.PENDING.value,
                    source_key=source_key,
                ))
                existing_dates.add(occurrence_date)
                source_keys.add(source_key)

        return sorted(persisted, key=lambda occurrence: occurrence.occurrence_date)

    @classmethod
    def iter_occurrence_dates_between(
        cls,
        schedule: TaskSchedule,
        start_date: date,
        end_date: date,
    ):
        current = max(start_date, schedule.starts_on)
        if schedule.ends_on is not None:
            end_date = min(end_date, schedule.ends_on)
        while current <= end_date:
            if cls._matches(schedule, current):
                yield current
            current += timedelta(days=1)

    def materialize_until(self, user_id: UUID, target_date: date) -> list[TaskOccurrence]:
        tasks = self.db.query(Task).join(TaskSchedule).filter(
            Task.user_id == user_id,
            TaskSchedule.is_active.is_(True),
        ).all()
        for task in tasks:
            self.materialize_task_until(task, target_date, commit=False)
        self.db.commit()
        return self.db.query(TaskOccurrence).join(Task).filter(
            Task.user_id == user_id,
            TaskOccurrence.occurrence_date <= target_date,
        ).order_by(TaskOccurrence.occurrence_date.asc()).all()

    def get_or_create_occurrence(
        self,
        task: Task,
        occurrence_date: date,
        *,
        commit: bool = False,
    ) -> TaskOccurrence:
        occurrence = self.db.query(TaskOccurrence).filter(
            TaskOccurrence.task_id == task.id,
            TaskOccurrence.occurrence_date == occurrence_date,
        ).one_or_none()
        if occurrence is not None:
            return occurrence

        if task.schedule is not None:
            if not self._matches(task.schedule, occurrence_date):
                raise self._error(422, "TASK_OCCURRENCE_NOT_SCHEDULED", "该日期不是任务的重复日期。")
            self.materialize_task_until(task, occurrence_date, commit=False)
            occurrence = self.db.query(TaskOccurrence).filter(
                TaskOccurrence.task_id == task.id,
                TaskOccurrence.occurrence_date == occurrence_date,
            ).one_or_none()
        else:
            occurrence = TaskOccurrence(
                task_id=task.id,
                occurrence_date=occurrence_date,
                source_key=f"task:{task.id}:{occurrence_date.isoformat()}",
            )
            self.db.add(occurrence)
            self.db.flush()

        if occurrence is None:
            raise self._error(409, "TASK_OCCURRENCE_NOT_FOUND", "任务 occurrence 不存在，请刷新后重试。")
        if commit:
            self.db.commit()
        return occurrence

    @classmethod
    def deadline_for_occurrence(cls, task: Task, occurrence_date: date) -> Optional[datetime]:
        if task.deadline is None:
            return None
        deadline_timezone = task.deadline.tzinfo
        if task.schedule is not None:
            deadline_timezone = ZoneInfo(task.schedule.timezone or cls.TIMEZONE_NAME)
        return datetime.combine(
            occurrence_date,
            time(
                hour=task.deadline.hour,
                minute=task.deadline.minute,
                second=task.deadline.second,
                microsecond=task.deadline.microsecond,
                tzinfo=deadline_timezone,
            ),
        )

    @classmethod
    def state_for(cls, task: Task, occurrence: TaskOccurrence) -> TaskScheduleStateResponse:
        task_deadline = cls.deadline_for_occurrence(task, occurrence.occurrence_date)
        schedule = task.schedule
        return TaskScheduleStateResponse(
            task_id=task.id,
            title=task.title,
            occurrence_date=occurrence.occurrence_date,
            status=occurrence.status,
            deadline=task_deadline,
            snoozed_until=occurrence.snoozed_until,
            schedule=schedule,
        )

    def snooze(
        self,
        task: Task,
        until: datetime,
        occurrence_date: Optional[date] = None,
    ) -> TaskScheduleStateResponse:
        if task.status == TaskStatus.COMPLETED.value:
            raise self._error(409, "TASK_ALREADY_COMPLETED", "已完成任务不能延期。")

        until_utc = self._aware_utc(until)
        if until_utc <= self._now_utc():
            raise self._error(422, "TASK_SNOOZE_IN_PAST", "延期时间必须晚于当前时间。")

        target_date = occurrence_date or self._local_date(task.deadline)
        if target_date is None:
            raise self._error(422, "TASK_NOT_SCHEDULED", "没有截止日期的任务不能使用延期。")
        occurrence = self.get_or_create_occurrence(task, target_date)
        if occurrence.status == TaskStatus.COMPLETED.value:
            raise self._error(409, "TASK_ALREADY_COMPLETED", "已完成任务不能延期。")
        occurrence.snoozed_until = until_utc
        self.db.commit()
        self.db.refresh(occurrence)
        return self.state_for(task, occurrence)

    def reschedule(
        self,
        task: Task,
        *,
        deadline: Optional[datetime] = None,
        occurrence_date: Optional[date] = None,
        new_occurrence_date: Optional[date] = None,
    ) -> TaskScheduleStateResponse:
        if task.status == TaskStatus.COMPLETED.value:
            raise self._error(409, "TASK_ALREADY_COMPLETED", "已完成任务不能重新安排。")

        today = self._today()
        if deadline is not None:
            if self._aware_utc(deadline) <= self._now_utc():
                raise self._error(422, "TASK_DATE_IN_PAST", "截止时间必须晚于当前时间。")
            task.deadline = deadline
            target_date = self._local_date(deadline) or today
            occurrence = self.db.query(TaskOccurrence).filter(
                TaskOccurrence.task_id == task.id,
            ).order_by(TaskOccurrence.occurrence_date.desc()).first()
            if occurrence is None:
                occurrence = self.get_or_create_occurrence(task, target_date)
            elif task.schedule is None:
                occurrence.occurrence_date = target_date
                occurrence.source_key = f"task:{task.id}:{target_date.isoformat()}"
        else:
            if new_occurrence_date is None or occurrence_date is None:
                raise self._error(422, "TASK_RESCHEDULE_TARGET_REQUIRED", "请提供要移动的 occurrence 日期。")
            if new_occurrence_date < today:
                raise self._error(422, "TASK_DATE_IN_PAST", "新的任务日期不能早于今天。")
            occurrence = self.get_or_create_occurrence(task, occurrence_date)
            if occurrence.status == TaskStatus.COMPLETED.value:
                raise self._error(409, "TASK_ALREADY_COMPLETED", "已完成任务不能重新安排。")
            existing = self.db.query(TaskOccurrence).filter(
                TaskOccurrence.task_id == task.id,
                TaskOccurrence.occurrence_date == new_occurrence_date,
                TaskOccurrence.id != occurrence.id,
            ).one_or_none()
            if existing is not None:
                raise self._error(409, "TASK_OCCURRENCE_CONFLICT", "目标日期已经存在同一重复任务。")
            occurrence.occurrence_date = new_occurrence_date
            occurrence.snoozed_until = None

        self.db.commit()
        self.db.refresh(task)
        self.db.refresh(occurrence)
        return self.state_for(task, occurrence)
