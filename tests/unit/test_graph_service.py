"""Tests for GraphService knowledge graph read operations."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.services.graph_service import GraphService


def _make_entity(entity_id: str = "ent-1", name: str = "Acme Corp") -> dict:
    """Helper to build a mock entity dict."""
    return {
        "id": entity_id,
        "canonical_name": name,
        "entity_type": "company",
        "created_at": "2025-01-01T00:00:00Z",
    }


def _make_findings() -> list[dict]:
    return [
        {
            "id": "f-1",
            "finding_text": "Revenue grew 20%",
            "confidence": 0.95,
            "sources": ["10-K"],
            "contradicts": None,
            "freshness_at": "2025-06-01T00:00:00Z",
        },
    ]


def _make_relationships() -> list[dict]:
    return [
        {
            "id": "e-1",
            "relationship": "acquires",
            "target_id": "ent-2",
            "confidence": 0.9,
            "evidence": "press release",
            "source_url": "https://example.com",
            "target_name": "Beta Inc",
        },
    ]


class TestQueryEntityByName:
    """Entity found via canonical_name returns full context."""

    def test_query_entity_by_name_returns_entity(self):
        svc = GraphService(supabase_client=MagicMock())
        entity = _make_entity()

        with (
            patch.object(svc, "_query_by_name", return_value=entity),
            patch.object(svc, "_get_findings", return_value=_make_findings()),
            patch.object(svc, "_get_relationships", return_value=_make_relationships()),
        ):
            result = svc.query_entity("Acme Corp", domain="financial")

        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Acme Corp"
        assert len(result["findings"]) == 1
        assert len(result["relationships"]) == 1
        assert result["domain"] == "financial"


class TestQueryEntityNotFound:
    """Neither name nor alias match returns found=False."""

    def test_query_entity_not_found_returns_empty(self):
        svc = GraphService(supabase_client=MagicMock())

        with (
            patch.object(svc, "_query_by_name", return_value=None),
            patch.object(svc, "_query_by_alias", return_value=None),
        ):
            result = svc.query_entity("Nonexistent", domain="marketing")

        assert result["found"] is False
        assert result["entity"] is None
        assert result["findings"] == []
        assert result["relationships"] == []


class TestQueryEntityViaAlias:
    """Name miss, alias hit should still resolve the entity."""

    def test_query_entity_checks_aliases(self):
        svc = GraphService(supabase_client=MagicMock())
        entity = _make_entity()

        with (
            patch.object(svc, "_query_by_name", return_value=None),
            patch.object(svc, "_query_by_alias", return_value=entity),
            patch.object(svc, "_get_findings", return_value=[]),
            patch.object(svc, "_get_relationships", return_value=[]),
        ):
            result = svc.query_entity("ACME", domain="sales")

        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Acme Corp"


class TestFreshnessCheck:
    """is_stale static method validates timestamp age."""

    def test_check_freshness_returns_stale(self):
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=10)).isoformat()
        assert GraphService.is_stale(old_ts, threshold_hours=4) is True

    def test_check_freshness_returns_fresh(self):
        recent_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        assert GraphService.is_stale(recent_ts, threshold_hours=4) is False

    def test_empty_freshness_is_stale(self):
        assert GraphService.is_stale("", threshold_hours=4) is True

    def test_none_freshness_is_stale(self):
        assert GraphService.is_stale(None, threshold_hours=4) is True


class TestQueryEntityError:
    """Database errors produce graceful empty result with error key."""

    def test_query_entity_error_returns_graceful_empty(self):
        bad_client = MagicMock()
        bad_client.table.side_effect = RuntimeError("connection refused")

        svc = GraphService(supabase_client=bad_client)
        result = svc.query_entity("Boom", domain="compliance")

        assert result["found"] is False
        assert "error" in result
        assert "connection refused" in result["error"]
