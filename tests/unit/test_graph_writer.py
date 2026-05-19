"""Tests for the research graph writer tool.

Updated in Plan 112-05: write_to_graph is now async and delegates to the
shared intelligence module (get_or_create_entity + write_claims).
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.agents.research.tools.graph_writer import write_to_graph

_ENTITY_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CLAIM_UUIDS = [
    UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
    UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
]


def _make_synthesis(
    *,
    findings_count: int = 2,
    query: str = "AI market trends",
    confidence: float = 0.78,
) -> dict:
    """Build a minimal synthesis dict for testing."""
    findings = [
        {
            "text": f"Finding {i} about the topic.",
            "source_url": f"https://example.com/{i}",
            "source_title": f"Source {i}",
            "confidence": 0.8,
        }
        for i in range(findings_count)
    ]
    return {
        "success": True,
        "original_query": query,
        "domain": "financial",
        "confidence": confidence,
        "findings": findings,
        "all_sources": [{"url": "https://example.com/0", "score": 0.9}],
        "tracks_succeeded": 3,
        "tracks_failed": 0,
    }


@pytest.mark.asyncio
@patch(
    "app.services.intelligence.get_or_create_entity",
    new_callable=AsyncMock,
)
@patch(
    "app.services.intelligence.write_claims",
    new_callable=AsyncMock,
)
async def test_write_findings_to_graph_creates_entities(
    mock_write_claims, mock_get_or_create
):
    """get_or_create_entity called once; write_claims called with all findings."""
    mock_get_or_create.return_value = _ENTITY_UUID
    mock_write_claims.return_value = _CLAIM_UUIDS[:3]

    synthesis = _make_synthesis(findings_count=3)

    result = await write_to_graph(synthesis, domain="financial", user_id="user-1")

    assert result["success"] is True
    assert result["entities_written"] == 1
    assert result["findings_written"] == 3
    assert result["entity_id"] == str(_ENTITY_UUID)

    mock_get_or_create.assert_called_once_with(
        canonical_name="AI market trends",
        entity_type="topic",
        domains=["financial"],
        properties={
            "confidence": 0.78,
            "source_count": 1,
            "tracks_succeeded": 3,
        },
    )
    mock_write_claims.assert_called_once()
    payloads = mock_write_claims.call_args[0][0]
    assert len(payloads) == 3
    assert all(p.agent_id == "research" for p in payloads)
    assert all(p.claim_type == "research_finding" for p in payloads)


@pytest.mark.asyncio
@patch(
    "app.services.intelligence.get_or_create_entity",
    new_callable=AsyncMock,
)
async def test_write_findings_handles_db_error(mock_get_or_create):
    """Exception from shared module returns success=False without raising."""
    mock_get_or_create.side_effect = RuntimeError("Connection refused")

    synthesis = _make_synthesis()

    result = await write_to_graph(synthesis, domain="marketing")

    assert result["success"] is False
    assert result["entities_written"] == 0
    assert result["findings_written"] == 0
    assert result["entity_id"] is None
    assert "Connection refused" in result["error"]
