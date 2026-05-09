# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression test: dead wrapper aliases must not reappear in enhanced_tools.

REGISTRY-05 deleted single-line wrapper aliases that just forwarded to the
canonical media tools (e.g. instagram_post_image -> generate_image, and
generate_short_video / generate_short_videos -> media.generate_video[s]).

If anyone re-introduces these wrappers, this test will fail loudly so they
get redirected to the canonical functions (generate_image with size, and
app.agents.tools.media.generate_video / generate_videos).
"""

from app.agents import enhanced_tools


def test_enhanced_tools_has_no_dead_wrappers() -> None:
    """enhanced_tools must not expose the deleted wrapper aliases."""
    for attr in ("instagram_post_image", "generate_short_video", "generate_short_videos"):
        assert not hasattr(enhanced_tools, attr), (
            f"enhanced_tools.{attr} was deleted in REGISTRY-05. "
            "Use the canonical tool instead "
            "(generate_image(prompt, size='1080x1080') / "
            "app.agents.tools.media.generate_video / generate_videos)."
        )
