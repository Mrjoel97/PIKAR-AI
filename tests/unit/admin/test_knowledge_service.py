"""Unit tests for app.services.knowledge_service.

Tests verify:
- test_process_pdf: PDF bytes are extracted with pypdf, chunked, and ingested with scope=system
- test_process_docx: DOCX bytes are extracted with python-docx, same embedding flow
- test_process_txt: TXT bytes are decoded raw and ingested
- test_process_image: Image bytes trigger Gemini vision description + embedding storage
- test_process_video_enqueues: Video bytes are stored in Storage, entry inserted as processing, ai_jobs enqueued
- test_process_video_transcript: Audio extracted, transcribed, ingested; entry updated to completed
- test_process_video_transcript_failure: Exception updates entry to failed with error_message
- test_search_system_scope: search_system_knowledge calls match_system_knowledge RPC
- test_get_knowledge_stats: Stats aggregation returns per-agent counts and total embeddings
- test_process_document_empty: Empty content returns error dict without DB inserts
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------

_SERVICE_CLIENT_PATCH = "app.services.knowledge_service.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.services.knowledge_service.execute_async"
_INGEST_DOCUMENT_PATCH = "app.services.knowledge_service.ingest_document"
_GENERATE_EMBEDDINGS_PATCH = "app.services.knowledge_service.generate_embeddings_batch"
_TRANSCRIBE_AUDIO_PATCH = "app.services.knowledge_service.transcribe_audio"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_result(data: list) -> MagicMock:
    """Build a mock Supabase result with .data == data."""
    result = MagicMock()
    result.data = data
    return result


def _make_supabase_client_chain() -> MagicMock:
    """Return a MagicMock Supabase client with a fully chainable query mock."""
    client = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.insert.return_value = chain
    chain.upsert.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = _make_mock_result([{"id": "entry-uuid"}])
    client.table.return_value = chain
    # Storage mock
    storage_mock = MagicMock()
    bucket_mock = MagicMock()
    bucket_mock.upload.return_value = MagicMock(data={"path": "entry-uuid/test.pdf"})
    bucket_mock.download.return_value = b"fake-video-bytes"
    storage_mock.from_.return_value = bucket_mock
    client.storage = storage_mock
    # RPC mock
    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = _make_mock_result([
        {"id": "emb-1", "content": "test content", "metadata": {}, "similarity": 0.9}
    ])
    client.rpc.return_value = rpc_chain
    return client


# ===========================================================================
# process_document — PDF
# ===========================================================================


@pytest.mark.asyncio
async def test_process_pdf():
    """process_document with PDF bytes calls pypdf, chunks text, calls ingest_document."""
    from app.services.knowledge_service import process_document

    mock_client = _make_supabase_client_chain()
    embedding_ids = ["emb-1", "emb-2"]

    # Mock pypdf.PdfReader to return two pages of text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page text content with enough words to chunk."
    mock_pdf_reader = MagicMock()
    mock_pdf_reader.pages = [mock_page, mock_page]

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, return_value=_make_mock_result([{"id": "entry-uuid"}])):
            with patch(_INGEST_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=embedding_ids):
                with patch("pypdf.PdfReader", return_value=mock_pdf_reader):
                    result = await process_document(
                        file_bytes=b"%PDF-1.4 fake pdf",
                        filename="report.pdf",
                        mime_type="application/pdf",
                        agent_scope="financial",
                        uploaded_by="admin@test.com",
                    )

    assert result["status"] == "completed"
    assert result["chunk_count"] == 2
    assert "entry_id" in result


@pytest.mark.asyncio
async def test_process_docx():
    """process_document with DOCX bytes calls python-docx Document, same flow."""
    from app.services.knowledge_service import process_document

    mock_client = _make_supabase_client_chain()
    embedding_ids = ["emb-1"]

    mock_para = MagicMock()
    mock_para.text = "This is a paragraph in a DOCX file."
    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para, mock_para]

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, return_value=_make_mock_result([{"id": "entry-uuid"}])):
            with patch(_INGEST_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=embedding_ids):
                with patch("docx.Document", return_value=mock_doc):
                    result = await process_document(
                        file_bytes=b"PK fake docx content",
                        filename="contract.docx",
                        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        agent_scope=None,
                        uploaded_by="admin@test.com",
                    )

    assert result["status"] == "completed"
    assert "entry_id" in result


@pytest.mark.asyncio
async def test_process_xlsx_with_generic_mime():
    """process_document should extract XLSX content even when MIME is octet-stream."""
    from app.services.knowledge_service import process_document

    mock_client = _make_supabase_client_chain()
    embedding_ids = ["emb-1", "emb-2"]

    mock_sheet = MagicMock()
    mock_sheet.title = "Pipeline"
    mock_sheet.iter_rows.return_value = [
        ("Stage", "Owner"),
        ("Qualified", "Ada"),
    ]
    mock_workbook = MagicMock()
    mock_workbook.worksheets = [mock_sheet]

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, return_value=_make_mock_result([{"id": "entry-uuid"}])):
            with patch(_INGEST_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=embedding_ids):
                with patch("app.services.document_text_extraction.load_workbook", return_value=mock_workbook):
                    result = await process_document(
                        file_bytes=b"PK fake xlsx content",
                        filename="pipeline.xlsx",
                        mime_type="application/octet-stream",
                        agent_scope="sales",
                        uploaded_by="admin@test.com",
                    )

    assert result["status"] == "completed"
    assert result["chunk_count"] == 2
    assert "entry_id" in result
    mock_workbook.close.assert_called_once()


@pytest.mark.asyncio
async def test_process_txt():
    """process_document with TXT bytes reads raw text and ingests."""
    from app.services.knowledge_service import process_document

    mock_client = _make_supabase_client_chain()
    embedding_ids = ["emb-1", "emb-2", "emb-3"]

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, return_value=_make_mock_result([{"id": "entry-uuid"}])):
            with patch(_INGEST_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=embedding_ids):
                result = await process_document(
                    file_bytes=b"Plain text document content for embedding.",
                    filename="notes.txt",
                    mime_type="text/plain",
                    agent_scope="hr",
                    uploaded_by="admin@test.com",
                )

    assert result["status"] == "completed"
    assert result["chunk_count"] == 3
    assert "entry_id" in result


# ===========================================================================
# process_document — empty content guard
# ===========================================================================


@pytest.mark.asyncio
async def test_process_document_empty():
    """process_document with empty content returns error dict without DB inserts."""
    from app.services.knowledge_service import process_document

    mock_client = _make_supabase_client_chain()

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH) as mock_execute:
            result = await process_document(
                file_bytes=b"   ",  # whitespace-only
                filename="empty.txt",
                mime_type="text/plain",
                agent_scope=None,
                uploaded_by="admin@test.com",
            )

    assert "error" in result
    mock_execute.assert_not_called()  # no DB interaction on empty content


# ===========================================================================
# process_image
# ===========================================================================


@pytest.mark.asyncio
async def test_process_image():
    """process_image calls Gemini vision, embeds description, stores in Storage, inserts entry."""
    from app.services.knowledge_service import process_image

    mock_client = _make_supabase_client_chain()
    fake_description = "A bar chart showing quarterly revenue growth for 2025."

    # Mock Gemini genai client
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = fake_description
    mock_genai_client.models.generate_content.return_value = mock_response

    fake_embedding = [[0.1] * 768]

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, return_value=_make_mock_result([{"id": "entry-uuid"}])):
            with patch(_GENERATE_EMBEDDINGS_PATCH, return_value=fake_embedding):
                with patch("app.services.knowledge_service._get_genai_client", return_value=mock_genai_client):
                    result = await process_image(
                        file_bytes=b"\x89PNG\r\n\x1a\n fake image",
                        filename="chart.png",
                        mime_type="image/png",
                        agent_scope="data",
                        uploaded_by="admin@test.com",
                    )

    assert result["status"] == "completed"
    assert result["chunk_count"] == 1
    assert "entry_id" in result
    assert "description" in result


# ===========================================================================
# process_video — enqueue only (no inline transcription)
# ===========================================================================


@pytest.mark.asyncio
async def test_process_video_enqueues():
    """process_video stores file, inserts entry with status=processing, enqueues ai_jobs row."""
    from app.services.knowledge_service import process_video

    mock_client = _make_supabase_client_chain()

    execute_calls: list = []

    async def _mock_execute(query, **kwargs):
        execute_calls.append(query)
        return _make_mock_result([{"id": "entry-uuid"}])

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, side_effect=_mock_execute):
            result = await process_video(
                file_bytes=b"\x00\x00\x00\x18ftyp fake mp4",
                filename="training.mp4",
                mime_type="video/mp4",
                agent_scope="operations",
                uploaded_by="admin@test.com",
            )

    assert result["status"] == "processing"
    assert "entry_id" in result
    assert "queued" in result["message"].lower()
    # Two execute_async calls: insert entry + insert ai_jobs row
    assert len(execute_calls) >= 2


# ===========================================================================
# process_video_transcript — background worker handler
# ===========================================================================


@pytest.mark.asyncio
async def test_process_video_transcript():
    """process_video_transcript downloads video, extracts audio, transcribes, ingests, updates entry."""
    from app.services.knowledge_service import process_video_transcript

    mock_client = _make_supabase_client_chain()
    # Simulate successful download
    mock_client.storage.from_().download.return_value = b"\x00\x00\x00\x18ftyp fake video"

    embedding_ids = ["emb-1", "emb-2", "emb-3"]
    transcript_result = {"success": True, "transcript": "Welcome to our quarterly review.", "confidence": 0.95}

    fake_audio_output = b"RIFF fake wav data"

    async def _mock_execute(query, **kwargs):
        return _make_mock_result([{"id": "entry-uuid", "filename": "training.mp4", "agent_scope": "sales"}])

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, side_effect=_mock_execute):
            with patch(_INGEST_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=embedding_ids):
                with patch(_TRANSCRIBE_AUDIO_PATCH, return_value=transcript_result):
                    with patch("app.services.knowledge_service._extract_audio_from_video",
                               new_callable=AsyncMock, return_value=fake_audio_output):
                        result = await process_video_transcript(
                            entry_id="entry-uuid",
                            file_path="entry-uuid/training.mp4",
                            agent_scope="sales",
                            mime_type="video/mp4",
                        )

    assert result["status"] == "completed"
    assert result["chunk_count"] == 3
    assert result["transcript_length"] > 0
    assert "entry_id" in result


@pytest.mark.asyncio
async def test_process_video_transcript_failure():
    """process_video_transcript with error updates entry to failed with error_message and re-raises."""
    from app.services.knowledge_service import process_video_transcript

    mock_client = _make_supabase_client_chain()
    mock_client.storage.from_().download.side_effect = Exception("Storage download failed")

    execute_calls: list = []

    async def _mock_execute(query, **kwargs):
        execute_calls.append(query)
        return _make_mock_result([{"id": "entry-uuid", "filename": "bad.mp4", "agent_scope": None}])

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, side_effect=_mock_execute):
            with pytest.raises(Exception, match="Storage download failed"):
                await process_video_transcript(
                    entry_id="entry-uuid",
                    file_path="entry-uuid/bad.mp4",
                    agent_scope=None,
                    mime_type="video/mp4",
                )

    # At least one execute_async call was made to update status=failed
    assert len(execute_calls) >= 1


# ===========================================================================
# search_system_knowledge
# ===========================================================================


@pytest.mark.asyncio
async def test_search_system_scope():
    """search_system_knowledge calls match_system_knowledge RPC with query embedding and agent_scope."""
    from app.services.knowledge_service import search_system_knowledge

    mock_client = _make_supabase_client_chain()
    fake_embedding = [[0.1] * 768]
    rpc_result = [
        {"id": "emb-1", "content": "Quarterly revenue grew 12%.", "metadata": {"scope": "system"}, "similarity": 0.92}
    ]
    mock_client.rpc.return_value.execute.return_value = _make_mock_result(rpc_result)

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_GENERATE_EMBEDDINGS_PATCH, return_value=fake_embedding):
            results = await search_system_knowledge(
                query="revenue growth",
                agent_name="financial",
                top_k=5,
            )

    assert len(results) == 1
    assert results[0]["content"] == "Quarterly revenue grew 12%."
    assert results[0]["similarity"] == 0.92
    mock_client.rpc.assert_called_once()
    call_args = mock_client.rpc.call_args
    assert call_args[0][0] == "match_system_knowledge"


# ===========================================================================
# get_knowledge_stats
# ===========================================================================


@pytest.mark.asyncio
async def test_get_knowledge_stats():
    """get_knowledge_stats returns per-agent counts, total entries, total embeddings, storage_bytes."""
    from app.services.knowledge_service import get_knowledge_stats

    mock_client = _make_supabase_client_chain()
    entries = [
        {"id": "e1", "agent_scope": "financial", "chunk_count": 5, "file_size_bytes": 1024},
        {"id": "e2", "agent_scope": "financial", "chunk_count": 3, "file_size_bytes": 2048},
        {"id": "e3", "agent_scope": None,         "chunk_count": 7, "file_size_bytes": 512},
        {"id": "e4", "agent_scope": "hr",          "chunk_count": 2, "file_size_bytes": 256},
    ]

    async def _mock_execute(query, **kwargs):
        return _make_mock_result(entries)

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
        with patch(_EXECUTE_ASYNC_PATCH, side_effect=_mock_execute):
            stats = await get_knowledge_stats()

    assert stats["total_entries"] == 4
    assert stats["total_embeddings"] == 17  # 5+3+7+2
    assert stats["storage_bytes"] == 3840   # 1024+2048+512+256
    assert stats["by_agent"]["financial"] == 2
    assert stats["by_agent"]["hr"] == 1
    assert stats["by_agent"].get("global", 0) + stats["by_agent"].get(None, 0) >= 1
