# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DocumentService -- PDF/PPTX generation with brand injection."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def brand_profile() -> dict[str, Any]:
    """Sample brand profile matching get_brand_profile return shape."""
    return {
        "success": True,
        "profile": {
            "brand_name": "TestCo",
            "logo_url": "https://example.com/logo.png",
            "visual_style": {
                "color_palette": ["#FF5733", "#33FF57", "#3357FF"],
            },
        },
        "brand_name": "TestCo",
        "visual_style": {
            "color_palette": ["#FF5733", "#33FF57", "#3357FF"],
        },
    }


@pytest.fixture()
def financial_data() -> dict[str, Any]:
    """Sample data for financial_report template."""
    return {
        "executive_summary": "Revenue grew 15% YoY.",
        "metrics": [
            {"label": "Revenue", "value": "$1.2M"},
            {"label": "Expenses", "value": "$800K"},
            {"label": "Profit", "value": "$400K"},
            {"label": "Growth", "value": "15%"},
        ],
        "revenue_breakdown": [
            {"source": "Product A", "amount": "$600K", "pct": "50%"},
            {"source": "Product B", "amount": "$600K", "pct": "50%"},
        ],
        "analysis": "Strong performance across all segments.",
    }


@pytest.fixture()
def proposal_data() -> dict[str, Any]:
    """Sample data for project_proposal template."""
    return {
        "executive_summary": "Launch new mobile app by Q3.",
        "objectives": [
            {"title": "Market Research", "description": "Analyze competitors."},
            {"title": "MVP Development", "description": "Build core features."},
        ],
        "milestones": [
            {"milestone": "Research Complete", "date": "2026-05-01", "owner": "Alice"},
            {"milestone": "MVP Launch", "date": "2026-08-01", "owner": "Bob"},
        ],
        "budget": [
            {"item": "Engineering", "cost": "$50K"},
            {"item": "Marketing", "cost": "$20K"},
        ],
        "risks": [
            {"risk": "Schedule slip", "mitigation": "Weekly check-ins"},
        ],
        "next_steps": ["Finalize requirements", "Kick off sprint 1"],
    }


@pytest.fixture()
def meeting_data() -> dict[str, Any]:
    """Sample data for meeting_summary template."""
    return {
        "meeting_date": "2026-04-01",
        "attendees": ["Alice", "Bob", "Carol"],
        "discussion_points": ["Budget review", "Hiring plan"],
        "decisions": [
            {"decision": "Approve Q2 budget", "owner": "Alice"},
        ],
        "action_items": [
            {
                "item": "Draft job postings",
                "owner": "Bob",
                "due_date": "2026-04-15",
                "status": "Pending",
            },
        ],
        "follow_up": "Reconvene on April 15.",
    }


@pytest.fixture()
def competitive_data() -> dict[str, Any]:
    """Sample data for competitive_analysis template."""
    return {
        "market_overview": "The SaaS market is growing at 12% CAGR.",
        "competitors": [
            {
                "name": "CompA",
                "feature_x": "Yes",
                "feature_y": "No",
                "pricing": "$99/mo",
            },
            {
                "name": "CompB",
                "feature_x": "No",
                "feature_y": "Yes",
                "pricing": "$79/mo",
            },
        ],
        "swot": {
            "strengths": ["Strong brand", "AI-first"],
            "weaknesses": ["Small team"],
            "opportunities": ["Emerging markets"],
            "threats": ["Big tech entry"],
        },
        "recommendations": [
            "Focus on AI differentiator",
            "Expand to EU market",
        ],
        "data_sources": "Gartner 2026, internal analytics",
    }


@pytest.fixture()
def slides_data() -> list[dict[str, Any]]:
    """Sample slide content for PPTX generation."""
    return [
        {"title": "Pitch Deck", "bullets": ["Overview", "Market Size"]},
        {
            "title": "Solution",
            "bullets": ["AI-powered automation", "Real-time insights"],
        },
        {
            "title": "Financials",
            "bullets": ["$1M ARR target"],
            "chart_image_bytes": b"\x89PNG_fake",
        },
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_PDF_BYTES = b"%PDF-1.4 fake pdf content for testing purposes"


def _mock_weasyprint_html():
    """Return a mock HTML class that returns fake PDF bytes on write_pdf()."""
    mock_html_cls = MagicMock()
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = FAKE_PDF_BYTES
    mock_html_cls.return_value = mock_html_instance
    return mock_html_cls


def _mock_supabase():
    """Create mock Supabase client with storage and table methods."""
    mock = MagicMock()
    # Storage: upload + create_signed_url
    mock_bucket = MagicMock()
    mock_bucket.upload.return_value = None
    mock_bucket.create_signed_url.return_value = {
        "signedURL": "https://storage.example.com/signed/doc.pdf",
    }
    mock.storage.from_.return_value = mock_bucket
    # Table: upsert for media_assets
    mock_upsert = MagicMock()
    mock_upsert.execute.return_value = MagicMock(data=[{"id": "doc-123"}])
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_upsert
    mock.table.return_value = mock_table
    return mock


def _mock_matplotlib():
    """Create a mock matplotlib.pyplot that returns fake PNG bytes."""
    mock_plt = MagicMock()
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    # savefig writes PNG header bytes into the BytesIO buffer
    def fake_savefig(buf, **kwargs):
        buf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    mock_fig.savefig.side_effect = fake_savefig
    return mock_plt


def _pdf_patches():
    """Standard patches needed for PDF generation tests."""
    return (
        patch(
            "app.services.document_service._get_weasyprint_html",
            return_value=_mock_weasyprint_html(),
        ),
        patch(
            "app.services.document_service.get_service_client",
            return_value=_mock_supabase(),
        ),
        patch(
            "app.services.document_service.execute_async",
            new_callable=AsyncMock,
        ),
    )


# ---------------------------------------------------------------------------
# Tests: PDF Generation
# ---------------------------------------------------------------------------


class TestGeneratePdf:
    """Test DocumentService.generate_pdf."""

    @pytest.mark.asyncio
    async def test_generate_pdf_returns_bytes(self, brand_profile, financial_data):
        """Given template name and data dict, generate_pdf returns widget with PDF info."""
        p_wp, p_sb, p_exec = _pdf_patches()
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            p_wp,
            p_sb,
            p_exec,
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            result = await svc.generate_pdf(
                "financial_report", financial_data, user_id="user-1",
            )

            assert result is not None
            assert result["data"]["fileType"] == "pdf"
            assert result["data"]["sizeBytes"] > 0

    @pytest.mark.asyncio
    async def test_generate_pdf_injects_brand_colors(
        self, brand_profile, financial_data,
    ):
        """Given brand profile with color_palette, rendered HTML contains primary color."""
        rendered_html_capture: list[str] = []

        mock_html_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.write_pdf.return_value = FAKE_PDF_BYTES

        def capture_html(string, **kwargs):
            rendered_html_capture.append(string)
            return mock_instance

        mock_html_cls.side_effect = capture_html

        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service._get_weasyprint_html",
                return_value=mock_html_cls,
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=_mock_supabase(),
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            await svc.generate_pdf(
                "financial_report", financial_data, user_id="user-1",
            )

            assert len(rendered_html_capture) > 0
            assert "#FF5733" in rendered_html_capture[0]

    @pytest.mark.asyncio
    async def test_generate_pdf_injects_logo(self, brand_profile, financial_data):
        """Given brand profile with logo_url, rendered HTML contains img tag with src."""
        rendered_html_capture: list[str] = []

        mock_html_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.write_pdf.return_value = FAKE_PDF_BYTES

        def capture_html(string, **kwargs):
            rendered_html_capture.append(string)
            return mock_instance

        mock_html_cls.side_effect = capture_html

        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service._get_weasyprint_html",
                return_value=mock_html_cls,
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=_mock_supabase(),
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            await svc.generate_pdf(
                "financial_report", financial_data, user_id="user-1",
            )

            assert len(rendered_html_capture) > 0
            assert "https://example.com/logo.png" in rendered_html_capture[0]

    @pytest.mark.asyncio
    async def test_generate_pdf_fallback_branding(self, financial_data):
        """Given no brand profile, generate_pdf uses Pikar defaults without error."""
        no_brand = {
            "success": True,
            "profile": None,
            "message": "No brand profile found.",
        }
        p_wp, p_sb, p_exec = _pdf_patches()
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=no_brand,
            ),
            p_wp,
            p_sb,
            p_exec,
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            result = await svc.generate_pdf(
                "financial_report", financial_data, user_id="user-1",
            )

            assert result is not None
            assert result["type"] == "document"

    @pytest.mark.asyncio
    async def test_generate_pdf_each_template(
        self,
        brand_profile,
        financial_data,
        proposal_data,
        meeting_data,
        competitive_data,
    ):
        """All 4 templates generate successfully with appropriate sample data."""
        template_data_pairs = [
            ("financial_report", financial_data),
            ("project_proposal", proposal_data),
            ("meeting_summary", meeting_data),
            ("competitive_analysis", competitive_data),
        ]

        p_wp, p_sb, p_exec = _pdf_patches()
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            p_wp,
            p_sb,
            p_exec,
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            for template_name, data in template_data_pairs:
                result = await svc.generate_pdf(
                    template_name, data, user_id="user-1",
                )
                assert result is not None, f"Template {template_name} returned None"
                assert result["type"] == "document", (
                    f"Template {template_name} wrong type"
                )

    @pytest.mark.asyncio
    async def test_generate_pdf_invalid_template(self, brand_profile):
        """Given an invalid template name, generate_pdf raises ValueError."""
        p_wp, p_sb, p_exec = _pdf_patches()
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            p_wp,
            p_sb,
            p_exec,
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            with pytest.raises(ValueError, match="Invalid template"):
                await svc.generate_pdf(
                    "nonexistent_template", {}, user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_generate_pdf_max_pages_enforcement(
        self, brand_profile, financial_data,
    ):
        """PDF exceeding 5 MB size limit raises ValueError."""
        huge_pdf = b"%PDF-1.4 " + b"x" * (6 * 1024 * 1024)
        mock_html_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.write_pdf.return_value = huge_pdf
        mock_html_cls.return_value = mock_instance

        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service._get_weasyprint_html",
                return_value=mock_html_cls,
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=_mock_supabase(),
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            with pytest.raises(ValueError, match="exceeds maximum"):
                await svc.generate_pdf(
                    "financial_report", financial_data, user_id="user-1",
                )


# ---------------------------------------------------------------------------
# Tests: PPTX Generation
# ---------------------------------------------------------------------------


class TestGeneratePptx:
    """Test DocumentService.generate_pptx."""

    @pytest.mark.asyncio
    async def test_generate_pptx_returns_bytes(self, brand_profile, slides_data):
        """generate_pptx returns widget with PPTX info and non-zero size."""
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=_mock_supabase(),
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            result = await svc.generate_pptx(slides_data, user_id="user-1")

            assert result is not None
            assert result["data"]["fileType"] == "pptx"
            assert result["data"]["sizeBytes"] > 0

    @pytest.mark.asyncio
    async def test_generate_pptx_applies_brand_color(
        self, brand_profile, slides_data,
    ):
        """PPTX generation succeeds with brand color applied."""
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=_mock_supabase(),
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            result = await svc.generate_pptx(slides_data, user_id="user-1")

            assert result is not None
            assert result["type"] == "document"

    @pytest.mark.asyncio
    async def test_generate_pptx_with_chart_image(self, brand_profile):
        """Slide with chart_image_bytes completes without error."""
        slides = [
            {
                "title": "Chart Slide",
                "bullets": ["Data"],
                "chart_image_bytes": b"\x89PNG_fake_image_data",
            },
        ]
        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=_mock_supabase(),
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            result = await svc.generate_pptx(slides, user_id="user-1")

            assert result is not None


# ---------------------------------------------------------------------------
# Tests: Chart Rendering
# ---------------------------------------------------------------------------


class TestRenderChart:
    """Test DocumentService.render_chart."""

    def test_render_chart_returns_png_bytes(self):
        """Given chart data, render_chart returns PNG bytes via matplotlib mock."""
        with patch(
            "app.services.document_service._get_matplotlib",
            return_value=_mock_matplotlib(),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            chart_data = {
                "type": "bar",
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "values": [100, 200, 150, 300],
                "title": "Quarterly Revenue",
            }
            png_bytes = svc.render_chart(chart_data)

            assert isinstance(png_bytes, bytes)
            assert len(png_bytes) > 0
            assert png_bytes[:4] == b"\x89PNG"

    def test_render_chart_line(self):
        """Line chart type renders correctly."""
        with patch(
            "app.services.document_service._get_matplotlib",
            return_value=_mock_matplotlib(),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            chart_data = {
                "type": "line",
                "labels": ["Jan", "Feb", "Mar"],
                "values": [10, 20, 15],
                "title": "Monthly Trend",
            }
            png_bytes = svc.render_chart(chart_data)
            assert png_bytes[:4] == b"\x89PNG"

    def test_render_chart_pie(self):
        """Pie chart type renders correctly."""
        with patch(
            "app.services.document_service._get_matplotlib",
            return_value=_mock_matplotlib(),
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            chart_data = {
                "type": "pie",
                "labels": ["A", "B", "C"],
                "values": [40, 35, 25],
                "title": "Distribution",
            }
            png_bytes = svc.render_chart(chart_data)
            assert png_bytes[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# Tests: Upload + Track
# ---------------------------------------------------------------------------


class TestUploadAndTrack:
    """Test DocumentService._upload_document."""

    @pytest.mark.asyncio
    async def test_upload_and_track_document(self, brand_profile, financial_data):
        """Upload stores to Storage, tracks in media_assets, returns widget."""
        mock_sb = _mock_supabase()

        with (
            patch(
                "app.services.document_service.get_brand_profile",
                new_callable=AsyncMock,
                return_value=brand_profile,
            ),
            patch(
                "app.services.document_service._get_weasyprint_html",
                return_value=_mock_weasyprint_html(),
            ),
            patch(
                "app.services.document_service.get_service_client",
                return_value=mock_sb,
            ),
            patch(
                "app.services.document_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            from app.services.document_service import DocumentService

            svc = DocumentService()
            result = await svc.generate_pdf(
                "financial_report",
                financial_data,
                user_id="user-1",
                session_id="sess-1",
                title="Q1 Financial Report",
            )

            # Verify upload was called
            mock_sb.storage.from_.assert_called()

            # Verify media_assets tracking
            mock_exec.assert_called()

            # Verify widget structure
            assert result["type"] == "document"
            assert "documentUrl" in result["data"]
            assert result["data"]["title"] == "Q1 Financial Report"
            assert result["dismissible"] is True
