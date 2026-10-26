"""Small management actions that share the REST business service paths."""
from typing import Any
from uuid import UUID

from app.schemas.finance import RecurringResponse, RecurringUpdate
from app.schemas.project import ProjectResponse
from app.services.finance import FinanceService
from app.services.project import ProjectService


def register(mcp, resolve_user_id, serialize, session_factory):
    tools = {}

    def tool(function):
        tools[function.__name__] = function
        mcp.tool()(function)
        return function

    @tool
    def start_project(project_id: str) -> Any:
        """Start an owned project using the normal lifecycle transition rules."""
        with session_factory() as db:
            uid = resolve_user_id(db)
            service = ProjectService(db)
            project = service.get_project_for_user_locked(UUID(project_id), uid)
            started = service.start_project(project)
            stats = service._compute_project_stats(started)
            response = ProjectResponse.model_validate(started).model_copy(update={
                'total_tasks': stats['total_tasks'],
                'completed_tasks': stats['completed_tasks'],
                'progress': stats['progress'],
            })
            return serialize(response)

    @tool
    def update_recurring_transaction(recurring_id: str, changes: dict[str, Any]) -> Any:
        """Update explicit recurring fields. Null clears category or description; account ownership is enforced."""
        unknown = set(changes) - set(RecurringUpdate.model_fields)
        if unknown:
            raise ValueError(f'Unknown recurring fields: {sorted(unknown)}')
        data = RecurringUpdate.model_validate(changes)
        with session_factory() as db:
            uid = resolve_user_id(db)
            service = FinanceService(db)
            recurring = service.recurring_repo.get_by_id(UUID(recurring_id))
            if recurring is None or recurring.user_id != uid:
                raise ValueError('Recurring transaction not found')
            updated = service.update_recurring(recurring, data, uid)
            return serialize(RecurringResponse.model_validate(updated))

    return tools
