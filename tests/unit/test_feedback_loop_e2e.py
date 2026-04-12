# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integration tests for the feedback loop data path.

Proves that user feedback flows through to evaluate_skills and produces
a non-default positive_rate reflecting the actual signal.

Tests:
    1. feedback_changes_positive_rate — single negative feedback -> positive_rate = 0.0
    2. multiple_feedback_signals — 2 negative + 1 positive -> positive_rate ~ 0.333
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers -- Supabase stubs
# ---------------------------------------------------------------------------


def _stub_supabase_modules():
    """Ensure supabase and app.services.supabase are importable without real credentials."""
    if "supabase" not in sys.modules:
        fake_supabase = ModuleType("supabase")
        fake_supabase.Client = MagicMock  # type: ignore[attr-defined]
        sys.modules["supabase"] = fake_supabase

    fake_svc_mod = sys.modules.get("app.services.supabase")
    if fake_svc_mod is None:
        fake_svc_mod = ModuleType("app.services.supabase")
        sys.modules["app.services.supabase"] = fake_svc_mod
    fake_svc_mod.get_service_client = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

    fake_async_mod = sys.modules.get("app.services.supabase_async")
    if fake_async_mod is None:
        fake_async_mod = ModuleType("app.services.supabase_async")
        sys.modules["app.services.supabase_async"] = fake_async_mod
    fake_async_mod.execute_async = AsyncMock()  # type: ignore[attr-defined]

    # Stub request context
    fake_ctx = sys.modules.get("app.services.request_context")
    if fake_ctx is None:
        fake_ctx = ModuleType("app.services.request_context")
        sys.modules["app.services.request_context"] = fake_ctx
    fake_ctx.get_current_user_id = MagicMock(return_value="test-user-id")  # type: ignore[attr-defined]


def _make_interaction_row(
    *,
    agent_id: str = "test_agent",
    skill_name: str = "test_skill",
    feedback: str | None = None,
    task_completed: bool = True,
    was_escalated: bool = False,
    had_followup: bool = False,
    created_at: str | None = None,
) -> dict:
    """Build a mock interaction_logs row matching the keys _compute_metrics reads.

    Note: _group_by_skill reads ``skill_name`` and _compute_metrics reads
    ``feedback`` -- these are the dict keys the engine expects after
    _fetch_interaction_logs returns raw DB rows.
    """
    if created_at is None:
        created_at = datetime.now(tz=timezone.utc).isoformat()

    return {
        "id": f"mock-uuid-{hash(created_at) % 10000}",
        "agent_id": agent_id,
        "skill_name": skill_name,
        "skill_used": skill_name,
        "user_query": "test query",
        "agent_response_summary": "test response",
        "session_id": "test-session",
        "response_time_ms": 100,
        "feedback": feedback,
        "user_feedback": feedback,
        "task_completed": task_completed,
        "was_escalated": was_escalated,
        "had_followup": had_followup,
        "created_at": created_at,
        "metadata": {},
    }


def _make_response(data: list[dict]) -> MagicMock:
    """Create a mock response object with .data attribute."""
    resp = MagicMock()
    resp.data = data
    return resp


# ---------------------------------------------------------------------------
# Test 1: Single negative feedback -> positive_rate = 0.0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feedback_changes_positive_rate():
    """A single negative feedback produces positive_rate = 0.0 (not the 0.5 default).

    Steps:
        a. Create mock interaction row with feedback="negative"
        b. Mock _fetch_interaction_logs to return that row
        c. Call evaluate_skills(days=1)
        d. Assert positive_rate == 0.0 (one negative, zero positive, not 0.5 default)
    """
    _stub_supabase_modules()

    now = datetime.now(tz=timezone.utc)
    row = _make_interaction_row(
        feedback="negative",
        task_completed=True,
        created_at=(now - timedelta(hours=1)).isoformat(),
    )

    # Build the mock execute_async that returns our rows for fetch_logs
    # and empty for score insert
    async def mock_execute_async(query, *, op_name=""):
        if "fetch_logs" in op_name:
            # Current period returns our row; previous period returns empty
            return _make_response([row])
        # For score inserts and other operations, return empty
        return _make_response([])

    with (
        patch(
            "app.services.self_improvement_engine.get_service_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.self_improvement_engine.execute_async",
            side_effect=mock_execute_async,
        ),
        patch(
            "app.services.self_improvement_engine.CustomSkillsService",
            return_value=MagicMock(),
        ),
    ):
        # Lazy import to avoid Supabase init at module import time
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()

        # _fetch_interaction_logs is called twice (current + previous period)
        # We need different data for each call: current has our row, previous is empty
        call_count = 0

        async def mock_execute_with_period(query, *, op_name=""):
            nonlocal call_count
            if "fetch_logs" in op_name:
                call_count += 1
                if call_count == 1:
                    # Current period -- has our feedback row
                    return _make_response([row])
                # Previous period -- empty
                return _make_response([])
            # Score insert -- just succeed
            return _make_response([])

        with patch(
            "app.services.self_improvement_engine.execute_async",
            side_effect=mock_execute_with_period,
        ):
            scores = await engine.evaluate_skills(days=1)

    # Should have one score for our test skill
    assert len(scores) >= 1, f"Expected at least 1 score, got {len(scores)}"

    test_score = next(
        (s for s in scores if s["skill_name"] == "test_skill"),
        None,
    )
    assert test_score is not None, (
        f"No score found for 'test_skill'. Available: {[s['skill_name'] for s in scores]}"
    )

    # With 1 negative feedback and 0 positive: positive_rate = 0/1 = 0.0
    # The default (no feedback at all) would be 0.5
    assert test_score["positive_rate"] == 0.0, (
        f"Expected positive_rate=0.0 (1 negative), got {test_score['positive_rate']}"
    )

    # Verify effectiveness_score is NOT the default (which would be
    # 0.35*0.5 + 0.30*completion + 0.20*(1-esc) + 0.15*(1-retry) if no feedback)
    # With positive_rate=0.0, task_completed=True, no escalation, no followup:
    # effectiveness = 0.35*0.0 + 0.30*1.0 + 0.20*1.0 + 0.15*1.0 = 0.65
    assert test_score["effectiveness_score"] == pytest.approx(0.65, abs=0.01), (
        f"Expected effectiveness ~0.65, got {test_score['effectiveness_score']}"
    )


# ---------------------------------------------------------------------------
# Test 2: Multiple feedback signals -> positive_rate ~ 0.333
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_feedback_signals():
    """2 negative + 1 positive feedback -> positive_rate ~ 0.333.

    Steps:
        a. Create 3 interaction rows for same agent/skill: 2 negative, 1 positive
        b. Mock _fetch_interaction_logs to return all 3
        c. Call evaluate_skills(days=1)
        d. Assert positive_rate ~ 1/3 = 0.333
    """
    _stub_supabase_modules()

    now = datetime.now(tz=timezone.utc)
    rows = [
        _make_interaction_row(
            feedback="negative",
            task_completed=True,
            created_at=(now - timedelta(hours=3)).isoformat(),
        ),
        _make_interaction_row(
            feedback="negative",
            task_completed=True,
            created_at=(now - timedelta(hours=2)).isoformat(),
        ),
        _make_interaction_row(
            feedback="positive",
            task_completed=True,
            created_at=(now - timedelta(hours=1)).isoformat(),
        ),
    ]

    call_count = 0

    async def mock_execute_async(query, *, op_name=""):
        nonlocal call_count
        if "fetch_logs" in op_name:
            call_count += 1
            if call_count == 1:
                # Current period -- has all 3 rows
                return _make_response(rows)
            # Previous period -- empty
            return _make_response([])
        # Score insert -- just succeed
        return _make_response([])

    with (
        patch(
            "app.services.self_improvement_engine.get_service_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.self_improvement_engine.execute_async",
            side_effect=mock_execute_async,
        ),
        patch(
            "app.services.self_improvement_engine.CustomSkillsService",
            return_value=MagicMock(),
        ),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        scores = await engine.evaluate_skills(days=1)

    assert len(scores) >= 1, f"Expected at least 1 score, got {len(scores)}"

    test_score = next(
        (s for s in scores if s["skill_name"] == "test_skill"),
        None,
    )
    assert test_score is not None, (
        f"No score found for 'test_skill'. Available: {[s['skill_name'] for s in scores]}"
    )

    # With 2 negative + 1 positive: positive_rate = 1/3 ~ 0.3333
    assert test_score["positive_rate"] == pytest.approx(0.3333, abs=0.01), (
        f"Expected positive_rate ~0.333, got {test_score['positive_rate']}"
    )

    # Verify total_uses = 3
    assert test_score["total_uses"] == 3, (
        f"Expected total_uses=3, got {test_score['total_uses']}"
    )

    # Effectiveness with positive_rate=0.333, completion=1.0, escalation=0, retry=0:
    # 0.35*0.333 + 0.30*1.0 + 0.20*1.0 + 0.15*1.0 = 0.1167 + 0.30 + 0.20 + 0.15 = 0.7667
    assert test_score["effectiveness_score"] == pytest.approx(0.7667, abs=0.01), (
        f"Expected effectiveness ~0.767, got {test_score['effectiveness_score']}"
    )
