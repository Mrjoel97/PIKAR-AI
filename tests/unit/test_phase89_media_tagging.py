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
    table.upsert.return_value = query
    supabase.table.return_value = table
    return supabase


def _schedule_immediately(task_sink: list[asyncio.Task[object]]):
    def _fake_schedule(coro, _label: str) -> None:
        async def _runner():
            try:
                await coro
            except Exception:
                return None
            return None

        task_sink.append(asyncio.create_task(_runner()))

    return _fake_schedule


@pytest.mark.asyncio
async def test_image_gen_ingest_uses_document_type_image():
    scheduled: list[asyncio.Task[object]] = []
    image_bytes = base64.b64encode(b"fake-image-bytes").decode()

    with (
        patch("app.agents.tools.media._get_supabase_client", return_value=_make_supabase()),
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
            side_effect=_schedule_immediately(scheduled),
        ),
        patch(
            "app.rag.knowledge_vault.ingest_document_content",
            new_callable=AsyncMock,
        ) as ingest_mock,
        patch("app.services.request_context.get_current_session_id", return_value="sess-1"),
        patch(
            "app.services.request_context.get_current_workflow_execution_id",
            return_value="exec-1",
        ),
    ):
        result = await media.generate_image(
            prompt="hero shot",
            style="vibrant",
            user_id="user-1",
        )
        await asyncio.gather(*scheduled, return_exceptions=True)

    assert result["type"] == "image"
    ingest_mock.assert_awaited_once()
    kwargs = ingest_mock.await_args.kwargs
    assert kwargs["document_type"] == "image"
    assert kwargs["metadata"]["asset_type"] == "image"
    assert kwargs["metadata"]["bucket_id"] == "knowledge-vault"
    assert kwargs["metadata"]["file_path"]
    assert kwargs["metadata"]["prompt"] == "hero shot"
    assert kwargs["metadata"]["session_id"] == "sess-1"
    assert kwargs["metadata"]["workflow_execution_id"] == "exec-1"
    assert kwargs["metadata"]["asset_id"]


@pytest.mark.asyncio
async def test_video_fallback_ingest_uses_document_type_video():
    scheduled: list[asyncio.Task[object]] = []

    with (
        patch("app.agents.tools.media._get_supabase_client", return_value=_make_supabase()),
        patch(
            "app.services.vertex_video_service.generate_video",
            return_value={
                "success": True,
                "video_bytes": b"video-bytes",
                "video_url": None,
                "model_used": "veo-test",
            },
        ),
        patch(
            "app.agents.tools.media._register_media_contract",
            new_callable=AsyncMock,
            return_value={"workspace_mode": "focus"},
        ),
        patch(
            "app.agents.tools.media._schedule_best_effort_task",
            side_effect=_schedule_immediately(scheduled),
        ),
        patch(
            "app.rag.knowledge_vault.ingest_document_content",
            new_callable=AsyncMock,
        ) as ingest_mock,
        patch("app.services.request_context.get_current_session_id", return_value="sess-2"),
        patch(
            "app.services.request_context.get_current_workflow_execution_id",
            return_value="exec-2",
        ),
    ):
        result = await media.generate_video(
            prompt="launch teaser",
            duration_seconds=6,
            user_id="user-1",
        )
        await asyncio.gather(*scheduled, return_exceptions=True)

    assert result["type"] == "video"
    ingest_mock.assert_awaited_once()
    kwargs = ingest_mock.await_args.kwargs
    assert kwargs["document_type"] == "video"
    assert kwargs["metadata"]["asset_type"] == "video"
    assert kwargs["metadata"]["bucket_id"] == "knowledge-vault"
    assert kwargs["metadata"]["file_path"]
    assert kwargs["metadata"]["prompt"] == "launch teaser"
    assert kwargs["metadata"]["source"] == "vertex veo"
    assert kwargs["metadata"]["session_id"] == "sess-2"
    assert kwargs["metadata"]["workflow_execution_id"] == "exec-2"
    assert kwargs["metadata"]["asset_id"]


@pytest.mark.asyncio
async def test_image_ingest_failure_does_not_break_widget_return():
    scheduled: list[asyncio.Task[object]] = []
    image_bytes = base64.b64encode(b"fake-image-bytes").decode()

    with (
        patch("app.agents.tools.media._get_supabase_client", return_value=_make_supabase()),
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
            side_effect=_schedule_immediately(scheduled),
        ),
        patch(
            "app.rag.knowledge_vault.ingest_document_content",
            new_callable=AsyncMock,
            side_effect=RuntimeError("ingest failed"),
        ),
    ):
        result = await media.generate_image(
            prompt="hero shot",
            style="vibrant",
            user_id="user-1",
        )
        await asyncio.gather(*scheduled, return_exceptions=True)

    assert result["type"] == "image"
