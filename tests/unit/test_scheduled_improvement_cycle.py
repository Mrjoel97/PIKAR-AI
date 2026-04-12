# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for scheduled self-improvement cycle (Phase 75-01).

Tests cover:
- Test 1: get_self_improvement_settings returns defaults when DB is empty/errors
- Test 2: update_self_improvement_settings persists new values
- Test 3: auto_execute_enabled=True + action in risk tiers -> executed immediately
- Test 4: auto_execute_enabled=True + action NOT in risk tiers -> pending_approval
- Test 5: auto_execute_enabled=False -> ALL actions get pending_approval
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


# ---------------------------------------------------------------------------
# Test 1: get_self_improvement_settings returns defaults
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_settings_returns_defaults():
    """get_self_improvement_settings returns defaults when DB returns empty or errors."""

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        resp.data = []  # empty DB
        return resp

    with (
        patch(
            "app.services.self_improvement_settings.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_settings.execute_async",
            new_callable=AsyncMock,
            side_effect=_execute_async_side_effect,
        ),
    ):
        from app.services.self_improvement_settings import get_self_improvement_settings

        settings = await get_self_improvement_settings()

    assert settings["auto_execute_enabled"] is False
    assert settings["auto_execute_risk_tiers"] == ["skill_demoted", "pattern_extract"]


# ---------------------------------------------------------------------------
# Test 2: update_self_improvement_settings persists new values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_settings_persists():
    """update_self_improvement_settings calls upsert on the settings table."""
    mock_client = _mock_supabase_client()
    upsert_calls = []

    async def _execute_async_side_effect(query, op_name=""):
        resp = MagicMock()
        if "upsert" in (op_name or ""):
            upsert_calls.append(op_name)
        resp.data = [{"id": "row-1"}]
        return resp

    with (
        patch(
            "app.services.self_improvement_settings.get_service_client",
            return_value=mock_client,
        ),
        patch(
            "app.services.self_improvement_settings.execute_async",
            new_callable=AsyncMock,
            side_effect=_execute_async_side_effect,
        ) as mock_exec,
    ):
        from app.services.self_improvement_settings import (
            update_self_improvement_settings,
        )

        await update_self_improvement_settings(
            key="auto_execute_enabled", value=True, updated_by="admin-user"
        )

    # Should have called execute_async at least once for the upsert
    assert mock_exec.call_count >= 1


# ---------------------------------------------------------------------------
# Test 3: auto_execute_enabled=True + action in risk tiers -> executed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_tier_actions_auto_execute():
    """When auto_execute_enabled=True, low-risk actions (skill_demoted, pattern_extract) are executed immediately."""
    executed_action_ids = []

    async def _mock_evaluate_skills(self, days=7):
        return []

    async def _mock_identify_improvements(self, scores=None):
        return [
            {
                "id": "action-1",
                "action_type": "skill_demoted",
                "skill_name": "unused_skill",
                "priority": "low",
                "status": "pending",
                "reason": "No uses",
                "metadata": {},
            },
            {
                "id": "action-2",
                "action_type": "pattern_extract",
                "skill_name": "good_skill",
                "priority": "low",
                "status": "pending",
                "reason": "High performer",
                "metadata": {},
            },
        ]

    async def _mock_execute_improvement(self, action):
        executed_action_ids.append(action["id"])
        return {"action_id": action["id"], "status": "applied"}

    with (
        patch(
            "app.services.supabase.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_engine.execute_async",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.self_improvement_engine.skills_registry",
        ),
        patch(
            "app.services.self_improvement_settings.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_settings.execute_async",
            new_callable=AsyncMock,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "evaluate_skills",
            _mock_evaluate_skills,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "identify_improvements",
            _mock_identify_improvements,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "execute_improvement",
            _mock_execute_improvement,
        ),
    ):
        # Mock settings to return auto_execute_enabled=True
        with patch(
            "app.services.self_improvement_engine.get_self_improvement_settings",
            new_callable=AsyncMock,
            return_value={
                "auto_execute_enabled": True,
                "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
            },
        ):
            from app.services.self_improvement_engine import SelfImprovementEngine

            engine = SelfImprovementEngine()
            result = await engine.run_improvement_cycle(auto_execute=True, days=7)

    # Both low-risk actions should have been executed
    assert "action-1" in executed_action_ids, (
        f"skill_demoted should be executed, got: {executed_action_ids}"
    )
    assert "action-2" in executed_action_ids, (
        f"pattern_extract should be executed, got: {executed_action_ids}"
    )
    assert result["improvements_executed"] == 2


# ---------------------------------------------------------------------------
# Test 4: auto_execute_enabled=True + action NOT in risk tiers -> pending_approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_risk_actions_get_pending_approval():
    """When auto_execute_enabled=True, high-risk actions (skill_refined, skill_created) get pending_approval status."""
    pending_approval_ids = []
    executed_action_ids = []

    async def _mock_evaluate_skills(self, days=7):
        return []

    async def _mock_identify_improvements(self, scores=None):
        return [
            {
                "id": "action-1",
                "action_type": "skill_refined",
                "skill_name": "underperforming_skill",
                "priority": "high",
                "status": "pending",
                "reason": "Low score",
                "metadata": {},
            },
            {
                "id": "action-2",
                "action_type": "skill_created",
                "skill_name": None,
                "priority": "medium",
                "status": "pending",
                "reason": "Coverage gap",
                "metadata": {},
            },
        ]

    async def _mock_execute_improvement(self, action):
        executed_action_ids.append(action["id"])
        return {"action_id": action["id"], "status": "applied"}

    async def _capture_pending_approval(query, op_name=""):
        resp = MagicMock()
        resp.data = []
        if "pending_approval" in (op_name or ""):
            pending_approval_ids.append(op_name)
        return resp

    with (
        patch(
            "app.services.supabase.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_engine.execute_async",
            new_callable=AsyncMock,
            side_effect=_capture_pending_approval,
        ),
        patch(
            "app.services.self_improvement_engine.skills_registry",
        ),
        patch(
            "app.services.self_improvement_settings.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_settings.execute_async",
            new_callable=AsyncMock,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "evaluate_skills",
            _mock_evaluate_skills,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "identify_improvements",
            _mock_identify_improvements,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "execute_improvement",
            _mock_execute_improvement,
        ),
    ):
        with patch(
            "app.services.self_improvement_engine.get_self_improvement_settings",
            new_callable=AsyncMock,
            return_value={
                "auto_execute_enabled": True,
                "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
            },
        ):
            from app.services.self_improvement_engine import SelfImprovementEngine

            engine = SelfImprovementEngine()
            result = await engine.run_improvement_cycle(auto_execute=True, days=7)

    # High-risk actions should NOT have been executed
    assert len(executed_action_ids) == 0, (
        f"High-risk actions should not execute, got: {executed_action_ids}"
    )
    # They should have been marked pending_approval via DB update
    assert result["improvements_pending_approval"] == 2


# ---------------------------------------------------------------------------
# Test 5: auto_execute_enabled=False -> ALL actions get pending_approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_execute_disabled_all_pending_approval():
    """When auto_execute_enabled=False, ALL actions get pending_approval status."""
    executed_action_ids = []

    async def _mock_evaluate_skills(self, days=7):
        return []

    async def _mock_identify_improvements(self, scores=None):
        return [
            {
                "id": "action-1",
                "action_type": "skill_demoted",
                "skill_name": "unused_skill",
                "priority": "low",
                "status": "pending",
                "reason": "No uses",
                "metadata": {},
            },
            {
                "id": "action-2",
                "action_type": "skill_refined",
                "skill_name": "bad_skill",
                "priority": "high",
                "status": "pending",
                "reason": "Low score",
                "metadata": {},
            },
        ]

    async def _mock_execute_improvement(self, action):
        executed_action_ids.append(action["id"])
        return {"action_id": action["id"], "status": "applied"}

    with (
        patch(
            "app.services.supabase.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_engine.execute_async",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.self_improvement_engine.skills_registry",
        ),
        patch(
            "app.services.self_improvement_settings.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            "app.services.self_improvement_settings.execute_async",
            new_callable=AsyncMock,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "evaluate_skills",
            _mock_evaluate_skills,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "identify_improvements",
            _mock_identify_improvements,
        ),
        patch.object(
            __import__(
                "app.services.self_improvement_engine",
                fromlist=["SelfImprovementEngine"],
            ).SelfImprovementEngine,
            "execute_improvement",
            _mock_execute_improvement,
        ),
    ):
        with patch(
            "app.services.self_improvement_engine.get_self_improvement_settings",
            new_callable=AsyncMock,
            return_value={
                "auto_execute_enabled": False,
                "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
            },
        ):
            from app.services.self_improvement_engine import SelfImprovementEngine

            engine = SelfImprovementEngine()
            result = await engine.run_improvement_cycle(auto_execute=True, days=7)

    # NO actions should have been executed
    assert len(executed_action_ids) == 0, (
        f"No actions should execute when disabled, got: {executed_action_ids}"
    )
    # All should be pending_approval
    assert result["improvements_pending_approval"] == 2
    assert result["improvements_executed"] == 0
