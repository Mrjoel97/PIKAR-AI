# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ExternalDbQueryService — read-only enforcement, timeouts, row cap."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — inject fake psycopg2 and google.cloud.bigquery stubs
# ---------------------------------------------------------------------------


def _make_psycopg2_stub() -> ModuleType:
    """Return a minimal psycopg2 stub injected into sys.modules."""
    stub = ModuleType("psycopg2")

    class OperationalError(Exception):
        """Stub OperationalError."""

    stub.OperationalError = OperationalError  # type: ignore[attr-defined]
    stub.connect = MagicMock()
    return stub


def _install_psycopg2_stub() -> ModuleType:
    """Inject psycopg2 stub into sys.modules so lazy imports resolve."""
    stub = _make_psycopg2_stub()
    sys.modules.setdefault("psycopg2", stub)
    return sys.modules["psycopg2"]  # type: ignore[return-value]


def _make_bq_stub() -> tuple[ModuleType, ModuleType]:
    """Return (google.cloud.bigquery stub, google.oauth2.service_account stub)."""
    bq_stub = ModuleType("google.cloud.bigquery")
    sa_stub = ModuleType("google.oauth2.service_account")

    mock_creds = MagicMock()
    sa_stub.Credentials = MagicMock()  # type: ignore[attr-defined]
    sa_stub.Credentials.from_service_account_info = MagicMock(return_value=mock_creds)

    bq_stub.Client = MagicMock()  # type: ignore[attr-defined]

    return bq_stub, sa_stub


def _install_bq_stubs() -> tuple[ModuleType, ModuleType]:
    """Inject BigQuery + service_account stubs into sys.modules."""
    bq_stub, sa_stub = _make_bq_stub()

    google_stub = sys.modules.setdefault("google", ModuleType("google"))
    google_cloud_stub = sys.modules.setdefault("google.cloud", ModuleType("google.cloud"))
    google_oauth2_stub = sys.modules.setdefault("google.oauth2", ModuleType("google.oauth2"))

    if not hasattr(google_stub, "cloud"):
        google_stub.cloud = google_cloud_stub  # type: ignore[attr-defined]
    if not hasattr(google_stub, "oauth2"):
        google_stub.oauth2 = google_oauth2_stub  # type: ignore[attr-defined]

    sys.modules["google.cloud.bigquery"] = bq_stub
    sys.modules["google.oauth2.service_account"] = sa_stub

    if not hasattr(google_cloud_stub, "bigquery"):
        google_cloud_stub.bigquery = bq_stub  # type: ignore[attr-defined]
    if not hasattr(google_oauth2_stub, "service_account"):
        google_oauth2_stub.service_account = sa_stub  # type: ignore[attr-defined]

    return bq_stub, sa_stub


# Install both stubs at module load time so all tests can import freely
_install_psycopg2_stub()
_install_bq_stubs()


# ---------------------------------------------------------------------------
# Provider registry tests
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    """Verify provider registrations in integration_providers.py."""

    def test_postgresql_registered_with_api_key(self):
        """postgresql provider must exist in PROVIDER_REGISTRY with api_key auth."""
        from app.config.integration_providers import PROVIDER_REGISTRY

        assert "postgresql" in PROVIDER_REGISTRY
        cfg = PROVIDER_REGISTRY["postgresql"]
        assert cfg.auth_type == "api_key"
        assert cfg.category == "analytics"

    def test_bigquery_has_readonly_scope(self):
        """bigquery provider must include the bigquery.readonly scope."""
        from app.config.integration_providers import PROVIDER_REGISTRY

        assert "bigquery" in PROVIDER_REGISTRY
        scopes = PROVIDER_REGISTRY["bigquery"].scopes
        assert any("bigquery.readonly" in s for s in scopes)


# ---------------------------------------------------------------------------
# ExternalDbQueryService — classify_sql
# ---------------------------------------------------------------------------


class TestClassifySql:
    """SQL classification heuristic distinguishes simple vs complex queries."""

    def _svc(self):
        from app.services.external_db_service import ExternalDbQueryService

        return ExternalDbQueryService()

    def test_simple_select_is_auto(self):
        """Plain SELECT without JOINs/subqueries returns 'auto'."""
        assert self._svc().classify_sql("SELECT id, name FROM customers WHERE active = true") == "auto"

    def test_join_requires_confirmation(self):
        """SELECT with JOIN returns 'needs_confirmation'."""
        sql = "SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id"
        assert self._svc().classify_sql(sql) == "needs_confirmation"

    def test_group_by_requires_confirmation(self):
        """SELECT with GROUP BY returns 'needs_confirmation'."""
        sql = "SELECT status, COUNT(*) FROM orders GROUP BY status"
        assert self._svc().classify_sql(sql) == "needs_confirmation"

    def test_subquery_requires_confirmation(self):
        """Nested SELECT (subquery) returns 'needs_confirmation'."""
        sql = "SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE premium = true)"
        assert self._svc().classify_sql(sql) == "needs_confirmation"

    def test_union_requires_confirmation(self):
        """UNION query returns 'needs_confirmation'."""
        sql = "SELECT id FROM table_a UNION SELECT id FROM table_b"
        assert self._svc().classify_sql(sql) == "needs_confirmation"

    def test_having_requires_confirmation(self):
        """HAVING clause returns 'needs_confirmation'."""
        sql = "SELECT status, COUNT(*) FROM orders GROUP BY status HAVING COUNT(*) > 10"
        assert self._svc().classify_sql(sql) == "needs_confirmation"

    def test_cte_requires_confirmation(self):
        """WITH clause (CTE) returns 'needs_confirmation'."""
        sql = (
            "WITH recent AS (SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days') "
            "SELECT * FROM recent"
        )
        assert self._svc().classify_sql(sql) == "needs_confirmation"

    def test_case_insensitive_classification(self):
        """Keyword detection is case-insensitive."""
        assert self._svc().classify_sql("SELECT a FROM t1 INNER JOIN t2 ON t1.id = t2.id") == "needs_confirmation"
        assert self._svc().classify_sql("select id from users") == "auto"


# ---------------------------------------------------------------------------
# ExternalDbQueryService — query_postgres
# ---------------------------------------------------------------------------


def _build_pg_mocks():
    """Return (mock_conn, mock_cursor) wired for context-manager use."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Wire cursor() to work as both context manager and direct call
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


class TestQueryPostgres:
    """Read-only enforcement, timeout, and row-cap for PostgreSQL queries."""

    @pytest.mark.asyncio
    async def test_readonly_session_set(self):
        """set_session(readonly=True) must be called on the psycopg2 connection."""
        mock_conn, mock_cursor = _build_pg_mocks()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [(1, "Alice"), (2, "Bob")]

        psycopg2_mod = sys.modules["psycopg2"]
        psycopg2_mod.connect = MagicMock(return_value=mock_conn)  # type: ignore[attr-defined]

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id, name FROM users")

        mock_conn.set_session.assert_called_once_with(readonly=True)

    @pytest.mark.asyncio
    async def test_statement_timeout_set(self):
        """SET statement_timeout must be executed on the cursor with 30000ms."""
        mock_conn, mock_cursor = _build_pg_mocks()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchmany.return_value = [(1,)]

        psycopg2_mod = sys.modules["psycopg2"]
        psycopg2_mod.connect = MagicMock(return_value=mock_conn)  # type: ignore[attr-defined]

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id FROM t", timeout_sec=30)

        execute_calls = mock_cursor.execute.call_args_list
        timeout_calls = [c for c in execute_calls if "statement_timeout" in str(c)]
        assert len(timeout_calls) >= 1, "statement_timeout SET not found in execute calls"
        assert "30000" in str(timeout_calls[0])

    @pytest.mark.asyncio
    async def test_row_cap_1000(self):
        """fetchmany(1000) must be used to cap results at 1000 rows."""
        mock_conn, mock_cursor = _build_pg_mocks()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchmany.return_value = [(i,) for i in range(1000)]

        psycopg2_mod = sys.modules["psycopg2"]
        psycopg2_mod.connect = MagicMock(return_value=mock_conn)  # type: ignore[attr-defined]

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id FROM big_table")

        mock_cursor.fetchmany.assert_called_with(1000)
        assert result["row_count"] == 1000

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Return dict must contain columns, rows, row_count, truncated keys."""
        mock_conn, mock_cursor = _build_pg_mocks()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [(1, "Alice")]

        psycopg2_mod = sys.modules["psycopg2"]
        psycopg2_mod.connect = MagicMock(return_value=mock_conn)  # type: ignore[attr-defined]

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id, name FROM users")

        assert "columns" in result
        assert "rows" in result
        assert "row_count" in result
        assert "truncated" in result
        assert result["columns"] == ["id", "name"]
        assert result["rows"] == [(1, "Alice")]
        assert result["row_count"] == 1

    @pytest.mark.asyncio
    async def test_password_sanitized_in_error(self):
        """OperationalError must not expose plaintext password in re-raised exception."""
        psycopg2_mod = sys.modules["psycopg2"]
        OperationalError = psycopg2_mod.OperationalError  # type: ignore[attr-defined]
        psycopg2_mod.connect = MagicMock(side_effect=OperationalError("could not connect to server"))  # type: ignore[attr-defined]

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        with pytest.raises(Exception) as exc_info:
            await svc.query_postgres(
                "postgresql://myuser:s3cr3tpassword@host/db",
                "SELECT 1",
            )

        assert "s3cr3tpassword" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """asyncio.wait_for raises TimeoutError when query exceeds timeout."""
        import asyncio

        def _slow_connect(*args, **kwargs):
            import time
            time.sleep(10)
            return MagicMock()

        psycopg2_mod = sys.modules["psycopg2"]
        psycopg2_mod.connect = MagicMock(side_effect=_slow_connect)  # type: ignore[attr-defined]

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await asyncio.wait_for(
                svc.query_postgres("postgresql://user:pass@host/db", "SELECT 1", timeout_sec=1),
                timeout=2,
            )


# ---------------------------------------------------------------------------
# ExternalDbQueryService — query_bigquery
# ---------------------------------------------------------------------------


class TestQueryBigQuery:
    """Timeout and result format for BigQuery queries."""

    @pytest.mark.asyncio
    async def test_bigquery_timeout_passed(self):
        """timeout=30 must be passed to the BigQuery job.result() call."""
        bq_stub = sys.modules["google.cloud.bigquery"]
        sa_stub = sys.modules["google.oauth2.service_account"]

        mock_client_instance = MagicMock()
        mock_job = MagicMock()

        # Simulate one row returned
        mock_row = MagicMock()
        mock_row.keys.return_value = ["id", "name"]
        mock_row.values.return_value = [1, "Alice"]
        mock_job.result.return_value = [mock_row]
        mock_client_instance.query.return_value = mock_job

        bq_stub.Client = MagicMock(return_value=mock_client_instance)  # type: ignore[attr-defined]
        mock_creds = MagicMock()
        sa_stub.Credentials = MagicMock()  # type: ignore[attr-defined]
        sa_stub.Credentials.from_service_account_info = MagicMock(return_value=mock_creds)

        import json

        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = await svc.query_bigquery(
            project_id="my-project",
            credentials_json=json.dumps({"type": "service_account"}),
            sql="SELECT id, name FROM dataset.table",
            timeout_sec=30,
        )

        mock_job.result.assert_called_once_with(timeout=30)
        assert "columns" in result
        assert "rows" in result
        assert "row_count" in result


# ---------------------------------------------------------------------------
# ExternalDbQueryService — suggest_chart_type
# ---------------------------------------------------------------------------


class TestSuggestChartType:
    """Chart type heuristic based on column types."""

    def _svc(self):
        from app.services.external_db_service import ExternalDbQueryService

        return ExternalDbQueryService()

    def test_string_plus_numeric_suggests_bar(self):
        """One string + one numeric column → 'bar'."""
        result = self._svc().suggest_chart_type(
            ["category", "revenue"], [("Electronics", 5000), ("Clothing", 3000)]
        )
        assert result == "bar"

    def test_two_numeric_suggests_scatter(self):
        """Two numeric columns → 'scatter'."""
        result = self._svc().suggest_chart_type(
            ["price", "quantity"], [(10.5, 100), (20.0, 50)]
        )
        assert result == "scatter"

    def test_date_plus_numeric_suggests_line(self):
        """Date-like column + numeric → 'line'."""
        result = self._svc().suggest_chart_type(["date", "revenue"], [("2026-01-01", 1000)])
        assert result == "line"

    def test_unknown_pattern_returns_none(self):
        """Non-matching column pattern → None."""
        result = self._svc().suggest_chart_type(
            ["id", "name", "email"], [(1, "Alice", "a@b.com")]
        )
        assert result is None
