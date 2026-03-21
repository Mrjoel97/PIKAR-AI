"""Tests for the research graph writer tool."""

from unittest.mock import MagicMock, patch

from app.agents.research.tools.graph_writer import write_to_graph


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


def _mock_client_with_entity_id(entity_id: str = "ent-uuid-123") -> MagicMock:
    """Return a mock Supabase client that supports upsert and insert chains."""
    client = MagicMock()

    # kg_entities upsert chain
    upsert_result = MagicMock()
    upsert_result.data = [{"id": entity_id}]
    client.table.return_value.upsert.return_value.execute.return_value = upsert_result

    # kg_findings insert chain
    insert_result = MagicMock()
    insert_result.data = [{"id": "finding-uuid-1"}]
    client.table.return_value.insert.return_value.execute.return_value = insert_result

    return client


@patch("app.agents.research.tools.graph_writer._get_supabase")
def test_write_findings_to_graph_creates_entities(mock_get_sb):
    """Upsert creates entity, inserts findings, returns success."""
    entity_id = "ent-uuid-abc"
    client = _mock_client_with_entity_id(entity_id)
    mock_get_sb.return_value = client

    synthesis = _make_synthesis(findings_count=3)

    result = write_to_graph(synthesis, domain="financial", user_id="user-1")

    assert result["success"] is True
    assert result["entities_written"] == 1
    assert result["findings_written"] == 3
    assert result["entity_id"] == entity_id

    # Verify upsert was called on kg_entities
    client.table.assert_any_call("kg_entities")
    client.table.return_value.upsert.assert_called_once()
    upsert_kwargs = client.table.return_value.upsert.call_args
    assert upsert_kwargs[1]["on_conflict"] == "canonical_name,entity_type"

    # Verify insert was called for each finding
    assert client.table.return_value.insert.call_count == 3


@patch("app.agents.research.tools.graph_writer._get_supabase")
def test_write_findings_handles_db_error(mock_get_sb):
    """DB exception returns success=False without raising."""
    mock_get_sb.side_effect = RuntimeError("Connection refused")

    synthesis = _make_synthesis()

    result = write_to_graph(synthesis, domain="marketing")

    assert result["success"] is False
    assert result["entities_written"] == 0
    assert result["findings_written"] == 0
    assert result["entity_id"] is None
    assert "Connection refused" in result["error"]
