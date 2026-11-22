"""Verify MCP clients can distinguish read-only, write and destructive tools."""

import asyncio

import mcp_server
from app.mcp.tool_annotations import (
    DESTRUCTIVE_TOOL_NAMES,
    READ_ONLY_TOOL_NAMES,
)


def test_all_mcp_tools_have_safety_annotations():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    assert len(tools) == 173

    read_only = set()
    destructive = set()
    writes = set()

    for tool in tools:
        assert tool.annotations is not None, tool.name
        assert tool.annotations.readOnlyHint is not None, tool.name
        assert tool.annotations.destructiveHint is not None, tool.name
        assert not (
            tool.annotations.readOnlyHint and tool.annotations.destructiveHint
        ), tool.name

        if tool.annotations.readOnlyHint:
            read_only.add(tool.name)
        elif tool.annotations.destructiveHint:
            destructive.add(tool.name)
        else:
            writes.add(tool.name)

    assert read_only == READ_ONLY_TOOL_NAMES
    assert destructive == DESTRUCTIVE_TOOL_NAMES
    assert len(read_only) == 69
    assert len(destructive) == 26
    assert len(writes) == 78

    assert {
        "list_tasks",
        "get_profile",
        "get_action_center",
        "get_encounter_catalog",
    } <= read_only
    assert {
        "delete_task",
        "refund_shop_exchange",
        "attempt_tribulation",
    } <= destructive
    assert {
        "login",
        "create_task",
        "complete_habit",
        "update_note",
    } <= writes
