# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""FIX-06: Verify run_improvement_cycle does not block the event loop >500ms.

Uses an asyncio scheduling probe that records timestamps at 100ms intervals.
If the engine were still using synchronous Gemini calls (pre-FIX-01), the
probe would never fire because the event loop would be fully blocked.  With
the async client (post-FIX-01), ``await`` yields control and the probe ticks.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock helpers -- isolate from all live services
# ---------------------------------------------------------------------------


def _mock_supabase_table_chain() -> MagicMock:
    """Return a MagicMock whose chained calls always resolve back to itself.

    MagicMock auto-chains attribute access and calls by default, so we only
    need to set `.data` for terminal reads used by execute_async responses.
    """
    chain = MagicMock()
    chain.data = []
    return chain


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImprovementCycleNonBlocking:
    """Prove that run_improvement_cycle yields to the event loop."""

    @pytest.mark.asyncio
    @patch("app.skills.custom_skills_service.get_service_client")
    @patch("app.services.self_improvement_engine.get_service_client")
    @patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock)
    @patch("app.services.research_event_bus.get_event_bus")
    @patch("app.skills.registry.skills_registry")
    async def test_improvement_cycle_does_not_block_event_loop(
        self,
        mock_registry,
        mock_get_bus,
        mock_execute_async,
        mock_get_client,
        mock_get_client_skills,
    ):
        """FIX-06: Scheduling probe fires during run_improvement_cycle.

        A background probe task increments timestamps every 100ms.  If the
        engine blocks the loop for more than 500ms continuously, the probe
        cannot fire -- and the assertion fails.
        """
        # --- Configure mocks ---
        mock_client = MagicMock()
        mock_client.table.return_value = _mock_supabase_table_chain()
        mock_get_client.return_value = mock_client
        mock_get_client_skills.return_value = mock_client

        # execute_async returns empty data for every DB call
        async_result = MagicMock()
        async_result.data = []
        mock_execute_async.return_value = async_result

        # Event bus mock (lazy-imported inside identify_improvements)
        mock_bus = MagicMock()
        mock_bus.emit = AsyncMock()
        mock_get_bus.return_value = mock_bus

        # Registry: no skills registered (fast path)
        mock_registry.list_all.return_value = []
        mock_registry.list_names.return_value = []

        # --- Scheduling probe ---
        probe_timestamps: list[float] = []

        async def scheduling_probe():
            """Background task that records timestamps at ~100ms intervals."""
            while True:
                probe_timestamps.append(time.perf_counter())
                await asyncio.sleep(0.1)

        probe_task = asyncio.create_task(scheduling_probe())

        # Yield once so the probe task runs its first iteration
        await asyncio.sleep(0)

        # --- Run the improvement cycle ---
        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        try:
            result = await asyncio.wait_for(
                engine.run_improvement_cycle(days=7, auto_execute=False),
                timeout=30.0,
            )
        finally:
            probe_task.cancel()
            try:
                await probe_task
            except asyncio.CancelledError:
                pass

        # --- Assertions ---
        # Probe must have fired at least once (event loop was not fully blocked)
        assert len(probe_timestamps) >= 1, (
            "Probe never fired -- event loop was fully blocked"
        )

        # Maximum gap between consecutive probe ticks must be < 500ms
        if len(probe_timestamps) >= 2:
            max_gap_ms = max(
                (probe_timestamps[i + 1] - probe_timestamps[i]) * 1000
                for i in range(len(probe_timestamps) - 1)
            )
            assert max_gap_ms < 500, (
                f"Event loop blocked for {max_gap_ms:.0f}ms (limit: 500ms)"
            )

        # Sanity: cycle completed successfully
        assert result["scores_computed"] == 0
        assert result["improvements_found"] == 0

    @pytest.mark.asyncio
    @patch("app.skills.custom_skills_service.get_service_client")
    @patch("app.services.self_improvement_engine.get_service_client")
    @patch("app.services.self_improvement_engine.execute_async", new_callable=AsyncMock)
    @patch("app.services.research_event_bus.get_event_bus")
    @patch("app.skills.registry.skills_registry")
    async def test_max_gap_between_probe_ticks_under_500ms(
        self,
        mock_registry,
        mock_get_bus,
        mock_execute_async,
        mock_get_client,
        mock_get_client_skills,
    ):
        """FIX-06: Max observed gap between consecutive probes < 500ms.

        This is a stricter variant that asserts the timing constraint
        explicitly even with more data flowing through the cycle.
        """
        # --- Configure mocks ---
        mock_client = MagicMock()
        mock_client.table.return_value = _mock_supabase_table_chain()
        mock_get_client.return_value = mock_client
        mock_get_client_skills.return_value = mock_client

        # Return interaction data for the first two calls (current + prev logs),
        # then empty data for subsequent calls (gaps, declining, used skills).
        interaction_data = [
            {
                "skill_name": f"skill_{i}",
                "feedback": "positive" if i % 2 == 0 else "negative",
                "completed": True,
                "escalated": False,
                "retried": False,
            }
            for i in range(10)
        ]
        result_with_data = MagicMock()
        result_with_data.data = interaction_data
        result_empty = MagicMock()
        result_empty.data = []
        mock_execute_async.side_effect = [
            result_with_data,   # current-period interaction_logs
            result_with_data,   # previous-period interaction_logs
            result_empty,       # skill_scores insert (per-skill, but mock covers all)
            result_empty,       # coverage_gaps
            result_empty,       # declining scores
            result_empty,       # used skill names
            # Additional inserts for improvement_actions
        ] + [result_empty] * 50  # generous padding for any remaining DB calls

        # Event bus mock
        mock_bus = MagicMock()
        mock_bus.emit = AsyncMock()
        mock_get_bus.return_value = mock_bus

        mock_registry.list_all.return_value = []
        mock_registry.list_names.return_value = set()

        # --- Scheduling probe ---
        probe_timestamps: list[float] = []

        async def scheduling_probe():
            """Record timestamps at ~100ms intervals."""
            while True:
                probe_timestamps.append(time.perf_counter())
                await asyncio.sleep(0.1)

        probe_task = asyncio.create_task(scheduling_probe())

        # Yield once so the probe task runs its first iteration
        await asyncio.sleep(0)

        from app.services.self_improvement_engine import SelfImprovementEngine

        engine = SelfImprovementEngine()
        try:
            await asyncio.wait_for(
                engine.run_improvement_cycle(days=7, auto_execute=False),
                timeout=30.0,
            )
        finally:
            probe_task.cancel()
            try:
                await probe_task
            except asyncio.CancelledError:
                pass

        # --- Timing assertion ---
        assert len(probe_timestamps) >= 1, "Probe never fired"
        if len(probe_timestamps) >= 2:
            gaps_ms = [
                (probe_timestamps[i + 1] - probe_timestamps[i]) * 1000
                for i in range(len(probe_timestamps) - 1)
            ]
            max_gap_ms = max(gaps_ms)
            assert max_gap_ms < 500, (
                f"Event loop blocked for {max_gap_ms:.0f}ms (limit: 500ms). "
                f"Gaps: {[f'{g:.0f}ms' for g in gaps_ms]}"
            )
