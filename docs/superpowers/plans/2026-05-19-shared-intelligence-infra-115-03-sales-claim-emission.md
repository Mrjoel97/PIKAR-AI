# Shared Intelligence Infrastructure — Plan 115-03: Sales Claim Emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit three Sales-domain claim types into `kg_findings` so the calibrated `LeadQualification` outputs from Plan 115-01 and the cached HubSpot reads from Plan 115-02 become visible to cross-agent semantic search (`search_claims_semantic`) and to the Strategic Agent's eventual cross-domain consolidation (Phase 121). Ship the **`lead_score` mutate-via-contradicts pattern** so per-lead lead-score history never accumulates as an unbounded sequence of claims — a new score writes a new claim with `contradicts=[old_lead_score_claim_id]`, and downstream consumers always see exactly one current claim per lead.

**Architecture:** Three claim types per spec Phase 115:

| Claim type | Source | Mutation pattern | Embed | Entity binding |
|---|---|---|---|---|
| `lead_score` | LeadQualification annotation (after Plan 115-01 wiring) | **Mutate-via-contradicts** — new claim per re-score, sets `contradicts=[prior_lead_score_claim_id]`. Exactly one fresh claim per `lead_entity` at any time. | True | Per-lead `kg_entity` (entity_type="person", canonical_name=lead.email or lead.name+company) |
| `deal_stage_signal` | `sync_deal_notes` invocations + significant `update_hubspot_deal` calls | Append-only — each stage transition gets its own claim with `expires_at = now + 30d` so they roll off automatically | True | Per-deal `kg_entity` (entity_type="topic", canonical_name=f"deal:{deal_id}") |
| `pipeline_health` | Periodic snapshot (manual or scheduled) — aggregates open deals + win/loss for a user's pipeline | Append-only, **but** the Redis/graph cache from Plan 115-02 means only the freshest one is consulted | True | Per-user pipeline `kg_entity` (entity_type="topic", canonical_name=f"pipeline:{user_id}") |

**The `lead_score` contradicts pattern in detail:**

A naive append-only approach would mean a lead re-scored 50 times during a sales cycle generates 50 `lead_score` claims. `search_claims_semantic` returns all 50; consumers can't tell which is current; the graph bloats; Phase 121's Strategic Agent has to manually de-dupe.

The spec mandates the **contradicts chain** instead: each new `lead_score` for a given lead's entity_id finds the prior fresh `lead_score` claim, writes a new claim with `contradicts=[prior.id]`, and the prior is auto-deemed superseded by reader logic (`find_claims` returns freshest first; consumers filter out claims that appear in another claim's `contradicts` list, leaving exactly one current). Phase 113-05's automatic `contradicts` auto-population only flags topical overlaps (≥0.85 cosine); we explicitly add the prior `lead_score.id` to the `contradicts` list to make the supersession unambiguous regardless of phrasing similarity.

**Tech Stack:** `app/services/intelligence/claims.py` (existing `write_claim`, `find_claims`, `get_or_create_entity`), `app/agents/sales/agent.py` (extend `annotate_lead_qualification_confidence` to emit), `app/agents/tools/hubspot_tools.py` (`sync_deal_notes` and `update_hubspot_deal` emit `deal_stage_signal`), new `app/agents/sales/claims.py` (claim-emission helpers).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 115 — Notable claim types (`lead_score`, `deal_stage_signal`, `pipeline_health`).

**Out of scope:** Calibrating the band thresholds (Phase 112 settled `to_band`). Triggering Strategic Agent's `cross_domain_risk_consolidation` from new claims (Phase 121). Scheduling automatic `pipeline_health` snapshots — this plan emits them when explicitly called; a cron schedule is deferred. Per-claim retention beyond `expires_at` (covered by `kg_findings` migrations).

---

## File structure

**Create:**
- `app/agents/sales/claims.py` — `emit_lead_score_claim`, `emit_deal_stage_signal_claim`, `emit_pipeline_health_claim`
- `tests/unit/agents/sales/test_sales_claim_emission.py` — unit tests with mocked `write_claim`
- `tests/integration/test_sales_claims_round_trip.py` — integration test against local Supabase

**Modify:**
- `app/agents/sales/agent.py` — `annotate_lead_qualification_confidence` calls `emit_lead_score_claim` after computing confidence
- `app/agents/tools/hubspot_tools.py` — `sync_deal_notes` emits `deal_stage_signal` on stage change
- `app/agents/tools/hubspot_tools.py` — new agent tool `snapshot_pipeline_health` for explicit snapshots

---

## Pre-flight context

**`lead_score` claim payload shape:**

```python
ClaimPayload(
    entity_id=lead_entity_id,  # person entity, kg_entities
    domain="sales",
    finding_text=f"Lead {lead_name} @ {company}: score {score}/100 ({band}, BANT). "
                 f"Confidence {confidence:.2f}. Qualified={qualified}.",
    confidence=confidence,  # from sales_confidence
    sources=[
        ClaimSource(kind="other", ref=f"contact:{contact_id}"),
        # optional: ClaimSource(kind="other", ref=f"hubspot_contact:{hs_id}")
    ],
    agent_id="sales",
    claim_type="lead_score",
    embed=True,
    contradicts=[prior_id] if prior_id else [],
)
```

**`deal_stage_signal` claim payload shape:**

```python
ClaimPayload(
    entity_id=deal_entity_id,
    domain="sales",
    finding_text=f"Deal {deal_name} transitioned from {old_stage} to {new_stage} on {date}. "
                 f"Notes: {notes_excerpt}",
    confidence=0.9,  # high — stage transitions are observed facts, not inferences
    sources=[ClaimSource(kind="other", ref=f"deal:{deal_id}")],
    agent_id="sales",
    claim_type="deal_stage_signal",
    embed=True,
    expires_at=now + 30 days,
)
```

**`pipeline_health` claim payload shape:**

```python
ClaimPayload(
    entity_id=pipeline_entity_id,
    domain="sales",
    finding_text=f"Pipeline health for {user_id}: {n_open} open deals, "
                 f"${total_value:.0f} aggregate value, win rate {wr:.0%} (last 30 days). "
                 f"Top stage: {top_stage} ({top_count} deals).",
    confidence=pipeline_health_confidence,  # see Task 5 — uses sales_confidence
    sources=[ClaimSource(kind="other", ref=f"snapshot:{ts}")],
    agent_id="sales",
    claim_type="pipeline_health",
    embed=True,
    expires_at=now + 7 days,  # weekly refresh expected
)
```

**Why `expires_at` differs:**

- `lead_score`: no expiry — supersession via `contradicts` makes prior claims invisible without DB pressure.
- `deal_stage_signal`: 30 days — stage transitions are historical events; we keep them for trend analysis but they auto-roll-off so the graph stays small.
- `pipeline_health`: 7 days — snapshots are designed to be refreshed weekly; older snapshots are misleading.

**Entity resolution:**

`get_or_create_entity` is idempotent by `(canonical_name, entity_type)`. We use:

| Claim type | entity_type | canonical_name shape |
|---|---|---|
| `lead_score` | `"person"` | `lead.email` if present else `f"{lead_name}|{company}"` |
| `deal_stage_signal` | `"topic"` | `f"deal:{pikar_deal_id}"` |
| `pipeline_health` | `"topic"` | `f"pipeline:{user_id}"` |

The pipe-separator in lead's canonical_name avoids collisions when two people share a name across companies.

**`kg_entities` CHECK constraint** (from reference): allowed entity_types are `'company', 'person', 'regulation', 'market', 'technology', 'topic', 'metric', 'country', 'institution', 'product', 'event'`. We use `person` for leads and `topic` for deals/pipelines — both pre-existing.

Acceptance bar (from spec):
- `lead_score` claim emitted with `contradicts=[old_id]` on re-score (Task 3)
- Per-lead claim count stays bounded — re-scoring a lead 10× produces 10 claims, but exactly 1 is "current" (Task 6 round-trip)
- `deal_stage_signal` and `pipeline_health` claims emitted
- `search_claims_semantic(query="lead score for Acme", agent_id="sales")` returns the freshest Sales claim
- Sales Agent test suite green
- `find_claims(entity_id=lead_entity, claim_type="lead_score")` ordered by freshness DESC produces the chain head first

Environment quirks: Windows + uv + Supabase local stack. Integration tests need `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL` per Plan 113-05 pattern.

---

## Tasks

### Task 1: Implement `emit_lead_score_claim` with contradicts chain (TDD)

**Files:**
- Create: `app/agents/sales/claims.py`
- Create: `tests/unit/agents/sales/test_sales_claim_emission.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for Sales claim-emission helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.mark.asyncio
async def test_emit_lead_score_claim_first_time_no_contradicts():
    """First score for a lead writes a claim with empty contradicts."""
    from app.agents.sales.claims import emit_lead_score_claim

    new_id = uuid4()
    lead_entity = uuid4()

    captured = {}

    async def fake_write(**kwargs):
        captured.update(kwargs)
        return new_id

    with patch(
        "app.agents.sales.claims.get_or_create_entity",
        new=AsyncMock(return_value=lead_entity),
    ), patch(
        "app.agents.sales.claims.find_claims",
        new=AsyncMock(return_value=[]),  # no prior claim
    ), patch(
        "app.agents.sales.claims.write_claim",
        new=AsyncMock(side_effect=fake_write),
    ):
        result_id = await emit_lead_score_claim(
            lead_name="Jane Doe",
            company="Acme",
            email="jane@acme.com",
            score=85,
            band="high",
            confidence=0.82,
            framework="BANT",
            qualified=True,
            contact_id="c1",
        )

    assert result_id == new_id
    assert captured["agent_id"] == "sales"
    assert captured["claim_type"] == "lead_score"
    assert captured["embed"] is True
    assert captured["entity_id"] == lead_entity
    assert list(captured["contradicts"]) == []
    assert captured["confidence"] == pytest.approx(0.82)
    assert "Jane Doe" in captured["finding_text"]
    assert "85/100" in captured["finding_text"] or "85" in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_lead_score_claim_re_score_supersedes_prior():
    """Second score for same lead writes a claim with contradicts=[prior_id]."""
    from datetime import datetime, timezone

    from app.agents.sales.claims import emit_lead_score_claim
    from app.services.intelligence.schemas import Claim, ClaimSource

    prior_id = uuid4()
    new_id = uuid4()
    lead_entity = uuid4()

    prior_claim = Claim(
        id=prior_id,
        entity_id=lead_entity,
        edge_id=None,
        agent_id="sales",
        claim_type="lead_score",
        domain="sales",
        finding_text="Lead Jane Doe @ Acme: score 72/100 (medium, BANT).",
        confidence=0.65,
        sources=[ClaimSource(kind="other", ref="contact:c1")],
        contradicts=[],
        freshness_at=datetime.now(timezone.utc),
        expires_at=None,
        created_at=datetime.now(timezone.utc),
    )

    captured = {}

    async def fake_write(**kwargs):
        captured.update(kwargs)
        return new_id

    with patch(
        "app.agents.sales.claims.get_or_create_entity",
        new=AsyncMock(return_value=lead_entity),
    ), patch(
        "app.agents.sales.claims.find_claims",
        new=AsyncMock(return_value=[prior_claim]),
    ), patch(
        "app.agents.sales.claims.write_claim",
        new=AsyncMock(side_effect=fake_write),
    ):
        result_id = await emit_lead_score_claim(
            lead_name="Jane Doe",
            company="Acme",
            email="jane@acme.com",
            score=85,
            band="high",
            confidence=0.82,
            framework="BANT",
            qualified=True,
            contact_id="c1",
        )

    assert result_id == new_id
    assert list(captured["contradicts"]) == [prior_id]


@pytest.mark.asyncio
async def test_emit_lead_score_claim_third_score_supersedes_only_freshest():
    """Third score's contradicts list contains only the immediate predecessor."""
    from datetime import datetime, timedelta, timezone

    from app.agents.sales.claims import emit_lead_score_claim
    from app.services.intelligence.schemas import Claim, ClaimSource

    older_id = uuid4()
    freshest_prior = uuid4()
    new_id = uuid4()
    lead_entity = uuid4()

    now = datetime.now(timezone.utc)
    # find_claims returns freshest first
    prior_claims = [
        Claim(
            id=freshest_prior,
            entity_id=lead_entity,
            edge_id=None,
            agent_id="sales",
            claim_type="lead_score",
            domain="sales",
            finding_text="...",
            confidence=0.7,
            sources=[ClaimSource(kind="other", ref="x")],
            contradicts=[older_id],
            freshness_at=now,
            expires_at=None,
            created_at=now,
        ),
        Claim(
            id=older_id,
            entity_id=lead_entity,
            edge_id=None,
            agent_id="sales",
            claim_type="lead_score",
            domain="sales",
            finding_text="...",
            confidence=0.5,
            sources=[ClaimSource(kind="other", ref="x")],
            contradicts=[],
            freshness_at=now - timedelta(days=1),
            expires_at=None,
            created_at=now - timedelta(days=1),
        ),
    ]

    captured = {}

    async def fake_write(**kwargs):
        captured.update(kwargs)
        return new_id

    with patch(
        "app.agents.sales.claims.get_or_create_entity",
        new=AsyncMock(return_value=lead_entity),
    ), patch(
        "app.agents.sales.claims.find_claims",
        new=AsyncMock(return_value=prior_claims),
    ), patch(
        "app.agents.sales.claims.write_claim",
        new=AsyncMock(side_effect=fake_write),
    ):
        await emit_lead_score_claim(
            lead_name="Jane Doe", company="Acme", email="jane@acme.com",
            score=88, band="high", confidence=0.85,
            framework="BANT", qualified=True, contact_id="c1",
        )

    # Only the immediately-prior (freshest) claim is in contradicts.
    # The older one is already chained-out via the prior's contradicts.
    assert list(captured["contradicts"]) == [freshest_prior]


@pytest.mark.asyncio
async def test_emit_lead_score_canonical_name_prefers_email():
    """Canonical name uses email when present."""
    from app.agents.sales.claims import emit_lead_score_claim

    captured = {}

    async def fake_get_entity(*, canonical_name, entity_type, **kw):
        captured["canonical_name"] = canonical_name
        captured["entity_type"] = entity_type
        return uuid4()

    with patch(
        "app.agents.sales.claims.get_or_create_entity",
        side_effect=fake_get_entity,
    ), patch(
        "app.agents.sales.claims.find_claims",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.agents.sales.claims.write_claim",
        new=AsyncMock(return_value=uuid4()),
    ):
        await emit_lead_score_claim(
            lead_name="Jane Doe", company="Acme", email="jane@acme.com",
            score=85, band="high", confidence=0.8,
            framework="BANT", qualified=True, contact_id="c1",
        )

    assert captured["canonical_name"] == "jane@acme.com"
    assert captured["entity_type"] == "person"


@pytest.mark.asyncio
async def test_emit_lead_score_canonical_name_falls_back_to_name_company():
    """No email → canonical = 'Name|Company'."""
    from app.agents.sales.claims import emit_lead_score_claim

    captured = {}

    async def fake_get_entity(*, canonical_name, entity_type, **kw):
        captured["canonical_name"] = canonical_name
        return uuid4()

    with patch(
        "app.agents.sales.claims.get_or_create_entity",
        side_effect=fake_get_entity,
    ), patch(
        "app.agents.sales.claims.find_claims",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.agents.sales.claims.write_claim",
        new=AsyncMock(return_value=uuid4()),
    ):
        await emit_lead_score_claim(
            lead_name="Jane Doe", company="Acme", email=None,
            score=85, band="high", confidence=0.8,
            framework="BANT", qualified=True, contact_id=None,
        )

    assert captured["canonical_name"] == "Jane Doe|Acme"
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/sales/test_sales_claim_emission.py -v --tb=short
```

- [ ] **Step 3: Implement `app/agents/sales/claims.py`**

```python
"""Claim-emission helpers for the Sales Agent.

Phase 115-03 — three claim types:
- lead_score: mutate-via-contradicts (one current per lead)
- deal_stage_signal: append-only with 30d expires_at
- pipeline_health: append-only with 7d expires_at, refreshed via cron later
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.services.intelligence import (
    find_claims,
    get_or_create_entity,
    write_claim,
)
from app.services.intelligence.schemas import ClaimSource

logger = logging.getLogger(__name__)


def _lead_canonical_name(*, email: str | None, lead_name: str, company: str) -> str:
    """Pick the strongest unique key for a person entity."""
    if email:
        return email.strip().lower()
    return f"{lead_name.strip()}|{company.strip()}"


async def emit_lead_score_claim(
    *,
    lead_name: str,
    company: str,
    email: str | None,
    score: int,
    band: str,
    confidence: float,
    framework: str,
    qualified: bool,
    contact_id: str | None,
) -> UUID:
    """Emit a lead_score claim with contradicts-chain supersession.

    On re-score, finds the freshest prior lead_score claim for the same
    lead entity and includes its ID in the new claim's `contradicts` list.
    Downstream readers (Phase 121 Strategic Agent, /admin/research/overview)
    filter freshest-with-no-superseder to show exactly one current score.

    Args:
        lead_name: Lead's full name.
        company: Lead's company (used for canonical-name fallback).
        email: Lead's email — preferred canonical key.
        score: 0-100 score from the framework.
        band: "low" | "medium" | "high" (from sales_confidence + to_band).
        confidence: [0.0, 1.0] from sales_confidence.
        framework: "BANT" | "MEDDIC" | "CHAMP".
        qualified: Whether the lead is qualified.
        contact_id: Pikar contacts.id — joins to HubSpot via hubspot_contact_id.

    Returns:
        UUID of the newly written kg_findings row.
    """
    canonical = _lead_canonical_name(
        email=email, lead_name=lead_name, company=company,
    )

    lead_entity = await get_or_create_entity(
        canonical_name=canonical,
        entity_type="person",
        domains=["sales"],
        properties={"company": company, "lead_name": lead_name},
    )

    # Look up freshest prior lead_score for this lead — to chain contradicts.
    prior_ids: list[UUID] = []
    try:
        prior = await find_claims(
            entity_id=lead_entity,
            agent_id="sales",
            claim_type="lead_score",
            limit=1,  # only the freshest — older claims are already chained
        )
        if prior:
            prior_ids = [prior[0].id]
    except Exception as exc:
        logger.warning("emit_lead_score_claim: prior lookup failed: %s", exc)

    sources: list[dict] = []
    if contact_id:
        sources.append({"kind": "other", "ref": f"contact:{contact_id}"})

    finding_text = (
        f"Lead {lead_name} @ {company}: score {score}/100 ({band}, {framework}). "
        f"Confidence {confidence:.2f}. Qualified={qualified}."
    )

    return await write_claim(
        entity_id=lead_entity,
        domain="sales",
        finding_text=finding_text,
        confidence=float(confidence),
        sources=sources,
        agent_id="sales",
        claim_type="lead_score",
        embed=True,
        contradicts=prior_ids,
    )


async def emit_deal_stage_signal_claim(
    *,
    deal_id: str,
    deal_name: str,
    old_stage: str | None,
    new_stage: str,
    notes_excerpt: str | None = None,
    confidence: float = 0.9,
) -> UUID:
    """Emit a deal_stage_signal claim. Append-only, 30-day expiry."""
    deal_entity = await get_or_create_entity(
        canonical_name=f"deal:{deal_id}",
        entity_type="topic",
        domains=["sales"],
        properties={"deal_name": deal_name},
    )

    transition = f"transitioned from {old_stage} to {new_stage}" if old_stage else f"entered stage {new_stage}"
    notes_part = f" Notes: {notes_excerpt[:200]}" if notes_excerpt else ""
    finding_text = (
        f"Deal '{deal_name}' (id={deal_id}) {transition} on "
        f"{datetime.now(timezone.utc).date().isoformat()}.{notes_part}"
    )

    expires = datetime.now(timezone.utc) + timedelta(days=30)

    return await write_claim(
        entity_id=deal_entity,
        domain="sales",
        finding_text=finding_text,
        confidence=float(confidence),
        sources=[{"kind": "other", "ref": f"deal:{deal_id}"}],
        agent_id="sales",
        claim_type="deal_stage_signal",
        embed=True,
        expires_at=expires,
    )


async def emit_pipeline_health_claim(
    *,
    user_id: str,
    open_deal_count: int,
    total_value: float,
    win_rate_30d: float,
    top_stage: str,
    top_stage_count: int,
    confidence: float,
) -> UUID:
    """Emit a pipeline_health snapshot claim. 7-day expiry, weekly refresh."""
    pipeline_entity = await get_or_create_entity(
        canonical_name=f"pipeline:{user_id}",
        entity_type="topic",
        domains=["sales"],
        properties={"user_id": user_id},
    )

    finding_text = (
        f"Pipeline health for user {user_id}: {open_deal_count} open deals, "
        f"${total_value:,.0f} aggregate value, win rate {win_rate_30d:.0%} "
        f"(last 30 days). Top stage: {top_stage} ({top_stage_count} deals)."
    )

    expires = datetime.now(timezone.utc) + timedelta(days=7)

    return await write_claim(
        entity_id=pipeline_entity,
        domain="sales",
        finding_text=finding_text,
        confidence=float(confidence),
        sources=[{"kind": "other", "ref": f"snapshot:{datetime.now(timezone.utc).isoformat()}"}],
        agent_id="sales",
        claim_type="pipeline_health",
        embed=True,
        expires_at=expires,
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/sales/test_sales_claim_emission.py -v --tb=short
```

Expected output snippet:

```
test_emit_lead_score_claim_first_time_no_contradicts PASSED
test_emit_lead_score_claim_re_score_supersedes_prior PASSED
test_emit_lead_score_claim_third_score_supersedes_only_freshest PASSED
test_emit_lead_score_canonical_name_prefers_email PASSED
test_emit_lead_score_canonical_name_falls_back_to_name_company PASSED
======== 5 passed in 0.XXs ========
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/sales/claims.py tests/unit/agents/sales/test_sales_claim_emission.py
git commit -m "feat(115-03): emit_lead_score_claim with contradicts-chain supersession (GREEN)"
```

### Task 2: Wire `emit_lead_score_claim` into the Sales director's annotation path

**Files:**
- Modify: `app/agents/sales/agent.py` — `annotate_lead_qualification_confidence` calls `emit_lead_score_claim` after computing confidence

The wiring extends Plan 115-01's `annotate_lead_qualification_confidence` so that as soon as we compute the confidence + band, we also persist the score as a `lead_score` claim. The emission is fire-and-forget logged-on-failure — a Supabase outage MUST NOT block the conversational narration.

- [ ] **Step 1: Add a failing test**

```python
# Append to tests/unit/agents/sales/test_sales_confidence_wiring.py


@pytest.mark.asyncio
async def test_annotate_lead_qualification_emits_lead_score_claim_on_success():
    """When CRM lookup succeeds, a lead_score claim is emitted."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    payload = {
        "lead_name": "Jane Doe", "company": "Acme",
        "score": 85, "framework": "BANT", "qualified": True,
        "priority": "high", "next_steps": [],
        "criteria_breakdown": [
            {"criterion": "Budget", "score": 85, "notes": "Confirmed"},
            {"criterion": "Authority", "score": 90, "notes": "Decision maker"},
            {"criterion": "Need", "score": 80, "notes": "Pain points"},
            {"criterion": "Timeline", "score": 85, "notes": "Q2"},
        ],
    }
    qual = LeadQualification.model_validate(payload)

    emit_mock = AsyncMock(return_value=uuid4())
    with patch(
        "app.agents.sales.agent._lookup_contact_crm_meta",
        new=AsyncMock(return_value={
            "hubspot_contact_id": "h1",
            "source": "inbound",
            "days_since_last_touch": 2.0,
            "email": "jane@acme.com",
            "contact_id": "c1",
        }),
    ), patch(
        "app.agents.sales.agent.emit_lead_score_claim",
        new=emit_mock,
    ):
        await annotate_lead_qualification_confidence(qual)

    emit_mock.assert_awaited_once()
    args, kwargs = emit_mock.call_args
    assert kwargs["lead_name"] == "Jane Doe"
    assert kwargs["company"] == "Acme"
    assert kwargs["email"] == "jane@acme.com"
    assert kwargs["score"] == 85
    assert kwargs["framework"] == "BANT"
    assert kwargs["qualified"] is True


@pytest.mark.asyncio
async def test_annotate_lead_qualification_swallows_emit_errors():
    """Claim emit failure does NOT block narration — confidence still set."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    qual = LeadQualification.model_validate({
        "lead_name": "X", "company": "Y",
        "score": 50, "framework": "BANT", "qualified": False,
        "priority": "low", "next_steps": [],
        "criteria_breakdown": [],
    })

    with patch(
        "app.agents.sales.agent._lookup_contact_crm_meta",
        new=AsyncMock(return_value={}),
    ), patch(
        "app.agents.sales.agent.emit_lead_score_claim",
        new=AsyncMock(side_effect=RuntimeError("supabase down")),
    ):
        # Must NOT raise
        result = await annotate_lead_qualification_confidence(qual)

    assert result.confidence is not None
    assert result.band is not None
```

Add `from uuid import uuid4` to the test file imports if missing.

- [ ] **Step 2: Run — should FAIL on the first new test**

```powershell
uv run pytest tests/unit/agents/sales/test_sales_confidence_wiring.py -v --tb=short -k "emits_lead_score or swallows_emit"
```

- [ ] **Step 3: Extend `_lookup_contact_crm_meta` to also return `email` + `contact_id`** (it already fetches the contact row — just include the fields)

In `app/agents/sales/agent.py` `_lookup_contact_crm_meta`, change the `.select("id, hubspot_contact_id, source")` to `.select("id, name, email, hubspot_contact_id, source")` and the returned dict to include:

```python
return {
    "hubspot_contact_id": contact.get("hubspot_contact_id"),
    "source": contact.get("source"),
    "days_since_last_touch": days_since,
    "email": contact.get("email"),
    "contact_id": contact.get("id"),
}
```

- [ ] **Step 4: Modify `annotate_lead_qualification_confidence` to emit after computing**

After the `qual.confidence = confidence; qual.band = to_band(confidence)` lines, append:

```python
# Phase 115-03: persist as a lead_score claim. Fire-and-forget — a claim
# emission failure MUST NOT block conversational narration.
try:
    from app.agents.sales.claims import emit_lead_score_claim

    await emit_lead_score_claim(
        lead_name=qual.lead_name,
        company=qual.company,
        email=(meta or {}).get("email") if meta else None,
        score=qual.score,
        band=qual.band,
        confidence=qual.confidence,
        framework=qual.framework,
        qualified=qual.qualified,
        contact_id=(meta or {}).get("contact_id") if meta else None,
    )
except Exception as exc:
    logger.warning(
        "annotate_lead_qualification_confidence: claim emit failed (non-fatal): %s",
        exc,
    )
```

Note we import `emit_lead_score_claim` at function scope so the test's patch of `app.agents.sales.agent.emit_lead_score_claim` works — that means we also need to make it a module-level symbol so the patch resolves. The cleanest fix: add `from app.agents.sales.claims import emit_lead_score_claim` at the top of `app/agents/sales/agent.py` (alongside other imports) and remove the function-scope import.

- [ ] **Step 5: Re-run + commit**

```powershell
uv run pytest tests/unit/agents/sales/test_sales_confidence_wiring.py -v --tb=short
```

Expected: all green including the two new tests.

```bash
git add app/agents/sales/agent.py tests/unit/agents/sales/test_sales_confidence_wiring.py
git commit -m "feat(115-03): wire emit_lead_score_claim into LeadQualification annotation"
```

### Task 3: Emit `deal_stage_signal` from `sync_deal_notes`

**Files:**
- Modify: `app/agents/tools/hubspot_tools.py` — `sync_deal_notes`
- Create: `tests/unit/agents/tools/test_sync_deal_notes_emits_signal.py`

`sync_deal_notes` already accepts a `stage_change` parameter and tracks whether the stage actually changed via `stage_changed`. When `stage_changed is True`, we emit a `deal_stage_signal` claim with the old + new stages from the deal record.

- [ ] **Step 1: Failing test**

```python
"""sync_deal_notes emits deal_stage_signal claim on stage change."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_sync_deal_notes_emits_signal_on_stage_change():
    """Stage transition → deal_stage_signal claim emitted."""
    from app.agents.tools import hubspot_tools

    deal_row = {
        "id": "deal-uuid-1",
        "deal_name": "Acme Renewal",
        "stage": "discovery",
        "hubspot_deal_id": "hs-100",
        "user_id": "user-1",
        "properties": {},
    }

    fake_admin = MagicMock()
    fake_admin.client.table.return_value.select.return_value.eq.return_value \
        .or_.return_value.limit.return_value = "find_deal_query"
    fake_admin.client.table.return_value.update.return_value.eq.return_value = "update_query"

    fake_svc = MagicMock()
    fake_svc.add_deal_note = AsyncMock(return_value={"stage_changed": True})

    emit_mock = AsyncMock(return_value=uuid4())

    async def fake_execute(query, op_name=None):
        # Return the deal_row on lookup, no-op on update.
        result = MagicMock()
        if op_name == "hubspot_tools.sync_deal_notes.find_deal":
            result.data = [deal_row]
        else:
            result.data = [{}]
        return result

    with patch(
        "app.agents.tools.hubspot_tools.AdminService",
        return_value=fake_admin,
    ), patch(
        "app.agents.tools.hubspot_tools.HubSpotService",
        return_value=fake_svc,
    ), patch(
        "app.agents.tools.hubspot_tools._execute_async_query",
        side_effect=fake_execute,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ), patch(
        "app.agents.tools.hubspot_tools.emit_deal_stage_signal_claim",
        new=emit_mock,
    ):
        result = await hubspot_tools.sync_deal_notes(
            deal_name_or_id="Acme Renewal",
            notes="Customer ready to negotiate",
            stage_change="negotiation",
        )

    assert result["success"] is True
    assert result["stage_changed"] is True
    emit_mock.assert_awaited_once()
    kw = emit_mock.call_args.kwargs
    assert kw["deal_id"] == "deal-uuid-1"
    assert kw["deal_name"] == "Acme Renewal"
    assert kw["old_stage"] == "discovery"
    assert kw["new_stage"] == "negotiation"


@pytest.mark.asyncio
async def test_sync_deal_notes_no_emit_when_stage_unchanged():
    """No stage change → no deal_stage_signal claim."""
    from app.agents.tools import hubspot_tools

    deal_row = {
        "id": "deal-uuid-2",
        "deal_name": "Beta Deal",
        "stage": "qualified",
        "hubspot_deal_id": "hs-200",
        "user_id": "user-1",
        "properties": {},
    }

    fake_admin = MagicMock()
    fake_svc = MagicMock()
    fake_svc.add_deal_note = AsyncMock(return_value={"stage_changed": False})
    emit_mock = AsyncMock(return_value=uuid4())

    async def fake_execute(query, op_name=None):
        result = MagicMock()
        if op_name == "hubspot_tools.sync_deal_notes.find_deal":
            result.data = [deal_row]
        else:
            result.data = [{}]
        return result

    with patch(
        "app.agents.tools.hubspot_tools.AdminService",
        return_value=fake_admin,
    ), patch(
        "app.agents.tools.hubspot_tools.HubSpotService",
        return_value=fake_svc,
    ), patch(
        "app.agents.tools.hubspot_tools._execute_async_query",
        side_effect=fake_execute,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ), patch(
        "app.agents.tools.hubspot_tools.emit_deal_stage_signal_claim",
        new=emit_mock,
    ):
        await hubspot_tools.sync_deal_notes(
            deal_name_or_id="Beta Deal",
            notes="Continued discovery; no stage change",
            stage_change=None,
        )

    emit_mock.assert_not_called()
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/tools/test_sync_deal_notes_emits_signal.py -v --tb=short
```

- [ ] **Step 3: Modify `sync_deal_notes`**

At the top of `app/agents/tools/hubspot_tools.py` imports, add:

```python
from app.agents.sales.claims import emit_deal_stage_signal_claim
```

In `sync_deal_notes`, after the existing local-properties update and before the final `return` block, add:

```python
# Phase 115-03: emit deal_stage_signal claim on actual stage change.
# Fire-and-forget; failures must NOT mask the tool result.
if stage_changed and stage_change:
    try:
        await emit_deal_stage_signal_claim(
            deal_id=deal_id,
            deal_name=deal.get("deal_name") or "(unknown)",
            old_stage=deal.get("stage"),
            new_stage=stage_change,
            notes_excerpt=notes,
        )
    except Exception:
        logger.warning(
            "sync_deal_notes: deal_stage_signal claim emit failed for deal=%s",
            deal_id,
        )
```

- [ ] **Step 4: Re-run + commit**

```powershell
uv run pytest tests/unit/agents/tools/test_sync_deal_notes_emits_signal.py -v --tb=short
```

Expected: 2 passed.

```bash
git add app/agents/tools/hubspot_tools.py tests/unit/agents/tools/test_sync_deal_notes_emits_signal.py
git commit -m "feat(115-03): emit deal_stage_signal claim from sync_deal_notes on stage change"
```

### Task 4: New agent tool `snapshot_pipeline_health` for explicit pipeline snapshots

**Files:**
- Modify: `app/agents/tools/hubspot_tools.py` — append `snapshot_pipeline_health`
- Modify: `app/agents/sales/tools.py` — extend `_TOOL_IDS` (no, the import is `hubspot_tools` — verify)
- Create: `tests/unit/agents/tools/test_snapshot_pipeline_health.py`

`snapshot_pipeline_health()` aggregates the user's open deals from `hubspot_deals`, computes the metrics, and emits a `pipeline_health` claim. It uses `sales_confidence(...)` so the claim's confidence reflects the quality of the underlying data (deal count = `lead_criteria_completeness` proxy, ages = `recency`, etc.).

- [ ] **Step 1: Failing test**

```python
"""snapshot_pipeline_health aggregates pipeline + emits pipeline_health claim."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_snapshot_pipeline_health_emits_claim_with_metrics():
    """Tool aggregates deals and emits pipeline_health claim with correct fields."""
    from app.agents.tools import hubspot_tools

    deals = [
        {"id": "d1", "stage": "qualified", "amount": "10000", "created_at": "2026-05-01T00:00:00Z"},
        {"id": "d2", "stage": "qualified", "amount": "20000", "created_at": "2026-05-05T00:00:00Z"},
        {"id": "d3", "stage": "negotiation", "amount": "50000", "created_at": "2026-05-10T00:00:00Z"},
        {"id": "d4", "stage": "closedwon", "amount": "30000", "created_at": "2026-04-15T00:00:00Z"},
        {"id": "d5", "stage": "closedlost", "amount": "5000", "created_at": "2026-04-20T00:00:00Z"},
    ]

    fake_admin = MagicMock()
    fake_admin.client.table.return_value.select.return_value.eq.return_value = "q"

    async def fake_execute(query, op_name=None):
        result = MagicMock()
        result.data = deals
        return result

    emit_mock = AsyncMock(return_value=uuid4())

    with patch(
        "app.agents.tools.hubspot_tools.AdminService",
        return_value=fake_admin,
    ), patch(
        "app.agents.tools.hubspot_tools._execute_async_query",
        side_effect=fake_execute,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ), patch(
        "app.agents.tools.hubspot_tools.emit_pipeline_health_claim",
        new=emit_mock,
    ):
        result = await hubspot_tools.snapshot_pipeline_health()

    assert result["success"] is True
    emit_mock.assert_awaited_once()
    kw = emit_mock.call_args.kwargs
    # 3 open (qualified×2 + negotiation×1)
    assert kw["open_deal_count"] == 3
    # total open value = 10000 + 20000 + 50000 = 80000
    assert kw["total_value"] == pytest.approx(80000.0)
    # 1 won / (1 won + 1 lost) = 50% win rate
    assert kw["win_rate_30d"] == pytest.approx(0.5)
    # Top stage = 'qualified' (2 deals)
    assert kw["top_stage"] == "qualified"
    assert kw["top_stage_count"] == 2
    assert 0.0 <= kw["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_snapshot_pipeline_health_empty_pipeline():
    """No deals → claim still emitted with zeroed metrics + low confidence."""
    from app.agents.tools import hubspot_tools

    async def fake_execute(query, op_name=None):
        result = MagicMock()
        result.data = []
        return result

    emit_mock = AsyncMock(return_value=uuid4())

    with patch(
        "app.agents.tools.hubspot_tools.AdminService",
        return_value=MagicMock(),
    ), patch(
        "app.agents.tools.hubspot_tools._execute_async_query",
        side_effect=fake_execute,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ), patch(
        "app.agents.tools.hubspot_tools.emit_pipeline_health_claim",
        new=emit_mock,
    ):
        result = await hubspot_tools.snapshot_pipeline_health()

    assert result["success"] is True
    emit_mock.assert_awaited_once()
    kw = emit_mock.call_args.kwargs
    assert kw["open_deal_count"] == 0
    assert kw["total_value"] == 0
    assert kw["confidence"] < 0.5  # empty pipeline → low confidence
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/tools/test_snapshot_pipeline_health.py -v --tb=short
```

- [ ] **Step 3: Implement `snapshot_pipeline_health` in `hubspot_tools.py`**

Add to imports:

```python
from app.agents.sales.claims import emit_pipeline_health_claim
from app.services.intelligence.presets import sales_confidence
```

Append the function:

```python
_OPEN_STAGES = {"qualified", "appointmentscheduled", "qualifiedtobuy", "presentationscheduled", "decisionmakerboughtin", "contractsent", "negotiation"}
_WON_STAGES = {"closedwon"}
_LOST_STAGES = {"closedlost"}


async def snapshot_pipeline_health() -> dict[str, Any]:
    """Aggregate the user's pipeline and emit a pipeline_health claim.

    Reads hubspot_deals for the current user, computes open count, total
    value, win rate, and top stage, and emits a Phase 115-03
    pipeline_health claim with confidence derived from sales_confidence.

    Returns:
        Dict with success + the computed metrics (claim_id on success).
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    admin = AdminService()
    try:
        result = await _execute_async_query(
            admin.client.table("hubspot_deals").select(
                "id, stage, amount, created_at"
            ).eq("user_id", user_id),
            op_name="hubspot_tools.snapshot_pipeline_health.list",
        )
        deals = result.data or []
    except Exception as exc:
        logger.exception("snapshot_pipeline_health list failed")
        return {"error": f"Failed to list deals: {exc}"}

    open_deals = [d for d in deals if (d.get("stage") or "").lower() in _OPEN_STAGES]
    won = [d for d in deals if (d.get("stage") or "").lower() in _WON_STAGES]
    lost = [d for d in deals if (d.get("stage") or "").lower() in _LOST_STAGES]
    total_value = sum(float(d.get("amount") or 0) for d in open_deals)

    # Top stage among open deals
    stage_counts: dict[str, int] = {}
    for d in open_deals:
        s = (d.get("stage") or "unknown").lower()
        stage_counts[s] = stage_counts.get(s, 0) + 1
    if stage_counts:
        top_stage, top_count = max(stage_counts.items(), key=lambda kv: kv[1])
    else:
        top_stage, top_count = "none", 0

    win_rate = 0.0
    closed_total = len(won) + len(lost)
    if closed_total > 0:
        win_rate = len(won) / closed_total

    # Confidence proxies:
    # - lead_criteria_completeness ≈ min(1, n_open / 10) (10 open deals = healthy)
    # - crm_authority = 0.9 (HubSpot-sourced deal data)
    # - recency = 1 - min(1, avg_age_days / 90) — capped at 0 for 90+ day pipelines
    # - signal_consistency = 1 - clamp(stdev(stage_counts.values()) / 5)
    import statistics as _stats

    completeness = min(1.0, len(open_deals) / 10.0)
    authority = 0.9
    # Average age of open deals (cap recency horizon at 90d for pipeline freshness)
    ages_days: list[float] = []
    for d in open_deals:
        ts = d.get("created_at")
        if isinstance(ts, str):
            try:
                created = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ages_days.append(
                    (datetime.now(timezone.utc) - created).total_seconds() / 86400.0
                )
            except ValueError:
                continue
    avg_age = sum(ages_days) / len(ages_days) if ages_days else 0.0
    recency = max(0.0, 1.0 - min(1.0, avg_age / 90.0))

    if len(stage_counts) > 1:
        stdev = _stats.stdev(stage_counts.values())
        consistency = max(0.0, 1.0 - min(1.0, stdev / 5.0))
    else:
        consistency = 0.6  # single-stage pipeline = moderate consistency

    confidence = sales_confidence(
        lead_criteria_completeness=completeness,
        crm_authority=authority,
        recency=recency,
        signal_consistency=consistency,
    )

    try:
        claim_id = await emit_pipeline_health_claim(
            user_id=user_id,
            open_deal_count=len(open_deals),
            total_value=total_value,
            win_rate_30d=win_rate,
            top_stage=top_stage,
            top_stage_count=top_count,
            confidence=confidence,
        )
        return {
            "success": True,
            "claim_id": str(claim_id),
            "open_deal_count": len(open_deals),
            "total_value": round(total_value, 2),
            "win_rate_30d": round(win_rate, 3),
            "top_stage": top_stage,
            "confidence": round(confidence, 3),
        }
    except Exception as exc:
        logger.exception("snapshot_pipeline_health: claim emit failed")
        return {"error": f"Failed to emit pipeline_health claim: {exc}"}
```

- [ ] **Step 4: Register the new tool**

In `app/agents/tools/hubspot_tools.py` append `snapshot_pipeline_health` to `HUBSPOT_TOOLS`:

```python
HUBSPOT_TOOLS = [
    search_hubspot_contacts,
    get_hubspot_deal_context,
    create_hubspot_contact,
    update_hubspot_deal,
    list_hubspot_deals,
    score_hubspot_lead,
    query_hubspot_crm,
    sync_deal_notes,
    snapshot_pipeline_health,  # Phase 115-03 addition
]
```

The `hubspot_tools` pack is already in `_TOOL_IDS` in `app/agents/sales/tools.py:120` — the new function gets picked up automatically via the manifest.

- [ ] **Step 5: Re-run + commit**

```powershell
uv run pytest tests/unit/agents/tools/test_snapshot_pipeline_health.py -v --tb=short
```

Expected: 2 passed.

```bash
git add app/agents/tools/hubspot_tools.py tests/unit/agents/tools/test_snapshot_pipeline_health.py
git commit -m "feat(115-03): snapshot_pipeline_health tool emits pipeline_health claim"
```

### Task 5: Integration test — full round-trip against local Supabase

**Files:**
- Create: `tests/integration/test_sales_claims_round_trip.py`

End-to-end against the local Supabase stack: emit a lead_score claim, emit again (re-score), verify only one current claim survives the contradicts filter. Then verify `search_claims_semantic(query="lead score", agent_id="sales")` returns the freshest.

- [ ] **Step 1: Write the integration test**

```python
"""Sales claim round-trip against local Supabase."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(v) for v in [
                "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_DB_URL",
            ]
        ),
        reason="Supabase env not configured",
    ),
]


@pytest.mark.asyncio
async def test_lead_score_contradicts_chain_keeps_one_current():
    """Re-scoring a lead 3× produces 3 rows but exactly 1 current (chain head)."""
    from app.agents.sales.claims import emit_lead_score_claim
    from app.services.intelligence import find_claims

    unique = uuid4().hex[:8]
    lead_name = f"Test Lead {unique}"
    company = f"Test Co {unique}"
    email = f"lead-{unique}@example.com"

    id1 = await emit_lead_score_claim(
        lead_name=lead_name, company=company, email=email,
        score=60, band="medium", confidence=0.55,
        framework="BANT", qualified=False, contact_id=None,
    )
    id2 = await emit_lead_score_claim(
        lead_name=lead_name, company=company, email=email,
        score=78, band="medium", confidence=0.70,
        framework="BANT", qualified=True, contact_id=None,
    )
    id3 = await emit_lead_score_claim(
        lead_name=lead_name, company=company, email=email,
        score=90, band="high", confidence=0.85,
        framework="BANT", qualified=True, contact_id=None,
    )

    # Find all lead_score claims for this lead's entity
    from app.services.intelligence import get_or_create_entity
    entity = await get_or_create_entity(
        canonical_name=email,
        entity_type="person",
        domains=["sales"],
    )

    all_claims = await find_claims(
        entity_id=entity,
        agent_id="sales",
        claim_type="lead_score",
        limit=50,
    )
    # All three rows should exist (append-only writes)
    ids = {c.id for c in all_claims}
    assert {id1, id2, id3}.issubset(ids), (
        f"Expected all 3 claim IDs in find_claims result, got {ids}"
    )

    # Apply the supersession filter: a claim is current iff no other claim's
    # `contradicts` includes it.
    superseded = set()
    for c in all_claims:
        superseded.update(c.contradicts)
    current = [c for c in all_claims if c.id not in superseded]

    assert len(current) == 1, (
        f"Expected exactly 1 current claim after supersession filter, "
        f"got {len(current)}: {[c.id for c in current]}"
    )
    assert current[0].id == id3, (
        f"Expected chain head to be id3={id3}, got {current[0].id}"
    )


@pytest.mark.asyncio
async def test_lead_score_appears_in_search_claims_semantic():
    """Freshly emitted lead_score is discoverable via semantic search."""
    from app.agents.sales.claims import emit_lead_score_claim
    from app.services.intelligence import search_claims_semantic

    unique = uuid4().hex[:8]
    company = f"SearchTest {unique}"

    await emit_lead_score_claim(
        lead_name=f"Search Test {unique}", company=company,
        email=f"search-{unique}@example.com",
        score=82, band="high", confidence=0.78,
        framework="BANT", qualified=True, contact_id=None,
    )

    results = await search_claims_semantic(
        query=f"lead score for {company}",
        agent_id="sales",
        claim_type="lead_score",
        top_k=5,
    )

    assert results, "search_claims_semantic returned no results for the new lead"
    found = next(
        (c for c, _sim in results if company in c.finding_text), None
    )
    assert found is not None, (
        f"Expected to find a lead_score claim referencing '{company}' in search results"
    )


@pytest.mark.asyncio
async def test_pipeline_health_claim_round_trip():
    """pipeline_health claim writes and is findable, with 7d expiry."""
    from app.agents.sales.claims import emit_pipeline_health_claim
    from app.services.intelligence import find_claims, get_or_create_entity

    unique = uuid4().hex[:8]
    user_id = f"user-{unique}"

    claim_id = await emit_pipeline_health_claim(
        user_id=user_id,
        open_deal_count=12,
        total_value=180000.0,
        win_rate_30d=0.42,
        top_stage="qualified",
        top_stage_count=7,
        confidence=0.72,
    )

    entity = await get_or_create_entity(
        canonical_name=f"pipeline:{user_id}",
        entity_type="topic",
        domains=["sales"],
    )

    claims = await find_claims(
        entity_id=entity, claim_type="pipeline_health", limit=5,
    )
    assert any(c.id == claim_id for c in claims)
    head = next(c for c in claims if c.id == claim_id)
    assert head.confidence == pytest.approx(0.72)
    assert head.expires_at is not None
    # 7-day expiry sanity check (allow for clock skew)
    from datetime import datetime, timedelta, timezone
    delta = head.expires_at - datetime.now(timezone.utc)
    assert timedelta(days=6) < delta < timedelta(days=8)
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_sales_claims_round_trip.py -v --tb=short
```

Expected: 3 passed.

If the supersession assertion fails (multiple "current" claims), the `find_claims` `limit=1` in `emit_lead_score_claim` is finding the wrong row — verify it returns freshest-first.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_sales_claims_round_trip.py
git commit -m "test(115-03): integration round-trip for lead_score chain + pipeline_health"
```

### Task 6: Document the claim-type vocabulary in the agent README/instructions

**Files:**
- Modify: `app/agents/sales/instructions.md` — append "Claim Emission" section

This makes the claim taxonomy visible to anyone reading the agent's behavior contract, mirroring how Plan 113-03 documented the Data Agent's claim vocabulary.

- [ ] **Step 1: Append the new section**

```markdown

## CLAIM EMISSION (Phase 115-03)

The Sales Intelligence Agent emits three knowledge-graph claim types into `kg_findings`:

| Claim type | When emitted | Mutation pattern | Expiry |
|---|---|---|---|
| `lead_score` | After every LeadQualification annotation (Plan 115-01) | Mutate-via-contradicts — one current per lead, prior claims superseded by `contradicts=[old.id]` | None (supersession handles cleanup) |
| `deal_stage_signal` | On stage change in `sync_deal_notes` | Append-only | 30 days |
| `pipeline_health` | On `snapshot_pipeline_health()` invocation | Append-only | 7 days |

**Important — never present a stale lead score:**
When narrating CRM context for a contact, the agent should query `find_claims(entity_id=<lead_entity>, claim_type="lead_score", limit=50)` and apply the supersession filter (a claim is current iff no other claim's `contradicts` includes it) before quoting. Quoting an older `lead_score` confuses users — they expect "current" to mean "latest re-scoring".

**Pipeline health snapshots:**
Call `snapshot_pipeline_health()` at the START of any pipeline-review conversation. The 7-day TTL means the answer is fresh enough for weekly reviews but won't pollute the graph with daily noise.
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/sales/instructions.md
git commit -m "docs(115-03): document Sales claim taxonomy + supersession protocol"
```

### Task 7: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/agents/sales/claims.py app/agents/sales/agent.py app/agents/tools/hubspot_tools.py tests/unit/agents/sales/test_sales_claim_emission.py tests/unit/agents/sales/test_sales_confidence_wiring.py tests/unit/agents/tools/test_sync_deal_notes_emits_signal.py tests/unit/agents/tools/test_snapshot_pipeline_health.py tests/integration/test_sales_claims_round_trip.py
uv run ruff format app/agents/sales/claims.py app/agents/sales/agent.py app/agents/tools/hubspot_tools.py tests/unit/agents/sales/test_sales_claim_emission.py tests/unit/agents/sales/test_sales_confidence_wiring.py tests/unit/agents/tools/test_sync_deal_notes_emits_signal.py tests/unit/agents/tools/test_snapshot_pipeline_health.py tests/integration/test_sales_claims_round_trip.py --check
```

Fix in place. Commit:

```bash
git add -u
git commit -m "style(115-03): ruff format + lint fixes for plan 115-03 files"
```

- [ ] **Step 2: Phase 115 acceptance — cross-check ALL plans 115-01 through 115-03**

| Phase 115 acceptance line | Verified by |
|---|---|
| Self-improvement engine audit done first (Decision #8) | Plan 115-01 Task 1 |
| `sales_confidence` preset shipped | Plan 115-01 Task 2 |
| All Sales outputs carry `confidence` + `band` | Plan 115-01 Tasks 3-5 |
| HubSpot API rate reduced ≥40% on synthetic load | Plan 115-02 Task 4 |
| TTLs match spec (300s contact/deal, 600s pipeline) | Plan 115-02 Task 2 |
| Two-tier graph (24h) + Redis (5–10min) pattern | Plan 115-02 Tasks 2 + 6 |
| `lead_score` claim shipped with contradicts-chain supersession | Plan 115-03 Task 1 |
| Per-lead claim count bounded — exactly 1 current after N re-scores | Plan 115-03 Task 5 |
| `deal_stage_signal` claim shipped | Plan 115-03 Task 3 |
| `pipeline_health` claim shipped | Plan 115-03 Task 4 |
| `search_claims_semantic` returns Sales claims | Plan 115-03 Task 5 |
| Sales Agent test suite green (regression) | All three plans |
| Lint clean | All three plans Task 7 |

- [ ] **Step 3: Plan 115-03 complete. Phase 115 (Sales Agent adoption) is fully shipped.**

Next planned work: Phase 116 — Compliance Agent adoption (preset + claims, 2 plans, no cache surface). The infrastructure-spine pattern this phase exercised — preset → wiring → cache → claims — is reusable for every subsequent specialized agent in the rollout (114–122).

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `lead_score` claim type emitted | Task 1 |
| `lead_score` mutate-via-contradicts pattern (per-lead history doesn't accumulate) | Task 1, Task 5 |
| `deal_stage_signal` claim type emitted | Task 3 |
| `pipeline_health` claim type emitted | Task 4 |
| Claims carry `confidence` from `sales_confidence` | Tasks 2 + 4 |
| `expires_at` set per spec (30d deal_stage, 7d pipeline_health, none for lead_score) | Tasks 1, 3, 4 |
| `embed=True` for all Sales claim types | Tasks 1, 3, 4 |
| Entity binding: `person` for leads, `topic` for deals + pipelines | Task 1 |
| Claim emit failure does NOT block conversation | Task 2 + Task 3 (fire-and-forget wrappers) |
| Round-trip via `find_claims` + `search_claims_semantic` | Task 5 |
| Phase 113-05 auto-`contradicts` from embedding similarity STILL fires alongside the manual chain | Task 1 + the existing `write_claim` auto-populate path (Plan 113-05) |
| Lint clean | Task 7 |

All spec lines covered.
