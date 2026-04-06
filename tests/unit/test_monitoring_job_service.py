# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for MonitoringJobService — CRUD, cadence filtering, and monitoring tick."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-00000000-0000-0000-0000-000000000001"
JOB_ID = "job-00000000-0000-0000-0000-000000000001"

_JOB_CRITICAL = {
    "id": JOB_ID,
    "user_id": USER_ID,
    "topic": "OpenAI",
    "monitoring_type": "competitor",
    "importance": "critical",
    "is_active": True,
    "keyword_triggers": ["GPT-5", "acquisition"],
    "pinned_urls": [],
    "excluded_urls": [],
    "last_run_at": None,
    "last_brief_id": None,
    "previous_state_hash": None,
    "created_at": "2026-04-06T00:00:00Z",
    "updated_at": "2026-04-06T00:00:00Z",
}

_JOB_NORMAL = {
    **_JOB_CRITICAL,
    "id": "job-00000000-0000-0000-0000-000000000002",
    "topic": "AI market trends",
    "monitoring_type": "market",
    "importance": "normal",
    "keyword_triggers": [],
}

_JOB_LOW = {
    **_JOB_CRITICAL,
    "id": "job-00000000-0000-0000-0000-000000000003",
    "topic": "Python packaging",
    "monitoring_type": "topic",
    "importance": "low",
    "keyword_triggers": [],
}

_JOB_INACTIVE = {
    **_JOB_CRITICAL,
    "id": "job-00000000-0000-0000-0000-000000000004",
    "topic": "Old competitor",
    "is_active": False,
}


# ---------------------------------------------------------------------------
# Helpers — supabase mock builder
# ---------------------------------------------------------------------------


def _make_supabase_mock(data: list[dict] | None = None) -> MagicMock:
    """Return a mock supabase client where table ops return given data."""
    mock_result = MagicMock()
    mock_result.data = data if data is not None else []

    mock_chain = MagicMock()
    mock_chain.insert.return_value = mock_chain
    mock_chain.select.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.execute.return_value = mock_result

    mock_client = MagicMock()
    mock_client.table.return_value = mock_chain
    return mock_client


# ---------------------------------------------------------------------------
# Tests: create_job
# ---------------------------------------------------------------------------


class TestCreateJob:
    """create_job inserts and returns the created job dict with id."""

    @pytest.mark.asyncio
    async def test_create_job_returns_job_dict(self):
        """create_job returns the created job dict including id."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            result = await svc.create_job(
                user_id=USER_ID,
                topic="OpenAI",
                monitoring_type="competitor",
                importance="critical",
                keyword_triggers=["GPT-5", "acquisition"],
            )

        assert result["id"] == JOB_ID
        assert result["topic"] == "OpenAI"
        assert result["importance"] == "critical"

    @pytest.mark.asyncio
    async def test_create_job_calls_insert(self):
        """create_job calls supabase insert on monitoring_jobs table."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.create_job(
                user_id=USER_ID,
                topic="OpenAI",
            )

        mock_client.table.assert_called_with("monitoring_jobs")


# ---------------------------------------------------------------------------
# Tests: list_jobs
# ---------------------------------------------------------------------------


class TestListJobs:
    """list_jobs returns only jobs for the given user_id."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_user_jobs(self):
        """list_jobs returns all jobs for the specified user."""
        jobs = [_JOB_CRITICAL, _JOB_NORMAL]
        mock_client = _make_supabase_mock(data=jobs)

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            result = await svc.list_jobs(user_id=USER_ID)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_filters_by_user_id(self):
        """list_jobs queries with user_id filter."""
        mock_client = _make_supabase_mock(data=[])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.list_jobs(user_id=USER_ID)

        # .eq("user_id", ...) must be called on the chain
        chain = mock_client.table.return_value
        chain.eq.assert_called()


# ---------------------------------------------------------------------------
# Tests: update_job
# ---------------------------------------------------------------------------


class TestUpdateJob:
    """update_job modifies allowed fields and returns the updated job."""

    @pytest.mark.asyncio
    async def test_update_job_returns_updated_dict(self):
        """update_job returns the updated job dict."""
        updated = {**_JOB_CRITICAL, "is_active": False}
        mock_client = _make_supabase_mock(data=[updated])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            result = await svc.update_job(
                job_id=JOB_ID, user_id=USER_ID, is_active=False
            )

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_job_calls_update_with_allowed_fields(self):
        """update_job calls supabase update with is_active and importance."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.update_job(
                job_id=JOB_ID, user_id=USER_ID, importance="low"
            )

        chain = mock_client.table.return_value
        chain.update.assert_called()


# ---------------------------------------------------------------------------
# Tests: delete_job
# ---------------------------------------------------------------------------


class TestDeleteJob:
    """delete_job removes the job row."""

    @pytest.mark.asyncio
    async def test_delete_job_returns_confirmation(self):
        """delete_job returns a dict confirming deletion."""
        mock_client = _make_supabase_mock(data=[])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            result = await svc.delete_job(job_id=JOB_ID, user_id=USER_ID)

        assert "deleted" in result or "status" in result

    @pytest.mark.asyncio
    async def test_delete_job_calls_delete(self):
        """delete_job calls supabase delete on monitoring_jobs."""
        mock_client = _make_supabase_mock(data=[])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.delete_job(job_id=JOB_ID, user_id=USER_ID)

        chain = mock_client.table.return_value
        chain.delete.assert_called()


# ---------------------------------------------------------------------------
# Tests: get_due_jobs — cadence filtering
# ---------------------------------------------------------------------------


class TestGetDueJobs:
    """get_due_jobs maps cadence to importance levels correctly."""

    @pytest.mark.asyncio
    async def test_daily_returns_critical_only(self):
        """get_due_jobs('daily') returns only critical active jobs."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.get_due_jobs("daily")

        assert len(results) == 1
        assert results[0]["importance"] == "critical"

    @pytest.mark.asyncio
    async def test_weekly_queries_critical_and_normal(self):
        """get_due_jobs('weekly') calls supabase with in_ filter for critical and normal."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL, _JOB_NORMAL])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.get_due_jobs("weekly")

        chain = mock_client.table.return_value
        # in_ filter must be called with importance values
        chain.in_.assert_called()

    @pytest.mark.asyncio
    async def test_biweekly_returns_all_active(self):
        """get_due_jobs('biweekly') returns all active jobs regardless of importance."""
        all_active = [_JOB_CRITICAL, _JOB_NORMAL, _JOB_LOW]
        mock_client = _make_supabase_mock(data=all_active)

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.get_due_jobs("biweekly")

        assert len(results) == 3


# ---------------------------------------------------------------------------
# Tests: run_monitoring_tick — execution flow
# ---------------------------------------------------------------------------


class TestRunMonitoringTick:
    """run_monitoring_tick executes research pipeline and dispatches alerts."""

    def _make_synthesis(self, text: str = "AI news findings") -> dict[str, Any]:
        return {
            "success": True,
            "original_query": "OpenAI",
            "findings": [{"text": text, "confidence": 0.9}],
            "confidence": 0.85,
            "all_sources": [],
            "tracks_succeeded": 1,
            "tracks_failed": 0,
        }

    @pytest.mark.asyncio
    async def test_run_tick_calls_research_job_for_each_due_job(self):
        """run_monitoring_tick calls _execute_research_job for each due job."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])
        research_result = {
            "success": True,
            "synthesis": self._make_synthesis(),
            "findings": ["finding1"],
        }

        mock_execute = AsyncMock(return_value=research_result)
        mock_vault = AsyncMock(return_value={"success": True, "chunk_count": 2, "title": "T", "embedding_ids": []})

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", mock_execute),
            patch("app.services.monitoring_job_service._check_budget", return_value=True),
            patch("app.services.monitoring_job_service.dispatch_notification", new_callable=AsyncMock),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", mock_vault),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.run_monitoring_tick("daily")

        mock_execute.assert_called_once()
        assert len(results) == 1
        assert results[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_run_tick_checks_budget_before_each_job(self):
        """run_monitoring_tick calls _check_budget before each job."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])
        research_result = {"success": True, "synthesis": self._make_synthesis()}

        mock_budget = MagicMock(return_value=True)

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", AsyncMock(return_value=research_result)),
            patch("app.services.monitoring_job_service._check_budget", mock_budget),
            patch("app.services.monitoring_job_service.dispatch_notification", new_callable=AsyncMock),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", AsyncMock(return_value={"success": True, "chunk_count": 1, "title": "T", "embedding_ids": []})),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.run_monitoring_tick("daily")

        mock_budget.assert_called_with("research")

    @pytest.mark.asyncio
    async def test_run_tick_stops_when_budget_exhausted(self):
        """run_monitoring_tick skips jobs when _check_budget returns False."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL, _JOB_NORMAL])
        mock_execute = AsyncMock()

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", mock_execute),
            patch("app.services.monitoring_job_service._check_budget", return_value=False),
            patch("app.services.monitoring_job_service.dispatch_notification", new_callable=AsyncMock),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", AsyncMock(return_value={"success": True})),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.run_monitoring_tick("biweekly")

        # Research not called since budget exhausted
        mock_execute.assert_not_called()
        # All jobs skipped
        assert all(r["status"] == "skipped" for r in results)

    @pytest.mark.asyncio
    async def test_run_tick_dispatches_notification_on_hash_change_with_significance(self):
        """run_monitoring_tick dispatches alert when hash changes and AI judges significant."""
        job = {
            **_JOB_CRITICAL,
            "previous_state_hash": "old-hash-abc",
            "keyword_triggers": [],
        }
        mock_client = _make_supabase_mock(data=[job])
        synthesis = self._make_synthesis("Major GPT product launch announced")
        research_result = {"success": True, "synthesis": synthesis}

        mock_dispatch = AsyncMock(return_value={"slack": True})
        mock_significance = AsyncMock(return_value=True)

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", AsyncMock(return_value=research_result)),
            patch("app.services.monitoring_job_service._check_budget", return_value=True),
            patch("app.services.monitoring_job_service.dispatch_notification", mock_dispatch),
            patch("app.services.monitoring_job_service._is_significant_change", mock_significance),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", AsyncMock(return_value={"success": True, "chunk_count": 1, "title": "T", "embedding_ids": []})),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.run_monitoring_tick("daily")

        mock_dispatch.assert_called_once()
        call_kwargs = mock_dispatch.call_args
        assert results[0]["alerted"] is True

    @pytest.mark.asyncio
    async def test_run_tick_dispatches_on_keyword_trigger_regardless_of_significance(self):
        """run_monitoring_tick dispatches alert when keyword_triggers match synthesis text."""
        job = {
            **_JOB_CRITICAL,
            "previous_state_hash": "old-hash-xyz",
            "keyword_triggers": ["GPT-5"],
        }
        mock_client = _make_supabase_mock(data=[job])
        synthesis = self._make_synthesis("OpenAI released GPT-5 this week")
        research_result = {"success": True, "synthesis": synthesis}

        mock_dispatch = AsyncMock(return_value={"slack": True})
        mock_significance = AsyncMock(return_value=False)  # NOT significant by AI

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", AsyncMock(return_value=research_result)),
            patch("app.services.monitoring_job_service._check_budget", return_value=True),
            patch("app.services.monitoring_job_service.dispatch_notification", mock_dispatch),
            patch("app.services.monitoring_job_service._is_significant_change", mock_significance),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", AsyncMock(return_value={"success": True, "chunk_count": 1, "title": "T", "embedding_ids": []})),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.run_monitoring_tick("daily")

        # Keyword match triggers dispatch even though AI says not significant
        mock_dispatch.assert_called_once()
        assert results[0]["alerted"] is True

    @pytest.mark.asyncio
    async def test_run_tick_no_alert_when_hash_unchanged(self):
        """run_monitoring_tick does NOT dispatch when hash is unchanged."""
        import hashlib
        synthesis_text = "AI news findings"
        synthesis = self._make_synthesis(synthesis_text)
        # Compute the hash that will be generated from synthesis findings text
        findings_text = " ".join(
            f.get("text", "") for f in synthesis.get("findings", [])
        )
        existing_hash = hashlib.sha256(findings_text.encode()).hexdigest()

        job = {
            **_JOB_CRITICAL,
            "previous_state_hash": existing_hash,
            "keyword_triggers": [],
        }
        mock_client = _make_supabase_mock(data=[job])
        research_result = {"success": True, "synthesis": synthesis}

        mock_dispatch = AsyncMock()

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", AsyncMock(return_value=research_result)),
            patch("app.services.monitoring_job_service._check_budget", return_value=True),
            patch("app.services.monitoring_job_service.dispatch_notification", mock_dispatch),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", AsyncMock(return_value={"success": True, "chunk_count": 1, "title": "T", "embedding_ids": []})),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            results = await svc.run_monitoring_tick("daily")

        mock_dispatch.assert_not_called()
        assert results[0]["alerted"] is False

    @pytest.mark.asyncio
    async def test_run_tick_updates_hash_and_last_run_at(self):
        """run_monitoring_tick updates last_run_at and previous_state_hash after execution."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])
        research_result = {"success": True, "synthesis": self._make_synthesis()}

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", AsyncMock(return_value=research_result)),
            patch("app.services.monitoring_job_service._check_budget", return_value=True),
            patch("app.services.monitoring_job_service.dispatch_notification", new_callable=AsyncMock),
            patch("app.services.monitoring_job_service.write_to_graph", return_value={"success": True}),
            patch("app.services.monitoring_job_service.write_to_vault", AsyncMock(return_value={"success": True, "chunk_count": 1, "title": "T", "embedding_ids": []})),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.run_monitoring_tick("daily")

        # update must have been called
        chain = mock_client.table.return_value
        chain.update.assert_called()

    @pytest.mark.asyncio
    async def test_run_tick_calls_write_to_graph_and_vault(self):
        """run_monitoring_tick calls write_to_graph and write_to_vault with synthesis."""
        mock_client = _make_supabase_mock(data=[_JOB_CRITICAL])
        synthesis = self._make_synthesis()
        research_result = {"success": True, "synthesis": synthesis}

        mock_graph = MagicMock(return_value={"success": True})
        mock_vault = AsyncMock(return_value={"success": True, "chunk_count": 3, "title": "Research: OpenAI", "embedding_ids": ["e1"]})

        with (
            patch("app.services.monitoring_job_service.get_service_client", return_value=mock_client),
            patch("app.services.monitoring_job_service._execute_research_job", AsyncMock(return_value=research_result)),
            patch("app.services.monitoring_job_service._check_budget", return_value=True),
            patch("app.services.monitoring_job_service.dispatch_notification", new_callable=AsyncMock),
            patch("app.services.monitoring_job_service.write_to_graph", mock_graph),
            patch("app.services.monitoring_job_service.write_to_vault", mock_vault),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc.run_monitoring_tick("daily")

        mock_graph.assert_called_once()
        mock_vault.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: module-level run_monitoring_tick function
# ---------------------------------------------------------------------------


class TestModuleLevelRunMonitoringTick:
    """Module-level run_monitoring_tick convenience function."""

    @pytest.mark.asyncio
    async def test_module_function_delegates_to_service(self):
        """Module-level run_monitoring_tick instantiates service and calls method."""
        mock_client = _make_supabase_mock(data=[])

        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=mock_client,
        ):
            from app.services.monitoring_job_service import run_monitoring_tick

            results = await run_monitoring_tick("daily")

        assert isinstance(results, list)
