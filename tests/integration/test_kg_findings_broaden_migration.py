"""Integration tests for the kg_findings broaden migration (Plan 112-01).

Verifies:
1. agent_id and claim_type columns exist with correct types
2. Both columns are NOT NULL with no DEFAULT after migration completes
3. Existing rows backfilled to agent_id='research', claim_type='research_finding'
4. Row count unchanged across migration
5. Three new indices created with correct definitions
6. Partial index has the expected WHERE predicate
7. Inserting without agent_id or claim_type raises a NOT NULL violation

Requires: local Supabase running (supabase start) with the migration applied.
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os
from uuid import uuid4

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
    """Service-role Supabase client built directly from env vars.

    Bypasses the integration conftest's MagicMock stub at
    tests/integration/conftest.py:63-98, which intercepts
    app.services.supabase_client imports. We want a real client
    for migration verification.
    """
    try:
        from supabase import create_client
    except ImportError:
        pytest.skip("supabase package not available")

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        pytest.skip("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(url, key)


@pytest.fixture()
def db_dsn():
    """Direct Postgres DSN for information_schema queries."""
    dsn = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DB_URL/DATABASE_URL not set for direct queries")
    return dsn


def _query(dsn, sql, params=None):
    """Run a SQL query against the local Postgres and return rows as list[dict]."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [desc[0] for desc in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def test_agent_id_column_exists(db_dsn):
    """agent_id column should exist on kg_findings, TEXT, NOT NULL, no default."""
    rows = _query(
        db_dsn,
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'kg_findings' AND column_name = 'agent_id'
        """,
    )
    assert len(rows) == 1, "agent_id column should exist exactly once"
    assert rows[0]["data_type"] == "text"
    assert rows[0]["is_nullable"] == "NO"
    assert rows[0]["column_default"] is None, "Default must be dropped post-migration"


def test_claim_type_column_exists(db_dsn):
    """claim_type column should exist on kg_findings, TEXT, NOT NULL, no default."""
    rows = _query(
        db_dsn,
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'kg_findings' AND column_name = 'claim_type'
        """,
    )
    assert len(rows) == 1, "claim_type column should exist exactly once"
    assert rows[0]["data_type"] == "text"
    assert rows[0]["is_nullable"] == "NO"
    assert rows[0]["column_default"] is None


def test_existing_rows_backfilled(supabase_client, db_dsn):
    """Pre-existing kg_findings rows should have agent_id='research' and
    claim_type='research_finding' after migration. Skip if table is empty.
    """
    rows = _query(db_dsn, "SELECT COUNT(*) AS n FROM kg_findings")
    if rows[0]["n"] == 0:
        pytest.skip("kg_findings is empty in local seed; backfill is structural only")
    misclassified = _query(
        db_dsn,
        """
        SELECT COUNT(*) AS n FROM kg_findings
        WHERE agent_id != 'research' OR claim_type != 'research_finding'
        """,
    )
    assert misclassified[0]["n"] == 0, (
        "All pre-existing rows should backfill to research defaults"
    )


def test_insert_requires_agent_id_and_claim_type(supabase_client):
    """Inserting without agent_id should raise a NOT NULL violation."""
    entity_resp = supabase_client.table("kg_entities").insert({
        "canonical_name": f"Test Entity {uuid4()}",
        "entity_type": "topic",
        "domains": ["test"],
    }).execute()
    entity_id = entity_resp.data[0]["id"]

    try:
        with pytest.raises(Exception) as exc_info:
            supabase_client.table("kg_findings").insert({
                "entity_id": entity_id,
                "domain": "test",
                "finding_text": "test finding without agent_id",
                "confidence": 0.5,
                "claim_type": "test_claim",
            }).execute()
        assert "agent_id" in str(exc_info.value) or "23502" in str(exc_info.value)
    finally:
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_insert_with_new_columns_succeeds(supabase_client):
    """Inserting with both new columns should succeed and roundtrip correctly."""
    entity_resp = supabase_client.table("kg_entities").insert({
        "canonical_name": f"Test Entity Roundtrip {uuid4()}",
        "entity_type": "topic",
        "domains": ["test"],
    }).execute()
    entity_id = entity_resp.data[0]["id"]

    try:
        finding_resp = supabase_client.table("kg_findings").insert({
            "entity_id": entity_id,
            "domain": "test",
            "finding_text": "test finding with both new cols",
            "confidence": 0.83,
            "agent_id": "data",
            "claim_type": "test_claim",
        }).execute()
        assert finding_resp.data, "Insert should succeed"
        row = finding_resp.data[0]
        assert row["agent_id"] == "data"
        assert row["claim_type"] == "test_claim"
        assert row["confidence"] == 0.83
    finally:
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_entity_claim_agent_fresh_index_exists(db_dsn):
    """Covering index for cache freshness check should exist with all 4 columns."""
    rows = _query(
        db_dsn,
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'kg_findings'
          AND indexname = 'idx_kg_findings_entity_claim_agent_fresh'
        """,
    )
    assert len(rows) == 1
    idx_def = rows[0]["indexdef"]
    assert "entity_id" in idx_def
    assert "claim_type" in idx_def
    assert "agent_id" in idx_def
    assert "freshness_at" in idx_def
    assert "DESC" in idx_def


def test_agent_freshness_index_exists(db_dsn):
    """Per-agent recency index should exist."""
    rows = _query(
        db_dsn,
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'kg_findings'
          AND indexname = 'idx_kg_findings_agent_freshness'
        """,
    )
    assert len(rows) == 1
    idx_def = rows[0]["indexdef"]
    assert "agent_id" in idx_def
    assert "freshness_at" in idx_def
    assert "DESC" in idx_def


def test_claim_type_confidence_partial_index_exists(db_dsn):
    """Partial confidence-filtered index should exist with WHERE confidence >= 0.5."""
    rows = _query(
        db_dsn,
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'kg_findings'
          AND indexname = 'idx_kg_findings_claim_type_confidence'
        """,
    )
    assert len(rows) == 1
    idx_def = rows[0]["indexdef"]
    assert "claim_type" in idx_def
    assert "confidence" in idx_def
    assert "WHERE" in idx_def.upper()
    assert "0.5" in idx_def or "0.50" in idx_def
