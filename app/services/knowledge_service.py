"""Agent Knowledge Base service.

Provides backend operations for uploading, processing, and searching admin-managed
training documents, images, and videos for the agent knowledge base.

Exports:
    process_document       — Extract + chunk + embed PDF/DOCX/TXT/MD files
    process_image          — Generate Gemini vision description + embed image
    process_video          — Upload video + enqueue background transcription job
    process_video_transcript — Background worker: extract audio, transcribe, embed
    search_system_knowledge — Semantic search over system-scoped embeddings
    get_knowledge_stats    — Aggregated knowledge base statistics

All Supabase calls use the service-role client via ``execute_async`` to avoid
blocking the event loop.  Follows patterns from agent_config_service.py.
"""

from __future__ import annotations

import asyncio
import io
import logging
import uuid
from typing import Any

from app.rag.embedding_service import generate_embeddings_batch
from app.rag.ingestion_service import ingest_document
from app.services.speech_to_text_service import transcribe_audio
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

_STORAGE_BUCKET = "admin-knowledge"
_VISION_PROMPT = (
    "Describe this image in detail for a business knowledge base. "
    "Include all visible text, objects, and context."
)
_VISION_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_genai_client() -> Any:
    """Return a google.genai client, or raise ImportError if unavailable."""
    try:
        from google import genai  # type: ignore[import]

        return genai.Client()
    except Exception as exc:  # pragma: no cover - import guard
        raise ImportError(f"google.genai unavailable: {exc}") from exc


async def _extract_audio_from_video(video_bytes: bytes) -> bytes:
    """Extract WAV audio track from video bytes using ffmpeg-python.

    Runs ffmpeg in a thread to avoid blocking the event loop.
    Requires the ``ffmpeg`` binary to be available on PATH.
    """
    try:
        import ffmpeg  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "ffmpeg-python is required for video transcription. "
            "Install it with: uv add ffmpeg-python. "
            "The ffmpeg binary must also be available on PATH."
        ) from exc

    def _run_ffmpeg(data: bytes) -> bytes:
        out, _ = (
            ffmpeg.input("pipe:", format="mp4")
            .output("pipe:", format="wav", acodec="pcm_s16le", ac=1, ar=16000)
            .run(input=data, capture_stdout=True, capture_stderr=True)
        )
        return out

    return await asyncio.to_thread(_run_ffmpeg, video_bytes)


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    import pypdf  # type: ignore[import]

    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_docx_text(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    import docx  # type: ignore[import]

    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def _extract_text_by_mime(file_bytes: bytes, mime_type: str) -> str:
    """Dispatch text extraction based on MIME type."""
    normalized = (mime_type or "").lower().split(";")[0].strip()

    if normalized == "application/pdf":
        return _extract_pdf_text(file_bytes)

    if normalized == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx_text(file_bytes)

    # text/plain, text/markdown, text/x-markdown, text/md, application/octet-stream fallback
    return file_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def process_document(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    agent_scope: str | None,
    uploaded_by: str,
) -> dict[str, Any]:
    """Extract, chunk, and embed a document file (PDF / DOCX / TXT / MD).

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used in metadata + Storage path).
        mime_type: MIME type string to select the extraction strategy.
        agent_scope: Agent name to restrict scope, or None for global access.
        uploaded_by: Admin identifier recorded in the tracking entry.

    Returns:
        dict with ``entry_id``, ``chunk_count``, and ``status``.
        Returns ``{"error": str}`` if content extraction yields nothing.
    """
    content = _extract_text_by_mime(file_bytes, mime_type)
    if not content or not content.strip():
        return {"error": "No text content extracted"}

    client = get_service_client()
    entry_id = str(uuid.uuid4())

    # Upload raw file to Storage
    try:
        client.storage.from_(_STORAGE_BUCKET).upload(
            f"{entry_id}/{filename}",
            file_bytes,
            {"content-type": mime_type or "application/octet-stream"},
        )
    except Exception as exc:  # pragma: no cover - storage errors are non-fatal for text docs
        logger.warning("Storage upload failed for %s: %s", filename, exc)

    # Embed via RAG ingestion pipeline (agent_id=None, user_id=None per RESEARCH.md Pitfall 1)
    embedding_ids: list[str] = await ingest_document(
        client,
        content,
        source_type="admin_training",
        source_id=entry_id,
        metadata={
            "scope": "system",
            "agent_scope": agent_scope,
            "filename": filename,
        },
        agent_id=None,
        user_id=None,
    )
    chunk_count = len(embedding_ids)

    # Persist tracking entry
    await execute_async(
        client.table("admin_knowledge_entries").insert({
            "id": entry_id,
            "filename": filename,
            "file_type": "document",
            "mime_type": mime_type,
            "file_path": f"{entry_id}/{filename}",
            "agent_scope": agent_scope,
            "uploaded_by": uploaded_by,
            "status": "completed",
            "chunk_count": chunk_count,
            "embedding_ids": embedding_ids,
            "file_size_bytes": len(file_bytes),
        })
    )

    return {"entry_id": entry_id, "chunk_count": chunk_count, "status": "completed"}


async def process_image(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    agent_scope: str | None,
    uploaded_by: str,
) -> dict[str, Any]:
    """Generate a Gemini vision description for an image and embed it.

    Args:
        file_bytes: Raw image bytes.
        filename: Original filename.
        mime_type: Image MIME type (image/png, image/jpeg, …).
        agent_scope: Agent name or None for global.
        uploaded_by: Admin identifier.

    Returns:
        dict with ``entry_id``, ``description`` (first 200 chars), ``chunk_count``, ``status``.
    """
    client = get_service_client()
    entry_id = str(uuid.uuid4())

    # Upload to Storage
    try:
        client.storage.from_(_STORAGE_BUCKET).upload(
            f"{entry_id}/{filename}",
            file_bytes,
            {"content-type": mime_type or "image/jpeg"},
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Storage upload failed for image %s: %s", filename, exc)

    # Generate description via Gemini vision
    description = ""
    try:
        genai_client = _get_genai_client()
        from google.genai import types as genai_types  # type: ignore[import]

        response = genai_client.models.generate_content(
            model=_VISION_MODEL,
            contents=[
                genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type or "image/jpeg"),
                _VISION_PROMPT,
            ],
        )
        description = response.text or ""
    except Exception as exc:
        logger.warning("Gemini vision description failed for %s: %s", filename, exc)
        description = f"Image file: {filename}"

    # Embed the description
    embeddings = generate_embeddings_batch([description])
    embedding_id = str(uuid.uuid4())

    await execute_async(
        client.table("embeddings").insert({
            "id": embedding_id,
            "user_id": None,
            "agent_id": None,
            "source_type": "admin_training_image",
            "source_id": entry_id,
            "content": description,
            "embedding": embeddings[0] if embeddings else [],
            "metadata": {
                "scope": "system",
                "agent_scope": agent_scope,
                "filename": filename,
            },
        })
    )

    # Persist tracking entry
    await execute_async(
        client.table("admin_knowledge_entries").insert({
            "id": entry_id,
            "filename": filename,
            "file_type": "image",
            "mime_type": mime_type,
            "file_path": f"{entry_id}/{filename}",
            "agent_scope": agent_scope,
            "uploaded_by": uploaded_by,
            "status": "completed",
            "chunk_count": 1,
            "embedding_ids": [embedding_id],
            "file_size_bytes": len(file_bytes),
        })
    )

    return {
        "entry_id": entry_id,
        "description": description[:200],
        "chunk_count": 1,
        "status": "completed",
    }


async def process_video(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    agent_scope: str | None,
    uploaded_by: str,
) -> dict[str, Any]:
    """Upload a video and enqueue background transcription (no inline processing).

    Per RESEARCH.md Pitfall 2: video transcription is NOT done inline.
    The WorkflowWorker picks up the admin_knowledge_video job and calls
    process_video_transcript when it is ready.

    Args:
        file_bytes: Raw video bytes.
        filename: Original filename.
        mime_type: Video MIME type (video/mp4, …).
        agent_scope: Agent name or None for global.
        uploaded_by: Admin identifier.

    Returns:
        dict with ``entry_id``, ``status="processing"``, and a ``message``.
    """
    client = get_service_client()
    entry_id = str(uuid.uuid4())
    file_path = f"{entry_id}/{filename}"

    # Upload video to Storage
    try:
        client.storage.from_(_STORAGE_BUCKET).upload(
            file_path,
            file_bytes,
            {"content-type": mime_type or "video/mp4"},
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Storage upload failed for video %s: %s", filename, exc)

    # Insert tracking entry with status=processing
    await execute_async(
        client.table("admin_knowledge_entries").insert({
            "id": entry_id,
            "filename": filename,
            "file_type": "video",
            "mime_type": mime_type,
            "file_path": file_path,
            "agent_scope": agent_scope,
            "uploaded_by": uploaded_by,
            "status": "processing",
            "chunk_count": 0,
            "embedding_ids": [],
            "file_size_bytes": len(file_bytes),
        })
    )

    # Enqueue background job
    await execute_async(
        client.table("ai_jobs").insert({
            "job_type": "admin_knowledge_video",
            "status": "pending",
            "input_data": {
                "entry_id": entry_id,
                "file_path": file_path,
                "agent_scope": agent_scope,
                "mime_type": mime_type,
            },
        })
    )

    return {
        "entry_id": entry_id,
        "status": "processing",
        "message": "Video queued for background transcription",
    }


async def process_video_transcript(
    entry_id: str,
    file_path: str,
    agent_scope: str | None,
    mime_type: str = "video/mp4",
) -> dict[str, Any]:
    """Background worker: download video, extract audio, transcribe, chunk, embed.

    Called by WorkflowWorker.handle_admin_knowledge_video when it picks up
    an admin_knowledge_video ai_jobs row.

    Args:
        entry_id: UUID of the admin_knowledge_entries row.
        file_path: Storage path within admin-knowledge bucket.
        agent_scope: Agent name or None for global.
        mime_type: Video MIME type for transcription hints.

    Returns:
        dict with ``entry_id``, ``chunk_count``, ``status``, ``transcript_length``.

    Raises:
        Exception: Re-raises any error so WorkflowWorker can call fail_ai_job.
    """
    client = get_service_client()

    try:
        # Fetch entry metadata (for filename)
        entry_result = await execute_async(
            client.table("admin_knowledge_entries")
            .select("id, filename, agent_scope")
            .eq("id", entry_id)
            .limit(1)
        )
        entry = entry_result.data[0] if entry_result.data else {}
        filename = entry.get("filename", "video")

        # Download video from Storage
        video_bytes: bytes = await asyncio.to_thread(
            client.storage.from_(_STORAGE_BUCKET).download, file_path
        )

        # Extract WAV audio track via ffmpeg
        audio_bytes = await _extract_audio_from_video(video_bytes)

        # Transcribe audio
        transcription = transcribe_audio(audio_bytes, mime_type="audio/wav")
        transcript: str = transcription.get("transcript") or ""

        # Handle empty transcript gracefully
        if not transcript.strip():
            logger.info("No speech detected in video %s — marking completed with 0 chunks", entry_id)
            await execute_async(
                client.table("admin_knowledge_entries")
                .update({"status": "completed", "chunk_count": 0, "updated_at": "now()"})
                .eq("id", entry_id)
            )
            return {
                "entry_id": entry_id,
                "chunk_count": 0,
                "status": "completed",
                "transcript_length": 0,
            }

        # Chunk + embed transcript
        embedding_ids: list[str] = await ingest_document(
            client,
            transcript,
            source_type="admin_training_video",
            source_id=entry_id,
            metadata={
                "scope": "system",
                "agent_scope": agent_scope,
                "filename": filename,
                "source": "video_transcript",
            },
            agent_id=None,
            user_id=None,
        )
        chunk_count = len(embedding_ids)

        # Update tracking entry to completed
        await execute_async(
            client.table("admin_knowledge_entries")
            .update({
                "status": "completed",
                "chunk_count": chunk_count,
                "embedding_ids": embedding_ids,
                "updated_at": "now()",
            })
            .eq("id", entry_id)
        )

        return {
            "entry_id": entry_id,
            "chunk_count": chunk_count,
            "status": "completed",
            "transcript_length": len(transcript),
        }

    except Exception as exc:
        logger.error("Video transcript processing failed for entry %s: %s", entry_id, exc, exc_info=True)
        # Update entry to failed so UI reflects the error
        try:
            await execute_async(
                client.table("admin_knowledge_entries")
                .update({
                    "status": "failed",
                    "error_message": str(exc),
                    "updated_at": "now()",
                })
                .eq("id", entry_id)
            )
        except Exception as update_exc:  # pragma: no cover
            logger.error("Failed to mark entry %s as failed: %s", entry_id, update_exc)
        raise  # re-raise so WorkflowWorker fires fail_ai_job RPC


async def search_system_knowledge(
    query: str,
    agent_name: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Semantic search over system-scoped knowledge embeddings.

    Args:
        query: Natural language query string.
        agent_name: Optional agent name to narrow results (None = all system knowledge).
        top_k: Maximum number of results to return.

    Returns:
        List of dicts with ``content``, ``similarity``, and ``metadata`` keys.
    """
    client = get_service_client()

    embeddings = generate_embeddings_batch([query])
    query_embedding = embeddings[0] if embeddings else []

    result = client.rpc(
        "match_system_knowledge",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.5,
            "match_count": top_k,
            "filter_agent_scope": agent_name,
        },
    ).execute()

    rows = result.data or []
    return [
        {
            "content": row.get("content", ""),
            "similarity": row.get("similarity", 0.0),
            "metadata": row.get("metadata", {}),
        }
        for row in rows
    ]


async def get_knowledge_stats() -> dict[str, Any]:
    """Aggregate knowledge base statistics.

    Returns:
        dict with ``total_entries``, ``total_embeddings``, ``by_agent``,
        and ``storage_bytes`` keys.
    """
    client = get_service_client()

    result = await execute_async(
        client.table("admin_knowledge_entries")
        .select("id, agent_scope, chunk_count, file_size_bytes")
    )
    rows = result.data or []

    total_entries = len(rows)
    total_embeddings = sum(r.get("chunk_count") or 0 for r in rows)
    storage_bytes = sum(r.get("file_size_bytes") or 0 for r in rows)

    by_agent: dict[str, int] = {}
    for row in rows:
        scope = row.get("agent_scope") or "global"
        by_agent[scope] = by_agent.get(scope, 0) + 1

    return {
        "total_entries": total_entries,
        "total_embeddings": total_embeddings,
        "by_agent": by_agent,
        "storage_bytes": storage_bytes,
    }
