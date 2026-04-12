# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for approval queue, governance audit logging, and circuit breaker (Phase 75-02).

Tests cover:
- Test 1: POST /self-improvement/actions/{id}/approve on pending_approval -> executes and sets applied
- Test 2: POST /self-improvement/actions/{id}/reject on pending_approval -> sets declined, no execution
- Test 3: POST /self-improvement/actions/{id}/approve on non-pending_approval -> 409 Conflict
- Test 4: Auto-executed action produces governance_audit_log row with correct fields
- Test 5: Admin-approved action produces governance_audit_log row with admin user_id
- Test 6: Rejected action produces rejection audit log only, not execution audit log
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENGINE_MODULE = "app.services.self_improvement_engine"
_ROUTER_MODULE = "app.routers.self_improvement"


def _mock_supabase_client() -> MagicMock:
    """Return a MagicMock that fakes Supabase table().select()...execute_async."""
    client = MagicMock()
    chain = MagicMock()
    chain.return_value = chain  # chaining: .select(), .eq(), .gte(), etc.
    chain.data = []
    client.table.return_value = chain
    return client


def _make_pending_action(action_id: str = "action-1") -> dict:
    """Return a minimal pending_approval improvement_actions row."""
    return {
        "id": action_id,
        "action_type": "skill_refined",
        "skill_name": "test_skill",
        "agent_id": None,
        "trigger_reason": "Low effectiveness",
        "reason": "Low effectiveness",
        "status": "pending_approval",
        "effectiveness_before": 0.35,
        "effectiveness_after": None,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "approved_by": None,
        "approved_at": None,
        "details": {},
        "metadata": {"effectiveness_score": 0.35},
    }


def _create_test_app(*, user_id: str = "admin-user-1") -> FastAPI:
    """Create a FastAPI app with the self-improvement router, rate limiter bypassed."""
    # Clear cached router module to pick up fresh imports
    for mod_name in list(sys.modules.keys()):
        if "self_improvement" in mod_name and "test_" not in mod_name:
            del sys.modules[mod_name]

    app = FastAPI()

    with patch("app.middleware.rate_limiter.limiter") as mock_limiter:
        mock_limiter.limit.return_value = lambda fn: fn
        from app.routers.self_improvement import router

        app.include_router(router)

    from app.routers.onboarding import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: user_id

    return app


# ---------------------------------------------------------------------------
# Test 1: Approve pending_approval action -> executes and sets applied
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_pending_action_executes_and_sets_applied():
    """POST /actions/{id}/approve on pending_approval calls execute_improvement and returns applied."""
    action = _make_pending_action("action-approve-1")
    execute_calls: list[dict] = []

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        if "fetch_action_for_approval" in (op_name or ""):
            resp.data = [action]
        else:
            resp.data = []
        return resp

    async def _mock_execute_improvement(self, action_data, actor_id=None):
        execute_calls.append({"action": action_data, "actor_id": actor_id})
        return {"action_id": action_data["id"], "status": "applied"}

    app = _create_test_app(user_id="admin-user-1")

    with (
        patch(
            f"{_ROUTER_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ROUTER_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_ENGINE_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_ENGINE_MODULE}.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
        patch(
            f"{_ENGINE_MODULE}.skills_registry",
        ),
        patch(
            f"{_ENGINE_MODULE}.CustomSkillsService",
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "execute_improvement",
            _mock_execute_improvement,
        ),
        patch(
            "app.services.governance_service.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
    ):
        client = TestClient(app)
        resp = client.post("/self-improvement/actions/action-approve-1/approve")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "applied"
    assert len(execute_calls) == 1
    assert execute_calls[0]["actor_id"] == "admin-user-1"


# ---------------------------------------------------------------------------
# Test 2: Reject pending_approval action -> declined, no execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_pending_action_sets_declined_no_execution():
    """POST /actions/{id}/reject on pending_approval sets declined without calling execute_improvement."""
    action = _make_pending_action("action-reject-1")
    execute_calls: list[str] = []

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        if "fetch_action_for_approval" in (op_name or ""):
            resp.data = [action]
        else:
            resp.data = []
        return resp

    async def _mock_execute_improvement(self, action_data, actor_id=None):
        execute_calls.append(action_data["id"])
        return {"action_id": action_data["id"], "status": "applied"}

    app = _create_test_app(user_id="admin-user-2")

    with (
        patch(
            f"{_ROUTER_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ROUTER_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
    ):
        client = TestClient(app)
        resp = client.post("/self-improvement/actions/action-reject-1/reject")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "declined"
    # execute_improvement must NOT have been called
    assert len(execute_calls) == 0, f"execute_improvement should not be called on reject, got: {execute_calls}"


# ---------------------------------------------------------------------------
# Test 3: Approve non-pending_approval action -> 409 Conflict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_non_pending_action_returns_409():
    """POST /actions/{id}/approve on an already-applied action returns 409 Conflict."""
    action = _make_pending_action("action-conflict-1")
    action["status"] = "applied"  # NOT pending_approval

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        if "fetch_action_for_approval" in (op_name or ""):
            resp.data = [action]
        else:
            resp.data = []
        return resp

    app = _create_test_app(user_id="admin-user-3")

    with (
        patch(
            f"{_ROUTER_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ROUTER_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
    ):
        client = TestClient(app)
        resp = client.post("/self-improvement/actions/action-conflict-1/approve")

    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 4: Auto-executed action produces governance_audit_log row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_executed_action_produces_audit_log():
    """When execute_improvement runs for an auto-executed action, a governance audit log row is created."""
    audit_log_calls: list[dict] = []

    async def _mock_gov_log_event(
        self, user_id, action_type, resource_type, resource_id=None, details=None, ip_address=None,
    ):
        audit_log_calls.append({
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
        })

    action = {
        "id": "auto-action-1",
        "action_type": "skill_demoted",
        "skill_name": "unused_skill",
        "trigger_reason": "No uses in 30 days",
        "status": "pending",
        "metadata": {"effectiveness_score": 0.2},
        "effectiveness_before": 0.2,
    }

    mock_client = _mock_supabase_client()

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        resp.data = []
        return resp

    with (
        patch(
            f"{_ENGINE_MODULE}.get_service_client",
            return_value=mock_client,
        ),
        patch(
            f"{_ENGINE_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ENGINE_MODULE}.skills_registry",
        ),
        patch(
            f"{_ENGINE_MODULE}.CustomSkillsService",
        ),
        patch(
            "app.services.governance_service.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
        patch.object(
            __import__("app.services.governance_service", fromlist=["GovernanceService"]).GovernanceService,
            "log_event",
            _mock_gov_log_event,
        ),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        # Call execute_improvement with default actor (system)
        result = await engine.execute_improvement(action)

    assert result["status"] == "applied"
    # Should have produced an audit log entry
    execution_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_action_executed"]
    assert len(execution_logs) >= 1, f"Expected audit log for execution, got: {audit_log_calls}"
    log_entry = execution_logs[0]
    assert log_entry["user_id"] == "system:self-improvement-engine"
    assert log_entry["details"]["skill_name"] == "unused_skill"
    assert log_entry["details"]["action_type"] == "skill_demoted"


# ---------------------------------------------------------------------------
# Test 5: Admin-approved action produces audit log with admin user_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_approved_action_audit_log_has_admin_id():
    """When an admin approves an action, the audit log row uses the admin's user_id as actor."""
    audit_log_calls: list[dict] = []

    async def _mock_gov_log_event(
        self, user_id, action_type, resource_type, resource_id=None, details=None, ip_address=None,
    ):
        audit_log_calls.append({
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
        })

    action = {
        "id": "admin-action-1",
        "action_type": "skill_refined",
        "skill_name": "test_skill",
        "trigger_reason": "Low effectiveness",
        "status": "pending_approval",
        "metadata": {"effectiveness_score": 0.3},
        "effectiveness_before": 0.3,
    }

    mock_client = _mock_supabase_client()

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        resp.data = []
        return resp

    with (
        patch(
            f"{_ENGINE_MODULE}.get_service_client",
            return_value=mock_client,
        ),
        patch(
            f"{_ENGINE_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ENGINE_MODULE}.skills_registry",
        ),
        patch(
            f"{_ENGINE_MODULE}.CustomSkillsService",
        ),
        patch(
            "app.services.governance_service.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
        patch.object(
            __import__("app.services.governance_service", fromlist=["GovernanceService"]).GovernanceService,
            "log_event",
            _mock_gov_log_event,
        ),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        # Admin passes actor_id
        result = await engine.execute_improvement(action, actor_id="admin-user-55")

    assert result["status"] == "applied"
    execution_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_action_executed"]
    assert len(execution_logs) >= 1, f"Expected audit log, got: {audit_log_calls}"
    assert execution_logs[0]["user_id"] == "admin-user-55"


# ---------------------------------------------------------------------------
# Test 6: Rejected action does NOT produce an execution audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rejected_action_no_execution_audit_log():
    """Rejected action produces a rejection audit log but NOT an execution audit log."""
    action = _make_pending_action("action-reject-audit-1")
    audit_log_calls: list[dict] = []

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        if "fetch_action_for_approval" in (op_name or ""):
            resp.data = [action]
        else:
            resp.data = []
        return resp

    async def _mock_gov_log_event(
        self, user_id, action_type, resource_type, resource_id=None, details=None, ip_address=None,
    ):
        audit_log_calls.append({
            "user_id": user_id,
            "action_type": action_type,
        })

    app = _create_test_app(user_id="admin-user-reject")

    with (
        patch(
            f"{_ROUTER_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ROUTER_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.governance_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
        patch.object(
            __import__("app.services.governance_service", fromlist=["GovernanceService"]).GovernanceService,
            "log_event",
            _mock_gov_log_event,
        ),
    ):
        client = TestClient(app)
        resp = client.post("/self-improvement/actions/action-reject-audit-1/reject")

    assert resp.status_code == 200
    # Should have a rejection audit log
    rejection_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_action_rejected"]
    assert len(rejection_logs) >= 1, f"Expected rejection audit log, got: {audit_log_calls}"
    # Should NOT have an execution audit log
    execution_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_action_executed"]
    assert len(execution_logs) == 0, f"Should not have execution audit log on reject, got: {audit_log_calls}"


# ===========================================================================
# Circuit Breaker Tests (Task 2)
# ===========================================================================

# Shared helper for circuit breaker tests
def _make_engine_with_mocks(
    *,
    score_snapshots: list[list[dict]],
    settings_rows: list[dict] | None = None,
    audit_log_calls: list[dict] | None = None,
    settings_update_calls: list[dict] | None = None,
):
    """Build a SelfImprovementEngine with mocked DB responses for circuit breaker tests.

    Args:
        score_snapshots: List of snapshot groups. Each group is a list of
            {"skill_name": str, "effectiveness_score": float, "evaluated_at": str} dicts.
            Ordered newest-first (index 0 = most recent snapshot).
        settings_rows: Rows returned by self_improvement_settings.select().
        audit_log_calls: Mutable list to capture governance log_event calls.
        settings_update_calls: Mutable list to capture update_self_improvement_settings calls.

    Returns:
        Tuple of (patches context managers list, engine creation callable).
    """
    if audit_log_calls is None:
        audit_log_calls = []
    if settings_update_calls is None:
        settings_update_calls = []

    # Build flat score rows from snapshots (newest first)
    all_score_rows: list[dict] = []
    for group in score_snapshots:
        all_score_rows.extend(group)

    call_counter = {"settings_get": 0}

    async def _mock_engine_execute_async(query, op_name=""):
        resp = MagicMock()
        if "circuit_breaker_scores" in (op_name or ""):
            # Return all score rows for the circuit breaker query
            resp.data = all_score_rows
        elif "self_improvement_settings.get_all" in (op_name or ""):
            resp.data = settings_rows or []
        else:
            resp.data = []
        return resp

    async def _mock_settings_get():
        regressions = 0
        for row in (settings_rows or []):
            if row.get("key") == "circuit_breaker_consecutive_regressions":
                regressions = row.get("value", 0)
        return {
            "auto_execute_enabled": True,
            "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
            "circuit_breaker_consecutive_regressions": regressions,
        }

    async def _mock_settings_update(key, value, updated_by):
        settings_update_calls.append({"key": key, "value": value, "updated_by": updated_by})

    async def _mock_gov_log_event(
        self, user_id, action_type, resource_type, resource_id=None, details=None, ip_address=None,
    ):
        audit_log_calls.append({
            "user_id": user_id,
            "action_type": action_type,
            "details": details,
        })

    return (
        _mock_engine_execute_async,
        _mock_settings_get,
        _mock_settings_update,
        _mock_gov_log_event,
    )


# ---------------------------------------------------------------------------
# Test 7: Two consecutive >5% regressions trips the circuit breaker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_two_consecutive_regressions():
    """After two consecutive cycles where avg effectiveness regressed by >5%, auto_execute_enabled flips to false."""
    settings_update_calls: list[dict] = []
    audit_log_calls: list[dict] = []

    # Two snapshots: current avg=0.50, previous avg=0.60 => 10% regression
    # And the settings already show 1 consecutive regression (from last cycle)
    score_snapshots = [
        # Most recent (current cycle)
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.50, "evaluated_at": "2026-04-12T03:00:00Z"},
            {"skill_name": "skill_b", "effectiveness_score": 0.50, "evaluated_at": "2026-04-12T03:00:00Z"},
        ],
        # Previous cycle
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.60, "evaluated_at": "2026-04-11T03:00:00Z"},
            {"skill_name": "skill_b", "effectiveness_score": 0.60, "evaluated_at": "2026-04-11T03:00:00Z"},
        ],
    ]

    settings_rows = [
        {"key": "circuit_breaker_consecutive_regressions", "value": 1},
        {"key": "auto_execute_enabled", "value": True},
    ]

    (mock_exec, mock_settings_get, mock_settings_update, mock_gov_log) = _make_engine_with_mocks(
        score_snapshots=score_snapshots,
        settings_rows=settings_rows,
        audit_log_calls=audit_log_calls,
        settings_update_calls=settings_update_calls,
    )

    with (
        patch(f"{_ENGINE_MODULE}.get_service_client", return_value=_mock_supabase_client()),
        patch(f"{_ENGINE_MODULE}.execute_async", new_callable=AsyncMock, side_effect=mock_exec),
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        patch(f"{_ENGINE_MODULE}.get_self_improvement_settings", new_callable=AsyncMock, side_effect=mock_settings_get),
        patch("app.services.self_improvement_settings.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_settings.execute_async", new_callable=AsyncMock),
        patch(
            "app.services.self_improvement_engine.update_self_improvement_settings",
            new_callable=AsyncMock,
            side_effect=mock_settings_update,
        ),
        patch("app.services.governance_service.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.governance_service.execute_async", new_callable=AsyncMock, return_value=MagicMock(data=[])),
        patch.object(
            __import__("app.services.governance_service", fromlist=["GovernanceService"]).GovernanceService,
            "log_event",
            mock_gov_log,
        ),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        await engine._check_circuit_breaker()

    # auto_execute_enabled should have been flipped to False
    disable_calls = [c for c in settings_update_calls if c["key"] == "auto_execute_enabled" and c["value"] is False]
    assert len(disable_calls) >= 1, f"Circuit breaker should disable auto_execute, got updates: {settings_update_calls}"

    # Should produce a governance audit log
    cb_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_circuit_breaker"]
    assert len(cb_logs) >= 1, f"Circuit breaker should produce audit log, got: {audit_log_calls}"


# ---------------------------------------------------------------------------
# Test 8: Single cycle regression does NOT trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_regression_does_not_trip_circuit_breaker():
    """A single cycle regression does NOT trip the circuit breaker."""
    settings_update_calls: list[dict] = []

    # Two snapshots: current avg=0.50, previous avg=0.60 => 10% regression
    # But consecutive_regressions is 0 (this is the first regression)
    score_snapshots = [
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.50, "evaluated_at": "2026-04-12T03:00:00Z"},
            {"skill_name": "skill_b", "effectiveness_score": 0.50, "evaluated_at": "2026-04-12T03:00:00Z"},
        ],
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.60, "evaluated_at": "2026-04-11T03:00:00Z"},
            {"skill_name": "skill_b", "effectiveness_score": 0.60, "evaluated_at": "2026-04-11T03:00:00Z"},
        ],
    ]

    settings_rows = [
        {"key": "circuit_breaker_consecutive_regressions", "value": 0},
        {"key": "auto_execute_enabled", "value": True},
    ]

    (mock_exec, mock_settings_get, mock_settings_update, mock_gov_log) = _make_engine_with_mocks(
        score_snapshots=score_snapshots,
        settings_rows=settings_rows,
        settings_update_calls=settings_update_calls,
    )

    with (
        patch(f"{_ENGINE_MODULE}.get_service_client", return_value=_mock_supabase_client()),
        patch(f"{_ENGINE_MODULE}.execute_async", new_callable=AsyncMock, side_effect=mock_exec),
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        patch(f"{_ENGINE_MODULE}.get_self_improvement_settings", new_callable=AsyncMock, side_effect=mock_settings_get),
        patch("app.services.self_improvement_settings.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_settings.execute_async", new_callable=AsyncMock),
        patch(
            "app.services.self_improvement_engine.update_self_improvement_settings",
            new_callable=AsyncMock,
            side_effect=mock_settings_update,
        ),
        patch("app.services.governance_service.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.governance_service.execute_async", new_callable=AsyncMock, return_value=MagicMock(data=[])),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        await engine._check_circuit_breaker()

    # auto_execute_enabled should NOT have been flipped
    disable_calls = [c for c in settings_update_calls if c["key"] == "auto_execute_enabled" and c["value"] is False]
    assert len(disable_calls) == 0, f"Single regression should not trip circuit breaker, got: {settings_update_calls}"

    # But consecutive_regressions should have been incremented to 1
    regression_calls = [c for c in settings_update_calls if c["key"] == "circuit_breaker_consecutive_regressions"]
    assert len(regression_calls) >= 1, f"Should increment regression counter, got: {settings_update_calls}"
    assert regression_calls[0]["value"] == 1


# ---------------------------------------------------------------------------
# Test 9: Two consecutive <=5% regressions do NOT trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_small_regressions_do_not_trip_circuit_breaker():
    """Two consecutive cycles where regression is exactly 5% or less do NOT trip the circuit breaker."""
    settings_update_calls: list[dict] = []

    # Two snapshots: current avg=0.57, previous avg=0.60 => 3% regression (<=5%)
    score_snapshots = [
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.57, "evaluated_at": "2026-04-12T03:00:00Z"},
            {"skill_name": "skill_b", "effectiveness_score": 0.57, "evaluated_at": "2026-04-12T03:00:00Z"},
        ],
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.60, "evaluated_at": "2026-04-11T03:00:00Z"},
            {"skill_name": "skill_b", "effectiveness_score": 0.60, "evaluated_at": "2026-04-11T03:00:00Z"},
        ],
    ]

    # Even if previous cycle also had small regression, should not trip
    settings_rows = [
        {"key": "circuit_breaker_consecutive_regressions", "value": 1},
        {"key": "auto_execute_enabled", "value": True},
    ]

    (mock_exec, mock_settings_get, mock_settings_update, mock_gov_log) = _make_engine_with_mocks(
        score_snapshots=score_snapshots,
        settings_rows=settings_rows,
        settings_update_calls=settings_update_calls,
    )

    with (
        patch(f"{_ENGINE_MODULE}.get_service_client", return_value=_mock_supabase_client()),
        patch(f"{_ENGINE_MODULE}.execute_async", new_callable=AsyncMock, side_effect=mock_exec),
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        patch(f"{_ENGINE_MODULE}.get_self_improvement_settings", new_callable=AsyncMock, side_effect=mock_settings_get),
        patch("app.services.self_improvement_settings.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_settings.execute_async", new_callable=AsyncMock),
        patch(
            "app.services.self_improvement_engine.update_self_improvement_settings",
            new_callable=AsyncMock,
            side_effect=mock_settings_update,
        ),
        patch("app.services.governance_service.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.governance_service.execute_async", new_callable=AsyncMock, return_value=MagicMock(data=[])),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        await engine._check_circuit_breaker()

    # auto_execute_enabled should NOT be flipped (regression is <=5%)
    disable_calls = [c for c in settings_update_calls if c["key"] == "auto_execute_enabled" and c["value"] is False]
    assert len(disable_calls) == 0, f"Small regressions should not trip, got: {settings_update_calls}"

    # Consecutive regressions should be reset to 0 (not a significant regression)
    regression_calls = [c for c in settings_update_calls if c["key"] == "circuit_breaker_consecutive_regressions"]
    assert len(regression_calls) >= 1
    assert regression_calls[0]["value"] == 0, f"Should reset regression counter, got: {regression_calls}"


# ---------------------------------------------------------------------------
# Test 10: Circuit breaker trip produces governance audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_circuit_breaker_trip_produces_audit_log():
    """After circuit breaker trips, the engine logs a governance_audit_log entry."""
    audit_log_calls: list[dict] = []
    settings_update_calls: list[dict] = []

    score_snapshots = [
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.45, "evaluated_at": "2026-04-12T03:00:00Z"},
        ],
        [
            {"skill_name": "skill_a", "effectiveness_score": 0.55, "evaluated_at": "2026-04-11T03:00:00Z"},
        ],
    ]

    settings_rows = [
        {"key": "circuit_breaker_consecutive_regressions", "value": 1},
        {"key": "auto_execute_enabled", "value": True},
    ]

    (mock_exec, mock_settings_get, mock_settings_update, mock_gov_log) = _make_engine_with_mocks(
        score_snapshots=score_snapshots,
        settings_rows=settings_rows,
        audit_log_calls=audit_log_calls,
        settings_update_calls=settings_update_calls,
    )

    with (
        patch(f"{_ENGINE_MODULE}.get_service_client", return_value=_mock_supabase_client()),
        patch(f"{_ENGINE_MODULE}.execute_async", new_callable=AsyncMock, side_effect=mock_exec),
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        patch(f"{_ENGINE_MODULE}.get_self_improvement_settings", new_callable=AsyncMock, side_effect=mock_settings_get),
        patch("app.services.self_improvement_settings.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_settings.execute_async", new_callable=AsyncMock),
        patch(
            "app.services.self_improvement_engine.update_self_improvement_settings",
            new_callable=AsyncMock,
            side_effect=mock_settings_update,
        ),
        patch("app.services.governance_service.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.governance_service.execute_async", new_callable=AsyncMock, return_value=MagicMock(data=[])),
        patch.object(
            __import__("app.services.governance_service", fromlist=["GovernanceService"]).GovernanceService,
            "log_event",
            mock_gov_log,
        ),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        await engine._check_circuit_breaker()

    # Should produce a governance audit log for circuit breaker trip
    cb_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_circuit_breaker"]
    assert len(cb_logs) >= 1, f"Circuit breaker trip should produce audit log, got: {audit_log_calls}"
    assert cb_logs[0]["user_id"] == "system:circuit-breaker"
    assert "regression" in str(cb_logs[0]["details"]).lower() or "delta" in str(cb_logs[0]["details"]).lower()
