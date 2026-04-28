# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the vault router process endpoint.

Covers:
- Successful processing via shared extraction helper
- ExtractionError from extraction helper returns failure response
- Unsupported/storage-only formats return a helpful non-error response
- Cross-user access rejection (user_id body != token identity)
- File not found in storage returns 404
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router.
# ---------------------------------------------------------------------------

CURRENT_USER = "user-abc"
OTHER_USER = "user-xyz"


async def _default_get_current_user_id() -> str:  # noqa: RUF029
    """Fake dependency that returns the test user."""
    return CURRENT_USER


def _stub_module(path: str, **attrs: object) -> None:
    """Insert a stub module into sys.modules if not already present."""
    if path not in sys.modules:
        mod = types.ModuleType(path)
        for name, val in attrs.items():
            setattr(mod, name, val)
        sys.modules[path] = mod


# Rate limiter — disable actual limiting for unit tests
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_limiter_mod = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *a, **kw: (lambda fn: fn)
    _mock_limiter_mod.limiter = _mock_limiter
    _mock_limiter_mod.get_user_persona_limit = MagicMock(return_value="100/minute")
    sys.modules["app.middleware.rate_limiter"] = _mock_limiter_mod

_MOCK_SUPABASE = MagicMock()

_stub_module(
    "app.routers.onboarding",
    get_current_user_id=_default_get_current_user_id,
    router=MagicMock(),
)
_stub_module(
    "app.services.supabase",
    get_service_client=MagicMock(return_value=_MOCK_SUPABASE),
)

# Stub RAG dependencies
_stub_module(
    "app.rag.knowledge_vault",
    ingest_document_content=AsyncMock(return_value={"chunk_count": 0}),
    search_knowledge=AsyncMock(return_value={"results": []}),
)


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------


def _make_query(data: list) -> MagicMock:
    """Return a fluent Supabase-style query mock that returns *data* on execute."""
    query = MagicMock()
    query.execute.return_value = SimpleNamespace(data=data)
    query.select.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    query.update.return_value = query
    return query


def _configure_supabase(file_bytes: bytes | None, doc_row: dict | None = None) -> MagicMock:
    """Configure the shared _MOCK_SUPABASE for a specific test scenario.

    Both _assert_storage_access and the MIME-type lookup query vault_documents.
    We return the doc_row for all table queries so both paths succeed when
    the file exists; an empty list simulates missing-file / no-access cases.
    """
    storage_bucket = MagicMock()
    storage_bucket.download.return_value = file_bytes
    _MOCK_SUPABASE.storage.from_.return_value = storage_bucket

    row_list = [doc_row] if doc_row is not None else []
    table_mock = MagicMock()
    query = _make_query(row_list)
    table_mock.select.return_value = query
    table_mock.update.return_value = query
    _MOCK_SUPABASE.table.return_value = table_mock
    return _MOCK_SUPABASE


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Minimal FastAPI test client for vault router only."""
    from app.routers.vault import router, get_current_user_id

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = _default_get_current_user_id
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests: process endpoint
# ---------------------------------------------------------------------------


class TestProcessEndpoint:
    """Tests for POST /vault/process."""

    def test_successful_text_processing(self, client: TestClient):
        """Plain-text file should be extracted and ingested successfully."""
        file_bytes = b"Plain text content for RAG processing."
        doc_row = {
            "id": "doc-1",
            "user_id": CURRENT_USER,
            "file_path": f"{CURRENT_USER}/test.txt",
            "file_type": "text/plain",
        }
        _configure_supabase(file_bytes, doc_row)

        with (
            patch(
                "app.routers.vault.extract_text_from_bytes",
                return_value="Plain text content for RAG processing.",
            ),
            patch(
                "app.routers.vault.ingest_document_content",
                new_callable=AsyncMock,
                return_value={"chunk_count": 3},
            ),
        ):
            resp = client.post(
                "/vault/process",
                json={"file_path": f"{CURRENT_USER}/test.txt"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["embedding_count"] == 3

    def test_xlsx_processing_passes_filename_for_extension_fallback(self, client: TestClient):
        """Generic-binary spreadsheet uploads should pass filename into extraction."""
        file_bytes = b"PK fake xlsx bytes"
        doc_row = {
            "id": "doc-xlsx",
            "user_id": CURRENT_USER,
            "file_path": f"{CURRENT_USER}/report.xlsx",
            "file_type": "application/octet-stream",
        }
        _configure_supabase(file_bytes, doc_row)

        with (
            patch(
                "app.routers.vault.extract_text_from_bytes",
                return_value="[Sheet: Revenue]\nQuarter\tRevenue",
            ) as extract_mock,
            patch(
                "app.routers.vault.ingest_document_content",
                new_callable=AsyncMock,
                return_value={"chunk_count": 2},
            ),
        ):
            resp = client.post(
                "/vault/process",
                json={"file_path": f"{CURRENT_USER}/report.xlsx"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["embedding_count"] == 2
        extract_mock.assert_called_once_with(
            file_bytes,
            "application/octet-stream",
            filename="report.xlsx",
        )

    def test_extraction_error_returns_failure_response(self, client: TestClient):
        """ExtractionError from extraction helper should yield success=False response."""
        from app.services.document_text_extraction import ExtractionError

        file_bytes = b"corrupted pdf bytes"
        doc_row = {
            "id": "doc-2",
            "user_id": CURRENT_USER,
            "file_path": f"{CURRENT_USER}/bad.pdf",
            "file_type": "application/pdf",
        }
        _configure_supabase(file_bytes, doc_row)

        with patch(
            "app.routers.vault.extract_text_from_bytes",
            side_effect=ExtractionError("PDF extraction failed: malformed"),
        ):
            resp = client.post(
                "/vault/process",
                json={"file_path": f"{CURRENT_USER}/bad.pdf"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "extraction" in data["message"].lower() or "pdf" in data["message"].lower()

    def test_storage_only_format_returns_not_searchable_message(self, client: TestClient):
        """Image/video files (extract returns None) should return success=False with clear message."""
        file_bytes = b"\x89PNG\r\n\x1a\n fake image bytes"
        doc_row = {
            "id": "doc-3",
            "user_id": CURRENT_USER,
            "file_path": f"{CURRENT_USER}/photo.png",
            "file_type": "image/png",
        }
        _configure_supabase(file_bytes, doc_row)

        with patch(
            "app.routers.vault.extract_text_from_bytes",
            return_value=None,
        ):
            resp = client.post(
                "/vault/process",
                json={"file_path": f"{CURRENT_USER}/photo.png"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "storage" in data["message"].lower() or "searchable" in data["message"].lower()

    def test_cross_user_access_rejected(self, client: TestClient):
        """Body user_id for a different user must be rejected with 403."""
        _configure_supabase(None)

        resp = client.post(
            "/vault/process",
            json={"file_path": "some/path.txt", "user_id": OTHER_USER},
        )

        assert resp.status_code == 403

    def test_file_not_found_in_storage(self, client: TestClient):
        """Storage returning empty/None bytes should raise 404."""
        # _assert_storage_access succeeds (doc row exists), but download returns None
        doc_row = {
            "id": "doc-4",
            "user_id": CURRENT_USER,
            "file_path": f"{CURRENT_USER}/missing.txt",
            "file_type": "text/plain",
        }
        _configure_supabase(None, doc_row)

        resp = client.post(
            "/vault/process",
            json={"file_path": f"{CURRENT_USER}/missing.txt"},
        )

        assert resp.status_code == 404
