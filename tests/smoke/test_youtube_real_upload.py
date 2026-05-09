"""Real-API smoke test for YouTube resumable upload (POST-07 SC1).

Skipped unless ``PIKAR_RUN_YOUTUBE_SMOKE=1`` is set. Requires:
  - ``YOUTUBE_TEST_USER_ID`` env var pointing to a Pikar user with a connected
    YouTube test channel.
  - ``YOUTUBE_TEST_MEDIA_URL`` env var pointing to a publicly fetchable URL of
    the 1MB MP4 fixture (e.g., a Supabase Storage signed URL).

Manual verification step: visit ``https://youtube.com/watch?v={post_id}``
after the test passes and delete the test video from the channel.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PIKAR_RUN_YOUTUBE_SMOKE") != "1",
    reason="Set PIKAR_RUN_YOUTUBE_SMOKE=1 to run real-API YouTube smoke test",
)


@pytest.mark.asyncio
async def test_real_upload_to_test_channel():
    """Upload a 1MB MP4 fixture to a real YouTube test channel."""
    from app.social.publisher import get_social_publisher

    user_id = os.environ["YOUTUBE_TEST_USER_ID"]
    media_url = os.environ["YOUTUBE_TEST_MEDIA_URL"]
    fixture = Path(__file__).parent.parent / "fixtures" / "test_video_1mb.mp4"
    assert fixture.exists(), f"Missing fixture: {fixture}"

    pub = get_social_publisher()
    result = await pub.post_with_media(
        user_id=user_id,
        platform="youtube",
        content="Pikar smoke test upload -- DELETE ME",
        media_urls=[media_url],
        media_type="video",
    )
    assert result.get("success") is True, f"Upload failed: {result}"
    assert result.get("post_id"), "post_id missing from result"
    # Manual verification at https://youtube.com/watch?v={post_id}
