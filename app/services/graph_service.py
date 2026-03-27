# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Knowledge Graph service for reading and writing structured intelligence.

Provides query methods for entities, relationships, and findings in the
knowledge graph. Handles entity resolution (exact match -> alias -> semantic)
and freshness checking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class GraphService:
    """Service for querying the knowledge graph stored in Supabase."""

    def __init__(self, supabase_client: Any) -> None:
        self._db = supabase_client

    def query_entity(
        self,
        query: str,
        domain: str,
        include_findings: bool = True,
        include_relationships: bool = True,
        findings_limit: int = 10,
    ) -> dict[str, Any]:
        """Query the knowledge graph for an entity and its context.

        Resolution order: exact canonical_name -> alias -> (semantic in Phase 2).

        Args:
            query: Entity name or alias to search for.
            domain: Domain to scope findings and relationships.
            include_findings: Whether to fetch related findings.
            include_relationships: Whether to fetch related edges.
            findings_limit: Max findings to return.

        Returns:
            Dict with keys: found, entity, findings, relationships, error.
        """
        try:
            # Step 1: exact name match
            entity = self._query_by_name(query)
            # Step 2: alias match
            if entity is None:
                entity = self._query_by_alias(query)

            if entity is None:
                return {
                    "found": False,
                    "entity": None,
                    "findings": [],
                    "relationships": [],
                    "query": query,
                    "domain": domain,
                }

            findings: list[dict[str, Any]] = []
            relationships: list[dict[str, Any]] = []
            if include_findings:
                findings = self._get_findings(entity["id"], domain, findings_limit)
            if include_relationships:
                relationships = self._get_relationships(entity["id"], domain)

            return {
                "found": True,
                "entity": entity,
                "findings": findings,
                "relationships": relationships,
                "query": query,
                "domain": domain,
            }
        except Exception as e:
            logger.error("Graph query error for '%s' in %s: %s", query, domain, e)
            return {
                "found": False,
                "entity": None,
                "findings": [],
                "relationships": [],
                "query": query,
                "domain": domain,
                "error": str(e),
            }

    def _query_by_name(self, name: str) -> dict[str, Any] | None:
        """Find entity by exact canonical_name (case-insensitive)."""
        response = (
            self._db.table("kg_entities")
            .select("*")
            .ilike("canonical_name", name)
            .execute()
        )
        return response.data[0] if response.data else None

    def _query_by_alias(self, alias: str) -> dict[str, Any] | None:
        """Find entity via alias table (case-insensitive)."""
        alias_response = (
            self._db.table("kg_aliases")
            .select("entity_id")
            .ilike("alias", alias)
            .execute()
        )
        if not alias_response.data:
            return None
        entity_id = alias_response.data[0]["entity_id"]
        entity_response = (
            self._db.table("kg_entities").select("*").eq("id", entity_id).execute()
        )
        return entity_response.data[0] if entity_response.data else None

    def _get_findings(
        self, entity_id: str, domain: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get findings for an entity in a specific domain."""
        response = (
            self._db.table("kg_findings")
            .select("id, finding_text, confidence, sources, contradicts, freshness_at")
            .eq("entity_id", entity_id)
            .eq("domain", domain)
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def _get_relationships(self, entity_id: str, domain: str) -> list[dict[str, Any]]:
        """Get edges from an entity in a specific domain, with target names.

        Uses batch query for target names to avoid N+1.
        """
        response = (
            self._db.table("kg_edges")
            .select("id, relationship, target_id, confidence, evidence, source_url")
            .eq("source_id", entity_id)
            .eq("domain", domain)
            .execute()
        )
        edges = response.data or []
        if not edges:
            return []

        # Batch-resolve target names
        target_ids = list({edge["target_id"] for edge in edges})
        targets_resp = (
            self._db.table("kg_entities")
            .select("id, canonical_name")
            .in_("id", target_ids)
            .execute()
        )
        target_map = {t["id"]: t["canonical_name"] for t in (targets_resp.data or [])}
        for edge in edges:
            edge["target_name"] = target_map.get(edge["target_id"], "Unknown")
        return edges

    @staticmethod
    def is_stale(freshness_at: str, threshold_hours: float) -> bool:
        """Check if a timestamp is older than the threshold.

        Args:
            freshness_at: ISO format timestamp string.
            threshold_hours: Maximum age in hours before data is stale.

        Returns:
            True if the data is stale (older than threshold).
        """
        if not freshness_at:
            return True
        try:
            ts = datetime.fromisoformat(freshness_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(tz=timezone.utc) - ts).total_seconds() / 3600
            return age_hours > threshold_hours
        except (ValueError, TypeError):
            return True
