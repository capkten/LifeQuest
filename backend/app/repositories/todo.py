from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.todo import Habit, Task, Goal, Subtask
from app.repositories.base import BaseRepository


class HabitRepository(BaseRepository[Habit]):
    def __init__(self, db: Session):
        super().__init__(Habit, db)

    def get_by_user(self, user_id: UUID) -> List[Habit]:
        return self.db.query(Habit).filter(Habit.user_id == user_id).all()

    def get_active_by_user(self, user_id: UUID) -> List[Habit]:
        return self.db.query(Habit).filter(
            Habit.user_id == user_id, Habit.is_active == True
        ).all()


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

    def get_by_user(self, user_id: UUID) -> List[Task]:
        return self.db.query(Task).filter(Task.user_id == user_id).all()

    def get_by_status(self, user_id: UUID, status: str) -> List[Task]:
        return self.db.query(Task).filter(
            Task.user_id == user_id, Task.status == status
        ).all()


class GoalRepository(BaseRepository[Goal]):
    def __init__(self, db: Session):
        super().__init__(Goal, db)

    def get_by_user(self, user_id: UUID) -> List[Goal]:
        return self.db.query(Goal).filter(Goal.user_id == user_id).all()

    def get_by_status(self, user_id: UUID, status: str) -> List[Goal]:
        return self.db.query(Goal).filter(
            Goal.user_id == user_id, Goal.status == status
        ).all()


class SubtaskRepository(BaseRepository[Subtask]):
    def __init__(self, db: Session):
        super().__init__(Subtask, db)

    def get_by_task(self, task_id: UUID) -> List[Subtask]:
        return self.db.query(Subtask).filter(Subtask.task_id == task_id).all()
