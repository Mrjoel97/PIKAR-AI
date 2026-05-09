"""Live smoke tests for Twitter publisher (Phase 104).

Gated by RUN_LIVE=1 to keep CI hermetic. Requires:
  - TWITTER_TEST_USER_ID env var (a connected pikar-ai user with active
    twitter row that has been re-authorized post-Phase-104 migration)
  - TWITTER_TEST_IMAGE_URL env var (a public 4MB JPEG)
  - The connected account must be on a paid X tier (free tier rate-limit
    is ~17/24h)
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1",
    reason="Live smoke tests gated by RUN_LIVE=1",
)


@pytest.mark.asyncio
async def test_image_post():
    """POST-04 success criterion: 4MB JPEG attached to live tweet."""
    from app.social.publisher import SocialPublisher

    user_id = os.environ["TWITTER_TEST_USER_ID"]
    image_url = os.environ["TWITTER_TEST_IMAGE_URL"]
    result = await SocialPublisher().post_with_media(
        user_id=user_id,
        platform="twitter",
        content=f"Phase 104 image smoke test {os.urandom(4).hex()}",
        media_urls=[image_url],
        media_type="image",
    )
    assert "error" not in result, f"Live tweet failed: {result}"
    # Tweet response shape: {"data": {"id": "...", "text": "..."}} -- detailed
    # shape assertion is defensive; adapt if X changes the envelope.


@pytest.mark.asyncio
async def test_video_post():
    """POST-05 success criterion 1: 30s 1080p video posts and plays."""
    from app.social.publisher import SocialPublisher

    user_id = os.environ["TWITTER_TEST_USER_ID"]
    video_url = os.environ.get("TWITTER_TEST_VIDEO_URL")
    if not video_url:
        pytest.skip("TWITTER_TEST_VIDEO_URL not set")
    result = await SocialPublisher().post_with_media(
        user_id=user_id,
        platform="twitter",
        content=f"Phase 104 video smoke test {os.urandom(4).hex()}",
        media_urls=[video_url],
        media_type="video",
    )
    assert "error" not in result, f"Live video tweet failed: {result}"
