"""Regression test for the image-generation async path in app.agents.tools.media.

The image-path used to invoke `supabase.storage.from_(...).upload(...)` and
`supabase.table("media_assets").insert(row).execute()` synchronously inside an
`async def` coroutine, which blocks the SSE event loop under concurrent load.
The video-path equivalent (`_save_and_return_video_widget`) was fixed earlier;
this test guards the matching fix on the image path.

Both Supabase calls must be routed through `asyncio.to_thread` so they run in
a worker thread instead of blocking the event loop.
"""

from __future__ import annotations

import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tools import media


def _make_supabase() -> MagicMock:
    supabase = MagicMock()
    bucket = MagicMock()
    bucket.upload.return_value = None
    bucket.create_signed_url.return_value = {
        "signedURL": "https://storage.example.com/generated-asset",
    }
    supabase.storage.from_.return_value = bucket

    table = MagicMock()
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[{"id": "row-1"}])
    table.insert.return_value = query
    supabase.table.return_value = table
    return supabase


def _noop_schedule(coro, _label: str) -> None:
    """Best-effort task sink that drops scheduled coroutines without running them.

    The image path schedules a knowledge-vault ingest as a fire-and-forget task;
    we don't need to exercise it here, but we must close the coroutine to
    silence "coroutine was never awaited" warnings.
    """
    try:
        coro.close()
    except Exception:  # noqa: BLE001 — defensive cleanup
        pass


@pytest.mark.asyncio
async def test_generate_image_routes_supabase_calls_through_to_thread():
    """Both the storage upload and media_assets insert must go through
    `asyncio.to_thread`. If either call is invoked synchronously the SSE event
    loop will stall under concurrent load.
    """
    supabase = _make_supabase()
    image_bytes = base64.b64encode(b"fake-image-bytes").decode()

    real_to_thread = asyncio.to_thread
    to_thread_spy = AsyncMock(side_effect=real_to_thread)

    with (
        patch("app.agents.tools.media._get_supabase_client", return_value=supabase),
        patch(
            "app.services.vertex_image_service.generate_image",
            return_value={
                "success": True,
                "image_bytes_base64": image_bytes,
                "mime_type": "image/png",
                "model_used": "imagen-test",
            },
        ),
        patch(
            "app.agents.tools.media._register_media_contract",
            new_callable=AsyncMock,
            return_value={"workspace_mode": "focus"},
        ),
        patch(
            "app.agents.tools.media._schedule_best_effort_task",
            side_effect=_noop_schedule,
        ),
        patch("app.agents.tools.media.asyncio.to_thread", to_thread_spy),
    ):
        result = await media.generate_image(
            prompt="hero shot",
            style="vibrant",
            user_id="user-1",
        )

    assert result["type"] == "image"

    # Collect the callables routed through asyncio.to_thread. The Vertex image
    # generation call is also offloaded via to_thread (positional callable
    # form), so we filter to just the Supabase-bound lambdas/calls.
    routed_callables = [call.args[0] for call in to_thread_spy.await_args_list]

    # Storage upload must have been routed through to_thread.
    assert supabase.storage.from_.return_value.upload.called, (
        "storage upload was never invoked — fix the test harness"
    )
    bucket_mock = supabase.storage.from_.return_value
    upload_routed = any(
        cb in (bucket_mock.upload,)
        or (
            callable(cb)
            and getattr(cb, "__name__", "") == "<lambda>"
            and bucket_mock.upload.called
        )
        for cb in routed_callables
    )
    assert upload_routed, (
        "supabase.storage.from_(...).upload(...) must be wrapped in "
        "asyncio.to_thread to avoid blocking the SSE event loop"
    )

    # media_assets insert must have been routed through to_thread.
    table_mock = supabase.table.return_value
    assert table_mock.insert.called, (
        "media_assets insert was never invoked — fix the test harness"
    )
    insert_routed = any(
        callable(cb)
        and getattr(cb, "__name__", "") == "<lambda>"
        and table_mock.insert.called
        for cb in routed_callables
    )
    assert insert_routed, (
        "supabase.table('media_assets').insert(row).execute() must be wrapped "
        "in asyncio.to_thread to avoid blocking the SSE event loop"
    )

    # Stronger assertion: the awaited count must include at least the two
    # Supabase routings (upload + insert) plus the Vertex generate call. If
    # either Supabase call regressed back to a sync invocation this drops to 1.
    assert to_thread_spy.await_count >= 3, (
        f"expected at least 3 asyncio.to_thread awaits "
        f"(vertex generate + storage upload + media_assets insert), "
        f"got {to_thread_spy.await_count}"
    )
