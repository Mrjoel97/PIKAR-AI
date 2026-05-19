"""Integration tests for app.services.intelligence.claims.

Requires local Supabase running and Plan 112-01 migration applied.
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]


@pytest.fixture()
def supabase_client():
    """Real Supabase client built from env vars, bypassing conftest mocks.

    Same pattern as tests/integration/test_kg_findings_broaden_migration.py
    (Plan 112-01) — the integration conftest stubs app.services.supabase_client
    with MagicMock at import time, which we don't want for real DB testing.
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
def cleanup_entities():
    """Track entity IDs created during tests and delete them after.

    Yields a list — tests append IDs to it.
    """
    created: list[UUID] = []
    yield created
    # Best-effort cleanup; ignore failures
    if created:
        try:
            from supabase import create_client

            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            client = create_client(url, key)  # type: ignore[arg-type]
            for entity_id in created:
                try:
                    client.table("kg_entities").delete().eq("id", str(entity_id)).execute()
                except Exception:
                    pass
        except Exception:
            pass


# ---------------------------------------------------------------------------
# get_or_create_entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_entity_creates_new(supabase_client, cleanup_entities):
    """First call with a new canonical_name+entity_type creates a row."""
    from app.services.intelligence.claims import get_or_create_entity

    name = f"Test Topic {uuid4()}"
    entity_id = await get_or_create_entity(
        canonical_name=name,
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    assert isinstance(entity_id, UUID)
    # Verify it persists
    rows = supabase_client.table("kg_entities").select("*").eq("id", str(entity_id)).execute()
    assert len(rows.data) == 1
    assert rows.data[0]["canonical_name"] == name
    assert rows.data[0]["entity_type"] == "topic"


@pytest.mark.asyncio
async def test_get_or_create_entity_idempotent(supabase_client, cleanup_entities):
    """Repeated call with same (canonical_name, entity_type) returns same UUID."""
    from app.services.intelligence.claims import get_or_create_entity

    name = f"Idempotent Test {uuid4()}"
    first = await get_or_create_entity(
        canonical_name=name,
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(first)
    second = await get_or_create_entity(
        canonical_name=name,
        entity_type="topic",
        domains=["test"],
    )

    assert first == second, "Idempotent upsert should return same UUID"


@pytest.mark.asyncio
async def test_get_or_create_entity_different_types_distinct(
    supabase_client,
    cleanup_entities,
):
    """Same canonical_name with different entity_type produces distinct rows."""
    from app.services.intelligence.claims import get_or_create_entity

    name = f"Acme Corp {uuid4()}"
    as_company = await get_or_create_entity(
        canonical_name=name,
        entity_type="company",
        domains=["test"],
    )
    as_topic = await get_or_create_entity(
        canonical_name=name,
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.extend([as_company, as_topic])

    assert as_company != as_topic


# ---------------------------------------------------------------------------
# write_claim
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_claim_single(supabase_client, cleanup_entities):
    """Single claim insert returns the new claim's UUID."""
    from app.services.intelligence.claims import get_or_create_entity, write_claim

    entity_id = await get_or_create_entity(
        canonical_name=f"WC Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    claim_id = await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="test claim from write_claim integration test",
        confidence=0.83,
        sources=[{"kind": "stripe_row", "ref": "test:abc"}],
        agent_id="data",
        claim_type="cohort_retention",
    )

    assert isinstance(claim_id, UUID)
    # Verify persistence
    row = supabase_client.table("kg_findings").select("*").eq("id", str(claim_id)).execute()
    assert len(row.data) == 1
    assert row.data[0]["agent_id"] == "data"
    assert row.data[0]["claim_type"] == "cohort_retention"
    assert row.data[0]["confidence"] == 0.83


@pytest.mark.asyncio
async def test_write_claim_without_entity_or_edge_raises(supabase_client):
    """DB CHECK constraint should reject claims with neither entity_id nor edge_id."""
    from app.services.intelligence.claims import write_claim

    with pytest.raises(Exception):  # PostgREST/PostgreSQL constraint violation
        await write_claim(
            entity_id=None,
            edge_id=None,
            domain="test",
            finding_text="orphan claim",
            confidence=0.5,
            sources=[],
            agent_id="test",
            claim_type="orphan",
        )


@pytest.mark.asyncio
async def test_write_claim_skips_embedding_by_default(supabase_client, cleanup_entities):
    """embed=False (default) should NOT generate or store an embedding."""
    from app.services.intelligence.claims import get_or_create_entity, write_claim

    entity_id = await get_or_create_entity(
        canonical_name=f"NoEmbed Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    claim_id = await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="no embed",
        confidence=0.5,
        sources=[],
        agent_id="test",
        claim_type="probe",
    )
    row = supabase_client.table("kg_findings").select("embedding").eq(
        "id", str(claim_id)
    ).execute()
    # NULL embedding (PostgREST returns None for NULL pgvector)
    assert row.data[0]["embedding"] is None


# ---------------------------------------------------------------------------
# write_claims (bulk)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_claims_bulk(supabase_client, cleanup_entities):
    """Bulk insert returns UUIDs in input order and persists all rows."""
    from app.services.intelligence.claims import get_or_create_entity, write_claims
    from app.services.intelligence.schemas import ClaimPayload, ClaimSource

    entity_id = await get_or_create_entity(
        canonical_name=f"Bulk Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    payloads = [
        ClaimPayload(
            entity_id=entity_id,
            domain="test",
            finding_text=f"bulk claim {i}",
            confidence=0.5 + i * 0.1,
            sources=[ClaimSource(kind="other", ref=f"bulk:{i}")],
            agent_id="data",
            claim_type="probe",
        )
        for i in range(3)
    ]

    ids = await write_claims(payloads)
    assert len(ids) == 3
    assert all(isinstance(i, UUID) for i in ids)

    rows = supabase_client.table("kg_findings").select("finding_text").in_(
        "id", [str(i) for i in ids]
    ).execute()
    assert len(rows.data) == 3
    texts = {r["finding_text"] for r in rows.data}
    assert texts == {f"bulk claim {i}" for i in range(3)}


@pytest.mark.asyncio
async def test_write_claims_empty_list_returns_empty(supabase_client):
    """Empty input returns empty list — no DB call."""
    from app.services.intelligence.claims import write_claims

    ids = await write_claims([])
    assert ids == []


# ---------------------------------------------------------------------------
# find_claims and claim_freshness_hours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_claims_by_entity(supabase_client, cleanup_entities):
    """find_claims with entity_id filter returns matching claims."""
    from app.services.intelligence.claims import (
        find_claims,
        get_or_create_entity,
        write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Find Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="findable claim",
        confidence=0.9,
        sources=[{"kind": "other", "ref": "x"}],
        agent_id="research",
        claim_type="research_finding",
    )

    results = await find_claims(entity_id=entity_id, limit=10)
    assert len(results) >= 1
    assert any(c.finding_text == "findable claim" for c in results)
    # band is computed
    matched = next(c for c in results if c.finding_text == "findable claim")
    assert matched.band == "high"  # 0.9 >= 0.75


@pytest.mark.asyncio
async def test_find_claims_min_confidence_filter(supabase_client, cleanup_entities):
    """min_confidence filters out low-confidence claims."""
    from app.services.intelligence.claims import (
        find_claims,
        get_or_create_entity,
        write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Conf Filter {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="low conf",
        confidence=0.30,
        sources=[],
        agent_id="test",
        claim_type="probe",
    )
    await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="high conf",
        confidence=0.85,
        sources=[],
        agent_id="test",
        claim_type="probe",
    )

    high = await find_claims(entity_id=entity_id, min_confidence=0.75)
    assert all(c.confidence >= 0.75 for c in high)
    assert any(c.finding_text == "high conf" for c in high)
    assert not any(c.finding_text == "low conf" for c in high)


@pytest.mark.asyncio
async def test_claim_freshness_hours_returns_age(supabase_client, cleanup_entities):
    """claim_freshness_hours returns age of latest matching claim in hours."""
    from app.services.intelligence.claims import (
        claim_freshness_hours,
        get_or_create_entity,
        write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Fresh Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="recent claim",
        confidence=0.5,
        sources=[],
        agent_id="data",
        claim_type="cohort_retention",
    )

    age = await claim_freshness_hours(
        entity_id=entity_id,
        claim_type="cohort_retention",
        agent_id="data",
    )
    assert age is not None
    assert 0.0 <= age <= 1.0  # we just inserted, should be under an hour old


@pytest.mark.asyncio
async def test_claim_freshness_hours_no_match_returns_none(
    supabase_client,
    cleanup_entities,
):
    """claim_freshness_hours returns None when no matching claim exists."""
    from app.services.intelligence.claims import claim_freshness_hours

    nonexistent = uuid4()
    age = await claim_freshness_hours(
        entity_id=nonexistent,
        claim_type="cohort_retention",
        agent_id="data",
    )
    assert age is None
