"""Unit tests for the search_system_knowledge user-facing agent tool (Phase 12.1).

Tests verify:
- search_system_knowledge tool delegates to knowledge_service with query and top_k
- search_system_knowledge returns empty list when no system knowledge exists
- search_system_knowledge returns both global and agent-scoped results
"""

from unittest.mock import AsyncMock, patch

import pytest

_KNOWLEDGE_SERVICE_SEARCH_PATCH = (
    "app.services.knowledge_service.search_system_knowledge"
)


@pytest.mark.asyncio
async def test_search_system_knowledge_tool():
    """search_system_knowledge delegates to knowledge_service.search_system_knowledge."""
    fake_results = [
        {"content": "Financial policy document", "similarity": 0.91, "metadata": {"scope": "system"}},
        {"content": "Global training material", "similarity": 0.85, "metadata": {"scope": "system"}},
    ]

    with patch(
        _KNOWLEDGE_SERVICE_SEARCH_PATCH,
        new_callable=AsyncMock,
        return_value=fake_results,
    ) as mock_search:
        from app.agents.tools.system_knowledge import search_system_knowledge

        result = await search_system_knowledge(query="financial policy", top_k=5)

    assert result["count"] == 2
    assert len(result["results"]) == 2
    assert result["results"][0]["similarity"] == 0.91
    mock_search.assert_called_once_with(query="financial policy", agent_name=None, top_k=5)


@pytest.mark.asyncio
async def test_search_system_knowledge_empty():
    """search_system_knowledge returns empty results when no knowledge exists."""
    with patch(
        _KNOWLEDGE_SERVICE_SEARCH_PATCH,
        new_callable=AsyncMock,
        return_value=[],
    ):
        from app.agents.tools.system_knowledge import search_system_knowledge

        result = await search_system_knowledge(query="nonexistent topic", top_k=3)

    assert result["count"] == 0
    assert result["results"] == []
    assert "error" not in result


@pytest.mark.asyncio
async def test_search_system_knowledge_returns_global_and_agent():
    """search_system_knowledge returns both global and agent-scoped results."""
    mixed_results = [
        {"content": "Agent-specific doc", "similarity": 0.93, "metadata": {"scope": "system", "agent_scope": "financial"}},
        {"content": "Global doc", "similarity": 0.88, "metadata": {"scope": "system", "agent_scope": None}},
        {"content": "Another global", "similarity": 0.82, "metadata": {"scope": "system", "agent_scope": None}},
    ]

    with patch(
        _KNOWLEDGE_SERVICE_SEARCH_PATCH,
        new_callable=AsyncMock,
        return_value=mixed_results,
    ):
        from app.agents.tools.system_knowledge import search_system_knowledge

        result = await search_system_knowledge(query="training data", top_k=5)

    assert result["count"] == 3
    # Verify both agent-scoped and global entries are returned
    scopes = [r["metadata"].get("agent_scope") for r in result["results"]]
    assert "financial" in scopes
    assert None in scopes
