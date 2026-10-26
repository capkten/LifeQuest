"""Execution planning and explicit note links through existing business services."""
from datetime import date
from typing import Any, Optional
from uuid import UUID

from app.schemas.action_center import TodayActionCenter
from app.schemas.note_link import NoteLinkCreate, NoteLinkSummary
from app.schemas.review import WeeklyReviewResponse
from app.schemas.task_schedule import TaskSnoozeRequest, TaskRescheduleRequest
from app.services.action_center import ActionCenterService
from app.services.note_link import NoteLinkService
from app.services.review import ReviewService
from app.services.todo import TodoService


def register(mcp, resolve_user_id, serialize, session_factory):
    tools = {}

    def tool(function):
        tools[function.__name__] = function
        mcp.tool()(function)
        return function

    def run(service, operation):
        with session_factory() as db:
            uid = resolve_user_id(db)
            return serialize(operation(service(db), uid))

    @tool
    def get_weekly_review(week_start: Optional[str] = None) -> Any:
        """Read a China calendar weekly review. Optional ISO week_start must be Monday."""
        start = date.fromisoformat(week_start) if week_start is not None else None
        return run(ReviewService, lambda svc, uid: WeeklyReviewResponse.model_validate(svc.get_weekly_review(uid, start)))

    @tool
    def get_action_center(target_date: Optional[str] = None) -> Any:
        """Read today's execution actions or an ISO China calendar date without completing anything."""
        target = date.fromisoformat(target_date) if target_date is not None else None
        return run(ActionCenterService, lambda svc, uid: TodayActionCenter.model_validate(svc.get_today(uid, target)))

    @tool
    def snooze_task(task_id: str, until: str, occurrence_date: Optional[str] = None) -> Any:
        """Snooze an owned task until an ISO timestamp; recurring tasks accept an occurrence date."""
        request = TaskSnoozeRequest.model_validate({'until': until, 'occurrence_date': occurrence_date})
        return run(TodoService, lambda svc, uid: svc.schedule_service.snooze(svc.get_task_for_user(UUID(task_id), uid), request.until, request.occurrence_date))

    @tool
    def reschedule_task(task_id: str, deadline: Optional[str] = None, occurrence_date: Optional[str] = None, new_occurrence_date: Optional[str] = None) -> Any:
        """Set a task deadline or move one recurring occurrence. Supply one target form."""
        request = TaskRescheduleRequest.model_validate({'deadline': deadline, 'occurrence_date': occurrence_date, 'new_occurrence_date': new_occurrence_date})
        return run(TodoService, lambda svc, uid: svc.schedule_service.reschedule(svc.get_task_for_user(UUID(task_id), uid), deadline=request.deadline, occurrence_date=request.occurrence_date, new_occurrence_date=request.new_occurrence_date))

    @tool
    def list_note_links(note_id: str) -> Any:
        """Read accessible task, goal and project link summaries attached to a note."""
        return run(NoteLinkService, lambda svc, uid: [NoteLinkSummary.model_validate(item) for item in svc.list_for_note(UUID(note_id), uid)])

    @tool
    def list_target_notes(kind: str, target_id: str) -> Any:
        """Read accessible linked notes for an owned task, goal or project."""
        request = NoteLinkCreate.model_validate({'kind': kind, 'target_id': target_id})
        return run(NoteLinkService, lambda svc, uid: [NoteLinkSummary.model_validate(item) for item in svc.list_for_target(request.kind, request.target_id, uid)])

    @tool
    def create_note_link(note_id: str, kind: str, target_id: str) -> Any:
        """Link a writable note to an owned task, goal or project; duplicate links are rejected."""
        request = NoteLinkCreate.model_validate({'kind': kind, 'target_id': target_id})
        return run(NoteLinkService, lambda svc, uid: NoteLinkSummary.model_validate(svc.link(UUID(note_id), request.kind, request.target_id, uid)))

    @tool
    def delete_note_link(note_id: str, kind: str, target_id: str) -> Any:
        """Remove an explicit link after validating note write access and target ownership."""
        request = NoteLinkCreate.model_validate({'kind': kind, 'target_id': target_id})
        def remove(svc, uid):
            svc.unlink(UUID(note_id), request.kind, request.target_id, uid)
            return {'deleted': True}
        return run(NoteLinkService, remove)

    return tools
