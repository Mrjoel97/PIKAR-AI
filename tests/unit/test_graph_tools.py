"""Tests for the graph_read ADK tool."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.tools.graph_tools import GRAPH_TOOLS, graph_read


@pytest.fixture()
def _found_result():
    """Graph result with a known entity and findings."""
    return {
        "found": True,
        "entity": {
            "id": "ent-001",
            "canonical_name": "Acme Corp",
            "entity_type": "company",
        },
        "findings": [
            {
                "id": "f-1",
                "finding_text": "Revenue grew 15% YoY",
                "confidence": 0.92,
                "sources": ["10-K filing"],
                "contradicts": None,
                "freshness_at": "2099-01-01T00:00:00+00:00",
            },
        ],
        "relationships": [
            {
                "id": "e-1",
                "relationship": "competes_with",
                "target_id": "ent-002",
                "target_name": "Beta Inc",
                "confidence": 0.85,
                "evidence": "Market analysis",
                "source_url": None,
            },
        ],
        "query": "Acme Corp",
        "domain": "financial",
    }


@pytest.fixture()
def _not_found_result():
    """Graph result for an unknown entity."""
    return {
        "found": False,
        "entity": None,
        "findings": [],
        "relationships": [],
        "query": "Unknown Entity",
        "domain": "marketing",
    }


class TestGraphRead:
    """Tests for the graph_read tool function."""

    @patch("app.agents.tools.graph_tools._get_cached_or_query")
    def test_graph_read_returns_findings_for_known_entity(
        self, mock_query, _found_result
    ):
        """Known entities return success=True, found=True, with findings."""
        mock_query.return_value = _found_result

        result = graph_read(query="Acme Corp", domain="financial")

        assert result["success"] is True
        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Acme Corp"
        assert len(result["findings"]) == 1
        assert result["findings"][0]["finding_text"] == "Revenue grew 15% YoY"
        assert len(result["relationships"]) == 1
        mock_query.assert_called_once_with("Acme Corp", "financial", None)

    @patch("app.agents.tools.graph_tools._get_cached_or_query")
    def test_graph_read_returns_not_found(self, mock_query, _not_found_result):
        """Unknown entities return success=True, found=False."""
        mock_query.return_value = _not_found_result

        result = graph_read(query="Unknown Entity", domain="marketing")

        assert result["success"] is True
        assert result["found"] is False
        assert result["entity"] is None
        assert result["findings"] == []
        assert result["relationships"] == []

    @patch("app.agents.tools.graph_tools._get_cached_or_query")
    def test_graph_read_handles_errors_gracefully(self, mock_query):
        """Exceptions are caught and returned as success=False with error."""
        mock_query.side_effect = Exception("database connection lost")

        result = graph_read(query="Acme Corp", domain="financial")

        assert result["success"] is False
        assert "error" in result
        assert "database connection lost" in result["error"]
        assert result["found"] is False

    def test_graph_tools_exports_list(self):
        """GRAPH_TOOLS is a list containing the graph_read function."""
        assert isinstance(GRAPH_TOOLS, list)
        assert len(GRAPH_TOOLS) == 1
        assert GRAPH_TOOLS[0].__name__ == "graph_read"

    @patch("app.agents.tools.graph_tools._get_cached_or_query")
    def test_graph_read_adds_staleness_warning(self, mock_query, _found_result):
        """Stale findings trigger a staleness_warning in the response."""
        # Make the finding stale by setting freshness_at far in the past
        _found_result["findings"][0]["freshness_at"] = "2020-01-01T00:00:00+00:00"
        mock_query.return_value = _found_result

        result = graph_read(query="Acme Corp", domain="financial")

        assert result["success"] is True
        assert result["found"] is True
        assert "staleness_warning" in result
        assert "1/1 findings exceed" in result["staleness_warning"]

    @patch("app.agents.tools.graph_tools._get_cached_or_query")
    def test_graph_read_no_staleness_warning_when_fresh(
        self, mock_query, _found_result
    ):
        """Fresh findings do not produce a staleness_warning."""
        # freshness_at is 2099 in the fixture — well within threshold
        mock_query.return_value = _found_result

        result = graph_read(query="Acme Corp", domain="financial")

        assert result["success"] is True
        assert "staleness_warning" not in result
