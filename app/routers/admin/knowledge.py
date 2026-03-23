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
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import app.services.knowledge_service as knowledge_service
from app.middleware.admin_auth import require_admin
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Endpoint 1: POST /knowledge/upload — multipart file upload
# ---------------------------------------------------------------------------


@router.post("/knowledge/upload")
async def upload_knowledge_file(
    file: UploadFile,
    uploaded_by: str = Form(...),
    agent_scope: str | None = Form(default=None),
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> JSONResponse:
    """Upload a document, image, or video to the agent knowledge base.

    Routes the file to the appropriate processing pipeline based on MIME type:
    - PDF / DOCX / text files → process_document (returns 200)
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
    file_bytes = await file.read()
    filename = file.filename or "upload"

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
                   "Upload PDF, DOCX, TXT, MD, image/*, or video/* files.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("upload_knowledge_file failed for %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Endpoint 2: GET /knowledge/entries — paginated list
# ---------------------------------------------------------------------------


@router.get("/knowledge/entries")
async def list_knowledge_entries(
    agent_scope: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Return a paginated list of knowledge entries.

    Args:
        agent_scope: Optional filter by agent name. None returns all entries.
        status: Optional filter by processing status (completed/processing/failed).
        limit: Maximum number of rows to return (default 50).
        offset: Row offset for pagination (default 0).
        admin_user: Injected by require_admin.

    Returns:
        List of entry dicts ordered newest-first.
    """
    client = get_service_client()
    try:
        query = (
            client.table("admin_knowledge_entries")
            .select(
                "id, filename, file_type, mime_type, agent_scope, status, "
                "chunk_count, file_size_bytes, uploaded_by, created_at"
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
        return result.data or []
    except Exception as exc:
        logger.error("list_knowledge_entries failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list knowledge entries"
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 3: GET /knowledge/entries/{entry_id} — single entry detail
# ---------------------------------------------------------------------------


@router.get("/knowledge/entries/{entry_id}")
async def get_knowledge_entry(
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
async def delete_knowledge_entry(
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
async def get_knowledge_stats(
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
async def search_knowledge(
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
