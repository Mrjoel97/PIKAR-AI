# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Data I/O agent tools -- CSV import and export via chat.

Provides two agent-callable functions that wire into the DataImportService
and DataExportService created in Phase 40 Plan 01.  The tools extract the
current user from request context and delegate to the corresponding service.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


def _get_session_id() -> str | None:
    """Extract the current session ID from the request-scoped context."""
    from app.services.request_context import get_current_session_id

    return get_current_session_id()


# ---------------------------------------------------------------------------
# Import tool
# ---------------------------------------------------------------------------

async def import_csv_data(table_name: str, file_url: str) -> dict[str, Any]:
    """Import CSV data from a file URL into the specified database table.

    Downloads the CSV file from the given URL, uses AI to map columns to
    the target table schema, validates each row, and commits valid rows.

    Supported tables: contacts, financial_records, department_tasks,
    initiatives, content_bundles, support_tickets, recruitment_candidates,
    compliance_risks, compliance_audits.

    Args:
        table_name: Target table to import into (e.g. ``contacts``).
        file_url: Public or signed URL pointing to the CSV file to import.

    Returns:
        Dict with import results including counts and any errors.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"status": "error", "message": "No authenticated user found."}

    from app.services.data_import_service import IMPORTABLE_TABLES, DataImportService

    if table_name not in IMPORTABLE_TABLES:
        return {
            "status": "error",
            "message": (
                f"Table '{table_name}' is not importable. "
                f"Supported tables: {', '.join(IMPORTABLE_TABLES)}"
            ),
        }

    # Download CSV bytes from the provided URL
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(file_url)
            resp.raise_for_status()
            csv_bytes = resp.content
    except httpx.HTTPError as exc:
        return {
            "status": "error",
            "message": f"Failed to download CSV from URL: {exc}",
        }

    service = DataImportService(user_id=user_id)

    # Parse
    try:
        df = service.parse_csv(csv_bytes)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    if len(df) == 0:
        return {"status": "error", "message": "CSV file is empty (no data rows)."}

    # AI column mapping
    column_mapping = await service.suggest_mappings(df, table_name)
    if not column_mapping:
        return {
            "status": "error",
            "message": "Could not determine column mappings for this CSV.",
        }

    # Validate
    errors = service.validate(df, column_mapping, table_name)
    if errors:
        # Summarise first 10 errors for the agent
        sample = errors[:10]
        summary = "; ".join(
            f"Row {e['row']}: {e['reason']}" for e in sample
        )
        if len(errors) > 10:
            summary += f" ... and {len(errors) - 10} more errors"
        return {
            "status": "error",
            "message": f"Validation failed with {len(errors)} error(s): {summary}",
            "error_count": len(errors),
            "errors": sample,
        }

    # Commit
    result = await service.commit(
        df,
        column_mapping,
        table_name,
        on_duplicate="skip",
    )

    # Save successful mapping for future imports
    try:
        await service.save_column_mapping(table_name, column_mapping)
    except Exception:
        logger.debug("Could not save column mapping (non-critical)")

    return {
        "status": "success",
        "imported_count": result["imported_count"],
        "skipped_count": result["skipped_count"],
        "errors": result.get("errors", []),
    }


# ---------------------------------------------------------------------------
# Export tool
# ---------------------------------------------------------------------------

async def export_data_to_csv(
    table_name: str,
    filters: str | None = None,
) -> dict[str, Any]:
    """Export data from a database table to a CSV file and return a download URL.

    Queries the specified table (respecting row-level security), converts
    the results to CSV, uploads to storage, and returns a signed URL.

    Supported tables: contacts, financial_records, department_tasks,
    initiatives, content_bundles, support_tickets, recruitment_candidates,
    compliance_risks, compliance_audits.

    Args:
        table_name: The table to export (e.g. ``contacts``).
        filters: Optional JSON string of column-value equality filters,
            e.g. ``'{"status": "active"}'``.

    Returns:
        Dict with download URL, filename, file size, and a document widget.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"status": "error", "message": "No authenticated user found."}

    from app.services.data_export_service import EXPORTABLE_TABLES, DataExportService

    if table_name not in EXPORTABLE_TABLES:
        return {
            "status": "error",
            "message": (
                f"Table '{table_name}' is not exportable. "
                f"Supported tables: {', '.join(EXPORTABLE_TABLES)}"
            ),
        }

    # Parse optional JSON filters
    parsed_filters: dict[str, Any] | None = None
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": f"Invalid JSON in filters parameter: {filters}",
            }

    service = DataExportService(user_id=user_id)

    try:
        result = await service.export_table(table_name, filters=parsed_filters)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    label = EXPORTABLE_TABLES[table_name].get("label", table_name)

    return {
        "status": "success",
        "url": result["url"],
        "filename": result["filename"],
        "size_bytes": result["size_bytes"],
        "widget": {
            "type": "document",
            "title": f"{label} Export",
            "data": {
                "documentUrl": result["url"],
                "title": f"{label} Export",
                "fileType": "csv",
                "sizeBytes": result["size_bytes"],
            },
            "dismissible": True,
            "expandable": False,
        },
    }


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

DATA_IO_TOOLS = [import_csv_data, export_data_to_csv]
