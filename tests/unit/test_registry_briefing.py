"""Verify briefing tools are correctly wired into the workflow registry."""

import pytest


def test_briefing_tools_in_registry():
    """All 5 briefing tools must be registered in TOOL_REGISTRY."""
    from app.agents.tools.registry import TOOL_REGISTRY

    expected = [
        "get_daily_briefing",
        "refresh_briefing",
        "approve_draft",
        "dismiss_item",
        "undo_auto_action",
    ]
    for name in expected:
        assert name in TOOL_REGISTRY, f"'{name}' missing from TOOL_REGISTRY"
        assert callable(TOOL_REGISTRY[name]), f"'{name}' is not callable"


@pytest.mark.asyncio
async def test_approve_draft_blocked_in_workflow_context():
    """approve_draft should return an error when called without agent context."""
    from app.agents.tools.registry import TOOL_REGISTRY

    result = await TOOL_REGISTRY["approve_draft"](triage_item_id="fake-id")
    assert result["status"] == "error"
    assert "agent context" in result["message"].lower()
