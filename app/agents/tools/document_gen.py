# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Document generation agent tools -- PDF reports and PowerPoint pitch decks.

Provides two agent-callable functions that wire into the DocumentService
created in Phase 40 Plan 02.  Generated documents are uploaded to Supabase
Storage and returned as chat widgets with download URLs.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


def _get_session_id() -> str | None:
    """Extract the current session ID from the request-scoped context."""
    from app.services.request_context import get_current_session_id

    return get_current_session_id()


# ---------------------------------------------------------------------------
# PDF Report tool
# ---------------------------------------------------------------------------

async def generate_pdf_report(
    template: str,
    data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a branded PDF report and return a download widget.

    Renders an HTML template with the provided data, converts to PDF using
    weasyprint, and uploads to storage.  The result is a document widget
    that the frontend renders as a download card.

    Templates and expected data:

    - **financial_report**: ``revenue`` (float), ``expenses`` (float),
      ``net_income`` (float), ``period`` (str), ``highlights`` (list[str]),
      optionally ``chart_data`` (list of chart dicts).
    - **project_proposal**: ``project_name`` (str), ``objectives`` (list[str]),
      ``timeline`` (str), ``budget`` (float), ``team`` (list[str]).
    - **meeting_summary**: ``meeting_title`` (str), ``date`` (str),
      ``attendees`` (list[str]), ``agenda`` (list[str]),
      ``decisions`` (list[str]), ``action_items`` (list[str]).
    - **competitive_analysis**: ``company`` (str),
      ``competitors`` (list[dict] with name/strengths/weaknesses),
      ``market_position`` (str), ``recommendations`` (list[str]).

    Args:
        template: Template name -- one of ``financial_report``,
            ``project_proposal``, ``meeting_summary``, ``competitive_analysis``.
        data: Structured content dict matching the template schema above.
        title: Optional human-readable document title.

    Returns:
        Widget dict with document download information.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"status": "error", "message": "No authenticated user found."}

    session_id = _get_session_id()

    from app.services.document_service import VALID_TEMPLATES, DocumentService

    if template not in VALID_TEMPLATES:
        return {
            "status": "error",
            "message": (
                f"Invalid template '{template}'. "
                f"Must be one of: {', '.join(VALID_TEMPLATES)}"
            ),
        }

    service = DocumentService()
    try:
        widget = await service.generate_pdf(
            template_name=template,
            data=data,
            user_id=user_id,
            session_id=session_id,
            title=title,
        )
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        logger.exception("PDF generation failed")
        return {"status": "error", "message": f"PDF generation failed: {exc}"}

    return {"status": "success", "widget": widget}


# ---------------------------------------------------------------------------
# Pitch Deck tool
# ---------------------------------------------------------------------------

async def generate_pitch_deck(
    content: list[dict[str, Any]],
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a branded PowerPoint pitch deck and return a download widget.

    Creates a multi-slide PPTX presentation.  Each slide dict should contain:

    - ``title`` (str, required): The slide heading.
    - ``content`` (list[str], optional): Bullet points for the slide body.
    - ``chart_data`` (dict, optional): Chart to embed on the slide.
      Keys: ``type`` (bar|line|pie), ``labels`` (list[str]),
      ``values`` (list[float]), ``title`` (str).

    When chart_data is provided, the chart is rendered as a PNG and embedded
    in the slide alongside the bullet points.

    Args:
        content: List of slide dicts as described above.
        title: Optional deck title (defaults to "Pitch Deck").

    Returns:
        Widget dict with document download information.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"status": "error", "message": "No authenticated user found."}

    session_id = _get_session_id()

    from app.services.document_service import DocumentService

    service = DocumentService()

    # Pre-render any charts into image bytes for embedding
    slides_data: list[dict[str, Any]] = []
    for slide in content:
        slide_copy: dict[str, Any] = {
            "title": slide.get("title", ""),
            "bullets": slide.get("content", []),
        }

        chart_data = slide.get("chart_data")
        if chart_data and isinstance(chart_data, dict):
            try:
                chart_bytes = service.render_chart(chart_data)
                slide_copy["chart_image_bytes"] = chart_bytes
            except Exception:
                logger.warning("Chart rendering failed for slide '%s'", slide.get("title"))

        slides_data.append(slide_copy)

    try:
        widget = await service.generate_pptx(
            slides_data=slides_data,
            user_id=user_id,
            session_id=session_id,
            title=title,
        )
    except Exception as exc:
        logger.exception("PPTX generation failed")
        return {"status": "error", "message": f"Pitch deck generation failed: {exc}"}

    return {"status": "success", "widget": widget}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

DOCUMENT_GEN_TOOLS = [generate_pdf_report, generate_pitch_deck]
