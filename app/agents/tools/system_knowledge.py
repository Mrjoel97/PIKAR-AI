# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""System knowledge search tool for user-facing agents (Phase 12.1).

Provides access to admin-uploaded training data (KNOW-06).
Each specialized agent adds this tool to its tools list so it can
query the knowledge base that admin has curated for business operations.

The tool passes agent_name=None to return ALL system-scoped knowledge
(both global and all agent-scoped entries). This is intentional —
the match_system_knowledge RPC with filter_agent_scope=NULL returns
all system-scoped entries, giving agents access to the full knowledge base.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def search_system_knowledge(
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Search admin-uploaded system knowledge relevant to the current query.

    Use this tool to find business-specific training data, documents, and
    reference material that the admin has uploaded for your domain.

    Args:
        query: The search query describing what knowledge to find.
        top_k: Maximum number of results to return (default 5).

    Returns:
        Dict with ``results`` list of matching knowledge entries (content + similarity)
        and ``count`` of results returned.
    """
    from app.services.knowledge_service import search_system_knowledge as _search

    try:
        results = await _search(query=query, agent_name=None, top_k=top_k)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.warning("System knowledge search failed: %s", e)
        return {"results": [], "count": 0, "error": str(e)}
