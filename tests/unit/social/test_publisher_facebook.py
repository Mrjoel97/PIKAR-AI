# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the Facebook three-phase video upload (Plan 107-01).

Covers POST-09 success criteria:
  SC-1: three-phase request sequence (start -> transfer x N -> finish) on a
        2-chunk path.
  SC-1: legacy ``file_url`` JSON parameter is grep-absent from
        ``app/social/publisher.py``.
  SC-2: failed transfer chunk retries exactly once before surfacing a
        structured error.
  SC-2: structured ``FacebookUploadError`` raised after the retry is
        exhausted (no infinite retry loop).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from app.social.publisher import (
    FB_GRAPH_API_VERSION,
    FacebookUploadError,
    _upload_facebook_video,
)
from tests.unit.social.conftest import extract_form_field, extract_upload_phase

PAGE_ID = "PAGE_1234567890"
PAGE_TOKEN = "EAAG_FAKE_PAGE_ACCESS_TOKEN"
URL = f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/{PAGE_ID}/videos"


@pytest.mark.asyncio
@respx.mock
async def test_video_upload_three_phase_two_chunks(mp4_bytes):
    """SC-1: start -> transfer (chunk 1) -> transfer (chunk 2) -> finish."""
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "upload_session_id": "SID_HAPPY",
                    "video_id": "VID_999",
                    "start_offset": "0",
                    "end_offset": "5242880",
                },
            ),
            httpx.Response(
                200,
                json={"start_offset": "5242880", "end_offset": "10485760"},
            ),
            httpx.Response(
                200,
                json={"start_offset": "10485760", "end_offset": "10485760"},
            ),
            httpx.Response(200, json={"success": True}),
        ]
    )

    async with httpx.AsyncClient() as http:
        result = await _upload_facebook_video(
            http,
            page_id=PAGE_ID,
            page_access_token=PAGE_TOKEN,
            video_bytes=mp4_bytes,
            description="test caption",
        )

    assert result == {"video_id": "VID_999", "success": True}
    assert route.call_count == 4

    phases = [extract_upload_phase(call.request) for call in route.calls]
    assert phases == ["start", "transfer", "transfer", "finish"]

    # First transfer chunk starts at offset 0.
    assert extract_form_field(route.calls[1].request, "start_offset") == "0"
    # Second transfer chunk starts at the end of the first.
    assert extract_form_field(route.calls[2].request, "start_offset") == "5242880"
    # Finish carries the caption.
    assert extract_form_field(route.calls[3].request, "description") == "test caption"


@pytest.mark.asyncio
@respx.mock
async def test_video_upload_retries_chunk_once_on_5xx():
    """SC-2: a single 5xx on a transfer chunk triggers exactly one retry."""
    # 5 MB video so a single-chunk window suffices.
    small_bytes = b"\x00" * (5 * 1024 * 1024)

    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "upload_session_id": "SID_RETRY",
                    "video_id": "VID_R",
                    "start_offset": "0",
                    "end_offset": "5242880",
                },
            ),
            httpx.Response(500, json={"error": "server_busy"}),
            httpx.Response(
                200,
                json={"start_offset": "5242880", "end_offset": "5242880"},
            ),
            httpx.Response(200, json={"success": True}),
        ]
    )

    async with httpx.AsyncClient() as http:
        result = await _upload_facebook_video(
            http,
            page_id=PAGE_ID,
            page_access_token=PAGE_TOKEN,
            video_bytes=small_bytes,
            description="retry test",
        )

    assert result["success"] is True
    assert route.call_count == 4  # start + 500 + retry + finish

    phases = [extract_upload_phase(call.request) for call in route.calls]
    assert phases == ["start", "transfer", "transfer", "finish"]


@pytest.mark.asyncio
@respx.mock
async def test_video_upload_surfaces_error_after_retry_exhausted():
    """SC-2: two consecutive 5xx on a chunk -> FacebookUploadError, no third attempt."""
    small_bytes = b"\x00" * (5 * 1024 * 1024)

    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "upload_session_id": "SID_RETRY_EXHAUSTED",
                    "video_id": "VID_E",
                    "start_offset": "0",
                    "end_offset": "5242880",
                },
            ),
            httpx.Response(500, json={"error": "server_busy"}),
            httpx.Response(500, json={"error": "still_busy"}),
        ]
    )

    async with httpx.AsyncClient() as http:
        with pytest.raises(FacebookUploadError) as exc_info:
            await _upload_facebook_video(
                http,
                page_id=PAGE_ID,
                page_access_token=PAGE_TOKEN,
                video_bytes=small_bytes,
                description="exhaustion test",
            )

    assert exc_info.value.phase == "transfer"
    assert exc_info.value.session_id == "SID_RETRY_EXHAUSTED"
    assert exc_info.value.status_code == 500
    # No third transfer attempt and no finish call.
    assert route.call_count == 3


def test_no_legacy_file_url_in_publisher():
    """SC-1 static check: the legacy public-URL JSON field is grep-absent."""
    publisher_path = (
        Path(__file__).resolve().parents[3] / "app" / "social" / "publisher.py"
    )
    source = publisher_path.read_text(encoding="utf-8")
    assert "file_url" not in source, (
        "Legacy `file_url` JSON parameter must not appear in app/social/publisher.py"
    )
    assert "v18.0" not in source, (
        "Hardcoded API version v18.0 must not appear in app/social/publisher.py "
        "(use FB_GRAPH_API_VERSION constant)."
    )
