from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.project import (
    Project,
    ProjectPhase,
    ProjectMilestone,
    ProjectStatus,
    MilestoneStatus,
    normalize_project_status,
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
from app.schemas.todo import TaskCreate, TaskUpdate
from app.services.achievement import AchievementService
from app.services.title import TitleService
from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.coin_transaction import CoinTransactionRepository


_UNSET = object()


class ProjectService:
    _PROJECT_TRANSITIONS = {
        ProjectStatus.PLANNING.value: {ProjectStatus.ACTIVE.value},
        ProjectStatus.ACTIVE.value: {
            ProjectStatus.COMPLETED.value,
            ProjectStatus.ARCHIVED.value,
        },
        ProjectStatus.COMPLETED.value: {ProjectStatus.ARCHIVED.value},
        ProjectStatus.ARCHIVED.value: set(),
    }
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

    def get_project_for_user_locked(self, project_id: UUID, user_id: UUID) -> Project:
        project = self.project_repo.get_for_update(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return project

    def get_phase_for_project(
        self, phase_id: UUID, project_id: UUID, for_update: bool = False
    ) -> ProjectPhase:
        phase = (
            self.phase_repo.get_for_update(phase_id)
            if for_update
            else self.phase_repo.get_by_id(phase_id)
        )
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

    def get_milestone_for_project_locked(
        self, milestone_id: UUID, project_id: UUID
    ) -> ProjectMilestone:
        milestone = self.milestone_repo.get_for_update(milestone_id)
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
        tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.user_id == project.user_id,
        ).all()
        stats["phases"] = phases
        stats["milestones"] = milestones
        stats["tasks"] = tasks
        return stats

    def update_project(self, project: Project, data: ProjectUpdate) -> Project:
        try:
            update_data = data.model_dump(exclude_unset=True)
            if "status" in update_data:
                target_status = update_data["status"].value
                current_status = normalize_project_status(project.status)
                if current_status != target_status:
                    self._validate_project_transition(current_status, target_status)
                update_data["status"] = target_status
            return self.project_repo.update(project, update_data)
        except Exception:
            self.db.rollback()
            raise

    def _ensure_no_foreign_task_links(self, task_filter, owner_id: UUID) -> None:
        if self.db.query(Task.id).filter(
            task_filter,
            Task.user_id != owner_id,
        ).first() is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "PROJECT_RESOURCE_HAS_FOREIGN_TASKS",
                    "message": "项目层级存在其他用户的历史任务关联，暂不能删除。",
                },
            )

    @staticmethod
    def _project_task_link_filter(project_id: UUID):
        return or_(
            Task.project_id == project_id,
            Task.phase_id.in_(
                select(ProjectPhase.id).where(ProjectPhase.project_id == project_id)
            ),
            Task.milestone_id.in_(
                select(ProjectMilestone.id).where(ProjectMilestone.project_id == project_id)
            ),
        )

    def delete_project(self, project: Project) -> None:
        try:
            self.user_repo.lock(project.user_id)
            locked_project = self.project_repo.get_for_update(project.id)
            if locked_project is None:
                raise HTTPException(status_code=404, detail="Project not found")
            project = locked_project
            task_filter = self._project_task_link_filter(project.id)
            self._ensure_no_foreign_task_links(task_filter, project.user_id)
            # Detach only the owner's tasks before deleting the project tree.
            self.db.query(Task).filter(
                task_filter,
                Task.user_id == project.user_id,
            ).update(
                {Task.project_id: None, Task.phase_id: None, Task.milestone_id: None},
                synchronize_session=False,
            )
            self.db.flush()
            self.project_repo.delete(project.id)
        except Exception:
            self.db.rollback()
            raise

    @classmethod
    def _validate_project_transition(cls, current_status: str, target_status: str) -> None:
        if target_status not in cls._PROJECT_TRANSITIONS.get(current_status, set()):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot transition project from {current_status} to {target_status}",
            )

    def _transition_project(
        self, project: Project, target_status: str, *, commit: bool = True
    ) -> Project:
        current_status = normalize_project_status(project.status)
        if current_status == target_status:
            return project
        self._validate_project_transition(current_status, target_status)
        project.status = target_status
        project.updated_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()
            self.db.refresh(project)
        return project

    def start_project(self, project: Project) -> Project:
        return self._transition_project(project, ProjectStatus.ACTIVE.value)

    def complete_project(self, project: Project) -> Project:
        if normalize_project_status(project.status) == ProjectStatus.COMPLETED.value:
            return project
        try:
            project = self._transition_project(
                project, ProjectStatus.COMPLETED.value, commit=False
            )
            self.db.flush()
            completed_count = self.db.query(Project).filter(
                Project.user_id == project.user_id,
                Project.status == ProjectStatus.COMPLETED,
            ).count()
            self.achievement_service.check_and_unlock(
                project.user_id,
                "project_completed",
                completed_count,
                commit=False,
            )
            self.db.commit()
            self.db.refresh(project)
            return project
        except Exception:
            self.db.rollback()
            raise

    # --- Phase CRUD ---
    def create_phase(self, project_id: UUID, data: PhaseCreate) -> ProjectPhase:
        try:
            obj_data = data.model_dump()
            obj_data["project_id"] = project_id
            return self.phase_repo.create(obj_data)
        except Exception:
            self.db.rollback()
            raise

    def update_phase(self, phase: ProjectPhase, data: PhaseUpdate) -> ProjectPhase:
        try:
            update_data = data.model_dump(exclude_unset=True)
            return self.phase_repo.update(phase, update_data)
        except Exception:
            self.db.rollback()
            raise

    def delete_phase(self, phase: ProjectPhase) -> None:
        try:
            self.user_repo.lock(phase.project.user_id)
            self.project_repo.get_for_update(phase.project_id)
            locked_phase = self.phase_repo.get_for_update(phase.id)
            if locked_phase is None:
                raise HTTPException(status_code=404, detail="Phase not found")
            self._ensure_no_foreign_task_links(
                Task.phase_id == phase.id,
                locked_phase.project.user_id,
            )
            task_count = self.phase_repo.count_tasks(phase.id)
            if task_count:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "PROJECT_PHASE_HAS_TASKS",
                        "message": f"阶段仍有 {task_count} 个任务，请先移动任务后再删除。",
                        "task_count": task_count,
                    },
                )
            if not self.phase_repo.delete_if_empty(phase.id):
                task_count = self.phase_repo.count_tasks(phase.id)
                if task_count:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "PROJECT_PHASE_HAS_TASKS",
                            "message": f"阶段仍有 {task_count} 个任务，请先移动任务后再删除。",
                            "task_count": task_count,
                        },
                    )
                raise HTTPException(status_code=404, detail="Phase not found")
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # --- Milestone CRUD ---
    def create_milestone(self, project_id: UUID, data: MilestoneCreate) -> ProjectMilestone:
        obj_data = data.model_dump()
        obj_data["project_id"] = project_id
        return self.milestone_repo.create(obj_data)

    def update_milestone(self, milestone: ProjectMilestone, data: MilestoneUpdate) -> ProjectMilestone:
        update_data = data.model_dump(exclude_unset=True)
        return self.milestone_repo.update(milestone, update_data)

    def delete_milestone(self, milestone: ProjectMilestone) -> None:
        try:
            self.user_repo.lock(milestone.project.user_id)
            locked_project = self.project_repo.get_for_update(milestone.project_id)
            if locked_project is None:
                raise HTTPException(status_code=404, detail="Project not found")
            locked_milestone = self.milestone_repo.get_for_update(milestone.id)
            if locked_milestone is None:
                raise HTTPException(status_code=404, detail="Milestone not found")
            milestone = locked_milestone
            owner_id = locked_project.user_id
            self._ensure_no_foreign_task_links(
                Task.milestone_id == milestone.id,
                owner_id,
            )
            self.db.query(Task).filter(
                Task.milestone_id == milestone.id,
                Task.user_id == owner_id,
            ).update(
                {Task.milestone_id: None},
                synchronize_session=False,
            )
            self.db.flush()
            self.milestone_repo.delete(milestone.id)
        except Exception:
            self.db.rollback()
            raise

    def reach_milestone(self, milestone: ProjectMilestone) -> ProjectMilestone:
        if milestone.status == MilestoneStatus.REACHED or milestone.reached_at is not None:
            return milestone
        milestone.status = MilestoneStatus.REACHED
        milestone.reached_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(milestone)
        return milestone

    # --- Tasks within project ---
    def create_project_task(self, user_id: UUID, project_id: UUID, data: TaskCreate) -> Task:
        from app.services.todo import TodoService

        return TodoService(self.db).create_task(user_id, data.model_copy(update={"project_id": project_id}))

    def get_project_tasks(
        self,
        project_id: UUID,
        user_id: UUID,
        phase_id: Optional[UUID] = None,
        milestone_id: Optional[UUID] = None,
    ) -> List[Task]:
        query = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.user_id == user_id,
        )
        if phase_id:
            query = query.filter(Task.phase_id == phase_id)
        if milestone_id:
            query = query.filter(Task.milestone_id == milestone_id)
        return query.order_by(Task.sort_order).all()

    def move_task(
        self,
        task: Task,
        user_id: UUID,
        project_id: UUID | None | object = _UNSET,
        phase_id: UUID | None | object = _UNSET,
        milestone_id: UUID | None | object = _UNSET,
        status: TaskStatus | None | object = _UNSET,
    ) -> Task:
        from app.services.todo import TodoService

        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        changes = {field: value for field, value in (
            ("project_id", project_id), ("phase_id", phase_id),
            ("milestone_id", milestone_id), ("status", status),
        ) if value is not _UNSET}
        return TodoService(self.db).update_task(task, TaskUpdate(**changes))

    # --- Stats helper ---
    def _compute_project_stats(self, project: Project) -> dict:
        total = self.db.query(Task).filter(
            Task.project_id == project.id,
            Task.user_id == project.user_id,
        ).count()
        completed = self.db.query(Task).filter(
            Task.project_id == project.id,
            Task.user_id == project.user_id,
            Task.status == TaskStatus.COMPLETED,
        ).count()
        progress = (completed / total * 100) if total > 0 else 0.0
        return {
            "project": project,
            "total_tasks": total,
            "completed_tasks": completed,
            "progress": round(progress, 1),
        }
