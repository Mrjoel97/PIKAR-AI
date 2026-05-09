# Copyright (c) 2024-2026 Pikar AI. All rights reserved.

"""Unit tests for REGISTRY-06 typed PDF payload schemas.

These TypedDicts are typing-only; runtime behaviour of
``generate_pdf_report`` is unchanged. The tests assert that a valid payload
for each template is accepted and dispatched correctly to the underlying
``DocumentService.generate_pdf``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# Each test payload uses the discriminated ``template`` field so the static
# typing matches the TypedDict member; we still pass them through as plain
# dicts because TypedDict is a typing-only construct.
SAMPLE_PAYLOADS: dict[str, dict] = {
    "financial_report": {
        "template": "financial_report",
        "revenue": 100000.0,
        "expenses": 70000.0,
        "net_income": 30000.0,
        "period": "Q4 2025",
        "highlights": ["Revenue up 12% QoQ"],
    },
    "project_proposal": {
        "template": "project_proposal",
        "project_name": "Phoenix",
        "objectives": ["Migrate auth"],
        "timeline": "6 weeks",
        "budget": 50000.0,
        "team": ["Alice", "Bob"],
    },
    "meeting_summary": {
        "template": "meeting_summary",
        "meeting_title": "Weekly Standup",
        "date": "2026-05-09",
        "attendees": ["Alice"],
        "agenda": ["Status updates"],
        "decisions": [],
        "action_items": ["Ship the manifest"],
    },
    "competitive_analysis": {
        "template": "competitive_analysis",
        "company": "Acme",
        "competitors": [
            {"name": "Foo", "strengths": ["scale"], "weaknesses": ["price"]},
        ],
        "market_position": "Leader",
        "recommendations": ["Lean into product velocity"],
    },
    "sales_proposal": {
        "template": "sales_proposal",
        "client_name": "Acme",
        "project_name": "Implementation",
        "objectives": ["Deploy"],
        "line_items": [{"name": "Setup", "amount": 10000}],
        "timeline": "4 weeks",
        "total": 10000.0,
    },
    "narrative_report": {
        "template": "narrative_report",
        "subtitle": "Deep dive",
        "executive_summary": "Markdown body",
        "sections": [
            {"heading": "Intro", "body_markdown": "Hello"},
        ],
    },
}


# ---------------------------------------------------------------------------
# TypedDict shape checks
# ---------------------------------------------------------------------------


class TestTypedDictShapes:
    """Static TypedDicts are typing-only; we just verify they import."""

    def test_imports_typeddicts(self):
        from app.agents.tools.document_gen import (
            CompetitiveAnalysisData,
            FinancialReportData,
            MeetingSummaryData,
            NarrativeReportData,
            PdfReportData,
            ProjectProposalData,
            SalesProposalData,
        )

        # Sanity: every TypedDict has __required_keys__ / __optional_keys__.
        for cls in (
            FinancialReportData,
            ProjectProposalData,
            MeetingSummaryData,
            CompetitiveAnalysisData,
            SalesProposalData,
            NarrativeReportData,
        ):
            assert hasattr(cls, "__annotations__")
        # PdfReportData is a Union; just check it resolves.
        assert PdfReportData is not None

    @pytest.mark.parametrize("template,payload", list(SAMPLE_PAYLOADS.items()))
    def test_each_payload_has_expected_template_field(self, template, payload):
        assert payload["template"] == template


# ---------------------------------------------------------------------------
# Runtime dispatch (each member dict is accepted)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("template,payload", list(SAMPLE_PAYLOADS.items()))
async def test_generate_pdf_report_accepts_typed_payload(template, payload):
    """generate_pdf_report should dispatch each typed payload to DocumentService."""
    from app.agents.tools import document_gen

    fake_widget = {"type": "document", "url": "https://example.test/doc.pdf"}

    with (
        patch.object(document_gen, "_get_user_id", return_value="user-1"),
        patch.object(document_gen, "_get_session_id", return_value="sess-1"),
        patch("app.services.document_service.DocumentService") as svc_cls,
    ):
        svc_instance = svc_cls.return_value
        svc_instance.generate_pdf = AsyncMock(return_value=fake_widget)

        result = await document_gen.generate_pdf_report(
            template=template,
            data=dict(payload),
            title="Test Doc",
        )

        assert result == {"status": "success", "widget": fake_widget}
        svc_instance.generate_pdf.assert_awaited_once()
        kwargs = svc_instance.generate_pdf.await_args.kwargs
        assert kwargs["template_name"] == template
        assert kwargs["data"]["template"] == template


@pytest.mark.asyncio
async def test_generate_pdf_report_rejects_invalid_template():
    from app.agents.tools import document_gen

    with (
        patch.object(document_gen, "_get_user_id", return_value="user-1"),
        patch.object(document_gen, "_get_session_id", return_value="sess-1"),
    ):
        result = await document_gen.generate_pdf_report(
            template="not_a_real_template",
            data={"template": "not_a_real_template"},
        )

    assert result["status"] == "error"
    assert "Invalid template" in result["message"]
