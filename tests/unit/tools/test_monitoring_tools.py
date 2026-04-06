# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for monitoring agent tools — create, list, pause, resume, delete."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-00000000-0000-0000-0000-000000000001"
JOB_ID = "job-00000000-0000-0000-0000-000000000002"

_CREATED_JOB = {
    "id": JOB_ID,
    "user_id": USER_ID,
    "topic": "OpenAI",
    "monitoring_type": "competitor",
    "importance": "critical",
    "is_active": True,
    "keyword_triggers": ["GPT-5"],
    "pinned_urls": [],
    "excluded_urls": [],
    "last_run_at": None,
    "created_at": "2026-04-06T00:00:00Z",
}

_JOB_NORMAL = {
    **_CREATED_JOB,
    "id": "job-00000000-0000-0000-0000-000000000003",
    "topic": "AI market",
    "monitoring_type": "market",
    "importance": "normal",
    "keyword_triggers": [],
}

_JOB_LOW = {
    **_CREATED_JOB,
    "id": "job-00000000-0000-0000-0000-000000000004",
    "topic": "Python packaging",
    "monitoring_type": "topic",
    "importance": "low",
    "keyword_triggers": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_mock(
    create_return=None,
    list_return=None,
    update_return=None,
    delete_return=None,
) -> MagicMock:
    """Build a mock MonitoringJobService with preset return values."""
    svc = MagicMock()
    svc.create_job = AsyncMock(return_value=create_return or _CREATED_JOB)
    svc.list_jobs = AsyncMock(return_value=list_return or [])
    svc.update_job = AsyncMock(return_value=update_return or _CREATED_JOB)
    svc.delete_job = AsyncMock(return_value={"deleted": True, "job_id": JOB_ID})
    return svc


# ---------------------------------------------------------------------------
# Tests: MONITORING_TOOLS export
# ---------------------------------------------------------------------------


class TestMonitoringToolsExport:
    """MONITORING_TOOLS list must contain all 5 tool functions."""

    def test_tools_list_contains_all_five_functions(self):
        """MONITORING_TOOLS must include all 5 tool functions."""
        from app.agents.research.tools.monitoring_tools import MONITORING_TOOLS

        tool_names = [fn.__name__ for fn in MONITORING_TOOLS]
        assert "create_monitoring_job" in tool_names
        assert "list_monitoring_jobs" in tool_names
        assert "pause_monitoring_job" in tool_names
        assert "resume_monitoring_job" in tool_names
        assert "delete_monitoring_job" in tool_names

    def test_tools_list_is_list_of_length_five(self):
        """MONITORING_TOOLS must be a list of exactly 5 functions."""
        from app.agents.research.tools.monitoring_tools import MONITORING_TOOLS

        assert isinstance(MONITORING_TOOLS, list)
        assert len(MONITORING_TOOLS) == 5


# ---------------------------------------------------------------------------
# Tests: create_monitoring_job
# ---------------------------------------------------------------------------


class TestCreateMonitoringJob:
    """create_monitoring_job returns created job dict with schedule info."""

    @pytest.mark.asyncio
    async def test_returns_job_dict_with_schedule_info(self):
        """Returns dict with status, job, schedule, and message keys."""
        mock_svc = _make_service_mock(create_return=_CREATED_JOB)

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import create_monitoring_job

            result = await create_monitoring_job(
                topic="OpenAI",
                monitoring_type="competitor",
                importance="critical",
            )

        assert result["status"] == "success"
        assert "job" in result
        assert "schedule" in result
        assert "daily" in result["schedule"].lower()
        assert "message" in result

    @pytest.mark.asyncio
    async def test_normal_importance_shows_weekly_schedule(self):
        """Normal importance maps to weekly schedule description."""
        normal_job = {**_CREATED_JOB, "importance": "normal"}
        mock_svc = _make_service_mock(create_return=normal_job)

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import create_monitoring_job

            result = await create_monitoring_job(topic="AI market", importance="normal")

        assert "weekly" in result["schedule"].lower()

    @pytest.mark.asyncio
    async def test_low_importance_shows_biweekly_schedule(self):
        """Low importance maps to biweekly schedule description."""
        low_job = {**_CREATED_JOB, "importance": "low"}
        mock_svc = _make_service_mock(create_return=low_job)

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import create_monitoring_job

            result = await create_monitoring_job(topic="Python", importance="low")

        assert "biweekly" in result["schedule"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_when_not_authenticated(self):
        """Returns error dict when user_id is unavailable."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=None):
            from app.agents.research.tools.monitoring_tools import create_monitoring_job

            result = await create_monitoring_job(topic="OpenAI")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_validates_monitoring_type(self):
        """Returns error when monitoring_type is invalid."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID):
            from app.agents.research.tools.monitoring_tools import create_monitoring_job

            result = await create_monitoring_job(
                topic="OpenAI", monitoring_type="invalid_type"
            )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_validates_importance(self):
        """Returns error when importance is invalid."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID):
            from app.agents.research.tools.monitoring_tools import create_monitoring_job

            result = await create_monitoring_job(
                topic="OpenAI", importance="super_critical"
            )

        assert "error" in result


# ---------------------------------------------------------------------------
# Tests: list_monitoring_jobs
# ---------------------------------------------------------------------------


class TestListMonitoringJobs:
    """list_monitoring_jobs returns user jobs with schedule descriptions."""

    @pytest.mark.asyncio
    async def test_returns_jobs_list_with_count(self):
        """Returns dict with status, jobs list, and count."""
        jobs = [_CREATED_JOB, _JOB_NORMAL, _JOB_LOW]
        mock_svc = _make_service_mock(list_return=jobs)

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import list_monitoring_jobs

            result = await list_monitoring_jobs()

        assert result["status"] == "success"
        assert result["count"] == 3
        assert len(result["jobs"]) == 3

    @pytest.mark.asyncio
    async def test_jobs_include_schedule_description(self):
        """Each job in the list includes a schedule_description field."""
        mock_svc = _make_service_mock(list_return=[_CREATED_JOB])

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import list_monitoring_jobs

            result = await list_monitoring_jobs()

        assert "schedule_description" in result["jobs"][0]

    @pytest.mark.asyncio
    async def test_returns_error_when_not_authenticated(self):
        """Returns error dict when user_id is unavailable."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=None):
            from app.agents.research.tools.monitoring_tools import list_monitoring_jobs

            result = await list_monitoring_jobs()

        assert "error" in result


# ---------------------------------------------------------------------------
# Tests: pause_monitoring_job
# ---------------------------------------------------------------------------


class TestPauseMonitoringJob:
    """pause_monitoring_job sets is_active=False."""

    @pytest.mark.asyncio
    async def test_pause_calls_update_with_is_active_false(self):
        """pause_monitoring_job calls update_job with is_active=False."""
        mock_svc = _make_service_mock()

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import pause_monitoring_job

            result = await pause_monitoring_job(job_id=JOB_ID)

        mock_svc.update_job.assert_called_once_with(
            job_id=JOB_ID, user_id=USER_ID, is_active=False
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_pause_returns_error_when_not_authenticated(self):
        """Returns error dict when user_id is unavailable."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=None):
            from app.agents.research.tools.monitoring_tools import pause_monitoring_job

            result = await pause_monitoring_job(job_id=JOB_ID)

        assert "error" in result


# ---------------------------------------------------------------------------
# Tests: resume_monitoring_job
# ---------------------------------------------------------------------------


class TestResumeMonitoringJob:
    """resume_monitoring_job sets is_active=True."""

    @pytest.mark.asyncio
    async def test_resume_calls_update_with_is_active_true(self):
        """resume_monitoring_job calls update_job with is_active=True."""
        mock_svc = _make_service_mock()

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import resume_monitoring_job

            result = await resume_monitoring_job(job_id=JOB_ID)

        mock_svc.update_job.assert_called_once_with(
            job_id=JOB_ID, user_id=USER_ID, is_active=True
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_resume_returns_error_when_not_authenticated(self):
        """Returns error dict when user_id is unavailable."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=None):
            from app.agents.research.tools.monitoring_tools import resume_monitoring_job

            result = await resume_monitoring_job(job_id=JOB_ID)

        assert "error" in result


# ---------------------------------------------------------------------------
# Tests: delete_monitoring_job
# ---------------------------------------------------------------------------


class TestDeleteMonitoringJob:
    """delete_monitoring_job removes the job."""

    @pytest.mark.asyncio
    async def test_delete_calls_service_delete_job(self):
        """delete_monitoring_job calls service.delete_job with correct args."""
        mock_svc = _make_service_mock()

        with (
            patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=USER_ID),
            patch("app.services.monitoring_job_service.MonitoringJobService", return_value=mock_svc),
        ):
            from app.agents.research.tools.monitoring_tools import delete_monitoring_job

            result = await delete_monitoring_job(job_id=JOB_ID)

        mock_svc.delete_job.assert_called_once_with(job_id=JOB_ID, user_id=USER_ID)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_returns_error_when_not_authenticated(self):
        """Returns error dict when user_id is unavailable."""
        with patch("app.agents.research.tools.monitoring_tools._get_user_id", return_value=None):
            from app.agents.research.tools.monitoring_tools import delete_monitoring_job

            result = await delete_monitoring_job(job_id=JOB_ID)

        assert "error" in result
