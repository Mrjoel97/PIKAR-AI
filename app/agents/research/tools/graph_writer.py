"""Graph writer for persisting research findings to the knowledge graph.

Writes synthesized research output to two destinations:
1. Knowledge Graph (kg_entities + kg_findings) — structured graph nodes
2. Knowledge Vault (embeddings) — full markdown report for RAG retrieval

Both functions are designed to never raise on failure, returning a
success=False dict instead. This keeps the research pipeline resilient:
a persistence failure should not block the agent from returning results
to the user.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase():
    """Get Supabase client. Isolated for easy test patching."""
    from app.services.supabase_client import get_supabase_client

    return get_supabase_client()


def write_to_graph(
    synthesis: dict[str, Any],
    domain: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Persist synthesized findings to the knowledge graph tables.

    Creates a topic entity via upsert on kg_entities, then inserts each
    finding into kg_findings linked to that entity.

    Args:
        synthesis: Output from synthesize_tracks() containing findings,
                   confidence, all_sources, original_query, etc.
        domain: Agent domain (e.g. 'financial', 'marketing').
        user_id: Optional user ID for audit trail.

    Returns:
        Dict with success flag, counts of entities/findings written,
        and the entity ID (or None on failure).
    """
    try:
        client = _get_supabase()

        original_query = synthesis.get("original_query", "research topic")
        confidence = synthesis.get("confidence", 0.5)
        findings = synthesis.get("findings", [])
        sources = synthesis.get("all_sources", [])

        # Upsert topic entity
        entity_data = {
            "canonical_name": original_query,
            "entity_type": "topic",
            "domains": [domain],
            "properties": {
                "confidence": confidence,
                "source_count": len(sources),
                "tracks_succeeded": synthesis.get("tracks_succeeded", 0),
            },
            "source_count": len(sources),
        }

        entity_result = (
            client.table("kg_entities")
            .upsert(entity_data, on_conflict="canonical_name,entity_type")
            .execute()
        )

        entity_id = None
        if entity_result.data:
            entity_id = entity_result.data[0].get("id")

        if not entity_id:
            logger.warning("Entity upsert returned no ID for '%s'", original_query)
            return {
                "success": False,
                "entities_written": 0,
                "findings_written": 0,
                "entity_id": None,
                "error": "Entity upsert returned no ID",
            }

        # Insert findings
        findings_written = 0
        for finding in findings:
            finding_data = {
                "entity_id": entity_id,
                "domain": domain,
                "finding_text": finding.get("text", ""),
                "confidence": finding.get("confidence", 0.5),
                "sources": json.dumps(
                    [
                        {
                            "url": finding.get("source_url", ""),
                            "title": finding.get("source_title", ""),
                        }
                    ]
                ),
            }

            client.table("kg_findings").insert(finding_data).execute()
            findings_written += 1

        logger.info(
            "Graph write complete: entity=%s, findings=%d, domain=%s",
            entity_id,
            findings_written,
            domain,
        )

        return {
            "success": True,
            "entities_written": 1,
            "findings_written": findings_written,
            "entity_id": entity_id,
        }

    except Exception as e:
        logger.error("Graph write failed: %s", e)
        return {
            "success": False,
            "entities_written": 0,
            "findings_written": 0,
            "entity_id": None,
            "error": str(e),
        }


async def write_to_vault(
    synthesis: dict[str, Any],
    topic: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Persist a full markdown research report to the Knowledge Vault.

    Builds a markdown document from the synthesis and calls
    ingest_document_content() to chunk, embed, and store it for
    future RAG retrieval.

    Args:
        synthesis: Output from synthesize_tracks().
        topic: Human-readable research topic / title.
        user_id: Optional user ID for multi-tenant isolation.

    Returns:
        Dict with success flag and vault metadata (chunk_count, etc.).
    """
    try:
        from app.rag.knowledge_vault import ingest_document_content

        # Build markdown report
        report = _build_markdown_report(synthesis, topic)

        if not report.strip():
            return {
                "success": False,
                "error": "Empty report — nothing to store",
            }

        result = await ingest_document_content(
            content=report,
            title=f"Research: {topic}",
            document_type="research_report",
            user_id=user_id,
            metadata={
                "domain": synthesis.get("domain", ""),
                "confidence": synthesis.get("confidence", 0),
                "source": "research_agent",
            },
        )

        return {
            "success": result.get("success", False),
            "chunk_count": result.get("chunk_count", 0),
            "embedding_ids": result.get("embedding_ids", []),
            "title": result.get("title", ""),
        }

    except Exception as e:
        logger.error("Vault write failed for topic '%s': %s", topic, e)
        return {
            "success": False,
            "error": str(e),
        }


def _build_markdown_report(
    synthesis: dict[str, Any],
    topic: str,
) -> str:
    """Build a markdown research report from synthesis output.

    Args:
        synthesis: Synthesis dict with findings, sources, confidence.
        topic: Research topic title.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    lines.append(f"# Research Report: {topic}")
    lines.append("")

    confidence = synthesis.get("confidence", 0)
    lines.append(f"**Confidence:** {confidence:.1%}")
    lines.append(
        f"**Tracks:** {synthesis.get('tracks_succeeded', 0)} succeeded, "
        f"{synthesis.get('tracks_failed', 0)} failed"
    )
    lines.append("")

    # Findings
    findings = synthesis.get("findings", [])
    if findings:
        lines.append("## Key Findings")
        lines.append("")
        for i, finding in enumerate(findings, 1):
            text = finding.get("text", "").strip()
            source_url = finding.get("source_url", "")
            if text:
                lines.append(f"### Finding {i}")
                lines.append(text)
                if source_url:
                    lines.append(f"\n*Source: {source_url}*")
                lines.append("")

    # Contradictions
    contradictions = synthesis.get("contradictions", [])
    if contradictions:
        lines.append("## Contradictions")
        lines.append("")
        for contradiction in contradictions:
            lines.append(f"- {contradiction}")
        lines.append("")

    # Sources
    sources = synthesis.get("all_sources", [])
    if sources:
        lines.append("## Sources")
        lines.append("")
        for source in sources[:10]:
            title = source.get("title", source.get("url", "Unknown"))
            url = source.get("url", "")
            score = source.get("score", 0)
            lines.append(f"- [{title}]({url}) (relevance: {score:.2f})")
        lines.append("")

    return "\n".join(lines)


# ADK tool export
GRAPH_WRITER_TOOLS = [write_to_graph]
