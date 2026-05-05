# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""HTTP endpoints for the document viewer widget.

This router exposes three endpoints used by the document-viewer frontend:

- ``GET  /documents/{document_id}/source``    — fetch current source + binary URL
- ``GET  /documents/{document_id}/versions``  — list versions (newest first)
- ``POST /documents/{document_id}/revert``    — re-point source at target version,
  append a new "user-created" version row, return the new state

Each handler enforces user ownership in code (matching the agent-tool
``_load_owned_record`` pattern) since the underlying services run with
service-role access. ``revert`` returns 404 (not 403) when the target version
belongs to a different document, to avoid leaking version existence across
documents; 403 is reserved for cross-user access on a valid version.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.onboarding import get_current_user_id
from app.services.document_source_service import DocumentSourceService
from app.services.document_version_service import DocumentVersionService

router = APIRouter(prefix="/documents", tags=["Document Viewer"])


class SourceResponse(BaseModel):
    """Response payload for ``GET /documents/{id}/source``."""

    document_id: str
    doc_class: str
    binary_url: str | None
    source: dict[str, Any] | None
    forked_from_upload: bool


class VersionItem(BaseModel):
    """One entry in a versions listing."""

    id: str
    diff_summary: str | None
    binary_url: str
    created_at: str
    created_by: str


class VersionsResponse(BaseModel):
    """Response payload for ``GET /documents/{id}/versions``."""

    versions: list[VersionItem]


class RevertRequest(BaseModel):
    """Request body for ``POST /documents/{id}/revert``."""

    target_version_id: str


class RevertResponse(BaseModel):
    """Response payload for ``POST /documents/{id}/revert``."""

    new_version_id: str
    new_binary_url: str
    diff_summary: str


async def _source_service() -> DocumentSourceService:
    """Build a :class:`DocumentSourceService` for one request.

    The service runs with service-role credentials; ownership is enforced
    by the route handlers comparing ``record["user_id"]`` to the
    authenticated ``user_id``.
    """
    return DocumentSourceService()


async def _version_service() -> DocumentVersionService:
    """Build a :class:`DocumentVersionService` for one request.

    The service runs with service-role credentials; ownership is enforced
    by the route handlers comparing ``record["user_id"]`` to the
    authenticated ``user_id``.
    """
    return DocumentVersionService()


@router.get("/{document_id}/source", response_model=SourceResponse)
async def get_source(
    document_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[DocumentSourceService, Depends(_source_service)],
) -> SourceResponse:
    """Return the current source (and rendered binary URL) for a document.

    Returns 404 when no row exists OR when the row belongs to another user
    (the same status is used for "missing" and "not yours" to avoid leaking
    document existence across users).
    """
    record = await service.get(document_id)
    if record is None or record["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return SourceResponse(
        document_id=record["document_id"],
        doc_class=record["doc_class"],
        binary_url=record.get("binary_url"),
        source=record.get("source"),
        forked_from_upload=bool(record.get("forked_from_upload", False)),
    )


@router.get("/{document_id}/versions", response_model=VersionsResponse)
async def get_versions(
    document_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[DocumentVersionService, Depends(_version_service)],
    limit: int = 10,
) -> VersionsResponse:
    """List versions for a document, newest first, filtered to the caller.

    An empty ``versions`` list is a valid response (e.g. unknown document or
    document with no versions yet) — the endpoint never 404s on the listing
    so the frontend can render the empty state without a special-case error.
    """
    rows = await service.list(document_id, limit=limit)
    rows = [r for r in rows if r["user_id"] == user_id]
    return VersionsResponse(
        versions=[
            VersionItem(
                id=str(r["id"]),
                diff_summary=r.get("diff_summary"),
                binary_url=r["binary_url"],
                created_at=str(r["created_at"]),
                created_by=r["created_by"],
            )
            for r in rows
        ]
    )


@router.post("/{document_id}/revert", response_model=RevertResponse)
async def revert(
    document_id: str,
    body: RevertRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    source_svc: Annotated[DocumentSourceService, Depends(_source_service)],
    version_svc: Annotated[DocumentVersionService, Depends(_version_service)],
) -> RevertResponse:
    """Revert the document's canonical source to a previous version.

    The handler:

    1. Loads the target version row and validates it belongs to the same
       ``document_id`` (404 otherwise — hides cross-document version IDs).
    2. Validates the version is owned by the calling user (403 otherwise).
    3. Re-points ``document_sources`` at the target snapshot/binary.
    4. Appends a new ``document_versions`` row marked ``created_by="user"``
       so the revert itself is captured in the version chain.

    Returns the id, binary URL, and diff summary of the newly appended row.
    """
    target = await version_svc.get(body.target_version_id)
    if target is None or target["document_id"] != document_id:
        raise HTTPException(status_code=404, detail="Target version not found")
    if target["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    snapshot = target["source_snapshot"] or {}
    binary_url = target["binary_url"]

    await source_svc.update_source(
        document_id=document_id,
        new_source=snapshot,
        new_binary_url=binary_url,
    )

    new_version = await version_svc.append(
        document_id=document_id,
        user_id=user_id,
        source_snapshot=snapshot,
        binary_url=binary_url,
        diff_summary=f"Reverted to {body.target_version_id[:8]}",
        created_by="user",
    )

    return RevertResponse(
        new_version_id=str(new_version["id"]),
        new_binary_url=binary_url,
        diff_summary=new_version["diff_summary"],
    )


__all__ = [
    "RevertRequest",
    "RevertResponse",
    "SourceResponse",
    "VersionItem",
    "VersionsResponse",
    "router",
]
