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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers – mock Supabase + skills_registry to isolate engine construction
# ---------------------------------------------------------------------------

def _mock_supabase_client() -> MagicMock:
    """Return a MagicMock that fakes Supabase table().select()...execute_async."""
    client = MagicMock()
    # Default: every table chain returns empty data
    resp = MagicMock()
    resp.data = []
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


# ---------------------------------------------------------------------------
# Test 1: _generate_with_gemini uses async path (client.aio.models)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_with_gemini_uses_async_client():
    """FIX-01: _generate_with_gemini must await client.aio.models.generate_content."""
    mock_response = MagicMock()
    mock_response.text = "Generated text"

    # Build a mock genai.Client whose .aio.models.generate_content is an AsyncMock
    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )
    # The sync path should NOT be called
    mock_client_instance.models.generate_content = MagicMock(
        side_effect=AssertionError("sync path called – should use async")
    )

    mock_genai_module = MagicMock()
    mock_genai_module.Client.return_value = mock_client_instance

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        patch.dict("sys.modules", {"google.genai": mock_genai_module}),
    ):
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        result = await engine._generate_with_gemini("test prompt")

    assert result == "Generated text"
    mock_client_instance.aio.models.generate_content.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2: identify_improvements uses `await bus.emit()` (no run_until_complete)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_identify_improvements_awaits_bus_emit():
    """FIX-02: identify_improvements must call `await bus.emit(...)` directly."""
    mock_bus = MagicMock()
    mock_bus.emit = AsyncMock(return_value={"success": True})

    # Provide a score that triggers coverage_gap processing
    # We need at least one gap to trigger the emit path
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
        if "coverage_gaps" in op_name:
            return mock_gap_resp
        resp = MagicMock()
        resp.data = []
        return resp

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_execute_async_side_effect),
        patch("app.services.self_improvement_engine.get_event_bus", return_value=mock_bus),
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
    """FIX-05: run_improvement_cycle must return cycle_duration_ms, gemini_call_latency_ms, actions_executed_total."""
    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
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
    """FIX-05: _generate_with_gemini records latency and cycle surfaces it as gemini_call_latency_ms."""
    mock_response = MagicMock()
    mock_response.text = "Generated"

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )
    mock_genai_module = MagicMock()
    mock_genai_module.Client.return_value = mock_client_instance

    with (
        patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
        patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        patch("app.services.self_improvement_engine.skills_registry") as mock_registry,
        patch.dict("sys.modules", {"google.genai": mock_genai_module}),
    ):
        mock_registry.list_names.return_value = []

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()

        # Call _generate directly to verify latency tracking
        await engine._generate_with_gemini("test")
        assert hasattr(engine, "_last_gemini_latency_ms")
        assert engine._last_gemini_latency_ms >= 0


# ---------------------------------------------------------------------------
# Test 5: genai import failure returns None with latency 0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_with_gemini_import_failure_returns_none():
    """When genai import fails, _generate_with_gemini returns None and latency is 0."""
    # Remove google.genai so the import fails inside the method
    import sys

    saved = sys.modules.get("google.genai")
    sys.modules["google.genai"] = None  # type: ignore[assignment]

    try:
        with (
            patch("app.services.supabase.get_service_client", return_value=_mock_supabase_client()),
            patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock, side_effect=_empty_async_resp),
        ):
            from app.services.self_improvement_engine import SelfImprovementEngine

            engine = SelfImprovementEngine()
            result = await engine._generate_with_gemini("test prompt")

        assert result is None
        assert engine._last_gemini_latency_ms == 0.0
    finally:
        if saved is not None:
            sys.modules["google.genai"] = saved
        else:
            sys.modules.pop("google.genai", None)
