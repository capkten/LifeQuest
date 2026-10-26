"""Verify the integrated registry exposed by the real compatibility entrypoint."""
import asyncio
import json

import mcp_server


def test_integrated_registry_preserves_legacy_and_registers_new_domains():
    registered = asyncio.run(mcp_server.mcp.list_tools())
    names = [tool.name for tool in registered]
    assert len(names) == len(set(names)) == 173
    assert {
        'login', 'login_with_token', 'list_tasks', 'complete_habit', 'get_workbench',
        'finance_dashboard', 'move_project_task', 'create_note', 'start_focus_session',
        'get_weekly_review', 'get_action_center', 'snooze_task', 'reschedule_task',
        'create_note_link', 'list_target_notes', 'start_project',
        'update_recurring_transaction', 'purchase_shop_item', 'refund_shop_exchange',
        'get_coin_history', 'equip_backpack_item', 'get_habit_stats',
        'update_notebook', 'add_notebook_member', 'get_cultivation_world',
        'attempt_tribulation', 'ascend', 'run_immortal_activity',
        'get_focus_session_history', 'get_encounter_catalog',
    } <= set(names)
    for tool in registered:
        assert json.dumps(tool.inputSchema)
        assert 'user_id' not in tool.inputSchema.get('properties', {})
    schema = {tool.name: tool.inputSchema for tool in registered}
    assert 'base_revision' in schema['update_note']['properties']
    assert 'schedule' in schema['create_task']['properties']
    assert 'occurrence_date' in schema['complete_task']['properties']
    assert 'force_encounter' not in schema['complete_focus_session']['properties']
