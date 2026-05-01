from __future__ import annotations

import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from app.agents.tools import media
from app.routers.vault import ProcessDocumentRequest, process_document_for_rag
from app.services.request_context import set_current_user_id


def _make_search_client(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    rpc_query = MagicMock()
    rpc_query.execute = AsyncMock(return_value=MagicMock(data=rows))
    client.rpc.return_value = rpc_query
    return client


def _make_document_supabase() -> MagicMock:
    supabase = MagicMock()
    bucket = MagicMock()
    bucket.upload.return_value = None
    bucket.create_signed_url.return_value = {
        "signedURL": "https://storage.example.com/signed/doc.pdf",
    }
    supabase.storage.from_.return_value = bucket
    table = MagicMock()
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[{"id": "row-1"}])
    table.upsert.return_value = query
    supabase.table.return_value = table
    return supabase


def _make_media_supabase() -> MagicMock:
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
async def test_search_returns_mixed_document_types():
    rows = [
        {
            "content": "Q4 strategy outline...",
            "similarity": 0.92,
            "source_type": "pdf",
            "metadata": {
                "document_type": "pdf",
                "asset_id": "p1",
                "template": "competitive_analysis",
            },
            "source_id": "p1",
        },
        {
            "content": "Pitch deck for fundraising...",
            "similarity": 0.88,
            "source_type": "pitch_deck",
            "metadata": {"document_type": "pitch_deck", "asset_id": "pd1"},
            "source_id": "pd1",
        },
        {
            "content": "Generated pro video: Q4...",
            "similarity": 0.85,
            "source_type": "video",
            "metadata": {
                "document_type": "video",
                "asset_id": "v1",
                "asset_type": "video",
            },
            "source_id": "v1",
        },
        {
            "content": "Generated image: hero...",
            "similarity": 0.81,
            "source_type": "image",
            "metadata": {
                "document_type": "image",
                "asset_id": "i1",
                "asset_type": "image",
            },
            "source_id": "i1",
        },
        {
            "content": "User-uploaded business plan",
            "similarity": 0.78,
            "source_type": "uploaded_document",
            "metadata": {
                "document_type": "uploaded_document",
                "file_path": "user-1/plan.pdf",
            },
            "source_id": "u1",
        },
    ]
    client = _make_search_client(rows)

    try:
        set_current_user_id("user-1")
        with (
            patch(
                "app.rag.knowledge_vault.get_supabase_client",
                AsyncMock(return_value=client),
            ),
            patch(
                "app.rag.search_service.generate_embedding",
                return_value=[0.1] * 768,
            ),
        ):
            from app.agent import search_business_knowledge

            result = await search_business_knowledge("Q4 strategy")
    finally:
        set_current_user_id(None)

    assert "error" not in result
    assert len(result["results"]) == 5
    assert result["results"][0]["similarity"] == 0.92
    assert {row["source_type"] for row in result["results"]} == {
        "pdf",
        "pitch_deck",
        "video",
        "image",
        "uploaded_document",
    }
    client.rpc.assert_called_once()
    assert client.rpc.call_args.args[0] == "match_embeddings"
    assert client.rpc.call_args.args[1]["filter_user_id"] == "user-1"


@pytest.mark.asyncio
async def test_pdf_ingest_is_retrievable_via_search():
    financial_data = {
        "executive_summary": "Revenue grew 15% YoY.",
        "metrics": [{"label": "Revenue", "value": "$1.2M"}],
        "revenue_breakdown": [{"source": "Product A", "amount": "$600K", "pct": "50%"}],
        "analysis": "Strong performance across all segments.",
    }
    mock_html_cls = MagicMock()
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = b"%PDF-1.4 fake pdf content"
    mock_html_cls.return_value = mock_html_instance

    with (
        patch(
            "app.services.document_service.get_brand_profile",
            new_callable=AsyncMock,
            return_value={"success": True, "profile": None},
        ),
        patch(
            "app.services.document_service._get_weasyprint_html",
            return_value=mock_html_cls,
        ),
        patch(
            "app.services.document_service.get_service_client",
            return_value=_make_document_supabase(),
        ),
        patch(
            "app.services.document_service.execute_async",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.document_service.extract_text_from_bytes",
            return_value="Q4 Strategy Deck financial summary",
        ),
        patch(
            "app.services.document_service.ingest_document_content",
            new_callable=AsyncMock,
        ) as ingest_mock,
    ):
        from app.services.document_service import DocumentService

        svc = DocumentService()
        await svc.generate_pdf(
            "financial_report",
            financial_data,
            user_id="user-1",
            session_id="sess-1",
            title="Q4 Strategy Deck",
        )

    ingest_kwargs = ingest_mock.await_args.kwargs
    search_rows = [
        {
            "content": ingest_kwargs["content"],
            "similarity": 0.91,
            "source_type": ingest_kwargs["document_type"],
            "metadata": {
                "document_type": ingest_kwargs["document_type"],
                **ingest_kwargs["metadata"],
            },
            "source_id": ingest_kwargs["metadata"]["asset_id"],
        }
    ]
    client = _make_search_client(search_rows)

    try:
        set_current_user_id("user-1")
        with (
            patch(
                "app.rag.knowledge_vault.get_supabase_client",
                AsyncMock(return_value=client),
            ),
            patch(
                "app.rag.search_service.generate_embedding",
                return_value=[0.1] * 768,
            ),
        ):
            from app.agent import search_business_knowledge

            result = await search_business_knowledge("Q4 Strategy")
    finally:
        set_current_user_id(None)

    assert len(result["results"]) == 1
    row = result["results"][0]
    assert row["metadata"]["document_type"] == "pdf"
    assert row["metadata"]["template"] == "financial_report"


@pytest.mark.asyncio
async def test_manual_upload_branch_unchanged_after_phase89():
    supabase = MagicMock()
    bucket = MagicMock()
    bucket.download.return_value = b"uploaded pdf bytes"
    supabase.storage.from_.return_value = bucket

    select_query = MagicMock()
    select_query.eq.return_value = select_query
    select_query.limit.return_value = select_query
    select_query.execute.return_value = SimpleNamespace(
        data=[{"file_type": "application/pdf"}]
    )

    update_query = MagicMock()
    update_query.eq.return_value = update_query
    update_query.execute.return_value = SimpleNamespace(data=[{"ok": True}])

    table = MagicMock()
    table.select.return_value = select_query
    table.update.return_value = update_query
    supabase.table.return_value = table

    with (
        patch("app.routers.vault.get_supabase", return_value=supabase),
        patch("app.routers.vault._assert_storage_access", return_value=None),
        patch(
            "app.routers.vault.extract_text_from_bytes",
            return_value="User uploaded content",
        ),
        patch(
            "app.routers.vault.ingest_document_content",
            new_callable=AsyncMock,
            return_value={"chunk_count": 2},
        ) as ingest_mock,
    ):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/vault/process",
                "headers": [],
            }
        )
        result = await process_document_for_rag(
            request=request,
            body=ProcessDocumentRequest(file_path="user-1/report.pdf"),
            current_user_id="user-1",
        )

    assert result.success is True
    assert result.embedding_count == 2
    assert ingest_mock.await_args.kwargs["document_type"] == "uploaded_document"


@pytest.mark.asyncio
async def test_media_py_paths_preserve_legacy_asset_type():
    image_tasks: list[asyncio.Task[object]] = []
    image_bytes = base64.b64encode(b"fake-image-bytes").decode()

    with (
        patch("app.agents.tools.media._get_supabase_client", return_value=_make_media_supabase()),
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
            side_effect=_schedule_immediately(image_tasks),
        ),
        patch(
            "app.rag.knowledge_vault.ingest_document_content",
            new_callable=AsyncMock,
        ) as ingest_image_mock,
    ):
        await media.generate_image(prompt="hero shot", user_id="user-1")
        await asyncio.gather(*image_tasks, return_exceptions=True)

    assert ingest_image_mock.await_args.kwargs["document_type"] == "image"
    assert ingest_image_mock.await_args.kwargs["metadata"]["asset_type"] == "image"

    video_tasks: list[asyncio.Task[object]] = []
    with (
        patch("app.agents.tools.media._get_supabase_client", return_value=_make_media_supabase()),
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
            side_effect=_schedule_immediately(video_tasks),
        ),
        patch(
            "app.rag.knowledge_vault.ingest_document_content",
            new_callable=AsyncMock,
        ) as ingest_video_mock,
    ):
        await media.generate_video(prompt="launch teaser", duration_seconds=6, user_id="user-1")
        await asyncio.gather(*video_tasks, return_exceptions=True)

    assert ingest_video_mock.await_args.kwargs["document_type"] == "video"
    assert ingest_video_mock.await_args.kwargs["metadata"]["asset_type"] == "video"
