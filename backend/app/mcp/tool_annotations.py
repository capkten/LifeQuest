"""MCP tool safety metadata for client-side confirmation policies."""

from mcp.server.fastmcp import FastMCP


READ_ONLY_TOOL_NAMES = frozenset({
    "list_habits",
    "list_tasks",
    "list_goals",
    "get_habit_history",
    "get_habit_pause_intervals",
    "get_habit_leave_intervals",
    "list_subtasks",
    "get_workbench",
    "get_daily_summary",
    "finance_dashboard",
    "list_accounts",
    "list_categories",
    "list_transactions",
    "list_budgets",
    "list_recurring_transactions",
    "list_debts",
    "list_projects",
    "get_project_detail",
    "list_project_tasks",
    "get_stats",
    "get_profile",
    "list_notebooks",
    "get_notebook_tree",
    "list_note_children",
    "list_recent_notes",
    "discover_notes",
    "search_notes",
    "get_note",
    "get_active_focus_session",
    "list_shop_items",
    "get_shop_item",
    "list_shop_exchanges",
    "get_shop_exchange",
    "get_coin_totals",
    "get_coin_history",
    "list_backpack_items",
    "get_backpack_item",
    "get_backpack_history",
    "get_task_trends",
    "get_habit_stats",
    "get_coin_trends",
    "get_level_progress",
    "get_calendar_events",
    "get_calendar_day",
    "get_checkin_status",
    "get_task",
    "get_habit",
    "get_goal",
    "get_subtask",
    "list_achievements",
    "get_user_achievements",
    "list_titles",
    "get_user_titles",
    "list_notebook_members",
    "get_cultivation_overview",
    "get_cultivation_world",
    "list_sects",
    "get_sect_access",
    "evaluate_hidden_sects",
    "get_techniques",
    "list_npcs",
    "get_tribulation_preview",
    "get_immortal_overview",
    "get_weekly_review",
    "get_action_center",
    "list_note_links",
    "list_target_notes",
    "get_focus_session_history",
    "get_encounter_catalog",
})

DESTRUCTIVE_TOOL_NAMES = frozenset({
    "delete_goal",
    "delete_task",
    "delete_habit",
    "delete_habit_leave",
    "delete_subtask",
    "delete_account",
    "delete_category",
    "delete_transaction",
    "delete_budget",
    "delete_recurring_transaction",
    "delete_debt",
    "delete_project",
    "delete_project_phase",
    "delete_project_milestone",
    "delete_notebook",
    "delete_node",
    "delete_shop_item",
    "delete_note_link",
    "remove_notebook_member",
    "abort_focus_session",
    "refund_shop_exchange",
    "discard_backpack_item",
    "use_backpack_item",
    "leave_sect",
    "attempt_tribulation",
    "transfer",
})

READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
}
WRITE_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
}
DESTRUCTIVE_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
}


def tool_annotations(tool_name: str) -> dict[str, bool]:
    """Return conservative safety hints for a registered MCP tool."""
    if tool_name in READ_ONLY_TOOL_NAMES:
        return READ_ONLY_ANNOTATIONS.copy()
    if tool_name in DESTRUCTIVE_TOOL_NAMES:
        return DESTRUCTIVE_ANNOTATIONS.copy()
    return WRITE_ANNOTATIONS.copy()


class LifeQuestFastMCP(FastMCP):
    """FastMCP server that annotates every tool by its business semantics."""

    def tool(self, name=None, description=None, annotations=None):
        if annotations is not None:
            return super().tool(name, description, annotations)

        def decorator(function):
            return super(LifeQuestFastMCP, self).tool(
                name=name,
                description=description,
                annotations=tool_annotations(name or function.__name__),
            )(function)

        return decorator
