# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""DocumentVersionService -- CRUD over the document_versions table.

The service backs the document-viewer feature, which keeps a per-document
version chain. Each row pairs a structured ``source_snapshot`` (JSONB) with a
rendered ``binary_url``, an optional ``diff_summary``, and a ``created_by``
attribution (``agent``/``user``/``system``).

The service subclasses :class:`AsyncBaseService` so RLS policies are enforced
when a user JWT is supplied via the constructor.
"""

from __future__ import annotations

from typing import Any

from app.services.base_service import AsyncBaseService
from app.services.supabase_async import execute_async

_TABLE = "document_versions"

_ALLOWED_CREATED_BY = frozenset({"agent", "user", "system"})


class DocumentVersionService(AsyncBaseService):
    """Read/write the ``document_versions`` table.

    Each row is one version in a per-document version chain. All methods
    route through :meth:`AsyncBaseService.get_client` and
    :func:`execute_async`, so the same service works for user-scoped (JWT)
    and service-level callers.
    """

    async def append(
        self,
        *,
        document_id: str,
        user_id: str,
        source_snapshot: dict[str, Any],
        binary_url: str,
        diff_summary: str | None,
        created_by: str,
    ) -> dict[str, Any]:
        """Insert a new ``document_versions`` row and return the inserted record.

        Args:
            document_id: Parent document id (FK to ``document_sources``).
            user_id: Owning user id (must match ``auth.uid()`` under RLS).
            source_snapshot: Canonical structured payload for this version
                (NOT NULL per schema).
            binary_url: URL to the rendered binary asset for this version
                (NOT NULL per schema).
            diff_summary: Optional human-readable diff vs. the prior version.
            created_by: One of ``agent``, ``user``, ``system`` (matches the
                schema CHECK constraint).

        Returns:
            The inserted row as a dict.

        Raises:
            ValueError: If ``created_by`` is not one of the allowed values,
                or if the insert returned no data.
        """
        if created_by not in _ALLOWED_CREATED_BY:
            raise ValueError(
                f"created_by must be one of {sorted(_ALLOWED_CREATED_BY)!r}, "
                f"got {created_by!r}"
            )

        client = await self.get_client()
        payload = {
            "document_id": document_id,
            "user_id": user_id,
            "source_snapshot": source_snapshot,
            "binary_url": binary_url,
            "diff_summary": diff_summary,
            "created_by": created_by,
        }
        result = await execute_async(
            client.table(_TABLE).insert(payload),
            op_name="document_versions.append",
        )
        if not result.data:
            raise ValueError(
                f"append_version returned no data for document_id={document_id!r}"
            )
        return result.data[0]

    async def list(
        self,
        document_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` versions for ``document_id``, newest first.

        An empty list is a valid response (the document has no versions yet)
        and is NOT treated as an error.

        Args:
            document_id: The parent document id to filter on.
            limit: Maximum number of versions to return. Defaults to 10.

        Returns:
            A list of version rows ordered by ``created_at`` descending.
        """
        client = await self.get_client()
        result = await execute_async(
            client.table(_TABLE)
            .select("*")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="document_versions.list",
        )
        return result.data or []

    async def get(self, version_id: str) -> dict[str, Any] | None:
        """Return the version row for ``version_id`` or ``None`` if not present.

        Args:
            version_id: The version id (primary key of ``document_versions``).

        Returns:
            The row as a dict, or ``None`` when no row exists.
        """
        client = await self.get_client()
        result = await execute_async(
            client.table(_TABLE).select("*").eq("id", version_id).maybe_single(),
            op_name="document_versions.get",
        )
        return result.data if result.data else None


__all__ = ["DocumentVersionService"]
