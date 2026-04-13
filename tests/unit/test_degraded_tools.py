"""Tests for previously-degraded tools, now promoted to registry.py.

These tools were moved from degraded_tools.py to registry.py in Phase 70-02.
They now return success=True (not "degraded_completed") and live in the
app.agents.tools.registry module.

analyze_sentiment and ocr_document are excluded here — Phase 70-01 covers them.
"""

import pytest

from app.agents.tools import registry as reg


@pytest.fixture(autouse=True)
def _patch_dependencies(monkeypatch):
    """Patch all underlying service calls so tests are fast and isolated."""

    async def _fake_create_task(description: str, **kwargs):
        return {"success": True, "task": {"id": "task-1", "description": description}}

    async def _fake_save_content(title: str, content: str, **kwargs):
        return {
            "success": True,
            "content": {"id": "content-1", "title": title, "content": content},
        }

    async def _fake_track_event(
        event_name: str, category: str, properties: str | None = None, **kwargs
    ):
        return {
            "success": True,
            "event": {
                "name": event_name,
                "category": category,
                "properties": properties,
            },
        }

    async def _fake_create_initiative(title: str, description: str, **kwargs):
        return {
            "success": True,
            "initiative": {"id": "init-1", "title": title, "description": description},
        }

    async def _fake_create_audit(
        title: str, scope: str, auditor: str, scheduled_date: str, **kwargs
    ):
        return {
            "success": True,
            "audit": {
                "id": "audit-1",
                "title": title,
                "scope": scope,
                "auditor": auditor,
            },
        }

    monkeypatch.setattr(reg, "create_task", _fake_create_task)
    monkeypatch.setattr(reg, "save_content", _fake_save_content)
    monkeypatch.setattr(reg, "track_event", _fake_track_event)
    monkeypatch.setattr(reg, "create_initiative", _fake_create_initiative)
    monkeypatch.setattr(reg, "create_audit", _fake_create_audit)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fn_name", "kwargs"),
    [
        ("promoted_create_folder", {"name": "Ops"}),
        ("promoted_create_project", {"name": "Project X"}),
        ("promoted_record_notes", {"title": "Meeting notes"}),
        ("promoted_upload_document", {"name": "spec.pdf"}),
        ("promoted_upload_file", {"name": "brief.txt"}),
        ("promoted_run_audit", {"title": "Ops Audit", "scope": "operations"}),
        ("promoted_update_subscription", {"plan": "pro", "status": "active"}),
        ("promoted_create_task_list", {"name": "Sprint backlog"}),
        ("promoted_create_checklist", {"name": "Launch checklist"}),
        ("promoted_run_checklist", {"name": "Launch checklist"}),
        ("promoted_process_expense", {"expense_title": "Flight", "amount": 450.0}),
        ("promoted_log_shipment", {"reference": "SHP-1"}),
        ("promoted_verify_po", {"reference": "PO-1"}),
        (
            "promoted_create_alert",
            {"message": "Threshold exceeded", "severity": "high"},
        ),
        ("promoted_run_test", {"name": "Regression"}),
        ("promoted_test_scenario", {"name": "Checkout flow"}),
    ],
)
async def test_promoted_tool_returns_success(fn_name, kwargs):
    """All promoted tools return success=True with a tool identifier."""
    fn = getattr(reg, fn_name)
    result = await fn(**kwargs)
    assert result.get("success") is True, f"{fn_name} returned {result}"
    assert result.get("tool"), f"{fn_name} missing 'tool' field"
    # Must NOT be reporting degraded status
    assert result.get("status") != "degraded_completed", (
        f"{fn_name} still returns 'degraded_completed'"
    )
    assert result.get("status") != "simulated_success", (
        f"{fn_name} returns simulated_success"
    )


@pytest.mark.asyncio
async def test_not_available_book_travel():
    """book_travel returns success=False with an honest error message."""
    result = await reg.not_available_book_travel(traveler="Alice", itinerary="NYC")
    assert result["success"] is False
    assert "error" in result
    msg = result["error"].lower()
    assert "not available" in msg or "not yet" in msg, (
        f"Expected limitation message, got: {result['error']}"
    )
    assert result.get("tool") == "book_travel"


@pytest.mark.asyncio
async def test_promoted_tool_module_is_registry():
    """Promoted tools live in the registry module, not degraded_tools."""
    promoted_fns = [
        reg.promoted_create_folder,
        reg.promoted_create_project,
        reg.promoted_record_notes,
        reg.promoted_upload_document,
        reg.promoted_upload_file,
        reg.promoted_run_audit,
        reg.promoted_update_subscription,
        reg.promoted_create_task_list,
        reg.promoted_create_checklist,
        reg.promoted_run_checklist,
        reg.promoted_process_expense,
        reg.promoted_log_shipment,
        reg.promoted_verify_po,
        reg.promoted_create_alert,
        reg.promoted_run_test,
        reg.promoted_test_scenario,
        reg.not_available_book_travel,
    ]
    for fn in promoted_fns:
        mod = getattr(fn, "__module__", "")
        assert "degraded_tools" not in mod, (
            f"{fn.__name__} still in degraded_tools module: {mod}"
        )
