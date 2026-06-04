from datetime import date, timedelta
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, func, extract
from sqlalchemy.orm import Session

from app.models.todo import Habit, Task, Goal, Frequency, TaskStatus
from app.models.checkin import DailyCheckin


class CalendarService:
    def __init__(self, db: Session):
        self.db = db

    def get_events(self, user_id: UUID, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Return a flat list of calendar events in the date range."""
        events: List[Dict[str, Any]] = []

        # 1. Tasks with deadline in range
        tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.deadline.isnot(None),
            func.date(Task.deadline) >= start_date,
            func.date(Task.deadline) <= end_date,
        ).all()
        for t in tasks:
            events.append({
                "date": t.deadline.strftime("%Y-%m-%d"),
                "type": "task",
                "title": t.title,
                "status": t.status,
                "id": str(t.id),
                "project_id": str(t.project_id) if t.project_id else None,
                "project_name": t.project.name if t.project else None,
                "project_color": t.project.color if t.project else None,
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
            })

        return events

    def get_day_detail(self, user_id: UUID, target_date: date) -> Dict[str, Any]:
        """Return detailed info for a specific date."""
        # Tasks due on target_date
        tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.deadline.isnot(None),
            func.date(Task.deadline) == target_date,
        ).all()
        task_list = [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "difficulty": t.difficulty,
                "description": t.description,
                "project_id": str(t.project_id) if t.project_id else None,
                "project_name": t.project.name if t.project else None,
                "project_color": t.project.color if t.project else None,
            }
            for t in tasks
        ]

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
