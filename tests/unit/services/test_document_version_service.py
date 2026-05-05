# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DocumentVersionService -- version-chain CRUD."""

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
        self.order_calls: list[tuple[str, dict[str, Any]]] = []
        self.limit_calls: list[int] = []


def _make_query_chain(recorder: _Recorder) -> MagicMock:
    """Build a MagicMock supabase async client whose chained methods record calls.

    The mock supports the chains used by DocumentVersionService:

    - ``client.table("t").insert(payload).execute()``
    - ``client.table("t").select("*").eq("k", v).order(...).limit(n).execute()``
    - ``client.table("t").select("*").eq("k", v).maybe_single().execute()``
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

    def _eq(key: str, value: Any) -> MagicMock:
        recorder.eq_calls.append((key, value))
        return chain

    def _maybe_single() -> MagicMock:
        recorder.maybe_single_called = True
        return chain

    def _order(column: str, **kwargs: Any) -> MagicMock:
        recorder.order_calls.append((column, dict(kwargs)))
        return chain

    def _limit(n: int) -> MagicMock:
        recorder.limit_calls.append(n)
        return chain

    chain.insert.side_effect = _insert
    chain.select.side_effect = _select
    chain.eq.side_effect = _eq
    chain.maybe_single.side_effect = _maybe_single
    chain.order.side_effect = _order
    chain.limit.side_effect = _limit

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


class TestAppend:
    """DocumentVersionService.append inserts a row into document_versions."""

    @pytest.mark.asyncio
    async def test_inserts_row_and_returns_data(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """Given a version spec, append() inserts into document_versions and returns the row."""
        from app.services.document_version_service import DocumentVersionService

        user_id = str(uuid4())
        document_id = str(uuid4())
        snapshot = {"sections": [{"heading": "Intro", "content": "Hello"}]}
        binary_url = "https://example.com/v1.pdf"
        diff_summary = "initial version"
        row = {
            "id": str(uuid4()),
            "document_id": document_id,
            "user_id": user_id,
            "source_snapshot": snapshot,
            "binary_url": binary_url,
            "diff_summary": diff_summary,
            "created_by": "agent",
        }

        with (
            patch.object(
                DocumentVersionService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_version_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[row]),
            ),
        ):
            svc = DocumentVersionService()
            result = await svc.append(
                document_id=document_id,
                user_id=user_id,
                source_snapshot=snapshot,
                binary_url=binary_url,
                diff_summary=diff_summary,
                created_by="agent",
            )

        assert recorder.table_name == "document_versions"
        assert recorder.op == "insert"
        assert recorder.payload == {
            "document_id": document_id,
            "user_id": user_id,
            "source_snapshot": snapshot,
            "binary_url": binary_url,
            "diff_summary": diff_summary,
            "created_by": "agent",
        }
        assert result == row

    @pytest.mark.asyncio
    async def test_append_rejects_invalid_created_by(
        self,
        mock_client: MagicMock,
    ) -> None:
        """append() raises ValueError when created_by is not in the allowed set."""
        from app.services.document_version_service import DocumentVersionService

        with patch.object(
            DocumentVersionService,
            "get_client",
            new=AsyncMock(return_value=mock_client),
        ):
            svc = DocumentVersionService()
            with pytest.raises(ValueError, match="created_by"):
                await svc.append(
                    document_id=str(uuid4()),
                    user_id=str(uuid4()),
                    source_snapshot={"sections": []},
                    binary_url="https://example.com/v1.pdf",
                    diff_summary=None,
                    created_by="robot",  # invalid
                )

    @pytest.mark.asyncio
    async def test_append_raises_when_data_empty(
        self,
        mock_client: MagicMock,
    ) -> None:
        """append() raises ValueError when result.data is empty (no row returned)."""
        from app.services.document_version_service import DocumentVersionService

        document_id = str(uuid4())

        with (
            patch.object(
                DocumentVersionService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_version_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[]),
            ),
        ):
            svc = DocumentVersionService()
            with pytest.raises(ValueError, match=document_id):
                await svc.append(
                    document_id=document_id,
                    user_id=str(uuid4()),
                    source_snapshot={"sections": []},
                    binary_url="https://example.com/v1.pdf",
                    diff_summary=None,
                    created_by="user",
                )


class TestList:
    """DocumentVersionService.list returns version rows newest-first."""

    @pytest.mark.asyncio
    async def test_list_orders_newest_first(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """list() selects by document_id ordered by created_at DESC with default limit=10."""
        from app.services.document_version_service import DocumentVersionService

        document_id = str(uuid4())
        rows = [
            {"id": str(uuid4()), "document_id": document_id, "created_by": "agent"},
            {"id": str(uuid4()), "document_id": document_id, "created_by": "user"},
        ]

        with (
            patch.object(
                DocumentVersionService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_version_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=rows),
            ),
        ):
            svc = DocumentVersionService()
            result = await svc.list(document_id)

        assert recorder.table_name == "document_versions"
        assert recorder.op == "select"
        assert recorder.select_arg == "*"
        assert recorder.eq_calls == [("document_id", document_id)]
        # Newest-first order on created_at must be asserted via the recorder.
        assert recorder.order_calls == [("created_at", {"desc": True})]
        assert recorder.limit_calls == [10]
        assert result == rows

    @pytest.mark.asyncio
    async def test_list_propagates_explicit_limit(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """An explicit ``limit`` kwarg propagates to .limit(n) on the chain."""
        from app.services.document_version_service import DocumentVersionService

        document_id = str(uuid4())

        with (
            patch.object(
                DocumentVersionService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_version_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[]),
            ),
        ):
            svc = DocumentVersionService()
            result = await svc.list(document_id, limit=42)

        assert recorder.limit_calls == [42]
        # Empty list is a valid response (no rows yet) -- not an error.
        assert result == []


class TestGet:
    """DocumentVersionService.get returns a single version row or None."""

    @pytest.mark.asyncio
    async def test_get_returns_row(
        self,
        recorder: _Recorder,
        mock_client: MagicMock,
    ) -> None:
        """get() selects by id with maybe_single() and returns the row."""
        from app.services.document_version_service import DocumentVersionService

        version_id = str(uuid4())
        row = {"id": version_id, "created_by": "agent"}

        with (
            patch.object(
                DocumentVersionService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_version_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=row),
            ),
        ):
            svc = DocumentVersionService()
            result = await svc.get(version_id)

        assert recorder.table_name == "document_versions"
        assert recorder.op == "select"
        assert recorder.select_arg == "*"
        assert recorder.eq_calls == [("id", version_id)]
        assert recorder.maybe_single_called is True
        assert result == row

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(
        self,
        mock_client: MagicMock,
    ) -> None:
        """get() returns None when execute_async result has no data."""
        from app.services.document_version_service import DocumentVersionService

        with (
            patch.object(
                DocumentVersionService,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.document_version_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=None),
            ),
        ):
            svc = DocumentVersionService()
            result = await svc.get(str(uuid4()))

        assert result is None
