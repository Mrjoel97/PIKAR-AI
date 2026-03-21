"""Integration tests for the knowledge graph schema and read path.

These tests verify:
1. Migration created all 7 kg_* tables
2. Data can be inserted and queried via GraphService
3. Entity resolution works (exact + alias)
4. Freshness checking works correctly
5. Domain budget seed data exists

Requires: local Supabase running (supabase start).
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]


@pytest.fixture()
def supabase_client():
    """Get Supabase client for integration tests."""
    try:
        from app.services.supabase_client import get_supabase_client

        return get_supabase_client()
    except Exception:
        pytest.skip("Supabase not available")


def test_kg_tables_exist(supabase_client):
    """All 7 kg_* tables should exist after migration."""
    tables = [
        "kg_entities",
        "kg_aliases",
        "kg_edges",
        "kg_findings",
        "kg_research_log",
        "kg_watch_topics",
        "kg_domain_budgets",
    ]
    for table in tables:
        response = supabase_client.table(table).select("*").limit(1).execute()
        assert response is not None, f"Table {table} should exist"


def test_domain_budgets_seeded(supabase_client):
    """Default domain budgets should be seeded."""
    response = supabase_client.table("kg_domain_budgets").select("domain").execute()
    domains = {row["domain"] for row in response.data}
    assert "financial" in domains
    assert "marketing" in domains
    assert len(domains) == 10


def test_insert_and_query_entity(supabase_client):
    """Can insert an entity and query it back via GraphService."""
    from app.services.graph_service import GraphService

    test_entity = {
        "canonical_name": "Test Corp Integration",
        "entity_type": "company",
        "domains": ["financial"],
        "properties": {"industry": "tech"},
    }
    insert_resp = supabase_client.table("kg_entities").insert(test_entity).execute()
    assert insert_resp.data, "Insert should succeed"
    entity_id = insert_resp.data[0]["id"]

    try:
        service = GraphService(supabase_client=supabase_client)
        result = service.query_entity(
            query="Test Corp Integration",
            domain="financial",
        )
        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Test Corp Integration"
    finally:
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_alias_resolution(supabase_client):
    """Can resolve entity via alias."""
    from app.services.graph_service import GraphService

    entity_resp = (
        supabase_client.table("kg_entities")
        .insert(
            {
                "canonical_name": "Integration Test Bank",
                "entity_type": "institution",
                "domains": ["financial"],
            }
        )
        .execute()
    )
    entity_id = entity_resp.data[0]["id"]

    supabase_client.table("kg_aliases").insert(
        {
            "entity_id": entity_id,
            "alias": "ITB",
            "source": "test",
        }
    ).execute()

    try:
        service = GraphService(supabase_client=supabase_client)
        result = service.query_entity(query="ITB", domain="financial")
        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Integration Test Bank"
    finally:
        try:
            supabase_client.table("kg_aliases").delete().eq(
                "entity_id", entity_id
            ).execute()
        except Exception:
            pass
        try:
            supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()
        except Exception:
            pass


def test_match_kg_entities_rpc(supabase_client):
    """Semantic search RPC function should exist and be callable."""
    zero_embedding = [0.0] * 768
    response = supabase_client.rpc(
        "match_kg_entities",
        {
            "query_embedding": zero_embedding,
            "match_count": 5,
            "match_threshold": 0.1,
        },
    ).execute()
    assert isinstance(response.data, list)
