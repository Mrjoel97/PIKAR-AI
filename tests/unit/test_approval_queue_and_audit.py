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

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        "status": "pending_approval",
        "effectiveness_before": 0.35,
        "effectiveness_after": None,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "approved_by": None,
        "approved_at": None,
        "details": {},
        "metadata": {"effectiveness_score": 0.35},
    }


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

    from fastapi.testclient import TestClient

    with (
        patch(
            f"{_ROUTER_MODULE}.get_current_user_id",
            return_value="admin-user-1",
        ),
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
        from app.routers.self_improvement import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
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

    from fastapi.testclient import TestClient

    with (
        patch(
            f"{_ROUTER_MODULE}.get_current_user_id",
            return_value="admin-user-2",
        ),
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
        from app.routers.self_improvement import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
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

    from fastapi.testclient import TestClient

    with (
        patch(
            f"{_ROUTER_MODULE}.get_current_user_id",
            return_value="admin-user-3",
        ),
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
        from app.routers.self_improvement import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
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

    from fastapi.testclient import TestClient

    with (
        patch(
            f"{_ROUTER_MODULE}.get_current_user_id",
            return_value="admin-user-reject",
        ),
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
        from app.routers.self_improvement import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/self-improvement/actions/action-reject-audit-1/reject")

    assert resp.status_code == 200
    # Should have a rejection audit log
    rejection_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_action_rejected"]
    assert len(rejection_logs) >= 1, f"Expected rejection audit log, got: {audit_log_calls}"
    # Should NOT have an execution audit log
    execution_logs = [c for c in audit_log_calls if c["action_type"] == "self_improvement_action_executed"]
    assert len(execution_logs) == 0, f"Should not have execution audit log on reject, got: {audit_log_calls}"
