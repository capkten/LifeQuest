from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import (
    Project,
    ProjectPhase,
    ProjectMilestone,
    ProjectStatus,
    MilestoneStatus,
)
from app.models.todo import Task, TaskStatus
from app.repositories.project import ProjectRepository, PhaseRepository, MilestoneRepository
from app.repositories.todo import TaskRepository
from app.repositories.user import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    PhaseCreate,
    PhaseUpdate,
    MilestoneCreate,
    MilestoneUpdate,
)
from app.schemas.todo import TaskCreate
from app.services.achievement import AchievementService
from app.services.title import TitleService
from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.coin_transaction import CoinTransactionRepository


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.phase_repo = PhaseRepository(db)
        self.milestone_repo = MilestoneRepository(db)
        self.task_repo = TaskRepository(db)
        self.user_repo = UserRepository(db)
        self.coin_repo = CoinTransactionRepository(db)
        self.achievement_service = AchievementService(db)
        self.title_service = TitleService(db)

    # --- Ownership check ---
    def get_project_for_user(self, project_id: UUID, user_id: UUID) -> Project:
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return project

    def get_phase_for_project(self, phase_id: UUID, project_id: UUID) -> ProjectPhase:
        phase = self.phase_repo.get_by_id(phase_id)
        if phase is None:
            raise HTTPException(status_code=404, detail="Phase not found")
        if phase.project_id != project_id:
            raise HTTPException(status_code=403, detail="Phase does not belong to this project")
        return phase

    def get_milestone_for_project(self, milestone_id: UUID, project_id: UUID) -> ProjectMilestone:
        milestone = self.milestone_repo.get_by_id(milestone_id)
        if milestone is None:
            raise HTTPException(status_code=404, detail="Milestone not found")
        if milestone.project_id != project_id:
            raise HTTPException(status_code=403, detail="Milestone does not belong to this project")
        return milestone

    # --- Project CRUD ---
    def create_project(self, user_id: UUID, data: ProjectCreate) -> dict:
        obj_data = data.model_dump()
        obj_data["user_id"] = user_id
        project = self.project_repo.create(obj_data)
        return {
            "project": project,
            "total_tasks": 0,
            "completed_tasks": 0,
            "progress": 0.0,
        }

    def get_projects(self, user_id: UUID, status: Optional[str] = None) -> List[dict]:
        projects = self.project_repo.get_by_user(user_id, status)
        result = []
        for p in projects:
            stats = self._compute_project_stats(p)
            result.append(stats)
        return result

    def get_project_detail(self, project_id: UUID, user_id: UUID) -> dict:
        project = self.get_project_for_user(project_id, user_id)
        stats = self._compute_project_stats(project)
        phases = self.phase_repo.get_by_project_ordered(project_id)
        milestones = self.milestone_repo.get_by_project_ordered(project_id)
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        stats["phases"] = phases
        stats["milestones"] = milestones
        stats["tasks"] = tasks
        return stats

    def update_project(self, project: Project, data: ProjectUpdate) -> Project:
        update_data = data.model_dump(exclude_unset=True)
        return self.project_repo.update(project, update_data)

    def delete_project(self, project: Project) -> None:
        # Nullify task references before deleting
        self.db.query(Task).filter(Task.project_id == project.id).update(
            {Task.project_id: None, Task.phase_id: None, Task.milestone_id: None}
        )
        self.db.flush()
        self.project_repo.delete(project.id)

    def complete_project(self, project: Project) -> Project:
        if project.status == ProjectStatus.COMPLETED:
            return project
        project.status = ProjectStatus.COMPLETED
        project.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(project)

        # Check project achievements
        try:
            completed_count = self.db.query(Project).filter(
                Project.user_id == project.user_id,
                Project.status == ProjectStatus.COMPLETED,
            ).count()
            self.achievement_service.check_and_unlock(project.user_id, "project_completed", completed_count)
        except Exception:
            pass

        return project

    # --- Phase CRUD ---
    def create_phase(self, project_id: UUID, data: PhaseCreate) -> ProjectPhase:
        obj_data = data.model_dump()
        obj_data["project_id"] = project_id
        return self.phase_repo.create(obj_data)

    def update_phase(self, phase: ProjectPhase, data: PhaseUpdate) -> ProjectPhase:
        update_data = data.model_dump(exclude_unset=True)
        return self.phase_repo.update(phase, update_data)

    def delete_phase(self, phase: ProjectPhase) -> None:
        # Nullify tasks referencing this phase
        self.db.query(Task).filter(Task.phase_id == phase.id).update({Task.phase_id: None})
        self.db.flush()
        self.phase_repo.delete(phase.id)

    # --- Milestone CRUD ---
    def create_milestone(self, project_id: UUID, data: MilestoneCreate) -> ProjectMilestone:
        obj_data = data.model_dump()
        obj_data["project_id"] = project_id
        return self.milestone_repo.create(obj_data)

    def update_milestone(self, milestone: ProjectMilestone, data: MilestoneUpdate) -> ProjectMilestone:
        update_data = data.model_dump(exclude_unset=True)
        return self.milestone_repo.update(milestone, update_data)

    def delete_milestone(self, milestone: ProjectMilestone) -> None:
        # Nullify tasks referencing this milestone
        self.db.query(Task).filter(Task.milestone_id == milestone.id).update(
            {Task.milestone_id: None}
        )
        self.db.flush()
        self.milestone_repo.delete(milestone.id)

    def reach_milestone(self, milestone: ProjectMilestone) -> ProjectMilestone:
        milestone.status = MilestoneStatus.REACHED
        milestone.reached_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(milestone)
        return milestone

    # --- Tasks within project ---
    def create_project_task(self, user_id: UUID, project_id: UUID, data: TaskCreate) -> Task:
        obj_data = data.model_dump()
        obj_data["user_id"] = user_id
        obj_data["project_id"] = project_id
        return self.task_repo.create(obj_data)

    def get_project_tasks(
        self,
        project_id: UUID,
        phase_id: Optional[UUID] = None,
        milestone_id: Optional[UUID] = None,
    ) -> List[Task]:
        query = self.db.query(Task).filter(Task.project_id == project_id)
        if phase_id:
            query = query.filter(Task.phase_id == phase_id)
        if milestone_id:
            query = query.filter(Task.milestone_id == milestone_id)
        return query.order_by(Task.sort_order).all()

    def move_task(
        self,
        task: Task,
        project_id: Optional[UUID] = None,
        phase_id: Optional[UUID] = None,
        milestone_id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
    ) -> Task:
        if project_id is not None:
            task.project_id = project_id
        if phase_id is not None:
            task.phase_id = phase_id
        if milestone_id is not None:
            task.milestone_id = milestone_id
        if status is not None:
            task.status = status
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now(timezone.utc)
            elif task.completed_at is not None:
                task.completed_at = None
        self.db.commit()
        self.db.refresh(task)
        return task

    # --- Stats helper ---
    def _compute_project_stats(self, project: Project) -> dict:
        total = self.db.query(Task).filter(Task.project_id == project.id).count()
        completed = self.db.query(Task).filter(
            Task.project_id == project.id, Task.status == TaskStatus.COMPLETED
        ).count()
        progress = (completed / total * 100) if total > 0 else 0.0
        return {
            "project": project,
            "total_tasks": total,
            "completed_tasks": completed,
            "progress": round(progress, 1),
        }
