from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, exists, func
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

    def update(self, db_obj: Project, obj_in: dict) -> Project:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

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

    def count_tasks(self, phase_id: UUID) -> int:
        return self.db.query(Task).filter(Task.phase_id == phase_id).count()

    def get_for_update(self, phase_id: UUID) -> Optional[ProjectPhase]:
        return (
            self.db.query(ProjectPhase)
            .filter(ProjectPhase.id == phase_id)
            .with_for_update()
            .first()
        )

    def delete_if_empty(self, phase_id: UUID) -> bool:
        result = self.db.execute(
            delete(ProjectPhase).where(
                ProjectPhase.id == phase_id,
                ~exists().where(Task.phase_id == phase_id),
            )
        )
        return result.rowcount == 1


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
