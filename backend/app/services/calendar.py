from datetime import date, timedelta
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.todo import Habit, Task, Goal, Frequency, TaskStatus
from app.models.habit_pause import HabitPauseInterval
from app.models.habit_leave import HabitLeaveInterval
from app.models.checkin import DailyCheckin
from app.models.habit_completion import HabitCompletion
from app.services.habit_metrics import valid_completion_dates
from app.timezone import day_start_utc, day_bounds_utc, local_date
from app.services.habit_schedule import is_excused_on, is_paused_on


class CalendarService:
    def __init__(self, db: Session):
        self.db = db

    def get_events(self, user_id: UUID, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Return a flat list of calendar events in the date range."""
        events: List[Dict[str, Any]] = []
        start = day_start_utc(start_date)
        end = day_start_utc(end_date + timedelta(days=1))

        # 1. Tasks with deadline in range
        tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.deadline.isnot(None),
            Task.deadline >= start,
            Task.deadline < end,
        ).all()
        for t in tasks:
            events.append({
                "date": local_date(t.deadline).isoformat(),
                "type": "task",
                "title": t.title,
                "status": t.status,
                "id": str(t.id),
                "project_id": str(t.project_id) if t.project and t.project.user_id == user_id else None,
                "project_name": t.project.name if t.project and t.project.user_id == user_id else None,
                "project_color": t.project.color if t.project and t.project.user_id == user_id else None,
            })

        # 2. Goals with deadline in range
        goals = self.db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.deadline.isnot(None),
            Goal.deadline >= start,
            Goal.deadline < end,
        ).all()
        for g in goals:
            events.append({
                "date": local_date(g.deadline).isoformat(),
                "type": "goal",
                "title": g.title,
                "status": g.status,
                "id": str(g.id),
            })

        # 3. Habits: keep historical scheduled dates after deactivation.
        habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
        ).all()
        pause_intervals = self._pause_intervals_by_habit(habits, user_id)
        leave_intervals = self._leave_intervals_by_habit(habits, user_id)
        completion_dates = {habit.id: set() for habit in habits}
        if completion_dates:
            completion_rows = self.db.query(HabitCompletion).filter(
                HabitCompletion.user_id == user_id,
                HabitCompletion.habit_id.in_(completion_dates),
                HabitCompletion.completed_on >= start_date,
                HabitCompletion.completed_on <= end_date,
            ).all()
            for completion in completion_rows:
                completion_dates[completion.habit_id].add(completion.completed_on)
        valid_dates = {
            habit.id: valid_completion_dates(
                habit,
                completion_dates[habit.id],
                pause_intervals.get(habit.id),
                leave_intervals.get(habit.id),
                as_of=end_date,
            )
            for habit in habits
        }

        current = start_date
        while current <= end_date:
            for h in habits:
                if (
                    self._is_habit_due_on_date(h, current)
                    and not is_paused_on(pause_intervals.get(h.id), current)
                    and not is_excused_on(leave_intervals.get(h.id), current)
                ):
                    events.append({
                        "date": current.strftime("%Y-%m-%d"),
                        "type": "habit",
                        "title": h.title,
                        "status": "completed" if current in valid_dates[h.id] else "due",
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
        start, end = day_bounds_utc(target_date)
        # Tasks due on target_date
        tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.deadline.isnot(None),
            Task.deadline >= start,
            Task.deadline < end,
        ).all()
        task_list = [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "difficulty": t.difficulty,
                "description": t.description,
                "project_id": str(t.project_id) if t.project and t.project.user_id == user_id else None,
                "project_name": t.project.name if t.project and t.project.user_id == user_id else None,
                "project_color": t.project.color if t.project and t.project.user_id == user_id else None,
            }
            for t in tasks
        ]

        # Goals due on target_date
        goals = self.db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.deadline.isnot(None),
            Goal.deadline >= start,
            Goal.deadline < end,
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

        # Habits due on target_date, including historical inactive habits.
        habits = self.db.query(Habit).filter(
            Habit.user_id == user_id,
        ).all()
        pause_intervals = self._pause_intervals_by_habit(habits, user_id)
        leave_intervals = self._leave_intervals_by_habit(habits, user_id)
        habit_list = [
            {
                "id": str(h.id),
                "title": h.title,
                "difficulty": h.difficulty,
                "frequency": h.frequency,
                "weekly_target": h.weekly_target,
                "streak": h.streak,
            }
            for h in habits
            if self._is_habit_due_on_date(h, target_date)
            and not is_paused_on(pause_intervals.get(h.id), target_date)
            and not is_excused_on(leave_intervals.get(h.id), target_date)
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
        from app.services.habit_schedule import is_due
        if habit.created_at is not None and d < local_date(habit.created_at):
            return False
        return is_due(habit, d)

    def _pause_intervals_by_habit(self, habits, user_id):
        habit_ids = [habit.id for habit in habits]
        if not habit_ids:
            return {}
        intervals = self.db.query(HabitPauseInterval).filter(
            HabitPauseInterval.user_id == user_id,
            HabitPauseInterval.habit_id.in_(habit_ids),
        ).all()
        grouped = {}
        for interval in intervals:
            grouped.setdefault(interval.habit_id, []).append(interval)
        return grouped

    def _leave_intervals_by_habit(self, habits, user_id):
        habit_ids = [habit.id for habit in habits]
        if not habit_ids:
            return {}
        intervals = self.db.query(HabitLeaveInterval).filter(
            HabitLeaveInterval.user_id == user_id,
            HabitLeaveInterval.habit_id.in_(habit_ids),
        ).all()
        grouped = {}
        for interval in intervals:
            grouped.setdefault(interval.habit_id, []).append(interval)
        return grouped
