# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for :class:`SlideImageService` — PPTX → PNG strip rendering.

Two of the three tests are real round-trip integration tests: they invoke
``render_pptx_from_source`` to build genuine PPTX bytes, then feed them
through LibreOffice and ``pdf2image``. They are gated on LibreOffice being
on the PATH so the suite stays green on dev machines without it.

The third test (``test_raises_when_libreoffice_missing``) does not require
LibreOffice — it monkeypatches the module-level binding to assert the early
:class:`LibreOfficeNotInstalledError` path.
"""

from __future__ import annotations

import shutil

import pytest

from app.services import slide_image_service
from app.services.document_service import render_pptx_from_source
from app.services.slide_image_service import (
    LibreOfficeNotInstalledError,
    SlideImageService,
)

HAS_LIBREOFFICE = (
    shutil.which("libreoffice") is not None or shutil.which("soffice") is not None
)

requires_libreoffice = pytest.mark.skipif(
    not HAS_LIBREOFFICE,
    reason=(
        "LibreOffice not on PATH; install libreoffice/soffice "
        "to run this round-trip test"
    ),
)


@requires_libreoffice
@pytest.mark.asyncio
async def test_render_to_pngs_returns_one_png_per_slide() -> None:
    source = {
        "title": "Test",
        "slides": [
            {
                "layout": "title",
                "title": f"Slide {i}",
                "body": "",
                "speaker_notes": None,
            }
            for i in range(3)
        ],
    }
    pptx_bytes = await render_pptx_from_source(source)
    service = SlideImageService()

    pngs = await service.render_to_pngs(pptx_bytes)

    assert len(pngs) == 3
    for png in pngs:
        assert isinstance(png, bytes)
        assert png.startswith(b"\x89PNG")


@requires_libreoffice
@pytest.mark.asyncio
async def test_render_single_slide_returns_one_png() -> None:
    source = {
        "title": "X",
        "slides": [
            {
                "layout": "title",
                "title": "One",
                "body": "",
                "speaker_notes": None,
            }
        ],
    }
    pptx_bytes = await render_pptx_from_source(source)
    service = SlideImageService()

    png = await service.render_single_slide(pptx_bytes, slide_index=0)

    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_raises_when_libreoffice_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The early-error path runs everywhere — LibreOffice not required."""
    monkeypatch.setattr(slide_image_service, "LIBREOFFICE_BIN", None)
    service = SlideImageService()

    with pytest.raises(LibreOfficeNotInstalledError):
        await service.render_to_pngs(b"not-actually-pptx")
