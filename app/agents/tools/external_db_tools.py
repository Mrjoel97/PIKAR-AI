# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""External database agent tools — NL-to-SQL query execution and connection listing.

Provides three agent-callable functions that let users query their connected
PostgreSQL or BigQuery databases in natural language.

Flow:
1. ``list_db_connections`` — shows which databases the user has connected.
2. ``external_db_query`` — translates a natural language question to SQL,
   classifies complexity, and either auto-executes (simple) or returns a
   confirmation request (complex).
3. ``confirm_and_run_query`` — executes pre-confirmed complex SQL directly.

All tools use lazy imports and ``_get_user_id()`` from request context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Providers treated as external databases
_DB_PROVIDERS = ["postgresql", "bigquery"]

# SQL generation system prompt — injected with schema info at call time
_SQL_SYSTEM_PROMPT = """\
You are a SQL expert. Generate a single, correct SELECT statement that answers
the user's question based on the schema provided.

Rules:
- Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, or any DDL.
- Return ONLY the SQL statement. No explanations, no markdown code fences.
- Use standard ANSI SQL compatible with the target database.
- Alias columns with descriptive names when helpful.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def _generate_sql(natural_language_query: str, provider: str = "postgresql") -> str:
    """Generate a SELECT SQL statement from a natural language query via Gemini.

    Args:
        natural_language_query: The user's question in plain English.
        provider: Target database type for dialect hints.

    Returns:
        Generated SQL string (SELECT only).
    """
    try:
        import google.generativeai as genai

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=_SQL_SYSTEM_PROMPT,
        )
        prompt = f"Database type: {provider}\n\nQuestion: {natural_language_query}"
        response = model.generate_content(prompt)
        sql = response.text.strip()
        # Strip markdown fences if the model added them anyway
        if sql.startswith("```"):
            lines = sql.splitlines()
            sql = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()
        return sql
    except Exception as exc:
        logger.warning("SQL generation failed, using fallback: %s", exc)
        # Safe fallback — agent will surface this to the user
        return f"-- SQL generation failed: {exc}"


async def _get_db_credentials(user_id: str) -> list[dict[str, Any]]:
    """Fetch postgresql/bigquery credentials for the user.

    Args:
        user_id: Authenticated user UUID.

    Returns:
        List of credential rows from ``integration_credentials``.
    """
    from app.services.base_service import AdminService
    from app.services.supabase_async import execute_async

    admin = AdminService()
    result = await execute_async(
        admin.client.table("integration_credentials")
        .select("id, provider, account_name, credentials, connected_at")
        .eq("user_id", user_id)
        .in_("provider", _DB_PROVIDERS),
        op_name="external_db_tools.get_credentials",
    )
    return result.data or []


# ---------------------------------------------------------------------------
# Tool 1: external_db_query
# ---------------------------------------------------------------------------


async def external_db_query(
    natural_language_query: str,
    database: str | None = None,
) -> dict[str, Any]:
    """Query an external database using natural language.

    Translates the question to SQL via Gemini, classifies complexity, and
    either executes immediately (simple queries) or returns a confirmation
    request (complex queries involving JOINs, GROUP BY, subqueries, etc.).

    Args:
        natural_language_query: The user's question in plain English.
        database: Provider key to use (``"postgresql"`` or ``"bigquery"``).
            If omitted and multiple connections exist, the user is prompted
            to choose.

    Returns:
        On auto-execute: dict with ``sql_generated``, ``columns``, ``rows``,
        ``row_count``, ``chart_suggestion``, ``nl_summary``, ``needs_confirmation=False``.

        On complex query: dict with ``needs_confirmation=True``, ``sql_generated``,
        and ``explanation``.

        On error: dict with ``error`` key.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.encryption import decrypt_secret
        from app.services.external_db_service import ExternalDbQueryService

        credentials = await _get_db_credentials(user_id)

        if not credentials:
            return {
                "error": (
                    "No external databases connected. "
                    "Use the Configuration page to connect a PostgreSQL or BigQuery database."
                ),
                "connections": [],
            }

        # Filter to the requested provider if specified
        if database:
            matching = [c for c in credentials if c["provider"] == database]
            if not matching:
                available = [c["provider"] for c in credentials]
                return {
                    "error": (
                        f"No '{database}' connection found. "
                        f"Connected databases: {available}"
                    ),
                }
            cred = matching[0]
        elif len(credentials) == 1:
            cred = credentials[0]
        else:
            # Multiple connections — ask user to choose
            return {
                "needs_selection": True,
                "message": "Multiple databases connected. Please specify which to use.",
                "available_databases": [
                    {"provider": c["provider"], "name": c["account_name"]}
                    for c in credentials
                ],
            }

        provider = cred["provider"]

        # Generate SQL from natural language
        sql = await _generate_sql(natural_language_query, provider=provider)

        svc = ExternalDbQueryService()
        complexity = svc.classify_sql(sql)

        if complexity == "needs_confirmation":
            return {
                "needs_confirmation": True,
                "sql_generated": sql,
                "explanation": (
                    "This query involves JOINs, aggregations, or subqueries. "
                    "Please review the SQL above and use confirm_and_run_query() to execute."
                ),
            }

        # Auto-execute simple query
        raw_creds = decrypt_secret(cred["credentials"])
        query_result = await _execute_for_provider(svc, provider, cred, raw_creds, sql)

        if "error" in query_result:
            return query_result

        chart = svc.suggest_chart_type(query_result["columns"], query_result["rows"])
        row_count = query_result["row_count"]
        nl_summary = f"Found {row_count} row{'s' if row_count != 1 else ''}."
        if query_result.get("truncated"):
            nl_summary += " Results are truncated at 1000 rows."

        return {
            "sql_generated": sql,
            "columns": query_result["columns"],
            "rows": query_result["rows"],
            "row_count": row_count,
            "chart_suggestion": chart,
            "nl_summary": nl_summary,
            "needs_confirmation": False,
        }

    except Exception as exc:
        logger.exception("external_db_query failed for user=%s", user_id)
        return {"error": f"Query failed: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: confirm_and_run_query
# ---------------------------------------------------------------------------


async def confirm_and_run_query(
    sql: str,
    database: str | None = None,
) -> dict[str, Any]:
    """Execute a pre-confirmed complex SQL query.

    Used after the user reviews and approves a complex query returned by
    ``external_db_query`` with ``needs_confirmation=True``.

    Args:
        sql: The SQL statement to execute (no re-generation — runs as-is).
        database: Provider key (``"postgresql"`` or ``"bigquery"``).

    Returns:
        Same result format as ``external_db_query`` auto-execute path.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.encryption import decrypt_secret
        from app.services.external_db_service import ExternalDbQueryService

        credentials = await _get_db_credentials(user_id)

        if not credentials:
            return {"error": "No external databases connected."}

        if database:
            matching = [c for c in credentials if c["provider"] == database]
            cred = matching[0] if matching else credentials[0]
        else:
            cred = credentials[0]

        provider = cred["provider"]
        raw_creds = decrypt_secret(cred["credentials"])

        svc = ExternalDbQueryService()
        query_result = await _execute_for_provider(svc, provider, cred, raw_creds, sql)

        if "error" in query_result:
            return query_result

        chart = svc.suggest_chart_type(query_result["columns"], query_result["rows"])
        row_count = query_result["row_count"]
        nl_summary = f"Found {row_count} row{'s' if row_count != 1 else ''}."
        if query_result.get("truncated"):
            nl_summary += " Results are truncated at 1000 rows."

        return {
            "sql_generated": sql,
            "columns": query_result["columns"],
            "rows": query_result["rows"],
            "row_count": row_count,
            "chart_suggestion": chart,
            "nl_summary": nl_summary,
            "needs_confirmation": False,
        }

    except Exception as exc:
        logger.exception("confirm_and_run_query failed for user=%s", user_id)
        return {"error": f"Query failed: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: list_db_connections
# ---------------------------------------------------------------------------


async def list_db_connections() -> dict[str, Any]:
    """List the user's connected external databases.

    Returns:
        Dict with ``connections`` list, each entry containing ``provider``,
        ``account_name``, and ``connected_at``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        credentials = await _get_db_credentials(user_id)

        connections = [
            {
                "provider": c["provider"],
                "account_name": c.get("account_name", ""),
                "connected_at": c.get("connected_at"),
            }
            for c in credentials
        ]

        if not connections:
            return {
                "connections": [],
                "message": (
                    "No external databases connected. "
                    "Use the Configuration page to connect PostgreSQL or BigQuery."
                ),
            }

        return {
            "connections": connections,
            "count": len(connections),
        }

    except Exception as exc:
        logger.exception("list_db_connections failed for user=%s", user_id)
        return {"error": f"Failed to list database connections: {exc}"}


# ---------------------------------------------------------------------------
# Internal — dispatch query to the right provider
# ---------------------------------------------------------------------------


async def _execute_for_provider(
    svc: Any,
    provider: str,
    cred: dict[str, Any],
    raw_creds: str,
    sql: str,
) -> dict[str, Any]:
    """Route query execution to the correct provider method.

    Args:
        svc: ``ExternalDbQueryService`` instance.
        provider: ``"postgresql"`` or ``"bigquery"``.
        cred: Credential row from ``integration_credentials``.
        raw_creds: Decrypted credential string (DSN or JSON).
        sql: SQL to execute.

    Returns:
        Query result dict or ``{"error": ...}`` on failure.
    """
    import json as _json

    if provider == "postgresql":
        return await svc.query_postgres(connection_string=raw_creds, sql=sql)

    if provider == "bigquery":
        try:
            creds_data = _json.loads(raw_creds)
        except ValueError:
            return {"error": "BigQuery credentials are not valid JSON."}

        project_id = creds_data.get("project_id", cred.get("account_name", ""))
        return await svc.query_bigquery(
            project_id=project_id,
            credentials_json=raw_creds,
            sql=sql,
        )

    return {"error": f"Unsupported provider: {provider!r}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

EXTERNAL_DB_TOOLS = [
    external_db_query,
    confirm_and_run_query,
    list_db_connections,
]
