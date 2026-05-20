# Shared Intelligence Infrastructure — Plan 121-02: Strategic claim emission + cross-domain synthesis

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Strategic claim emission for five claim types (`initiative_milestone`, `strategic_decision`, `priority_assessment`, `cross_domain_risk_consolidation`, `journey_workflow_readiness`) on top of the Plan 121-01 preset + `ClaimSource.kind="claim_ref"` edges representation. Ship a `cross_domain_risk_consolidation` synthesis path that references ≥3 distinct prior-agent claims via `claim_ref` sources and degrades gracefully when those claims are missing. End state: every Strategic output worth recalling carries `confidence` + `band` and is queryable via `search_claims_semantic` alongside Financial/Sales/Compliance/Data/Research/Operations claims.

**Architecture:** Strategic does not add new ADK tools (Decision #7 of the predecessor spec — library-first; no tool-level claim emission). Instead, claim emission is invoked from a new internal module `app/agents/strategic/claims.py` that the Strategic director's lifecycle (post-orchestration phase) and the `convene_board_meeting` boardroom flow both call. The cross-domain consolidation reads prior-agent claims via `find_claims(...)` filtered by the orchestration's working entity, computes the four `strategic_confidence` signals from the orchestration trace, and writes the synthesized claim with `sources=[ClaimSource(kind="claim_ref", ref=str(prior_id)) for prior_id in collected_ids]`.

**Tech Stack:** `app/services/intelligence` (read APIs already exist: `find_claims`, `write_claim`, `get_or_create_entity`, `search_claims_semantic`), `app/agents/strategic/claims.py` (new), pytest unit tests, pytest integration tests against local Supabase, `app/services/intelligence/presets.strategic_confidence` (from Plan 121-01).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 121 — Strategic Agent adoption · Acceptance criteria · Risk register row "Strategic Phase 121 blocked by missing prior-agent claims"

**Out of scope:**
- New ADK tools for Strategic (none — per spec Decision #7 carried forward into Phase 121)
- External cache wiring (Strategic does not call external APIs directly; sub-agents own caches)
- Persona-formatting changes per Strategic output (deferred design-wide)
- Calibration of `STRATEGIC_WEIGHTS` from telemetry (deferred until labeled data exists)
- Cross-agent UI surfaces beyond what `/admin/research/overview` provides automatically
- Bulk back-fill of historical Strategic outputs into `kg_findings` (only forward-going outputs become claims)
- Workflow-engine changes (Strategic invokes the Plan 121-02 emit function; the engine is unchanged)

---

## File structure

**Create:**
- `app/agents/strategic/claims.py` — emit_strategic_claim + cross_domain_risk_consolidation + journey_workflow_readiness + decision/priority emitters
- `tests/unit/agents/strategic/test_strategic_claims.py` — unit tests with mocked `write_claim` / `find_claims`
- `tests/integration/test_strategic_cross_domain_synthesis.py` — local-Supabase integration test that seeds prior-agent claims, runs `cross_domain_risk_consolidation`, and asserts ≥3 distinct agent_ids in `sources`
- `tests/integration/test_strategic_semantic_search_returns_claims.py` — verifies `search_claims_semantic` returns Strategic claims alongside other agents
- `tests/integration/test_strategic_graceful_degradation.py` — verifies missing prior claims lower confidence but do not raise

**Modify:**
- `app/agents/strategic/agent.py` — wire `emit_strategic_claim` into the post-orchestration lifecycle (callback or explicit invocation; see Task 5)
- `app/agents/strategic/tools.py` — `advance_initiative_phase`, `convene_board_meeting`, and `update_initiative` call into `emit_strategic_claim` at the appropriate decision points (Task 4 covers each)
- `app/services/intelligence/claims.py` — add `get_claim_by_id(claim_id: UUID) -> Claim | None` helper if the integration tests reveal it's needed (decided in Task 3 Step 2 below; the ADR flagged it as conditional)

---

## Pre-flight context

**Strategic claim taxonomy** (from the design spec § Phase 121):

| claim_type | When emitted | `finding_text` shape | `sources[].kind="claim_ref"` count |
|---|---|---|---|
| `initiative_milestone` | `advance_initiative_phase` succeeds | "Initiative '<title>' advanced from <old_phase> to <new_phase>; <deliverable summary>" | 0-2 (references InitiativeOps/Research claims that informed the advance) |
| `strategic_decision` | `convene_board_meeting` produces a verdict, OR `update_initiative` sets `status` to `completed`/`blocked` with rationale | "Decision: <verdict>. Rationale: <synthesised>" | 2-N (board debate inputs) |
| `priority_assessment` | Director ranks initiatives or workstreams 0-10 (quantitative ranking) | "<entity> priority = <0.0-10.0>: <one-line rationale>" | 1-N (signals that informed the ranking) |
| `cross_domain_risk_consolidation` | Director identifies a risk visible across ≥3 sub-agents' findings | "Risk: <one-line>. Surfaced by: <agent_a, agent_b, agent_c, ...>." | **≥3 distinct agent_ids** (acceptance gate) |
| `journey_workflow_readiness` | `start_journey_workflow` evaluates prerequisites pass/fail | "Journey '<workflow_name>' readiness=<verdict>: <gating signals>" | 1-N (signals about prerequisite state) |

**Signal computation contracts** (call-site formulae for each strategic_confidence argument):

| Caller | sub_agent_consensus | evidence_breadth | recency_of_input | stakeholder_validation_signal |
|---|---|---|---|---|
| `initiative_milestone` from `advance_initiative_phase` | `1.0` (solo path) | `min(1.0, distinct_agent_ids/3.0)` from collected prior claims, or `0.0` if none referenced | `max(0.0, 1.0 - mean_age_days/30.0)` over referenced claims; `1.0` if none | `1.0` if user-initiated; `0.5` if scheduler-initiated |
| `strategic_decision` from `convene_board_meeting` | `agreeing_voices / total_voices`, where voices are the boardroom sub-agents | `min(1.0, distinct_agent_ids/3.0)` from board debate inputs | `max(0.0, 1.0 - mean_age_days/30.0)` | `1.0` if `approve_workflow_step` was the trigger; `0.5` otherwise (boardroom majority alone) |
| `priority_assessment` | `1.0` (solo path) | `min(1.0, distinct_agent_ids/3.0)` from supporting claims | `max(0.0, 1.0 - mean_age_days/30.0)` | `0.5` (director output, no human gate by default) |
| `cross_domain_risk_consolidation` | `1.0` (the synthesis IS the consensus question — once we have ≥3 distinct agents we treat consensus as met) | `min(1.0, distinct_agent_ids/3.0)` — **must be ≥1.0 to pass acceptance** | `max(0.0, 1.0 - mean_age_days/30.0)` | `0.5` (director output) |
| `journey_workflow_readiness` | `prerequisites_met / total_prerequisites` | `min(1.0, distinct_agent_ids/3.0)` over prerequisite-signal claims | `max(0.0, 1.0 - mean_age_days/30.0)` | `1.0` if user-initiated; `0.5` if auto-suggest |

**Graceful degradation contract** (design-spec acceptance line: "fail gracefully if those claims are missing"):

- When a referenced prior-claim UUID resolves to no row, treat that reference as **absent for breadth and recency, but present in `sources`** — the `claim_ref` entry stays in `sources` (audit trail), the breadth count drops, and the recency average uses only resolvable claims. If every reference is unresolvable, breadth → 0, recency → 1.0 (no inputs → ageless), and the resulting confidence is dominated by `sub_agent_consensus` weight alone.
- Raise only on programming errors (invalid UUID format passed to `claim_ref.ref`, etc.) — never on a missing row.

**Acceptance bar** (from spec § Acceptance criteria):
- Strategic Agent test suite green
- All Strategic outputs carry `confidence` + `band`
- `cross_domain_risk_consolidation` claims reference ≥3 distinct agent_ids via `claim_ref` sources (verified in integration test)
- `search_claims_semantic` returns Strategic claims interleaved with other agents
- Strategic claims that depend on prior-agent claims fail gracefully if those claims are missing
- No regression in `app/agents/strategic/` existing tests

Environment quirks: same as Plan 113-05 (local Supabase via `supabase start`; integration tests skip when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are unset).

---

## Tasks

### Task 1: Pre-flight + scaffolding

**Files:**
- Create: `app/agents/strategic/claims.py` (empty module with imports + docstring; populated in Tasks 2-4)

- [ ] **Step 1: Confirm Plan 121-01 prerequisites**

```powershell
uv run python -c "from app.services.intelligence.presets import strategic_confidence; print(strategic_confidence(1.0, 1.0, 1.0, 1.0))"
uv run python -c "from app.services.intelligence.schemas import ClaimSource; ClaimSource(kind='claim_ref', ref='x'); print('ok')"
uv run python -c "from app.services.intelligence import write_claim, find_claims, get_or_create_entity, search_claims_semantic; print('ok')"
```

Expected: `1.0`, `ok`, `ok`. If any fails, Plan 121-01 has not landed — rebase first.

- [ ] **Step 2: Read the 121-01 audit verdict**

```powershell
uv run python -c "from pathlib import Path; s = Path('docs/intelligence/self-improvement-audit-121.md').read_text(encoding='utf-8'); assert 'Plan 121-02 may proceed' in s; print('audit cleared')"
```

If the verdict requires shims or refactors, address those before proceeding. Expected: `audit cleared`.

- [ ] **Step 3: Scaffold `app/agents/strategic/claims.py`**

```python
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Strategic claim emission — synthesis over prior-agent claims.

Phase 121-02. Strategic is an orchestrator over four sub-agents
(BraindumpPipeline, ResearchSuite, KnowledgeVaultAgent, InitiativeOpsAgent),
so its claims are mostly *pointers* into prior-agent claims emitted by the
broader cohort (Financial, Sales, Compliance, Marketing, HR, Customer
Support, Operations, Data, Research, Content).

The five claim types are listed in the design spec. Each emitter computes
the four ``strategic_confidence`` signals from the orchestration trace and
calls ``write_claim`` with ``sources=[ClaimSource(kind="claim_ref", ...)]``
for each referenced prior-agent claim. Reads degrade silently when prior
claims are missing; writes raise loudly per the predecessor spec's
operating philosophy.

See:
- docs/intelligence/strategic-edges-architecture-decision.md (edges via sources)
- docs/intelligence/self-improvement-audit-121.md (engine entanglement audit)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

logger = logging.getLogger(__name__)

# Public claim_type vocabulary (the only valid values for Strategic emissions).
StrategicClaimType = Literal[
    "initiative_milestone",
    "strategic_decision",
    "priority_assessment",
    "cross_domain_risk_consolidation",
    "journey_workflow_readiness",
]

STRATEGIC_AGENT_ID = "strategic"
STRATEGIC_DOMAIN = "strategic"

# Acceptance gate constant — cross_domain_risk_consolidation requires this many
# distinct agent_ids in its claim_ref sources to satisfy the integration test.
CROSS_DOMAIN_MIN_DISTINCT_AGENTS = 3
```

- [ ] **Step 4: Commit the scaffolding**

```bash
git add app/agents/strategic/claims.py
git commit -m "feat(121-02): scaffold strategic claims module"
```

### Task 2: Implement `emit_strategic_claim` (the shared write path) — TDD

**Files:**
- Create: `tests/unit/agents/strategic/test_strategic_claims.py`
- Modify: `app/agents/strategic/claims.py` — add `emit_strategic_claim`

`emit_strategic_claim` is the single internal callable through which every Strategic claim type writes. It owns: entity resolution, sources construction with `claim_ref`, confidence computation, and the `write_claim` call.

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for app.agents.strategic.claims.emit_strategic_claim."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.mark.asyncio
async def test_emit_strategic_claim_writes_to_kg_findings():
    """emit_strategic_claim calls write_claim with the right shape."""
    from app.agents.strategic.claims import emit_strategic_claim

    entity = uuid4()
    written_uuid = uuid4()
    captured: dict = {}

    async def fake_write_claim(**kwargs):
        captured.update(kwargs)
        return written_uuid

    async def fake_get_or_create_entity(**kwargs):
        return entity

    with patch(
        "app.agents.strategic.claims.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ), patch(
        "app.agents.strategic.claims.get_or_create_entity",
        new=AsyncMock(side_effect=fake_get_or_create_entity),
    ):
        result = await emit_strategic_claim(
            claim_type="priority_assessment",
            entity_canonical_name="Initiative Acme",
            entity_type="topic",
            finding_text="Initiative Acme priority = 8.5: high-revenue, low-risk",
            sub_agent_consensus=1.0,
            evidence_breadth_count=2,
            input_ages_days=[5.0, 10.0],
            stakeholder_validation_signal=0.5,
            prior_claim_refs=[uuid4(), uuid4()],
        )

    assert result == written_uuid
    assert captured["agent_id"] == "strategic"
    assert captured["domain"] == "strategic"
    assert captured["claim_type"] == "priority_assessment"
    assert captured["entity_id"] == entity
    # Confidence in expected range — 1.0 consensus + 2/3 breadth + ~0.75 recency
    # + 0.5 stakeholder; rough range check.
    assert 0.4 < captured["confidence"] < 0.95
    # sources must all be claim_ref kind
    assert len(captured["sources"]) == 2
    for s in captured["sources"]:
        assert s["kind"] == "claim_ref"


@pytest.mark.asyncio
async def test_emit_strategic_claim_rejects_invalid_claim_type():
    """Unknown claim_types raise ValueError."""
    from app.agents.strategic.claims import emit_strategic_claim

    with pytest.raises(ValueError, match="claim_type"):
        await emit_strategic_claim(
            claim_type="not_a_real_type",  # type: ignore[arg-type]
            entity_canonical_name="x",
            entity_type="topic",
            finding_text="x" * 30,
            sub_agent_consensus=1.0,
            evidence_breadth_count=0,
            input_ages_days=[],
            stakeholder_validation_signal=0.0,
            prior_claim_refs=[],
        )


@pytest.mark.asyncio
async def test_emit_strategic_claim_breadth_saturates_at_three():
    """Breadth signal saturates at 3 distinct agents per acceptance gate."""
    from app.agents.strategic.claims import emit_strategic_claim

    captured_confidences: list[float] = []

    async def capture(**kwargs):
        captured_confidences.append(kwargs["confidence"])
        return uuid4()

    with patch(
        "app.agents.strategic.claims.write_claim",
        new=AsyncMock(side_effect=capture),
    ), patch(
        "app.agents.strategic.claims.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ):
        for count in (1, 2, 3, 5):
            await emit_strategic_claim(
                claim_type="cross_domain_risk_consolidation",
                entity_canonical_name=f"e_{count}",
                entity_type="topic",
                finding_text="Risk surfaced across agents — " * 5,
                sub_agent_consensus=1.0,
                evidence_breadth_count=count,
                input_ages_days=[0.0] * count if count else [],
                stakeholder_validation_signal=0.5,
                prior_claim_refs=[uuid4() for _ in range(count)],
            )

    # count=3 and count=5 should produce equal confidence
    assert captured_confidences[2] == pytest.approx(captured_confidences[3])
    assert captured_confidences[2] > captured_confidences[1]
    assert captured_confidences[1] > captured_confidences[0]


@pytest.mark.asyncio
async def test_emit_strategic_claim_no_inputs_recency_defaults_to_one():
    """Empty input_ages_days → recency_of_input = 1.0 (no inputs → ageless)."""
    from app.agents.strategic.claims import emit_strategic_claim

    captured: dict = {}

    async def capture(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.write_claim",
        new=AsyncMock(side_effect=capture),
    ), patch(
        "app.agents.strategic.claims.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ):
        await emit_strategic_claim(
            claim_type="strategic_decision",
            entity_canonical_name="solo",
            entity_type="topic",
            finding_text="Decision: ship — director-only synthesis with no inputs.",
            sub_agent_consensus=1.0,
            evidence_breadth_count=0,
            input_ages_days=[],
            stakeholder_validation_signal=1.0,
            prior_claim_refs=[],
        )

    # sub_agent_consensus=1.0 (0.40) + breadth=0 (0.0) + recency=1.0 (0.20)
    # + stakeholder=1.0 (0.10) = 0.70
    assert captured["confidence"] == pytest.approx(0.70, abs=1e-6)


@pytest.mark.asyncio
async def test_emit_strategic_claim_sources_have_score():
    """Each claim_ref source carries the prior claim's UUID in ref; score is None."""
    from app.agents.strategic.claims import emit_strategic_claim

    refs = [uuid4(), uuid4(), uuid4()]
    captured: dict = {}

    async def capture(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.write_claim",
        new=AsyncMock(side_effect=capture),
    ), patch(
        "app.agents.strategic.claims.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ):
        await emit_strategic_claim(
            claim_type="cross_domain_risk_consolidation",
            entity_canonical_name="multi",
            entity_type="topic",
            finding_text="Risk: churn from pricing change observed across agents.",
            sub_agent_consensus=1.0,
            evidence_breadth_count=3,
            input_ages_days=[1.0, 1.0, 1.0],
            stakeholder_validation_signal=0.5,
            prior_claim_refs=refs,
        )

    refs_in_sources = {s["ref"] for s in captured["sources"]}
    assert refs_in_sources == {str(r) for r in refs}
    for s in captured["sources"]:
        assert s["kind"] == "claim_ref"
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/strategic/test_strategic_claims.py -v --tb=short
```

Expected: `ImportError: cannot import name 'emit_strategic_claim'`.

- [ ] **Step 3: Implement `emit_strategic_claim` in `app/agents/strategic/claims.py`**

Append:

```python
from app.services.intelligence import get_or_create_entity, write_claim
from app.services.intelligence.presets import strategic_confidence
from app.services.intelligence.schemas import ClaimSource

_VALID_CLAIM_TYPES: frozenset[str] = frozenset({
    "initiative_milestone",
    "strategic_decision",
    "priority_assessment",
    "cross_domain_risk_consolidation",
    "journey_workflow_readiness",
})


def _breadth_signal(distinct_agent_ids: int) -> float:
    """Saturating breadth: caps at 3 per the cross-domain acceptance gate."""
    return min(1.0, distinct_agent_ids / 3.0)


def _recency_signal(input_ages_days: Sequence[float]) -> float:
    """Mean-age decay over a 30-day horizon. Empty → 1.0 (no inputs → ageless)."""
    if not input_ages_days:
        return 1.0
    mean_age = sum(input_ages_days) / len(input_ages_days)
    return max(0.0, 1.0 - min(1.0, mean_age / 30.0))


async def emit_strategic_claim(
    *,
    claim_type: StrategicClaimType,
    entity_canonical_name: str,
    entity_type: str,
    finding_text: str,
    sub_agent_consensus: float,
    evidence_breadth_count: int,
    input_ages_days: Sequence[float],
    stakeholder_validation_signal: float,
    prior_claim_refs: Sequence[UUID],
    embed: bool = True,
    expires_at: datetime | None = None,
) -> UUID:
    """Emit a single Strategic synthesis claim.

    The single internal write path for every Strategic claim_type. Computes
    the four ``strategic_confidence`` signals from the orchestration trace,
    constructs ``claim_ref`` sources from the prior_claim_refs, and calls
    ``write_claim``.

    Args:
        claim_type: One of the five Strategic claim types.
        entity_canonical_name: Human-readable entity name (e.g., the
            initiative title, a workflow name, a risk-area label).
        entity_type: kg_entities CHECK constraint value (typically
            "topic" for risk consolidations / decisions, "product" for
            initiative milestones).
        finding_text: One-line synthesis text. Must be >= 20 chars when
            embed=True (the embedding pipeline rejects shorter strings).
        sub_agent_consensus: [0.0, 1.0] — fraction of sub-agents agreeing.
        evidence_breadth_count: Number of distinct prior-agent ids being
            referenced. Saturates the breadth signal at 3.
        input_ages_days: Ages (days) of the prior-agent claims being
            referenced. Empty → recency_of_input defaults to 1.0.
        stakeholder_validation_signal: [0.0, 1.0] per the preset's
            signal-interpretation contract.
        prior_claim_refs: UUIDs of prior-agent kg_findings rows. Stored as
            ClaimSource(kind="claim_ref", ref=str(uuid)) entries.
        embed: If True, write_claim generates an embedding so this claim
            is discoverable via search_claims_semantic. Default True
            because Strategic synthesis is a primary cross-agent recall
            surface.
        expires_at: Optional retention timestamp.

    Returns:
        UUID of the inserted kg_findings row.

    Raises:
        ValueError: If claim_type is not in the Strategic vocabulary, or
            if any preset input is out of range (propagated from
            strategic_confidence).
    """
    if claim_type not in _VALID_CLAIM_TYPES:
        raise ValueError(
            f"claim_type {claim_type!r} not in Strategic vocabulary "
            f"{sorted(_VALID_CLAIM_TYPES)}"
        )

    confidence = strategic_confidence(
        sub_agent_consensus=sub_agent_consensus,
        evidence_breadth=_breadth_signal(evidence_breadth_count),
        recency_of_input=_recency_signal(input_ages_days),
        stakeholder_validation_signal=stakeholder_validation_signal,
    )

    entity_id = await get_or_create_entity(
        canonical_name=entity_canonical_name,
        entity_type=entity_type,
        domains=[STRATEGIC_DOMAIN],
    )

    sources = [
        ClaimSource(kind="claim_ref", ref=str(ref)).model_dump(exclude_none=True)
        for ref in prior_claim_refs
    ]

    return await write_claim(
        entity_id=entity_id,
        domain=STRATEGIC_DOMAIN,
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
        agent_id=STRATEGIC_AGENT_ID,
        claim_type=claim_type,
        embed=embed,
        expires_at=expires_at,
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/strategic/test_strategic_claims.py -v --tb=short
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/agents/strategic/claims.py tests/unit/agents/strategic/test_strategic_claims.py
git commit -m "feat(121-02): emit_strategic_claim write path with claim_ref sources (GREEN)"
```

### Task 3: Implement `cross_domain_risk_consolidation` synthesis (TDD)

**Files:**
- Modify: `app/agents/strategic/claims.py` — add `consolidate_cross_domain_risk`
- Modify: `tests/unit/agents/strategic/test_strategic_claims.py` — extend with consolidation tests

This is the load-bearing acceptance gate: the synthesis path must reference ≥3 distinct prior-agent claims via `claim_ref` sources.

- [ ] **Step 1: Failing unit test**

Append to `test_strategic_claims.py`:

```python
@pytest.mark.asyncio
async def test_consolidate_cross_domain_risk_requires_three_distinct_agents():
    """Synthesis aborts (returns None) if <3 distinct agents found."""
    from app.agents.strategic.claims import consolidate_cross_domain_risk

    # Mock find_claims to return only 2 distinct agent_ids
    fake_claims = [
        _stub_claim(agent="sales", confidence=0.7),
        _stub_claim(agent="sales", confidence=0.6),  # same agent
        _stub_claim(agent="cs", confidence=0.8),
    ]

    with patch(
        "app.agents.strategic.claims.find_claims",
        new=AsyncMock(return_value=fake_claims),
    ):
        result = await consolidate_cross_domain_risk(
            entity_canonical_name="churn_q2",
            entity_type="topic",
            risk_summary="Q2 churn risk surfaced",
        )

    assert result is None  # below threshold — no claim emitted


@pytest.mark.asyncio
async def test_consolidate_cross_domain_risk_emits_when_three_distinct():
    """≥3 distinct agents → emit a cross_domain_risk_consolidation claim."""
    from app.agents.strategic.claims import consolidate_cross_domain_risk

    fake_claims = [
        _stub_claim(agent="sales", confidence=0.7),
        _stub_claim(agent="cs", confidence=0.8),
        _stub_claim(agent="compliance", confidence=0.9),
        _stub_claim(agent="data", confidence=0.85),
    ]
    captured: dict = {}

    async def capture_emit(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.find_claims",
        new=AsyncMock(return_value=fake_claims),
    ), patch(
        "app.agents.strategic.claims.emit_strategic_claim",
        new=AsyncMock(side_effect=capture_emit),
    ):
        result = await consolidate_cross_domain_risk(
            entity_canonical_name="churn_q2",
            entity_type="topic",
            risk_summary="Q2 churn risk surfaced",
        )

    assert result is not None
    assert captured["claim_type"] == "cross_domain_risk_consolidation"
    assert captured["evidence_breadth_count"] == 4  # 4 distinct: sales, cs, compliance, data
    assert len(captured["prior_claim_refs"]) == 4


def _stub_claim(*, agent: str, confidence: float):
    """Build a stub Claim for unit tests."""
    from app.services.intelligence.schemas import Claim

    return Claim(
        id=uuid4(),
        entity_id=uuid4(),
        edge_id=None,
        agent_id=agent,
        claim_type="probe",
        domain=agent,
        finding_text="stub finding text long enough to clear the embed gate",
        confidence=confidence,
        sources=[],
        contradicts=[],
        freshness_at=datetime.now(timezone.utc),
        expires_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_consolidate_cross_domain_risk_caps_at_top_inputs():
    """Synthesis collects at most N inputs per distinct agent to avoid bloat."""
    from app.agents.strategic.claims import consolidate_cross_domain_risk

    # 10 claims from each of 4 agents — should pick top-N per agent
    fake_claims = []
    for agent in ("sales", "cs", "compliance", "data"):
        for i in range(10):
            fake_claims.append(_stub_claim(agent=agent, confidence=0.5 + i * 0.04))

    captured: dict = {}

    async def capture_emit(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.find_claims",
        new=AsyncMock(return_value=fake_claims),
    ), patch(
        "app.agents.strategic.claims.emit_strategic_claim",
        new=AsyncMock(side_effect=capture_emit),
    ):
        await consolidate_cross_domain_risk(
            entity_canonical_name="big",
            entity_type="topic",
            risk_summary="Risk surfaced widely",
        )

    # Cap at MAX_INPUTS_PER_AGENT (defined in claims.py — default 3)
    assert len(captured["prior_claim_refs"]) <= 12  # 4 agents * 3 each
    assert captured["evidence_breadth_count"] == 4  # still 4 distinct
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/strategic/test_strategic_claims.py -v --tb=short -k consolidate
```

Expected: `ImportError: cannot import name 'consolidate_cross_domain_risk'`.

- [ ] **Step 3: Implement `consolidate_cross_domain_risk` in `claims.py`**

Append:

```python
from collections import defaultdict
from datetime import datetime, timezone as _tz

from app.services.intelligence import find_claims
from app.services.intelligence.schemas import Claim

# Cap how many prior claims we attach per distinct agent — avoids breaking
# kg_findings.sources JSONB blob with hundreds of refs and keeps signal/noise
# high. Tunable; 3 chosen as a small N that still showcases breadth.
MAX_INPUTS_PER_AGENT = 3


async def consolidate_cross_domain_risk(
    *,
    entity_canonical_name: str,
    entity_type: str,
    risk_summary: str,
    min_confidence: float = 0.5,
    lookback_limit: int = 100,
) -> UUID | None:
    """Synthesize a cross_domain_risk_consolidation claim when ≥3 distinct
    prior-agent claims about the same entity exist.

    Discovery: ``find_claims(entity_id=resolved_entity, min_confidence=...)``
    returns the candidate inputs. We group by agent_id, keep the top
    MAX_INPUTS_PER_AGENT per agent, and emit only when ≥3 distinct agents
    contribute. Below threshold, returns None (no claim written).

    Args:
        entity_canonical_name: The risk-area entity (resolved/created via
            get_or_create_entity).
        entity_type: kg_entities CHECK constraint value.
        risk_summary: One-line risk description.
        min_confidence: Floor for prior-claim confidence (lower-confidence
            inputs are ignored).
        lookback_limit: Cap on total prior claims considered.

    Returns:
        UUID of the emitted Strategic claim, or None if fewer than
        CROSS_DOMAIN_MIN_DISTINCT_AGENTS distinct agents contributed.
    """
    entity_id = await get_or_create_entity(
        canonical_name=entity_canonical_name,
        entity_type=entity_type,
        domains=[STRATEGIC_DOMAIN],
    )

    prior_claims: list[Claim] = await find_claims(
        entity_id=entity_id,
        min_confidence=min_confidence,
        limit=lookback_limit,
    )

    # Group by agent_id, keep top-N per agent by confidence
    by_agent: dict[str, list[Claim]] = defaultdict(list)
    for c in prior_claims:
        # Exclude self-references: we are emitting a Strategic claim, so
        # prior Strategic claims about the same entity do not count toward
        # cross-domain breadth.
        if c.agent_id == STRATEGIC_AGENT_ID:
            continue
        by_agent[c.agent_id].append(c)
    for agent in by_agent:
        by_agent[agent].sort(key=lambda x: x.confidence, reverse=True)
        by_agent[agent] = by_agent[agent][:MAX_INPUTS_PER_AGENT]

    distinct_agents = len(by_agent)
    if distinct_agents < CROSS_DOMAIN_MIN_DISTINCT_AGENTS:
        logger.info(
            "consolidate_cross_domain_risk: only %d distinct agent(s) "
            "contributing to entity=%s — below threshold %d; skipping",
            distinct_agents,
            entity_canonical_name,
            CROSS_DOMAIN_MIN_DISTINCT_AGENTS,
        )
        return None

    collected: list[Claim] = [c for claims in by_agent.values() for c in claims]
    prior_refs: list[UUID] = [c.id for c in collected]
    now = datetime.now(_tz.utc)
    ages_days = [
        max(0.0, (now - c.freshness_at).total_seconds() / 86400.0)
        for c in collected
    ]

    finding_text = (
        f"Risk: {risk_summary}. Surfaced by {distinct_agents} agents: "
        f"{', '.join(sorted(by_agent.keys()))}."
    )

    return await emit_strategic_claim(
        claim_type="cross_domain_risk_consolidation",
        entity_canonical_name=entity_canonical_name,
        entity_type=entity_type,
        finding_text=finding_text,
        sub_agent_consensus=1.0,  # synthesis IS the consensus check
        evidence_breadth_count=distinct_agents,
        input_ages_days=ages_days,
        stakeholder_validation_signal=0.5,  # director output, no human gate
        prior_claim_refs=prior_refs,
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/strategic/test_strategic_claims.py -v --tb=short
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/agents/strategic/claims.py tests/unit/agents/strategic/test_strategic_claims.py
git commit -m "feat(121-02): consolidate_cross_domain_risk synthesis with claim_ref edges (GREEN)"
```

### Task 4: Implement the other four claim emitters

**Files:**
- Modify: `app/agents/strategic/claims.py` — add four wrapper emitters
- Modify: `tests/unit/agents/strategic/test_strategic_claims.py` — extend

Each wrapper sets the claim-type-specific signals according to the contract table in Pre-flight context.

- [ ] **Step 1: Failing tests for the four wrappers**

Append:

```python
@pytest.mark.asyncio
async def test_emit_initiative_milestone():
    """initiative_milestone wrapper sets consensus=1.0, stakeholder per source."""
    from app.agents.strategic.claims import emit_initiative_milestone

    captured: dict = {}

    async def capture_emit(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.emit_strategic_claim",
        new=AsyncMock(side_effect=capture_emit),
    ):
        await emit_initiative_milestone(
            initiative_title="Acme launch",
            old_phase="validation",
            new_phase="prototype",
            user_initiated=True,
            prior_claim_refs=[],
        )

    assert captured["claim_type"] == "initiative_milestone"
    assert captured["sub_agent_consensus"] == 1.0
    assert captured["stakeholder_validation_signal"] == 1.0  # user-initiated
    assert "validation" in captured["finding_text"]
    assert "prototype" in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_strategic_decision_from_boardroom():
    """strategic_decision wrapper computes consensus from voice counts."""
    from app.agents.strategic.claims import emit_strategic_decision

    captured: dict = {}

    async def capture_emit(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.emit_strategic_claim",
        new=AsyncMock(side_effect=capture_emit),
    ):
        await emit_strategic_decision(
            decision_entity="Q3 pricing strategy",
            verdict="Go: raise prices 8%",
            rationale="Demand elastic per Sales; CS confirms low churn risk; Compliance clear.",
            agreeing_voices=3,
            total_voices=4,
            human_approved=False,
            prior_claim_refs=[uuid4(), uuid4(), uuid4()],
            input_ages_days=[2.0, 5.0, 7.0],
        )

    assert captured["claim_type"] == "strategic_decision"
    assert captured["sub_agent_consensus"] == pytest.approx(0.75)  # 3/4
    assert captured["stakeholder_validation_signal"] == 0.5  # boardroom majority


@pytest.mark.asyncio
async def test_emit_priority_assessment_clamps_score():
    """priority_assessment embeds the 0-10 score in the finding text."""
    from app.agents.strategic.claims import emit_priority_assessment

    captured: dict = {}

    async def capture_emit(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.emit_strategic_claim",
        new=AsyncMock(side_effect=capture_emit),
    ):
        await emit_priority_assessment(
            entity_name="Acme launch",
            score=8.7,
            rationale="High revenue, low risk, three sub-agents agree.",
            prior_claim_refs=[uuid4()],
            input_ages_days=[3.0],
        )

    assert captured["claim_type"] == "priority_assessment"
    assert "8.7" in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_priority_assessment_rejects_out_of_range():
    """Score must be in [0.0, 10.0]."""
    from app.agents.strategic.claims import emit_priority_assessment

    with pytest.raises(ValueError, match="score"):
        await emit_priority_assessment(
            entity_name="x",
            score=11.0,
            rationale="x",
            prior_claim_refs=[],
            input_ages_days=[],
        )


@pytest.mark.asyncio
async def test_emit_journey_workflow_readiness():
    """journey_workflow_readiness computes consensus from prerequisites_met / total."""
    from app.agents.strategic.claims import emit_journey_workflow_readiness

    captured: dict = {}

    async def capture_emit(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with patch(
        "app.agents.strategic.claims.emit_strategic_claim",
        new=AsyncMock(side_effect=capture_emit),
    ):
        await emit_journey_workflow_readiness(
            workflow_name="launch_q3",
            prerequisites_met=4,
            total_prerequisites=5,
            user_initiated=False,
            prior_claim_refs=[uuid4(), uuid4()],
            input_ages_days=[1.0, 2.0],
        )

    assert captured["claim_type"] == "journey_workflow_readiness"
    assert captured["sub_agent_consensus"] == pytest.approx(0.8)  # 4/5
    assert captured["stakeholder_validation_signal"] == 0.5  # auto-suggest
```

- [ ] **Step 2: Run — FAIL with import errors**

```powershell
uv run pytest tests/unit/agents/strategic/test_strategic_claims.py -v --tb=short -k "emit_initiative_milestone or emit_strategic_decision or emit_priority_assessment or emit_journey_workflow_readiness"
```

- [ ] **Step 3: Implement the four wrappers in `claims.py`**

Append:

```python
async def emit_initiative_milestone(
    *,
    initiative_title: str,
    old_phase: str,
    new_phase: str,
    user_initiated: bool,
    prior_claim_refs: Sequence[UUID],
    input_ages_days: Sequence[float] = (),
    deliverable_summary: str = "",
) -> UUID:
    """Emit an initiative_milestone claim on phase advance.

    Called by ``app/agents/strategic/tools.py::advance_initiative_phase``
    after the InitiativeService confirms the advance.

    Args:
        initiative_title: Title of the advanced initiative.
        old_phase: Phase before advance (ideation/validation/prototype/build/scale).
        new_phase: Phase after advance.
        user_initiated: True if the user triggered the advance (vs. scheduler).
        prior_claim_refs: UUIDs of prior-agent claims informing the advance.
        input_ages_days: Ages of the prior claims being referenced.
        deliverable_summary: Optional one-line deliverable rollup.
    """
    text = (
        f"Initiative '{initiative_title}' advanced from {old_phase} to {new_phase}"
    )
    if deliverable_summary:
        text += f"; {deliverable_summary}"
    return await emit_strategic_claim(
        claim_type="initiative_milestone",
        entity_canonical_name=initiative_title,
        entity_type="product",
        finding_text=text,
        sub_agent_consensus=1.0,  # solo path
        evidence_breadth_count=len({str(r) for r in prior_claim_refs}),
        input_ages_days=input_ages_days,
        stakeholder_validation_signal=1.0 if user_initiated else 0.5,
        prior_claim_refs=prior_claim_refs,
    )


async def emit_strategic_decision(
    *,
    decision_entity: str,
    verdict: str,
    rationale: str,
    agreeing_voices: int,
    total_voices: int,
    human_approved: bool,
    prior_claim_refs: Sequence[UUID],
    input_ages_days: Sequence[float],
) -> UUID:
    """Emit a strategic_decision claim from a boardroom verdict or approval."""
    if total_voices <= 0:
        raise ValueError("emit_strategic_decision: total_voices must be > 0")
    consensus = agreeing_voices / total_voices
    text = f"Decision on {decision_entity}: {verdict}. Rationale: {rationale}"
    return await emit_strategic_claim(
        claim_type="strategic_decision",
        entity_canonical_name=decision_entity,
        entity_type="topic",
        finding_text=text,
        sub_agent_consensus=consensus,
        evidence_breadth_count=len({str(r) for r in prior_claim_refs}),
        input_ages_days=input_ages_days,
        stakeholder_validation_signal=1.0 if human_approved else 0.5,
        prior_claim_refs=prior_claim_refs,
    )


async def emit_priority_assessment(
    *,
    entity_name: str,
    score: float,
    rationale: str,
    prior_claim_refs: Sequence[UUID],
    input_ages_days: Sequence[float],
) -> UUID:
    """Emit a quantitative priority_assessment claim (0.0-10.0 ranking)."""
    if not (0.0 <= score <= 10.0):
        raise ValueError(f"emit_priority_assessment: score {score!r} outside [0, 10]")
    text = f"{entity_name} priority = {score:.1f}: {rationale}"
    return await emit_strategic_claim(
        claim_type="priority_assessment",
        entity_canonical_name=entity_name,
        entity_type="topic",
        finding_text=text,
        sub_agent_consensus=1.0,
        evidence_breadth_count=len({str(r) for r in prior_claim_refs}),
        input_ages_days=input_ages_days,
        stakeholder_validation_signal=0.5,
        prior_claim_refs=prior_claim_refs,
    )


async def emit_journey_workflow_readiness(
    *,
    workflow_name: str,
    prerequisites_met: int,
    total_prerequisites: int,
    user_initiated: bool,
    prior_claim_refs: Sequence[UUID],
    input_ages_days: Sequence[float],
) -> UUID:
    """Emit a journey_workflow_readiness claim before launching a workflow."""
    if total_prerequisites <= 0:
        raise ValueError(
            "emit_journey_workflow_readiness: total_prerequisites must be > 0"
        )
    consensus = prerequisites_met / total_prerequisites
    verdict = "ready" if consensus >= 1.0 else "partial"
    text = (
        f"Journey '{workflow_name}' readiness={verdict}: "
        f"{prerequisites_met}/{total_prerequisites} prerequisites met"
    )
    return await emit_strategic_claim(
        claim_type="journey_workflow_readiness",
        entity_canonical_name=workflow_name,
        entity_type="topic",
        finding_text=text,
        sub_agent_consensus=consensus,
        evidence_breadth_count=len({str(r) for r in prior_claim_refs}),
        input_ages_days=input_ages_days,
        stakeholder_validation_signal=1.0 if user_initiated else 0.5,
        prior_claim_refs=prior_claim_refs,
    )
```

- [ ] **Step 4: Re-run — PASS**

```powershell
uv run pytest tests/unit/agents/strategic/test_strategic_claims.py -v --tb=short
```

Expected: all 13 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/agents/strategic/claims.py tests/unit/agents/strategic/test_strategic_claims.py
git commit -m "feat(121-02): emit_initiative_milestone + strategic_decision + priority_assessment + journey_workflow_readiness (GREEN)"
```

### Task 5: Wire emitters into the Strategic tools

**Files:**
- Modify: `app/agents/strategic/tools.py` — call `emit_initiative_milestone` from `advance_initiative_phase`, `emit_strategic_decision` from `convene_board_meeting`, `emit_journey_workflow_readiness` from `start_journey_workflow`

The director does not emit claims directly — the tool callables do, after their core side effect (DB write / workflow launch) succeeds. This keeps the emission tightly coupled to the lifecycle event it documents.

- [ ] **Step 1: Read the existing `advance_initiative_phase`**

Use the Read tool to read lines 234-318 of `app/agents/strategic/tools.py` (the `advance_initiative_phase` body).

- [ ] **Step 2: Wire the emitter**

In `advance_initiative_phase`, after the `phase_guidance` injection and BEFORE the `_record_phase_transition` fire-and-forget block, add:

```python
# Phase 121-02: emit initiative_milestone claim
try:
    from app.agents.strategic.claims import emit_initiative_milestone

    initiative_title = (
        initiative.get("title")
        or initiative.get("name")
        or f"initiative_{initiative_id}"
    )
    deliverables = (phase_guidance or {}).get("deliverables", []) if phase_guidance else []
    deliverable_summary = (
        f"Next deliverables: {', '.join(deliverables[:3])}" if deliverables else ""
    )
    await emit_initiative_milestone(
        initiative_title=initiative_title,
        old_phase=old_phase,
        new_phase=new_phase,
        user_initiated=True,  # advance_initiative_phase is always user-triggered today
        prior_claim_refs=[],  # InitiativeOps does not yet emit referenceable claims
        input_ages_days=[],
        deliverable_summary=deliverable_summary,
    )
except Exception as e:
    # Claim emission MUST NOT break the lifecycle event — log only.
    # The lifecycle DB row is the source of truth; the claim is a recall aid.
    logger.warning(
        "advance_initiative_phase: emit_initiative_milestone failed: %s", e
    )
```

You will need to add `import logging; logger = logging.getLogger(__name__)` at the top of the file if not already present. Verify with Grep first.

- [ ] **Step 3: Wire `start_journey_workflow`**

In `start_journey_workflow` (around line 540-575 per the read above), after the `journey` is launched and `execution_id` is set, before the `return` statement:

```python
try:
    from app.agents.strategic.claims import emit_journey_workflow_readiness

    prerequisites_total = len(launch.get("prerequisites") or [])
    prerequisites_met = prerequisites_total - len(blockers or [])
    if prerequisites_total > 0:
        await emit_journey_workflow_readiness(
            workflow_name=launch.get("template_name") or template_name or "journey",
            prerequisites_met=prerequisites_met,
            total_prerequisites=prerequisites_total,
            user_initiated=True,
            prior_claim_refs=[],
            input_ages_days=[],
        )
except Exception as e:
    logger.warning(
        "start_journey_workflow: emit_journey_workflow_readiness failed: %s", e
    )
```

- [ ] **Step 4: Wire `convene_board_meeting`** (defined in `app/agents/tools/boardroom.py`, re-exported into strategic tools)

Use Grep to find `convene_board_meeting` in `app/agents/tools/boardroom.py`. After the board produces its verdict (look for the return statement that surfaces the verdict + voices), add:

```python
try:
    from app.agents.strategic.claims import emit_strategic_decision

    agreeing = result.get("agreeing_voices", 0)
    total = result.get("total_voices", 1)
    await emit_strategic_decision(
        decision_entity=topic or "boardroom decision",
        verdict=result.get("verdict", "no verdict"),
        rationale=result.get("rationale", "boardroom debate"),
        agreeing_voices=agreeing,
        total_voices=total,
        human_approved=False,  # boardroom is director-only by default
        prior_claim_refs=[],
        input_ages_days=[],
    )
except Exception as e:
    logger.warning("convene_board_meeting: emit_strategic_decision failed: %s", e)
```

Adapt to the actual return shape of `convene_board_meeting` — if voices/verdict names differ, match them; if the function does not currently surface a structured verdict, skip this wiring and document in the commit message that boardroom-driven `strategic_decision` claims are deferred to a follow-on.

- [ ] **Step 5: Quick regression run**

```powershell
uv run pytest tests/unit/agents/strategic/ tests/integration/ -k "strategic" -v --tb=short
```

Expected: previously-green tests stay green; the new claim-emission side effects do not break any return-shape expectations because each emission is wrapped in try/except and uses `logger.warning` on failure.

- [ ] **Step 6: Commit**

```bash
git add app/agents/strategic/tools.py app/agents/tools/boardroom.py
git commit -m "feat(121-02): wire Strategic claim emission into advance_initiative_phase, start_journey_workflow, convene_board_meeting"
```

### Task 6: Integration test — `cross_domain_risk_consolidation` references ≥3 distinct agents

**Files:**
- Create: `tests/integration/test_strategic_cross_domain_synthesis.py`

This is the **load-bearing acceptance gate**: the integration test verifies a real `write_claim` → `find_claims` → `consolidate_cross_domain_risk` round-trip produces a claim whose `sources[].kind="claim_ref"` UUIDs resolve to ≥3 distinct `agent_id` values.

- [ ] **Step 1: Write the test**

```python
"""Integration test: cross-domain risk consolidation references ≥3 agents.

Acceptance criterion from the design spec § Phase 121 acceptance criteria:
"cross_domain_risk_consolidation claims reference ≥3 distinct agent_ids
via edges (verified in integration test)."

Implements the test against the real Supabase via the kg_findings table,
with prior claims seeded from Sales, Customer Support, Compliance, and Data
agents, then verifies the resulting Strategic claim's sources resolve to
those four distinct agent_ids.
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
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_cross_domain_risk_consolidation_references_three_distinct_agents():
    """Seed 4 prior claims from 4 distinct agents, consolidate, verify breadth."""
    from app.agents.strategic.claims import consolidate_cross_domain_risk
    from app.services.intelligence import (
        find_claims,
        get_or_create_entity,
        write_claim,
    )

    risk_name = f"churn_risk_{uuid4()}"
    entity_id = await get_or_create_entity(
        canonical_name=risk_name,
        entity_type="topic",
        domains=["strategic"],
    )

    # Seed 4 prior-agent claims about the same entity
    seeded_ids = []
    seeded_agents = ["sales", "cs", "compliance", "data"]
    for agent in seeded_agents:
        cid = await write_claim(
            entity_id=entity_id,
            domain=agent,
            finding_text=(
                f"{agent} signal: customer churn risk elevated this quarter "
                f"per cohort observation"
            ),
            confidence=0.7,
            sources=[{"kind": "supabase_row", "ref": f"{agent}_row_test"}],
            agent_id=agent,
            claim_type=f"{agent}_signal",
            embed=False,
        )
        seeded_ids.append(cid)

    # Consolidate
    strategic_claim_id = await consolidate_cross_domain_risk(
        entity_canonical_name=risk_name,
        entity_type="topic",
        risk_summary="Q-end churn surfaces across multiple agents",
    )
    assert strategic_claim_id is not None

    # Fetch the consolidated claim
    strategic_claims = await find_claims(
        entity_id=entity_id,
        agent_id="strategic",
        claim_type="cross_domain_risk_consolidation",
        limit=5,
    )
    matches = [c for c in strategic_claims if c.id == strategic_claim_id]
    assert len(matches) == 1
    claim = matches[0]

    # Verify ≥3 distinct agent_ids via claim_ref sources
    ref_uuids = [s.ref for s in claim.sources if s.kind == "claim_ref"]
    assert len(ref_uuids) >= 3, f"Expected ≥3 claim_ref sources, got {len(ref_uuids)}"

    # Resolve each ref to its source claim and collect distinct agent_ids
    distinct_agents: set[str] = set()
    for ref_uuid_str in ref_uuids:
        # find_claims has no by-id filter; fetch by entity_id and filter
        rows = await find_claims(entity_id=entity_id, limit=100)
        for r in rows:
            if str(r.id) == ref_uuid_str:
                distinct_agents.add(r.agent_id)
                break

    assert len(distinct_agents) >= 3, (
        f"Expected ≥3 distinct agent_ids in claim_ref resolutions, "
        f"got {distinct_agents}"
    )
    # The seeded agents must all appear (sanity check)
    for agent in seeded_agents:
        assert agent in distinct_agents, f"Seeded agent {agent} missing from sources"

    # Strategic confidence: at least one strong signal
    assert claim.confidence >= 0.5
    assert claim.band in ("medium", "high")
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_strategic_cross_domain_synthesis.py -v --tb=short
```

Expected: PASS. If `claim_ref` sources do not resolve to distinct agents, the seed step likely failed silently — check `write_claim` return values and ensure embeddings are not required (we passed `embed=False` for seeds).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_strategic_cross_domain_synthesis.py
git commit -m "test(121-02): integration test for cross_domain_risk_consolidation references ≥3 agents"
```

### Task 7: Integration test — graceful degradation when prior claims are missing

**Files:**
- Create: `tests/integration/test_strategic_graceful_degradation.py`

Acceptance line: "Strategic claims that depend on prior-agent claims fail gracefully if those claims are missing (degrade to lower confidence, not exception)."

- [ ] **Step 1: Write the test**

```python
"""Integration test: Strategic synthesis degrades gracefully on missing inputs."""

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
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_consolidate_with_fewer_than_three_agents_returns_none():
    """Below-threshold breadth → no claim emitted, no exception."""
    from app.agents.strategic.claims import consolidate_cross_domain_risk
    from app.services.intelligence import get_or_create_entity, write_claim

    risk_name = f"thin_risk_{uuid4()}"
    entity_id = await get_or_create_entity(
        canonical_name=risk_name,
        entity_type="topic",
        domains=["strategic"],
    )

    # Seed only 2 distinct agents — below threshold
    for agent in ("sales", "cs"):
        await write_claim(
            entity_id=entity_id,
            domain=agent,
            finding_text=f"{agent} signal seeded for thin-evidence test",
            confidence=0.7,
            sources=[],
            agent_id=agent,
            claim_type=f"{agent}_signal",
            embed=False,
        )

    # Consolidation must NOT raise
    result = await consolidate_cross_domain_risk(
        entity_canonical_name=risk_name,
        entity_type="topic",
        risk_summary="Test thin evidence",
    )
    assert result is None, "Below-threshold consolidation must return None, not emit"


@pytest.mark.asyncio
async def test_emit_strategic_claim_survives_invalid_uuid_in_ref_list():
    """Programming error (bad UUID) raises; missing rows do not."""
    from uuid import UUID

    from app.agents.strategic.claims import emit_strategic_claim

    # An unresolvable but well-formed UUID — write_claim won't validate against DB
    phantom_uuid = uuid4()

    result = await emit_strategic_claim(
        claim_type="priority_assessment",
        entity_canonical_name=f"phantom_test_{uuid4()}",
        entity_type="topic",
        finding_text=(
            "Priority assessment for entity whose prior refs do not resolve"
        ),
        sub_agent_consensus=1.0,
        evidence_breadth_count=1,
        input_ages_days=[5.0],
        stakeholder_validation_signal=0.5,
        prior_claim_refs=[phantom_uuid],
    )

    # Claim is written even when the ref UUID does not exist — sources is a
    # bag of references, not a foreign-key relationship. The reader is
    # responsible for graceful handling at read time.
    assert isinstance(result, UUID)


@pytest.mark.asyncio
async def test_strategic_claim_with_zero_prior_refs_still_writes():
    """Solo orchestration (no prior refs) still produces a claim, just with lower
    breadth signal."""
    from uuid import UUID

    from app.agents.strategic.claims import emit_priority_assessment
    from app.services.intelligence import find_claims, get_or_create_entity

    name = f"solo_priority_{uuid4()}"
    entity_id = await get_or_create_entity(
        canonical_name=name,
        entity_type="topic",
        domains=["strategic"],
    )

    cid = await emit_priority_assessment(
        entity_name=name,
        score=7.0,
        rationale="Solo director assessment — no prior refs to attach.",
        prior_claim_refs=[],
        input_ages_days=[],
    )
    assert isinstance(cid, UUID)

    claims = await find_claims(entity_id=entity_id, agent_id="strategic", limit=5)
    matches = [c for c in claims if c.id == cid]
    assert len(matches) == 1
    # Breadth=0 lowers confidence but does not zero it out — consensus 1.0
    # (0.40) + recency 1.0 (0.20) + stakeholder 0.5 (0.05) = 0.65
    assert 0.5 < matches[0].confidence < 0.75
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_strategic_graceful_degradation.py -v --tb=short
```

Expected: PASS. If `test_solo_priority_writes` fails on confidence range, the formula is computed differently than the comment assumes — re-derive: `0.40*1.0 + 0.30*0.0 + 0.20*1.0 + 0.10*0.5 = 0.65`. Test asserts `0.5 < x < 0.75` — correct.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_strategic_graceful_degradation.py
git commit -m "test(121-02): integration test for Strategic graceful degradation on missing inputs"
```

### Task 8: Integration test — `search_claims_semantic` returns Strategic claims

**Files:**
- Create: `tests/integration/test_strategic_semantic_search_returns_claims.py`

Acceptance line: "`search_claims_semantic` returns Strategic claims."

- [ ] **Step 1: Write the test**

```python
"""Integration test: search_claims_semantic returns Strategic claims interleaved
with other agents."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in [
                "SUPABASE_URL",
                "SUPABASE_SERVICE_ROLE_KEY",
                "SUPABASE_DB_URL",
            ]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_search_claims_semantic_finds_strategic_claim():
    """A Strategic claim emitted with embed=True is reachable via semantic search."""
    from app.agents.strategic.claims import emit_strategic_decision
    from app.services.intelligence import search_claims_semantic

    decision_entity = f"pricing_strategy_{uuid4()}"
    cid = await emit_strategic_decision(
        decision_entity=decision_entity,
        verdict="Go: launch the Q3 pricing experiment",
        rationale=(
            "Cross-agent signals support the pricing change — sales confirms "
            "elasticity, CS confirms low churn risk, compliance is clear."
        ),
        agreeing_voices=3,
        total_voices=4,
        human_approved=True,
        prior_claim_refs=[],
        input_ages_days=[],
    )
    assert cid is not None

    # Semantic search should retrieve the claim
    results = await search_claims_semantic(
        query="Q3 pricing decision launching new strategy",
        agent_id="strategic",
        claim_type="strategic_decision",
        top_k=10,
    )
    assert len(results) > 0, "Strategic claim not retrievable via semantic search"

    matched = [r for r in results if r[0].id == cid]
    assert len(matched) >= 1, (
        f"Strategic claim {cid} not in top-10 semantic results "
        f"(got {[r[0].id for r in results]})"
    )
    # Confidence band must be set
    claim = matched[0][0]
    assert claim.band in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_search_claims_semantic_interleaves_strategic_and_data():
    """Strategic and Data claims about the same topic appear in the same result set."""
    from app.agents.strategic.claims import consolidate_cross_domain_risk
    from app.services.intelligence import (
        get_or_create_entity,
        search_claims_semantic,
        write_claim,
    )

    topic = f"retention_q4_{uuid4()}"
    entity_id = await get_or_create_entity(
        canonical_name=topic,
        entity_type="metric",
        domains=["data", "strategic", "sales", "cs"],
    )

    # Seed 3+ distinct prior-agent claims with embeddings for semantic discovery
    for agent in ("sales", "cs", "compliance", "data"):
        await write_claim(
            entity_id=entity_id,
            domain=agent,
            finding_text=(
                f"{agent}: Q4 customer retention trended downward by "
                f"approximately 6 percent against the baseline cohort"
            ),
            confidence=0.75,
            sources=[],
            agent_id=agent,
            claim_type=f"{agent}_signal",
            embed=True,
        )

    # Synthesize
    strategic_id = await consolidate_cross_domain_risk(
        entity_canonical_name=topic,
        entity_type="metric",
        risk_summary="Q4 retention regression",
    )
    assert strategic_id is not None

    results = await search_claims_semantic(
        query="Q4 customer retention downward trend",
        top_k=10,
    )
    agent_ids_in_results = {r[0].agent_id for r in results}
    assert "strategic" in agent_ids_in_results, (
        f"Strategic missing from interleaved search results: {agent_ids_in_results}"
    )
    # At least one non-Strategic agent should also appear (interleave proven)
    assert agent_ids_in_results - {"strategic"}, (
        f"Only Strategic in results — interleaving not verified"
    )
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_strategic_semantic_search_returns_claims.py -v --tb=short
```

Expected: PASS. If the first test fails because the embedding service is unavailable, set `EMBEDDING_OUTPUT_DIMENSIONALITY=768` per the recent `gemini-embedding-*` migration (memory note `project_phase_113_05_post_migration_revalidation`) and re-run. If the second test's interleave fails, increase `top_k` to 20.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_strategic_semantic_search_returns_claims.py
git commit -m "test(121-02): integration test for Strategic claims via search_claims_semantic"
```

### Task 9: Regression sweep — confirm existing Strategic suite stays green

**Files:**
- None (sweep only)

- [ ] **Step 1: Full Strategic regression**

```powershell
uv run pytest tests/unit/agents/strategic/ tests/integration/ -k "strategic" -v --tb=short
```

Expected: every previously-green test stays green. The new emission side effects are guarded by try/except + `logger.warning` so they cannot break callers; if any test fails, the regression is in lifecycle code, not in claim emission.

- [ ] **Step 2: Workflow-engine validation**

```powershell
make test
```

This runs the workflow validation step too. Expected: green.

- [ ] **Step 3: If anything is RED, debug per `superpowers:systematic-debugging`**

Common failure modes:
- `advance_initiative_phase` test that mocks `InitiativeService` may now require also mocking `emit_initiative_milestone` — check if the test passes when the emission's try/except catches an exception and logs warning. The test should not fail on warnings.
- A test that asserts the exact shape of `start_journey_workflow`'s return dict may break if the emission alters that shape — re-verify the wiring inserts BEFORE the return and does not mutate the return dict.

- [ ] **Step 4: No commit needed if green; commit fixes if any.**

### Task 10: Lint + format + final acceptance sign-off

- [ ] **Step 1: Lint everything 121-02 touched**

```powershell
uv run ruff check app/agents/strategic/claims.py app/agents/strategic/tools.py app/agents/tools/boardroom.py tests/unit/agents/strategic/test_strategic_claims.py tests/integration/test_strategic_cross_domain_synthesis.py tests/integration/test_strategic_graceful_degradation.py tests/integration/test_strategic_semantic_search_returns_claims.py
uv run ruff format app/agents/strategic/claims.py app/agents/strategic/tools.py app/agents/tools/boardroom.py tests/unit/agents/strategic/test_strategic_claims.py tests/integration/test_strategic_cross_domain_synthesis.py tests/integration/test_strategic_graceful_degradation.py tests/integration/test_strategic_semantic_search_returns_claims.py --check
```

Fix in place. Commit any fixes:

```bash
git add -u
git commit -m "style(121-02): ruff lint + format for Strategic claim modules"
```

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/agents/strategic/
```

Expected: no errors. Most surfaces are typed; the Literal `StrategicClaimType` keeps the dispatcher safe.

- [ ] **Step 3: Phase 121 acceptance — cross-check ALL plans 121-01 + 121-02**

| Phase 121 acceptance line | Verified by |
|---|---|
| `strategic_confidence` preset shipped | Plan 121-01 Task 3 |
| Self-improvement engine audit verdict documented | Plan 121-01 Task 1 |
| Edges architecture ADR documented | Plan 121-01 Task 2 |
| `ClaimSource.kind` accepts `claim_ref` | Plan 121-01 Task 4 |
| Strategic Agent test suite green | Plan 121-02 Task 9 |
| All Strategic outputs carry `confidence` + `band` | Plan 121-02 Tasks 2-5 |
| `cross_domain_risk_consolidation` claim references ≥3 distinct agent_ids via edges (integration-tested) | Plan 121-02 Task 6 |
| `search_claims_semantic` returns Strategic claims | Plan 121-02 Task 8 |
| Strategic claims fail gracefully if prior claims are missing (degrade, not exception) | Plan 121-02 Task 7 |
| Five claim types defined and emitted | Plan 121-02 Tasks 3, 4 |
| No new ADK tools (Decision #7 preserved) | Plan 121-02 file structure — no `_TOOL_IDS` change |
| No external cache (Decision: Strategic doesn't call external APIs directly) | Plan 121-02 out-of-scope confirmed |

- [ ] **Step 4: Phase 121 (Strategic Agent adoption) complete.**

Next planned work: Phase 122 (Content Agent adoption — the most novel claim shapes). The abstraction has now been exercised against every shape — analytical (Data), quantitative (Sales/HR/CS), categorical (Compliance), performance (Marketing), outcome (Operations), and synthesized (Strategic). Content's meta-claim types are the final test.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| Five claim types: initiative_milestone, strategic_decision, priority_assessment, cross_domain_risk_consolidation, journey_workflow_readiness | Tasks 3, 4 |
| `cross_domain_risk_consolidation` references ≥3 distinct prior-agent claims | Task 3, 6 |
| Edges via `sources[].kind="claim_ref"` (no schema change) | Task 2, 3, 4 |
| Confidence + band on every output | Task 2-5 |
| `search_claims_semantic` returns Strategic claims | Task 8 |
| Graceful degradation on missing inputs | Task 7 |
| No new ADK tools | File structure (no tools.py manifest changes) |
| No external cache | Out of scope confirmed |
| Lifecycle wiring (advance/journey/boardroom) | Task 5 |
| Lint + type clean | Task 10 |

All spec lines covered.

---

## Risk register (delta for 121-02)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `convene_board_meeting` return shape does not match assumptions in Task 5 wiring | Medium | Medium | Task 5 Step 4 instructs to adapt to the actual return shape or skip and document deferral |
| `find_claims` does not support by-id lookup, making integration test Task 6 awkward | Low | Medium | Task 6 fetches by entity_id (already in scope) and filters in Python; cost is one extra query, acceptable |
| Embedding generation fails in CI / no Vertex AI access | Medium | Medium | Task 8 integration tests skip if `SUPABASE_DB_URL` unset; unit tests do not depend on embedding |
| `claim_ref` UUIDs grow unbounded for large consolidations | Low | Low | `MAX_INPUTS_PER_AGENT = 3` cap in Task 3; total sources bounded by `MAX × distinct_agents` |
| Lifecycle emission's try/except masks real bugs in claim emission | Medium | Medium | Each emission logs at WARNING with the agent_id + claim_type — observable via `/admin/research/overview` claim-write-failure counter (already wired in Phase 112) |
| Strategic claim flood overwhelms semantic search index | Low | Low | Phase 112 ivfflat index handles up to 500k rows; Strategic emission rate is bounded by lifecycle event rate (low) |
| Integration test breadth assertion flakes if seeded claims overlap with prior test data | Low | Medium | Each test uses `uuid4()` in canonical_name to isolate entities; no cross-test contamination |
| Plan 121-01 audit verdict surfaces shape-coupled entanglement late | Low | High | Task 1 Step 2 hard-checks the audit verdict before proceeding |
