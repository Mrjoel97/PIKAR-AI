# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the weekly-report PDF export pipeline.

Covers:

- ``WeeklyReportService.format_report_as_narrative_pdf_data`` — six shape
  tests verifying the narrative_report PDF template payload.
- ``GET /briefing/weekly-report`` — three integration tests verifying the
  endpoint augments the briefing card with ``pdf.url`` / ``pdf.asset_id``,
  upserts a ``media_assets`` row with ``asset_type='pdf'``, and degrades
  gracefully when PDF generation fails.
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
    "GOOGLE_API_KEY": "fake-api-key",
}


def _sample_report(*, with_anomalies: bool = False) -> dict:
    report = {
        "period": {
            "start": "2026-05-04",
            "end": "2026-05-10",
            "label": "Week of May 4",
        },
        "revenue_summary": {
            "current": 12500.50,
            "previous": 10000.0,
            "change_pct": 25.01,
            "currency": "USD",
        },
        "top_metrics": [
            {
                "name": "Revenue",
                "value": 12500.50,
                "change_pct": 25.01,
                "trend": "up",
            },
            {
                "name": "Expenses",
                "value": 4200.0,
                "change_pct": -3.5,
                "trend": "down",
            },
        ],
        "anomalies": [],
        "executive_summary": "Revenue rose meaningfully week-over-week.",
        "generated_at": "2026-05-10T00:00:00+00:00",
    }
    if with_anomalies:
        report["anomalies"] = [
            {
                "metric": "Revenue",
                "expected": 10000.0,
                "actual": 12500.50,
                "severity": "medium",
            },
            {
                "metric": "Expenses",
                "expected": 4350.0,
                "actual": 4200.0,
                "severity": "high",
            },
        ]
    return report


def _make_service():
    """Return a WeeklyReportService with a stubbed Supabase client."""
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ),
    ):
        from app.services.weekly_report_service import WeeklyReportService

        svc = WeeklyReportService()
        _ = svc.client
        return svc


# ---------------------------------------------------------------------------
# Formatter shape tests (6)
# ---------------------------------------------------------------------------


class TestFormatReportAsNarrativePdfData:
    """Shape tests for ``format_report_as_narrative_pdf_data``."""

    def test_returns_required_top_level_keys(self):
        """Result must include subtitle, executive_summary, sections, appendix."""
        svc = _make_service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        for key in ("subtitle", "executive_summary", "sections", "appendix"):
            assert key in out, f"Missing key: {key}"

    def test_subtitle_includes_period_label_and_dates(self):
        """Subtitle contains the period label plus start/end dates."""
        svc = _make_service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        assert "Week of May 4" in out["subtitle"]
        assert "2026-05-04" in out["subtitle"]
        assert "2026-05-10" in out["subtitle"]

    def test_executive_summary_passthrough(self):
        """Executive summary is copied directly from the report."""
        svc = _make_service()
        report = _sample_report()
        out = svc.format_report_as_narrative_pdf_data(report)
        assert out["executive_summary"] == report["executive_summary"]

    def test_revenue_section_is_markdown_with_currency(self):
        """First section is the revenue summary rendered as markdown."""
        svc = _make_service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        sections = out["sections"]
        assert len(sections) >= 2
        revenue_section = sections[0]
        assert revenue_section["heading"] == "Revenue Summary"
        body = revenue_section["body_markdown"]
        assert "USD" in body
        assert "12,500.50" in body
        assert "10,000.00" in body
        # Markdown bullet syntax
        assert body.lstrip().startswith("- ")

    def test_metrics_section_is_markdown_table(self):
        """Key Metrics section is a pipe-delimited markdown table."""
        svc = _make_service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        metrics_section = next(
            s for s in out["sections"] if s["heading"] == "Key Metrics"
        )
        body = metrics_section["body_markdown"]
        # Markdown table separator + header
        assert "| Metric |" in body
        assert "| --- |" in body
        # Both metric rows present
        assert "Revenue" in body
        assert "Expenses" in body

    def test_anomalies_section_appended_only_when_present(self):
        """Anomalies section + appendix appear only when anomalies exist."""
        svc = _make_service()

        # No anomalies → no anomalies section, empty appendix
        out_no = svc.format_report_as_narrative_pdf_data(_sample_report())
        assert all(s["heading"] != "Anomalies" for s in out_no["sections"])
        assert out_no["appendix"] == ""

        # With anomalies → section appended and appendix populated
        out_yes = svc.format_report_as_narrative_pdf_data(
            _sample_report(with_anomalies=True)
        )
        anomalies_section = next(
            (s for s in out_yes["sections"] if s["heading"] == "Anomalies"), None
        )
        assert anomalies_section is not None
        body = anomalies_section["body_markdown"]
        assert "Revenue" in body
        assert "medium" in body
        assert "high" in body
        assert out_yes["appendix"]  # non-empty
        assert "%" in out_yes["appendix"]


# ---------------------------------------------------------------------------
# Endpoint integration tests (3)
# ---------------------------------------------------------------------------


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000099"


def _stub_widget(size: int = 4096, url: str = "https://signed.example/w.pdf"):
    return {
        "type": "document",
        "title": "Weekly Business Report",
        "data": {
            "documentUrl": url,
            "title": "Weekly Business Report",
            "fileType": "pdf",
            "sizeBytes": size,
            "templateName": "narrative_report",
        },
    }


class _StubWeeklyReportService:
    """Stub WeeklyReportService that returns deterministic data."""

    def __init__(self):
        self._report = _sample_report(with_anomalies=True)

    async def generate_weekly_report(self, user_id):  # noqa: ARG002
        return self._report

    def format_report_as_briefing_card(self, report):
        return {
            "type": "weekly_report",
            "title": "Weekly Business Report",
            "summary": report.get("executive_summary", ""),
            "generated_at": report.get("generated_at", ""),
            "sections": [{"id": "revenue", "label": "Revenue"}],
        }

    def format_report_as_narrative_pdf_data(self, report):  # noqa: ARG002
        return {
            "subtitle": "Week of May 4 — 2026-05-04 to 2026-05-10",
            "executive_summary": "stub",
            "sections": [{"heading": "Revenue Summary", "body_markdown": "x"}],
            "appendix": "",
        }


@pytest.fixture
def client_with_stubs(monkeypatch):
    """Boot the FastAPI app with auth + WeeklyReportService stubbed."""
    from fastapi.testclient import TestClient

    from app import fast_api_app
    import app.routers.briefing as briefing_router
    import app.routers.onboarding as onboarding_router

    monkeypatch.setattr(
        "app.services.weekly_report_service.WeeklyReportService",
        _StubWeeklyReportService,
    )

    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = (
        _override_user_id
    )
    try:
        yield TestClient(fast_api_app.app), briefing_router
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_weekly_report_response_includes_pdf_block(client_with_stubs, monkeypatch):
    """Response augments the briefing card with pdf.url and pdf.asset_id."""
    client, briefing_router = client_with_stubs

    # Stub DocumentService.generate_pdf to return a widget
    fake_widget = _stub_widget()
    mock_doc_service = MagicMock()
    mock_doc_service.generate_pdf = AsyncMock(return_value=fake_widget)

    # Stub media_assets upsert path
    captured = {}

    async def _fake_execute_async(query_builder, **_kwargs):
        captured["called"] = True
        return MagicMock(data=[])

    with (
        patch(
            "app.services.document_service.DocumentService",
            return_value=mock_doc_service,
        ),
        patch("app.routers.briefing.get_service_client", return_value=MagicMock()),
        patch(
            "app.services.supabase_async.execute_async",
            side_effect=_fake_execute_async,
        ),
    ):
        resp = client.get("/briefing/weekly-report")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "pdf" in body, f"pdf block missing: {body}"
    assert body["pdf"]["url"] == fake_widget["data"]["documentUrl"]
    assert body["pdf"]["asset_id"]
    # Back-compat top-level field
    assert body["pdf_url"] == fake_widget["data"]["documentUrl"]
    # Card shape preserved
    assert body["type"] == "weekly_report"
    assert body["title"] == "Weekly Business Report"


def test_weekly_report_upserts_media_assets_row_for_pdf(
    client_with_stubs, monkeypatch
):
    """media_assets row is upserted with asset_type='pdf' and metadata.kind."""
    client, _ = client_with_stubs

    fake_widget = _stub_widget(size=2048)
    mock_doc_service = MagicMock()
    mock_doc_service.generate_pdf = AsyncMock(return_value=fake_widget)

    upsert_payloads: list[dict] = []

    # Capture the dict passed to .upsert() on the media_assets table
    fake_supabase = MagicMock()
    fake_table = MagicMock()
    fake_supabase.table.return_value = fake_table

    def _table_upsert(payload, on_conflict=None):  # noqa: ARG001
        upsert_payloads.append(payload)
        return MagicMock()

    fake_table.upsert.side_effect = _table_upsert

    async def _fake_execute_async(query_builder, **_kwargs):  # noqa: ARG001
        return MagicMock(data=[])

    with (
        patch(
            "app.services.document_service.DocumentService",
            return_value=mock_doc_service,
        ),
        patch(
            "app.routers.briefing.get_service_client",
            return_value=fake_supabase,
        ),
        patch(
            "app.services.supabase_async.execute_async",
            side_effect=_fake_execute_async,
        ),
    ):
        resp = client.get("/briefing/weekly-report")

    assert resp.status_code == 200, resp.text
    assert upsert_payloads, "media_assets.upsert was not called"
    # Find the weekly_report payload (there should be exactly one for this flow)
    weekly_payloads = [
        p for p in upsert_payloads if (p.get("metadata") or {}).get("kind") == "weekly_report"
    ]
    assert weekly_payloads, f"No weekly_report upsert: {upsert_payloads}"
    payload = weekly_payloads[0]
    assert payload["asset_type"] == "pdf"
    assert payload["metadata"]["kind"] == "weekly_report"
    assert "period" in payload["metadata"]
    assert payload["file_url"] == fake_widget["data"]["documentUrl"]


def test_weekly_report_pdf_failure_does_not_break_response(
    client_with_stubs, monkeypatch
):
    """If PDF generation raises, the endpoint still returns the card."""
    client, _ = client_with_stubs

    mock_doc_service = MagicMock()
    mock_doc_service.generate_pdf = AsyncMock(
        side_effect=RuntimeError("weasyprint exploded")
    )

    with (
        patch(
            "app.services.document_service.DocumentService",
            return_value=mock_doc_service,
        ),
        patch("app.routers.briefing.get_service_client", return_value=MagicMock()),
    ):
        resp = client.get("/briefing/weekly-report")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Card payload remains intact, no pdf field
    assert body["type"] == "weekly_report"
    assert body["title"] == "Weekly Business Report"
    assert "pdf" not in body
    assert "pdf_url" not in body
