from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectPhase, ProjectMilestone
from app.models.todo import Task, TaskStatus
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: Session):
        super().__init__(Project, db)

    def get_by_user(self, user_id: UUID, status: Optional[str] = None) -> List[Project]:
        query = self.db.query(Project).filter(Project.user_id == user_id)
        if status:
            query = query.filter(Project.status == status)
        return query.order_by(Project.created_at.desc()).all()

    def get_with_stats(self, project_id: UUID) -> Optional[dict]:
        project = self.get_by_id(project_id)
        if project is None:
            return None
        total, completed = self._compute_stats(project_id)
        return {
            "project": project,
            "total_tasks": total,
            "completed_tasks": completed,
            "progress": (completed / total * 100) if total > 0 else 0.0,
        }

    def _compute_stats(self, project_id: UUID) -> tuple:
        total = self.db.query(Task).filter(Task.project_id == project_id).count()
        completed = self.db.query(Task).filter(
            Task.project_id == project_id, Task.status == TaskStatus.COMPLETED
        ).count()
        return total, completed


class PhaseRepository(BaseRepository[ProjectPhase]):
    def __init__(self, db: Session):
        super().__init__(ProjectPhase, db)

    def get_by_project(self, project_id: UUID) -> List[ProjectPhase]:
        return self.db.query(ProjectPhase).filter(
            ProjectPhase.project_id == project_id
        ).all()

    def get_by_project_ordered(self, project_id: UUID) -> List[ProjectPhase]:
        return self.db.query(ProjectPhase).filter(
            ProjectPhase.project_id == project_id
        ).order_by(ProjectPhase.sort_order).all()


class MilestoneRepository(BaseRepository[ProjectMilestone]):
    def __init__(self, db: Session):
        super().__init__(ProjectMilestone, db)

    def get_by_project(self, project_id: UUID) -> List[ProjectMilestone]:
        return self.db.query(ProjectMilestone).filter(
            ProjectMilestone.project_id == project_id
        ).all()

    def get_by_project_ordered(self, project_id: UUID) -> List[ProjectMilestone]:
        return self.db.query(ProjectMilestone).filter(
            ProjectMilestone.project_id == project_id
        ).order_by(ProjectMilestone.sort_order).all()
