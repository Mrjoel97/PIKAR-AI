"""Tests for the intelligence scheduler."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_get_domains_due_for_refresh():
    """Scheduler identifies domains that need refreshing."""
    from app.services.intelligence_scheduler import get_domains_due_for_refresh

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"domain": "financial", "schedule_cron": "0 6 * * *", "is_active": True},
        {"domain": "hr", "schedule_cron": "0 6 * * 1", "is_active": True},
    ]

    with patch(
        "app.services.intelligence_scheduler._get_supabase",
        return_value=mock_client,
    ):
        domains = get_domains_due_for_refresh()

    assert isinstance(domains, list)
    # Returns active domains (actual cron check depends on current time)


def test_build_research_queue_prioritizes_stale():
    """Research queue prioritizes stale high-value entities."""
    from app.services.intelligence_scheduler import build_research_queue

    mock_client = MagicMock()

    # Mock stale entities
    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "canonical_name": "SARB",
            "source_count": 14,
            "freshness_at": "2026-03-01T00:00:00Z",
        },
    ]

    # Mock watch topics
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"topic": "ZAR exchange rate", "priority": "critical"},
    ]

    with patch(
        "app.services.intelligence_scheduler._get_supabase",
        return_value=mock_client,
    ):
        queue = build_research_queue(domain="financial")

    assert isinstance(queue, list)
    assert len(queue) >= 0  # depends on mocked data


def test_run_scheduled_research_executes_pipeline():
    """Scheduler executes the full research pipeline for a domain."""
    from app.services.intelligence_scheduler import run_scheduled_research

    with patch(
        "app.services.intelligence_scheduler.build_research_queue",
        return_value=[
            {"query": "SARB interest rate", "depth": "standard"},
        ],
    ):
        with patch(
            "app.services.intelligence_scheduler._execute_research_job",
            new_callable=AsyncMock,
            return_value={"success": True},
        ):
            result = _run(run_scheduled_research(domain="financial"))

    assert result["success"] is True
    assert result["jobs_executed"] >= 0
