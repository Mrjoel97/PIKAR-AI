# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared knowledge search tool used by multiple agents.

Relocated from app.agents.content.tools to avoid tight coupling -- this tool
is used by HR, Customer Support, Compliance, Data, Marketing, and Content agents.
"""

import logging

logger = logging.getLogger(__name__)


async def search_knowledge(
    query: str,
    top_k: int = 3,
    user_id: str | None = None,
) -> dict:
    """Search business knowledge base for relevant information.

    Args:
        query: The search query to find relevant business knowledge.
        top_k: Maximum number of results to return.
        user_id: Optional user scope for multi-tenant knowledge lookups.

    Returns:
        Dictionary containing search results.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge as kb_search
        from app.services.request_context import get_current_user_id

        scoped_user_id = user_id or get_current_user_id()
        return await kb_search(query, top_k=top_k, user_id=scoped_user_id)
    except Exception as exc:
        logger.warning("Shared search_knowledge failed: %s", exc)
        return {"results": [], "query": query, "error": str(exc)}
