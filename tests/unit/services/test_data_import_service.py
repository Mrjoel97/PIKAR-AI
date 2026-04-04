# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DataImportService — CSV parsing, AI mapping, validation, preview, commit."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _csv_bytes(rows: list[list[str]], headers: list[str] | None = None) -> bytes:
    """Build CSV bytes from a list of rows."""
    buf = io.StringIO()
    if headers:
        buf.write(",".join(headers) + "\n")
    for row in rows:
        buf.write(",".join(str(c) for c in row) + "\n")
    return buf.getvalue().encode("utf-8")


def _make_service():
    """Return a DataImportService with mocked Supabase client."""
    with patch(
        "app.services.data_import_service.get_service_client",
        return_value=MagicMock(),
    ):
        from app.services.data_import_service import DataImportService

        svc = DataImportService(user_id=USER_ID)
    return svc


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseCsv:
    """parse_csv returns a polars DataFrame with correct columns and row count."""

    def test_returns_column_headers_and_row_count(self):
        svc = _make_service()
        csv = _csv_bytes(
            [["Alice", "alice@example.com"], ["Bob", "bob@example.com"]],
            headers=["name", "email"],
        )
        df = svc.parse_csv(csv)
        assert isinstance(df, pl.DataFrame)
        assert df.columns == ["name", "email"]
        assert len(df) == 2

    def test_handles_encoding_issues(self):
        """CSV with BOM succeeds via utf8-lossy fallback."""
        svc = _make_service()
        bom = b"\xef\xbb\xbf"
        csv = bom + _csv_bytes(
            [["Alice", "alice@example.com"]],
            headers=["name", "email"],
        )
        df = svc.parse_csv(csv)
        assert len(df) == 1
        # Column name should not contain BOM characters
        assert "name" in df.columns

    def test_rejects_files_over_50mb(self):
        svc = _make_service()
        # 51 MB of zeros
        big_bytes = b"x" * (51 * 1024 * 1024)
        with pytest.raises(ValueError, match="50"):
            svc.parse_csv(big_bytes)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidate:
    """validate returns per-row errors for invalid data."""

    def test_returns_row_level_errors(self):
        svc = _make_service()
        df = pl.DataFrame(
            {
                "name": ["Alice", None],
                "email": ["alice@example.com", "bob@example.com"],
            }
        )
        mapping = {"name": "name", "email": "email"}
        errors = svc.validate(df, mapping, "contacts")
        assert isinstance(errors, list)
        # Row 2 has None name (required) -> should produce an error
        assert any(e["column"] == "name" for e in errors)
        assert any("required" in e["reason"].lower() for e in errors)

    def test_validate_enum_columns(self):
        svc = _make_service()
        df = pl.DataFrame(
            {
                "name": ["Alice"],
                "email": ["alice@example.com"],
                "lifecycle_stage": ["INVALID_STAGE"],
            }
        )
        mapping = {
            "name": "name",
            "email": "email",
            "lifecycle_stage": "lifecycle_stage",
        }
        errors = svc.validate(df, mapping, "contacts")
        assert len(errors) >= 1
        err = next(e for e in errors if e["column"] == "lifecycle_stage")
        assert "lead" in err["reason"].lower() or "valid" in err["reason"].lower()


# ---------------------------------------------------------------------------
# AI Column Mapping
# ---------------------------------------------------------------------------


class TestAiSuggestMappings:
    """suggest_mappings returns a dict mapping CSV columns to target columns."""

    @pytest.mark.asyncio
    async def test_returns_mapping_dict(self):
        svc = _make_service()
        df = pl.DataFrame(
            {
                "Full Name": ["Alice"],
                "Email Address": ["alice@example.com"],
            }
        )
        with patch(
            "app.services.data_import_service.DataImportService._call_gemini_for_mapping",
            new_callable=AsyncMock,
            return_value={"Full Name": "name", "Email Address": "email"},
        ):
            result = await svc.suggest_mappings(df, "contacts")
        assert isinstance(result, dict)
        assert result["Full Name"] == "name"
        assert result["Email Address"] == "email"


# ---------------------------------------------------------------------------
# Column Mapping Persistence
# ---------------------------------------------------------------------------


class TestColumnMappingPersistence:
    """Saved column mappings load on next call for same user + table."""

    @pytest.mark.asyncio
    async def test_save_and_load_column_mappings(self):
        svc = _make_service()
        mapping = {"Full Name": "name", "Email Address": "email"}

        # Mock the supabase calls for save
        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute = MagicMock(return_value=MagicMock(data=[{"id": "1"}]))
        mock_table.upsert = MagicMock(return_value=mock_upsert)
        svc._admin_client = MagicMock()
        svc._admin_client.table = MagicMock(return_value=mock_table)

        with patch(
            "app.services.data_import_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[{"id": "1"}]),
        ):
            await svc.save_column_mapping("contacts", mapping)

        # Mock the load
        with patch(
            "app.services.data_import_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[{"mapping": mapping}]),
        ):
            loaded = await svc.load_column_mapping("contacts")

        assert loaded == mapping


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


class TestPreview:
    """preview returns first N rows as list of dicts."""

    def test_returns_first_10_rows(self):
        svc = _make_service()
        df = pl.DataFrame({"name": [f"user_{i}" for i in range(50)]})
        mapping = {"name": "name"}
        result = svc.preview(df, mapping, limit=10)
        assert isinstance(result, list)
        assert len(result) == 10
        assert result[0]["name"] == "user_0"


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------


class TestCommit:
    """commit inserts in batches and calls progress callback."""

    @pytest.mark.asyncio
    async def test_batches_inserts(self):
        svc = _make_service()
        df = pl.DataFrame(
            {
                "name": [f"user_{i}" for i in range(250)],
                "email": [f"u{i}@test.com" for i in range(250)],
            }
        )
        mapping = {"name": "name", "email": "email"}

        progress_calls: list[float] = []

        def on_progress(pct: float) -> None:
            progress_calls.append(pct)

        with patch(
            "app.services.data_import_service.execute_async",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[]),
        ):
            result = await svc.commit(
                df,
                mapping,
                "contacts",
                progress_callback=on_progress,
            )

        assert result["imported_count"] == 250
        # With 250 rows at batch 100, should have 3 progress calls
        assert len(progress_calls) >= 3
