# Shared Intelligence Infrastructure — Plan 118-02: HR Claim Emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire HR claim emission into the recruitment toolchain. Every meaningful HR action (`add_candidate`, `update_candidate_status`, `generate_interview_questions`, `get_hiring_funnel`) produces a `kg_findings` row with the confidence band from Plan 118-01's `hr_confidence` preset. `candidate_signal` claims follow the **update-freshness-at-on-each-interaction, expire-on-terminal-status** lifecycle, which is structurally different from the new-claim-with-contradicts pattern Sales uses for lead scores (Plan 115-03) — this is the central novel pattern of Phase 118.

**Architecture:** Emission lives in a new module `app/agents/hr/claims.py` (separate from `tools.py` so the tool callables stay focused on their original business logic and the claim side-effect is a single import). Each existing tool gains a one-line call to an emitter helper. The emitter:

1. Resolves the candidate / requisition entity via `get_or_create_entity` (uses Plan 118-01's canonical-name helpers).
2. Looks up the existing `candidate_signal` claim (if any) via `find_claims(entity_id=..., claim_type='candidate_signal', limit=1)`.
3. If found AND status is non-terminal → **UPDATE** that row's `freshness_at = now()` and `confidence` / `finding_text` / `sources` payload (single PATCH against `kg_findings`).
4. If found AND new status IS terminal → **UPDATE** that row to set `expires_at = now()` and persist the final confidence; do not refresh `freshness_at` (the claim is now sealed).
5. If not found → **INSERT** a new claim via `write_claim(...)`.

`hiring_pipeline_state` claims always take path (5) — append-only snapshots with `expires_at = now() + 7d`.

The "UPDATE freshness_at" path is the deviation from Sales 115-03's pattern. Sales' `lead_score` accumulates as new claim rows with `contradicts=[old_id]`, so each interaction creates a new row. HR's `candidate_signal` would explode the row count (a hot candidate gets 30+ touchpoints) AND lose the "single source of truth per (candidate, job)" property recruiters depend on. So HR mutates in place. To do that we need an UPDATE-claim helper that doesn't currently exist in `app/services/intelligence/claims.py`.

**Tech Stack:** Existing `app/services/intelligence/` (Phase 112/113), `app/agents/hr/claims.py` (new), Pydantic v2, asyncpg/postgrest, pytest.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 118 — HR Agent adoption.

**Out of scope:** Modifying confidence band thresholds (Plan 118-01 uses the defaults from `to_band`). Bias-fairness logic integration (the HR instructions already enforce guardrails; confidence does NOT gate hiring decisions). External ATS ingestion (e.g., Greenhouse / Lever sync). Onboarding-state claims (`onboarding_completion_state` deferred from Phase 118 scope). UI surface for confidence band on the recruitment dashboard (admin UI work, separate phase).

---

## File structure

**Create:**
- `app/agents/hr/claims.py` — emitter helpers
- `tests/unit/agents/hr/test_hr_claim_emission.py` — unit tests (mocked Supabase + embedding)
- `tests/integration/agents/hr/test_hr_claim_lifecycle.py` — integration tests against real Supabase
- `tests/integration/agents/hr/__init__.py` — empty init if missing

**Modify:**
- `app/services/intelligence/claims.py` — add `update_claim_freshness(claim_id, *, confidence?, finding_text?, sources?, expires_at?)`
- `app/services/intelligence/__init__.py` — re-export `update_claim_freshness`
- `app/agents/hr/tools.py` — call `claims.emit_candidate_signal(...)` from `add_candidate`, `update_candidate_status`, `generate_interview_questions`; call `claims.emit_hiring_pipeline_state(...)` from `get_hiring_funnel`

**Read-only (reference):**
- `app/services/intelligence/presets/hr_claim_schema.py` (Plan 118-01)
- `app/services/intelligence/presets/hr.py` (Plan 118-01)
- `docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md` (Plan 118-01)

---

## Pre-flight context

### The freshness_at UPDATE pattern (the load-bearing novelty)

`app/services/intelligence/claims.py` currently has:

- `write_claim(...)` — append-only INSERT, returns new UUID.
- `write_claims(...)` — bulk INSERT.
- `find_claims(...)` — read.
- `claim_freshness_hours(...)` — read latest row's age.
- `search_claims_semantic(...)` — pgvector read.
- `detect_contradictions(...)` — pgvector read used by `write_claim`.

There is **no UPDATE path**. Phase 112 deliberately omitted one because every other claim_type emitted so far is append-only (Research multi-track findings, Data cohort summaries — both never mutate). HR's `candidate_signal` is the first claim_type with a mutate-in-place lifecycle.

We add `update_claim_freshness(claim_id, *, confidence=None, finding_text=None, sources=None, expires_at=None)`:

- Mutates exactly the row identified by `claim_id`.
- Always sets `freshness_at = now()` UNLESS `expires_at` is being set (terminal transition) — in that case `freshness_at` stays as it was and only `expires_at` is updated, marking the claim sealed at its last refresh.
- Optional `confidence` / `finding_text` / `sources` get UPDATE'd; None means leave unchanged.
- Re-embeds if `finding_text` changed AND the existing row had `embedding IS NOT NULL`.
- Returns the updated row's `freshness_at` so the caller can log it.

This is the single most contagious thing in Plan 118-02 — once it exists, Sales / Customer Support / Compliance can use it for their own update-in-place claim types if they want to. Phase 118 is the spec's chosen vehicle for introducing it because HR's CRUD shape makes the use case unambiguous.

### Why HR's pattern differs from Sales 115-03

Sales' lead score uses `contradicts=[old_lead_score_id]` and writes a new row per recalculation. This gives:

- Full audit trail of every score over time (compliance + sales-ops requirement).
- The contradicts edge auto-populates via `detect_contradictions` (Plan 113-05) — embedding similarity flags the prior row.
- Latest-row-wins is enforced via `ORDER BY freshness_at DESC LIMIT 1`.

HR's `candidate_signal` would semantically *want* the same audit trail, but the cardinality is wrong: a single candidate at the offer stage might have 30+ touchpoints (4-5 interviews + reference checks + take-home review + multiple status nudges). Writing 30 rows per candidate-job pair × hundreds of candidates × concurrent reqs = bloat that dilutes `find_claims` results without informational value.

**Trade-off accepted:** HR loses the per-touchpoint audit trail in `kg_findings`. The audit trail still exists in `recruitment_candidates` + `interaction_logs` (the existing operational tables). `kg_findings` holds the *latest synthesized signal* per candidate-job pair, not the history.

If this trade-off proves wrong in production (e.g., recruiters need to see "when did this candidate's confidence drop"), the fix is to add an `kg_findings_history` shadow table in a future phase, not to switch HR to the contradicts pattern.

### Emission points

| Tool / event | claim_type | Action | Why |
|---|---|---|---|
| `add_candidate(name, email, job_id, ...)` | `candidate_signal` | UPSERT (always create — first interaction) | Initial baseline. `interviewer_score_sigma=0` (no interviews yet), `assessment_battery_coverage=0`. |
| `update_candidate_status(candidate_id, status='interviewing')` | `candidate_signal` | UPDATE `freshness_at` + recompute confidence | Non-terminal transition. |
| `update_candidate_status(candidate_id, status='offer')` | `candidate_signal` | UPDATE `freshness_at` + recompute confidence | Still non-terminal — `offer` means offer extended, not accepted. |
| `update_candidate_status(candidate_id, status='hired')` | `candidate_signal` | UPDATE — set `expires_at=now()`, persist final confidence | **Terminal transition.** Lifecycle ends here. |
| `update_candidate_status(candidate_id, status='rejected')` | `candidate_signal` | UPDATE — set `expires_at=now()`, persist final confidence | **Terminal transition.** Lifecycle ends here. |
| `generate_interview_questions(job_id, ...)` | (no claim) | nothing | Rubric generation doesn't change candidate signal. |
| `get_hiring_funnel(job_id)` | `hiring_pipeline_state` | INSERT new snapshot, `expires_at = now() + 7d` | Append-only periodic snapshot. |
| `auto_generate_onboarding(candidate_id)` | (no claim) | nothing | Lifecycle has already ended at `update_candidate_status(status='hired')`. |

The `update_candidate_status` paths cover all 5 status transitions because of the lifecycle rule: non-terminal → freshness refresh; terminal → seal.

### Computing the four `hr_confidence` inputs from existing data

The preset signature is:

```python
hr_confidence(
    non_null_fields: int,
    expected_fields: int,
    interviewer_score_sigma: float,
    latest_touchpoint_age_hours: float,
    assessments_completed: int,
    assessments_planned: int,
)
```

For each candidate-job pair, the emitter computes inputs as:

| Input | Computation |
|---|---|
| `non_null_fields` | `sum(1 for v in candidate_row.values() if v is not None)` over a fixed projection (name, email, resume_url, job_id, status, current_stage, source, referral_id, salary_expectation, start_date_target). |
| `expected_fields` | `10` (the projection's cardinality). |
| `interviewer_score_sigma` | Stddev of `interviewer_rubric_scores` for this candidate-job pair. If there are no interviews yet, defaults to `0.0` (no disagreement signal — single-source consensus by definition). Note: this is *generous* at the cold-start; the recency signal will dominate. |
| `latest_touchpoint_age_hours` | `(now() - max(candidate.updated_at, latest_interview.updated_at, latest_status_change.created_at)) / 3600`. |
| `assessments_completed` | Count from a (future) `recruitment_assessments` table. **For Phase 118, default to `0`.** |
| `assessments_planned` | Count from the (future) `recruitment_assessments` table for this job. **For Phase 118, default to `0` so the `assessment_battery_coverage` signal becomes 1.0 (no-battery = no penalty per Plan 118-01).** |

The "assessments default 0/0" is an **explicit Phase 118 simplification**. When `recruitment_assessments` ships, the emitter's signal computation updates without touching any other code (the preset's coverage-defaults-to-1.0-when-planned-is-0 logic already accommodates this).

### `finding_text` shape for `candidate_signal`

The `finding_text` field is human-readable and is what `search_claims_semantic` embeds. Format:

```
Candidate <Name> for <Job Title> at <stage>; <N> interviews submitted; latest activity <age_h>h ago.
Confidence band: <band>.
```

Example:
```
Candidate Alice Yu for Senior Sales Engineer at interviewing; 3 interviews submitted; latest activity 8h ago.
Confidence band: medium.
```

This shape lets cross-agent semantic search ("who applied for the sales engineer role?") match against the candidate name AND the job title, and the band tag lets the executive agent filter on confidence in a follow-up structured query.

### `finding_text` shape for `hiring_pipeline_state`

```
Hiring pipeline for <Job Title> [job:<job_id>]: applied=<n> screening=<n> interviewing=<n> offer=<n> hired=<n> rejected=<n>. Snapshot at <iso>.
```

No name, just structured counts — the recruiter / executive needs the numbers, not prose.

### Environment quirks

Same as Plan 118-01:
- `uv run` only.
- Local Supabase: `supabase start`; `SUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres`.
- Integration tests use `supabase.create_client(url, key)` directly to bypass the conftest mock (already the pattern in `claims.py`).
- The kg_findings table accepts UPDATE via PostgREST PATCH — no special RPC needed for the new `update_claim_freshness` helper.

---

## Tasks

### Task 1: Pre-flight + read Plan 118-01 audit findings

**Files:**
- Read-only: `docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md`
- Read-only: `app/services/intelligence/presets/hr.py`, `app/services/intelligence/presets/hr_claim_schema.py`

- [ ] **Step 1: Confirm Plan 118-01 deliverables are present**

```powershell
uv run python -c "from app.services.intelligence.presets import hr_confidence; from app.services.intelligence.presets.hr_claim_schema import CANDIDATE_SIGNAL, HIRING_PIPELINE_STATE, TERMINAL_CANDIDATE_STATUSES, candidate_entity_canonical_name; print('118-01 surface OK')"
```

Expected: prints `118-01 surface OK`.

- [ ] **Step 2: Read the audit notes**

```bash
cat docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md
```

Confirm:
- Q1-Q4 each have findings (not blank).
- The "Plan 118-02 must..." column has explicit constraints.
- Policy compliance checklist boxes can all be honored by this plan.

If any constraint says "Plan 118-02 must change `self_improvement_engine.py`" — **stop** and add an explicit prerequisite task to this plan before any code changes. Otherwise proceed.

- [ ] **Step 3: No commit — preflight only.**

### Task 2: Implement `update_claim_freshness` (the load-bearing UPDATE primitive)

**Files:**
- Create: `tests/unit/services/intelligence/test_update_claim_freshness.py`
- Modify: `app/services/intelligence/claims.py`
- Modify: `app/services/intelligence/__init__.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for update_claim_freshness."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_update_claim_freshness_sets_freshness_at_now():
    """A simple update without expires_at refreshes freshness_at to now."""
    from app.services.intelligence.claims import update_claim_freshness

    claim_id = uuid4()
    captured = {}

    fake_client = MagicMock()

    def capture_update(payload):
        captured["payload"] = payload
        result = MagicMock()
        result.data = [
            {
                "id": str(claim_id),
                "freshness_at": "2026-05-19T12:00:00+00:00",
            }
        ]
        return MagicMock(eq=lambda *a, **kw: MagicMock(execute=lambda: result))

    fake_client.table = MagicMock(
        return_value=MagicMock(update=capture_update)
    )

    with patch(
        "app.services.intelligence.claims._get_supabase_client",
        return_value=fake_client,
    ):
        await update_claim_freshness(claim_id)

    assert "freshness_at" in captured["payload"]
    # We don't assert the exact timestamp; just that the helper passed it
    assert captured["payload"]["freshness_at"] is not None


@pytest.mark.asyncio
async def test_update_claim_freshness_with_expires_at_seals_claim():
    """Terminal transition: expires_at is set, freshness_at is NOT refreshed."""
    from app.services.intelligence.claims import update_claim_freshness

    claim_id = uuid4()
    expires = datetime(2026, 5, 19, 18, 0, tzinfo=timezone.utc)
    captured = {}

    fake_client = MagicMock()

    def capture_update(payload):
        captured["payload"] = payload
        result = MagicMock()
        result.data = [{"id": str(claim_id), "freshness_at": "2026-05-19T12:00:00+00:00"}]
        return MagicMock(eq=lambda *a, **kw: MagicMock(execute=lambda: result))

    fake_client.table = MagicMock(return_value=MagicMock(update=capture_update))

    with patch(
        "app.services.intelligence.claims._get_supabase_client",
        return_value=fake_client,
    ):
        await update_claim_freshness(claim_id, expires_at=expires)

    assert captured["payload"]["expires_at"] == expires.isoformat()
    # Sealing the claim must NOT refresh freshness_at.
    assert "freshness_at" not in captured["payload"]


@pytest.mark.asyncio
async def test_update_claim_freshness_updates_optional_fields():
    """confidence / finding_text / sources are passed through when supplied."""
    from app.services.intelligence.claims import update_claim_freshness

    claim_id = uuid4()
    captured = {}

    fake_client = MagicMock()

    def capture_update(payload):
        captured["payload"] = payload
        result = MagicMock()
        result.data = [{"id": str(claim_id), "freshness_at": "2026-05-19T12:00:00+00:00"}]
        return MagicMock(eq=lambda *a, **kw: MagicMock(execute=lambda: result))

    fake_client.table = MagicMock(return_value=MagicMock(update=capture_update))

    with patch(
        "app.services.intelligence.claims._get_supabase_client",
        return_value=fake_client,
    ):
        await update_claim_freshness(
            claim_id,
            confidence=0.81,
            finding_text="Updated candidate signal text.",
            sources=[{"kind": "supabase_row", "ref": "recruitment_candidates/abc"}],
        )

    p = captured["payload"]
    assert p["confidence"] == 0.81
    assert p["finding_text"] == "Updated candidate signal text."
    assert p["sources"] == [{"kind": "supabase_row", "ref": "recruitment_candidates/abc"}]


@pytest.mark.asyncio
async def test_update_claim_freshness_returns_updated_row_freshness():
    """The helper returns the updated freshness_at as a timezone-aware datetime."""
    from app.services.intelligence.claims import update_claim_freshness

    claim_id = uuid4()
    fake_client = MagicMock()

    def capture_update(_payload):
        result = MagicMock()
        result.data = [{"id": str(claim_id), "freshness_at": "2026-05-19T12:00:00+00:00"}]
        return MagicMock(eq=lambda *a, **kw: MagicMock(execute=lambda: result))

    fake_client.table = MagicMock(return_value=MagicMock(update=capture_update))

    with patch(
        "app.services.intelligence.claims._get_supabase_client",
        return_value=fake_client,
    ):
        result = await update_claim_freshness(claim_id)

    assert isinstance(result, datetime)
    assert result.tzinfo is not None
```

- [ ] **Step 2: Run — should FAIL with ImportError**

```powershell
uv run pytest tests/unit/services/intelligence/test_update_claim_freshness.py -v --tb=short
```

Expected: 4 ImportError failures.

- [ ] **Step 3: Implement in `app/services/intelligence/claims.py`**

Append (after `claim_freshness_hours`):

```python
async def update_claim_freshness(
    claim_id: UUID,
    *,
    confidence: float | None = None,
    finding_text: str | None = None,
    sources: Sequence[dict] | None = None,
    expires_at: datetime | None = None,
) -> datetime:
    """Update an existing kg_findings row in place.

    Used by claim types with a mutate-in-place lifecycle (HR's
    ``candidate_signal`` introduced in Phase 118 is the first).

    Lifecycle rules encoded:
    - If ``expires_at`` is provided, the claim is being SEALED -- set
      ``expires_at`` and do NOT touch ``freshness_at``. The sealed claim
      remains queryable but is no longer considered "active" for
      cross-agent reads that filter on ``expires_at IS NULL OR
      expires_at > now()``.
    - Otherwise, refresh ``freshness_at = now()``. Optional fields
      (confidence, finding_text, sources) are applied iff supplied.

    Args:
        claim_id: kg_findings row to update.
        confidence: New confidence in [0.0, 1.0], or None to leave unchanged.
        finding_text: New human-readable claim text, or None.
        sources: New sources list (overwrites existing), or None.
        expires_at: When set, seals the claim (terminal lifecycle event).

    Returns:
        The updated row's ``freshness_at`` as a timezone-aware datetime.

    Raises:
        RuntimeError if the row does not exist (no matching update).
    """
    from datetime import timezone

    payload: dict = {}

    if expires_at is not None:
        payload["expires_at"] = expires_at.isoformat()
        # Sealing -- do NOT refresh freshness_at.
    else:
        payload["freshness_at"] = datetime.now(timezone.utc).isoformat()

    if confidence is not None:
        payload["confidence"] = confidence
    if finding_text is not None:
        payload["finding_text"] = finding_text
    if sources is not None:
        payload["sources"] = list(sources)

    client = _get_supabase_client()
    result = (
        client.table("kg_findings")
        .update(payload)
        .eq("id", str(claim_id))
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"update_claim_freshness: no row for id={claim_id}")

    freshness_raw = result.data[0]["freshness_at"]
    if isinstance(freshness_raw, str):
        return datetime.fromisoformat(freshness_raw.replace("Z", "+00:00"))
    return freshness_raw
```

Then re-export from `app/services/intelligence/__init__.py`:

```python
from app.services.intelligence.claims import (
    claim_freshness_hours,
    detect_contradictions,
    find_claims,
    get_or_create_entity,
    search_claims_semantic,
    update_claim_freshness,  # new
    write_claim,
    write_claims,
)
```

Add `"update_claim_freshness"` to `__all__`.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_update_claim_freshness.py -v --tb=short
```

Expected: 4/4 pass.

- [ ] **Step 5: Commit GREEN**

```bash
git add app/services/intelligence/claims.py app/services/intelligence/__init__.py tests/unit/services/intelligence/test_update_claim_freshness.py
git commit -m "feat(118-02): add update_claim_freshness primitive for mutate-in-place claims (GREEN)"
```

### Task 3: Emitter helpers — failing tests (RED)

**Files:**
- Create: `tests/unit/agents/hr/test_hr_claim_emission.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for HR claim emission (mocked Supabase + embedding)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.fixture
def candidate_row():
    """Minimal candidate row shape returned by recruitment_service.get_candidate."""
    return {
        "id": str(uuid4()),
        "name": "Alice Yu",
        "email": "alice@example.com",
        "resume_url": "https://example.com/resume.pdf",
        "job_id": str(uuid4()),
        "status": "interviewing",
        "current_stage": "phone_screen",
        "source": "referral",
        "referral_id": str(uuid4()),
        "salary_expectation": 140000,
        "start_date_target": "2026-07-01",
        "updated_at": "2026-05-19T08:00:00+00:00",
    }


@pytest.fixture
def job_row():
    """Minimal job row shape returned by recruitment_service.get_job."""
    return {
        "id": str(uuid4()),
        "title": "Senior Sales Engineer",
        "department": "sales",
        "status": "published",
        "seniority_level": "senior",
    }


@pytest.mark.asyncio
async def test_emit_candidate_signal_creates_claim_when_none_exists(candidate_row, job_row):
    """First emission for a new (candidate, job) pair INSERTs a new claim."""
    from app.agents.hr.claims import emit_candidate_signal

    new_claim_id = uuid4()
    entity_id = uuid4()

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.find_claims",
        new=AsyncMock(return_value=[]),  # no prior claim
    ), patch(
        "app.agents.hr.claims.write_claim",
        new=AsyncMock(return_value=new_claim_id),
    ) as mock_write, patch(
        "app.agents.hr.claims.update_claim_freshness",
        new=AsyncMock(),
    ) as mock_update:
        result = await emit_candidate_signal(
            candidate=candidate_row,
            job=job_row,
            interview_scores=[],
        )

    assert result == new_claim_id
    mock_write.assert_awaited_once()
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_emit_candidate_signal_updates_existing_non_terminal(candidate_row, job_row):
    """Non-terminal status with an existing claim UPDATEs freshness_at, does not INSERT."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import Claim, ClaimSource

    existing_id = uuid4()
    entity_id = uuid4()
    existing = Claim(
        id=existing_id,
        entity_id=entity_id,
        edge_id=None,
        agent_id="hr",
        claim_type="candidate_signal",
        domain="hr",
        finding_text="(old)",
        confidence=0.5,
        sources=[ClaimSource(kind="supabase_row", ref="x")],
        contradicts=[],
        freshness_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        expires_at=None,
        created_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
    )

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.find_claims",
        new=AsyncMock(return_value=[existing]),
    ), patch(
        "app.agents.hr.claims.write_claim",
        new=AsyncMock(),
    ) as mock_write, patch(
        "app.agents.hr.claims.update_claim_freshness",
        new=AsyncMock(return_value=datetime.now(timezone.utc)),
    ) as mock_update:
        result = await emit_candidate_signal(
            candidate=candidate_row,  # status='interviewing' -- non-terminal
            job=job_row,
            interview_scores=[4, 4, 5],
        )

    assert result == existing_id
    mock_write.assert_not_called()
    mock_update.assert_awaited_once()
    # The update call must NOT have set expires_at (non-terminal)
    call_kwargs = mock_update.await_args.kwargs
    assert call_kwargs.get("expires_at") is None
    # It MUST have set confidence (recomputed) and finding_text (refreshed)
    assert "confidence" in call_kwargs
    assert "finding_text" in call_kwargs


@pytest.mark.asyncio
async def test_emit_candidate_signal_seals_on_hired(candidate_row, job_row):
    """status='hired' is TERMINAL -- update sets expires_at, does not refresh freshness_at."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import Claim, ClaimSource

    existing_id = uuid4()
    entity_id = uuid4()
    existing = Claim(
        id=existing_id, entity_id=entity_id, edge_id=None,
        agent_id="hr", claim_type="candidate_signal", domain="hr",
        finding_text="(old)", confidence=0.7,
        sources=[ClaimSource(kind="supabase_row", ref="x")],
        contradicts=[],
        freshness_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        expires_at=None,
        created_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
    )
    candidate_row["status"] = "hired"

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.find_claims",
        new=AsyncMock(return_value=[existing]),
    ), patch(
        "app.agents.hr.claims.update_claim_freshness",
        new=AsyncMock(return_value=datetime.now(timezone.utc)),
    ) as mock_update:
        await emit_candidate_signal(
            candidate=candidate_row,
            job=job_row,
            interview_scores=[5, 5, 5],
        )

    call_kwargs = mock_update.await_args.kwargs
    assert call_kwargs.get("expires_at") is not None
    assert isinstance(call_kwargs["expires_at"], datetime)


@pytest.mark.asyncio
async def test_emit_candidate_signal_seals_on_rejected(candidate_row, job_row):
    """status='rejected' is TERMINAL -- same sealing path as 'hired'."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import Claim, ClaimSource

    existing_id = uuid4()
    entity_id = uuid4()
    existing = Claim(
        id=existing_id, entity_id=entity_id, edge_id=None,
        agent_id="hr", claim_type="candidate_signal", domain="hr",
        finding_text="(old)", confidence=0.4,
        sources=[ClaimSource(kind="supabase_row", ref="x")],
        contradicts=[],
        freshness_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        expires_at=None,
        created_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
    )
    candidate_row["status"] = "rejected"

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.find_claims",
        new=AsyncMock(return_value=[existing]),
    ), patch(
        "app.agents.hr.claims.update_claim_freshness",
        new=AsyncMock(return_value=datetime.now(timezone.utc)),
    ) as mock_update:
        await emit_candidate_signal(
            candidate=candidate_row,
            job=job_row,
            interview_scores=[],
        )

    assert mock_update.await_args.kwargs.get("expires_at") is not None


@pytest.mark.asyncio
async def test_emit_candidate_signal_offer_is_non_terminal(candidate_row, job_row):
    """status='offer' (offer extended) is NON-terminal -- waits for hired/rejected."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import Claim, ClaimSource

    existing_id = uuid4()
    entity_id = uuid4()
    existing = Claim(
        id=existing_id, entity_id=entity_id, edge_id=None,
        agent_id="hr", claim_type="candidate_signal", domain="hr",
        finding_text="(old)", confidence=0.6,
        sources=[ClaimSource(kind="supabase_row", ref="x")],
        contradicts=[],
        freshness_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        expires_at=None,
        created_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
    )
    candidate_row["status"] = "offer"

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.find_claims",
        new=AsyncMock(return_value=[existing]),
    ), patch(
        "app.agents.hr.claims.update_claim_freshness",
        new=AsyncMock(return_value=datetime.now(timezone.utc)),
    ) as mock_update:
        await emit_candidate_signal(
            candidate=candidate_row,
            job=job_row,
            interview_scores=[4, 5],
        )

    # expires_at must NOT be set on a non-terminal 'offer' status.
    assert mock_update.await_args.kwargs.get("expires_at") is None


@pytest.mark.asyncio
async def test_emit_hiring_pipeline_state_always_inserts(job_row):
    """Pipeline snapshots are append-only; each call INSERTs a fresh claim."""
    from app.agents.hr.claims import emit_hiring_pipeline_state

    new_id = uuid4()
    entity_id = uuid4()
    funnel = {
        "applied": 12, "screening": 5, "interviewing": 3,
        "offer": 1, "hired": 0, "rejected": 4,
    }

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.write_claim",
        new=AsyncMock(return_value=new_id),
    ) as mock_write:
        result = await emit_hiring_pipeline_state(job=job_row, funnel=funnel)

    assert result == new_id
    mock_write.assert_awaited_once()
    call_kwargs = mock_write.await_args.kwargs
    assert call_kwargs["claim_type"] == "hiring_pipeline_state"
    # expires_at must be ~7 days in the future.
    assert call_kwargs["expires_at"] is not None
    delta = call_kwargs["expires_at"] - datetime.now(timezone.utc)
    assert 6.5 <= delta.days <= 7.5


@pytest.mark.asyncio
async def test_emit_candidate_signal_includes_band_in_finding_text(candidate_row, job_row):
    """The finding_text payload must include the confidence band label."""
    from app.agents.hr.claims import emit_candidate_signal

    new_id = uuid4()
    entity_id = uuid4()

    with patch(
        "app.agents.hr.claims.get_or_create_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.hr.claims.find_claims",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.agents.hr.claims.write_claim",
        new=AsyncMock(return_value=new_id),
    ) as mock_write:
        await emit_candidate_signal(
            candidate=candidate_row,
            job=job_row,
            interview_scores=[4, 4, 4],
        )

    finding = mock_write.await_args.kwargs["finding_text"]
    assert "Confidence band" in finding
    assert any(band in finding for band in ("low", "medium", "high"))
```

- [ ] **Step 2: Run — should FAIL with ImportError**

```powershell
uv run pytest tests/unit/agents/hr/test_hr_claim_emission.py -v --tb=short
```

Expected: import-error failures across all tests. RED state confirmed.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/unit/agents/hr/test_hr_claim_emission.py
git commit -m "test(118-02): failing unit tests for HR claim emission (RED)"
```

### Task 4: Implement `app/agents/hr/claims.py` (GREEN)

**Files:**
- Create: `app/agents/hr/claims.py`

- [ ] **Step 1: Create the emitter module**

```python
"""HR claim-emission helpers.

Wraps the shared intelligence package (Plan 112) so each HR tool can emit
the right kg_findings row with one call. Lives outside tools.py so the
existing business-logic functions stay focused on their core CRUD job
and the claim side-effect is a single import.

Lifecycle rules (Phase 118 design):
- candidate_signal: one row per (candidate, job) pair. UPDATE on each
  interaction. SEAL (set expires_at) on terminal status (hired/rejected).
- hiring_pipeline_state: append-only periodic snapshot. Each call writes
  a new row with expires_at = now() + 7 days.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from app.services.intelligence import (
    Claim,
    ClaimSource,
    find_claims,
    get_or_create_entity,
    to_band,
    update_claim_freshness,
    write_claim,
)
from app.services.intelligence.presets import hr_confidence
from app.services.intelligence.presets.hr_claim_schema import (
    CANDIDATE_ENTITY_TYPE,
    CANDIDATE_SIGNAL,
    EMBED_CANDIDATE_SIGNAL,
    EMBED_HIRING_PIPELINE_STATE,
    HIRING_PIPELINE_STATE,
    HIRING_PIPELINE_STATE_TTL_DAYS,
    HR_AGENT_ID,
    HR_DOMAIN,
    REQUISITION_ENTITY_TYPE,
    SOURCE_KIND_SUPABASE_ROW,
    SOURCE_KIND_USER,
    TERMINAL_CANDIDATE_STATUSES,
    candidate_entity_canonical_name,
    requisition_entity_canonical_name,
)

logger = logging.getLogger(__name__)

# Fields counted toward candidate_data_completeness signal.
_CANDIDATE_EXPECTED_FIELDS: tuple[str, ...] = (
    "name", "email", "resume_url", "job_id", "status",
    "current_stage", "source", "referral_id",
    "salary_expectation", "start_date_target",
)


def _count_non_null(row: dict[str, Any], fields: tuple[str, ...]) -> int:
    """How many of the expected fields are populated (not None / not '')."""
    n = 0
    for f in fields:
        v = row.get(f)
        if v is not None and v != "":
            n += 1
    return n


def _interviewer_score_sigma(scores: list[float]) -> float:
    """Stddev of interviewer rubric scores. Returns 0.0 when < 2 scores
    (no disagreement signal -- single-source consensus by definition)."""
    if len(scores) < 2:
        return 0.0
    return statistics.stdev(scores)


def _touchpoint_age_hours(updated_at: str | datetime | None) -> float:
    """Hours since the most recent touchpoint. None -> very stale (720h)."""
    if updated_at is None:
        return 720.0
    if isinstance(updated_at, str):
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    else:
        ts = updated_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ts
    return max(0.0, delta.total_seconds() / 3600.0)


def _format_candidate_signal_text(
    candidate: dict, job: dict, n_interviews: int, age_h: float, band: str,
) -> str:
    """Format the human-readable claim text.

    Shape (load-bearing for semantic search across agents):
        Candidate <Name> for <Job Title> at <stage>; <N> interviews
        submitted; latest activity <age_h>h ago. Confidence band: <band>.
    """
    name = candidate.get("name", "(unknown)")
    title = job.get("title", "(unknown role)")
    stage = candidate.get("current_stage") or candidate.get("status", "(unknown)")
    return (
        f"Candidate {name} for {title} at {stage}; "
        f"{n_interviews} interviews submitted; "
        f"latest activity {age_h:.0f}h ago. "
        f"Confidence band: {band}."
    )


async def emit_candidate_signal(
    *,
    candidate: dict[str, Any],
    job: dict[str, Any],
    interview_scores: list[float] | None = None,
    assessments_completed: int = 0,
    assessments_planned: int = 0,
) -> UUID:
    """Emit or refresh the candidate_signal claim for a (candidate, job) pair.

    Resolves the candidate entity, computes confidence via the hr_confidence
    preset, and either:
    - INSERTs a new claim if none exists for this entity_id+claim_type, OR
    - UPDATEs the existing claim's freshness_at + payload (non-terminal), OR
    - UPDATEs the existing claim's expires_at to NOW (terminal status =
      hired or rejected) without refreshing freshness_at.

    Args:
        candidate: Row dict from recruitment_candidates (must include id,
                   name, status; other expected fields contribute to the
                   completeness signal).
        job: Row dict from recruitment_jobs (must include id, title).
        interview_scores: List of interviewer rubric scores (1-5). Empty
                          list means no interviews yet (consensus signal
                          defaults to 1.0).
        assessments_completed: Count of assessments the candidate has
                               completed (Phase 118 default 0).
        assessments_planned: Total planned assessments for the role
                             (Phase 118 default 0 -> coverage signal = 1.0).

    Returns:
        UUID of the inserted or updated kg_findings row.
    """
    interview_scores = interview_scores or []

    # 1. Resolve candidate entity (idempotent on canonical_name).
    canonical = candidate_entity_canonical_name(candidate["id"])
    entity_id = await get_or_create_entity(
        canonical_name=canonical,
        entity_type=CANDIDATE_ENTITY_TYPE,
        domains=[HR_DOMAIN],
        properties={"job_id": str(job.get("id", ""))},
    )

    # 2. Compute confidence inputs.
    non_null = _count_non_null(candidate, _CANDIDATE_EXPECTED_FIELDS)
    expected = len(_CANDIDATE_EXPECTED_FIELDS)
    sigma = _interviewer_score_sigma(interview_scores)
    age_h = _touchpoint_age_hours(candidate.get("updated_at"))

    confidence = hr_confidence(
        non_null_fields=non_null,
        expected_fields=expected,
        interviewer_score_sigma=sigma,
        latest_touchpoint_age_hours=age_h,
        assessments_completed=assessments_completed,
        assessments_planned=assessments_planned,
    )
    band = to_band(confidence)

    finding_text = _format_candidate_signal_text(
        candidate, job, len(interview_scores), age_h, band,
    )

    sources = [
        {
            "kind": SOURCE_KIND_SUPABASE_ROW,
            "ref": f"recruitment_candidates/{candidate['id']}",
        },
    ]
    if interview_scores:
        sources.append(
            {"kind": SOURCE_KIND_USER, "ref": f"interviewers:{len(interview_scores)}"}
        )

    # 3. Look up existing claim for this entity + claim_type.
    existing = await find_claims(
        entity_id=entity_id, claim_type=CANDIDATE_SIGNAL, limit=1,
    )

    status = (candidate.get("status") or "").lower()
    is_terminal = status in TERMINAL_CANDIDATE_STATUSES

    if not existing:
        # 4a. INSERT a fresh claim.
        expires_at = datetime.now(timezone.utc) if is_terminal else None
        return await write_claim(
            entity_id=entity_id,
            domain=HR_DOMAIN,
            finding_text=finding_text,
            confidence=confidence,
            sources=sources,
            agent_id=HR_AGENT_ID,
            claim_type=CANDIDATE_SIGNAL,
            embed=EMBED_CANDIDATE_SIGNAL,
            expires_at=expires_at,
        )

    # 4b. UPDATE the existing claim.
    prior: Claim = existing[0]
    if is_terminal:
        # SEAL: set expires_at, do NOT refresh freshness_at.
        await update_claim_freshness(
            prior.id,
            confidence=confidence,
            finding_text=finding_text,
            sources=sources,
            expires_at=datetime.now(timezone.utc),
        )
    else:
        # REFRESH: bump freshness_at + payload.
        await update_claim_freshness(
            prior.id,
            confidence=confidence,
            finding_text=finding_text,
            sources=sources,
        )
    return prior.id


async def emit_hiring_pipeline_state(
    *,
    job: dict[str, Any],
    funnel: dict[str, int],
) -> UUID:
    """Emit a hiring_pipeline_state snapshot for one requisition.

    Append-only -- each call writes a new kg_findings row with
    expires_at = now() + 7 days so semantic search prefers fresh
    snapshots over historical ones without losing the history entirely.

    Args:
        job: Row dict from recruitment_jobs (must include id, title).
        funnel: Stage -> count mapping. Stages: applied, screening,
                interviewing, offer, hired, rejected.

    Returns:
        UUID of the newly inserted kg_findings row.
    """
    canonical = requisition_entity_canonical_name(str(job["id"]))
    entity_id = await get_or_create_entity(
        canonical_name=canonical,
        entity_type=REQUISITION_ENTITY_TYPE,
        domains=[HR_DOMAIN],
        properties={"job_title": job.get("title", "")},
    )

    title = job.get("title", "(unknown role)")
    counts = " ".join(f"{k}={int(v)}" for k, v in funnel.items())
    now = datetime.now(timezone.utc)
    finding_text = (
        f"Hiring pipeline for {title} [job:{job['id']}]: {counts}. "
        f"Snapshot at {now.isoformat()}."
    )

    expires_at = now + timedelta(days=HIRING_PIPELINE_STATE_TTL_DAYS)

    # Pipeline snapshot confidence -- not a candidate signal, so the
    # preset's signals don't all apply. Use a fixed-high confidence
    # (operational data is ground-truth from our own DB) with a small
    # freshness discount via the recency signal only.
    confidence = hr_confidence(
        non_null_fields=len(funnel),
        expected_fields=6,  # applied, screening, interviewing, offer, hired, rejected
        interviewer_score_sigma=0.0,  # n/a for pipeline -> max consensus
        latest_touchpoint_age_hours=0.0,  # snapshot is by definition now
        assessments_completed=0,
        assessments_planned=0,
    )

    return await write_claim(
        entity_id=entity_id,
        domain=HR_DOMAIN,
        finding_text=finding_text,
        confidence=confidence,
        sources=[
            {"kind": SOURCE_KIND_SUPABASE_ROW, "ref": f"recruitment_jobs/{job['id']}"},
        ],
        agent_id=HR_AGENT_ID,
        claim_type=HIRING_PIPELINE_STATE,
        embed=EMBED_HIRING_PIPELINE_STATE,
        expires_at=expires_at,
    )
```

- [ ] **Step 2: Re-run unit tests — should PASS**

```powershell
uv run pytest tests/unit/agents/hr/test_hr_claim_emission.py -v --tb=short
```

Expected: 7/7 pass. If `test_emit_candidate_signal_includes_band_in_finding_text` fails because the band string doesn't appear, double-check `_format_candidate_signal_text` capitalization.

- [ ] **Step 3: Commit GREEN**

```bash
git add app/agents/hr/claims.py
git commit -m "feat(118-02): HR claim emitters with mutate-in-place lifecycle (GREEN)"
```

### Task 5: Wire emitters into `app/agents/hr/tools.py`

**Files:**
- Modify: `app/agents/hr/tools.py`

- [ ] **Step 1: Failing integration-shaped unit tests at the tool boundary**

Append to `tests/unit/agents/hr/test_hr_claim_emission.py`:

```python
@pytest.mark.asyncio
async def test_add_candidate_tool_emits_claim(candidate_row):
    """add_candidate -> emit_candidate_signal is invoked with the new row."""
    from app.agents.hr import tools

    with patch.object(tools, "_run_emit_candidate_signal", new=AsyncMock()) as mock_emit, \
         patch("app.agents.hr.tools.RecruitmentService") as svc_cls, \
         patch("app.services.request_context.get_current_user_id", return_value="u1"):
        svc = svc_cls.return_value
        svc.add_candidate = AsyncMock(return_value=candidate_row)
        svc.get_job = AsyncMock(return_value={"id": candidate_row["job_id"], "title": "Eng"})
        result = await tools.add_candidate(
            name="Alice Yu",
            email="alice@example.com",
            job_id=candidate_row["job_id"],
        )

    assert result["success"] is True
    mock_emit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_candidate_status_tool_emits_claim():
    """update_candidate_status -> emit_candidate_signal with the new status."""
    from app.agents.hr import tools

    updated_row = {
        "id": "cand-1", "name": "Alice", "email": "a@b.com",
        "job_id": "job-1", "status": "rejected",
        "updated_at": "2026-05-19T08:00:00+00:00",
    }
    with patch.object(tools, "_run_emit_candidate_signal", new=AsyncMock()) as mock_emit, \
         patch("app.agents.hr.tools.RecruitmentService") as svc_cls, \
         patch("app.services.request_context.get_current_user_id", return_value="u1"):
        svc = svc_cls.return_value
        svc.update_candidate_status = AsyncMock(return_value=updated_row)
        svc.get_job = AsyncMock(return_value={"id": "job-1", "title": "Eng"})
        result = await tools.update_candidate_status(
            candidate_id="cand-1", status="rejected",
        )

    assert result["success"] is True
    mock_emit.assert_awaited_once()
    # Verify it received the candidate row with the new status
    kwargs = mock_emit.await_args.kwargs
    assert kwargs["candidate"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_get_hiring_funnel_tool_emits_pipeline_state():
    """get_hiring_funnel(job_id=X) -> emit_hiring_pipeline_state for that job."""
    from app.agents.hr import tools

    funnel = {"applied": 5, "interviewing": 2, "offer": 1, "hired": 0, "rejected": 1, "screening": 1}
    with patch.object(tools, "_run_emit_hiring_pipeline_state", new=AsyncMock()) as mock_emit, \
         patch("app.agents.hr.tools.HiringFunnelService") as svc_cls, \
         patch("app.agents.hr.tools.RecruitmentService") as recruit_cls, \
         patch("app.services.request_context.get_current_user_id", return_value="u1"):
        svc = svc_cls.return_value
        svc.get_funnel_for_job = AsyncMock(return_value=funnel)
        recruit_cls.return_value.get_job = AsyncMock(return_value={"id": "job-1", "title": "Eng"})
        result = await tools.get_hiring_funnel(job_id="job-1")

    assert result["success"] is True
    mock_emit.assert_awaited_once()
```

- [ ] **Step 2: Run — should FAIL because `_run_emit_*` helpers don't exist on tools.py yet**

```powershell
uv run pytest tests/unit/agents/hr/test_hr_claim_emission.py -v --tb=short
```

Expected: 3 new failures (the existing 7 still pass).

- [ ] **Step 3: Modify `app/agents/hr/tools.py` to call emitters**

At the top of the file (after the existing imports), add a deferred-import helper to avoid circular imports at module load:

```python
async def _run_emit_candidate_signal(**kwargs) -> None:
    """Lazy wrapper around app.agents.hr.claims.emit_candidate_signal.

    Wrapped so the emission can be patched in tests without monkey-patching
    a deep module path, and so a failure in claim emission does NOT bubble
    up and break the CRUD tool's return value.
    """
    try:
        from app.agents.hr.claims import emit_candidate_signal
        await emit_candidate_signal(**kwargs)
    except Exception as e:
        # Claim emission is best-effort -- do not break the user-facing
        # tool result if kg_findings is unreachable.
        import logging
        logging.getLogger(__name__).warning(
            "emit_candidate_signal failed (ignored): %s", e
        )


async def _run_emit_hiring_pipeline_state(**kwargs) -> None:
    """Lazy wrapper around app.agents.hr.claims.emit_hiring_pipeline_state."""
    try:
        from app.agents.hr.claims import emit_hiring_pipeline_state
        await emit_hiring_pipeline_state(**kwargs)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "emit_hiring_pipeline_state failed (ignored): %s", e
        )
```

Then in `add_candidate`, after the successful `service.add_candidate(...)` call and before the `return`:

```python
        # Emit candidate_signal claim (best-effort)
        try:
            job = await service.get_job(job_id, user_id=get_current_user_id())
        except Exception:
            job = {"id": job_id, "title": ""}
        await _run_emit_candidate_signal(
            candidate=candidate,
            job=job,
            interview_scores=[],
        )
        return {"success": True, "candidate": candidate}
```

In `update_candidate_status`, after the successful update:

```python
        # Emit candidate_signal claim with the new status (best-effort).
        # This is the lifecycle event that may seal the claim if the new
        # status is 'hired' or 'rejected'.
        try:
            job = await service.get_job(
                candidate.get("job_id"), user_id=get_current_user_id(),
            )
        except Exception:
            job = {"id": candidate.get("job_id"), "title": ""}
        await _run_emit_candidate_signal(
            candidate=candidate,
            job=job,
            interview_scores=[],
        )
        return {"success": True, "candidate": candidate}
```

In `get_hiring_funnel`, after fetching the funnel and before returning:

```python
        # Emit hiring_pipeline_state snapshot (only when scoped to one job;
        # the all-positions summary is not per-requisition so it doesn't fit
        # the snapshot-per-requisition claim model).
        if job_id:
            try:
                recruit_svc = RecruitmentService()
                job = await recruit_svc.get_job(
                    job_id, user_id=get_current_user_id(),
                )
            except Exception:
                job = {"id": job_id, "title": ""}
            await _run_emit_hiring_pipeline_state(job=job, funnel=data)
        return {"success": True, "funnel": data}
```

(Adjust the imports in `get_hiring_funnel` to bring in `RecruitmentService` since the existing function only imports `HiringFunnelService`.)

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/hr/test_hr_claim_emission.py -v --tb=short
```

Expected: 10/10 pass.

- [ ] **Step 5: Run the broader HR unit suite for regression**

```powershell
uv run pytest tests/unit/agents/hr/ -v --tb=short
```

Expected: all existing HR contract / tools-manifest tests still green. If `test_tools_manifest.py` enumerates exact tool counts, the count is unchanged because we did not add public tools, only internal `_run_emit_*` helpers.

- [ ] **Step 6: Commit**

```bash
git add app/agents/hr/tools.py tests/unit/agents/hr/test_hr_claim_emission.py
git commit -m "feat(118-02): wire HR tools to emit candidate_signal + hiring_pipeline_state (GREEN)"
```

### Task 6: Integration test — full candidate lifecycle end-to-end

**Files:**
- Create: `tests/integration/agents/hr/__init__.py` (empty)
- Create: `tests/integration/agents/hr/test_hr_claim_lifecycle.py`

- [ ] **Step 1: Write the lifecycle integration test**

```python
"""Integration test: full candidate lifecycle through kg_findings.

Exercises the spec acceptance:
- All HR outputs carry confidence + band
- candidate_signal claims update freshness_at (NOT create new claim_id)
  on each interaction
- candidate_signal claims set expires_at on offer-accept or rejection
- search_claims_semantic returns HR claims
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
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
async def test_candidate_signal_lifecycle_full():
    """Full lifecycle: apply -> interview -> offer -> hired."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import find_claims
    from app.services.intelligence.presets.hr_claim_schema import (
        CANDIDATE_SIGNAL,
        candidate_entity_canonical_name,
    )
    from app.services.intelligence import get_or_create_entity

    candidate_id = str(uuid4())
    job = {"id": str(uuid4()), "title": "Integration Test Engineer"}

    base = {
        "id": candidate_id,
        "name": "Lifecycle Test Candidate",
        "email": "lc@example.com",
        "resume_url": "https://example.com/resume.pdf",
        "job_id": job["id"],
        "source": "test",
        "current_stage": "applied",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Initial application -- creates the claim.
    base["status"] = "applied"
    id1 = await emit_candidate_signal(candidate=base, job=job, interview_scores=[])

    # 2. Move to interviewing -- should UPDATE, not create.
    base["status"] = "interviewing"
    base["updated_at"] = datetime.now(timezone.utc).isoformat()
    id2 = await emit_candidate_signal(
        candidate=base, job=job, interview_scores=[4, 4],
    )
    assert id2 == id1, "interviewing transition must UPDATE the same claim_id, not insert"

    # 3. Move to offer -- still UPDATE (non-terminal).
    base["status"] = "offer"
    base["updated_at"] = datetime.now(timezone.utc).isoformat()
    id3 = await emit_candidate_signal(
        candidate=base, job=job, interview_scores=[4, 4, 5],
    )
    assert id3 == id1, "offer transition must still UPDATE the same claim_id"

    # Verify expires_at is still NULL (non-terminal).
    canonical = candidate_entity_canonical_name(candidate_id)
    entity_id = await get_or_create_entity(
        canonical_name=canonical, entity_type="person", domains=["hr"],
    )
    claims = await find_claims(entity_id=entity_id, claim_type=CANDIDATE_SIGNAL, limit=10)
    assert len(claims) == 1, f"expected exactly one row, got {len(claims)}"
    assert claims[0].expires_at is None, "non-terminal claim must not be sealed"

    # 4. Move to hired -- TERMINAL, must seal.
    base["status"] = "hired"
    base["updated_at"] = datetime.now(timezone.utc).isoformat()
    id4 = await emit_candidate_signal(
        candidate=base, job=job, interview_scores=[4, 4, 5, 5],
    )
    assert id4 == id1, "terminal transition must seal the same claim_id"

    claims = await find_claims(entity_id=entity_id, claim_type=CANDIDATE_SIGNAL, limit=10)
    assert len(claims) == 1, "still exactly one row -- no new claim on terminal"
    assert claims[0].expires_at is not None, "terminal claim must have expires_at set"
    # band must be high for a strong-consensus, low-sigma candidate with full data
    assert claims[0].band in ("medium", "high")


@pytest.mark.asyncio
async def test_rejection_also_seals_the_claim():
    """status='rejected' must seal exactly like 'hired'."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import find_claims, get_or_create_entity
    from app.services.intelligence.presets.hr_claim_schema import (
        CANDIDATE_SIGNAL, candidate_entity_canonical_name,
    )

    candidate_id = str(uuid4())
    job = {"id": str(uuid4()), "title": "Rejection Test Role"}
    row = {
        "id": candidate_id, "name": "Reject Me", "email": "r@e.com",
        "job_id": job["id"], "status": "applied",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await emit_candidate_signal(candidate=row, job=job)
    row["status"] = "rejected"
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    await emit_candidate_signal(candidate=row, job=job)

    entity_id = await get_or_create_entity(
        canonical_name=candidate_entity_canonical_name(candidate_id),
        entity_type="person", domains=["hr"],
    )
    claims = await find_claims(entity_id=entity_id, claim_type=CANDIDATE_SIGNAL, limit=5)
    assert len(claims) == 1
    assert claims[0].expires_at is not None


@pytest.mark.asyncio
async def test_pipeline_snapshot_is_append_only():
    """Two calls produce two distinct rows; both visible in find_claims."""
    from app.agents.hr.claims import emit_hiring_pipeline_state
    from app.services.intelligence import find_claims, get_or_create_entity
    from app.services.intelligence.presets.hr_claim_schema import (
        HIRING_PIPELINE_STATE, requisition_entity_canonical_name,
    )

    job = {"id": str(uuid4()), "title": "Pipeline Test Role"}
    f1 = {"applied": 5, "screening": 0, "interviewing": 0, "offer": 0, "hired": 0, "rejected": 0}
    f2 = {"applied": 5, "screening": 3, "interviewing": 1, "offer": 0, "hired": 0, "rejected": 1}
    id1 = await emit_hiring_pipeline_state(job=job, funnel=f1)
    id2 = await emit_hiring_pipeline_state(job=job, funnel=f2)
    assert id1 != id2

    entity_id = await get_or_create_entity(
        canonical_name=requisition_entity_canonical_name(str(job["id"])),
        entity_type="topic", domains=["hr"],
    )
    claims = await find_claims(
        entity_id=entity_id, claim_type=HIRING_PIPELINE_STATE, limit=10,
    )
    assert len(claims) >= 2
    # Each must have expires_at ~ 7 days out.
    for c in claims:
        assert c.expires_at is not None
        delta = c.expires_at - datetime.now(timezone.utc)
        assert 6.0 <= delta.days <= 8.0


@pytest.mark.asyncio
async def test_search_claims_semantic_returns_hr_claims():
    """A semantic search for the candidate name returns the HR claim."""
    from app.agents.hr.claims import emit_candidate_signal
    from app.services.intelligence import search_claims_semantic

    candidate_id = str(uuid4())
    unique_name = f"Searchable Candidate {candidate_id[:8]}"
    job = {"id": str(uuid4()), "title": "Searchable Role For HR Test"}
    row = {
        "id": candidate_id, "name": unique_name, "email": "s@e.com",
        "job_id": job["id"], "status": "interviewing",
        "current_stage": "interviewing", "resume_url": "https://x",
        "source": "test", "referral_id": str(uuid4()),
        "salary_expectation": 150000, "start_date_target": "2026-08-01",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await emit_candidate_signal(
        candidate=row, job=job, interview_scores=[4, 4, 5],
    )

    # Search by the unique name -- should retrieve the HR claim.
    results = await search_claims_semantic(
        query=f"interviews for {unique_name}",
        agent_id="hr",
        claim_type="candidate_signal",
        top_k=5,
    )
    assert len(results) >= 1, "semantic search returned no HR claims"
    found_name = any(unique_name in claim.finding_text for claim, _ in results)
    assert found_name, f"HR claim with name {unique_name!r} not in top results"
```

- [ ] **Step 2: Run with local Supabase up**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/agents/hr/test_hr_claim_lifecycle.py -v --tb=short
```

Expected: 4/4 pass. If `test_candidate_signal_lifecycle_full` fails on the "exactly one row" assertion, the UPDATE path is not being taken -- inspect `find_claims` filters in `emit_candidate_signal`.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/agents/hr/__init__.py tests/integration/agents/hr/test_hr_claim_lifecycle.py
git commit -m "test(118-02): integration tests for HR claim lifecycle (freshness update + seal)"
```

### Task 7: Lint + ruff format

- [ ] **Step 1: Run ruff check + format**

```powershell
uv run ruff check app/services/intelligence/claims.py app/services/intelligence/__init__.py app/agents/hr/claims.py app/agents/hr/tools.py tests/unit/services/intelligence/test_update_claim_freshness.py tests/unit/agents/hr/test_hr_claim_emission.py tests/integration/agents/hr/test_hr_claim_lifecycle.py
uv run ruff format app/services/intelligence/claims.py app/services/intelligence/__init__.py app/agents/hr/claims.py app/agents/hr/tools.py tests/unit/services/intelligence/test_update_claim_freshness.py tests/unit/agents/hr/test_hr_claim_emission.py tests/integration/agents/hr/test_hr_claim_lifecycle.py --check
```

Fix in place. Likely issues:
- D-rule docstring formatting (period at end of first line, blank line after summary).
- ARG / unused-arg warnings on the `_run_emit_*` helpers' `**kwargs` -- if `ruff` flags, suppress with the noqa or restructure.
- Long lines in finding_text format strings -- wrap if > 100 chars.

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/services/intelligence/claims.py app/agents/hr/claims.py
```

Expected: clean.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -u app/services/intelligence/ app/agents/hr/ tests/
git diff --cached --quiet || git commit -m "style(118-02): ruff lint + format for HR claim emission"
```

### Task 8: Performance sanity check — claim emission doesn't slow CRUD tools

**Files:**
- Create: `tests/integration/agents/hr/test_hr_emission_perf.py`

The HR CRUD tools are user-facing; adding a kg_findings round-trip on every call must not blow out latency.

- [ ] **Step 1: Write a perf test**

```python
"""Perf sanity: HR tools with claim emission stay under a reasonable budget."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_emit_candidate_signal_p95_under_budget():
    """20 emit_candidate_signal calls; p95 latency <= 1500 ms (includes embed)."""
    from app.agents.hr.claims import emit_candidate_signal

    latencies_ms: list[float] = []
    for i in range(20):
        candidate = {
            "id": str(uuid4()),
            "name": f"Perf Candidate {i}",
            "email": f"perf{i}@example.com",
            "resume_url": "https://x",
            "job_id": str(uuid4()),
            "status": "applied",
            "current_stage": "applied",
            "source": "test",
            "referral_id": str(uuid4()),
            "salary_expectation": 100000,
            "start_date_target": "2026-09-01",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        job = {"id": candidate["job_id"], "title": f"Perf Role {i}"}
        start = time.perf_counter()
        await emit_candidate_signal(candidate=candidate, job=job, interview_scores=[3, 4])
        latencies_ms.append((time.perf_counter() - start) * 1000)

    latencies_ms.sort()
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p50 = latencies_ms[10]
    print(f"p50={p50:.0f}ms p95={p95:.0f}ms n={len(latencies_ms)}")

    # Budget: 1500ms p95 includes embedding (~150-300ms via Vertex),
    # entity upsert (~50-100ms), find_claims (~50-100ms), write_claim
    # (~50-100ms). Above 1500ms suggests we're hitting Vertex retries
    # or the embedding cache is cold.
    assert p95 <= 1500, f"p95={p95:.0f}ms exceeds 1500ms budget"
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/agents/hr/test_hr_emission_perf.py -v
```

Expected: PASS. If p95 > 1500ms, the most likely cause is Vertex embedding latency on cold cache. Options if needed:
1. Skip embedding when `non_null_fields < 3` (very thin candidates not worth embedding).
2. Batch emissions when multiple status changes land in one request.
3. Defer emission to a background task (deferred to a later optimization phase).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/agents/hr/test_hr_emission_perf.py
git commit -m "test(118-02): p95 perf sanity for emit_candidate_signal"
```

### Task 9: Phase 118 acceptance sign-off

- [ ] **Step 1: Cross-check the Phase 118 spec acceptance criteria**

| Spec acceptance line (Phase 118) | Verified by |
|---|---|
| HR Agent test suite green | Task 5 Step 5 (`tests/unit/agents/hr/` regression) + Task 6 |
| All HR outputs carry confidence + band | Task 4 (`_format_candidate_signal_text` includes band) + Task 3 test `test_emit_candidate_signal_includes_band_in_finding_text` |
| `candidate_signal` claims update `freshness_at` (NOT create new claim_id) on each interaction | Task 6 `test_candidate_signal_lifecycle_full` -- asserts `id2 == id1`, `id3 == id1` |
| `candidate_signal` claims set `expires_at` on offer-accept or rejection transitions | Task 6 `test_candidate_signal_lifecycle_full` (hired) + `test_rejection_also_seals_the_claim` |
| `search_claims_semantic` returns HR claims | Task 6 `test_search_claims_semantic_returns_hr_claims` |
| `hiring_pipeline_state` is append-only with 7-day expiry | Task 6 `test_pipeline_snapshot_is_append_only` |
| Self-improvement engine entanglement honored | Plan 118-01 Task 6 audit + Plan 118-02 Task 1 read of the audit |
| Lint clean | Task 7 |
| Perf p95 within budget | Task 8 |

- [ ] **Step 2: Cross-check the originally enforced rules**

| Rule | Verified by |
|---|---|
| TDD: failing test -> minimal implementation -> passing test -> commit | Tasks 2-6 each follow RED -> GREEN -> commit |
| 2-5 minute steps | Tasks broken into bounded steps with clear stop points |
| No placeholders | `assessments_completed/planned` default 0 is an *explicit* simplification, documented in pre-flight; no `TODO`/`FIXME` left in shipped code |
| pytest with expected output | Each test step states "Expected: ... pass" or "Expected: ImportError" |
| git add + git commit -m "feat(118-NN): ..." per task | Each Task ends with a commit |
| `uv run pytest`, `uv run ruff check` | All commands use `uv run` |

- [ ] **Step 3: Plan 118-02 complete. Phase 118 (HR Agent adoption) is fully shipped.**

Next phase: 119 (Customer Support Agent adoption). The `update_claim_freshness` primitive shipped here is reusable by any future claim_type with a mutate-in-place lifecycle.

---

## Spec coverage check

| Spec requirement (Phase 118 § HR Agent adoption) | Task(s) |
|---|---|
| `candidate_signal` claims expire at offer-accept or rejection | Task 4 (`TERMINAL_CANDIDATE_STATUSES` branching) + Task 6 (`test_*_seals_the_claim`) |
| Before terminal status, `freshness_at` updates on each interaction | Task 4 (UPDATE path, no INSERT) + Task 6 (`id2 == id1 == id3`) |
| `claim_freshness_hours` pattern used | Implicit via `find_claims` lookup before update; `claim_freshness_hours` is not directly called because we read the full Claim, not just the age |
| `hiring_pipeline_state` is a periodic snapshot per requisition | Tasks 4-5 (`emit_hiring_pipeline_state` + tool wiring) + Task 6 (`test_pipeline_snapshot_is_append_only`) |
| Two sub-plans only (no external cache) | This plan + Plan 118-01; no 118-03 |
| All claims attached to entity (candidate-as-`person`, requisition-as-`topic`) | Task 4 + Plan 118-01's canonical-name helpers |
| Cross-agent `search_claims_semantic` returns HR claims | Task 6 `test_search_claims_semantic_returns_hr_claims` |
| Best-effort emission -- failures do not break HR CRUD tool returns | Task 5 (`_run_emit_*` wrappers swallow exceptions) |
| Bias-fairness guardrails preserved | Untouched -- emission adds claims downstream of the existing decision logic; the instructions file's BIAS & FAIRNESS section is unchanged |

All Phase 118 emission lines covered.

---

## Risks captured for follow-up phases

These do NOT block Phase 118 but should land in the rolling-adoption risk register for downstream phases:

1. **`update_claim_freshness` does not currently re-embed.** When `finding_text` changes materially, the embedding stays stale. For HR this is a minor signal-degradation risk (the name + role + stage don't change much within a candidate's lifecycle). For Customer Support's `ticket_sentiment` (Phase 119), which mutates more dramatically, this needs to be addressed: extend `update_claim_freshness` to re-embed when `finding_text` was passed AND the row had a prior embedding.

2. **No claim-row history.** The "trade-off accepted" in pre-flight context is acknowledged but not insured. If recruiters need a per-touchpoint audit trail in `kg_findings`, the fix is an `kg_findings_history` shadow table inserted via trigger -- separate phase.

3. **Pipeline snapshot frequency.** Every `get_hiring_funnel(job_id=X)` call writes a snapshot. For a recruiter polling the dashboard every 30s, that's 120 rows/hour per requisition. The 7-day TTL caps the bloat, but a debounce ("only emit if last snapshot > 30 min ago") may be wanted. Defer to a later phase or Customer Support Phase 119 if the same pattern shows up there.

4. **`_run_emit_*` helpers swallow ALL exceptions.** A persistent kg_findings outage will silently degrade the claim graph without any operator signal. The Phase 112 observability spec already includes `intelligence.claims.written` counter — emission failures should bump a `intelligence.claims.write_failed{agent_id="hr"}` counter the same way. Wire that in the next observability-touch phase.
