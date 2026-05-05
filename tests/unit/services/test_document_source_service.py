# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DocumentSourceService -- canonical source CRUD."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Ensure required env is present before importing the service module.
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Recorder:
    """Records the chained Supabase query calls for assertions in tests."""

    def __init__(self) -> None:
        """Initialize the recorder with empty call/payload stores."""
        self.table_name: str | None = None
        self.op: str | None = None
        self.payload: Any = None
        self.eq_calls: list[tuple[str, Any]] = []
        self.select_arg: str | None = None
        self.maybe_single_called: bool = False


def _make_query_chain(recorder: _Recorder) -> MagicMock:
    """Build a MagicMock supabase async client whose chained methods record calls.

    The mock supports the chains used by DocumentSourceService:

    - ``client.table("t").insert(payload).execute()``
    - ``client.table("t").select("*").eq("k", v).maybe_single().execute()``
    - ``client.table("t").update(payload).eq("k", v).execute()``
    """
    chain = MagicMock()

    def _insert(payload: Any) -> MagicMock:
        recorder.op = "insert"
        recorder.payload = payload
        return chain

    def _select(arg: str = "*") -> MagicMock:
        recorder.op = "select"
        recorder.select_arg = arg
        return chain

    def _update(payload: Any) -> MagicMock:
        recorder.op = "update"
        recorder.payload = payload
        return chain

    def _eq(key: str, value: Any) -> MagicMock:
        recorder.eq_calls.append((key, value))
        return chain

    def _maybe_single() -> MagicMock:
        recorder.maybe_single_called = True
        return chain

    chain.insert.side_effect = _insert
    chain.select.side_effect = _select
    chain.update.side_effect = _update
    chain.eq.side_effect = _eq
    chain.maybe_single.side_effect = _maybe_single

    client = MagicMock()

    def _table(name: str) -> MagicMock:
        recorder.table_name = name
        return chain

    client.table.side_effect = _table
    return client


@pytest.fixture()
def recorder() -> _Recorder:
    """Provide a fresh recorder for each test."""
    return _Recorder()


@pytest.fixture()
def mock_client(recorder: _Recorder) -> MagicMock:
    """Return a mock supabase async client wired to the recorder."""
    return _make_query_chain(recorder)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreate:
    """DocumentSourceService.create inserts a row into document_sources."""

    @pytest.mark.asyncio
    async def test_inserts_row_and_returns_data(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """Given a doc spec, create() inserts into document_sources and returns the row."""
        from app.services.document_source_service import DocumentSourceService

        user_id = str(uuid4())
        document_id = str(uuid4())
        source = {"sections": [{"heading": "Intro", "content": "Hello"}]}
        binary_url = "https://example.com/file.pdf"
        row = {
            "id": str(uuid4()),
            "user_id": user_id,
            "document_id": document_id,
            "doc_class": "report",
            "source": source,
            "binary_url": binary_url,
            "forked_from_upload": False,
        }

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[row]),
            ),
        ):
            svc = DocumentSourceService()
            result = await svc.create(
                user_id=user_id,
                document_id=document_id,
                doc_class="report",
                source=source,
                binary_url=binary_url,
            )

        assert recorder.table_name == "document_sources"
        assert recorder.op == "insert"
        assert recorder.payload == {
            "user_id": user_id,
            "document_id": document_id,
            "doc_class": "report",
            "source": source,
            "binary_url": binary_url,
            "forked_from_upload": False,
        }
        assert result == row

    @pytest.mark.asyncio
    async def test_create_passes_forked_from_upload_when_true(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """forked_from_upload kwarg propagates into the insert payload."""
        from app.services.document_source_service import DocumentSourceService

        document_id = str(uuid4())

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[{"document_id": document_id}]),
            ),
        ):
            svc = DocumentSourceService()
            await svc.create(
                user_id=str(uuid4()),
                document_id=document_id,
                doc_class="word",
                source=None,
                binary_url="https://example.com/upload.docx",
                forked_from_upload=True,
            )

        assert recorder.payload["forked_from_upload"] is True


class TestGet:
    """DocumentSourceService.get returns a single row or None."""

    @pytest.mark.asyncio
    async def test_get_returns_row(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """get() selects by document_id with maybe_single() and returns the row."""
        from app.services.document_source_service import DocumentSourceService

        document_id = str(uuid4())
        row = {"document_id": document_id, "doc_class": "spreadsheet"}

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=row),
            ),
        ):
            svc = DocumentSourceService()
            result = await svc.get(document_id)

        assert recorder.table_name == "document_sources"
        assert recorder.op == "select"
        assert recorder.select_arg == "*"
        assert recorder.eq_calls == [("document_id", document_id)]
        assert recorder.maybe_single_called is True
        assert result == row

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(
        self,
        mock_client: MagicMock,
    ) -> None:
        """get() returns None when execute_async result has no data."""
        from app.services.document_source_service import DocumentSourceService

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=None),
            ),
        ):
            svc = DocumentSourceService()
            result = await svc.get(str(uuid4()))

        assert result is None


class TestUpdateSource:
    """DocumentSourceService.update_source updates source and optional binary_url."""

    @pytest.mark.asyncio
    async def test_updates_source_and_binary_url(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """When new_binary_url is provided it is included in the update payload."""
        from app.services.document_source_service import DocumentSourceService

        document_id = str(uuid4())
        new_source = {"sections": [{"heading": "v2", "content": "..."}]}
        new_binary_url = "https://example.com/v2.pdf"
        row = {
            "document_id": document_id,
            "source": new_source,
            "binary_url": new_binary_url,
        }

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[row]),
            ),
        ):
            svc = DocumentSourceService()
            result = await svc.update_source(
                document_id=document_id,
                new_source=new_source,
                new_binary_url=new_binary_url,
            )

        assert recorder.table_name == "document_sources"
        assert recorder.op == "update"
        assert recorder.payload == {
            "source": new_source,
            "binary_url": new_binary_url,
        }
        assert recorder.eq_calls == [("document_id", document_id)]
        assert result == row

    @pytest.mark.asyncio
    async def test_omits_binary_url_when_none(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """When new_binary_url is None, the update payload must NOT include binary_url."""
        from app.services.document_source_service import DocumentSourceService

        document_id = str(uuid4())
        new_source = {"sections": []}

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[{"document_id": document_id}]),
            ),
        ):
            svc = DocumentSourceService()
            await svc.update_source(
                document_id=document_id,
                new_source=new_source,
                new_binary_url=None,
            )

        assert "binary_url" not in recorder.payload
        assert recorder.payload == {"source": new_source}


class TestSetExtractedText:
    """DocumentSourceService.set_extracted_text updates extracted_text + extracted_at."""

    @pytest.mark.asyncio
    async def test_sets_text_and_timestamp(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """set_extracted_text() updates both extracted_text and extracted_at."""
        from app.services.document_source_service import DocumentSourceService

        document_id = str(uuid4())
        text = "Lorem ipsum dolor sit amet."
        row = {
            "document_id": document_id,
            "extracted_text": text,
            "extracted_at": "2026-05-05T12:00:00+00:00",
        }

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[row]),
            ),
        ):
            svc = DocumentSourceService()
            result = await svc.set_extracted_text(document_id, text)

        assert recorder.table_name == "document_sources"
        assert recorder.op == "update"
        assert recorder.payload["extracted_text"] == text
        # extracted_at must be set to a non-empty ISO timestamp string.
        assert isinstance(recorder.payload["extracted_at"], str)
        assert len(recorder.payload["extracted_at"]) > 0
        # Trigger handles updated_at, so the service must NOT set it manually.
        assert "updated_at" not in recorder.payload
        assert recorder.eq_calls == [("document_id", document_id)]
        assert result == row


class TestMarkForkedFromUpload:
    """DocumentSourceService.mark_forked_from_upload flips the flag to True."""

    @pytest.mark.asyncio
    async def test_marks_forked_true(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """mark_forked_from_upload() updates only forked_from_upload=true."""
        from app.services.document_source_service import DocumentSourceService

        document_id = str(uuid4())
        row = {"document_id": document_id, "forked_from_upload": True}

        with (
            patch.object(
                DocumentSourceService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_source_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[row]),
            ),
        ):
            svc = DocumentSourceService()
            result = await svc.mark_forked_from_upload(document_id)

        assert recorder.table_name == "document_sources"
        assert recorder.op == "update"
        assert recorder.payload == {"forked_from_upload": True}
        assert recorder.eq_calls == [("document_id", document_id)]
        assert result == row
