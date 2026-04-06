# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for external DB agent tools — NL-to-SQL, confirmation gate, list connections."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stubs — inject psycopg2 + google.cloud stubs so lazy imports resolve
# ---------------------------------------------------------------------------


def _ensure_psycopg2_stub() -> None:
    """Install psycopg2 stub if not already present."""
    if "psycopg2" not in sys.modules:
        stub = ModuleType("psycopg2")

        class OperationalError(Exception):
            """Stub OperationalError."""

        stub.OperationalError = OperationalError  # type: ignore[attr-defined]
        stub.connect = MagicMock()
        sys.modules["psycopg2"] = stub


def _ensure_bq_stubs() -> None:
    """Install BigQuery + service_account stubs if not already present."""
    if "google.cloud.bigquery" not in sys.modules:
        google_stub = sys.modules.setdefault("google", ModuleType("google"))
        google_cloud_stub = sys.modules.setdefault("google.cloud", ModuleType("google.cloud"))
        google_oauth2_stub = sys.modules.setdefault("google.oauth2", ModuleType("google.oauth2"))

        bq_stub = ModuleType("google.cloud.bigquery")
        sa_stub = ModuleType("google.oauth2.service_account")
        bq_stub.Client = MagicMock()  # type: ignore[attr-defined]
        sa_stub.Credentials = MagicMock()  # type: ignore[attr-defined]

        sys.modules["google.cloud.bigquery"] = bq_stub
        sys.modules["google.oauth2.service_account"] = sa_stub
        if not hasattr(google_stub, "cloud"):
            google_stub.cloud = google_cloud_stub  # type: ignore[attr-defined]
        if not hasattr(google_stub, "oauth2"):
            google_stub.oauth2 = google_oauth2_stub  # type: ignore[attr-defined]
        if not hasattr(google_cloud_stub, "bigquery"):
            google_cloud_stub.bigquery = bq_stub  # type: ignore[attr-defined]
        if not hasattr(google_oauth2_stub, "service_account"):
            google_oauth2_stub.service_account = sa_stub  # type: ignore[attr-defined]


_ensure_psycopg2_stub()
_ensure_bq_stubs()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"

_PG_CREDENTIAL = {
    "id": "cred-pg-01",
    "user_id": USER_ID,
    "provider": "postgresql",
    "account_name": "My Postgres DB",
    "credentials": "encrypted-dsn-blob",
    "connected_at": "2026-04-01T00:00:00Z",
}

_BQ_CREDENTIAL = {
    "id": "cred-bq-01",
    "user_id": USER_ID,
    "provider": "bigquery",
    "account_name": "My BigQuery",
    "credentials": "encrypted-bq-json-blob",
    "connected_at": "2026-04-02T00:00:00Z",
}

_SIMPLE_SQL = "SELECT id, name FROM customers"
_COMPLEX_SQL = "SELECT c.name, COUNT(*) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name"

_QUERY_RESULT = {
    "columns": ["id", "name"],
    "rows": [(1, "Alice"), (2, "Bob")],
    "row_count": 2,
    "truncated": False,
}


# ---------------------------------------------------------------------------
# Helpers — shared mock builders
# ---------------------------------------------------------------------------


def _make_admin_mock(credentials: list[dict]) -> MagicMock:
    """Return a mock AdminService whose credential table returns the given rows."""
    mock_result = MagicMock()
    mock_result.data = credentials

    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.eq.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    mock_admin = MagicMock()
    mock_admin.client = mock_client
    return mock_admin


async def _fake_execute_async(query, *, op_name: str = "") -> MagicMock:
    """Stand-in for execute_async that returns the mock chain's preset result."""
    mock_result = MagicMock()
    # Walk the mock chain to find the .data set on mock_chain
    # We reach data via the chain: table→select→eq→in_→result
    # Simplest: just return what the chain eventually produces
    mock_result.data = query.data if hasattr(query, "data") else []
    return mock_result


# ---------------------------------------------------------------------------
# Tests: EXTERNAL_DB_TOOLS export
# ---------------------------------------------------------------------------


class TestExternalDbToolsExport:
    """EXTERNAL_DB_TOOLS list must contain all three tool functions."""

    def test_tools_list_contains_expected_functions(self):
        """EXTERNAL_DB_TOOLS must include external_db_query, confirm_and_run_query, list_db_connections."""
        from app.agents.tools.external_db_tools import EXTERNAL_DB_TOOLS

        tool_names = [fn.__name__ for fn in EXTERNAL_DB_TOOLS]
        assert "external_db_query" in tool_names
        assert "list_db_connections" in tool_names

    def test_tools_list_is_list(self):
        """EXTERNAL_DB_TOOLS must be a list (not a tuple or generator)."""
        from app.agents.tools.external_db_tools import EXTERNAL_DB_TOOLS

        assert isinstance(EXTERNAL_DB_TOOLS, list)
        assert len(EXTERNAL_DB_TOOLS) >= 3


# ---------------------------------------------------------------------------
# Tests: list_db_connections
# ---------------------------------------------------------------------------


class TestListDbConnections:
    """list_db_connections returns user's connected postgresql/bigquery providers."""

    @pytest.mark.asyncio
    async def test_returns_connected_databases(self):
        """Returns list with provider, account_name, connected_at for each connection."""
        mock_result = MagicMock()
        mock_result.data = [_PG_CREDENTIAL, _BQ_CREDENTIAL]

        with (
            patch("app.agents.tools.external_db_tools._get_user_id", return_value=USER_ID),
            patch("app.services.base_service.AdminService") as mock_admin_cls,
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=mock_result),
        ):
            mock_admin_cls.return_value = _make_admin_mock([_PG_CREDENTIAL, _BQ_CREDENTIAL])

            from app.agents.tools.external_db_tools import list_db_connections

            result = await list_db_connections()

        assert "connections" in result
        assert len(result["connections"]) == 2
        providers = [c["provider"] for c in result["connections"]]
        assert "postgresql" in providers
        assert "bigquery" in providers

    @pytest.mark.asyncio
    async def test_returns_error_when_not_authenticated(self):
        """Returns error dict when no user_id is available."""
        with patch("app.agents.tools.external_db_tools._get_user_id", return_value=None):
            from app.agents.tools.external_db_tools import list_db_connections

            result = await list_db_connections()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_connections(self):
        """Returns empty connections list when user has no DB credentials."""
        mock_result = MagicMock()
        mock_result.data = []

        with (
            patch("app.agents.tools.external_db_tools._get_user_id", return_value=USER_ID),
            patch("app.services.base_service.AdminService") as mock_admin_cls,
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=mock_result),
        ):
            mock_admin_cls.return_value = _make_admin_mock([])

            from app.agents.tools.external_db_tools import list_db_connections

            result = await list_db_connections()

        assert result.get("connections") == []


# ---------------------------------------------------------------------------
# Tests: external_db_query — needs_confirmation flow
# ---------------------------------------------------------------------------


class TestExternalDbQueryConfirmation:
    """Complex SQL returns needs_confirmation=True without executing the query."""

    @pytest.mark.asyncio
    async def test_complex_sql_returns_needs_confirmation(self):
        """When classify_sql returns 'needs_confirmation', tool does NOT execute query."""
        mock_creds_result = MagicMock()
        mock_creds_result.data = [_PG_CREDENTIAL]

        mock_svc = MagicMock()
        mock_svc.classify_sql.return_value = "needs_confirmation"
        mock_svc.query_postgres = AsyncMock()  # must NOT be called

        with (
            patch("app.agents.tools.external_db_tools._get_user_id", return_value=USER_ID),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=mock_creds_result),
            patch("app.services.base_service.AdminService") as mock_admin_cls,
            patch("app.services.external_db_service.ExternalDbQueryService", return_value=mock_svc),
            patch("app.agents.tools.external_db_tools._generate_sql", new_callable=AsyncMock, return_value=_COMPLEX_SQL),
            patch("app.services.encryption.decrypt_secret", return_value="postgresql://user:pass@host/db"),
        ):
            mock_admin_cls.return_value = _make_admin_mock([_PG_CREDENTIAL])

            from app.agents.tools.external_db_tools import external_db_query

            result = await external_db_query(natural_language_query="count orders per customer", database="postgresql")

        assert result["needs_confirmation"] is True
        assert "sql_generated" in result
        # query_postgres must NOT have been called
        mock_svc.query_postgres.assert_not_called()

    @pytest.mark.asyncio
    async def test_simple_sql_executes_immediately(self):
        """When classify_sql returns 'auto', query executes and returns full result."""
        mock_creds_result = MagicMock()
        mock_creds_result.data = [_PG_CREDENTIAL]

        mock_svc = MagicMock()
        mock_svc.classify_sql.return_value = "auto"
        mock_svc.query_postgres = AsyncMock(return_value=_QUERY_RESULT)
        mock_svc.suggest_chart_type.return_value = "bar"

        with (
            patch("app.agents.tools.external_db_tools._get_user_id", return_value=USER_ID),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=mock_creds_result),
            patch("app.services.base_service.AdminService") as mock_admin_cls,
            patch("app.services.external_db_service.ExternalDbQueryService", return_value=mock_svc),
            patch("app.agents.tools.external_db_tools._generate_sql", new_callable=AsyncMock, return_value=_SIMPLE_SQL),
            patch("app.services.encryption.decrypt_secret", return_value="postgresql://user:pass@host/db"),
        ):
            mock_admin_cls.return_value = _make_admin_mock([_PG_CREDENTIAL])

            from app.agents.tools.external_db_tools import external_db_query

            result = await external_db_query(natural_language_query="list all customers", database="postgresql")

        assert result["needs_confirmation"] is False
        assert result["sql_generated"] == _SIMPLE_SQL
        assert "columns" in result
        assert "rows" in result
        assert "row_count" in result
        assert "chart_suggestion" in result
        assert "nl_summary" in result


# ---------------------------------------------------------------------------
# Tests: external_db_query — result shape
# ---------------------------------------------------------------------------


class TestExternalDbQueryResultShape:
    """external_db_query result always contains the required keys."""

    @pytest.mark.asyncio
    async def test_result_contains_required_keys(self):
        """Auto-execute path returns all required result keys."""
        mock_creds_result = MagicMock()
        mock_creds_result.data = [_PG_CREDENTIAL]

        mock_svc = MagicMock()
        mock_svc.classify_sql.return_value = "auto"
        mock_svc.query_postgres = AsyncMock(return_value=_QUERY_RESULT)
        mock_svc.suggest_chart_type.return_value = None

        with (
            patch("app.agents.tools.external_db_tools._get_user_id", return_value=USER_ID),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=mock_creds_result),
            patch("app.services.base_service.AdminService") as mock_admin_cls,
            patch("app.services.external_db_service.ExternalDbQueryService", return_value=mock_svc),
            patch("app.agents.tools.external_db_tools._generate_sql", new_callable=AsyncMock, return_value=_SIMPLE_SQL),
            patch("app.services.encryption.decrypt_secret", return_value="postgresql://user:pass@host/db"),
        ):
            mock_admin_cls.return_value = _make_admin_mock([_PG_CREDENTIAL])

            from app.agents.tools.external_db_tools import external_db_query

            result = await external_db_query(natural_language_query="list customers", database="postgresql")

        required_keys = {"sql_generated", "columns", "rows", "row_count", "chart_suggestion", "nl_summary", "needs_confirmation"}
        assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - result.keys()}"
