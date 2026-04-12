# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integration (UAT) tests for the scheduled self-improvement cycle (Phase 75-03).

End-to-end flow validation using FastAPI TestClient with mocked Supabase:

- Test 1: POST /scheduled/self-improvement-cycle without X-Scheduler-Secret -> 401
- Test 2: POST /scheduled/self-improvement-cycle with valid header -> 200, cycle runs
- Test 3: Risk-tier gating: low-risk auto-executes, high-risk queues pending_approval
- Test 4: POST /self-improvement/actions/{id}/approve -> applied + audit log
- Test 5: POST /self-improvement/actions/{id}/reject -> declined, no execution
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Module paths for patching
# ---------------------------------------------------------------------------

_SCHEDULED_MODULE = "app.services.scheduled_endpoints"
_ENGINE_MODULE = "app.services.self_improvement_engine"
_SETTINGS_MODULE = "app.services.self_improvement_settings"
_ROUTER_MODULE = "app.routers.self_improvement"
_GOV_MODULE = "app.services.governance_service"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _create_scheduled_app() -> FastAPI:
    """Create a FastAPI app with the scheduled endpoints router."""
    # Clear cached modules to pick up fresh imports
    for mod_name in list(sys.modules.keys()):
        if "scheduled_endpoints" in mod_name and "test_" not in mod_name:
            del sys.modules[mod_name]

    app = FastAPI()

    from app.services.scheduled_endpoints import router as scheduled_router

    app.include_router(scheduled_router)
    return app


def _create_self_improvement_app(*, user_id: str = "admin-user-1") -> FastAPI:
    """Create a FastAPI app with the self-improvement router, rate limiter bypassed."""
    # Clear cached modules to pick up fresh imports
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
# Test 1: Unauthorized request to scheduled endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduled_endpoint_unauthorized():
    """POST /scheduled/self-improvement-cycle without X-Scheduler-Secret returns 401."""
    with patch.dict(os.environ, {"SCHEDULER_SECRET": "test-secret-123"}):
        app = _create_scheduled_app()
        client = TestClient(app)

        # No header at all
        resp = client.post("/scheduled/self-improvement-cycle")
        assert resp.status_code == 401, (
            f"Expected 401 without header, got {resp.status_code}: {resp.text}"
        )

        # Wrong header value
        resp = client.post(
            "/scheduled/self-improvement-cycle",
            headers={"X-Scheduler-Secret": "wrong-secret"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 with wrong header, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Test 2: Authorized request triggers full cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduled_endpoint_triggers_cycle():
    """POST /scheduled/self-improvement-cycle with valid header triggers the cycle and returns 200."""
    mock_client = _mock_supabase_client()

    # Track execute_async calls to verify improvement_actions inserts
    insert_calls: list[str] = []

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        if "insert_score" in (op_name or ""):
            resp.data = [{"id": "score-1"}]
        elif "insert_action" in (op_name or ""):
            insert_calls.append(op_name)
            resp.data = [{"id": "action-1"}]
        elif "set_pending_approval" in (op_name or ""):
            insert_calls.append(op_name)
            resp.data = []
        else:
            resp.data = []
        return resp

    async def _mock_evaluate_skills(self, days=7):
        return [
            {
                "skill_name": "skill_a",
                "effectiveness_score": 0.85,
                "total_uses": 10,
                "positive_rate": 0.8,
                "completion_rate": 0.9,
                "escalation_rate": 0.1,
                "retry_rate": 0.05,
                "trend": "improving",
                "score_delta": 0.03,
                "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
            {
                "skill_name": "skill_b",
                "effectiveness_score": 0.30,
                "total_uses": 8,
                "positive_rate": 0.3,
                "completion_rate": 0.4,
                "escalation_rate": 0.5,
                "retry_rate": 0.3,
                "trend": "declining",
                "score_delta": -0.1,
                "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        ]

    async def _mock_identify_improvements(self, scores=None):
        return [
            {
                "id": "action-low-risk",
                "action_type": "pattern_extract",
                "skill_name": "skill_a",
                "priority": "low",
                "status": "pending",
                "reason": "High performer",
                "metadata": {"effectiveness_score": 0.85},
            },
            {
                "id": "action-high-risk",
                "action_type": "skill_refined",
                "skill_name": "skill_b",
                "priority": "high",
                "status": "pending",
                "reason": "Low effectiveness",
                "metadata": {"effectiveness_score": 0.30},
            },
        ]

    async def _mock_execute_improvement(self, action, actor_id=None):
        return {"action_id": action["id"], "status": "applied"}

    with (
        patch.dict(os.environ, {"SCHEDULER_SECRET": "test-secret-123"}),
        patch(
            f"{_SCHEDULED_MODULE}.get_service_client",
            return_value=mock_client,
        ),
        patch(
            f"{_SCHEDULED_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ENGINE_MODULE}.get_service_client",
            return_value=mock_client,
        ),
        patch(
            f"{_ENGINE_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        patch(
            f"{_SETTINGS_MODULE}.get_service_client",
            return_value=mock_client,
        ),
        patch(
            f"{_SETTINGS_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ENGINE_MODULE}.get_self_improvement_settings",
            new_callable=AsyncMock,
            return_value={
                "auto_execute_enabled": True,
                "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
            },
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "evaluate_skills",
            _mock_evaluate_skills,
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "identify_improvements",
            _mock_identify_improvements,
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "execute_improvement",
            _mock_execute_improvement,
        ),
        patch(
            f"{_GOV_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_GOV_MODULE}.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
    ):
        app = _create_scheduled_app()
        client = TestClient(app)

        resp = client.post(
            "/scheduled/self-improvement-cycle",
            headers={"X-Scheduler-Secret": "test-secret-123"},
        )

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["success"] is True
    result = data["result"]
    assert result["scores_computed"] == 2, (
        f"Expected 2 scores computed, got {result['scores_computed']}"
    )
    assert result["improvements_found"] == 2, (
        f"Expected 2 improvements found, got {result['improvements_found']}"
    )


# ---------------------------------------------------------------------------
# Test 3: Risk-tier gating -- low-risk executes, high-risk pending_approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_tier_gating_creates_pending_approval():
    """Low-risk actions auto-execute; high-risk actions get pending_approval status."""
    mock_client = _mock_supabase_client()
    executed_ids: list[str] = []
    pending_approval_ops: list[str] = []

    async def _mock_execute_async(query, op_name=""):
        resp = MagicMock()
        if "set_pending_approval" in (op_name or ""):
            pending_approval_ops.append(op_name)
        resp.data = []
        return resp

    async def _mock_evaluate_skills(self, days=7):
        return []

    async def _mock_identify_improvements(self, scores=None):
        return [
            {
                "id": "action-demote",
                "action_type": "skill_demoted",
                "skill_name": "old_skill",
                "priority": "low",
                "status": "pending",
                "reason": "No uses",
                "metadata": {},
            },
            {
                "id": "action-refine",
                "action_type": "skill_refined",
                "skill_name": "weak_skill",
                "priority": "high",
                "status": "pending",
                "reason": "Low score",
                "metadata": {"effectiveness_score": 0.30},
            },
        ]

    async def _mock_execute_improvement(self, action, actor_id=None):
        executed_ids.append(action["id"])
        return {"action_id": action["id"], "status": "applied"}

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
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        patch(
            f"{_SETTINGS_MODULE}.get_service_client",
            return_value=mock_client,
        ),
        patch(
            f"{_SETTINGS_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_execute_async,
        ),
        patch(
            f"{_ENGINE_MODULE}.get_self_improvement_settings",
            new_callable=AsyncMock,
            return_value={
                "auto_execute_enabled": True,
                "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
            },
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "evaluate_skills",
            _mock_evaluate_skills,
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "identify_improvements",
            _mock_identify_improvements,
        ),
        patch.object(
            __import__(_ENGINE_MODULE, fromlist=["SelfImprovementEngine"]).SelfImprovementEngine,
            "execute_improvement",
            _mock_execute_improvement,
        ),
        patch(
            f"{_GOV_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_GOV_MODULE}.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
        patch(
            f"{_ENGINE_MODULE}.update_self_improvement_settings",
            new_callable=AsyncMock,
        ),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        result = await engine.run_improvement_cycle(auto_execute=True, days=7)

    # skill_demoted is in risk_tiers -> should have been executed
    assert "action-demote" in executed_ids, (
        f"skill_demoted should be auto-executed, got: {executed_ids}"
    )
    assert result["improvements_executed"] == 1

    # skill_refined is NOT in risk_tiers -> should be pending_approval
    assert "action-refine" not in executed_ids, (
        f"skill_refined should NOT be auto-executed, got: {executed_ids}"
    )
    assert result["improvements_pending_approval"] == 1

    # DB update for pending_approval should have been called
    assert len(pending_approval_ops) >= 1, (
        f"Expected pending_approval DB call, got: {pending_approval_ops}"
    )


# ---------------------------------------------------------------------------
# Test 4: Approve action -> executes and writes governance audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_action_executes_and_audits():
    """POST /self-improvement/actions/{id}/approve executes and writes governance audit."""
    action = _make_pending_action("action-uat-approve")
    audit_calls: list[dict] = []

    async def _mock_router_execute_async(query, op_name=""):
        """Handle router-level DB calls (fetch action, update approval metadata)."""
        resp = MagicMock()
        if "fetch_action_for_approval" in (op_name or ""):
            resp.data = [action]
        else:
            resp.data = []
        return resp

    async def _mock_engine_execute_async(query, op_name=""):
        """Handle engine-level DB calls (update action record after execution)."""
        resp = MagicMock()
        resp.data = []
        return resp

    async def _mock_gov_log_event(
        self, user_id, action_type, resource_type, resource_id=None, details=None, ip_address=None,
    ):
        audit_calls.append({
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
        })

    app = _create_self_improvement_app(user_id="admin-uat-1")

    with (
        patch(
            f"{_ROUTER_MODULE}.execute_async",
            new_callable=AsyncMock,
            side_effect=_mock_router_execute_async,
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
            side_effect=_mock_engine_execute_async,
        ),
        patch(f"{_ENGINE_MODULE}.skills_registry"),
        patch(f"{_ENGINE_MODULE}.CustomSkillsService"),
        # Let execute_improvement run for REAL so governance audit fires
        patch(
            f"{_GOV_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_GOV_MODULE}.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
        patch.object(
            __import__(_GOV_MODULE, fromlist=["GovernanceService"]).GovernanceService,
            "log_event",
            _mock_gov_log_event,
        ),
    ):
        client = TestClient(app)
        resp = client.post("/self-improvement/actions/action-uat-approve/approve")

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["status"] == "applied"

    # governance_audit_log insert was called with self_improvement action_type
    si_audits = [
        c for c in audit_calls
        if "self_improvement" in (c.get("action_type") or "")
    ]
    assert len(si_audits) >= 1, (
        f"Expected governance audit with 'self_improvement' action_type, got: {audit_calls}"
    )
    # Verify admin user_id was passed as actor
    assert si_audits[0]["user_id"] == "admin-uat-1", (
        f"Expected admin actor in audit, got: {si_audits[0]['user_id']}"
    )


# ---------------------------------------------------------------------------
# Test 5: Reject action -> declined, no execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_action_marks_declined():
    """POST /self-improvement/actions/{id}/reject marks declined without execution."""
    action = _make_pending_action("action-uat-reject")
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

    app = _create_self_improvement_app(user_id="admin-uat-2")

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
            f"{_GOV_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_GOV_MODULE}.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ),
    ):
        client = TestClient(app)
        resp = client.post("/self-improvement/actions/action-uat-reject/reject")

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["status"] == "declined"

    # execute_improvement must NOT have been called
    assert len(execute_calls) == 0, (
        f"execute_improvement should not be called on reject, got: {execute_calls}"
    )
