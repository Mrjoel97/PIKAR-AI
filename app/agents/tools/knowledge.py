# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared knowledge search tool used by multiple agents.

Relocated from app.agents.content.tools to avoid tight coupling -- this tool
is used by HR, Customer Support, Compliance, Data, Marketing, and Content agents.
"""

import logging

logger = logging.getLogger(__name__)


def search_knowledge(query: str) -> dict:
    """Search business knowledge base for relevant information.

    Args:
        query: The search query to find relevant business knowledge.

    Returns:
        Dictionary containing search results.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge as kb_search

        return kb_search(query, top_k=3)
    except Exception:
        return {"results": []}
