# Shared Intelligence Infrastructure — Plan 119-01: Customer Support Preset + Claim Schema + Self-Improvement Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `presets/customer_support.py` with a four-signal confidence formula, design the Customer Support claim taxonomy (`ticket_sentiment`, `csat_signal`, `churn_risk_indicator`), and audit `app/services/self_improvement_engine.py` for entanglement with the current Customer Support agent shape *before* any code changes land that move CS into the shared intelligence package.

**Architecture:** Customer Support has no existing claim schema and no external API surface (it consults the internal `SupportTicketService` + `CustomerHealthService`). The preset weights formalize what `CustomerHealthService.get_health_dashboard` already implies qualitatively — ticket volume, customer engagement, resolution clarity, and recency — and the claim schema design is captured *in this plan* so Plan 119-02 can emit claims against a settled contract. The self-improvement audit (Decision #8 from the rollout design) maps every reference the engine makes to CS-shaped data so we know the blast radius of moving CS outputs onto the shared `Claim` shape.

**Tech Stack:** `app/services/intelligence/confidence.py` (existing — generic scorer), `app/services/intelligence/presets/` (existing — Data + Research siblings), `app/services/intelligence/schemas.py` (existing — `Claim` + `ClaimPayload`), `kg_findings` table (existing, broadened by Phase 112), Phase 113 cross-cutting infra (`search_claims_semantic`, `detect_contradictions`).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 119 — Customer Support Agent adoption

**Out of scope:**
- Claim emission wiring inside `app/agents/customer_support/tools.py` — that's Plan 119-02
- External cache integration — Customer Support has no external API surface (see CLAUDE.md "Customer Support uses internal support_ticket_service" + spec § Phase 119)
- Persona-aware confidence formula variants — single CS preset for all personas; calibration deferred
- LLM-in-the-loop sentiment classification — `ticket.sentiment` is already classified by `SupportTicketService`; this plan reuses that signal as-is
- Changes to `kg_findings` schema — Phase 112 already broadened columns; no migration needed
- Weight calibration from telemetry — preset ships with educated-guess weights per spec § "Out of scope"

---

## File structure

**Create:**
- `app/services/intelligence/presets/customer_support.py` — `customer_support_confidence(...)` + `CUSTOMER_SUPPORT_WEIGHTS`
- `tests/unit/services/intelligence/presets/test_customer_support.py` — preset unit tests (boundary + property)
- `tests/unit/services/intelligence/presets/test_customer_support_schema.py` — claim-schema contract tests (claim_type vocabulary, TTL invariants)
- `docs/superpowers/plans/2026-05-19-self-improvement-audit-119.md` — output artefact from the audit step (Task 4)

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `customer_support_confidence`

**Read (audit-only, no edits):**
- `app/agents/customer_support/agent.py`
- `app/agents/customer_support/tools.py`
- `app/services/customer_health_service.py`
- `app/services/support_ticket_service.py`
- `app/services/self_improvement_engine.py`
- `app/services/skill_experiment_evaluator.py`

---

## Pre-flight context

### Why these four weights

The spec mandates:

```python
CUSTOMER_SUPPORT_WEIGHTS = {
    "ticket_volume_signal":          0.30,
    "customer_response_engagement":  0.25,
    "resolution_outcome_clarity":    0.25,
    "recency":                       0.20,
}
```

Weights sum to 1.0 exactly — the generic scorer (`score_confidence`) does NOT require weights to sum to 1.0 (it normalises in the clamp), but mirroring the Data and Research presets keeps interpretation simple ("each input contributes a known fraction").

Signal definitions (binding — Plan 119-02 must wire matching inputs):

| Signal | Range | Meaning | Source |
|---|---|---|---|
| `ticket_volume_signal` | [0, 1] | `min(1.0, ticket_count / volume_threshold)` — more tickets in the window = stronger signal up to a ceiling (default `volume_threshold=20`). Few tickets means we don't have enough data to assert sentiment/health/churn. | `SupportTicketService.get_ticket_stats().total_count` |
| `customer_response_engagement` | [0, 1] | Fraction of tickets where the customer responded after our reply (= customer is engaging, not ghosting). Defaults to 0.5 when unknown (neutral). | New helper in Plan 119-02 — for now, callers may pass `0.5` |
| `resolution_outcome_clarity` | [0, 1] | `resolved_count / total_count` — fraction of tickets that reached terminal state. Higher = clearer outcomes to learn from. | `SupportTicketService.get_ticket_stats().resolved_count / total_count` |
| `recency` | [0, 1] | `max(0.0, 1.0 - data_age_hours / recency_horizon_hours)` — same shape as Data preset. Default horizon 168 h = 7 days (CS data ages fast). | Computed from latest ticket's `created_at` |

Why `recency_horizon_hours=168` (7 days) instead of 720 (30 days, Data's default): customer sentiment turns over much faster than financial data. A month-old ticket is a poor signal for *this* customer's current state. The 7-day horizon also aligns with `churn_risk_indicator`'s 7-day TTL — by design, a CS claim from a week ago is barely usable.

### Why `ticket_volume_signal` is `min(1.0, ...)` not `1 - 1/n`

The naive "more data is better" curve `1 - 1/n` saturates too slowly: 5 tickets yields 0.8, 20 yields 0.95. For CS, we want clear differentiation across the 1–20 range: 1 ticket = 0.05, 10 tickets = 0.5, 20 tickets = 1.0. That's `min(1.0, n / 20)`.

### Claim-type vocabulary (settled in this plan; Plan 119-02 implements emission)

| Output type | Becomes a Claim? | claim_type | Notes |
|---|---|---|---|
| Per-ticket sentiment classification | Yes | `ticket_sentiment` | One claim per ticket-thread; entity = customer (`canonical_name = customer_email`, `entity_type='person'`). `freshness_at` updates on each ticket interaction. |
| CSAT score per customer (periodic) | Yes | `csat_signal` | One claim per `(customer, period)`; `period` encoded in `finding_text`. New claim per period rather than mutating prior. |
| Churn risk per customer | Yes | `churn_risk_indicator` | One claim per customer per emission. **MUST set `expires_at = now + 7d`** (Plan 119-02 acceptance criterion). |
| Health dashboard counts (e.g., `open_tickets=5`) | No | — | Transient aggregate; lives in dashboard response payload only. |
| Resolution drafted text | No | — | Response payload, not a claim. |
| FAQ suggestion (group of tickets) | No (provisional) | — | Could become `faq_suggestion_claim` later; deferred to keep Plan 119-02 minimal. |

### Why `ticket_sentiment` is per-thread, not per-message

The `SupportTicketService.tickets` table carries a single `sentiment` column at the ticket level; per-message granularity isn't available. Emitting one claim per ticket matches the data we have. If multi-message sentiment trajectory becomes interesting later (e.g., started negative, ended positive), add a `ticket_sentiment_trajectory` claim_type in a follow-up — *don't* try to retrofit per-message into the same claim_type.

### Self-improvement audit scope (Decision #8 from spec)

Per the rollout design's risk register row "Self-improvement engine entangles with old per-agent code paths," every phase's first sub-plan audits the engine *before* any code changes. The audit produces a written artefact (Task 4 output) that:

1. Lists every `customer_support` / `CUS` reference in `self_improvement_engine.py` and `skill_experiment_evaluator.py`.
2. For each reference, classifies it as: **shape-coupled** (engine reads CS-specific fields/methods that 119-02 will change), **id-only** (engine just routes by agent_id string, no shape coupling), or **policy-coupled** (engine applies a rule that mentions CS explicitly).
3. Records whether `docs/self-improvement-policy.md` exists and, if so, surfaces any clause that would block CS-specific changes Plan 119-02 plans to make. If the policy doc is missing, the audit notes that as a finding and Plan 119-02 must NOT auto-modify engine policy without explicit human review.

Acceptance bar (this plan):

- Preset `customer_support_confidence` shipped with the exact weights above.
- Preset clamped to [0.0, 1.0] for all signal inputs (property test).
- Re-export wired through `presets/__init__.py`.
- Claim schema documented in this plan AND captured as a contract test in `test_customer_support_schema.py` so Plan 119-02 can't drift.
- Self-improvement audit artefact committed at `docs/superpowers/plans/2026-05-19-self-improvement-audit-119.md`.

Environment quirks (Windows local-dev):

- `uv run pytest` only works under PowerShell, per `reference_local_dev_env_quirks.md`.
- `supabase` CLI isn't needed for this plan (no migrations).
- `frontend/.env` defaults `NEXT_PUBLIC_API_URL` to prod — irrelevant here; no frontend changes.

---

## Tasks

### Task 1: Pre-flight + read the data the preset must consume

**Files:**
- Read-only: `app/services/customer_health_service.py`, `app/services/support_ticket_service.py`, `app/agents/customer_support/tools.py`

- [ ] **Step 1: Confirm prerequisites**

```powershell
uv run python -c "from app.services.intelligence.confidence import score_confidence, to_band; from app.services.intelligence.presets import data_confidence, research_confidence; print('OK')"
```

Expected: `OK`. If this fails, Phase 113 didn't ship cleanly — stop and escalate.

- [ ] **Step 2: Verify `kg_findings` is broadened**

```powershell
uv run python -c "from app.services.intelligence.schemas import Claim, ClaimPayload; c = Claim.model_json_schema(); assert 'claim_type' in c['properties']; assert 'agent_id' in c['properties']; print('schema OK')"
```

Expected: `schema OK`. Confirms Phase 112's broadening landed.

- [ ] **Step 3: Inventory the exact field shapes the preset must consume**

Read `get_ticket_stats()` in `app/services/support_ticket_service.py` and `get_health_dashboard()` in `app/services/customer_health_service.py`. Record the keys you'll consume in Plan 119-02:

```
get_ticket_stats() returns:
  open_count: int
  resolved_count: int
  total_count: int
  avg_resolution_hours: float | None
  sentiment_breakdown: dict[str, int]    # positive/neutral/negative
  priority_breakdown: dict[str, int]     # low/normal/high/urgent

get_health_dashboard() returns:
  open_tickets: int
  avg_resolution_time_hours: float | None
  sentiment_summary: dict[str, int]
  churn_risk_level: Literal["low", "medium", "high"]
  churn_risk_factors: list[str]
  total_tickets: int
  resolution_rate: float                  # 0.0-100.0 percentage
```

No code change — this is reading + recording so Plan 119-02 doesn't accidentally invent fields that don't exist.

- [ ] **Step 4: Confirm the working tree is clean for Task 2's TDD work**

```powershell
git status -uno
```

Expected: no unrelated modified files. If `supabase/migrations/...` are modified (per the gitStatus header in this conversation), stash or commit them first.

### Task 2: TDD — `customer_support_confidence` preset (failing test → impl → green → commit)

**Files:**
- Create: `tests/unit/services/intelligence/presets/test_customer_support.py`
- Create: `app/services/intelligence/presets/customer_support.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Failing test**

Create `tests/unit/services/intelligence/presets/test_customer_support.py`:

```python
"""Unit tests for customer_support_confidence preset."""

from __future__ import annotations

import pytest


def test_customer_support_confidence_perfect_signals_returns_one():
    """All four signals at 1.0 → confidence saturates at 1.0."""
    from app.services.intelligence.presets import customer_support_confidence

    score = customer_support_confidence(
        ticket_count=20,
        customer_response_engagement=1.0,
        resolution_outcome_clarity=1.0,
        data_age_hours=0.0,
    )
    assert score == pytest.approx(1.0, abs=1e-9)


def test_customer_support_confidence_zero_signals_returns_zero():
    """Zero signal → zero confidence."""
    from app.services.intelligence.presets import customer_support_confidence

    score = customer_support_confidence(
        ticket_count=0,
        customer_response_engagement=0.0,
        resolution_outcome_clarity=0.0,
        data_age_hours=10_000.0,  # very old, recency floors to 0
    )
    assert score == pytest.approx(0.0, abs=1e-9)


def test_customer_support_confidence_typical_dashboard_values():
    """Realistic dashboard inputs return a sane mid-range score."""
    from app.services.intelligence.presets import customer_support_confidence

    # 10 tickets, 60% engagement, 70% resolved, 24h old data
    # ticket_volume_signal = 10/20 = 0.5    × 0.30 = 0.150
    # customer_response_engagement = 0.6     × 0.25 = 0.150
    # resolution_outcome_clarity = 0.7       × 0.25 = 0.175
    # recency = 1 - 24/168 = 0.857           × 0.20 = 0.1714
    # total ≈ 0.6464
    score = customer_support_confidence(
        ticket_count=10,
        customer_response_engagement=0.6,
        resolution_outcome_clarity=0.7,
        data_age_hours=24.0,
    )
    assert 0.60 < score < 0.70


def test_customer_support_confidence_clamped_to_unit_interval():
    """Score always in [0.0, 1.0] for any input."""
    from app.services.intelligence.presets import customer_support_confidence

    # Pathological: ticket_count above threshold + age below zero
    score = customer_support_confidence(
        ticket_count=10_000,  # well above 20
        customer_response_engagement=1.5,  # caller bug: > 1.0
        resolution_outcome_clarity=2.0,  # caller bug: > 1.0
        data_age_hours=-100.0,  # caller bug: negative
    )
    assert 0.0 <= score <= 1.0


def test_customer_support_confidence_volume_threshold_override():
    """Custom volume_threshold flexes the saturation point."""
    from app.services.intelligence.presets import customer_support_confidence

    # With threshold=50, ticket_count=10 yields 0.20 volume signal
    # (vs 0.50 at default threshold=20)
    low_vol = customer_support_confidence(
        ticket_count=10,
        customer_response_engagement=0.0,
        resolution_outcome_clarity=0.0,
        data_age_hours=10_000.0,
        volume_threshold=50,
    )
    high_vol = customer_support_confidence(
        ticket_count=10,
        customer_response_engagement=0.0,
        resolution_outcome_clarity=0.0,
        data_age_hours=10_000.0,
        volume_threshold=20,
    )
    assert low_vol < high_vol  # tighter threshold → lower volume signal


def test_customer_support_confidence_recency_horizon_override():
    """Custom recency_horizon_hours flexes the decay curve."""
    from app.services.intelligence.presets import customer_support_confidence

    # 24h-old data: with horizon=168 → recency=0.857
    # with horizon=24 → recency=0.0
    long_horizon = customer_support_confidence(
        ticket_count=0,
        customer_response_engagement=0.0,
        resolution_outcome_clarity=0.0,
        data_age_hours=24.0,
        recency_horizon_hours=168,
    )
    short_horizon = customer_support_confidence(
        ticket_count=0,
        customer_response_engagement=0.0,
        resolution_outcome_clarity=0.0,
        data_age_hours=24.0,
        recency_horizon_hours=24,
    )
    assert long_horizon > short_horizon


def test_customer_support_confidence_weights_sum_to_one():
    """CUSTOMER_SUPPORT_WEIGHTS sums to exactly 1.0 (sanity)."""
    from app.services.intelligence.presets.customer_support import (
        CUSTOMER_SUPPORT_WEIGHTS,
    )

    assert sum(CUSTOMER_SUPPORT_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)
    assert set(CUSTOMER_SUPPORT_WEIGHTS.keys()) == {
        "ticket_volume_signal",
        "customer_response_engagement",
        "resolution_outcome_clarity",
        "recency",
    }
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_customer_support.py -v --tb=short
```

Expected: `ModuleNotFoundError` or `ImportError: cannot import name 'customer_support_confidence'`. If the test imports succeed, the implementation already exists (shouldn't happen on a clean branch — re-confirm Step 4 of Task 1).

- [ ] **Step 3: Implement `presets/customer_support.py`**

Create `app/services/intelligence/presets/customer_support.py`:

```python
"""Customer-Support-domain confidence preset.

Phase 119-01 — pilots on the Customer Support Agent's outputs from
``app/agents/customer_support/tools.py``.

The formula weights four signals:
- ticket_volume_signal       (0.30): how much support traffic backs the claim?
- customer_response_engagement (0.25): is the customer engaging with our replies,
                                       or going silent (a churn precursor)?
- resolution_outcome_clarity (0.25): fraction of tickets reaching terminal state
                                     — clearer outcomes mean clearer signals.
- recency                    (0.20): how fresh is the underlying ticket data?
                                     CS data ages fast (default horizon 7 days).
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

CUSTOMER_SUPPORT_WEIGHTS: dict[str, float] = {
    "ticket_volume_signal": 0.30,
    "customer_response_engagement": 0.25,
    "resolution_outcome_clarity": 0.25,
    "recency": 0.20,
}


def customer_support_confidence(
    ticket_count: int,
    customer_response_engagement: float,
    resolution_outcome_clarity: float,
    data_age_hours: float,
    *,
    volume_threshold: int = 20,
    recency_horizon_hours: float = 168.0,
) -> float:
    """Compute Customer-Support-domain confidence from ticket-quality signals.

    Args:
        ticket_count: Number of tickets backing the claim (per-customer or
            per-window).
        customer_response_engagement: Fraction in [0.0, 1.0] of tickets where
            the customer responded after our reply. Pass 0.5 when unknown
            (neutral prior). Out-of-range values are clamped.
        resolution_outcome_clarity: Fraction in [0.0, 1.0] of tickets that
            reached terminal state (resolved/closed). Out-of-range values are
            clamped.
        data_age_hours: Age of the freshest ticket interaction in hours.
            Negative values are clamped to 0.
        volume_threshold: Ticket count at which the volume signal saturates
            (default 20).  Lowering this is appropriate for low-volume
            personas where 5 tickets is "a lot".
        recency_horizon_hours: Age at which recency saturates at 0
            (default 168 h = 7 days). CS data turns over fast; a month-old
            ticket is a poor signal for the customer's current state.

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Note — choice of saturation curves:
        ``ticket_volume_signal = min(1.0, ticket_count / volume_threshold)``
        gives clear differentiation across the 1–20 range
        (1 ticket = 0.05, 10 = 0.5, 20 = 1.0). A ``1 - 1/n`` curve was
        considered and rejected because it saturates too fast for CS's
        typical low-volume regime.

    Note — recency horizon vs Data preset:
        Data preset defaults to 720 h (30 days). Customer Support's
        7-day default aligns with the ``churn_risk_indicator`` TTL — by
        design, a CS claim from a week ago is barely usable.
    """
    ticket_volume_signal = min(1.0, max(0, ticket_count) / max(1, volume_threshold))
    engagement = max(0.0, min(1.0, customer_response_engagement))
    outcome_clarity = max(0.0, min(1.0, resolution_outcome_clarity))
    age = max(0.0, data_age_hours)
    recency = max(0.0, 1.0 - min(1.0, age / max(1.0, recency_horizon_hours)))

    return score_confidence(
        inputs={
            "ticket_volume_signal": ticket_volume_signal,
            "customer_response_engagement": engagement,
            "resolution_outcome_clarity": outcome_clarity,
            "recency": recency,
        },
        weights=CUSTOMER_SUPPORT_WEIGHTS,
    )
```

- [ ] **Step 4: Wire re-export in `presets/__init__.py`**

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula — Phase 113 adds data_confidence, Phase 119 adds
customer_support_confidence.
"""

from app.services.intelligence.presets.customer_support import (
    customer_support_confidence,
)
from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = [
    "customer_support_confidence",
    "data_confidence",
    "research_confidence",
]
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_customer_support.py -v --tb=short
```

Expected: all 7 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add app/services/intelligence/presets/customer_support.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/presets/test_customer_support.py
git commit -m "feat(119-01): customer_support_confidence preset + four-signal formula (GREEN)"
```

### Task 3: Claim-schema contract tests (TDD, locks the vocabulary for Plan 119-02)

**Files:**
- Create: `tests/unit/services/intelligence/presets/test_customer_support_schema.py`

The Customer Support agent has NO existing claim schema. To prevent Plan 119-02 from drifting away from the design captured in this plan, lock the schema with contract tests that fail loudly if 119-02 mis-spells a claim_type or forgets the TTL on `churn_risk_indicator`.

- [ ] **Step 1: Write the contract tests**

Create `tests/unit/services/intelligence/presets/test_customer_support_schema.py`:

```python
"""Contract tests for the Customer Support claim schema.

These tests do NOT exercise any production code yet — they lock the
vocabulary and invariants from Plan 119-01 so Plan 119-02 can't drift.

When Plan 119-02 lands and adds a CUSTOMER_SUPPORT_CLAIM_TYPES constant +
emit_churn_risk_indicator helper, these tests will start asserting against
real symbols. Until then the import-guarded tests xfail-skip.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------------------
# 1. Claim-type vocabulary is closed (no typos, no creep)
# ---------------------------------------------------------------------------

EXPECTED_CLAIM_TYPES: frozenset[str] = frozenset(
    {
        "ticket_sentiment",
        "csat_signal",
        "churn_risk_indicator",
    }
)


def test_expected_claim_types_documented_here():
    """Sanity: the three CS claim_types from the design doc are the only three."""
    assert EXPECTED_CLAIM_TYPES == {
        "ticket_sentiment",
        "csat_signal",
        "churn_risk_indicator",
    }


def test_customer_support_claim_types_constant_matches_design():
    """When Plan 119-02 ships CUSTOMER_SUPPORT_CLAIM_TYPES, it must match exactly."""
    try:
        from app.agents.customer_support.intelligence import (
            CUSTOMER_SUPPORT_CLAIM_TYPES,
        )
    except ImportError:
        pytest.xfail("Plan 119-02 has not landed yet")
    assert frozenset(CUSTOMER_SUPPORT_CLAIM_TYPES) == EXPECTED_CLAIM_TYPES


# ---------------------------------------------------------------------------
# 2. churn_risk_indicator MUST always carry expires_at <= now + 7d
# ---------------------------------------------------------------------------


def test_churn_risk_indicator_ttl_is_seven_days():
    """The TTL constant must be exactly 7 days (per spec + this plan)."""
    try:
        from app.agents.customer_support.intelligence import (
            CHURN_RISK_INDICATOR_TTL,
        )
    except ImportError:
        pytest.xfail("Plan 119-02 has not landed yet")

    assert CHURN_RISK_INDICATOR_TTL == timedelta(days=7)


def test_churn_risk_emission_helper_sets_expires_at_within_seven_days():
    """Any helper that emits churn_risk_indicator MUST set expires_at <= now+7d."""
    try:
        from app.agents.customer_support.intelligence import (
            build_churn_risk_payload,
        )
    except ImportError:
        pytest.xfail("Plan 119-02 has not landed yet")

    payload = build_churn_risk_payload(
        customer_email="user@example.com",
        risk_level="high",
        risk_factors=["5 unresolved tickets"],
        confidence=0.72,
    )
    now = datetime.now(timezone.utc)
    assert payload.claim_type == "churn_risk_indicator"
    assert payload.expires_at is not None
    delta = payload.expires_at - now
    # Allow a small tolerance for clock-skew between build and assertion.
    assert timedelta(days=6, hours=23) <= delta <= timedelta(days=7, minutes=5)


# ---------------------------------------------------------------------------
# 3. ticket_sentiment is per-thread (entity_id required, edge_id None)
# ---------------------------------------------------------------------------


def test_ticket_sentiment_attaches_to_customer_entity():
    """ticket_sentiment claims attach to the customer entity, not an edge."""
    try:
        from app.agents.customer_support.intelligence import (
            build_ticket_sentiment_payload,
        )
    except ImportError:
        pytest.xfail("Plan 119-02 has not landed yet")

    payload = build_ticket_sentiment_payload(
        ticket_id="t-123",
        customer_email="user@example.com",
        sentiment="negative",
        confidence=0.55,
    )
    assert payload.claim_type == "ticket_sentiment"
    assert payload.entity_id is not None
    assert payload.edge_id is None
    assert payload.expires_at is None  # ticket_sentiment does NOT expire


# ---------------------------------------------------------------------------
# 4. csat_signal is periodic (one claim per (customer, period))
# ---------------------------------------------------------------------------


def test_csat_signal_finding_text_carries_period():
    """csat_signal text must encode the period so new claims don't shadow prior."""
    try:
        from app.agents.customer_support.intelligence import (
            build_csat_signal_payload,
        )
    except ImportError:
        pytest.xfail("Plan 119-02 has not landed yet")

    payload = build_csat_signal_payload(
        customer_email="user@example.com",
        csat_score=4.3,
        period="2026-Q2",
        confidence=0.8,
    )
    assert payload.claim_type == "csat_signal"
    assert "2026-Q2" in payload.finding_text  # period encoded so we can search


# ---------------------------------------------------------------------------
# 5. agent_id + domain conventions
# ---------------------------------------------------------------------------


def test_all_cs_payloads_use_customer_support_agent_id():
    """Every CS claim payload uses agent_id='customer_support', domain='customer_support'."""
    try:
        from app.agents.customer_support.intelligence import (
            build_churn_risk_payload,
            build_csat_signal_payload,
            build_ticket_sentiment_payload,
        )
    except ImportError:
        pytest.xfail("Plan 119-02 has not landed yet")

    builders = [
        build_ticket_sentiment_payload(
            ticket_id="t-1",
            customer_email="u@e.com",
            sentiment="neutral",
            confidence=0.5,
        ),
        build_csat_signal_payload(
            customer_email="u@e.com",
            csat_score=3.5,
            period="2026-Q1",
            confidence=0.5,
        ),
        build_churn_risk_payload(
            customer_email="u@e.com",
            risk_level="medium",
            risk_factors=["test"],
            confidence=0.5,
        ),
    ]
    for p in builders:
        assert p.agent_id == "customer_support"
        assert p.domain == "customer_support"
```

- [ ] **Step 2: Run — should xfail-skip, not error**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_customer_support_schema.py -v --tb=short
```

Expected output: `2 passed, 7 xfailed` (the two non-import tests pass; the seven import-gated tests xfail until Plan 119-02 lands). If anything *errors* (rather than xfail-skipping), the test setup is wrong — fix before committing.

- [ ] **Step 3: Commit**

```powershell
git add tests/unit/services/intelligence/presets/test_customer_support_schema.py
git commit -m "test(119-01): lock CS claim_type vocabulary + churn TTL contract for 119-02"
```

### Task 4: Self-improvement engine audit (Decision #8) — produce artefact

**Files:**
- Create: `docs/superpowers/plans/2026-05-19-self-improvement-audit-119.md`

This is the load-bearing step per Decision #8 of the rollout design. The audit must happen *before* Plan 119-02 makes shape-coupled changes.

- [ ] **Step 1: Scan for `customer_support` / `CUS` references in the engine**

```powershell
# Engine + evaluator scan
uv run python -c "import re, pathlib; paths = [pathlib.Path('app/services/self_improvement_engine.py'), pathlib.Path('app/services/skill_experiment_evaluator.py')]; [print(f'== {p} ==') or [print(f'{i+1}: {ln.rstrip()}') for i, ln in enumerate(p.read_text(encoding='utf-8').splitlines()) if re.search(r'customer_support|\\bCUS\\b|customer support', ln, re.IGNORECASE)] for p in paths if p.exists()]"
```

Expected: a small number of hits. Per the codebase scan during plan design, the canonical reference is `mapping = {"CUS": "customer_support", ...}` in `self_improvement_engine.py` around line 1588. Any additional hits are findings.

- [ ] **Step 2: Classify each hit**

For each hit found above, classify as:

| Class | Meaning | Action for Plan 119-02 |
|---|---|---|
| **id-only** | Just routes by `agent_id` string, no shape coupling | Safe — 119-02 can change shapes freely |
| **shape-coupled** | Engine reads CS-specific fields/methods that 119-02 will change | DANGER — Plan 119-02 must add a translation layer or update the engine in lockstep |
| **policy-coupled** | Engine applies a CS-specific policy rule | Must consult `docs/self-improvement-policy.md` before touching |

- [ ] **Step 3: Check for `docs/self-improvement-policy.md`**

```powershell
Test-Path docs/self-improvement-policy.md
```

If `True`: read the file and surface any clause that mentions Customer Support, the engine's autonomy boundary, or rollback contract. If `False`: that itself is a finding — Plan 119-02 must NOT auto-modify engine policy without explicit human review.

- [ ] **Step 4: Write the audit artefact**

Create `docs/superpowers/plans/2026-05-19-self-improvement-audit-119.md`:

```markdown
# Self-Improvement Engine — Phase 119 (Customer Support) Audit

**Date:** 2026-05-19
**Auditor:** [agent / human name]
**Phase:** 119 — Customer Support Agent adoption of shared intelligence
**Audit scope:** `app/services/self_improvement_engine.py`, `app/services/skill_experiment_evaluator.py`
**Policy source:** `docs/self-improvement-policy.md` (exists: TRUE / FALSE)

## Summary

[1–2 sentences: total hits found, count by class, blockers for Plan 119-02 (if any).]

## References found

| File | Line(s) | Snippet | Class |
|---|---|---|---|
| `app/services/self_improvement_engine.py` | 1588 | `"CUS": "customer_support",` | id-only |
| ... | ... | ... | ... |

## Policy check

[If `docs/self-improvement-policy.md` exists, summarise any clause that mentions
Customer Support or the autonomy boundary the engine respects. If it does not
exist, state so explicitly and recommend Plan 119-02 avoid auto-modifying
engine policy without human review.]

## Blast radius for Plan 119-02

- Shape-coupled references: [count]
- id-only references: [count]
- Policy-coupled references: [count]

## Verdict

- [ ] Plan 119-02 is safe to proceed as designed
- [ ] Plan 119-02 must add task(s) to update the engine in lockstep
- [ ] Plan 119-02 must pause until policy doc is updated

## Notes for future audits (Phases 120-122)

[Any patterns observed that other rolling-adoption phases should pre-emptively
check.]
```

Fill out every section. Don't leave placeholders.

- [ ] **Step 5: Commit the audit artefact**

```powershell
git add docs/superpowers/plans/2026-05-19-self-improvement-audit-119.md
git commit -m "docs(119-01): self-improvement engine audit for Customer Support adoption (Decision #8)"
```

### Task 5: Cross-check the preset behaves identically to a manual `score_confidence` call

**Files:**
- Modify: `tests/unit/services/intelligence/presets/test_customer_support.py` — append an equivalence test

This guards against a subtle bug class where the preset diverges from the generic scorer.

- [ ] **Step 1: Append the equivalence test**

Append to `tests/unit/services/intelligence/presets/test_customer_support.py`:

```python
def test_customer_support_confidence_equivalent_to_manual_score_confidence():
    """Preset must produce the same result as a hand-rolled score_confidence call."""
    from app.services.intelligence.confidence import score_confidence
    from app.services.intelligence.presets import customer_support_confidence
    from app.services.intelligence.presets.customer_support import (
        CUSTOMER_SUPPORT_WEIGHTS,
    )

    # Realistic mid-range inputs
    ticket_count = 15
    engagement = 0.55
    outcome_clarity = 0.66
    age_hours = 36.0
    volume_threshold = 20
    horizon = 168.0

    expected_volume = min(1.0, ticket_count / volume_threshold)
    expected_recency = max(0.0, 1.0 - age_hours / horizon)

    manual = score_confidence(
        inputs={
            "ticket_volume_signal": expected_volume,
            "customer_response_engagement": engagement,
            "resolution_outcome_clarity": outcome_clarity,
            "recency": expected_recency,
        },
        weights=CUSTOMER_SUPPORT_WEIGHTS,
    )

    via_preset = customer_support_confidence(
        ticket_count=ticket_count,
        customer_response_engagement=engagement,
        resolution_outcome_clarity=outcome_clarity,
        data_age_hours=age_hours,
        volume_threshold=volume_threshold,
        recency_horizon_hours=horizon,
    )

    assert via_preset == pytest.approx(manual, abs=1e-12)
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_customer_support.py -v --tb=short
```

Expected: all 8 tests pass (7 original + the equivalence test).

- [ ] **Step 3: Commit**

```powershell
git add tests/unit/services/intelligence/presets/test_customer_support.py
git commit -m "test(119-01): equivalence test — preset vs manual score_confidence"
```

### Task 6: Lint + ruff format + plan-119-01 acceptance sign-off

- [ ] **Step 1: Lint everything touched**

```powershell
uv run ruff check app/services/intelligence/presets/ tests/unit/services/intelligence/presets/test_customer_support.py tests/unit/services/intelligence/presets/test_customer_support_schema.py
uv run ruff format app/services/intelligence/presets/ tests/unit/services/intelligence/presets/test_customer_support.py tests/unit/services/intelligence/presets/test_customer_support_schema.py --check
```

Expected: clean. If `ruff format --check` fails, run without `--check`, then commit:

```powershell
uv run ruff format app/services/intelligence/presets/ tests/unit/services/intelligence/presets/test_customer_support.py tests/unit/services/intelligence/presets/test_customer_support_schema.py
git add -u
git commit -m "style(119-01): ruff format"
```

- [ ] **Step 2: Type check** (best-effort — `ty` may not be configured for new files yet)

```powershell
uv run ty check app/services/intelligence/presets/customer_support.py
```

Expected: clean. If errors surface, fix in place and amend the equivalent feat commit if it's local-only, OR add a follow-up commit `fix(119-01): satisfy ty type check`.

- [ ] **Step 3: Plan 119-01 acceptance — cross-check this plan's deliverables**

| Plan 119-01 acceptance line | Verified by |
|---|---|
| `customer_support_confidence` preset shipped | Task 2 Step 3 |
| Weights exactly match the design (`0.30/0.25/0.25/0.20`) | Task 2 Step 1 `test_customer_support_confidence_weights_sum_to_one` + Step 3 constant |
| Score clamped to [0.0, 1.0] for any input | Task 2 Step 1 `test_customer_support_confidence_clamped_to_unit_interval` |
| Equivalent to manual `score_confidence` call | Task 5 Step 1 |
| Re-export wired through `presets/__init__.py` | Task 2 Step 4 |
| Claim-type vocabulary captured as contract test | Task 3 Step 1 |
| `churn_risk_indicator` TTL contract = 7 days | Task 3 Step 1 `test_churn_risk_indicator_ttl_is_seven_days` |
| Self-improvement audit artefact committed | Task 4 Step 5 |

- [ ] **Step 4: Plan 119-01 complete. Hand off to Plan 119-02.**

Plan 119-02 may now (a) import `customer_support_confidence` directly, (b) write `app/agents/customer_support/intelligence.py` with the symbols the schema tests xfail-skip on, and (c) wire emission into `app/agents/customer_support/tools.py`. The xfail-skipped tests in `test_customer_support_schema.py` will start passing as 119-02 lands each symbol — that's the implementation roadmap.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `presets/customer_support.py` shipped | Task 2 |
| `customer_support_confidence` four-signal formula with documented weights | Task 2 + module docstring |
| Claim schema designed from scratch (no prior schema for CS) | Task 3 |
| Claim taxonomy = `ticket_sentiment` / `csat_signal` / `churn_risk_indicator` | Task 3 `EXPECTED_CLAIM_TYPES` |
| `churn_risk_indicator` carries `expires_at` (TTL 7d) | Task 3 contract test (passes when 119-02 ships builder) |
| `csat_signal` is periodic per customer | Task 3 contract test `test_csat_signal_finding_text_carries_period` |
| `ticket_sentiment` is per ticket-thread, attaches to customer entity | Task 3 contract test `test_ticket_sentiment_attaches_to_customer_entity` |
| Self-improvement engine audit (Decision #8) before code changes | Task 4 |
| Audit artefact captured at `docs/superpowers/plans/...-self-improvement-audit-119.md` | Task 4 Step 4–5 |
| Score clamped, weights sum-to-1.0 | Task 2 Steps 1+5 |
| Equivalence to generic `score_confidence` | Task 5 |
| Lint clean (ruff check + format) | Task 6 |
| Per-task atomic commits via `git add` + `git commit -m "feat(119-NN): ..."` | Every task's last step |

All Plan 119-01 spec lines covered.
