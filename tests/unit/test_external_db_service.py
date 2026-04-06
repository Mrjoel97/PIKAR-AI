# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ExternalDbQueryService — read-only enforcement, timeouts, row cap."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


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

    def test_simple_select_is_auto(self):
        """Plain SELECT without JOINs/subqueries returns 'auto'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        assert svc.classify_sql("SELECT id, name FROM customers WHERE active = true") == "auto"

    def test_join_requires_confirmation(self):
        """SELECT with JOIN returns 'needs_confirmation'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        sql = "SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id"
        assert svc.classify_sql(sql) == "needs_confirmation"

    def test_group_by_requires_confirmation(self):
        """SELECT with GROUP BY returns 'needs_confirmation'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        sql = "SELECT status, COUNT(*) FROM orders GROUP BY status"
        assert svc.classify_sql(sql) == "needs_confirmation"

    def test_subquery_requires_confirmation(self):
        """Nested SELECT (subquery) returns 'needs_confirmation'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        sql = "SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE premium = true)"
        assert svc.classify_sql(sql) == "needs_confirmation"

    def test_union_requires_confirmation(self):
        """UNION query returns 'needs_confirmation'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        sql = "SELECT id FROM table_a UNION SELECT id FROM table_b"
        assert svc.classify_sql(sql) == "needs_confirmation"

    def test_having_requires_confirmation(self):
        """HAVING clause returns 'needs_confirmation'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        sql = "SELECT status, COUNT(*) FROM orders GROUP BY status HAVING COUNT(*) > 10"
        assert svc.classify_sql(sql) == "needs_confirmation"

    def test_cte_requires_confirmation(self):
        """WITH clause (CTE) returns 'needs_confirmation'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        sql = "WITH recent AS (SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days') SELECT * FROM recent"
        assert svc.classify_sql(sql) == "needs_confirmation"

    def test_case_insensitive_classification(self):
        """Keyword detection is case-insensitive."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        assert svc.classify_sql("SELECT a FROM t1 INNER JOIN t2 ON t1.id = t2.id") == "needs_confirmation"
        assert svc.classify_sql("select id from users") == "auto"


# ---------------------------------------------------------------------------
# ExternalDbQueryService — query_postgres
# ---------------------------------------------------------------------------


class TestQueryPostgres:
    """Read-only enforcement, timeout, and row-cap for PostgreSQL queries."""

    @pytest.mark.asyncio
    async def test_readonly_session_set(self):
        """set_session(readonly=True) must be called on the psycopg2 connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [(1, "Alice"), (2, "Bob")]

        with patch("psycopg2.connect", return_value=mock_conn):
            from app.services.external_db_service import ExternalDbQueryService

            svc = ExternalDbQueryService()
            await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id, name FROM users")

        mock_conn.set_session.assert_called_once_with(readonly=True)

    @pytest.mark.asyncio
    async def test_statement_timeout_set(self):
        """SET statement_timeout must be executed on the cursor with 30000ms."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.description = [("id",)]
        mock_cursor.fetchmany.return_value = [(1,)]

        with patch("psycopg2.connect", return_value=mock_conn):
            from importlib import reload

            import app.services.external_db_service as mod

            reload(mod)
            svc = mod.ExternalDbQueryService()
            await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id FROM t", timeout_sec=30)

        execute_calls = mock_cursor.execute.call_args_list
        timeout_calls = [c for c in execute_calls if "statement_timeout" in str(c)]
        assert len(timeout_calls) >= 1
        assert "30000" in str(timeout_calls[0])

    @pytest.mark.asyncio
    async def test_row_cap_1000(self):
        """fetchmany(1000) must be used to cap results at 1000 rows."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.description = [("id",)]
        mock_cursor.fetchmany.return_value = [(i,) for i in range(1000)]

        with patch("psycopg2.connect", return_value=mock_conn):
            from importlib import reload

            import app.services.external_db_service as mod

            reload(mod)
            svc = mod.ExternalDbQueryService()
            result = await svc.query_postgres("postgresql://user:pass@host/db", "SELECT id FROM big_table")

        mock_cursor.fetchmany.assert_called_with(1000)
        assert result["row_count"] == 1000

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Return dict must contain columns, rows, row_count, truncated keys."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [(1, "Alice")]

        with patch("psycopg2.connect", return_value=mock_conn):
            from importlib import reload

            import app.services.external_db_service as mod

            reload(mod)
            svc = mod.ExternalDbQueryService()
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
        import psycopg2

        with patch("psycopg2.connect", side_effect=psycopg2.OperationalError("could not connect to server")):
            from importlib import reload

            import app.services.external_db_service as mod

            reload(mod)
            svc = mod.ExternalDbQueryService()
            with pytest.raises(Exception) as exc_info:
                await svc.query_postgres(
                    "postgresql://myuser:s3cr3tpassword@host/db",
                    "SELECT 1",
                )

        error_str = str(exc_info.value)
        assert "s3cr3tpassword" not in error_str

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """asyncio.wait_for must raise TimeoutError when query exceeds timeout."""
        import asyncio

        def slow_connect(*args, **kwargs):
            """Simulate a slow connect by making to_thread hang."""
            import time

            time.sleep(10)
            return MagicMock()

        with patch("psycopg2.connect", side_effect=slow_connect):
            from importlib import reload

            import app.services.external_db_service as mod

            reload(mod)
            svc = mod.ExternalDbQueryService()
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
        mock_client_instance = MagicMock()
        mock_job = MagicMock()
        mock_row = MagicMock()
        mock_row.keys.return_value = ["id", "name"]
        mock_row.values.return_value = [1, "Alice"]
        mock_job.result.return_value = [mock_row]
        mock_client_instance.query.return_value = mock_job

        mock_bq_client_cls = MagicMock(return_value=mock_client_instance)
        mock_credentials = MagicMock()

        with (
            patch("google.cloud.bigquery.Client", mock_bq_client_cls),
            patch(
                "google.oauth2.service_account.Credentials.from_service_account_info",
                return_value=mock_credentials,
            ),
        ):
            from importlib import reload

            import app.services.external_db_service as mod

            reload(mod)
            svc = mod.ExternalDbQueryService()
            result = await svc.query_bigquery(
                project_id="my-project",
                credentials_json='{"type": "service_account"}',
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

    def test_string_plus_numeric_suggests_bar(self):
        """One string + one numeric column → 'bar'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = svc.suggest_chart_type(["category", "revenue"], [("Electronics", 5000), ("Clothing", 3000)])
        assert result == "bar"

    def test_two_numeric_suggests_scatter(self):
        """Two numeric columns → 'scatter'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = svc.suggest_chart_type(["price", "quantity"], [(10.5, 100), (20.0, 50)])
        assert result == "scatter"

    def test_date_plus_numeric_suggests_line(self):
        """Date-like column + numeric → 'line'."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = svc.suggest_chart_type(["date", "revenue"], [("2026-01-01", 1000)])
        assert result == "line"

    def test_unknown_pattern_returns_none(self):
        """Non-matching column pattern → None."""
        from app.services.external_db_service import ExternalDbQueryService

        svc = ExternalDbQueryService()
        result = svc.suggest_chart_type(["id", "name", "email"], [(1, "Alice", "a@b.com")])
        assert result is None
