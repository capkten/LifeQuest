from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload

from app.models.task_schedule import TaskOccurrence
from app.models.todo import Goal, Habit, Task, TaskStatus
from app.schemas.action_center import TodayActionCenter
from app.services.calendar import CalendarService
from app.services.task_schedule import TaskScheduleService


class ActionCenterService:
    APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
    TIMEZONE_NAME = "Asia/Shanghai"
    PRIORITY_RANK = {
        "urgent": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }
    OPEN_STATUSES = {"pending", "in_progress"}

    def __init__(self, db: Session):
        self.db = db
        self.schedule_service = TaskScheduleService(db)

    @classmethod
    def _value(cls, value: Any) -> Any:
        return getattr(value, "value", value)

    @classmethod
    def _local_date(cls, value: Optional[datetime]) -> Optional[date]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(cls.APP_TIMEZONE).date()

    @classmethod
    def _today(cls) -> date:
        return datetime.now(timezone.utc).astimezone(cls.APP_TIMEZONE).date()

    @classmethod
    def _deadline_sort_key(cls, item: dict) -> tuple:
        deadline = item.get("deadline")
        if deadline is None and item.get("occurrence_date") is not None:
            deadline = datetime.combine(item["occurrence_date"], datetime.min.time())
        if deadline is None:
            return (float("inf"), item["title"])
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return (deadline.timestamp(), item["title"])

    @classmethod
    def _task_sort_key(cls, item: dict) -> tuple:
        return (
            -cls.PRIORITY_RANK.get(item.get("priority"), 0),
            *cls._deadline_sort_key(item),
        )

    def _task_item(
        self,
        task: Task,
        overdue: bool = False,
        occurrence: Optional[TaskOccurrence] = None,
    ) -> dict:
        status = self._value(occurrence.status if occurrence is not None else task.status)
        project = getattr(task, "project", None)
        occurrence_date = occurrence.occurrence_date if occurrence is not None else None
        deadline = (
            self.schedule_service.deadline_for_occurrence(task, occurrence_date)
            if occurrence_date is not None
            else task.deadline
        )
        return {
            "kind": "task",
            "id": task.id,
            "title": task.title,
            "action": "complete",
            "status": status,
            "deadline": deadline,
            "difficulty": self._value(task.difficulty),
            "priority": self._value(task.priority),
            "completed": status == TaskStatus.COMPLETED.value,
            "overdue": overdue,
            "project_id": task.project_id,
            "project_name": project.name if project else None,
            "project_color": project.color if project else None,
            "occurrence_date": occurrence_date,
            "occurrence_status": occurrence.status if occurrence is not None else None,
            "snoozed_until": occurrence.snoozed_until if occurrence is not None else None,
        }

    @classmethod
    def _habit_item(cls, habit: Habit, completed: bool) -> dict:
        return {
            "kind": "habit",
            "id": habit.id,
            "title": habit.title,
            "action": "complete",
            "status": "completed" if completed else "due",
            "difficulty": cls._value(habit.difficulty),
            "streak": habit.streak,
            "completed": completed,
        }

    @classmethod
    def _goal_item(cls, goal: Goal) -> dict:
        return {
            "kind": "goal",
            "id": goal.id,
            "title": goal.title,
            "action": "open",
            "status": cls._value(goal.status),
            "deadline": goal.deadline,
            "difficulty": cls._value(goal.difficulty),
            "progress": goal.progress,
        }

    @classmethod
    def _is_snoozed(
        cls,
        occurrence: Optional[TaskOccurrence],
        target_date: date,
        now: Optional[datetime] = None,
    ) -> bool:
        if occurrence is None or occurrence.snoozed_until is None:
            return False
        until = occurrence.snoozed_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        local_until = until.astimezone(cls.APP_TIMEZONE)
        if local_until.date() > target_date:
            return True
        if local_until.date() < target_date:
            return False
        current = now or datetime.now(timezone.utc)
        return target_date == cls._today() and until > current

    def get_today(self, user_id: UUID, target_date: Optional[date] = None) -> TodayActionCenter:
        current_date = target_date or self._today()

        overdue: list[dict] = []
        today: list[dict] = []
        completed_count = 0
        occurrence_rows = self.schedule_service.materialize_until(user_id, current_date)
        occurrences_by_task: dict[UUID, list[TaskOccurrence]] = {}
        for occurrence in occurrence_rows:
            occurrences_by_task.setdefault(occurrence.task_id, []).append(occurrence)

        tasks = self.db.query(Task).options(
            joinedload(Task.schedule), joinedload(Task.project)
        ).filter(Task.user_id == user_id).all()
        now = datetime.now(timezone.utc)
        for task in tasks:
            status = self._value(task.status)
            if task.schedule is not None:
                if status in {TaskStatus.CANCELLED.value, TaskStatus.COMPLETED.value}:
                    continue
                for occurrence in occurrences_by_task.get(task.id, []):
                    if occurrence.occurrence_date > current_date:
                        continue
                    if occurrence.status == TaskStatus.COMPLETED.value:
                        if self._local_date(occurrence.completed_at) == current_date:
                            completed_count += 1
                        continue
                    if self._is_snoozed(occurrence, current_date, now):
                        continue
                    item = self._task_item(
                        task,
                        overdue=occurrence.occurrence_date < current_date,
                        occurrence=occurrence,
                    )
                    if occurrence.occurrence_date < current_date:
                        overdue.append(item)
                    else:
                        today.append(item)
                continue
            if status == TaskStatus.COMPLETED.value:
                if self._local_date(task.completed_at) == current_date:
                    completed_count += 1
                continue
            if status not in self.OPEN_STATUSES or task.deadline is None:
                continue
            deadline_date = self._local_date(task.deadline)
            if deadline_date is None:
                continue
            occurrence = next(
                (
                    item
                    for item in occurrences_by_task.get(task.id, [])
                    if item.occurrence_date == deadline_date
                ),
                None,
            )
            if occurrence is not None:
                if occurrence.status == TaskStatus.COMPLETED.value:
                    if self._local_date(occurrence.completed_at) == current_date:
                        completed_count += 1
                    continue
                if self._is_snoozed(occurrence, current_date, now):
                    continue
            if deadline_date < current_date:
                overdue.append(self._task_item(task, overdue=True, occurrence=occurrence))
            elif deadline_date == current_date:
                today.append(self._task_item(task, occurrence=occurrence))

        overdue.sort(key=self._deadline_sort_key)
        today.sort(key=self._task_sort_key)

        habits: list[dict] = []
        habit_completed_count = 0
        active_habits = (
            self.db.query(Habit)
            .filter(Habit.user_id == user_id, Habit.is_active.is_(True))
            .order_by(Habit.created_at.asc(), Habit.title.asc())
            .all()
        )
        for habit in active_habits:
            if not CalendarService._is_habit_due_on_date(habit, current_date):
                continue
            completed = self._local_date(habit.last_completed_at) == current_date
            habits.append(self._habit_item(habit, completed))
            if completed:
                habit_completed_count += 1
                completed_count += 1

        calendar: list[dict] = []
        goals = self.db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.deadline.is_not(None),
            Goal.status != TaskStatus.COMPLETED.value,
        ).all()
        for goal in goals:
            if self._local_date(goal.deadline) == current_date:
                calendar.append(self._goal_item(goal))
        calendar.sort(key=self._deadline_sort_key)

        sections = {
            "overdue": overdue,
            "today": today,
            "habits": habits,
            "calendar": calendar,
        }
        actionable = [
            *overdue,
            *today,
            *[item for item in habits if not item["completed"]],
            *calendar,
        ]
        summary = {
            "open_count": len(overdue) + len(today) + sum(
                not item["completed"] for item in habits
            ) + len(calendar),
            "overdue_count": len(overdue),
            "completed_count": completed_count,
            "habit_due_count": len(habits),
            "habit_completed_count": habit_completed_count,
        }
        return TodayActionCenter(
            date=current_date,
            timezone=self.TIMEZONE_NAME,
            summary=summary,
            sections=sections,
            next_action=actionable[0] if actionable else None,
        )
