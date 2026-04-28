# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Data I/O router — CSV import/export REST endpoints.

Endpoints:
    GET  /data-io/tables            — List importable/exportable tables with schemas
    POST /data-io/upload            — Upload CSV, parse, preview, suggest mappings
    POST /data-io/validate          — Validate mapped data against target schema
    POST /data-io/commit            — Commit validated data (SSE for >1000 rows)
    GET  /data-io/export/{table}    — Export table to CSV, return signed URL
"""


import json
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.routers.onboarding import get_current_user_id
from app.services.cache import get_cache_service
from app.services.data_export_service import DataExportService
from app.services.data_import_service import DataImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-io", tags=["Data I/O"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CSV_TEMP_KEY_PREFIX = "csv_temp:"
CSV_TEMP_TTL_SECONDS = 30 * 60  # 30 minutes
SSE_THRESHOLD_ROWS = 1000

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class TableInfo(BaseModel):
    """Importable/exportable table metadata."""

    name: str
    label: str
    columns: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response from CSV upload with preview and suggested mappings."""

    csv_data_key: str
    column_headers: list[str]
    row_count: int
    preview: list[dict[str, Any]]
    suggested_mappings: dict[str, str]


class ValidateRequest(BaseModel):
    """Request body for /validate endpoint."""

    csv_data_key: str
    column_mapping: dict[str, str]
    target_table: str
    on_duplicate: str = "skip"


class ValidateResponse(BaseModel):
    """Validation result with per-row errors."""

    valid: bool
    errors: list[dict[str, Any]]
    valid_count: int
    error_count: int


class CommitRequest(BaseModel):
    """Request body for /commit endpoint."""

    csv_data_key: str
    column_mapping: dict[str, str]
    target_table: str
    on_duplicate: str = "skip"


class CommitResponse(BaseModel):
    """Result of a small (non-SSE) import commit."""

    imported_count: int
    skipped_count: int
    errors: list[dict[str, Any]]


class ExportResponse(BaseModel):
    """Response from CSV export with signed download URL."""

    url: str
    filename: str
    size_bytes: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _store_csv_temp(csv_bytes: bytes, user_id: str) -> str:
    """Store CSV bytes in Redis with a temporary key.

    Returns:
        The cache key for later retrieval.
    """
    key = f"{CSV_TEMP_KEY_PREFIX}{user_id}:{uuid.uuid4().hex}"
    cache = get_cache_service()
    # Store as base64 to avoid JSON encoding issues with raw bytes
    import base64

    encoded = base64.b64encode(csv_bytes).decode("ascii")
    await cache.set_generic(key, encoded, ttl=CSV_TEMP_TTL_SECONDS)
    return key


async def _retrieve_csv_temp(key: str) -> bytes:
    """Retrieve CSV bytes from Redis by temporary key.

    Raises:
        HTTPException: If the key is expired or not found.
    """
    cache = get_cache_service()
    result = await cache.get_generic(key)
    if result.is_miss or result.is_error:
        raise HTTPException(
            status_code=410,
            detail="CSV data has expired. Please re-upload the file.",
        )
    import base64

    return base64.b64decode(result.value)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tables", response_model=list[TableInfo])
async def list_tables(
    user_id: str = Depends(get_current_user_id),
) -> list[TableInfo]:
    """Return importable/exportable tables with column schemas."""
    tables = DataImportService.get_importable_tables()
    return [
        TableInfo(
            name=name,
            label=info["label"],
            columns=info.get("columns", {}),
            required=info.get("required", []),
        )
        for name, info in tables.items()
    ]


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: Annotated[UploadFile, File(...)],
    target_table: Annotated[str, Query(description="Target table for import")],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UploadResponse:
    """Upload a CSV file, parse it, and return preview with suggested mappings.

    The raw CSV bytes are stored in Redis for 30 minutes so that subsequent
    validate/commit calls do not require re-upload.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    csv_bytes = await file.read()

    svc = DataImportService(user_id=user_id)

    try:
        df = svc.parse_csv(csv_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("CSV parse error")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV: {exc!s}",
        ) from exc

    # Store in Redis for validate/commit steps
    csv_data_key = await _store_csv_temp(csv_bytes, user_id)

    # Get suggested mappings (saved or AI)
    try:
        suggested_mappings = await svc.suggest_mappings(df, target_table)
    except Exception:
        logger.exception("Column mapping suggestion failed")
        # Fallback: identity map for matching names
        table_cols = list(
            DataImportService.get_importable_tables()
            .get(target_table, {})
            .get("columns", {})
            .keys()
        )
        suggested_mappings = {h: h for h in df.columns if h in table_cols}

    # Preview first 10 rows with suggested mapping
    preview = svc.preview(df, suggested_mappings, limit=10)

    return UploadResponse(
        csv_data_key=csv_data_key,
        column_headers=df.columns,
        row_count=len(df),
        preview=preview,
        suggested_mappings=suggested_mappings,
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_import(
    body: ValidateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ValidateResponse:
    """Validate mapped CSV data against the target table schema.

    Returns per-row errors without committing any data.
    """
    csv_bytes = await _retrieve_csv_temp(body.csv_data_key)
    svc = DataImportService(user_id=user_id)
    df = svc.parse_csv(csv_bytes)

    errors = svc.validate(df, body.column_mapping, body.target_table)

    return ValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        valid_count=len(df) - len({e["row"] for e in errors}),
        error_count=len({e["row"] for e in errors}),
    )


@router.post("/commit")
async def commit_import(
    body: CommitRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Commit validated CSV data to the target table.

    For imports with >1000 rows, returns an SSE stream with progress updates.
    For smaller imports, returns a JSON response.
    """
    csv_bytes = await _retrieve_csv_temp(body.csv_data_key)
    svc = DataImportService(user_id=user_id)
    df = svc.parse_csv(csv_bytes)

    if len(df) > SSE_THRESHOLD_ROWS:
        # SSE streaming for large imports
        async def _sse_generator():
            """Yield SSE events with progress updates."""
            import asyncio

            progress_queue: list[float] = []

            def on_progress(pct: float) -> None:
                progress_queue.append(pct)

            # Run commit in background, yielding progress events
            task = asyncio.create_task(
                svc.commit(
                    df,
                    body.column_mapping,
                    body.target_table,
                    on_duplicate=body.on_duplicate,
                    progress_callback=on_progress,
                )
            )

            while not task.done():
                await asyncio.sleep(0.2)
                while progress_queue:
                    pct = progress_queue.pop(0)
                    yield f"data: {json.dumps({'type': 'progress', 'percent': pct})}\n\n"

            result = task.result()

            # Save successful mapping
            try:
                await svc.save_column_mapping(body.target_table, body.column_mapping)
            except Exception:
                logger.exception("Failed to save column mapping")

            yield f"data: {json.dumps({'type': 'complete', **result})}\n\n"

        return StreamingResponse(
            _sse_generator(),
            media_type="text/event-stream",
        )

    # Small import: synchronous JSON response
    result = await svc.commit(
        df,
        body.column_mapping,
        body.target_table,
        on_duplicate=body.on_duplicate,
    )

    # Save successful mapping
    try:
        await svc.save_column_mapping(body.target_table, body.column_mapping)
    except Exception:
        logger.exception("Failed to save column mapping")

    return CommitResponse(**result)


@router.get("/export/{table_name}", response_model=ExportResponse)
async def export_table(
    table_name: str,
    user_id: str = Depends(get_current_user_id),
) -> ExportResponse:
    """Export a table to CSV and return a signed download URL.

    Optional query parameters are passed as equality filters on the table.
    """
    svc = DataExportService(user_id=user_id)

    try:
        result = await svc.export_table(table_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Export failed for table %s", table_name)
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {exc!s}",
        ) from exc

    return ExportResponse(**result)
