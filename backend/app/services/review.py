from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models.coin_transaction import CoinTransaction, CoinType
from app.models.cultivation import CultivationLog
from app.models.habit_completion import HabitCompletion
from app.models.note import Notebook
from app.models.note_node import NoteNode
from app.models.project import Project, ProjectStatus
from app.models.task_schedule import TaskSchedule
from app.models.todo import Habit, Task, TaskStatus
from app.services.task_schedule import TaskScheduleService


class ReviewService:
    APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
    TIMEZONE_NAME = "Asia/Shanghai"

    def __init__(self, db):
        self.db = db
        self.schedule_service = TaskScheduleService(db)

    @classmethod
    def _local_date(cls, value: Optional[datetime]) -> Optional[date]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(cls.APP_TIMEZONE).date()

    @classmethod
    def _utc_naive(cls, value: datetime) -> datetime:
        return cls._aware_utc(value).replace(tzinfo=None)

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _week_start_default(cls) -> date:
        today = datetime.now(timezone.utc).astimezone(cls.APP_TIMEZONE).date()
        return today - timedelta(days=today.weekday())

    @classmethod
    def _week_bounds(cls, week_start: Optional[date]) -> tuple[date, date, datetime, datetime]:
        start = week_start or cls._week_start_default()
        if start.weekday() != 0:
            raise ValueError("WEEK_START_MUST_BE_MONDAY")
        end = start + timedelta(days=6)
        start_local = datetime.combine(start, time.min, tzinfo=cls.APP_TIMEZONE)
        end_local = datetime.combine(end + timedelta(days=1), time.min, tzinfo=cls.APP_TIMEZONE)
        return start, end, cls._utc_naive(start_local), cls._utc_naive(end_local)

    @classmethod
    def _occurrence_deadline(cls, task: Task, occurrence_date: date) -> Optional[datetime]:
        return TaskScheduleService.deadline_for_occurrence(task, occurrence_date)

    @staticmethod
    def _item(
        *,
        item_id: UUID,
        title: str,
        url: str,
        kind: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        deadline: Optional[datetime] = None,
        occurrence_date: Optional[date] = None,
    ) -> dict:
        return {
            "id": item_id,
            "title": title,
            "url": url,
            "kind": kind,
            "status": status,
            "priority": priority,
            "deadline": deadline,
            "occurrence_date": occurrence_date,
        }

    @classmethod
    def _habit_due_dates(cls, habit: Habit, week_start: date, week_end: date) -> list[date]:
        created_on = cls._local_date(habit.created_at)
        due_dates = []
        current = week_start
        while current <= week_end:
            if created_on is None or current < created_on:
                current += timedelta(days=1)
                continue
            if habit.frequency == "daily":
                due_dates.append(current)
            elif habit.frequency == "weekly" and current.weekday() == created_on.weekday():
                due_dates.append(current)
            elif habit.frequency == "monthly" and current.day == created_on.day:
                due_dates.append(current)
            current += timedelta(days=1)
        return due_dates

    def _habit_review(self, user_id: UUID, week_start: date, week_end: date, start_utc: datetime, end_utc: datetime):
        habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
            Habit.is_active.is_(True),
            Habit.created_at < end_utc,
        ).order_by(Habit.title.asc(), Habit.id.asc()).all()

        changes = []
        due_count = 0
        completed_count = 0
        for habit in habits:
            due_dates = self._habit_due_dates(habit, week_start, week_end)
            history_dates = {
                completed_date
                for (completed_date,) in self.db.query(HabitCompletion.completed_date).filter(
                    HabitCompletion.habit_id == habit.id,
                ).all()
            }
            if history_dates:
                completed = len(history_dates.intersection(due_dates))
            else:
                completed_on = self._local_date(habit.last_completed_at)
                completed = int(completed_on in due_dates) if completed_on else 0
            due_count += len(due_dates)
            completed_count += completed
            if not due_dates and not completed:
                continue
            streak_after = max(0, int(habit.streak or 0))
            streak_before = max(0, streak_after - completed)
            changes.append({
                "id": habit.id,
                "title": habit.title,
                "due_count": len(due_dates),
                "completed_count": completed,
                "streak_before": streak_before,
                "streak_after": streak_after,
                "delta": completed,
            })
        return changes, due_count, completed_count

    def _task_review(self, user_id: UUID, week_start: date, week_end: date, start_utc: datetime, end_utc: datetime):
        tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.created_at < end_utc,
        ).order_by(Task.created_at.asc(), Task.id.asc()).all()
        scheduled_tasks = self.db.query(Task).join(
            TaskSchedule, TaskSchedule.task_id == Task.id
        ).filter(
            Task.user_id == user_id,
            TaskSchedule.is_active.is_(True),
            Task.created_at < end_utc,
        ).order_by(Task.id.asc()).all()
        occurrences = [
            (occurrence, task)
            for task in scheduled_tasks
            if task.status not in {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}
            for occurrence in self.schedule_service.get_occurrences_for_range(
                task, week_start, week_end
            )
        ]

        occurrence_task_ids = {task.id for _occurrence, task in occurrences}
        completed_count = 0
        open_count = 0
        overdue_count = 0
        high_priority = []
        now_utc = datetime.now(timezone.utc)

        for task in tasks:
            if task.schedule is not None or task.id in occurrence_task_ids:
                continue
            if task.status == TaskStatus.COMPLETED.value:
                if task.completed_at is not None:
                    completed_at = self._utc_naive(task.completed_at)
                    if start_utc <= completed_at < end_utc:
                        completed_count += 1
                continue
            if task.status == TaskStatus.CANCELLED.value:
                continue

            open_count += 1
            deadline = self._aware_utc(task.deadline) if task.deadline else None
            is_overdue = deadline is not None and deadline < now_utc
            overdue_count += int(is_overdue)
            if task.priority in {"high", "urgent"}:
                high_priority.append(self._item(
                    item_id=task.id,
                    title=task.title,
                    url=f"/todos?tab=tasks&task_id={task.id}",
                    kind="task",
                    status=task.status,
                    priority=task.priority,
                    deadline=task.deadline,
                ))

        for occurrence, task in occurrences:
            if occurrence.status == TaskStatus.COMPLETED.value:
                completed_at = (
                    self._utc_naive(occurrence.completed_at)
                    if occurrence.completed_at else None
                )
                if completed_at is not None and start_utc <= completed_at < end_utc:
                    completed_count += 1
                    continue
            if occurrence.status == TaskStatus.CANCELLED.value:
                continue
            open_count += 1
            deadline = self._occurrence_deadline(task, occurrence.occurrence_date)
            is_overdue = deadline is not None and deadline < now_utc
            overdue_count += int(is_overdue)
            if task.priority in {"high", "urgent"}:
                high_priority.append(self._item(
                    item_id=task.id,
                    title=task.title,
                    url=(
                        f"/todos?tab=tasks&task_id={task.id}"
                        f"&occurrence_date={occurrence.occurrence_date.isoformat()}"
                    ),
                    kind="task",
                    status=occurrence.status,
                    priority=task.priority,
                    deadline=deadline,
                    occurrence_date=occurrence.occurrence_date,
                ))

        priority_order = {"urgent": 0, "high": 1}
        high_priority.sort(key=lambda item: (
            priority_order.get(item["priority"], 2),
            self._utc_naive(item["deadline"]) if item["deadline"] else datetime.max,
            item["title"],
            str(item["id"]),
        ))
        return tasks, completed_count, open_count, overdue_count, high_priority

    def _projects_without_next_action(self, user_id: UUID, tasks: list[Task]):
        projects = self.db.query(Project).filter(
            Project.user_id == user_id,
            Project.status.notin_([ProjectStatus.COMPLETED.value, ProjectStatus.ARCHIVED.value]),
        ).order_by(Project.name.asc(), Project.id.asc()).all()
        open_by_project = {
            task.project_id
            for task in tasks
            if task.project_id is not None
            and task.status not in {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}
        }
        return [
            self._item(
                item_id=project.id,
                title=project.name,
                url=f"/projects/{project.id}",
                kind="project",
                status=project.status,
            )
            for project in projects
            if project.id not in open_by_project
        ]

    def _recent_notes(self, user_id: UUID, start_utc: datetime, end_utc: datetime):
        notes = self.db.query(NoteNode).join(
            Notebook, Notebook.id == NoteNode.notebook_id
        ).filter(
            Notebook.user_id == user_id,
            NoteNode.type == "note",
            NoteNode.updated_at >= start_utc,
            NoteNode.updated_at < end_utc,
        ).order_by(NoteNode.updated_at.desc(), NoteNode.id.asc()).limit(10).all()
        return [
            self._item(
                item_id=note.id,
                title=note.name,
                url=f"/notes/{note.notebook_id}/view/{note.id}",
                kind="note",
            )
            for note in notes
        ]

    def _rewards(self, user_id: UUID, start_utc: datetime, end_utc: datetime) -> dict:
        transactions = self.db.query(CoinTransaction).filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.created_at >= start_utc,
            CoinTransaction.created_at < end_utc,
        ).all()
        coins_earned = sum(
            int(transaction.amount or 0)
            for transaction in transactions
            if transaction.type == CoinType.EARN.value
        )
        coins_spent = sum(
            abs(int(transaction.amount or 0))
            for transaction in transactions
            if transaction.type == CoinType.SPEND.value
        )
        logs = self.db.query(CultivationLog).filter(
            CultivationLog.user_id == user_id,
            CultivationLog.created_at >= start_utc,
            CultivationLog.created_at < end_utc,
        ).all()
        cultivation = sum(int(log.cultivation_delta or 0) for log in logs)
        spirit_stones = sum(int(log.spirit_stones_delta or 0) for log in logs)
        return {
            "coins_earned": coins_earned,
            "coins_spent": coins_spent,
            "coins_delta": coins_earned - coins_spent,
            "experience": cultivation,
            "cultivation": cultivation,
            "spirit_stones": spirit_stones,
        }

    @staticmethod
    def _suggestions(high_priority: list[dict], projects: list[dict], notes: list[dict]):
        return [
            {
                "title": "先处理一个高优先级任务",
                "reason": "把最重要的未完成事项变成下一步行动。",
                "url": high_priority[0]["url"] if high_priority else "/todos?tab=tasks",
            },
            {
                "title": "为项目补充下一动作",
                "reason": "让项目拥有一个可以马上执行的具体任务。",
                "url": projects[0]["url"] if projects else "/projects",
            },
            {
                "title": "把复盘写进笔记",
                "reason": "记录决定与上下文，方便下周继续推进。",
                "url": notes[0]["url"] if notes else "/notes",
            },
        ]

    def get_weekly_review(self, user_id: UUID, week_start: Optional[date] = None) -> dict:
        start, end, start_utc, end_utc = self._week_bounds(week_start)
        tasks, task_completed, task_open, overdue, high_priority = self._task_review(
            user_id, start, end, start_utc, end_utc
        )
        habit_changes, habit_due, habit_completed = self._habit_review(
            user_id, start, end, start_utc, end_utc
        )
        projects = self._projects_without_next_action(user_id, tasks)
        notes = self._recent_notes(user_id, start_utc, end_utc)
        rewards = self._rewards(user_id, start_utc, end_utc)

        return {
            "week_start": start,
            "week_end": end,
            "timezone": self.TIMEZONE_NAME,
            "summary": {
                "completed_count": task_completed + habit_completed,
                "open_count": task_open,
                "overdue_count": overdue,
                "habit_due_count": habit_due,
                "habit_completed_count": habit_completed,
            },
            "habit_streak_changes": habit_changes,
            "rewards": rewards,
            "unfinished_high_priority": high_priority,
            "projects_without_next_action": projects,
            "notes": notes,
            "suggestions": self._suggestions(high_priority, projects, notes),
        }
