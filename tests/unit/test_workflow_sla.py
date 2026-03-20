"""Tests for workflow SLA tracking."""

import asyncio
from datetime import datetime, timedelta, timezone


def _run(coro):
    return asyncio.run(coro)


def test_sla_on_track():
    from app.workflows.step_executor import check_sla_status
    future = datetime.now(timezone.utc) + timedelta(hours=24)
    result = _run(check_sla_status({"sla_deadline": future}))
    assert result == "on_track"


def test_sla_at_risk():
    from app.workflows.step_executor import check_sla_status
    near_future = datetime.now(timezone.utc) + timedelta(hours=1)
    result = _run(check_sla_status({"sla_deadline": near_future}))
    assert result == "at_risk"


def test_sla_breached():
    from app.workflows.step_executor import check_sla_status
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    result = _run(check_sla_status({"sla_deadline": past}))
    assert result == "breached"


def test_sla_no_deadline():
    from app.workflows.step_executor import check_sla_status
    result = _run(check_sla_status({}))
    assert result == "on_track"


def test_sla_string_deadline():
    from app.workflows.step_executor import check_sla_status
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    result = _run(check_sla_status({"sla_deadline": past}))
    assert result == "breached"


def test_handle_breach_notify():
    from app.workflows.step_executor import handle_sla_breach
    result = _run(handle_sla_breach(
        {"name": "legal_review", "escalation": "notify"},
        "exec-123",
    ))
    assert result["action"] == "notification_sent"
    assert result["step"] == "legal_review"


def test_handle_breach_block():
    from app.workflows.step_executor import handle_sla_breach
    result = _run(handle_sla_breach(
        {"name": "approval_gate", "escalation": "block"},
        "exec-456",
    ))
    assert result["action"] == "workflow_blocked"


def test_handle_breach_auto_approve():
    from app.workflows.step_executor import handle_sla_breach
    result = _run(handle_sla_breach(
        {"name": "minor_check", "escalation": "auto_approve"},
        "exec-789",
    ))
    assert result["action"] == "auto_approved"
