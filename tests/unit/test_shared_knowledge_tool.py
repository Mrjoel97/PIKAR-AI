from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_shared_search_knowledge_awaits_vault_search_and_scopes_current_user(
    monkeypatch,
):
    from app.agents.tools import knowledge as shared_knowledge
    from app.rag import knowledge_vault
    from app.services import request_context

    vault_search = AsyncMock(return_value={"results": [{"id": "doc-1"}]})
    monkeypatch.setattr(knowledge_vault, "search_knowledge", vault_search)
    monkeypatch.setattr(request_context, "get_current_user_id", lambda: "user-123")

    result = await shared_knowledge.search_knowledge("pricing strategy")

    assert result == {"results": [{"id": "doc-1"}]}
    vault_search.assert_awaited_once_with(
        "pricing strategy",
        top_k=3,
        user_id="user-123",
    )


@pytest.mark.asyncio
async def test_read_docs_awaits_shared_search_knowledge(monkeypatch):
    from app.agents.tools import workflow_ops

    search_mock = AsyncMock(
        return_value={
            "results": [
                {"title": "Doc 1"},
                {"title": "Doc 2"},
            ]
        }
    )
    audit_mock = AsyncMock()
    monkeypatch.setattr(workflow_ops, "search_knowledge", search_mock)
    monkeypatch.setattr(workflow_ops, "_audit_event", audit_mock)

    result = await workflow_ops.read_docs(query="workflow docs", limit=1)

    assert result["documents"] == [{"title": "Doc 1"}]
    assert result["count"] == 1
    search_mock.assert_awaited_once_with("workflow docs")
    audit_mock.assert_awaited_once()
