"""Helpers for persisting spreadsheet connections used by scheduled reporting."""

from __future__ import annotations

from typing import Any

from app.services.supabase import get_service_client


class SpreadsheetConnectionService:
    """Persist and resolve spreadsheet connections for user-scoped reporting."""

    def __init__(self, supabase_client: Any | None = None):
        self._supabase = supabase_client

    @property
    def supabase(self) -> Any:
        if self._supabase is None:
            self._supabase = get_service_client()
        return self._supabase

    def upsert_connection(
        self,
        *,
        user_id: str,
        spreadsheet_id: str,
        spreadsheet_name: str,
        spreadsheet_url: str | None = None,
        metadata: dict[str, Any] | None = None,
        provider: str = "google_sheets",
    ) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "provider": provider,
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_url": spreadsheet_url,
            "metadata": metadata or {},
            "is_active": True,
        }
        result = (
            self.supabase.table("spreadsheet_connections")
            .upsert(
                payload,
                on_conflict="user_id,provider,spreadsheet_id",
            )
            .execute()
        )
        if result.data:
            return result.data[0]

        connection = self.get_connection(
            user_id=user_id,
            spreadsheet_id=spreadsheet_id,
            provider=provider,
        )
        return connection or payload

    def get_connection(
        self,
        *,
        user_id: str,
        spreadsheet_id: str,
        provider: str = "google_sheets",
    ) -> dict[str, Any] | None:
        result = (
            self.supabase.table("spreadsheet_connections")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .eq("spreadsheet_id", spreadsheet_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return (result.data or [None])[0]
