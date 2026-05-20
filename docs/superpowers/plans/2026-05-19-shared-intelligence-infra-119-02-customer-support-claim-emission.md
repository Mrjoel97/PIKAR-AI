# Shared Intelligence Infrastructure — Plan 119-02: Customer Support Claim Emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Customer Support Agent to emit `ticket_sentiment`, `csat_signal`, and `churn_risk_indicator` claims into `kg_findings` via the shared intelligence package. Every CS output carries `confidence` + `band`. `churn_risk_indicator` claims always carry `expires_at = now + 7d`. A nightly-aware test fixture verifies expired churn-risk claims are filtered out of `find_claims` results. Cross-agent `search_claims_semantic` returns CS claims alongside Data/Research claims.

**Architecture:** Customer Support has NO external API surface (it consults internal `SupportTicketService` + `CustomerHealthService`), so there is no external cache plan in Phase 119. Plan 119-02 introduces `app/agents/customer_support/intelligence.py` — a thin claim-builder + emit module that the existing tool functions in `app/agents/customer_support/tools.py` call after computing their results. Builders return `ClaimPayload`; callers either persist immediately via `write_claim` or accumulate for `write_claims`. The `churn_risk_indicator` TTL is enforced at *build time* in `build_churn_risk_payload` — every emission path goes through one helper, so TTL drift is impossible.

**TTL refresh mechanism (resolves ambiguity for `churn_risk_indicator`):** *Set-and-forget at write time.* The 7-day `expires_at` is stamped by `build_churn_risk_payload` on every emit. `find_claims` is extended (or its callers wrapped) to filter rows where `expires_at IS NULL OR expires_at > now()`. Refresh is implicit: whenever the Customer Support Agent recomputes a customer's churn risk and emits a new claim, the new claim has a fresh 7-day window. A weekly cron job is OUT of scope for this plan; the "weekly refresh" cadence is achieved by the agent's normal recompute pattern, not by a scheduled job. If a customer is never recomputed for >7 days, their churn-risk claim *correctly* falls out of the result set — that's by design, not a bug. (See "Open question for follow-up" at the bottom.)

**Tech Stack:** `app/services/intelligence/{claims,schemas}` (Phase 112), `app/services/intelligence/presets/customer_support` (Plan 119-01), `app/agents/customer_support/tools.py` (existing tool callables), `kg_findings` table, Phase 113 cross-cutting infra (`search_claims_semantic`, `detect_contradictions` auto-populate path).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 119 — Customer Support Agent adoption · plan 119-02 "Claim emission. churn_risk_indicator TTL = 7d (must be refreshed weekly via `expires_at` on write)."

**Out of scope:**
- External-API caching (no external surface — see Plan 119-01 design rationale)
- LLM-driven sentiment re-classification (we reuse the existing `ticket.sentiment` column populated by `SupportTicketService`)
- A dedicated weekly cron job that re-emits churn-risk claims (see "Open question for follow-up" — deferred; spec did not bind a cron)
- Editing the `_SCENARIO_TEMPLATES` response templates in `tools.py` — preserved verbatim
- Frontend wiring of `confidence` + `band` into dashboard UI (separate UX phase; `/admin/research/overview` auto-extends per spec § Observability)
- Persona-aware confidence variants (single CS preset for all personas; spec defers)
- ADK tool wrapper for `record_claim` (Decision #10 from Phase 112 — library-first; LLM does not directly emit claims)

---

## File structure

**Create:**
- `app/agents/customer_support/intelligence.py` — builders + emit helpers + claim-type constants
- `tests/unit/agents/customer_support/test_intelligence.py` — unit tests with mocked Supabase
- `tests/integration/agents/customer_support/test_intelligence_claims.py` — integration round-trip via `write_claim` → `find_claims`
- `tests/integration/agents/customer_support/test_churn_risk_ttl_expiry.py` — TTL-expiry verification (the "nightly job test fixture" from the spec)

**Modify:**
- `app/agents/customer_support/tools.py` — wire claim emission into `get_customer_health_dashboard`, `create_ticket`, `update_ticket`, and a new churn-risk emit path
- `app/services/intelligence/claims.py` — extend `find_claims` to filter expired claims by default (new `include_expired: bool = False` kwarg)
- `tests/unit/services/intelligence/test_claims.py` — add tests for the new filter behaviour

**Read (no edits):**
- `app/agents/customer_support/intelligence.py` (after Task 1 lands)
- `app/services/intelligence/presets/customer_support.py` (from Plan 119-01)

---

## Pre-flight context

### The `kg_findings.expires_at` filter

Phase 112's `kg_findings` table has an `expires_at TIMESTAMPTZ NULL` column. Today, `find_claims` does NOT filter on it (verified by reading the reference at `.planning/refs-114-122/intelligence-claims.py:255–343`). That's a Phase 112 oversight that becomes load-bearing here: without the filter, expired `churn_risk_indicator` claims would still surface in `find_claims(claim_type='churn_risk_indicator', ...)` calls, defeating the whole point of TTL.

The fix is additive — new kwarg `include_expired: bool = False` (default behaviour changes: expired claims now hidden by default). This is a deliberate breaking semantic change to `find_claims` for callers that depended on the bug, but per the spec acceptance criteria ("A nightly job ... verifies expired churn_risk claims are no longer returned by `find_claims`"), default-hide is the contract we must ship. Existing call-sites that need historical behaviour pass `include_expired=True` explicitly.

### Why no weekly cron

The spec says `churn_risk_indicator` TTL is "7d (must be refreshed weekly via `expires_at` on write)." Read literally: the *refresh mechanism* IS the `expires_at` written on each emit. As long as the agent recomputes churn risk at least once a week per customer (typical when any new ticket is filed for that customer), the claim refreshes. No cron required.

This plan documents that interpretation explicitly and ships a test (`test_churn_risk_ttl_expiry.py`) that verifies the *expiry behaviour* (claims older than 7 days fall out of `find_claims`). Whether to *guarantee* refresh via a cron is a follow-up question called out at the bottom of this plan, not blocking 119-02.

### Customer entity convention

`ticket_sentiment`, `csat_signal`, and `churn_risk_indicator` all attach to a customer entity in `kg_entities`. The entity convention:

- `canonical_name = customer_email.lower().strip()`
- `entity_type = "person"`
- `domains = ["customer_support"]`
- `properties = {"first_seen_via": "support_ticket"}` (optional metadata; only set on first create)

`get_or_create_entity` is idempotent on `(canonical_name, entity_type)` — repeated calls return the same UUID, so multiple emits for the same customer naturally cluster.

### Confidence wiring per claim_type

| claim_type | Preset call | Source of `data_age_hours` |
|---|---|---|
| `ticket_sentiment` | `customer_support_confidence(ticket_count=1, customer_response_engagement=0.5, resolution_outcome_clarity=resolved?1.0:0.0, data_age_hours=ticket_age_h)` | `now - ticket.updated_at` |
| `csat_signal` | `customer_support_confidence(ticket_count=tickets_in_period, customer_response_engagement=measured_engagement, resolution_outcome_clarity=resolved_in_period/total_in_period, data_age_hours=period_end_age_h)` | `now - period_end` |
| `churn_risk_indicator` | `customer_support_confidence(ticket_count=open_tickets+resolved_recent, customer_response_engagement=0.5, resolution_outcome_clarity=resolution_rate/100, data_age_hours=newest_ticket_age_h)` | `now - newest_ticket.created_at` |

`customer_response_engagement=0.5` is the documented neutral prior in Plan 119-01 — callers without a real measurement pass 0.5 rather than fabricate a value. Adding a real `customer_response_engagement` computation is a follow-up.

### Acceptance bar (from spec § Phase 119 + 119-02 brief)

- Customer Support Agent test suite green (existing tests not regressed)
- All CS outputs carry `confidence` + `band` (no hardcoded constants in returned payloads)
- `churn_risk_indicator` claims always carry `expires_at ≤ now + 7d` (build-time invariant + emission tests)
- A test fixture verifies expired churn-risk claims are no longer returned by `find_claims`
- `search_claims_semantic(query="customer churn", top_k=10)` returns CS claims interleaved with Data/Research claims (cross-agent integration)
- TDD enforced; 2–5 minute steps; pytest expected outputs; `git add` + `git commit -m "feat(119-02): ..."` per task

### Environment quirks

- `uv run pytest` only under PowerShell (per `reference_local_dev_env_quirks.md`).
- Integration tests need local Supabase: start with `supabase start`; export `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL` as shown in Plan 113-05 Task 3 Step 3.
- `frontend/.env` defaults to prod — irrelevant here.
- The `MagicMock` Supabase shim at `tests/integration/conftest.py:63-98` will silently swallow inserts; integration tests MUST build the Supabase client via `supabase.create_client(url, key)` (the canonical bypass — see `reference_integration_supabase_client_bypass.md`).

---

## Tasks

### Task 1: Pre-flight + scaffold `intelligence.py` with builders only (no emission yet)

**Files:**
- Create: `app/agents/customer_support/intelligence.py`
- Create: `tests/unit/agents/customer_support/test_intelligence.py`

This task makes Plan 119-01's xfail-skipped schema tests start passing — the contract is satisfied before any emission code lands.

- [ ] **Step 1: Confirm Plan 119-01 prerequisites**

```powershell
uv run python -c "from app.services.intelligence.presets import customer_support_confidence; print(customer_support_confidence(20, 1.0, 1.0, 0.0))"
```

Expected: `1.0`. If anything other than `1.0`, Plan 119-01 didn't land cleanly — stop and escalate.

Verify the xfailed contract tests from 119-01 are currently xfail-skipping (i.e., the symbols don't exist yet):

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_customer_support_schema.py -v 2>&1 | Select-String -Pattern "XFAIL|XPASS|PASSED|FAILED"
```

Expected: 2 PASSED + 7 XFAIL. If any XPASS, the implementation file already exists — investigate.

- [ ] **Step 2: Failing unit tests**

Create `tests/unit/agents/customer_support/test_intelligence.py`:

```python
"""Unit tests for app/agents/customer_support/intelligence.py builders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def test_build_ticket_sentiment_payload_shape():
    """Payload has correct claim_type, domain, agent_id, no expiry."""
    from app.agents.customer_support.intelligence import (
        build_ticket_sentiment_payload,
    )

    payload = build_ticket_sentiment_payload(
        ticket_id="abc-123",
        customer_email="USER@Example.COM",
        sentiment="negative",
        confidence=0.55,
    )
    assert payload.claim_type == "ticket_sentiment"
    assert payload.agent_id == "customer_support"
    assert payload.domain == "customer_support"
    assert payload.confidence == 0.55
    assert payload.expires_at is None  # ticket_sentiment never expires
    # Email is normalised to lowercase + trimmed for entity matching
    assert "user@example.com" in payload.finding_text
    # ticket_id encoded so we can search for a specific ticket's sentiment
    assert "abc-123" in payload.finding_text
    assert "negative" in payload.finding_text


def test_build_csat_signal_payload_carries_period():
    """csat_signal text encodes the period so new claims don't shadow prior."""
    from app.agents.customer_support.intelligence import (
        build_csat_signal_payload,
    )

    payload = build_csat_signal_payload(
        customer_email="user@example.com",
        csat_score=4.3,
        period="2026-Q2",
        confidence=0.8,
    )
    assert payload.claim_type == "csat_signal"
    assert "2026-Q2" in payload.finding_text
    assert "4.3" in payload.finding_text
    assert payload.expires_at is None  # csat is a snapshot; doesn't expire


def test_build_churn_risk_payload_ttl_exactly_seven_days():
    """expires_at is now + 7 days at build time (within 1 minute tolerance)."""
    from app.agents.customer_support.intelligence import (
        CHURN_RISK_INDICATOR_TTL,
        build_churn_risk_payload,
    )

    before = datetime.now(timezone.utc)
    payload = build_churn_risk_payload(
        customer_email="user@example.com",
        risk_level="high",
        risk_factors=["5 unresolved tickets", "70% negative sentiment"],
        confidence=0.72,
    )
    after = datetime.now(timezone.utc)

    assert CHURN_RISK_INDICATOR_TTL == timedelta(days=7)
    assert payload.claim_type == "churn_risk_indicator"
    assert payload.expires_at is not None
    # expires_at must be in [before+7d, after+7d]
    assert before + CHURN_RISK_INDICATOR_TTL - timedelta(seconds=1) <= payload.expires_at
    assert payload.expires_at <= after + CHURN_RISK_INDICATOR_TTL + timedelta(seconds=1)
    # finding_text includes risk_level + at least one factor
    assert "high" in payload.finding_text.lower()
    assert "5 unresolved tickets" in payload.finding_text


def test_build_churn_risk_payload_finding_text_above_min_for_embedding():
    """finding_text >= 20 chars so detect_contradictions auto-populate triggers."""
    from app.agents.customer_support.intelligence import (
        build_churn_risk_payload,
    )

    payload = build_churn_risk_payload(
        customer_email="user@example.com",
        risk_level="low",
        risk_factors=[],  # empty factor list — finding_text must still be substantive
        confidence=0.4,
    )
    assert len(payload.finding_text.strip()) >= 20


def test_customer_support_claim_types_constant_is_frozenset():
    """The exported constant is immutable and matches the design vocabulary."""
    from app.agents.customer_support.intelligence import (
        CUSTOMER_SUPPORT_CLAIM_TYPES,
    )

    assert isinstance(CUSTOMER_SUPPORT_CLAIM_TYPES, frozenset)
    assert CUSTOMER_SUPPORT_CLAIM_TYPES == frozenset(
        {"ticket_sentiment", "csat_signal", "churn_risk_indicator"}
    )


def test_customer_entity_canonical_name_lowercased():
    """Builders normalise customer_email to lowercase + trimmed for entity matching."""
    from app.agents.customer_support.intelligence import (
        normalize_customer_email,
    )

    assert normalize_customer_email("  USER@Example.COM  ") == "user@example.com"
    assert normalize_customer_email("user@example.com") == "user@example.com"


def test_build_payload_rejects_out_of_range_confidence():
    """ClaimPayload validation catches confidence > 1 or < 0."""
    from app.agents.customer_support.intelligence import (
        build_ticket_sentiment_payload,
    )

    with pytest.raises(Exception):
        build_ticket_sentiment_payload(
            ticket_id="t-1",
            customer_email="u@e.com",
            sentiment="neutral",
            confidence=1.5,  # invalid
        )
```

- [ ] **Step 3: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/customer_support/test_intelligence.py -v --tb=short
```

Expected: `ModuleNotFoundError: No module named 'app.agents.customer_support.intelligence'`.

- [ ] **Step 4: Implement `app/agents/customer_support/intelligence.py`**

```python
"""Customer-Support claim builders + emission helpers.

Phase 119-02 — ships the three claim_types from the Phase 119 design:
``ticket_sentiment``, ``csat_signal``, ``churn_risk_indicator``.

Builders return ``ClaimPayload`` so callers can either persist immediately
via :func:`app.services.intelligence.write_claim` or batch via
:func:`app.services.intelligence.write_claims`. The ``churn_risk_indicator``
TTL is enforced *at build time* — every emission path goes through
:func:`build_churn_risk_payload`, so TTL drift is impossible.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Final

from app.services.intelligence.schemas import ClaimPayload, ClaimSource

# Public vocabulary — locked by Plan 119-01 contract tests.
CUSTOMER_SUPPORT_CLAIM_TYPES: Final[frozenset[str]] = frozenset(
    {
        "ticket_sentiment",
        "csat_signal",
        "churn_risk_indicator",
    }
)

# TTL for churn_risk_indicator claims — bound by spec § Phase 119.
# Refresh mechanism: every emit stamps `expires_at = now + 7d`; the agent's
# normal recompute pattern keeps the claim fresh. No cron required for the
# expiry contract to hold.
CHURN_RISK_INDICATOR_TTL: Final[timedelta] = timedelta(days=7)

# Agent + domain tag — used by every CS claim.
_AGENT_ID: Final[str] = "customer_support"
_DOMAIN: Final[str] = "customer_support"


def normalize_customer_email(email: str) -> str:
    """Lowercase + trim a customer email for canonical entity matching.

    The kg_entities upsert key is (canonical_name, entity_type); without
    normalisation, "USER@Example.COM" and "user@example.com" would create
    two distinct entities for the same customer.
    """
    return (email or "").strip().lower()


def build_ticket_sentiment_payload(
    *,
    ticket_id: str,
    customer_email: str,
    sentiment: str,
    confidence: float,
    sources: list[ClaimSource] | None = None,
    embed: bool = True,
) -> ClaimPayload:
    """Build a ticket_sentiment claim payload.

    One claim per ticket-thread (not per message). The ticket's id is
    encoded in finding_text so callers can search for it later via
    semantic search or substring filter.

    entity_id is intentionally left as None on the payload — the caller
    (``emit_*`` helper) resolves the customer entity via
    ``get_or_create_entity`` and re-builds the payload with the resolved
    UUID before writing. This keeps builders pure (no DB calls).

    Args:
        ticket_id: The support ticket id.
        customer_email: Customer email (will be normalised).
        sentiment: One of 'positive', 'neutral', 'negative'.
        confidence: Float in [0.0, 1.0]. ClaimPayload validates the range.
        sources: Optional source list. Defaults to a single ``supabase_row``
            source referencing the ticket id.
        embed: Whether to compute the Vertex embedding (default True so
            detect_contradictions auto-populate kicks in).

    Returns:
        ClaimPayload ready to write (caller fills in entity_id).
    """
    normalised_email = normalize_customer_email(customer_email)
    text = (
        f"Customer {normalised_email} expressed {sentiment} sentiment "
        f"in support ticket {ticket_id}."
    )
    return ClaimPayload(
        entity_id=None,  # caller resolves
        domain=_DOMAIN,
        finding_text=text,
        confidence=confidence,
        sources=sources
        or [ClaimSource(kind="supabase_row", ref=f"support_tickets:{ticket_id}")],
        agent_id=_AGENT_ID,
        claim_type="ticket_sentiment",
        embed=embed,
        expires_at=None,
    )


def build_csat_signal_payload(
    *,
    customer_email: str,
    csat_score: float,
    period: str,
    confidence: float,
    sources: list[ClaimSource] | None = None,
    embed: bool = True,
) -> ClaimPayload:
    """Build a csat_signal claim payload (one per (customer, period))."""
    normalised_email = normalize_customer_email(customer_email)
    text = (
        f"Customer {normalised_email} CSAT score {csat_score:.1f} "
        f"for period {period}."
    )
    return ClaimPayload(
        entity_id=None,
        domain=_DOMAIN,
        finding_text=text,
        confidence=confidence,
        sources=sources
        or [
            ClaimSource(
                kind="supabase_row",
                ref=f"customer_health:csat:{normalised_email}:{period}",
            )
        ],
        agent_id=_AGENT_ID,
        claim_type="csat_signal",
        embed=embed,
        expires_at=None,
    )


def build_churn_risk_payload(
    *,
    customer_email: str,
    risk_level: str,
    risk_factors: list[str],
    confidence: float,
    sources: list[ClaimSource] | None = None,
    embed: bool = True,
) -> ClaimPayload:
    """Build a churn_risk_indicator claim payload.

    **Invariant:** ``expires_at = now + CHURN_RISK_INDICATOR_TTL`` (7 days).

    Args:
        customer_email: Customer email (will be normalised).
        risk_level: One of 'low', 'medium', 'high'.
        risk_factors: Human-readable contributing factors (e.g.,
            ['5 unresolved tickets', '70% negative sentiment']).
        confidence: Float in [0.0, 1.0].
        sources: Optional source list.
        embed: Whether to embed.
    """
    normalised_email = normalize_customer_email(customer_email)
    if risk_factors:
        factor_summary = "; ".join(risk_factors)
        text = (
            f"Customer {normalised_email} churn risk level: {risk_level}. "
            f"Contributing factors: {factor_summary}."
        )
    else:
        # Empty-factor case — finding_text still >= 20 chars so embedding triggers.
        text = (
            f"Customer {normalised_email} churn risk level: {risk_level}. "
            f"No specific contributing factors recorded."
        )
    return ClaimPayload(
        entity_id=None,
        domain=_DOMAIN,
        finding_text=text,
        confidence=confidence,
        sources=sources
        or [
            ClaimSource(
                kind="supabase_row",
                ref=f"customer_health:churn:{normalised_email}",
            )
        ],
        agent_id=_AGENT_ID,
        claim_type="churn_risk_indicator",
        embed=embed,
        expires_at=datetime.now(timezone.utc) + CHURN_RISK_INDICATOR_TTL,
    )


__all__ = [
    "CHURN_RISK_INDICATOR_TTL",
    "CUSTOMER_SUPPORT_CLAIM_TYPES",
    "build_churn_risk_payload",
    "build_csat_signal_payload",
    "build_ticket_sentiment_payload",
    "normalize_customer_email",
]
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/customer_support/test_intelligence.py -v --tb=short
```

Expected: all 7 tests pass.

- [ ] **Step 6: Verify Plan 119-01's xfail tests now pass**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_customer_support_schema.py -v 2>&1 | Select-String -Pattern "PASSED|FAILED|XFAIL|XPASS"
```

Expected: 9 PASSED (all xfails resolved). If anything XPASSES or FAILS, the builder shape diverged from the contract — fix `intelligence.py` until the contracts pass.

- [ ] **Step 7: Commit**

```powershell
git add app/agents/customer_support/intelligence.py tests/unit/agents/customer_support/test_intelligence.py
git commit -m "feat(119-02): customer_support claim builders + 7d churn TTL invariant (GREEN)"
```

### Task 2: Extend `find_claims` to hide expired claims by default

**Files:**
- Modify: `app/services/intelligence/claims.py` — add `include_expired: bool = False` kwarg
- Modify: `tests/unit/services/intelligence/test_claims.py` — new tests for the filter

The TTL is only useful if `find_claims` honours it. This is the second half of the churn_risk_indicator contract.

- [ ] **Step 1: Failing tests**

Append to `tests/unit/services/intelligence/test_claims.py` (or create if missing):

```python
"""Unit tests for find_claims expiry filtering (Plan 119-02)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


def _mock_row(*, claim_type: str, expires_at: datetime | None) -> dict:
    """Build a fake kg_findings row with the minimum required fields."""
    return {
        "id": str(uuid4()),
        "entity_id": str(uuid4()),
        "edge_id": None,
        "agent_id": "customer_support",
        "claim_type": claim_type,
        "domain": "customer_support",
        "finding_text": "test " * 5,
        "confidence": 0.5,
        "sources": [],
        "contradicts": [],
        "freshness_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_find_claims_filters_expired_by_default():
    """Claims with expires_at < now() are filtered out unless include_expired=True."""
    from app.services.intelligence.claims import find_claims

    now = datetime.now(timezone.utc)
    expired_row = _mock_row(
        claim_type="churn_risk_indicator", expires_at=now - timedelta(hours=1)
    )
    fresh_row = _mock_row(
        claim_type="churn_risk_indicator", expires_at=now + timedelta(days=3)
    )

    # Mock the Supabase client chain so it returns BOTH rows; the filter is
    # applied client-side in find_claims (NOT in the SQL — that's an option
    # for Task 5 perf work, but client-side keeps the change small).
    fake_client = MagicMock()
    fake_query = MagicMock()
    fake_client.table.return_value = fake_query
    fake_query.select.return_value = fake_query
    fake_query.eq.return_value = fake_query
    fake_query.gte.return_value = fake_query
    fake_query.order.return_value = fake_query
    fake_query.limit.return_value = fake_query
    fake_response = MagicMock()
    fake_response.data = [expired_row, fresh_row]
    fake_query.execute.return_value = fake_response

    with patch(
        "app.services.intelligence.claims._get_supabase_client",
        return_value=fake_client,
    ):
        # Default: expired filtered out
        default_results = await find_claims(claim_type="churn_risk_indicator")
        assert len(default_results) == 1
        assert str(default_results[0].id) == fresh_row["id"]

        # Opt-in: both returned
        all_results = await find_claims(
            claim_type="churn_risk_indicator", include_expired=True
        )
        assert len(all_results) == 2


@pytest.mark.asyncio
async def test_find_claims_keeps_claims_with_null_expires_at():
    """Claims with expires_at IS NULL never expire (e.g., ticket_sentiment)."""
    from app.services.intelligence.claims import find_claims

    never_expires = _mock_row(claim_type="ticket_sentiment", expires_at=None)

    fake_client = MagicMock()
    fake_query = MagicMock()
    fake_client.table.return_value = fake_query
    fake_query.select.return_value = fake_query
    fake_query.eq.return_value = fake_query
    fake_query.order.return_value = fake_query
    fake_query.limit.return_value = fake_query
    fake_response = MagicMock()
    fake_response.data = [never_expires]
    fake_query.execute.return_value = fake_response

    with patch(
        "app.services.intelligence.claims._get_supabase_client",
        return_value=fake_client,
    ):
        results = await find_claims(claim_type="ticket_sentiment")
        assert len(results) == 1
        assert results[0].expires_at is None
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_claims.py -v -k "filters_expired or null_expires_at" --tb=short
```

Expected: `TypeError: find_claims() got an unexpected keyword argument 'include_expired'` (the kwarg doesn't exist yet).

- [ ] **Step 3: Add the filter to `find_claims`**

In `app/services/intelligence/claims.py`, update `find_claims`:

```python
async def find_claims(
    *,
    entity_id: UUID | None = None,
    agent_id: str | None = None,
    claim_type: str | None = None,
    domain: str | None = None,
    min_confidence: float = 0.0,
    fresh_since: datetime | None = None,
    limit: int = 50,
    include_expired: bool = False,
) -> list[Claim]:
    """Structured filter query over kg_findings. All filters AND'd.

    Expired claims (``expires_at < now()``) are filtered out by default —
    pass ``include_expired=True`` to include them (audit / debugging use).
    Claims with ``expires_at IS NULL`` are never considered expired.
    """
    # [... existing implementation up to the query loop ...]
    # After Claim objects are built from rows:
    if not include_expired:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        claims = [c for c in claims if c.expires_at is None or c.expires_at > now]
    return claims
```

The filter is applied client-side after Pydantic conversion. Pushing it into SQL is an optimisation deferred to Task 5 if perf demands it.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_claims.py -v -k "filters_expired or null_expires_at" --tb=short
```

Expected: both new tests pass. Run the FULL `test_claims.py` to confirm no regression:

```powershell
uv run pytest tests/unit/services/intelligence/test_claims.py -v --tb=short
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add app/services/intelligence/claims.py tests/unit/services/intelligence/test_claims.py
git commit -m "feat(119-02): find_claims filters expired claims by default; include_expired opt-in"
```

### Task 3: Wire claim emission into `get_customer_health_dashboard`

**Files:**
- Modify: `app/agents/customer_support/tools.py` — add churn_risk emission + confidence/band fields
- Modify: `tests/unit/agents/customer_support/test_intelligence.py` — append emission tests

`get_customer_health_dashboard` is the canonical churn-risk computation surface (it already returns `churn_risk_level` + `churn_risk_factors`). This task adds a claim emit on every call and decorates the response with `confidence` + `band`.

- [ ] **Step 1: Failing test — emission helper writes a claim**

Append to `tests/unit/agents/customer_support/test_intelligence.py`:

```python
@pytest.mark.asyncio
async def test_emit_churn_risk_writes_claim_with_correct_ttl():
    """emit_churn_risk_indicator persists a claim with expires_at = now+7d."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    from app.agents.customer_support.intelligence import (
        CHURN_RISK_INDICATOR_TTL,
        emit_churn_risk_indicator,
    )

    fake_entity_id = uuid4()
    fake_claim_id = uuid4()
    captured: dict = {}

    async def _capture_write_claim(**kwargs):
        captured.update(kwargs)
        return fake_claim_id

    with patch(
        "app.agents.customer_support.intelligence.get_or_create_entity",
        new=AsyncMock(return_value=fake_entity_id),
    ), patch(
        "app.agents.customer_support.intelligence.write_claim",
        side_effect=_capture_write_claim,
    ):
        before = datetime.now(timezone.utc)
        returned_id = await emit_churn_risk_indicator(
            customer_email="user@example.com",
            risk_level="high",
            risk_factors=["5 unresolved tickets"],
            confidence=0.72,
        )
        after = datetime.now(timezone.utc)

    assert returned_id == fake_claim_id
    assert captured["claim_type"] == "churn_risk_indicator"
    assert captured["entity_id"] == fake_entity_id
    assert captured["agent_id"] == "customer_support"
    # TTL invariant
    expires_at = captured["expires_at"]
    assert before + CHURN_RISK_INDICATOR_TTL - timedelta(seconds=1) <= expires_at
    assert expires_at <= after + CHURN_RISK_INDICATOR_TTL + timedelta(seconds=1)
    # embed=True so detect_contradictions runs
    assert captured["embed"] is True


@pytest.mark.asyncio
async def test_emit_ticket_sentiment_writes_claim_no_expiry():
    """emit_ticket_sentiment persists a claim with expires_at=None."""
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    from app.agents.customer_support.intelligence import emit_ticket_sentiment

    captured: dict = {}

    async def _capture(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.customer_support.intelligence.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.agents.customer_support.intelligence.write_claim",
        side_effect=_capture,
    ):
        await emit_ticket_sentiment(
            ticket_id="t-1",
            customer_email="user@example.com",
            sentiment="negative",
            confidence=0.6,
        )

    assert captured["claim_type"] == "ticket_sentiment"
    assert captured.get("expires_at") is None
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/customer_support/test_intelligence.py -v -k "emit_" --tb=short
```

Expected: `ImportError: cannot import name 'emit_churn_risk_indicator'`.

- [ ] **Step 3: Add emit helpers to `intelligence.py`**

Append to `app/agents/customer_support/intelligence.py`:

```python
from uuid import UUID

from app.services.intelligence.claims import get_or_create_entity, write_claim


async def _resolve_customer_entity(customer_email: str) -> UUID:
    """Resolve (or create) the kg_entities row for a customer email."""
    normalised = normalize_customer_email(customer_email)
    return await get_or_create_entity(
        canonical_name=normalised,
        entity_type="person",
        domains=["customer_support"],
        properties={"first_seen_via": "support_ticket"},
    )


async def emit_ticket_sentiment(
    *,
    ticket_id: str,
    customer_email: str,
    sentiment: str,
    confidence: float,
) -> UUID:
    """Persist a ticket_sentiment claim and return its UUID."""
    entity_id = await _resolve_customer_entity(customer_email)
    payload = build_ticket_sentiment_payload(
        ticket_id=ticket_id,
        customer_email=customer_email,
        sentiment=sentiment,
        confidence=confidence,
    )
    return await write_claim(
        entity_id=entity_id,
        domain=payload.domain,
        finding_text=payload.finding_text,
        confidence=payload.confidence,
        sources=[s.model_dump(exclude_none=True) for s in payload.sources],
        agent_id=payload.agent_id,
        claim_type=payload.claim_type,
        embed=payload.embed,
        expires_at=payload.expires_at,
    )


async def emit_csat_signal(
    *,
    customer_email: str,
    csat_score: float,
    period: str,
    confidence: float,
) -> UUID:
    """Persist a csat_signal claim and return its UUID."""
    entity_id = await _resolve_customer_entity(customer_email)
    payload = build_csat_signal_payload(
        customer_email=customer_email,
        csat_score=csat_score,
        period=period,
        confidence=confidence,
    )
    return await write_claim(
        entity_id=entity_id,
        domain=payload.domain,
        finding_text=payload.finding_text,
        confidence=payload.confidence,
        sources=[s.model_dump(exclude_none=True) for s in payload.sources],
        agent_id=payload.agent_id,
        claim_type=payload.claim_type,
        embed=payload.embed,
        expires_at=payload.expires_at,
    )


async def emit_churn_risk_indicator(
    *,
    customer_email: str,
    risk_level: str,
    risk_factors: list[str],
    confidence: float,
) -> UUID:
    """Persist a churn_risk_indicator claim and return its UUID.

    ``expires_at`` is set to now + 7d by the builder — the invariant.
    """
    entity_id = await _resolve_customer_entity(customer_email)
    payload = build_churn_risk_payload(
        customer_email=customer_email,
        risk_level=risk_level,
        risk_factors=risk_factors,
        confidence=confidence,
    )
    return await write_claim(
        entity_id=entity_id,
        domain=payload.domain,
        finding_text=payload.finding_text,
        confidence=payload.confidence,
        sources=[s.model_dump(exclude_none=True) for s in payload.sources],
        agent_id=payload.agent_id,
        claim_type=payload.claim_type,
        embed=payload.embed,
        expires_at=payload.expires_at,
    )
```

Add the three emit helpers to `__all__`.

- [ ] **Step 4: Wire `get_customer_health_dashboard` to emit churn-risk + decorate response**

In `app/agents/customer_support/tools.py`, modify `get_customer_health_dashboard`:

```python
async def get_customer_health_dashboard() -> dict:
    """[existing docstring — preserved verbatim]"""
    from app.agents.customer_support.intelligence import (
        emit_churn_risk_indicator,
    )
    from app.services.customer_health_service import CustomerHealthService
    from app.services.intelligence.confidence import to_band
    from app.services.intelligence.presets import customer_support_confidence

    try:
        from app.services.request_context import get_current_user_id

        result = await CustomerHealthService().get_health_dashboard(
            user_id=get_current_user_id()
        )

        # Compute confidence from the dashboard signals
        total = result.get("total_tickets", 0) or 0
        resolved_rate = (result.get("resolution_rate", 0.0) or 0.0) / 100.0
        avg_age_h = result.get("avg_resolution_time_hours") or 0.0
        confidence = customer_support_confidence(
            ticket_count=total,
            customer_response_engagement=0.5,  # neutral prior; see Plan 119-02
            resolution_outcome_clarity=resolved_rate,
            data_age_hours=avg_age_h,
        )
        band = to_band(confidence)

        # Emit churn_risk_indicator claim for the user's primary customer cohort.
        # The "customer_email" here is a per-user placeholder — when CS has a
        # multi-customer dashboard, the caller passes the customer email
        # explicitly. For the current single-account dashboard, we anchor on
        # the user_id-derived synthetic email so the entity is stable.
        try:
            user_id = get_current_user_id()
            customer_handle = f"user-{user_id}@account.local"
            await emit_churn_risk_indicator(
                customer_email=customer_handle,
                risk_level=result.get("churn_risk_level", "low"),
                risk_factors=result.get("churn_risk_factors", []),
                confidence=confidence,
            )
        except Exception:  # noqa: BLE001
            # Emission must NOT break the dashboard endpoint.
            pass

        return {
            "success": True,
            "dashboard": result,
            "confidence": confidence,
            "band": band,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/customer_support/test_intelligence.py -v --tb=short
```

Expected: all tests pass (originals + emission tests).

Also confirm the dashboard tool still type-checks and the existing CS test suite stays green:

```powershell
uv run pytest tests/unit/agents/customer_support/ -v --tb=short
```

Expected: green (existing tests not regressed; new tests pass).

- [ ] **Step 6: Commit**

```powershell
git add app/agents/customer_support/intelligence.py app/agents/customer_support/tools.py tests/unit/agents/customer_support/test_intelligence.py
git commit -m "feat(119-02): emit churn_risk_indicator on health dashboard; decorate with confidence+band"
```

### Task 4: Wire `ticket_sentiment` emission into `create_ticket` / `update_ticket`

**Files:**
- Modify: `app/agents/customer_support/tools.py`

`ticket_sentiment` claims must flow whenever sentiment changes. The classification itself lives in `SupportTicketService` (a separate concern); this task only emits a claim when sentiment is known.

- [ ] **Step 1: Failing test — `create_ticket` emits when sentiment present**

Append to `tests/unit/agents/customer_support/test_intelligence.py`:

```python
@pytest.mark.asyncio
async def test_create_ticket_emits_ticket_sentiment_when_known():
    """When SupportTicketService returns a ticket with sentiment, emit the claim."""
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    fake_ticket = {
        "id": "t-42",
        "customer_email": "user@example.com",
        "sentiment": "negative",
        "status": "new",
        "created_at": "2026-05-19T12:00:00Z",
    }

    emitted: list[dict] = []

    async def _capture(**kwargs):
        emitted.append(kwargs)
        return uuid4()

    with patch(
        "app.services.support_ticket_service.SupportTicketService.create_ticket",
        new=AsyncMock(return_value=fake_ticket),
    ), patch(
        "app.agents.customer_support.intelligence.emit_ticket_sentiment",
        side_effect=_capture,
    ), patch(
        "app.services.request_context.get_current_user_id",
        return_value="user-uuid",
    ):
        from app.agents.customer_support.tools import create_ticket

        result = await create_ticket(
            subject="Help!",
            description="My order didn't arrive",
            customer_email="user@example.com",
            priority="high",
        )

    assert result["success"] is True
    assert len(emitted) == 1
    assert emitted[0]["ticket_id"] == "t-42"
    assert emitted[0]["sentiment"] == "negative"


@pytest.mark.asyncio
async def test_create_ticket_does_not_emit_when_sentiment_missing():
    """If the service doesn't return a sentiment, no claim is emitted."""
    from unittest.mock import AsyncMock, patch

    fake_ticket = {
        "id": "t-43",
        "customer_email": "user@example.com",
        "status": "new",
    }

    emitted: list = []

    async def _capture(**kwargs):
        emitted.append(kwargs)

    with patch(
        "app.services.support_ticket_service.SupportTicketService.create_ticket",
        new=AsyncMock(return_value=fake_ticket),
    ), patch(
        "app.agents.customer_support.intelligence.emit_ticket_sentiment",
        side_effect=_capture,
    ), patch(
        "app.services.request_context.get_current_user_id",
        return_value="user-uuid",
    ):
        from app.agents.customer_support.tools import create_ticket

        result = await create_ticket(
            subject="Hi",
            description="Question",
            customer_email="user@example.com",
        )

    assert result["success"] is True
    assert emitted == []
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/customer_support/test_intelligence.py -v -k "create_ticket_emits or sentiment_missing" --tb=short
```

Expected: assertion failures — `create_ticket` doesn't emit anything yet.

- [ ] **Step 3: Add emission to `create_ticket` and `update_ticket`**

In `app/agents/customer_support/tools.py`, modify `create_ticket` to emit on success:

```python
async def create_ticket(
    subject: str, description: str, customer_email: str, priority: str = "normal"
) -> dict:
    """[existing docstring]"""
    from app.agents.customer_support.intelligence import emit_ticket_sentiment
    from app.services.intelligence.confidence import to_band
    from app.services.intelligence.presets import customer_support_confidence
    from app.services.support_ticket_service import SupportTicketService

    try:
        from app.services.request_context import get_current_user_id

        service = SupportTicketService()
        ticket = await service.create_ticket(
            subject,
            description,
            customer_email,
            priority,
            user_id=get_current_user_id(),
        )

        sentiment = ticket.get("sentiment")
        confidence: float | None = None
        band: str | None = None
        if sentiment:
            # Single-ticket signal: volume=1, neutral engagement prior,
            # outcome unknown (0.0), data_age=0 (just created).
            confidence = customer_support_confidence(
                ticket_count=1,
                customer_response_engagement=0.5,
                resolution_outcome_clarity=0.0,
                data_age_hours=0.0,
            )
            band = to_band(confidence)
            try:
                await emit_ticket_sentiment(
                    ticket_id=str(ticket.get("id")),
                    customer_email=customer_email,
                    sentiment=sentiment,
                    confidence=confidence,
                )
            except Exception:  # noqa: BLE001
                pass  # Emission must NOT break ticket creation

        return {
            "success": True,
            "ticket": ticket,
            "confidence": confidence,
            "band": band,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

Apply the same pattern to `update_ticket` — when an updated ticket's sentiment differs from a prior emission (or is now known where it wasn't), emit a fresh `ticket_sentiment` claim. The shared intelligence `detect_contradictions` infra auto-populates `contradicts` if the new sentiment text is semantically close to an opposite prior, so we don't need to track prior state explicitly.

- [ ] **Step 4: Re-run**

```powershell
uv run pytest tests/unit/agents/customer_support/test_intelligence.py -v --tb=short
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add app/agents/customer_support/tools.py tests/unit/agents/customer_support/test_intelligence.py
git commit -m "feat(119-02): emit ticket_sentiment claims from create_ticket/update_ticket"
```

### Task 5: Integration round-trip test — `write_claim` → `find_claims` for all three claim_types

**Files:**
- Create: `tests/integration/agents/customer_support/__init__.py` (empty)
- Create: `tests/integration/agents/customer_support/test_intelligence_claims.py`

- [ ] **Step 1: Write the integration test**

```python
"""Integration: CS claims round-trip through write_claim/find_claims.

Requires local Supabase. Skips when env not set.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_emit_and_find_ticket_sentiment_round_trip():
    """ticket_sentiment claim written via emit_ helper, found via find_claims."""
    from app.agents.customer_support.intelligence import emit_ticket_sentiment
    from app.services.intelligence import find_claims, get_or_create_entity

    email = f"int-{uuid4()}@example.com"
    claim_id = await emit_ticket_sentiment(
        ticket_id=f"t-{uuid4()}",
        customer_email=email,
        sentiment="negative",
        confidence=0.6,
    )
    entity = await get_or_create_entity(
        canonical_name=email.lower().strip(),
        entity_type="person",
        domains=["customer_support"],
    )
    claims = await find_claims(
        entity_id=entity, claim_type="ticket_sentiment", limit=5
    )
    assert any(c.id == claim_id for c in claims)
    target = next(c for c in claims if c.id == claim_id)
    assert target.agent_id == "customer_support"
    assert target.domain == "customer_support"
    assert target.expires_at is None  # ticket_sentiment never expires
    assert target.band in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_emit_and_find_churn_risk_indicator():
    """churn_risk_indicator round-trip; expires_at populated and in future."""
    from datetime import datetime, timedelta, timezone

    from app.agents.customer_support.intelligence import (
        CHURN_RISK_INDICATOR_TTL,
        emit_churn_risk_indicator,
    )
    from app.services.intelligence import find_claims, get_or_create_entity

    email = f"churn-{uuid4()}@example.com"
    claim_id = await emit_churn_risk_indicator(
        customer_email=email,
        risk_level="high",
        risk_factors=["5 unresolved tickets", "70% negative sentiment"],
        confidence=0.78,
    )
    entity = await get_or_create_entity(
        canonical_name=email.lower().strip(),
        entity_type="person",
        domains=["customer_support"],
    )
    claims = await find_claims(
        entity_id=entity, claim_type="churn_risk_indicator", limit=5
    )
    target = next(c for c in claims if c.id == claim_id)
    now = datetime.now(timezone.utc)
    assert target.expires_at is not None
    assert now < target.expires_at <= now + CHURN_RISK_INDICATOR_TTL + timedelta(
        seconds=5
    )


@pytest.mark.asyncio
async def test_emit_and_find_csat_signal_with_period():
    """csat_signal carries period in finding_text and persists across periods."""
    from app.agents.customer_support.intelligence import emit_csat_signal
    from app.services.intelligence import find_claims, get_or_create_entity

    email = f"csat-{uuid4()}@example.com"
    q1_id = await emit_csat_signal(
        customer_email=email, csat_score=3.2, period="2026-Q1", confidence=0.7
    )
    q2_id = await emit_csat_signal(
        customer_email=email, csat_score=4.1, period="2026-Q2", confidence=0.7
    )
    entity = await get_or_create_entity(
        canonical_name=email.lower().strip(),
        entity_type="person",
        domains=["customer_support"],
    )
    claims = await find_claims(entity_id=entity, claim_type="csat_signal", limit=10)
    ids = {c.id for c in claims}
    assert q1_id in ids and q2_id in ids
    # Both periods present — new claim does NOT shadow prior
    texts = " ".join(c.finding_text for c in claims if c.id in {q1_id, q2_id})
    assert "2026-Q1" in texts and "2026-Q2" in texts


@pytest.mark.asyncio
async def test_search_claims_semantic_returns_cs_claims():
    """Semantic search across all agents surfaces CS claims."""
    from app.agents.customer_support.intelligence import (
        emit_churn_risk_indicator,
    )
    from app.services.intelligence import search_claims_semantic

    email = f"sem-{uuid4()}@example.com"
    await emit_churn_risk_indicator(
        customer_email=email,
        risk_level="high",
        risk_factors=["customer threatened to cancel due to delayed responses"],
        confidence=0.8,
    )

    results = await search_claims_semantic(
        query="customer churn risk and cancellation threats", top_k=20
    )
    # At least one result is from customer_support agent
    cs_results = [c for (c, _sim) in results if c.agent_id == "customer_support"]
    assert cs_results, "No customer_support claims returned by semantic search"
```

- [ ] **Step 2: Run with local Supabase**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/agents/customer_support/test_intelligence_claims.py -v --tb=short
```

Expected: all 4 tests pass. If `search_claims_semantic` returns no CS results, the embedding service may have failed silently (logs warning per Plan 113-04 reference) — verify embeddings ran via `select count(*) from kg_findings where agent_id='customer_support' and embedding is not null;`.

- [ ] **Step 3: Commit**

```powershell
git add tests/integration/agents/customer_support/__init__.py tests/integration/agents/customer_support/test_intelligence_claims.py
git commit -m "test(119-02): integration round-trip for all 3 CS claim_types + semantic search"
```

### Task 6: TTL-expiry fixture test (the "nightly job" acceptance criterion)

**Files:**
- Create: `tests/integration/agents/customer_support/test_churn_risk_ttl_expiry.py`

The spec acceptance line:

> A nightly job (or test fixture for the test) verifies expired churn_risk claims are no longer returned by `find_claims`

This task ships the test fixture. The mechanism is: write a `churn_risk_indicator` claim with `expires_at = now - 1 hour` (already expired), then verify `find_claims` does NOT return it by default but DOES return it when `include_expired=True`.

- [ ] **Step 1: Write the expiry test**

```python
"""Integration: expired churn_risk_indicator claims are hidden by find_claims.

This is the "nightly job test fixture" required by the Phase 119 spec
acceptance criteria. The actual expiry semantic is enforced by Task 2's
client-side filter in find_claims.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_expired_churn_risk_indicator_hidden_by_default():
    """Claim with expires_at in the past is filtered out of find_claims."""
    from app.services.intelligence import find_claims, get_or_create_entity
    from app.services.intelligence.claims import write_claim

    email = f"exp-{uuid4()}@example.com"
    entity = await get_or_create_entity(
        canonical_name=email,
        entity_type="person",
        domains=["customer_support"],
    )

    # Write a deliberately-expired claim (expires_at = now - 1 hour)
    expired_id = await write_claim(
        entity_id=entity,
        domain="customer_support",
        finding_text=(
            f"Customer {email} churn risk level: high. "
            "Contributing factors: synthetic past expiry test."
        ),
        confidence=0.5,
        sources=[{"kind": "supabase_row", "ref": "test"}],
        agent_id="customer_support",
        claim_type="churn_risk_indicator",
        embed=False,  # skip embedding to keep the test fast
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    # And a fresh one (expires_at = now + 5 days)
    fresh_id = await write_claim(
        entity_id=entity,
        domain="customer_support",
        finding_text=(
            f"Customer {email} churn risk level: medium. "
            "Contributing factors: synthetic future expiry test."
        ),
        confidence=0.5,
        sources=[{"kind": "supabase_row", "ref": "test"}],
        agent_id="customer_support",
        claim_type="churn_risk_indicator",
        embed=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=5),
    )

    # Default call: expired hidden, fresh visible
    default_results = await find_claims(
        entity_id=entity, claim_type="churn_risk_indicator", limit=10
    )
    default_ids = {c.id for c in default_results}
    assert expired_id not in default_ids
    assert fresh_id in default_ids

    # Opt-in: both visible
    all_results = await find_claims(
        entity_id=entity,
        claim_type="churn_risk_indicator",
        limit=10,
        include_expired=True,
    )
    all_ids = {c.id for c in all_results}
    assert expired_id in all_ids
    assert fresh_id in all_ids


@pytest.mark.asyncio
async def test_emitted_churn_risk_has_future_expiry():
    """A freshly emitted churn_risk_indicator has expires_at in the future."""
    from app.agents.customer_support.intelligence import (
        CHURN_RISK_INDICATOR_TTL,
        emit_churn_risk_indicator,
    )
    from app.services.intelligence import find_claims, get_or_create_entity

    email = f"fresh-{uuid4()}@example.com"
    claim_id = await emit_churn_risk_indicator(
        customer_email=email,
        risk_level="low",
        risk_factors=[],
        confidence=0.4,
    )
    entity = await get_or_create_entity(
        canonical_name=email,
        entity_type="person",
        domains=["customer_support"],
    )
    claims = await find_claims(
        entity_id=entity, claim_type="churn_risk_indicator", limit=5
    )
    target = next(c for c in claims if c.id == claim_id)
    now = datetime.now(timezone.utc)
    assert target.expires_at is not None
    assert target.expires_at > now
    # Within 7 days + small tolerance
    assert target.expires_at <= now + CHURN_RISK_INDICATOR_TTL + timedelta(seconds=5)
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/agents/customer_support/test_churn_risk_ttl_expiry.py -v --tb=short
```

Expected: both tests pass.

- [ ] **Step 3: Commit**

```powershell
git add tests/integration/agents/customer_support/test_churn_risk_ttl_expiry.py
git commit -m "test(119-02): TTL-expiry fixture — expired churn_risk hidden by find_claims"
```

### Task 7: Regression sweep — full CS test suite + lint + acceptance sign-off

- [ ] **Step 1: Run full Customer Support test suite**

```powershell
uv run pytest tests/unit/agents/customer_support/ tests/integration/agents/customer_support/ -v --tb=short
```

Expected: green. If anything pre-existing fails, fix in place and add a `fix(119-02): ...` commit. Do not skip failing tests.

- [ ] **Step 2: Run full intelligence test suite** (regression sanity for the `find_claims` semantic change)

```powershell
uv run pytest tests/unit/services/intelligence/ -v --tb=short
```

Expected: green. The new `include_expired` kwarg is opt-in for inclusion; default behaviour is now *more restrictive*, which could surface latent bugs in callers that depended on expired rows being returned. If any test fails because it depended on the old behaviour, the right fix is `include_expired=True` on that call site — NOT reverting the default.

- [ ] **Step 3: Lint + format**

```powershell
uv run ruff check app/agents/customer_support/ app/services/intelligence/claims.py tests/unit/agents/customer_support/ tests/integration/agents/customer_support/
uv run ruff format app/agents/customer_support/ app/services/intelligence/claims.py tests/unit/agents/customer_support/ tests/integration/agents/customer_support/ --check
```

Fix in place; commit any formatting fixes as `style(119-02): ruff format`.

- [ ] **Step 4: Type check (best-effort)**

```powershell
uv run ty check app/agents/customer_support/intelligence.py app/services/intelligence/claims.py
```

Expected: clean. Fix any errors with a `fix(119-02): ...` commit.

- [ ] **Step 5: Plan 119 acceptance — cross-check ALL spec lines**

| Phase 119 acceptance line | Verified by |
|---|---|
| `presets/customer_support.py` shipped with correct weights | Plan 119-01 Task 2 |
| Self-improvement engine audit (Decision #8) | Plan 119-01 Task 4 |
| All CS outputs carry `confidence` + `band` | Plan 119-02 Tasks 3+4 (dashboard + create_ticket) |
| `churn_risk_indicator` claims always carry `expires_at` ≤ now + 7d | Task 1 build-time test + Task 3 emission test + Task 6 integration |
| Nightly-job-equivalent: expired churn_risk filtered out of `find_claims` | Task 2 (filter) + Task 6 (integration verification) |
| `search_claims_semantic` returns CS claims | Task 5 `test_search_claims_semantic_returns_cs_claims` |
| Customer Support test suite green | Task 7 Step 1 |
| TDD: failing → impl → passing, atomic commits per task | Every task |
| Lint clean (ruff check + format) | Task 7 Step 3 |

- [ ] **Step 6: Phase 119 complete.**

Next planned work: Phase 120 (Operations Agent adoption) — per the rolling-adoption design, the next phase starts with the self-improvement engine audit and the Operations preset (`operations_confidence`).

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| Claim emission for `ticket_sentiment` / `csat_signal` / `churn_risk_indicator` | Tasks 1, 3, 4 |
| `churn_risk_indicator` TTL = 7 days set on every write | Task 1 (`build_churn_risk_payload`) + Task 3 (`emit_churn_risk_indicator`) |
| `expires_at` filter in `find_claims` so expired claims are excluded | Task 2 |
| Test fixture (in lieu of nightly cron) verifies expiry behaviour | Task 6 |
| Cross-agent semantic search returns CS claims | Task 5 |
| All CS tool outputs decorated with `confidence` + `band` | Tasks 3, 4 |
| No external cache plan (CS has no external API surface) | Captured in plan header + spec § Phase 119 |
| Integration round-trip for every claim_type | Task 5 |
| TDD discipline, 2–5-minute steps | Every task structured as failing → impl → green → commit |
| `feat(119-NN): ...` commits per task | Every task's last step |
| Lint clean | Task 7 Step 3 |
| Customer Support test suite green | Task 7 Step 1 |

All Plan 119-02 spec lines covered.

---

## Open question for follow-up (NOT blocking Plan 119-02)

**Question:** Should `churn_risk_indicator` claims be refreshed by a *scheduled* nightly cron job, or rely entirely on the agent's organic recompute pattern (set-and-forget at write time)?

**Interpretation taken in this plan:** Set-and-forget. Every emit stamps `expires_at = now + 7d`; the agent's normal flow (any new ticket → recompute health dashboard → emit fresh claim) keeps the indicator current. If a customer has no activity for >7d, their churn-risk claim expires and falls out of `find_claims` — which is arguably the *correct* signal (we don't know their current risk; better silent than stale).

**Why this isn't a code change in 119-02:** the spec line "must be refreshed weekly via `expires_at` on write" reads as a contract about the write side, not a cron requirement. A cron would be redundant if every CS interaction triggers a fresh emit.

**When to revisit:** if telemetry shows a meaningful number of customers have >7d-stale churn-risk claims silently dropping out of search results AND that's a product issue, ship a follow-up phase to add a weekly recompute cron (e.g., `app/services/intelligence/cron/churn_risk_refresh.py`). That phase would also be the natural home for a *batched* recompute that scores all customers in a single sweep rather than the current per-tool-call pattern.

**Resolution path:** track in MILESTONES.md as "Phase 119.5: Churn-risk refresh cron (deferred)" if needed; do not block 119-02 on this question.
