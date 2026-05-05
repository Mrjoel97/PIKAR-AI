# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""SlideImageService — render PPTX bytes to per-slide PNG bytes.

Pipeline: ``LibreOffice --headless --convert-to pdf`` → ``pdf2image`` → PNG.

LibreOffice is detected at module import via :func:`shutil.which` and stored
in :data:`LIBREOFFICE_BIN`. This module-level binding (rather than a per-call
lookup) lets tests monkeypatch the attribute to exercise the
"LibreOffice missing" code path without uninstalling the binary.

Used by the upcoming presentation editor to refresh per-slide images on
agent edit. CPU/IO-bound work is offloaded to :func:`asyncio.to_thread` so
the event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

# Resolved at import time so tests can monkeypatch this attribute directly.
LIBREOFFICE_BIN: str | None = shutil.which("libreoffice") or shutil.which("soffice")


class LibreOfficeNotInstalledError(RuntimeError):
    """Raised when LibreOffice headless is required but not on PATH."""


class SlideImageService:
    """Convert PPTX bytes to per-slide PNG bytes via LibreOffice + pdf2image.

    Args:
        dpi: Resolution passed to ``pdf2image`` for PDF→PNG rasterization.
            Default ``150`` is a good balance between fidelity and image size
            for slide-strip thumbnails.
    """

    def __init__(self, dpi: int = 150) -> None:
        self._dpi = dpi

    async def render_to_pngs(self, pptx_bytes: bytes) -> list[bytes]:
        """Render every slide of ``pptx_bytes`` to a PNG byte string.

        Args:
            pptx_bytes: Raw bytes of a ``.pptx`` presentation.

        Returns:
            One PNG byte string per slide, in deck order.

        Raises:
            LibreOfficeNotInstalledError: If neither ``libreoffice`` nor
                ``soffice`` is on ``PATH`` at module-load time.
            RuntimeError: If the LibreOffice subprocess fails or does not
                produce the expected ``input.pdf``.
        """
        if not LIBREOFFICE_BIN:
            raise LibreOfficeNotInstalledError(
                "LibreOffice (libreoffice/soffice) not found on PATH. "
                "Install it: apt-get install libreoffice on Linux, "
                "brew install --cask libreoffice on macOS."
            )

        logger.debug(
            "SlideImageService.render_to_pngs: %d bytes input, dpi=%d",
            len(pptx_bytes),
            self._dpi,
        )

        return await asyncio.to_thread(self._render_sync, pptx_bytes)

    async def render_single_slide(self, pptx_bytes: bytes, slide_index: int) -> bytes:
        """Render a single slide of ``pptx_bytes`` to PNG bytes.

        Currently renders the entire deck and returns the requested index.
        TODO: Build a single-slide PPTX before conversion to skip the other
        slides (~70% faster on large decks). Tracked as a v2 follow-up.

        Args:
            pptx_bytes: Raw bytes of a ``.pptx`` presentation.
            slide_index: Zero-based slide index to return.

        Returns:
            PNG byte string for the requested slide.

        Raises:
            LibreOfficeNotInstalledError: If LibreOffice is unavailable.
            IndexError: If ``slide_index`` is outside the deck's range.
        """
        pngs = await self.render_to_pngs(pptx_bytes)
        # Validate after fetching so the error message can include deck size.
        if slide_index < 0 or slide_index >= len(pngs):
            raise IndexError(
                f"slide_index {slide_index} out of range (deck has {len(pngs)} slides)"
            )
        return pngs[slide_index]

    def _render_sync(self, pptx_bytes: bytes) -> list[bytes]:
        """Synchronous body of :meth:`render_to_pngs`, run in a worker thread."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "input.pptx"
            pptx_path.write_bytes(pptx_bytes)

            self._run_libreoffice(pptx_path=pptx_path, output_dir=tmp_path)

            pdf_path = tmp_path / "input.pdf"
            if not pdf_path.exists():
                raise RuntimeError(
                    f"LibreOffice did not produce {pdf_path}. "
                    f"Inspect {tmp_path} for diagnostics."
                )

            images = convert_from_path(str(pdf_path), dpi=self._dpi)

            png_bytes_list: list[bytes] = []
            for img in images:
                # In-memory PNG encoding — avoid the disk write/read round-trip.
                buf = BytesIO()
                img.save(buf, format="PNG")
                png_bytes_list.append(buf.getvalue())

            logger.debug(
                "SlideImageService._render_sync: produced %d PNG(s)",
                len(png_bytes_list),
            )
            return png_bytes_list

    @staticmethod
    def _run_libreoffice(*, pptx_path: Path, output_dir: Path) -> None:
        """Invoke LibreOffice headless to convert ``pptx_path`` to PDF.

        Args:
            pptx_path: Path to the input ``.pptx`` file.
            output_dir: Directory where LibreOffice should write
                ``input.pdf``.

        Raises:
            RuntimeError: If LibreOffice exits with a non-zero return code.
                The decoded stderr is included in the message for production
                log forensics.
        """
        result = subprocess.run(
            [
                LIBREOFFICE_BIN,  # type: ignore[list-item]  # caller checks this
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(pptx_path),
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "LibreOffice failed "
                f"(rc={result.returncode}): {result.stderr.decode(errors='replace')}"
            )
