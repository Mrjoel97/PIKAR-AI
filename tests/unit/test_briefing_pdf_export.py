# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the weekly-report PDF export attached to ``/briefing/weekly-report``.

Covers:

- ``format_report_as_narrative_pdf_data`` produces the narrative-template
  schema (subtitle / executive_summary / sections / appendix).
- ``GET /briefing/weekly-report`` response includes ``pdf.url`` and
  ``pdf.asset_id`` plus a top-level ``pdf_url`` for back-compat.
- A ``media_assets`` row is upserted with ``asset_type="pdf"`` and
  ``metadata.kind="weekly_report"``.
- PDF generation failures degrade gracefully — the response still includes
  the briefing card and simply omits the ``pdf`` field.
"""

from __future__ import annotations

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure Supabase env vars are present before any router import that pulls
# AdminService (which validates them eagerly on construction).
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-test-key")

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router.
# ---------------------------------------------------------------------------

CURRENT_USER = "user-abc"


async def _default_get_current_user_id() -> str:  # noqa: RUF029
    """Fake dependency that returns the test user."""
    return CURRENT_USER


def _stub_module(path: str, **attrs: object) -> None:
    if path not in sys.modules:
        mod = types.ModuleType(path)
        for name, val in attrs.items():
            setattr(mod, name, val)
        sys.modules[path] = mod


# Rate limiter — disable actual limiting for unit tests
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_limiter_mod = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *a, **kw: (lambda fn: fn)
    _mock_limiter_mod.limiter = _mock_limiter
    _mock_limiter_mod.get_user_persona_limit = MagicMock(return_value="100/minute")
    _mock_limiter_mod._parse_limit_int = MagicMock(return_value=100)
    _mock_limiter_mod.build_rate_limit_headers = MagicMock(return_value={})
    _mock_limiter_mod.redis_sliding_window_check = AsyncMock(
        return_value=(True, 0, 0)
    )
    sys.modules["app.middleware.rate_limiter"] = _mock_limiter_mod


# ---------------------------------------------------------------------------
# Sample report fixture
# ---------------------------------------------------------------------------


def _sample_report() -> dict:
    return {
        "period": {
            "start": "2026-04-07",
            "end": "2026-04-13",
            "label": "Week of Apr 7",
        },
        "revenue_summary": {
            "current": 3500.0,
            "previous": 2000.0,
            "change_pct": 75.0,
            "currency": "USD",
        },
        "top_metrics": [
            {"name": "Revenue", "value": 3500.0, "change_pct": 75.0, "trend": "up"},
            {"name": "Expenses", "value": 1200.0, "change_pct": 5.0, "trend": "stable"},
        ],
        "anomalies": [
            {
                "metric": "Revenue",
                "expected": 2000.0,
                "actual": 3500.0,
                "severity": "high",
            }
        ],
        "executive_summary": "Revenue up 75% this week.",
        "generated_at": "2026-04-13T10:00:00Z",
    }


# ---------------------------------------------------------------------------
# 1. Narrative-PDF data formatter shape (independent unit test)
# ---------------------------------------------------------------------------


class TestFormatReportAsNarrativePdfData:
    """Schema-level checks for the narrative-template payload."""

    def _service(self):
        fake_env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "service-role-test-key",
            "SUPABASE_ANON_KEY": "anon-test-key",
        }
        with (
            patch.dict("os.environ", fake_env, clear=False),
            patch(
                "app.services.supabase.get_service_client",
                return_value=MagicMock(),
            ),
        ):
            from app.services.weekly_report_service import WeeklyReportService

            svc = WeeklyReportService()
            _ = svc.client
            return svc

    def test_returns_required_top_level_keys(self):
        svc = self._service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        assert "subtitle" in out
        assert "executive_summary" in out
        assert "sections" in out
        assert "appendix" in out

    def test_subtitle_uses_period_label(self):
        svc = self._service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        assert out["subtitle"] == "Week of Apr 7"

    def test_executive_summary_passes_through(self):
        svc = self._service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        assert out["executive_summary"] == "Revenue up 75% this week."

    def test_sections_include_revenue_and_metrics_and_anomalies(self):
        svc = self._service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        headings = [s.get("heading") for s in out["sections"]]
        assert "Revenue Summary" in headings
        assert "Key Metrics" in headings
        assert "Anomalies" in headings
        for section in out["sections"]:
            assert "body_markdown" in section
            assert isinstance(section["body_markdown"], str)
            assert section["body_markdown"].strip()

    def test_anomalies_section_omitted_when_none(self):
        svc = self._service()
        report = _sample_report()
        report["anomalies"] = []
        out = svc.format_report_as_narrative_pdf_data(report)
        headings = [s.get("heading") for s in out["sections"]]
        assert "Anomalies" not in headings

    def test_appendix_includes_period_dates(self):
        svc = self._service()
        out = svc.format_report_as_narrative_pdf_data(_sample_report())
        assert "2026-04-07" in out["appendix"]
        assert "2026-04-13" in out["appendix"]


# ---------------------------------------------------------------------------
# 2. Endpoint integration: PDF attached, media_assets tagged, failure mode
# ---------------------------------------------------------------------------


@pytest.fixture()
def briefing_app(monkeypatch):
    """Build a minimal FastAPI app that mounts only the briefing router."""
    # Import lazily so the rate-limiter stub above is in place.
    import app.routers.briefing as briefing_module

    # The endpoint calls the real WeeklyReportService; patch its methods so we
    # don't need to mock Supabase. ``generate_weekly_report`` is async.
    sample = _sample_report()

    monkeypatch.setattr(
        briefing_module,
        # The endpoint imports inside the function body; patch the source class
        # directly via its module.
        "logger",
        briefing_module.logger,
    )

    from app.services.weekly_report_service import WeeklyReportService

    monkeypatch.setattr(
        WeeklyReportService,
        "generate_weekly_report",
        AsyncMock(return_value=sample),
    )
    # Use real format_report_as_briefing_card and
    # format_report_as_narrative_pdf_data implementations.

    app = FastAPI()
    app.include_router(briefing_module.router)
    app.dependency_overrides[briefing_module.get_current_user_id] = (
        _default_get_current_user_id
    )
    return briefing_module, TestClient(app, raise_server_exceptions=False)


def _make_widget(signed_url: str) -> dict:
    return {
        "type": "document",
        "title": "Weekly Business Report — Week of Apr 7",
        "data": {
            "documentUrl": signed_url,
            "title": "Weekly Business Report — Week of Apr 7",
            "fileType": "pdf",
            "sizeBytes": 4096,
            "templateName": "narrative_report",
        },
        "dismissible": True,
        "expandable": False,
    }


class _CapturingSupabase:
    """Capture media_assets upsert payloads issued through ``execute_async``."""

    def __init__(self, asset_id: str = "asset-pdf-1"):
        self.asset_id = asset_id
        self.upsert_payloads: list[dict] = []
        self.lookup_calls = 0

    def table(self, name: str):
        assert name == "media_assets", f"unexpected table call: {name}"
        return _CapturingTable(self)


class _CapturingTable:
    def __init__(self, parent: _CapturingSupabase):
        self.parent = parent
        self._mode: str | None = None
        self._payload: dict | None = None

    # Lookup chain --------------------------------------------------------
    def select(self, *_a, **_kw):
        self._mode = "select"
        return self

    def eq(self, *_a, **_kw):
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    # Upsert chain --------------------------------------------------------
    def upsert(self, payload: dict, on_conflict: str | None = None):
        self._mode = "upsert"
        self._payload = payload
        return self


async def _fake_execute_async(query, *, op_name: str = ""):
    """Stand-in for ``app.services.supabase_async.execute_async``.

    Routes both the lookup (``select``) and the tag (``upsert``) calls through
    a single capturing object so the test can assert on the upsert payload.
    """
    parent: _CapturingSupabase = query.parent
    if query._mode == "select":
        parent.lookup_calls += 1
        return SimpleNamespace(data=[{"id": parent.asset_id}])
    if query._mode == "upsert":
        parent.upsert_payloads.append(query._payload)
        return SimpleNamespace(data=[query._payload])
    return SimpleNamespace(data=[])


def test_weekly_report_endpoint_includes_pdf_field(briefing_app):
    """Endpoint response includes ``pdf.url`` and ``pdf.asset_id``."""
    briefing_module, client = briefing_app
    signed_url = "https://signed.example.com/abc.pdf"
    capture = _CapturingSupabase(asset_id="asset-pdf-1")

    fake_doc_service = MagicMock()
    fake_doc_service.generate_pdf = AsyncMock(return_value=_make_widget(signed_url))

    with (
        patch(
            "app.services.document_service.DocumentService",
            return_value=fake_doc_service,
        ),
        patch(
            "app.routers.briefing.get_service_client",
            return_value=capture,
        ),
        patch(
            "app.services.supabase_async.execute_async",
            side_effect=_fake_execute_async,
        ),
        patch(
            "app.services.request_context.get_current_session_id",
            return_value="sess-42",
        ),
    ):
        resp = client.get("/briefing/weekly-report")

    assert resp.status_code == 200
    body = resp.json()

    # Card shape preserved
    assert body["type"] == "weekly_report"
    assert body["title"] == "Weekly Business Report"
    assert "sections" in body

    # PDF field added
    assert "pdf" in body
    assert body["pdf"]["url"] == signed_url
    assert body["pdf"]["asset_id"] == "asset-pdf-1"
    assert body["pdf_url"] == signed_url  # back-compat alias

    # generate_pdf was called with the narrative template
    fake_doc_service.generate_pdf.assert_awaited_once()
    kwargs = fake_doc_service.generate_pdf.await_args.kwargs
    assert kwargs["template_name"] == "narrative_report"
    assert kwargs["user_id"] == CURRENT_USER


def test_weekly_report_endpoint_tags_media_asset_with_kind(briefing_app):
    """A media_assets row is upserted with asset_type=pdf and kind=weekly_report."""
    briefing_module, client = briefing_app
    signed_url = "https://signed.example.com/xyz.pdf"
    capture = _CapturingSupabase(asset_id="asset-pdf-99")

    fake_doc_service = MagicMock()
    fake_doc_service.generate_pdf = AsyncMock(return_value=_make_widget(signed_url))

    with (
        patch(
            "app.services.document_service.DocumentService",
            return_value=fake_doc_service,
        ),
        patch(
            "app.routers.briefing.get_service_client",
            return_value=capture,
        ),
        patch(
            "app.services.supabase_async.execute_async",
            side_effect=_fake_execute_async,
        ),
        patch(
            "app.services.request_context.get_current_session_id",
            return_value="sess-42",
        ),
    ):
        resp = client.get("/briefing/weekly-report")

    assert resp.status_code == 200

    # Exactly one tagging upsert should have been issued.
    assert len(capture.upsert_payloads) == 1
    payload = capture.upsert_payloads[0]
    assert payload["asset_type"] == "pdf"
    assert payload["id"] == "asset-pdf-99"
    assert payload["user_id"] == CURRENT_USER
    metadata = payload["metadata"]
    assert metadata["kind"] == "weekly_report"
    assert metadata["session_id"] == "sess-42"
    assert metadata["period"]["start"] == "2026-04-07"
    assert metadata["period"]["end"] == "2026-04-13"


def test_weekly_report_endpoint_survives_pdf_failure(briefing_app):
    """If PDF generation raises, the endpoint still returns the briefing card."""
    briefing_module, client = briefing_app

    fake_doc_service = MagicMock()
    fake_doc_service.generate_pdf = AsyncMock(
        side_effect=RuntimeError("weasyprint exploded")
    )

    with (
        patch(
            "app.services.document_service.DocumentService",
            return_value=fake_doc_service,
        ),
        patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.request_context.get_current_session_id",
            return_value="sess-42",
        ),
    ):
        resp = client.get("/briefing/weekly-report")

    assert resp.status_code == 200
    body = resp.json()

    # Card payload is intact
    assert body["type"] == "weekly_report"
    assert body["title"] == "Weekly Business Report"
    assert "sections" in body
    assert body["summary"] == "Revenue up 75% this week."

    # No PDF field on failure
    assert "pdf" not in body
    assert "pdf_url" not in body
