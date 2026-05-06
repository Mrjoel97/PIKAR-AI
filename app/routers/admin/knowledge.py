# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin knowledge REST API — multipart upload, CRUD, stats, and search.

Provides 6 endpoints under ``/admin/knowledge/``:

- POST /knowledge/upload           — multipart file upload (PDF, image, video)
- GET  /knowledge/entries          — paginated list with optional filters
- GET  /knowledge/entries/{id}     — single entry detail
- DELETE /knowledge/entries/{id}   — delete entry + embeddings + Storage file
- GET  /knowledge/stats            — aggregate counts and storage usage
- GET  /knowledge/search           — semantic search over knowledge base

All endpoints require admin authentication via ``require_admin`` dependency.
Upload routing is based on content-type: document, image, or video pipeline.

Error envelope policy: errors return ``{detail: "<safe message>"}``. Raw
exception text is logged server-side but not surfaced to clients — we used
to leak Supabase internals via f"Upload failed: {exc}" which both confused
admins and exposed implementation details.
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

import app.services.knowledge_service as knowledge_service
from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.services.document_text_extraction import ExtractionError
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Upload limits — configurable so ops can lift the cap for special projects
# without a code change. 50MB default fits most policy + product decks while
# keeping a single multipart upload bounded enough that the worker doesn't
# OOM on a hostile or accidental gigabyte upload.
# ---------------------------------------------------------------------------

_DEFAULT_MAX_UPLOAD_MB = 50


def _max_upload_bytes() -> int:
    """Return the upload size ceiling in bytes (env-configurable, clamped >=1MB)."""
    raw = os.environ.get("ADMIN_KNOWLEDGE_MAX_UPLOAD_MB")
    try:
        mb = int(raw) if raw else _DEFAULT_MAX_UPLOAD_MB
    except ValueError:
        logger.warning(
            "Invalid ADMIN_KNOWLEDGE_MAX_UPLOAD_MB=%r — falling back to %d MB",
            raw,
            _DEFAULT_MAX_UPLOAD_MB,
        )
        mb = _DEFAULT_MAX_UPLOAD_MB
    return max(1, mb) * 1024 * 1024


# ---------------------------------------------------------------------------
# Endpoint 1: POST /knowledge/upload — multipart file upload
# ---------------------------------------------------------------------------


@router.post("/knowledge/upload")
@limiter.limit(get_user_persona_limit)
async def upload_knowledge_file(
    request: Request,
    file: UploadFile = File(...),
    uploaded_by: str = Form(...),
    agent_scope: str | None = Form(default=None),
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> JSONResponse:
    """Upload a document, image, or video to the agent knowledge base.

    Routes the file to the appropriate processing pipeline based on MIME type:
    - PDF / DOCX / XLSX / text files → process_document (returns 200)
    - Image files             → process_image (returns 200)
    - Video files             → process_video (returns 202, background processing)

    Args:
        file: The uploaded file (multipart form).
        uploaded_by: Admin identifier to record in the tracking entry.
        agent_scope: Optional agent name to scope this knowledge. None = global.
        admin_user: Injected by require_admin dependency.

    Returns:
        200 with ``{"entry_id", "chunk_count", "status"}`` for documents/images.
        202 with ``{"entry_id", "status": "processing", "message"}`` for videos.

    Raises:
        HTTPException 400: If the file content_type is not supported.
        HTTPException 500: On processing failure.
    """
    content_type = (file.content_type or "").lower()
    filename = file.filename or "upload"
    max_bytes = _max_upload_bytes()

    # Cheap pre-read size gate — Starlette sets file.size from Content-Length
    # when the client sends one. Reject early so a 5GB upload doesn't even
    # reach the worker process.
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File '{filename}' is too large "
                f"({file.size // (1024 * 1024)} MB). "
                f"Maximum allowed: {max_bytes // (1024 * 1024)} MB."
            ),
        )

    # Read with a hard ceiling. Reading max_bytes+1 lets us distinguish
    # exactly-at-limit (allowed) from over-limit (rejected) without holding
    # an unbounded payload in memory.
    file_bytes = await file.read(max_bytes + 1)
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File '{filename}' exceeds the maximum upload size of "
                f"{max_bytes // (1024 * 1024)} MB."
            ),
        )

    try:
        if content_type.startswith("image/"):
            result = await knowledge_service.process_image(
                file_bytes=file_bytes,
                filename=filename,
                mime_type=content_type,
                agent_scope=agent_scope,
                uploaded_by=uploaded_by,
            )
            return JSONResponse(content=result, status_code=200)

        if content_type.startswith("video/"):
            result = await knowledge_service.process_video(
                file_bytes=file_bytes,
                filename=filename,
                mime_type=content_type,
                agent_scope=agent_scope,
                uploaded_by=uploaded_by,
            )
            return JSONResponse(content=result, status_code=202)

        # Documents: application/pdf, application/vnd.openxml*, text/*, octet-stream
        if (
            content_type.startswith("application/")
            or content_type.startswith("text/")
        ):
            result = await knowledge_service.process_document(
                file_bytes=file_bytes,
                filename=filename,
                mime_type=content_type,
                agent_scope=agent_scope,
                uploaded_by=uploaded_by,
            )
            return JSONResponse(content=result, status_code=200)

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type '{content_type}'. "
                   "Upload PDF, DOCX, XLSX, CSV, TXT, MD, image/*, or video/* files.",
        )
    except HTTPException:
        raise
    except ExtractionError as exc:
        # Corrupt or unreadable file is a client-fixable problem (re-export
        # the PDF, fix the encoding) — return 400 with an actionable message
        # rather than a generic 500.
        logger.warning(
            "upload_knowledge_file extraction failed for %s: %s", filename, exc
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not extract text from '{filename}'. The file may be "
                "corrupted, password-protected, or in an unsupported format. "
                f"Details: {exc}"
            ),
        ) from exc
    except Exception as exc:
        # Log full exception server-side for debugging, return a sanitized
        # message — raw exception repr would leak Supabase internals, file
        # paths, or stack frames into an admin's browser.
        logger.exception(
            "upload_knowledge_file failed for %s (content_type=%s)",
            filename,
            content_type,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Upload of '{filename}' failed due to an internal error. "
                "Check server logs for details."
            ),
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 2: GET /knowledge/entries — paginated list
# ---------------------------------------------------------------------------


@router.get("/knowledge/entries")
@limiter.limit(get_user_persona_limit)
async def list_knowledge_entries(
    request: Request,
    agent_scope: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Return a paginated list of knowledge entries with total count.

    Returns:
        ``{"data": list[entry], "count": int}`` — ``count`` is the total
        number of rows matching the filters (ignoring limit/offset) so the
        admin UI can render pagination controls.
    """
    client = get_service_client()
    try:
        query = (
            client.table("admin_knowledge_entries")
            .select(
                "id, filename, file_type, mime_type, agent_scope, status, "
                "chunk_count, file_size_bytes, uploaded_by, created_at",
                count="exact",
            )
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )
        if agent_scope is not None:
            query = query.eq("agent_scope", agent_scope)
        if status is not None:
            query = query.eq("status", status)

        result = await execute_async(query, op_name="list_knowledge_entries")
        return {"data": result.data or [], "count": result.count or 0}
    except Exception as exc:
        logger.error("list_knowledge_entries failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list knowledge entries"
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 3: GET /knowledge/entries/{entry_id} — single entry detail
# ---------------------------------------------------------------------------


@router.get("/knowledge/entries/{entry_id}")
@limiter.limit(get_user_persona_limit)
async def get_knowledge_entry(
    request: Request,
    entry_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Return a single knowledge entry by ID.

    Args:
        entry_id: UUID of the admin_knowledge_entries row.
        admin_user: Injected by require_admin.

    Returns:
        Full entry dict.

    Raises:
        HTTPException 404: If the entry does not exist.
    """
    client = get_service_client()
    try:
        result = await execute_async(
            client.table("admin_knowledge_entries")
            .select("*")
            .eq("id", entry_id)
            .limit(1),
            op_name=f"get_knowledge_entry.{entry_id}",
        )
        rows = result.data or []
        if not rows:
            raise HTTPException(
                status_code=404, detail=f"Entry '{entry_id}' not found"
            )
        return rows[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_knowledge_entry failed for %s: %s", entry_id, exc)
        raise HTTPException(
            status_code=500, detail="Failed to get knowledge entry"
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 4: DELETE /knowledge/entries/{entry_id}
# ---------------------------------------------------------------------------


@router.delete("/knowledge/entries/{entry_id}")
@limiter.limit(get_user_persona_limit)
async def delete_knowledge_entry(
    request: Request,
    entry_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Delete a knowledge entry, its embeddings, and its Storage file.

    Args:
        entry_id: UUID of the admin_knowledge_entries row to delete.
        admin_user: Injected by require_admin.

    Returns:
        ``{"deleted": True, "entry_id": str}`` on success.

    Raises:
        HTTPException 404: If the entry does not exist.
    """
    client = get_service_client()
    try:
        # Fetch entry to get file_path
        entry_result = await execute_async(
            client.table("admin_knowledge_entries")
            .select("id, file_path")
            .eq("id", entry_id)
            .limit(1),
            op_name=f"delete_knowledge_entry.fetch.{entry_id}",
        )
        if not (entry_result.data or []):
            raise HTTPException(
                status_code=404, detail=f"Entry '{entry_id}' not found"
            )

        # Delete embeddings first
        await execute_async(
            client.table("embeddings")
            .delete()
            .eq("source_id", entry_id),
            op_name=f"delete_knowledge_entry.embeddings.{entry_id}",
        )

        # Delete the tracking entry
        await execute_async(
            client.table("admin_knowledge_entries")
            .delete()
            .eq("id", entry_id),
            op_name=f"delete_knowledge_entry.entry.{entry_id}",
        )

        # Attempt Storage cleanup (non-fatal)
        try:
            file_path = entry_result.data[0].get("file_path")
            if file_path:
                client.storage.from_("admin-knowledge").remove([file_path])
        except Exception as storage_exc:
            logger.warning("Storage cleanup failed for %s: %s", entry_id, storage_exc)

        return {"deleted": True, "entry_id": entry_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("delete_knowledge_entry failed for %s: %s", entry_id, exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete entry '{entry_id}'"
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 5: GET /knowledge/stats
# ---------------------------------------------------------------------------


@router.get("/knowledge/stats")
@limiter.limit(get_user_persona_limit)
async def get_knowledge_stats(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Return aggregated knowledge base statistics.

    Delegates to knowledge_service.get_knowledge_stats().

    Args:
        admin_user: Injected by require_admin.

    Returns:
        Dict with ``total_entries``, ``total_embeddings``, ``by_agent``,
        and ``storage_bytes``.
    """
    try:
        return await knowledge_service.get_knowledge_stats()
    except Exception as exc:
        logger.error("get_knowledge_stats endpoint failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to get knowledge stats"
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 6: GET /knowledge/search
# ---------------------------------------------------------------------------


@router.get("/knowledge/search")
@limiter.limit(get_user_persona_limit)
async def search_knowledge(
    request: Request,
    q: str,
    agent_scope: str | None = None,
    top_k: int = 5,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Semantic search over the knowledge base.

    Args:
        q: Search query string (required).
        agent_scope: Optional agent name to narrow results.
        top_k: Maximum number of results to return (default 5).
        admin_user: Injected by require_admin.

    Returns:
        List of ``{"content", "similarity", "metadata"}`` dicts.
    """
    try:
        return await knowledge_service.search_system_knowledge(
            query=q, agent_name=agent_scope, top_k=top_k
        )
    except Exception as exc:
        logger.error("search_knowledge endpoint failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to search knowledge"
        ) from exc
