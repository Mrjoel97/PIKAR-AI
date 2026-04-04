# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""DataExportService — CSV export pipeline with RLS-scoped queries.

Queries a target table respecting RLS, converts results to a polars DataFrame,
writes CSV bytes, uploads to Supabase Storage ``generated-documents`` bucket,
and returns a signed download URL.
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Any

import polars as pl

from app.services.base_service import BaseService
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUCKET_NAME = "generated-documents"
SIGNED_URL_EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours

EXPORTABLE_TABLES: dict[str, dict[str, Any]] = {
    "contacts": {"label": "Contacts"},
    "financial_records": {"label": "Financial Records"},
    "department_tasks": {"label": "Tasks"},
    "initiatives": {"label": "Initiatives"},
    "content_bundles": {"label": "Content Bundles"},
    "support_tickets": {"label": "Support Tickets"},
    "recruitment_candidates": {"label": "Candidates"},
    "compliance_risks": {"label": "Compliance Risks"},
    "compliance_audits": {"label": "Compliance Audits"},
}


class DataExportService(BaseService):
    """Export tables to CSV and upload to Supabase Storage.

    Args:
        user_id: Authenticated user's UUID.
        user_token: JWT token for RLS-scoped queries (optional; when
            omitted the service-role client is used — only for tests).
    """

    def __init__(
        self,
        user_id: str,
        user_token: str | None = None,
    ) -> None:
        super().__init__(user_token)
        self._user_id = user_id
        self._admin_client = get_service_client()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def records_to_csv_bytes(records: list[dict[str, Any]]) -> bytes:
        """Convert a list of record dicts to CSV bytes.

        Args:
            records: Row dicts with consistent keys.

        Returns:
            UTF-8 encoded CSV bytes with header row.
        """
        if not records:
            return b""

        df = pl.DataFrame(records)
        buf = io.BytesIO()
        df.write_csv(buf)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Export pipeline
    # ------------------------------------------------------------------

    async def export_table(
        self,
        table_name: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query table with RLS, generate CSV, upload to Storage.

        Args:
            table_name: Name of the table to export.
            filters: Optional dict of column -> value equality filters.

        Returns:
            Dict: ``{url, filename, size_bytes}``.

        Raises:
            ValueError: If ``table_name`` is not exportable.
        """
        if table_name not in EXPORTABLE_TABLES:
            msg = (
                f"Table '{table_name}' is not exportable. "
                f"Available: {', '.join(EXPORTABLE_TABLES)}"
            )
            raise ValueError(msg)

        # Query with RLS (uses anon key + user JWT)
        query = self.client.table(table_name).select("*")
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)

        result = await execute_async(query, op_name=f"data_export.query.{table_name}")
        records: list[dict[str, Any]] = result.data or []

        # Generate CSV bytes
        csv_bytes = self.records_to_csv_bytes(records)

        # Build storage path
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_{ts}.csv"
        storage_path = f"{self._user_id}/exports/{filename}"

        # Upload to Storage (blocking call wrapped in thread)
        await asyncio.to_thread(
            self._admin_client.storage.from_(BUCKET_NAME).upload,
            storage_path,
            csv_bytes,
            {"content-type": "text/csv; charset=utf-8"},
        )

        # Get signed URL
        url = await self._get_signed_url(storage_path)

        return {
            "url": url,
            "filename": filename,
            "size_bytes": len(csv_bytes),
        }

    async def _get_signed_url(self, path: str) -> str:
        """Create a signed download URL for a storage object.

        Args:
            path: Object path within the bucket.

        Returns:
            Signed URL string.
        """
        result = self._admin_client.storage.from_(BUCKET_NAME).create_signed_url(
            path, SIGNED_URL_EXPIRY_SECONDS
        )
        return result["signedURL"]

    # ------------------------------------------------------------------
    # Table info
    # ------------------------------------------------------------------

    @staticmethod
    def get_exportable_tables() -> dict[str, dict[str, Any]]:
        """Return the tables available for export."""
        return EXPORTABLE_TABLES
