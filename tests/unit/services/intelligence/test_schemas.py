"""Unit tests for app.services.intelligence.schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.services.intelligence.schemas import Claim, ClaimPayload, ClaimSource


def _make_claim(confidence: float = 0.83) -> Claim:
    """Helper: build a minimal valid Claim with the given confidence."""
    return Claim(
        id=uuid4(),
        entity_id=uuid4(),
        edge_id=None,
        agent_id="data",
        claim_type="cohort_retention",
        domain="data",
        finding_text="Q1 retention = 62.4%",
        confidence=confidence,
        sources=[ClaimSource(kind="stripe_row", ref="charges:2026-q1")],
        contradicts=[],
        freshness_at=datetime.now(timezone.utc),
        expires_at=None,
        created_at=datetime.now(timezone.utc),
    )


def test_claim_band_low():
    """band is 'low' when confidence < 0.50."""
    assert _make_claim(confidence=0.49).band == "low"
    assert _make_claim(confidence=0.0).band == "low"


def test_claim_band_medium():
    """band is 'medium' for [0.50, 0.75)."""
    assert _make_claim(confidence=0.50).band == "medium"
    assert _make_claim(confidence=0.74).band == "medium"


def test_claim_band_high():
    """band is 'high' for [0.75, 1.0]."""
    assert _make_claim(confidence=0.75).band == "high"
    assert _make_claim(confidence=1.0).band == "high"


def test_claim_confidence_out_of_range_rejected():
    """confidence < 0 or > 1 should fail validation."""
    with pytest.raises(ValidationError):
        _make_claim(confidence=-0.1)
    with pytest.raises(ValidationError):
        _make_claim(confidence=1.5)


def test_claim_source_score_optional():
    """ClaimSource.score defaults to None."""
    src = ClaimSource(kind="url", ref="https://example.com")
    assert src.score is None


def test_claim_source_kind_validation():
    """ClaimSource.kind must be one of the documented Literals."""
    with pytest.raises(ValidationError):
        ClaimSource(kind="invalid_kind", ref="x")  # type: ignore[arg-type]


def test_claim_payload_defaults():
    """ClaimPayload sensible defaults: embed=False, contradicts=[], expires_at=None."""
    payload = ClaimPayload(
        entity_id=uuid4(),
        domain="research",
        finding_text="x",
        confidence=0.5,
        sources=[],
        agent_id="research",
        claim_type="research_finding",
    )
    assert payload.embed is False
    assert payload.contradicts == []
    assert payload.expires_at is None
    assert payload.edge_id is None


def test_claim_payload_requires_either_entity_or_edge():
    """At app level, ClaimPayload doesn't enforce entity/edge — the DB CHECK does.

    This test confirms ClaimPayload accepts both being None (we rely on the
    DB CHECK constraint to reject at write time). This is intentional: the
    DB is the source of truth on this invariant.
    """
    payload = ClaimPayload(
        entity_id=None,
        edge_id=None,
        domain="x",
        finding_text="y",
        confidence=0.5,
        sources=[],
        agent_id="research",
        claim_type="research_finding",
    )
    assert payload.entity_id is None
    assert payload.edge_id is None
