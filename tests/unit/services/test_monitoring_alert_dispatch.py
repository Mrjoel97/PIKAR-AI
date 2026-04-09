# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for competitor monitoring alert dispatch in MonitoringJobService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


def _make_mock_client() -> MagicMock:
    """Build a mock Supabase service client with a chainable query interface."""
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.neq.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.insert.return_value = mock_chain
    mock_table.upsert.return_value = mock_chain
    mock_table.update.return_value = mock_chain
    mock_table.delete.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client


def _finding(
    text: str,
    confidence: float = 0.8,
    category: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Build a mock research finding."""
    return {
        "text": text,
        "confidence": confidence,
        "category": category or "general",
        "metadata": metadata or {},
    }


# ---------------------------------------------------------------------------
# _classify_competitor_change
# ---------------------------------------------------------------------------


class TestClassifyCompetitorChange:
    """_classify_competitor_change identifies change types from finding text."""

    def test_detects_pricing_change(self):
        """Pricing-related keywords are classified as pricing_change."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "Acme Corp has updated their pricing tiers with a 20% increase",
            {},
        )
        assert result == "pricing_change"

    def test_detects_product_launch(self):
        """Product launch keywords are classified as product_launch."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "Acme Corp launched a new AI-powered analytics product",
            {},
        )
        assert result == "product_launch"

    def test_detects_funding_round(self):
        """Funding round keywords are classified as funding_round."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "Acme Corp raised $50M in Series B funding",
            {},
        )
        assert result == "funding_round"

    def test_detects_acquisition(self):
        """Acquisition keywords are classified as acquisition."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "Acme Corp has acquired DataViz Inc for an undisclosed sum",
            {},
        )
        assert result == "acquisition"

    def test_detects_partnership(self):
        """Partnership keywords are classified as partnership."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "Acme Corp announced a strategic partnership with BigCo",
            {},
        )
        assert result == "partnership"

    def test_returns_none_for_unrelated_text(self):
        """Generic text without competitor change keywords returns None."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "The weather today is sunny with a high of 72F",
            {},
        )
        assert result is None

    def test_uses_metadata_category(self):
        """Change type from metadata category overrides text classification."""
        with patch(
            "app.services.monitoring_job_service.get_service_client",
            return_value=_make_mock_client(),
        ):
            from app.services.monitoring_job_service import (
                _classify_competitor_change,
            )

        result = _classify_competitor_change(
            "Some generic text about business operations",
            {"category": "funding_round"},
        )
        assert result == "funding_round"


# ---------------------------------------------------------------------------
# _dispatch_monitoring_alert
# ---------------------------------------------------------------------------


class TestDispatchMonitoringAlert:
    """_dispatch_monitoring_alert filters by confidence and dispatches alerts."""

    @pytest.mark.asyncio
    async def test_dispatches_for_high_confidence_findings(self):
        """Findings with confidence > 0.7 trigger alert dispatch."""
        mock_client = _make_mock_client()
        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        job = {
            "id": "job-1",
            "user_id": USER_ID,
            "topic": "Acme Corp",
            "monitoring_type": "competitor",
            "importance": "critical",
        }
        findings = [
            _finding(
                "Acme Corp raised $50M in Series B funding round",
                confidence=0.9,
                category="funding_round",
            ),
        ]

        with (
            patch(
                "app.services.monitoring_job_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.monitoring_job_service.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc._dispatch_monitoring_alert(USER_ID, job, findings)

        assert mock_dispatch.call_count >= 1
        call_kwargs = mock_dispatch.call_args_list[0][1]
        assert call_kwargs["alert_type"] == "competitor.change"
        assert "Acme Corp" in call_kwargs["title"]

    @pytest.mark.asyncio
    async def test_skips_low_confidence_findings(self):
        """Findings with confidence <= 0.7 and no critical category are skipped."""
        mock_client = _make_mock_client()
        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        job = {
            "id": "job-1",
            "user_id": USER_ID,
            "topic": "Acme Corp",
            "monitoring_type": "competitor",
            "importance": "normal",
        }
        findings = [
            _finding(
                "Some minor mention of Acme Corp in a blog post",
                confidence=0.3,
                category="general",
            ),
        ]

        with (
            patch(
                "app.services.monitoring_job_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.monitoring_job_service.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc._dispatch_monitoring_alert(USER_ID, job, findings)

        assert mock_dispatch.call_count == 0

    @pytest.mark.asyncio
    async def test_dispatches_for_significant_category_regardless_of_confidence(self):
        """Findings with significant categories alert even with low confidence."""
        mock_client = _make_mock_client()
        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        job = {
            "id": "job-1",
            "user_id": USER_ID,
            "topic": "Acme Corp",
            "monitoring_type": "competitor",
            "importance": "normal",
        }
        findings = [
            _finding(
                "Acme Corp acquired startup XYZ for $10M",
                confidence=0.5,
                category="acquisition",
            ),
        ]

        with (
            patch(
                "app.services.monitoring_job_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.monitoring_job_service.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc._dispatch_monitoring_alert(USER_ID, job, findings)

        assert mock_dispatch.call_count >= 1

    @pytest.mark.asyncio
    async def test_alert_message_includes_competitor_and_change_type(self):
        """Alert message references the competitor name and change type."""
        mock_client = _make_mock_client()
        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        job = {
            "id": "job-1",
            "user_id": USER_ID,
            "topic": "Acme Corp",
            "monitoring_type": "competitor",
            "importance": "critical",
        }
        findings = [
            _finding(
                "Acme Corp has changed their pricing structure significantly",
                confidence=0.85,
                category="pricing_change",
            ),
        ]

        with (
            patch(
                "app.services.monitoring_job_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.monitoring_job_service.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc._dispatch_monitoring_alert(USER_ID, job, findings)

        assert mock_dispatch.call_count >= 1
        call_kwargs = mock_dispatch.call_args_list[0][1]
        assert "Acme Corp" in call_kwargs["message"]
        assert "pricing" in call_kwargs["message"].lower()

    @pytest.mark.asyncio
    async def test_uses_dispatch_proactive_alert_with_correct_alert_type(self):
        """dispatch_proactive_alert is called with alert_type='competitor.change'."""
        mock_client = _make_mock_client()
        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        job = {
            "id": "job-1",
            "user_id": USER_ID,
            "topic": "Acme Corp",
            "monitoring_type": "competitor",
            "importance": "critical",
        }
        findings = [
            _finding(
                "Acme Corp launched a new enterprise product suite",
                confidence=0.9,
                category="product_launch",
            ),
        ]

        with (
            patch(
                "app.services.monitoring_job_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.monitoring_job_service.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.monitoring_job_service import MonitoringJobService

            svc = MonitoringJobService()
            await svc._dispatch_monitoring_alert(USER_ID, job, findings)

        call_kwargs = mock_dispatch.call_args_list[0][1]
        assert call_kwargs["alert_type"] == "competitor.change"
        assert call_kwargs["link"] == "/research/monitoring"
        assert "change_type" in call_kwargs["metadata"]
