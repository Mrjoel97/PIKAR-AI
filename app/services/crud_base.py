"""Backward-compatible synchronous CRUD helper.

This module previously exposed ``CRUDService`` and some older tests/imports still
depend on it.  The implementation is intentionally small and defensive: on
errors it returns sentinel values instead of raising, matching the historical
behavior expected by the tests.
"""

from __future__ import annotations

import logging
from typing import Any, Optional


logger = logging.getLogger(__name__)


class CRUDService:
    """Minimal generic CRUD wrapper around a Supabase client table."""

    def __init__(self, client: Any, table_name: str):
        self.client = client
        self.table_name = table_name

    def create(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        try:
            resp = self.client.table(self.table_name).insert(data).execute()
            rows = getattr(resp, "data", None) or []
            if isinstance(rows, list):
                return rows[0] if rows else None
            if isinstance(rows, dict):
                return rows
            return None
        except Exception as exc:  # pragma: no cover - exercised via tests/mocks
            logger.warning("CRUD create failed for %s: %s", self.table_name, exc)
            return None

    def get_by_id(self, record_id: str, id_field: str = "id") -> Optional[dict[str, Any]]:
        try:
            resp = (
                self.client.table(self.table_name)
                .select("*")
                .eq(id_field, record_id)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            return rows[0] if rows else None
        except Exception as exc:  # pragma: no cover - exercised via tests/mocks
            logger.warning("CRUD get_by_id failed for %s: %s", self.table_name, exc)
            return None

    def delete(self, record_id: str, id_field: str = "id") -> bool:
        try:
            self.client.table(self.table_name).delete().eq(id_field, record_id).execute()
            return True
        except Exception as exc:  # pragma: no cover - exercised via tests/mocks
            logger.warning("CRUD delete failed for %s: %s", self.table_name, exc)
            return False

    def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        try:
            query = self.client.table(self.table_name).select("*", count="exact")
            for key, value in (filters or {}).items():
                query = query.eq(key, value)
            resp = query.limit(0).execute()
            count = getattr(resp, "count", None)
            if isinstance(count, int):
                return count
            rows = getattr(resp, "data", None) or []
            return len(rows) if isinstance(rows, list) else 0
        except Exception as exc:  # pragma: no cover - exercised via tests/mocks
            logger.warning("CRUD count failed for %s: %s", self.table_name, exc)
            return 0

    def exists(self, field: str, value: Any) -> bool:
        try:
            resp = (
                self.client.table(self.table_name)
                .select("id")
                .eq(field, value)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            return bool(rows)
        except Exception as exc:  # pragma: no cover - exercised via tests/mocks
            logger.warning("CRUD exists failed for %s: %s", self.table_name, exc)
            return False
