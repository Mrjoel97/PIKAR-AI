# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""External database query service — PostgreSQL and BigQuery with safety guardrails.

Enforces read-only execution, 30-second query timeouts, and 1000-row result
caps on all external database queries. Connection string passwords are
sanitized before appearing in any exception message.

All heavy dependencies (psycopg2, google.cloud.bigquery) are lazy-imported
inside method bodies to prevent import-time failures on environments where
those libraries are not installed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Literal

logger = logging.getLogger(__name__)

# Maximum rows returned per query to prevent memory exhaustion
_MAX_ROWS = 1000

# Regex for stripping passwords from PostgreSQL DSNs in error messages
# Matches  user:password@  or  password=<value>  forms
_DSN_PASSWORD_RE = re.compile(
    r"(://[^:@]+:)([^@]+)(@)"  # URI form: //user:pass@host
    r"|"
    r"(password\s*=\s*)(\S+)",  # keyword form: password=secret
    re.IGNORECASE,
)


def _sanitize_dsn(message: str) -> str:
    """Replace plaintext passwords in connection strings with '***'.

    Args:
        message: Raw error or DSN string that may contain credentials.

    Returns:
        Sanitized string with password fields replaced.
    """
    return _DSN_PASSWORD_RE.sub(
        lambda m: (
            m.group(1) + "***" + m.group(3)
            if m.group(1)
            else m.group(4) + "***"
        ),
        message,
    )


class ExternalDbQueryService:
    """Safe, read-only query executor for external PostgreSQL and BigQuery databases.

    All query methods:
    - Enforce read-only session/transaction mode
    - Apply a 30-second statement timeout (server-side) plus an asyncio timeout
    - Cap results at 1000 rows
    - Sanitize connection credentials in error messages
    """

    # ------------------------------------------------------------------
    # SQL classification
    # ------------------------------------------------------------------

    def classify_sql(
        self, sql: str
    ) -> Literal["auto", "needs_confirmation"]:
        """Classify SQL complexity to determine whether user confirmation is needed.

        Simple ``SELECT`` statements run immediately.  Queries containing
        ``JOIN``, ``GROUP BY``, subqueries, ``UNION``, ``HAVING``, or CTEs
        (``WITH``) are flagged as complex and require explicit user confirmation
        before execution.

        Args:
            sql: SQL statement to classify.

        Returns:
            ``"auto"`` for simple queries, ``"needs_confirmation"`` for complex ones.
        """
        normalized = sql.lower()

        complex_indicators = [
            r"\bjoin\b",           # INNER JOIN, LEFT JOIN, etc.
            r"\bgroup\s+by\b",     # GROUP BY
            r"\bunion\b",          # UNION / UNION ALL
            r"\bhaving\b",         # HAVING
            r"\bwith\s+\w",        # CTE: WITH name AS (...)
        ]

        for pattern in complex_indicators:
            if re.search(pattern, normalized):
                return "needs_confirmation"

        # Subquery: nested SELECT not preceded by FROM/JOIN (i.e. a correlated subquery)
        # Simple heuristic: more than one SELECT keyword → subquery present
        if normalized.count("select") > 1:
            return "needs_confirmation"

        return "auto"

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------

    async def query_postgres(
        self,
        connection_string: str,
        sql: str,
        timeout_sec: int = 30,
    ) -> dict[str, Any]:
        """Execute a read-only SQL query against an external PostgreSQL database.

        Wraps a synchronous psycopg2 execution in ``asyncio.to_thread`` and
        applies an outer ``asyncio.wait_for`` timeout of ``timeout_sec + 2``
        seconds to handle cases where the server-side timeout is not honoured.

        Args:
            connection_string: PostgreSQL DSN (``postgresql://user:pass@host/db``).
            sql: SQL query to execute (must be a ``SELECT``).
            timeout_sec: Server-side and outer asyncio timeout in seconds.

        Returns:
            Dict with ``columns``, ``rows``, ``row_count``, and ``truncated`` keys.

        Raises:
            TimeoutError: When the query exceeds the configured timeout.
            RuntimeError: On database errors, with passwords stripped from message.
        """
        # Ensure SSL if not already specified
        if "sslmode" not in connection_string:
            sep = "&" if "?" in connection_string else "?"
            connection_string = f"{connection_string}{sep}sslmode=require"

        def _run_sync() -> dict[str, Any]:
            import psycopg2

            try:
                conn = psycopg2.connect(connection_string)
            except psycopg2.OperationalError as exc:
                sanitized = _sanitize_dsn(str(exc))
                raise RuntimeError(f"Database connection failed: {sanitized}") from None

            try:
                conn.set_session(readonly=True)
                with conn.cursor() as cur:
                    # Server-side timeout prevents runaway queries
                    cur.execute(f"SET statement_timeout = {timeout_sec * 1000}")
                    cur.execute(sql)

                    columns = (
                        [desc[0] for desc in cur.description]
                        if cur.description
                        else []
                    )
                    rows = cur.fetchmany(_MAX_ROWS)
                    truncated = len(rows) == _MAX_ROWS

                    return {
                        "columns": columns,
                        "rows": rows,
                        "row_count": len(rows),
                        "truncated": truncated,
                    }
            except psycopg2.OperationalError as exc:
                sanitized = _sanitize_dsn(str(exc))
                raise RuntimeError(f"Query failed: {sanitized}") from None
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        return await asyncio.wait_for(
            asyncio.to_thread(_run_sync),
            timeout=timeout_sec + 2,
        )

    # ------------------------------------------------------------------
    # BigQuery
    # ------------------------------------------------------------------

    async def query_bigquery(
        self,
        project_id: str,
        credentials_json: str,
        sql: str,
        timeout_sec: int = 30,
    ) -> dict[str, Any]:
        """Execute a read-only SQL query against Google BigQuery.

        Uses a service-account credentials JSON string to authenticate.
        Results are capped at 1000 rows.

        Args:
            project_id: GCP project ID.
            credentials_json: Service account JSON as a string.
            sql: Standard SQL query to execute.
            timeout_sec: Timeout passed to ``job.result(timeout=...)``.

        Returns:
            Dict with ``columns``, ``rows``, ``row_count``, and ``truncated`` keys.

        Raises:
            RuntimeError: On BigQuery API errors.
        """

        def _run_sync() -> dict[str, Any]:
            import google.cloud.bigquery as bq
            import google.oauth2.service_account as sa

            creds_info = json.loads(credentials_json)
            credentials = sa.Credentials.from_service_account_info(
                creds_info,
                scopes=["https://www.googleapis.com/auth/bigquery.readonly"],
            )
            client = bq.Client(project=project_id, credentials=credentials)

            try:
                job = client.query(sql)
                result_rows = job.result(timeout=timeout_sec)

                rows_list = []
                columns: list[str] = []
                for i, row in enumerate(result_rows):
                    if i == 0:
                        columns = list(row.keys())
                    if i >= _MAX_ROWS:
                        break
                    rows_list.append(list(row.values()))

                truncated = len(rows_list) == _MAX_ROWS

                return {
                    "columns": columns,
                    "rows": rows_list,
                    "row_count": len(rows_list),
                    "truncated": truncated,
                }
            except Exception as exc:
                raise RuntimeError(f"BigQuery query failed: {exc}") from exc
            finally:
                try:
                    client.close()
                except Exception:
                    pass

        return await asyncio.to_thread(_run_sync)

    # ------------------------------------------------------------------
    # Connectivity test
    # ------------------------------------------------------------------

    async def test_connection(
        self,
        provider: str,
        connection_string: str,
    ) -> dict[str, Any]:
        """Test whether a database connection can be established.

        For PostgreSQL: opens a read-only connection, runs ``SELECT version()``,
        and returns the server version string and database name.  Passwords are
        never included in error messages.

        For BigQuery: the ``connection_string`` is expected to be a service-
        account JSON string.  A ``SELECT 1`` query is executed to verify access.

        Args:
            provider: Database provider — ``"postgresql"`` or ``"bigquery"``.
            connection_string: PostgreSQL DSN or BigQuery service-account JSON.

        Returns:
            ``{"ok": True, "server_version": ..., "database": ...}`` on success,
            or ``{"ok": False, "error": "...sanitized..."}`` on failure.

        Raises:
            ValueError: For unsupported ``provider`` values.
        """
        if provider == "postgresql":
            return await self._test_postgres(connection_string)
        elif provider == "bigquery":
            return await self._test_bigquery(connection_string)
        else:
            return {"ok": False, "error": f"Unsupported provider: {provider}"}

    async def _test_postgres(self, connection_string: str) -> dict[str, Any]:
        """Execute a lightweight read-only connectivity check against PostgreSQL."""
        # Ensure SSL
        if "sslmode" not in connection_string:
            sep = "&" if "?" in connection_string else "?"
            connection_string = f"{connection_string}{sep}sslmode=require"

        def _run_sync() -> dict[str, Any]:
            import psycopg2

            try:
                conn = psycopg2.connect(connection_string)
            except psycopg2.OperationalError as exc:
                sanitized = _sanitize_dsn(str(exc))
                return {"ok": False, "error": f"Connection failed: {sanitized}"}

            try:
                conn.set_session(readonly=True)
                with conn.cursor() as cur:
                    cur.execute("SET statement_timeout = 10000")
                    cur.execute("SELECT version()")
                    row = cur.fetchone()
                    server_version = row[0] if row else "unknown"

                    # Extract database name from DSN if possible
                    database = "unknown"
                    try:
                        dsn_info = conn.dsn or ""
                        for part in dsn_info.split():
                            if part.startswith("dbname="):
                                database = part.split("=", 1)[1]
                    except Exception:
                        pass

                    return {
                        "ok": True,
                        "server_version": server_version,
                        "database": database,
                    }
            except psycopg2.OperationalError as exc:
                sanitized = _sanitize_dsn(str(exc))
                return {"ok": False, "error": f"Query failed: {sanitized}"}
            except Exception as exc:
                sanitized = _sanitize_dsn(str(exc))
                return {"ok": False, "error": f"Unexpected error: {sanitized}"}
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_run_sync),
                timeout=12,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "error": "Connection timed out after 10 seconds"}

    async def _test_bigquery(self, connection_string: str) -> dict[str, Any]:
        """Execute a lightweight connectivity check against BigQuery."""

        def _run_sync() -> dict[str, Any]:
            try:
                import json as _json

                import google.cloud.bigquery as bq
                import google.oauth2.service_account as sa

                creds_info = _json.loads(connection_string)
                project_id = creds_info.get("project_id", "")
                credentials = sa.Credentials.from_service_account_info(
                    creds_info,
                    scopes=["https://www.googleapis.com/auth/bigquery.readonly"],
                )
                client = bq.Client(project=project_id, credentials=credentials)
                try:
                    job = client.query("SELECT 1")
                    job.result(timeout=10)
                    return {"ok": True, "project_id": project_id}
                except Exception as exc:
                    return {"ok": False, "error": f"BigQuery query failed: {exc}"}
                finally:
                    try:
                        client.close()
                    except Exception:
                        pass
            except Exception as exc:
                return {"ok": False, "error": f"BigQuery connection failed: {exc}"}

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_run_sync),
                timeout=15,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "error": "BigQuery connection timed out"}

    # ------------------------------------------------------------------
    # Chart type suggestion
    # ------------------------------------------------------------------

    def suggest_chart_type(
        self,
        columns: list[str],
        rows: list[Any],
    ) -> str | None:
        """Suggest a chart type based on column names and sample data.

        Heuristics (checked in order):
        - One date-like column + one numeric column → ``"line"``
        - One string column + one numeric column → ``"bar"``
        - Two numeric columns → ``"scatter"``
        - Otherwise → ``None``

        Args:
            columns: Column names from the query result.
            rows: Sample rows (list of tuples or lists).

        Returns:
            Chart type string or ``None`` if no suitable type is detected.
        """
        if not columns or not rows:
            return None

        sample = rows[0]
        if len(columns) != len(sample):
            return None

        _DATE_KEYWORDS = {"date", "time", "created", "updated", "day", "month", "year", "week"}

        def _is_numeric(value: Any) -> bool:
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        def _is_date_col(col_name: str, value: Any) -> bool:
            name_lower = col_name.lower()
            has_date_keyword = any(kw in name_lower for kw in _DATE_KEYWORDS)
            is_date_str = isinstance(value, str) and bool(
                re.match(r"\d{4}-\d{2}-\d{2}", value)
            )
            return has_date_keyword or is_date_str

        if len(columns) == 2:
            col0, col1 = columns[0], columns[1]
            val0, val1 = sample[0], sample[1]

            # Date + numeric → line
            if _is_date_col(col0, val0) and _is_numeric(val1):
                return "line"
            if _is_date_col(col1, val1) and _is_numeric(val0):
                return "line"

            # Both numeric → scatter
            if _is_numeric(val0) and _is_numeric(val1):
                return "scatter"

            # String + numeric → bar
            if isinstance(val0, str) and _is_numeric(val1):
                return "bar"
            if isinstance(val1, str) and _is_numeric(val0):
                return "bar"

        return None
