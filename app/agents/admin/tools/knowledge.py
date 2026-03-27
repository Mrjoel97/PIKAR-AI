# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Knowledge management tools for the AdminAgent (Phase 12.1).

Provides 8 tools for managing the agent knowledge base through the AdminAgent
chat interface. Files are uploaded via the REST endpoint; these tools manage
the lifecycle and metadata of knowledge entries.

**Autonomy tiers:**

- AUTO: list_knowledge_entries, search_knowledge, get_knowledge_stats,
  check_knowledge_duplicate, validate_knowledge_relevance, recommend_chunking_strategy
- CONFIRM: upload_knowledge, delete_knowledge_entry

**Upload flow note:**
Files are uploaded via POST /admin/knowledge/upload REST endpoint, which calls
knowledge_service directly. The upload_knowledge tool is called AFTER upload to
confirm the action and report the result. It does NOT receive binary file data.

**SKIL-09 tools:**
check_knowledge_duplicate, validate_knowledge_relevance, and recommend_chunking_strategy
implement pre-upload intelligence for dedup detection, relevance validation, and
optimal chunking strategy recommendation.
"""

from __future__ import annotations

import logging
from typing import Any

import app.services.knowledge_service as knowledge_service
from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Domain keyword sets for relevance validation (SKIL-09)
_AGENT_DOMAIN_KEYWORDS: dict[str, frozenset[str]] = {
    "financial": frozenset({
        "revenue", "cost", "profit", "margin", "budget", "expense", "invoice",
        "forecast", "financial", "accounting", "cashflow", "balance", "audit",
        "tax", "payment", "income", "loss", "equity", "asset", "liability",
    }),
    "marketing": frozenset({
        "marketing", "campaign", "brand", "seo", "social", "ad", "conversion",
        "engagement", "analytics", "content", "lead", "funnel", "acquisition",
        "retention", "email", "promotion", "advertising", "market", "audience",
    }),
    "sales": frozenset({
        "sales", "deal", "pipeline", "prospect", "customer", "crm", "quota",
        "revenue", "negotiation", "proposal", "contract", "close", "lead",
        "account", "opportunity", "forecast", "target", "commission",
    }),
    "hr": frozenset({
        "employee", "hiring", "onboarding", "payroll", "performance", "hr",
        "benefits", "recruitment", "training", "culture", "policy", "leave",
        "compensation", "review", "talent", "workforce", "retention",
    }),
    "compliance": frozenset({
        "compliance", "regulation", "legal", "policy", "audit", "risk",
        "gdpr", "sox", "hipaa", "security", "governance", "control",
        "requirement", "standard", "procedure", "documentation",
    }),
    "operations": frozenset({
        "operations", "process", "workflow", "efficiency", "supply", "vendor",
        "logistics", "inventory", "production", "quality", "project",
        "delivery", "sla", "automation", "infrastructure", "resource",
    }),
    "strategic": frozenset({
        "strategy", "growth", "vision", "mission", "objective", "goal",
        "planning", "market", "competitive", "opportunity", "roadmap",
        "innovation", "transformation", "expansion", "partnership",
    }),
    "content": frozenset({
        "content", "blog", "article", "copy", "writing", "creative", "media",
        "publication", "editorial", "story", "narrative", "brand", "voice",
        "video", "image", "design", "portfolio",
    }),
    "customer_support": frozenset({
        "customer", "support", "ticket", "resolution", "complaint", "service",
        "help", "satisfaction", "feedback", "escalation", "issue", "problem",
        "response", "faq", "knowledge", "refund",
    }),
    "data": frozenset({
        "data", "analytics", "metrics", "dashboard", "report", "insight",
        "kpi", "visualization", "pipeline", "etl", "database", "query",
        "model", "ml", "prediction", "analysis", "statistics",
    }),
}


# ---------------------------------------------------------------------------
# Tool 1: upload_knowledge (confirm tier)
# ---------------------------------------------------------------------------


async def upload_knowledge(
    entry_id: str,
    filename: str,
    mime_type: str,
    agent_scope: str | None = None,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Confirm and report the result of a knowledge upload.

    Files are uploaded via the REST endpoint POST /admin/knowledge/upload,
    which processes the file and creates the admin_knowledge_entries row.
    This tool is called AFTER the file is stored to confirm the action and
    return the processing result to the AdminAgent.

    Autonomy tier: confirm (KNOW-04).

    Args:
        entry_id: UUID of the admin_knowledge_entries row created by the REST upload.
        filename: Original filename (for confirmation display).
        mime_type: MIME type of the uploaded file.
        agent_scope: Agent name to restrict scope, or None for global access.
        confirmation_token: Token from a prior confirmation request.

    Returns:
        Without token: ``{"requires_confirmation": True, ...}`` dict.
        With token: Entry details with ``entry_id``, ``status``, ``chunk_count``.
    """
    gate = await _check_autonomy("upload_knowledge")
    if gate is not None and confirmation_token is None:
        return gate

    try:
        result = await execute_async(
            get_service_client()
            .table("admin_knowledge_entries")
            .select("id, filename, file_type, status, chunk_count, agent_scope, created_at")
            .eq("id", entry_id)
            .limit(1)
        )
        rows = result.data or []
        if not rows:
            return {"error": f"Entry '{entry_id}' not found"}
        row = rows[0]
        return {
            "entry_id": row.get("id"),
            "filename": row.get("filename"),
            "file_type": row.get("file_type"),
            "status": row.get("status"),
            "chunk_count": row.get("chunk_count"),
            "agent_scope": row.get("agent_scope"),
            "created_at": row.get("created_at"),
        }
    except Exception as exc:
        logger.error("upload_knowledge failed for entry %s: %s", entry_id, exc)
        return {"error": f"Failed to confirm upload for '{entry_id}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: list_knowledge_entries (auto tier)
# ---------------------------------------------------------------------------


async def list_knowledge_entries(
    agent_scope: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]] | dict[str, Any]:
    """List knowledge entries, optionally filtered by agent_scope and status.

    Autonomy tier: auto (read-only).

    Args:
        agent_scope: Filter by agent name (e.g. "financial"), or None for all entries.
        status: Filter by processing status (e.g. "completed", "processing", "failed").
        limit: Maximum number of rows to return (default 20).

    Returns:
        List of entry dicts ordered newest-first, or ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("list_knowledge_entries")
    if gate is not None:
        return gate

    try:
        client = get_service_client()
        query = (
            client.table("admin_knowledge_entries")
            .select(
                "id, filename, file_type, mime_type, agent_scope, status, "
                "chunk_count, file_size_bytes, uploaded_by, created_at"
            )
            .order("created_at", desc=True)
            .limit(limit)
        )
        if agent_scope is not None:
            query = query.eq("agent_scope", agent_scope)
        if status is not None:
            query = query.eq("status", status)

        result = await execute_async(query)
        return result.data or []
    except Exception as exc:
        logger.error("list_knowledge_entries failed: %s", exc)
        return {"error": f"Failed to list knowledge entries: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: search_knowledge (auto tier)
# ---------------------------------------------------------------------------


async def search_knowledge(
    query: str,
    agent_name: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Search the knowledge base using semantic similarity.

    Delegates to knowledge_service.search_system_knowledge to perform
    vector similarity search over system-scoped embeddings.

    Autonomy tier: auto (read-only).

    Args:
        query: Natural language query string.
        agent_name: Optional agent name to narrow results. None returns all.
        top_k: Maximum number of results to return (default 5).

    Returns:
        List of ``{"content", "similarity", "metadata"}`` dicts, or error dict.
    """
    gate = await _check_autonomy("search_knowledge")
    if gate is not None:
        return gate

    try:
        return await knowledge_service.search_system_knowledge(
            query=query, agent_name=agent_name, top_k=top_k
        )
    except Exception as exc:
        logger.error("search_knowledge failed: %s", exc)
        return {"error": f"Failed to search knowledge: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: delete_knowledge_entry (confirm tier)
# ---------------------------------------------------------------------------


async def delete_knowledge_entry(
    entry_id: str,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Delete a knowledge entry, its embeddings, and its Storage file.

    Autonomy tier: confirm (KNOW-05 destructive action).

    Args:
        entry_id: UUID of the admin_knowledge_entries row to delete.
        confirmation_token: Token from a prior confirmation request.

    Returns:
        Without token: ``{"requires_confirmation": True, ...}`` dict.
        With token: ``{"deleted": True, "entry_id": str}`` on success.
    """
    gate = await _check_autonomy("delete_knowledge_entry")
    if gate is not None and confirmation_token is None:
        return gate

    client = get_service_client()
    try:
        # Fetch entry to get file_path for storage deletion
        entry_result = await execute_async(
            client.table("admin_knowledge_entries")
            .select("id, file_path")
            .eq("id", entry_id)
            .limit(1)
        )
        if not (entry_result.data or []):
            return {"error": f"Entry '{entry_id}' not found"}

        # Delete embeddings first (referential safety)
        await execute_async(
            client.table("embeddings")
            .delete()
            .eq("source_id", entry_id)
        )

        # Delete the tracking entry
        await execute_async(
            client.table("admin_knowledge_entries")
            .delete()
            .eq("id", entry_id)
        )

        # Attempt Storage cleanup (non-fatal)
        try:
            file_path = entry_result.data[0].get("file_path")
            if file_path:
                client.storage.from_("admin-knowledge").remove([file_path])
        except Exception as storage_exc:
            logger.warning("Storage cleanup failed for %s: %s", entry_id, storage_exc)

        return {"deleted": True, "entry_id": entry_id}
    except Exception as exc:
        logger.error("delete_knowledge_entry failed for %s: %s", entry_id, exc)
        return {"error": f"Failed to delete entry '{entry_id}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 5: get_knowledge_stats (auto tier)
# ---------------------------------------------------------------------------


async def get_knowledge_stats() -> dict[str, Any]:
    """Return aggregated knowledge base statistics.

    Delegates to knowledge_service.get_knowledge_stats().

    Autonomy tier: auto (read-only).

    Returns:
        Dict with ``total_entries``, ``total_embeddings``, ``by_agent``,
        and ``storage_bytes`` keys, or ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("get_knowledge_stats")
    if gate is not None:
        return gate

    try:
        return await knowledge_service.get_knowledge_stats()
    except Exception as exc:
        logger.error("get_knowledge_stats failed: %s", exc)
        return {"error": f"Failed to get knowledge stats: {exc}"}


# ---------------------------------------------------------------------------
# Tool 6: check_knowledge_duplicate (auto tier) -- SKIL-09
# ---------------------------------------------------------------------------


async def check_knowledge_duplicate(
    text_sample: str,
    agent_scope: str | None = None,
    threshold: float = 0.92,
) -> dict[str, Any]:
    """Detect near-duplicate content before uploading (SKIL-09).

    Takes the first 500 characters of text_sample, searches the knowledge base,
    and reports whether similar content already exists above the threshold.

    Autonomy tier: auto (SKIL-09 pre-upload intelligence).

    Args:
        text_sample: Sample text from the document to check (first 500 chars used).
        agent_scope: Agent scope to check within, or None to check all system knowledge.
        threshold: Similarity threshold above which content is considered a near-duplicate
            (default 0.92).

    Returns:
        ``{"near_duplicate": True, "similar_entry": ..., "similarity": float}`` if
        a near-duplicate is found, or ``{"near_duplicate": False, "closest_similarity": float}``.
    """
    gate = await _check_autonomy("check_knowledge_duplicate")
    if gate is not None:
        return gate

    try:
        sample = text_sample[:500]
        results = await knowledge_service.search_system_knowledge(
            query=sample, agent_name=agent_scope, top_k=3
        )

        if results:
            top = results[0]
            similarity = top.get("similarity", 0.0)
            if similarity > threshold:
                return {
                    "near_duplicate": True,
                    "similar_entry": top.get("content", "")[:200],
                    "similarity": similarity,
                    "metadata": top.get("metadata", {}),
                }
            return {
                "near_duplicate": False,
                "closest_similarity": similarity,
            }

        return {"near_duplicate": False, "closest_similarity": 0.0}
    except Exception as exc:
        logger.error("check_knowledge_duplicate failed: %s", exc)
        return {"error": f"Failed to check for duplicates: {exc}"}


# ---------------------------------------------------------------------------
# Tool 7: validate_knowledge_relevance (auto tier) -- SKIL-09
# ---------------------------------------------------------------------------


async def validate_knowledge_relevance(
    text_sample: str,
    target_agent: str,
) -> dict[str, Any]:
    """Validate that content is relevant to a target agent's domain (SKIL-09).

    Checks the text_sample against domain keyword sets for the target agent
    and returns a relevance assessment with confidence score.

    Autonomy tier: auto (SKIL-09 pre-upload intelligence).

    Args:
        text_sample: Sample text to evaluate for relevance.
        target_agent: The agent name to validate relevance against
            (e.g. "financial", "marketing").

    Returns:
        ``{"relevant": bool, "confidence": float, "reason": str}`` dict.
    """
    gate = await _check_autonomy("validate_knowledge_relevance")
    if gate is not None:
        return gate

    try:
        domain_keywords = _AGENT_DOMAIN_KEYWORDS.get(target_agent.lower(), frozenset())

        if not domain_keywords:
            return {
                "relevant": True,
                "confidence": 0.5,
                "reason": f"No domain keywords configured for agent '{target_agent}'. Defaulting to relevant.",
            }

        # Tokenize the text sample (simple whitespace split, lowercase)
        words = set(text_sample.lower().split())
        # Count keyword matches
        matched = domain_keywords & words
        match_count = len(matched)

        # Confidence based on match ratio (at least 3 matches = moderate confidence)
        confidence: float
        if match_count >= 5:
            confidence = min(0.95, 0.6 + match_count * 0.05)
        elif match_count >= 2:
            confidence = 0.4 + match_count * 0.08
        elif match_count == 1:
            confidence = 0.3
        else:
            confidence = 0.1

        relevant = match_count >= 2
        matched_list = sorted(matched)[:5]  # show up to 5 matched keywords

        reason: str
        if relevant:
            reason = (
                f"Content matches {match_count} domain keywords for '{target_agent}': "
                f"{', '.join(matched_list)}"
            )
        else:
            reason = (
                f"Content has low domain relevance for '{target_agent}' "
                f"({match_count} keyword matches). Consider uploading to a more relevant agent."
            )

        return {"relevant": relevant, "confidence": round(confidence, 2), "reason": reason}
    except Exception as exc:
        logger.error("validate_knowledge_relevance failed for %s: %s", target_agent, exc)
        return {"error": f"Failed to validate relevance: {exc}"}


# ---------------------------------------------------------------------------
# Tool 8: recommend_chunking_strategy (auto tier) -- SKIL-09
# ---------------------------------------------------------------------------


async def recommend_chunking_strategy(
    filename: str,
    file_size_bytes: int,
    mime_type: str,
) -> dict[str, Any]:
    """Recommend optimal chunking strategy for a file (SKIL-09).

    Returns chunk_size and overlap recommendations based on file type and size.
    Does not require DB access — pure logic based on mime_type and file_size_bytes.

    Autonomy tier: auto (SKIL-09 pre-upload intelligence).

    Args:
        filename: Original filename (used for MIME-type hints and display).
        file_size_bytes: File size in bytes.
        mime_type: MIME type of the file.

    Returns:
        ``{"chunk_size": int, "chunk_overlap": int, "estimated_chunks": int, "warnings": list}``
    """
    gate = await _check_autonomy("recommend_chunking_strategy")
    if gate is not None:
        return gate

    warnings: list[str] = []
    normalized_mime = (mime_type or "").lower().split(";")[0].strip()

    # Images and videos have their own processing paths — chunking not applicable
    if normalized_mime.startswith("image/"):
        return {
            "chunk_size": 0,
            "chunk_overlap": 0,
            "estimated_chunks": 1,
            "warnings": ["Image files are embedded as a single description chunk via Gemini vision."],
        }

    if normalized_mime.startswith("video/"):
        return {
            "chunk_size": 500,
            "chunk_overlap": 50,
            "estimated_chunks": 0,
            "warnings": ["Video files are transcribed via background worker. Chunk count depends on transcript length."],
        }

    # Text / document chunking strategy
    if file_size_bytes > 500_000:  # >500KB
        chunk_size = 500
        chunk_overlap = 50
        # Rough estimate: average ~400 chars per chunk accounting for overlap
        estimated_chunks = max(1, file_size_bytes // 400)
        warnings.append(
            f"Large document ({file_size_bytes // 1024}KB). "
            f"Estimated {estimated_chunks} chunks. Consider summarizing before upload to reduce token usage."
        )
    elif file_size_bytes < 5_000:  # <5KB (short doc)
        chunk_size = 300
        chunk_overlap = 30
        estimated_chunks = max(1, file_size_bytes // 270)
    else:  # 5KB-500KB (standard)
        chunk_size = 500
        chunk_overlap = 50
        estimated_chunks = max(1, file_size_bytes // 450)

    return {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "estimated_chunks": estimated_chunks,
        "warnings": warnings,
    }
