# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DataExportService — CSV generation, Storage upload, signed URLs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service():
    """Return a DataExportService with mocked Supabase client."""
    with patch(
        "app.services.data_export_service.get_service_client",
        return_value=MagicMock(),
    ):
        from app.services.data_export_service import DataExportService

        svc = DataExportService(user_id=USER_ID)
    return svc


# ---------------------------------------------------------------------------
# CSV Generation
# ---------------------------------------------------------------------------


class TestExportCsvBytes:
    """export produces valid CSV bytes with headers."""

    def test_generates_csv_bytes(self):
        svc = _make_service()
        records = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
        csv_bytes = svc.records_to_csv_bytes(records)
        assert isinstance(csv_bytes, bytes)
        text = csv_bytes.decode("utf-8")
        lines = text.strip().split("\n")
        # Header + 2 data rows
        assert len(lines) == 3
        assert "name" in lines[0]
        assert "email" in lines[0]
        assert "Alice" in lines[1]


# ---------------------------------------------------------------------------
# Storage Upload
# ---------------------------------------------------------------------------


class TestExportUpload:
    """export_table uploads to generated-documents bucket and returns signed URL."""

    @pytest.mark.asyncio
    async def test_uploads_and_returns_signed_url(self):
        svc = _make_service()

        # Mock the table query to return records
        mock_response = MagicMock()
        mock_response.data = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]

        with (
            patch(
                "app.services.data_export_service.execute_async",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
            patch(
                "app.services.data_export_service.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_upload,
            patch.object(
                svc,
                "_get_signed_url",
                new_callable=AsyncMock,
                return_value="https://storage.example.com/signed/contacts.csv",
            ),
        ):
            result = await svc.export_table("contacts")

        assert "url" in result
        assert "filename" in result
        assert "size_bytes" in result
        assert result["url"].startswith("https://")
        assert "contacts" in result["filename"]
