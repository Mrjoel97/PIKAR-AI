"""Verify Phase 70 degraded tool cleanup is complete.

These tests confirm that:
1. No TOOL_REGISTRY entry resolves to the degraded_tools module.
2. classify_tool_trust returns 'direct' (not 'degraded') for all registered tools.
3. book_travel returns success=False with a clear limitation message.
4. Every previously-degraded tool is still present in the registry.
"""

import asyncio

import pytest

from app.agents.tools.registry import TOOL_REGISTRY
from app.workflows.execution_contracts import classify_tool


def test_no_degraded_tools_in_registry():
    """No TOOL_REGISTRY entry should resolve to the degraded_tools module.

    analyze_sentiment and ocr_document are exempt — Phase 70-01 handles them.
    """
    phase_70_01_scope = {"analyze_sentiment", "ocr_document"}
    degraded = {
        name: getattr(fn, "__module__", "unknown")
        for name, fn in TOOL_REGISTRY.items()
        if "degraded_tools" in getattr(fn, "__module__", "")
        and name not in phase_70_01_scope
    }
    assert degraded == {}, f"Degraded tools still in registry (70-02 scope): {degraded}"


def test_classify_tool_no_degraded_outside_70_01():
    """classify_tool should not return 'degraded' for 70-02 scope tools."""
    phase_70_01_scope = {"analyze_sentiment", "ocr_document"}
    degraded = [
        name
        for name in TOOL_REGISTRY
        if classify_tool(name) == "degraded" and name not in phase_70_01_scope
    ]
    assert degraded == [], (
        f"Tools classified as degraded (should be promoted): {degraded}"
    )


def test_book_travel_returns_honest_error():
    """book_travel should return success=False with clear limitation message."""
    fn = TOOL_REGISTRY["book_travel"]
    result = asyncio.run(fn(traveler="Test User", itinerary="NYC to LAX"))
    assert result["success"] is False
    assert "error" in result
    error_msg = result["error"].lower()
    assert "not available" in error_msg or "not yet" in error_msg, (
        f"Expected limitation message, got: {result['error']}"
    )


PROMOTED_TOOLS = [
    # Category A — save_content-backed
    "create_folder",
    "record_notes",
    "upload_document",
    "upload_file",
    # Category A — create_initiative-backed
    "create_project",
    # Category A — create_audit-backed
    "run_audit",
    # Category A — track_event-backed
    "update_subscription",
    # Category A — create_task-backed
    "create_task_list",
    "create_checklist",
    "run_checklist",
    "process_expense",
    "log_shipment",
    "verify_po",
    "create_alert",
    "run_test",
    "test_scenario",
    # Category C — already replaced by phases 60-69 (real implementations)
    "configure_ads",
    "optimize_spend",
    "create_contact",
    "query_crm",
    "generate_forecast",
    "create_forecast",
    "assign_training",
    "post_job_board",
    "query_analytics",
    "query_usage",
    # Category D — honest error stub
    "book_travel",
]


@pytest.mark.parametrize("tool_name", PROMOTED_TOOLS)
def test_promoted_tool_exists_in_registry(tool_name):
    """Every previously-degraded tool should still be accessible in the registry."""
    assert tool_name in TOOL_REGISTRY, f"{tool_name} missing from TOOL_REGISTRY"


@pytest.mark.parametrize("tool_name", PROMOTED_TOOLS)
def test_promoted_tool_not_from_degraded_module(tool_name):
    """Every previously-degraded tool must NOT point to degraded_tools module."""
    fn = TOOL_REGISTRY[tool_name]
    fn_module = getattr(fn, "__module__", "")
    assert "degraded_tools" not in fn_module, (
        f"{tool_name} still points to degraded_tools module: {fn_module}"
    )
