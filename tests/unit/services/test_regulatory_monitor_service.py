# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for RegulatoryMonitorService and ComplianceService deadline CRUD.

Plan 66-03 / LEGAL-03, LEGAL-05. Verifies:

- ComplianceService.create_deadline inserts a row with title, due_date, category, recurrence
- ComplianceService.list_deadlines returns deadlines ordered by due_date, filtered by status
- ComplianceService.list_deadlines with upcoming_only=True returns only future deadlines
- ComplianceService.update_deadline can mark a deadline as completed
- RegulatoryMonitorService.check_updates queries web search and returns structured results
- RegulatoryMonitorService.check_updates returns list of dicts with title, summary, source_url, relevance, date_published
- RegulatoryMonitorService.dispatch_deadline_reminders finds deadlines due within reminder window and dispatches alerts
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-test-key",
    "SUPABASE_ANON_KEY": "anon-test-key",
}


def _result(data=None):
    """Build a fake supabase result with ``.data``."""
    obj = MagicMock()
    obj.data = data if data is not None else []
    return obj


def _make_compliance_service():
    """Return a ComplianceService with stubbed Supabase client."""
    with patch.dict("os.environ", _FAKE_ENV, clear=False):
        from app.services.compliance_service import ComplianceService

        return ComplianceService()


# ---------------------------------------------------------------------------
# ComplianceService -- Deadline CRUD
# ---------------------------------------------------------------------------


class TestCreateDeadline:
    """ComplianceService.create_deadline inserts a deadline row."""

    @pytest.mark.asyncio
    async def test_create_deadline_returns_inserted_row(self):
        """create_deadline inserts and returns the new deadline."""
        svc = _make_compliance_service()
        inserted_row = {
            "id": "dl-1",
            "title": "GDPR Annual Review",
            "due_date": "2026-06-01",
            "category": "gdpr",
            "recurrence": "annual",
            "reminder_days_before": 14,
            "status": "upcoming",
            "user_id": "user-1",
        }

        async def fake_execute(query, **kwargs):
            return _result(data=[inserted_row])

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.compliance_service.execute_async",
            side_effect=fake_execute,
        ), patch(
            "app.services.compliance_service.get_current_user_id",
            return_value="user-1",
        ):
            result = await svc.create_deadline(
                title="GDPR Annual Review",
                due_date="2026-06-01",
                category="gdpr",
                recurrence="annual",
                user_id="user-1",
            )

        assert result["title"] == "GDPR Annual Review"
        assert result["category"] == "gdpr"

    @pytest.mark.asyncio
    async def test_create_deadline_rejects_invalid_category(self):
        """create_deadline raises for invalid category."""
        svc = _make_compliance_service()

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.compliance_service.get_current_user_id",
            return_value="user-1",
        ), pytest.raises(ValueError, match="Invalid category"):
            await svc.create_deadline(
                title="Bad Category",
                due_date="2026-06-01",
                category="invalid_cat",
                user_id="user-1",
            )


class TestListDeadlines:
    """ComplianceService.list_deadlines queries and filters deadlines."""

    @pytest.mark.asyncio
    async def test_list_deadlines_returns_ordered_results(self):
        """list_deadlines returns deadlines in order."""
        svc = _make_compliance_service()
        rows = [
            {"id": "dl-1", "title": "First", "due_date": "2026-05-01", "status": "upcoming"},
            {"id": "dl-2", "title": "Second", "due_date": "2026-06-01", "status": "upcoming"},
        ]

        async def fake_execute(query, **kwargs):
            return _result(data=rows)

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.compliance_service.execute_async",
            side_effect=fake_execute,
        ), patch(
            "app.services.compliance_service.get_current_user_id",
            return_value="user-1",
        ):
            result = await svc.list_deadlines(user_id="user-1")

        assert len(result) == 2
        assert result[0]["title"] == "First"

    @pytest.mark.asyncio
    async def test_list_deadlines_with_status_filter(self):
        """list_deadlines accepts a status filter."""
        svc = _make_compliance_service()

        async def fake_execute(query, **kwargs):
            return _result(data=[
                {"id": "dl-1", "title": "Done", "due_date": "2026-03-01", "status": "completed"},
            ])

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.compliance_service.execute_async",
            side_effect=fake_execute,
        ), patch(
            "app.services.compliance_service.get_current_user_id",
            return_value="user-1",
        ):
            result = await svc.list_deadlines(status="completed", user_id="user-1")

        assert len(result) == 1
        assert result[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_deadlines_upcoming_only(self):
        """list_deadlines with upcoming_only=True filters to future deadlines."""
        svc = _make_compliance_service()

        async def fake_execute(query, **kwargs):
            return _result(data=[
                {"id": "dl-2", "title": "Future", "due_date": "2027-01-01", "status": "upcoming"},
            ])

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.compliance_service.execute_async",
            side_effect=fake_execute,
        ), patch(
            "app.services.compliance_service.get_current_user_id",
            return_value="user-1",
        ):
            result = await svc.list_deadlines(upcoming_only=True, user_id="user-1")

        assert len(result) == 1
        assert result[0]["title"] == "Future"


class TestUpdateDeadline:
    """ComplianceService.update_deadline modifies deadline fields."""

    @pytest.mark.asyncio
    async def test_update_deadline_marks_completed(self):
        """update_deadline can set status to completed."""
        svc = _make_compliance_service()
        updated_row = {
            "id": "dl-1",
            "title": "GDPR Review",
            "status": "completed",
        }

        async def fake_execute(query, **kwargs):
            return _result(data=[updated_row])

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.compliance_service.execute_async",
            side_effect=fake_execute,
        ), patch(
            "app.services.compliance_service.get_current_user_id",
            return_value="user-1",
        ):
            result = await svc.update_deadline(
                deadline_id="dl-1",
                status="completed",
                user_id="user-1",
            )

        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# RegulatoryMonitorService
# ---------------------------------------------------------------------------


class TestCheckUpdates:
    """RegulatoryMonitorService.check_updates searches for regulatory changes."""

    @pytest.mark.asyncio
    async def test_check_updates_returns_structured_results(self):
        """check_updates parses web search results into structured format."""
        fake_search_result = {
            "results": [
                {
                    "title": "New GDPR Amendment 2026",
                    "url": "https://example.com/gdpr-2026",
                    "content": "The European Union has proposed new amendments to GDPR affecting data processing.",
                },
                {
                    "title": "Healthcare Data Protection Update",
                    "url": "https://example.com/healthcare-update",
                    "content": "New healthcare privacy rules announced for EU member states.",
                },
            ]
        }

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.regulatory_monitor_service.mcp_web_search",
            new_callable=AsyncMock,
            return_value=fake_search_result,
        ):
            from app.services.regulatory_monitor_service import RegulatoryMonitorService

            service = RegulatoryMonitorService()
            result = await service.check_updates(
                industry="healthcare",
                jurisdiction="European Union",
                topics=["data privacy"],
            )

        assert result["success"] is True
        assert result["industry"] == "healthcare"
        assert result["jurisdiction"] == "European Union"
        assert len(result["updates"]) == 2
        # Each update has required fields
        for update in result["updates"]:
            assert "title" in update
            assert "summary" in update
            assert "source_url" in update
            assert "relevance" in update
            assert "date_published" in update

    @pytest.mark.asyncio
    async def test_check_updates_handles_error(self):
        """check_updates returns error dict on failure."""
        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.regulatory_monitor_service.mcp_web_search",
            new_callable=AsyncMock,
            side_effect=Exception("Search API down"),
        ):
            from app.services.regulatory_monitor_service import RegulatoryMonitorService

            service = RegulatoryMonitorService()
            result = await service.check_updates(
                industry="fintech",
                jurisdiction="United States",
            )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_check_updates_relevance_scoring(self):
        """check_updates assigns relevance based on keyword matching."""
        fake_search_result = {
            "results": [
                {
                    "title": "Healthcare GDPR EU compliance changes",
                    "url": "https://example.com/relevant",
                    "content": "Healthcare sector in European Union faces new GDPR requirements.",
                },
                {
                    "title": "Unrelated crypto news",
                    "url": "https://example.com/unrelated",
                    "content": "Bitcoin price update from Asia markets.",
                },
            ]
        }

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.regulatory_monitor_service.mcp_web_search",
            new_callable=AsyncMock,
            return_value=fake_search_result,
        ):
            from app.services.regulatory_monitor_service import RegulatoryMonitorService

            service = RegulatoryMonitorService()
            result = await service.check_updates(
                industry="healthcare",
                jurisdiction="European Union",
            )

        assert result["success"] is True
        # First result mentions industry + jurisdiction => high relevance
        relevant = result["updates"][0]
        assert relevant["relevance"] in ("high", "medium")
        # Second result mentions neither => low
        unrelated = result["updates"][1]
        assert unrelated["relevance"] == "low"


class TestDispatchDeadlineReminders:
    """RegulatoryMonitorService.dispatch_deadline_reminders sends alerts."""

    @pytest.mark.asyncio
    async def test_dispatch_reminders_sends_alerts_for_upcoming(self):
        """dispatch_deadline_reminders finds deadlines in reminder window and dispatches."""
        deadlines_in_window = [
            {
                "id": "dl-1",
                "title": "GDPR Review",
                "due_date": "2026-04-20",
                "category": "gdpr",
                "reminder_days_before": 14,
            },
        ]

        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.regulatory_monitor_service.execute_async",
            new_callable=AsyncMock,
            return_value=_result(data=deadlines_in_window),
        ), patch(
            "app.services.regulatory_monitor_service.dispatch_proactive_alert",
            mock_dispatch,
        ):
            from app.services.regulatory_monitor_service import RegulatoryMonitorService

            service = RegulatoryMonitorService()
            result = await service.dispatch_deadline_reminders(user_id="user-1")

        assert result["reminders_sent"] == 1
        assert result["deadlines_checked"] == 1
        mock_dispatch.assert_called_once()
        call_kwargs = mock_dispatch.call_args
        assert call_kwargs[1]["alert_type"] == "compliance_deadline_reminder"
        assert "GDPR Review" in call_kwargs[1]["title"]

    @pytest.mark.asyncio
    async def test_dispatch_reminders_skips_outside_window(self):
        """dispatch_deadline_reminders returns 0 when no deadlines in window."""
        with patch.dict("os.environ", _FAKE_ENV, clear=False), patch(
            "app.services.regulatory_monitor_service.execute_async",
            new_callable=AsyncMock,
            return_value=_result(data=[]),
        ), patch(
            "app.services.regulatory_monitor_service.dispatch_proactive_alert",
            new_callable=AsyncMock,
        ) as mock_dispatch:
            from app.services.regulatory_monitor_service import RegulatoryMonitorService

            service = RegulatoryMonitorService()
            result = await service.dispatch_deadline_reminders(user_id="user-1")

        assert result["reminders_sent"] == 0
        assert result["deadlines_checked"] == 0
        mock_dispatch.assert_not_called()
