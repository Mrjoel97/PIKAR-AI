# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""DocumentSourceService -- CRUD over the document_sources table.

The service backs the document-viewer feature, which stores a canonical
source-of-truth payload (JSON for structured docs, plus an optional rendered
binary URL and cached extracted text) per ``document_id``.

The service subclasses :class:`AsyncBaseService` so RLS policies are enforced
when a user JWT is supplied via the constructor.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.base_service import AsyncBaseService
from app.services.supabase_async import execute_async

_TABLE = "document_sources"


class DocumentSourceService(AsyncBaseService):
    """Read/write the ``document_sources`` table.

    Each row is a per-document canonical source plus rendered/extracted derivatives.
    All methods route through :meth:`AsyncBaseService.get_client` and
    :func:`execute_async`, so the same service works for user-scoped (JWT) and
    service-level callers.
    """

    async def create(
        self,
        *,
        user_id: str,
        document_id: str,
        doc_class: str,
        source: dict[str, Any] | None,
        binary_url: str | None,
        forked_from_upload: bool = False,
    ) -> dict[str, Any]:
        """Insert a new ``document_sources`` row and return the inserted record.

        Args:
            user_id: Owner user id (must match ``auth.uid()`` under RLS).
            document_id: Stable id linking the source to its parent document.
            doc_class: One of the allowed CHECK values (``report``, ``spreadsheet``,
                ``presentation``, ``word``, ``google_doc``, ``google_sheet``).
            source: Canonical structured payload (JSONB) or ``None`` when only
                a binary upload exists.
            binary_url: Optional URL to the rendered/uploaded binary asset.
            forked_from_upload: ``True`` when the row was created from a binary
                upload that was later structured into ``source``.

        Returns:
            The inserted row as a dict.
        """
        client = await self.get_client()
        payload = {
            "user_id": user_id,
            "document_id": document_id,
            "doc_class": doc_class,
            "source": source,
            "binary_url": binary_url,
            "forked_from_upload": forked_from_upload,
        }
        result = await execute_async(
            client.table(_TABLE).insert(payload),
            op_name="document_sources.create",
        )
        return result.data[0]

    async def get(self, document_id: str) -> dict[str, Any] | None:
        """Return the row for ``document_id`` or ``None`` if not present.

        Args:
            document_id: The document id to look up.

        Returns:
            The row as a dict, or ``None`` when no row exists.
        """
        client = await self.get_client()
        result = await execute_async(
            client.table(_TABLE)
            .select("*")
            .eq("document_id", document_id)
            .maybe_single(),
            op_name="document_sources.get",
        )
        return result.data if result.data else None

    async def update_source(
        self,
        *,
        document_id: str,
        new_source: dict[str, Any],
        new_binary_url: str | None,
    ) -> dict[str, Any]:
        """Update ``source`` (and optionally ``binary_url``) for ``document_id``.

        Args:
            document_id: The document id whose row is being updated.
            new_source: Replacement canonical source payload.
            new_binary_url: New binary URL, or ``None`` to leave the existing
                value untouched (the column is intentionally not written when
                ``None`` to avoid clobbering with NULL).

        Returns:
            The updated row as a dict.
        """
        client = await self.get_client()
        payload: dict[str, Any] = {"source": new_source}
        if new_binary_url is not None:
            payload["binary_url"] = new_binary_url
        result = await execute_async(
            client.table(_TABLE).update(payload).eq("document_id", document_id),
            op_name="document_sources.update_source",
        )
        return result.data[0]

    async def set_extracted_text(
        self,
        document_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Cache the extracted plain-text rendition of a document.

        Sets both ``extracted_text`` and ``extracted_at``. The ``updated_at``
        column is maintained automatically by the ``moddatetime`` trigger and
        must NOT be set manually.

        Args:
            document_id: The document id to update.
            text: Extracted plain-text content.

        Returns:
            The updated row as a dict.
        """
        client = await self.get_client()
        payload = {
            "extracted_text": text,
            "extracted_at": datetime.now(UTC).isoformat(),
        }
        result = await execute_async(
            client.table(_TABLE).update(payload).eq("document_id", document_id),
            op_name="document_sources.set_extracted_text",
        )
        return result.data[0]

    async def mark_forked_from_upload(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        """Flip ``forked_from_upload`` to ``True`` for ``document_id``.

        Used when a binary-only upload has been structured into a canonical
        ``source`` payload via the document viewer's "fork" workflow.

        Args:
            document_id: The document id to update.

        Returns:
            The updated row as a dict.
        """
        client = await self.get_client()
        result = await execute_async(
            client.table(_TABLE)
            .update({"forked_from_upload": True})
            .eq("document_id", document_id),
            op_name="document_sources.mark_forked_from_upload",
        )
        return result.data[0]


__all__ = ["DocumentSourceService"]
