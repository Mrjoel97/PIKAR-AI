# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Document generation service — PDF reports and PowerPoint pitch decks.

Generates branded PDF documents from Jinja2 HTML templates using weasyprint,
and branded PowerPoint presentations using python-pptx.  All heavy rendering
runs in a thread-pool to avoid blocking the async event loop.

Documents are uploaded to Supabase Storage and tracked in the ``media_assets``
table for conversation linking.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.agents.tools.brand_profile import get_brand_profile
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


def _get_matplotlib():
    """Lazy import matplotlib to avoid import-time side effects."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _get_weasyprint_html():
    """Lazy import weasyprint.HTML (requires system C libraries)."""
    from weasyprint import HTML as _HTML

    return _HTML

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TEMPLATES = [
    "financial_report",
    "project_proposal",
    "meeting_summary",
    "competitive_analysis",
    "sales_proposal",
]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf"
DOCUMENT_BUCKET = "generated-documents"

# Pikar default brand colors (used when user has no brand profile)
DEFAULT_BRAND_NAME = "Pikar"
DEFAULT_PRIMARY_COLOR = "#4F46E5"
DEFAULT_SECONDARY_COLOR = "#10B981"
DEFAULT_ACCENT_COLOR = "#F59E0B"

# Safety limit: reject PDFs larger than 5 MB (~50+ pages of content)
MAX_PDF_BYTES = 5 * 1024 * 1024


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DocumentService:
    """Generate branded PDF and PPTX documents from structured data."""

    def __init__(self) -> None:
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    # ------------------------------------------------------------------
    # PDF Generation
    # ------------------------------------------------------------------

    async def generate_pdf(
        self,
        template_name: str,
        data: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Render an HTML template to a branded PDF and upload it.

        Args:
            template_name: One of :data:`VALID_TEMPLATES`.
            data: Template-specific data dict.
            user_id: Owner of the generated document.
            session_id: Optional conversation session for linking.
            title: Human-readable document title.

        Returns:
            Widget dict suitable for returning to the chat UI.

        Raises:
            ValueError: If *template_name* is invalid or the PDF exceeds size limits.
        """
        if template_name not in VALID_TEMPLATES:
            msg = f"Invalid template '{template_name}'. Must be one of {VALID_TEMPLATES}"
            raise ValueError(msg)

        # Resolve branding ---------------------------------------------------
        brand = await get_brand_profile(user_id=user_id)
        brand_vars = self._extract_brand_vars(brand)

        # Render charts if present -------------------------------------------
        chart_images: dict[str, str] = {}
        chart_entries = data.get("chart_data", [])
        if isinstance(chart_entries, list):
            for idx, chart_data in enumerate(chart_entries):
                png_bytes = self.render_chart(chart_data)
                b64 = base64.b64encode(png_bytes).decode()
                chart_images[f"chart_{idx}"] = f"data:image/png;base64,{b64}"

        # Build template context ---------------------------------------------
        context: dict[str, Any] = {
            **data,
            **brand_vars,
            "chart_images": chart_images,
        }

        template = self._jinja_env.get_template(f"{template_name}.html")
        rendered_html = template.render(**context)

        # Render PDF in thread pool (weasyprint is CPU-intensive sync code) --
        HTMLClass = _get_weasyprint_html()
        pdf_bytes: bytes = await asyncio.to_thread(
            HTMLClass(string=rendered_html).write_pdf,
        )

        # Enforce page/size limit --------------------------------------------
        if len(pdf_bytes) > MAX_PDF_BYTES:
            msg = (
                f"Generated PDF ({len(pdf_bytes):,} bytes) exceeds maximum "
                f"allowed size ({MAX_PDF_BYTES:,} bytes / ~50 pages)."
            )
            raise ValueError(msg)

        # Upload + track -----------------------------------------------------
        doc_id = str(uuid.uuid4())
        doc_title = title or f"{template_name.replace('_', ' ').title()}"
        filename = f"{doc_id}.pdf"

        widget = await self._upload_document(
            file_bytes=pdf_bytes,
            user_id=user_id,
            doc_id=doc_id,
            filename=filename,
            content_type="application/pdf",
            title=doc_title,
            template_name=template_name,
            session_id=session_id,
            file_type="pdf",
        )
        return widget

    # ------------------------------------------------------------------
    # PPTX Generation
    # ------------------------------------------------------------------

    async def generate_pptx(
        self,
        slides_data: list[dict[str, Any]],
        user_id: str,
        session_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Generate a branded PowerPoint pitch deck.

        Args:
            slides_data: List of slide dicts, each with ``title``, ``bullets``,
                and optionally ``chart_image_bytes``.
            user_id: Owner of the generated document.
            session_id: Optional conversation session for linking.
            title: Human-readable document title.

        Returns:
            Widget dict suitable for returning to the chat UI.
        """
        brand = await get_brand_profile(user_id=user_id)
        brand_vars = self._extract_brand_vars(brand)

        # Build presentation in thread pool ----------------------------------
        pptx_bytes = await asyncio.to_thread(
            self._build_pptx, slides_data, brand_vars,
        )

        doc_id = str(uuid.uuid4())
        doc_title = title or "Pitch Deck"
        filename = f"{doc_id}.pptx"

        widget = await self._upload_document(
            file_bytes=pptx_bytes,
            user_id=user_id,
            doc_id=doc_id,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            title=doc_title,
            template_name="pitch_deck",
            session_id=session_id,
            file_type="pptx",
        )
        return widget

    @staticmethod
    def _build_pptx(
        slides_data: list[dict[str, Any]],
        brand_vars: dict[str, Any],
    ) -> bytes:
        """Build a PPTX file in memory (sync, runs in thread pool)."""
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.util import Inches, Pt

        prs = Presentation()
        # 16:9 widescreen
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        primary_hex = brand_vars.get("primary_color", DEFAULT_PRIMARY_COLOR).lstrip("#")
        primary_rgb = RGBColor(
            int(primary_hex[0:2], 16),
            int(primary_hex[2:4], 16),
            int(primary_hex[4:6], 16),
        )

        blank_layout = prs.slide_layouts[6]  # blank layout

        for slide_data in slides_data:
            slide = prs.slides.add_slide(blank_layout)

            # Title textbox
            left = Inches(0.8)
            top = Inches(0.5)
            width = Inches(11.5)
            height = Inches(1.2)
            txbox = slide.shapes.add_textbox(left, top, width, height)
            tf = txbox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = slide_data.get("title", "")
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = primary_rgb

            # Bullet points
            bullets = slide_data.get("bullets", [])
            if bullets:
                bullet_top = Inches(2.0)
                bullet_height = Inches(4.0)
                btxbox = slide.shapes.add_textbox(left, bullet_top, width, bullet_height)
                btf = btxbox.text_frame
                btf.word_wrap = True
                for i, bullet in enumerate(bullets):
                    if i == 0:
                        bp = btf.paragraphs[0]
                    else:
                        bp = btf.add_paragraph()
                    bp.text = bullet
                    bp.font.size = Pt(20)
                    bp.space_after = Pt(12)

            # Chart image (if provided)
            chart_bytes = slide_data.get("chart_image_bytes")
            if chart_bytes and isinstance(chart_bytes, bytes):
                try:
                    img_stream = BytesIO(chart_bytes)
                    img_left = Inches(8.0)
                    img_top = Inches(2.0)
                    img_width = Inches(4.5)
                    slide.shapes.add_picture(img_stream, img_left, img_top, width=img_width)
                except Exception:
                    logger.warning("Failed to embed chart image in PPTX slide")

        buf = BytesIO()
        prs.save(buf)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Chart Rendering
    # ------------------------------------------------------------------

    @staticmethod
    def render_chart(chart_data: dict[str, Any]) -> bytes:
        """Render a chart to PNG bytes using matplotlib.

        Args:
            chart_data: Dict with keys ``type`` (bar|line|pie), ``labels``,
                ``values``, and ``title``.

        Returns:
            PNG image bytes.
        """
        plt = _get_matplotlib()

        chart_type = chart_data.get("type", "bar")
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        chart_title = chart_data.get("title", "")

        fig, ax = plt.subplots(figsize=(8, 5))
        try:
            if chart_type == "pie":
                ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            elif chart_type == "line":
                ax.plot(labels, values, marker="o", linewidth=2)
                ax.set_ylabel("Value")
            else:
                # Default to bar chart
                ax.bar(labels, values)
                ax.set_ylabel("Value")

            ax.set_title(chart_title)
            fig.tight_layout()

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            buf.seek(0)
            return buf.getvalue()
        finally:
            plt.close(fig)

    # ------------------------------------------------------------------
    # Brand Extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_brand_vars(brand_result: dict[str, Any]) -> dict[str, Any]:
        """Extract brand variables from a get_brand_profile result.

        Falls back to Pikar defaults when no profile is available.
        """
        profile = brand_result.get("profile") if brand_result.get("success") else None

        if profile is None:
            return {
                "brand_name": DEFAULT_BRAND_NAME,
                "logo_url": "",
                "primary_color": DEFAULT_PRIMARY_COLOR,
                "secondary_color": DEFAULT_SECONDARY_COLOR,
                "accent_color": DEFAULT_ACCENT_COLOR,
            }

        visual = profile.get("visual_style") or {}
        palette = visual.get("color_palette") or []

        return {
            "brand_name": profile.get("brand_name", DEFAULT_BRAND_NAME),
            "logo_url": profile.get("logo_url", ""),
            "primary_color": palette[0] if len(palette) > 0 else DEFAULT_PRIMARY_COLOR,
            "secondary_color": palette[1] if len(palette) > 1 else DEFAULT_SECONDARY_COLOR,
            "accent_color": palette[2] if len(palette) > 2 else DEFAULT_ACCENT_COLOR,
        }

    # ------------------------------------------------------------------
    # Upload + Track
    # ------------------------------------------------------------------

    async def _upload_document(
        self,
        file_bytes: bytes,
        user_id: str,
        doc_id: str,
        filename: str,
        content_type: str,
        title: str,
        template_name: str,
        session_id: str | None,
        file_type: str,
    ) -> dict[str, Any]:
        """Upload document to Supabase Storage and track in media_assets.

        Follows the same pattern as director_service for consistency.

        Returns:
            Widget dict for the chat UI.
        """
        supabase = get_service_client()
        path = f"{user_id}/{filename}"

        # Upload to Storage ---------------------------------------------------
        await asyncio.to_thread(
            supabase.storage.from_(DOCUMENT_BUCKET).upload,
            path,
            file_bytes,
            {"content-type": content_type},
        )

        # Signed URL for private access ---------------------------------------
        signed = await asyncio.to_thread(
            supabase.storage.from_(DOCUMENT_BUCKET).create_signed_url,
            path,
            3600,  # 1 hour expiry
        )
        signed_url = signed.get("signedURL", signed.get("signedUrl", ""))

        # Track in media_assets -----------------------------------------------
        try:
            await execute_async(
                supabase.table("media_assets").upsert(
                    {
                        "id": doc_id,
                        "user_id": user_id,
                        "bucket_id": DOCUMENT_BUCKET,
                        "asset_type": "document",
                        "title": title,
                        "filename": filename,
                        "file_path": path,
                        "file_url": signed_url,
                        "file_type": content_type,
                        "category": "generated",
                        "size_bytes": len(file_bytes),
                        "metadata": {
                            "template": template_name,
                            "session_id": session_id,
                        },
                    },
                    on_conflict="id",
                ),
                op_name="document_service.media_assets.upsert",
            )
        except Exception as exc:
            logger.warning("Failed to track document in media_assets: %s", exc)

        # Return widget dict --------------------------------------------------
        return {
            "type": "document",
            "title": title,
            "data": {
                "documentUrl": signed_url,
                "title": title,
                "fileType": file_type,
                "sizeBytes": len(file_bytes),
                "templateName": template_name,
            },
            "dismissible": True,
            "expandable": False,
        }
