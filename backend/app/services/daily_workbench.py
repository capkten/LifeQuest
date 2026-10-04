from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.daily_workbench import DailyFocusPlan, WorkbenchTaskRequest
from app.models.todo import Task, TaskStatus
from app.repositories.user import UserRepository
from app.schemas.daily_workbench import DailyFocusUpdate, QuickTaskCreate
from app.schemas.todo import TaskCreate, TaskResponse
from app.services.transaction import rollback_on_error
from app.timezone import day_bounds_utc, local_date, today


class DailyWorkbenchService:
    def __init__(self, db: Session):
        self.db = db

    def _parse_focus_task_ids(self, plan: DailyFocusPlan | None) -> list[UUID]:
        if not plan or not isinstance(plan.task_ids, list):
            return []

        task_ids = []
        seen = set()
        for raw_task_id in plan.task_ids:
            try:
                task_id = UUID(str(raw_task_id))
            except (TypeError, ValueError, AttributeError):
                continue
            if task_id in seen:
                continue
            seen.add(task_id)
            task_ids.append(task_id)
            if len(task_ids) == 3:
                break
        return task_ids

    def get_workbench(self, user_id: UUID) -> dict:
        current_date = today()
        start, end = day_bounds_utc(current_date)
        plan = self.db.query(DailyFocusPlan).filter_by(user_id=user_id, plan_date=current_date).first()
        open_tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
        ).order_by(Task.deadline.is_(None), Task.deadline, Task.created_at.desc(), Task.id).all()
        groups = {key: [] for key in ("today", "overdue", "unscheduled", "upcoming")}
        for task in open_tasks:
            if task.deadline is None:
                group = "unscheduled"
            else:
                due_date = local_date(task.deadline)
                group = "today" if due_date == current_date else "overdue" if due_date < current_date else "upcoming"
            groups[group].append(TaskResponse.model_validate(task).model_dump(mode="json"))

        focus_ids = self._parse_focus_task_ids(plan)
        focus_rows = self.db.query(Task).filter(
            Task.user_id == user_id, Task.id.in_(focus_ids), Task.status != TaskStatus.CANCELLED,
        ).all() if focus_ids else []
        focus_by_id = {task.id: task for task in focus_rows}
        focus_tasks = [TaskResponse.model_validate(focus_by_id[task_id]).model_dump(mode="json")
                       for task_id in focus_ids if task_id in focus_by_id]
        completed_today = self.db.query(Task).filter(
            Task.user_id == user_id, Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= start, Task.completed_at < end,
        ).count()
        return {
            "date": current_date.isoformat(),
            "revision": plan.revision if plan else 0,
            "focus_tasks": focus_tasks,
            "task_groups": groups,
            "summary": {
                "completed_today": completed_today,
                "open_tasks": len(open_tasks),
                "today": len(groups["today"]),
                "overdue": len(groups["overdue"]),
                "unscheduled": len(groups["unscheduled"]),
                "focus_completed": sum(task["status"] == TaskStatus.COMPLETED for task in focus_tasks),
            },
        }

    @rollback_on_error
    def update_focus(self, user_id: UUID, data: DailyFocusUpdate) -> dict:
        UserRepository(self.db).lock(user_id)
        if data.date != today():
            raise HTTPException(status_code=409, detail="中国日期已变化，请刷新后重新选择今日重点")
        plan = self.db.query(DailyFocusPlan).filter_by(
            user_id=user_id, plan_date=data.date,
        ).populate_existing().first()
        if data.revision != (plan.revision if plan else 0):
            raise HTTPException(status_code=409, detail="今日重点已在其他页面更新，请刷新后重新选择")
        tasks = self.db.query(Task).filter(
            Task.id.in_(data.task_ids), Task.user_id == user_id,
            Task.status != TaskStatus.CANCELLED,
        ).all() if data.task_ids else []
        if len(tasks) != len(data.task_ids):
            raise HTTPException(status_code=404, detail="所选任务不存在、已取消或无权访问")
        if plan is None:
            plan = DailyFocusPlan(user_id=user_id, plan_date=data.date, revision=0)
            self.db.add(plan)
        plan.task_ids = [str(task_id) for task_id in data.task_ids]
        plan.revision += 1
        self.db.commit()
        return self.get_workbench(user_id)

    @rollback_on_error
    def create_quick_task(self, user_id: UUID, data: QuickTaskCreate) -> Task:
        UserRepository(self.db).lock(user_id)
        payload = {
            "title": data.title,
            "schedule": data.schedule,
            "due_date": data.due_date.isoformat() if data.due_date else None,
        }
        existing = self.db.query(WorkbenchTaskRequest).filter_by(
            user_id=user_id, request_id=data.request_id,
        ).first()
        if existing:
            if existing.payload != payload:
                raise HTTPException(status_code=409, detail="此创建请求已用于其他内容，请重新开始创建")
            task = self.db.query(Task).filter_by(id=existing.task_id, user_id=user_id).first()
            if task is None:
                raise HTTPException(status_code=409, detail="此请求创建的任务已被删除，请重新开始创建")
            self.db.commit()
            return task

        due_date = today() if data.schedule == "today" else data.due_date
        deadline = day_bounds_utc(due_date)[1] - timedelta(microseconds=1) if due_date else None
        values = TaskCreate(title=data.title, deadline=deadline).model_dump()
        task = Task(user_id=user_id, **values)
        self.db.add(task)
        self.db.flush()
        self.db.add(WorkbenchTaskRequest(
            user_id=user_id, request_id=data.request_id, task_id=task.id, payload=payload,
        ))
        self.db.commit()
        self.db.refresh(task)
        return task
