from datetime import date, timedelta
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, func, extract
from sqlalchemy.orm import Session

from app.models.task_schedule import TaskOccurrence, TaskSchedule
from app.models.todo import Habit, Task, Goal, Frequency, TaskStatus
from app.models.checkin import DailyCheckin
from app.services.task_schedule import TaskScheduleService


class CalendarService:
    def __init__(self, db: Session):
        self.db = db
        self.schedule_service = TaskScheduleService(db)

    def get_events(self, user_id: UUID, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Return a flat list of calendar events in the date range."""
        events: List[Dict[str, Any]] = []

        # 1. One-off tasks with a deadline in range
        tasks = self.db.query(Task).outerjoin(TaskSchedule).filter(
            Task.user_id == user_id,
            Task.deadline.isnot(None),
            TaskSchedule.id.is_(None),
            func.date(Task.deadline) >= start_date,
            func.date(Task.deadline) <= end_date,
        ).all()
        for t in tasks:
            event_date = t.deadline.strftime("%Y-%m-%d")
            events.append({
                "date": event_date,
                "type": "task",
                "title": t.title,
                "status": t.status,
                "id": str(t.id),
                "target_id": str(t.id),
                "action": "open",
                "occurrence_date": None,
                "occurrence_status": t.status,
                "event_key": f"task:{t.id}:{event_date}",
                "project_id": str(t.project_id) if t.project_id else None,
                "project_name": t.project.name if t.project else None,
                "project_color": t.project.color if t.project else None,
            })

        # Recurring tasks are materialized before reading so the calendar has
        # stable per-date identities and can distinguish two occurrences of
        # the same task template.
        self.schedule_service.materialize_until(user_id, end_date)
        occurrences = self.db.query(TaskOccurrence).join(Task).join(TaskSchedule).filter(
            Task.user_id == user_id,
            TaskOccurrence.occurrence_date >= start_date,
            TaskOccurrence.occurrence_date <= end_date,
        ).all()
        for occurrence in occurrences:
            task = occurrence.task
            event_date = occurrence.occurrence_date.isoformat()
            events.append({
                "date": event_date,
                "type": "task",
                "title": task.title,
                "status": occurrence.status,
                "id": str(task.id),
                "target_id": str(task.id),
                "action": "open",
                "occurrence_date": event_date,
                "occurrence_status": occurrence.status,
                "event_key": f"task:{task.id}:{event_date}",
                "project_id": str(task.project_id) if task.project_id else None,
                "project_name": task.project.name if task.project else None,
                "project_color": task.project.color if task.project else None,
            })

        # 2. Goals with deadline in range
        goals = self.db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.deadline.isnot(None),
            func.date(Goal.deadline) >= start_date,
            func.date(Goal.deadline) <= end_date,
        ).all()
        for g in goals:
            events.append({
                "date": g.deadline.strftime("%Y-%m-%d"),
                "type": "goal",
                "title": g.title,
                "status": g.status,
                "id": str(g.id),
                "target_id": str(g.id),
                "action": "open",
                "event_key": f"goal:{g.id}:{g.deadline.strftime('%Y-%m-%d')}",
            })

        # 3. Active habits: for each day in range, check if habit is due
        habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
        ).all()

        current = start_date
        while current <= end_date:
            for h in habits:
                if self._is_habit_due_on_date(h, current):
                    events.append({
                        "date": current.strftime("%Y-%m-%d"),
                        "type": "habit",
                        "title": h.title,
                        "status": "due",
                        "id": str(h.id),
                        "target_id": str(h.id),
                        "action": "open",
                        "event_key": f"habit:{h.id}:{current.isoformat()}",
                    })
            current += timedelta(days=1)

        # 4. Check-ins in range
        checkins = self.db.query(DailyCheckin).filter(
            DailyCheckin.user_id == user_id,
            DailyCheckin.checkin_date >= start_date,
            DailyCheckin.checkin_date <= end_date,
        ).all()
        for c in checkins:
            events.append({
                "date": c.checkin_date.strftime("%Y-%m-%d"),
                "type": "checkin",
                "title": "每日签到",
                "status": "done",
                "id": str(c.id),
                "target_id": str(c.id),
                "action": "open",
                "event_key": f"checkin:{c.id}:{c.checkin_date.isoformat()}",
            })

        return events

    def get_day_detail(self, user_id: UUID, target_date: date) -> Dict[str, Any]:
        """Return detailed info for a specific date."""
        # One-off tasks due on target_date
        tasks = self.db.query(Task).outerjoin(TaskSchedule).filter(
            Task.user_id == user_id,
            Task.deadline.isnot(None),
            TaskSchedule.id.is_(None),
            func.date(Task.deadline) == target_date,
        ).all()
        task_list = [
            {
                "id": str(t.id),
                "target_id": str(t.id),
                "title": t.title,
                "status": t.status,
                "occurrence_status": t.status,
                "occurrence_date": None,
                "action": "open",
                "deadline": t.deadline,
                "difficulty": t.difficulty,
                "description": t.description,
                "project_id": str(t.project_id) if t.project_id else None,
                "project_name": t.project.name if t.project else None,
                "project_color": t.project.color if t.project else None,
            }
            for t in tasks
        ]

        self.schedule_service.materialize_until(user_id, target_date)
        occurrences = self.db.query(TaskOccurrence).join(Task).join(TaskSchedule).filter(
            Task.user_id == user_id,
            TaskOccurrence.occurrence_date == target_date,
        ).all()
        task_list.extend({
            "id": str(occurrence.task_id),
            "target_id": str(occurrence.task_id),
            "title": occurrence.task.title,
            "status": occurrence.status,
            "occurrence_status": occurrence.status,
            "occurrence_date": occurrence.occurrence_date.isoformat(),
            "action": "open",
            "deadline": self.schedule_service.deadline_for_occurrence(
                occurrence.task, occurrence.occurrence_date
            ),
            "difficulty": occurrence.task.difficulty,
            "description": occurrence.task.description,
            "project_id": str(occurrence.task.project_id) if occurrence.task.project_id else None,
            "project_name": occurrence.task.project.name if occurrence.task.project else None,
            "project_color": occurrence.task.project.color if occurrence.task.project else None,
        } for occurrence in occurrences)

        # Goals due on target_date
        goals = self.db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.deadline.isnot(None),
            func.date(Goal.deadline) == target_date,
        ).all()
        goal_list = [
            {
                "id": str(g.id),
                "title": g.title,
                "status": g.status,
                "difficulty": g.difficulty,
                "progress": g.progress,
                "description": g.description,
            }
            for g in goals
        ]

        # Active habits due on target_date
        habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
        ).all()
        habit_list = [
            {
                "id": str(h.id),
                "title": h.title,
                "difficulty": h.difficulty,
                "frequency": h.frequency,
                "streak": h.streak,
            }
            for h in habits
            if self._is_habit_due_on_date(h, target_date)
        ]

        # Check-in status
        checkin = self.db.query(DailyCheckin).filter(
            DailyCheckin.user_id == user_id,
            DailyCheckin.checkin_date == target_date,
        ).first()

        return {
            "tasks": task_list,
            "goals": goal_list,
            "habits": habit_list,
            "checked_in": checkin is not None,
        }

    @staticmethod
    def _is_habit_due_on_date(habit: Habit, d: date) -> bool:
        """Check if a habit is scheduled on the given date based on frequency."""
        if habit.frequency == Frequency.DAILY:
            return True
        if habit.frequency == Frequency.WEEKLY:
            # Created on a certain weekday; due every same weekday
            if habit.created_at:
                return d.weekday() == habit.created_at.weekday()
            return False
        if habit.frequency == Frequency.MONTHLY:
            # Due on the same day-of-month as creation
            if habit.created_at:
                return d.day == habit.created_at.day
            return False
        return False
