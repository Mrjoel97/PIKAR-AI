# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for SelfImprovementEngine async fixes and telemetry.

Tests cover:
- FIX-01: _generate_with_gemini uses async Gemini client (client.aio.models)
- FIX-02: identify_improvements uses `await bus.emit()` (no run_until_complete)
- FIX-05: run_improvement_cycle returns cycle_duration_ms, gemini_call_latency_ms,
          and actions_executed_total metrics
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers -- mock Supabase + skills_registry to isolate engine construction
# ---------------------------------------------------------------------------

def _mock_supabase_client() -> MagicMock:
    """Return a MagicMock that fakes Supabase table().select()...execute_async."""
    client = MagicMock()
    chain = MagicMock()
    chain.return_value = chain  # chaining: .select(), .eq(), .gte(), etc.
    chain.data = []
    client.table.return_value = chain
    return client


def _empty_async_resp(*_args, **_kwargs):
    """Async helper returning empty data for execute_async."""
    resp = MagicMock()
    resp.data = []
    return resp


def _make_genai_mock(response_text: str = "Generated text") -> tuple[MagicMock, MagicMock]:
    """Build a mock genai module + client instance with async generate_content.

    Returns (mock_genai_module, mock_client_instance).
    """
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_content = AsyncMock(
        return_value=mock_response,
    )
    # Sync path should NOT be called
    mock_client_instance.models.generate_content = MagicMock(
        side_effect=AssertionError("sync path called -- should use async"),
    )

    mock_genai_module = MagicMock()
    mock_genai_module.Client.return_value = mock_client_instance
    return mock_genai_module, mock_client_instance


@contextmanager
def _patch_genai(mock_genai_module: MagicMock):
    """Temporarily replace google.genai in sys.modules AND the google package.

    The conftest creates ``google.genai`` as a bare ``types.ModuleType`` on the
    ``google`` package.  ``import google.genai as genai`` resolves via the
    package attribute, so we must patch both ``sys.modules["google.genai"]``
    AND ``google.genai`` (the attribute on the google package).
    """
    google_pkg = sys.modules.get("google")
    saved_mod = sys.modules.get("google.genai")
    saved_attr = getattr(google_pkg, "genai", None) if google_pkg else None

    sys.modules["google.genai"] = mock_genai_module
    if google_pkg is not None:
        google_pkg.genai = mock_genai_module  # type: ignore[attr-defined]

    try:
        yield
    finally:
        if saved_mod is not None:
            sys.modules["google.genai"] = saved_mod
        else:
            sys.modules.pop("google.genai", None)

        if google_pkg is not None:
            if saved_attr is not None:
                google_pkg.genai = saved_attr  # type: ignore[attr-defined]
            elif hasattr(google_pkg, "genai"):
                delattr(google_pkg, "genai")


def test_group_by_skill_accepts_live_interaction_log_shape():
    """Live interaction_logs rows use skill_used rather than skill_name."""
    from app.services.self_improvement_engine import SelfImprovementEngine

    grouped = SelfImprovementEngine._group_by_skill(
        [
            {"skill_used": "sales_outreach", "user_id": "u1"},
            {"skill_name": "legacy_skill", "user_id": "u2"},
        ]
    )

    assert list(grouped.keys()) == ["sales_outreach", "legacy_skill"]


def test_compute_metrics_accepts_live_feedback_field():
    """Live interaction_logs rows store feedback in user_feedback."""
    from app.services.self_improvement_engine import SelfImprovementEngine

    metrics = SelfImprovementEngine._compute_metrics(
        [
            {
                "user_id": "u1",
                "user_feedback": "positive",
                "task_completed": True,
                "was_escalated": False,
                "had_followup": False,
            },
            {
                "user_id": "u2",
                "user_feedback": "negative",
                "task_completed": False,
                "was_escalated": True,
                "had_followup": True,
            },
        ]
    )

    assert metrics["unique_users"] == 2
    assert metrics["positive_rate"] == 0.5
    assert metrics["completion_rate"] == 0.5
    assert metrics["escalation_rate"] == 0.5
    assert metrics["retry_rate"] == 0.5


def test_serialize_action_for_storage_maps_runtime_action_to_live_columns():
    """Improvement actions should persist trigger_reason/details for production."""
    from app.services.self_improvement_engine import SelfImprovementEngine

    action = SelfImprovementEngine._make_action(
        skill_name="sales_outreach",
        action_type="skill_refined",
        reason="Low effectiveness score",
        priority="high",
        metadata={"effectiveness_score": 0.31},
    )

    serialized = SelfImprovementEngine._serialize_action_for_storage(action)

    assert serialized["trigger_reason"] == "Low effectiveness score"
    assert serialized["details"]["priority"] == "high"
    assert serialized["details"]["metadata"]["effectiveness_score"] == 0.31


# ---------------------------------------------------------------------------
# Test 1: _generate_with_gemini uses async path (client.aio.models)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_with_gemini_uses_async_client():
    """FIX-01: _generate_with_gemini must await client.aio.models.generate_content."""
    mock_genai_module, mock_client = _make_genai_mock("Generated text")

    with (
        patch("app.services.self_improvement_engine.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.CustomSkillsService"),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        _patch_genai(mock_genai_module),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        result = await engine._generate_with_gemini("test prompt")

    assert result == "Generated text"
    mock_client.aio.models.generate_content.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2: identify_improvements uses `await bus.emit()` (no run_until_complete)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_identify_improvements_awaits_bus_emit():
    """FIX-02: identify_improvements must call `await bus.emit(...)` directly."""
    mock_bus = MagicMock()
    mock_bus.emit = AsyncMock(return_value={"success": True})

    mock_gap_resp = MagicMock()
    mock_gap_resp.data = [
        {
            "id": "gap-1",
            "category": "finance",
            "description": "Missing cash flow analysis",
            "user_query": "How is my cash flow?",
            "agent_id": "FIN",
            "resolved": False,
            "occurrence_count": 3,
        },
    ]

    async def _execute_async_side_effect(query, op_name=""):
        """Route different DB calls to appropriate mock responses."""
        if "coverage_gaps" in op_name or "fetch_gaps" in op_name:
            return mock_gap_resp
        resp = MagicMock()
        resp.data = []
        return resp

    with (
        patch("app.services.self_improvement_engine.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.CustomSkillsService"),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect),
        patch("app.services.research_event_bus.get_event_bus", return_value=mock_bus),
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
    ):
        mock_registry.list_names.return_value = []

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        await engine.identify_improvements(scores=[])

    # The key assertion: bus.emit should have been AWAITED (not called via run_until_complete)
    mock_bus.emit.assert_awaited()


# ---------------------------------------------------------------------------
# Test 3: run_improvement_cycle returns telemetry metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_improvement_cycle_returns_telemetry_metrics():
    """FIX-05: run_improvement_cycle returns cycle_duration_ms, gemini_call_latency_ms, actions_executed_total."""
    with (
        patch("app.services.self_improvement_engine.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.CustomSkillsService"),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
    ):
        mock_registry.list_names.return_value = []

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        summary = await engine.run_improvement_cycle(days=7, auto_execute=False)

    assert "cycle_duration_ms" in summary
    assert "gemini_call_latency_ms" in summary
    assert "actions_executed_total" in summary

    assert isinstance(summary["cycle_duration_ms"], float)
    assert summary["cycle_duration_ms"] > 0
    assert isinstance(summary["gemini_call_latency_ms"], float)
    assert summary["gemini_call_latency_ms"] >= 0
    assert isinstance(summary["actions_executed_total"], int)
    assert summary["actions_executed_total"] >= 0


# ---------------------------------------------------------------------------
# Test 4: gemini_call_latency_ms surfaces per-call latency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_call_latency_surfaces_in_cycle():
    """FIX-05: _generate_with_gemini records latency; _last_gemini_latency_ms is set."""
    mock_genai_module, _mock_client = _make_genai_mock("Generated")

    with (
        patch("app.services.self_improvement_engine.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.CustomSkillsService"),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        _patch_genai(mock_genai_module),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()

        # Call _generate directly to verify latency tracking
        result = await engine._generate_with_gemini("test")

    assert result == "Generated"
    assert hasattr(engine, "_last_gemini_latency_ms")
    assert isinstance(engine._last_gemini_latency_ms, float)
    assert engine._last_gemini_latency_ms >= 0


# ---------------------------------------------------------------------------
# Test 5: genai import failure returns None with latency 0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_with_gemini_import_failure_returns_none():
    """When genai import fails, _generate_with_gemini returns None and latency is 0."""
    # Setting a module to None in sys.modules causes ImportError on import
    google_pkg = sys.modules.get("google")
    saved_genai = sys.modules.get("google.genai")
    saved_attr = getattr(google_pkg, "genai", None) if google_pkg else None

    sys.modules["google.genai"] = None  # type: ignore[assignment]
    if google_pkg is not None and hasattr(google_pkg, "genai"):
        google_pkg.genai = None  # type: ignore[attr-defined]

    try:
        with (
            patch("app.services.self_improvement_engine.get_service_client", return_value=_mock_supabase_client()),
            patch("app.services.self_improvement_engine.CustomSkillsService"),
            patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        ):
            from app.services.self_improvement_engine import SelfImprovementEngine

            engine = SelfImprovementEngine()
            result = await engine._generate_with_gemini("test prompt")

        assert result is None
        assert engine._last_gemini_latency_ms == 0.0
    finally:
        # Restore original state
        if saved_genai is not None:
            sys.modules["google.genai"] = saved_genai
        else:
            sys.modules.pop("google.genai", None)

        if google_pkg is not None:
            if saved_attr is not None:
                google_pkg.genai = saved_attr  # type: ignore[attr-defined]
