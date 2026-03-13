from unittest.mock import AsyncMock

import pytest

from app.agents.tools import deep_research as deep_research_module


@pytest.mark.asyncio
async def test_research_uses_wrappers_and_returns_structured_output(monkeypatch):
    search_mock = AsyncMock(
        return_value={
            "success": True,
            "answer": "summary",
            "results": [
                {
                    "title": "Source A",
                    "url": "https://example.com/a",
                    "content": "AI copilots are growing quickly in SMB workflows. More details follow.",
                    "score": 0.9,
                }
            ],
        }
    )
    scrape_mock = AsyncMock(
        return_value={
            "success": True,
            "markdown": "Detailed markdown content for structured synthesis. " * 30,
            "metadata": {"title": "Example"},
        }
    )
    ingest_mock = AsyncMock(return_value={"success": True})

    monkeypatch.setattr(deep_research_module, "web_search_with_context", search_mock)
    monkeypatch.setattr(deep_research_module, "web_scrape", scrape_mock)
    monkeypatch.setattr(deep_research_module, "ingest_document_content", ingest_mock)

    tool = deep_research_module.DeepResearchTool()
    result = await tool.research(
        topic="AI copilots for SMBs",
        research_type="market",
        num_sources=3,
        scrape_top_n=1,
        user_id="user-123",
        save_to_vault=True,
    )

    assert result["success"] is True
    assert result["saved_to_vault"] is True
    assert result["confidence_score"] > 0
    assert result["provider_status"]["search"]["successful_queries"] == 3
    assert result["provider_status"]["scrape"]["successful_urls"] == 1
    assert result["citations"][0]["url"] == "https://example.com/a"
    assert result["recommended_next_questions"]
    assert search_mock.await_count == 3
    assert scrape_mock.await_count == 1
    assert ingest_mock.await_count == 1
    assert search_mock.await_args_list[0].kwargs["agent_name"] == "deep_research"


@pytest.mark.asyncio
async def test_search_with_retry_retries_transient_failures(monkeypatch):
    search_mock = AsyncMock(
        side_effect=[
            {"success": False, "error": "temporary outage", "results": []},
            {
                "success": True,
                "results": [
                    {
                        "title": "Retry Source",
                        "url": "https://example.com/retry",
                        "content": "Recovered after retry.",
                        "score": 0.7,
                    }
                ],
            },
        ]
    )
    monkeypatch.setattr(deep_research_module, "web_search_with_context", search_mock)

    tool = deep_research_module.DeepResearchTool()
    tool.max_retries = 1
    tool.retry_delay_seconds = 0

    result = await tool._search_with_retry(
        query="AI copilots retry",
        max_results=5,
        depth="deep",
        user_id="user-123",
    )

    assert result["success"] is True
    assert search_mock.await_count == 2


@pytest.mark.asyncio
async def test_research_reports_vault_skip_without_user_id(monkeypatch):
    search_mock = AsyncMock(
        return_value={
            "success": True,
            "results": [
                {
                    "title": "Source B",
                    "url": "https://example.com/b",
                    "content": "Useful competitor data from a public source. More details follow.",
                    "score": 0.8,
                }
            ],
        }
    )
    scrape_mock = AsyncMock(
        return_value={
            "success": True,
            "markdown": "Long markdown content for competitor analysis. " * 20,
            "metadata": {"title": "Example B"},
        }
    )

    monkeypatch.setattr(deep_research_module, "web_search_with_context", search_mock)
    monkeypatch.setattr(deep_research_module, "web_scrape", scrape_mock)

    tool = deep_research_module.DeepResearchTool()
    result = await tool.research(
        topic="AI SDR tools",
        research_type="competitor",
        num_sources=2,
        scrape_top_n=1,
        save_to_vault=True,
    )

    assert result["success"] is True
    assert result["saved_to_vault"] is False
    assert any("Vault save skipped" in item for item in result["limitations"])
