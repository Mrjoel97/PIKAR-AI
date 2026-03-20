"""Knowledge Vault Router - API endpoints for document management.

Provides endpoints for:
- Listing documents by category (uploads, workspace, media, google docs)
- Generating signed download URLs
- Triggering RAG processing for uploaded documents
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.rag.knowledge_vault import ingest_document_content, search_knowledge
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client

router = APIRouter(prefix="/vault", tags=["vault"])
logger = logging.getLogger(__name__)


def get_supabase():
    """Get Supabase client from centralized service."""
    return get_service_client()


def _resolve_user_id(current_user_id: str, requested_user_id: str | None = None) -> str:
    if requested_user_id and requested_user_id != current_user_id:
        raise HTTPException(
            status_code=403, detail="Cannot access another user's vault data"
        )
    return current_user_id


def _assert_storage_access(supabase, user_id: str, bucket: str, file_path: str) -> None:
    if bucket == "knowledge-vault":
        result = (
            supabase.table("vault_documents")
            .select("id")
            .eq("user_id", user_id)
            .eq("file_path", file_path)
            .limit(1)
            .execute()
        )
        if result.data:
            return
    elif bucket in {
        "brand-assets",
        "user-content",
        "generated-assets",
        "generated-videos",
    }:
        result = (
            supabase.table("media_assets")
            .select("id")
            .eq("user_id", user_id)
            .eq("bucket_id", bucket)
            .eq("file_path", file_path)
            .limit(1)
            .execute()
        )
        if result.data:
            return

    raise HTTPException(status_code=403, detail="File access not allowed")


class VaultDocument(BaseModel):
    id: str
    filename: str
    file_path: str
    file_type: str | None = None
    size_bytes: int | None = None
    category: str | None = None
    created_at: str
    is_processed: bool | None = None
    source: str


class DocumentListResponse(BaseModel):
    documents: list[VaultDocument]
    total: int


class DownloadUrlRequest(BaseModel):
    file_path: str
    bucket: str = "knowledge-vault"


class DownloadUrlResponse(BaseModel):
    signed_url: str
    expires_in: int


class ProcessDocumentRequest(BaseModel):
    file_path: str
    user_id: str | None = None


class ProcessDocumentResponse(BaseModel):
    success: bool
    message: str
    embedding_count: int | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    user_id: str | None = None


class SearchResult(BaseModel):
    id: str
    content: str
    similarity: float
    source_type: str | None = None
    title: str | None = None
    metadata: dict | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    error: str | None = None


@router.get("/documents", response_model=DocumentListResponse)
@limiter.limit(get_user_persona_limit)
async def list_uploaded_documents(
    request: Request,
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
):
    """List the authenticated user's uploaded documents from the knowledge vault."""
    try:
        supabase = get_supabase()
        user_id = _resolve_user_id(current_user_id, user_id)

        result = (
            supabase.table("vault_documents")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        documents = [
            VaultDocument(
                id=doc["id"],
                filename=doc["filename"],
                file_path=doc["file_path"],
                file_type=doc.get("file_type"),
                size_bytes=doc.get("size_bytes"),
                category=doc.get("category"),
                created_at=doc["created_at"],
                is_processed=doc.get("is_processed", False),
                source="upload",
            )
            for doc in (result.data or [])
        ]

        return DocumentListResponse(
            documents=documents, total=result.count or len(documents)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace", response_model=DocumentListResponse)
@limiter.limit(get_user_persona_limit)
async def list_workspace_documents(
    request: Request,
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
):
    """List documents created in the authenticated user's workspaces."""
    try:
        supabase = get_supabase()
        user_id = _resolve_user_id(current_user_id, user_id)

        result = (
            supabase.table("landing_pages")
            .select("id, title, created_at, config", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        documents = [
            VaultDocument(
                id=doc["id"],
                filename=doc.get("title") or "Untitled Landing Page",
                file_path=f"/dashboard/landing-pages/{doc['id']}",
                file_type="text/html",
                size_bytes=None,
                category="Landing Page",
                created_at=doc["created_at"],
                is_processed=None,
                source="workspace",
            )
            for doc in (result.data or [])
        ]

        return DocumentListResponse(
            documents=documents, total=result.count or len(documents)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media", response_model=DocumentListResponse)
@limiter.limit(get_user_persona_limit)
async def list_media_files(
    request: Request,
    user_id: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
):
    """List the authenticated user's media files."""
    try:
        supabase = get_supabase()
        user_id = _resolve_user_id(current_user_id, user_id)

        query = (
            supabase.table("media_assets")
            .select("*", count="exact")
            .eq("user_id", user_id)
        )
        if category:
            query = query.eq("category", category)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        documents = [
            VaultDocument(
                id=doc["id"],
                filename=doc.get("filename") or doc.get("title") or str(doc["id"]),
                file_path=doc.get("file_path") or "",
                file_type=doc.get("file_type"),
                size_bytes=doc.get("size_bytes"),
                category=doc.get("category"),
                created_at=doc["created_at"],
                is_processed=None,
                source="media",
            )
            for doc in (result.data or [])
        ]

        return DocumentListResponse(
            documents=documents, total=result.count or len(documents)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google-docs", response_model=DocumentListResponse)
@limiter.limit(get_user_persona_limit)
async def list_google_docs(
    request: Request,
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
):
    """List Google Docs created by agents for the authenticated user."""
    try:
        supabase = get_supabase()
        user_id = _resolve_user_id(current_user_id, user_id)

        result = (
            supabase.table("agent_google_docs")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        documents = [
            VaultDocument(
                id=doc["id"],
                filename=doc["title"],
                file_path=doc["doc_url"],
                file_type="application/vnd.google-apps.document",
                size_bytes=None,
                category=doc.get("doc_type"),
                created_at=doc["created_at"],
                is_processed=None,
                source="google",
            )
            for doc in (result.data or [])
        ]

        return DocumentListResponse(
            documents=documents, total=result.count or len(documents)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download", response_model=DownloadUrlResponse)
@limiter.limit(get_user_persona_limit)
async def generate_download_url(
    request: Request,
    body: DownloadUrlRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Generate a signed URL for a file the authenticated user owns."""
    try:
        supabase = get_supabase()
        _assert_storage_access(supabase, current_user_id, body.bucket, body.file_path)
        expires_in = 300

        result = supabase.storage.from_(body.bucket).create_signed_url(
            body.file_path, expires_in
        )
        if result.get("error"):
            raise HTTPException(status_code=404, detail="File not found")

        return DownloadUrlResponse(
            signed_url=result["signedURL"], expires_in=expires_in
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
@limiter.limit(get_user_persona_limit)
async def search_vault(
    request: Request,
    body: SearchRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Semantic search across the authenticated user's Knowledge Vault."""
    try:
        user_id = _resolve_user_id(current_user_id, body.user_id)
        result = search_knowledge(query=body.query, top_k=body.top_k, user_id=user_id)

        if result.get("error"):
            return SearchResponse(results=[], query=body.query, error=result["error"])

        search_results = [
            SearchResult(
                id=r.get("id", ""),
                content=r.get("content", ""),
                similarity=r.get("similarity", 0.0),
                source_type=r.get("source_type"),
                title=r.get("metadata", {}).get("title") if r.get("metadata") else None,
                metadata=r.get("metadata"),
            )
            for r in result.get("results", [])
        ]

        return SearchResponse(results=search_results, query=body.query, error=None)
    except Exception as e:
        return SearchResponse(results=[], query=body.query, error=str(e))


@router.post("/process", response_model=ProcessDocumentResponse)
@limiter.limit(get_user_persona_limit)
async def process_document_for_rag(
    request: Request,
    body: ProcessDocumentRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Process an uploaded document for RAG (chunking and embedding)."""
    try:
        supabase = get_supabase()
        user_id = _resolve_user_id(current_user_id, body.user_id)
        _assert_storage_access(supabase, user_id, "knowledge-vault", body.file_path)

        file_data = supabase.storage.from_("knowledge-vault").download(body.file_path)
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")

        try:
            content = file_data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = file_data.decode("latin-1")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to decode file content. Only text-based files can be processed.",
                )

        filename = body.file_path.split("/")[-1]
        result = await ingest_document_content(
            content=content,
            title=filename,
            document_type="uploaded_document",
            user_id=user_id,
            metadata={"file_path": body.file_path},
        )

        supabase.table("vault_documents").update(
            {
                "is_processed": True,
                "embedding_count": result.get("chunk_count", 0),
            }
        ).eq("file_path", body.file_path).eq("user_id", user_id).execute()

        return ProcessDocumentResponse(
            success=True,
            message=f"Successfully processed document with {result.get('chunk_count', 0)} chunks",
            embedding_count=result.get("chunk_count", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        return ProcessDocumentResponse(
            success=False, message=str(e), embedding_count=None
        )


@router.delete("/documents/{document_id}")
@limiter.limit(get_user_persona_limit)
async def delete_document(
    request: Request,
    document_id: str,
    user_id: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
):
    """Delete a document from the authenticated user's vault."""
    try:
        supabase = get_supabase()
        user_id = _resolve_user_id(current_user_id, user_id)

        result = (
            supabase.table("vault_documents")
            .select("file_path")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = result.data["file_path"]
        supabase.storage.from_("knowledge-vault").remove([file_path])
        supabase.table("vault_documents").delete().eq("id", document_id).eq(
            "user_id", user_id
        ).execute()

        try:
            embeddings_result = (
                supabase.table("embeddings")
                .select("id")
                .filter("metadata->>file_path", "eq", file_path)
                .execute()
            )
            if embeddings_result.data:
                embedding_ids = [e["id"] for e in embeddings_result.data]
                supabase.table("embeddings").delete().in_("id", embedding_ids).execute()
                logger.info(
                    "Deleted %s embeddings for document %s",
                    len(embedding_ids),
                    document_id,
                )

            supabase.table("embeddings").delete().eq("source_id", document_id).execute()
        except Exception as e:
            logger.warning(
                "Could not delete embeddings for document %s: %s", document_id, e
            )

        return {"success": True, "message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
