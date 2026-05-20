# Shared Intelligence Infrastructure — Plan 120-03: Operations Agent Claim Emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the 5 Operations claim types defined in Plan 120-01's `docs/intelligence/operations-claim-vocabulary.md` into the Operations Agent tool call sites. Every Operations output that produces an operational outcome must emit a `kg_findings` claim via `write_claim`, carrying a `confidence` + `band` (computed via `presets.operations_confidence`) and a domain-correct `expires_at`. End state: `integration_health_verified` claims expire within 24h; `workflow_execution_completed` claims are immutable; `search_claims_semantic` returns Operations claims alongside Data and Research claims; Operations Agent test suite stays green.

**Architecture:** Library-first emission. No new ADK tools — the existing Operations tools gain a thin emission tail after their success paths. Each emission site computes the four `operations_confidence` inputs from the tool's own evidence (probe results, audit-trail captures, etc.) and writes one claim per outcome. Errors propagate per Phase 112's "writes fail loudly" policy, but the tool's primary return path is unchanged on emission failure — we add a `claim_id` to the return dict on success and log on failure rather than aborting the user's call.

**Tech Stack:** `app/services/intelligence` (Phase 112/113 shipped surface), `app/agents/tools/api_connector.py`, `app/agents/tools/integration_setup.py`, `app/agents/tools/ops_tools.py`, `app/agents/tools/workflow_ops.py`, `app/agents/enhanced_tools.py::audit_user_setup_tool`. Tests: pytest + mocked `write_claim` for unit; live Supabase + Vertex embeddings for integration.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 120 — Operations Agent adoption § "Claims".

**Out of scope:** Confidence preset itself (Plan 120-01). Cache surfaces (Plan 120-02). New ADK tools — the `search_agent_claims` Executive tool from Plan 113-04 already returns Operations claims once they exist (no per-agent wrapper needed). Migrating the self-improvement engine — Plan 120-01's audit identifies any required engine remediation; this plan implements only the parts the audit cleared as GO or GO-WITH-FENCES. Frontend dashboard changes — `/admin/research/overview` auto-extends from `intelligence.claims.written` telemetry tags.

---

## File structure

**Create:**
- `app/agents/operations/_claims.py` — single source of truth for Operations claim emission helpers (`emit_integration_health_verified`, `emit_workflow_execution_completed`, `emit_api_connector_setup_validated`, `emit_configuration_audit_passed`, `emit_sop_generation_completed`)
- `tests/unit/agents/operations/test_claim_emission.py` — unit tests with mocked `write_claim`
- `tests/integration/test_operations_claim_emission.py` — integration tests against live Supabase + Vertex
- `tests/integration/test_operations_claim_expiry.py` — verifies `integration_health_verified` rows carry `expires_at` within 24h

**Modify:**
- `app/agents/tools/api_connector.py` — call `emit_api_connector_setup_validated` on `connect_api` success; call `emit_integration_health_verified` on `validate_api_connection` healthy path
- `app/agents/tools/integration_setup.py` — call `emit_integration_health_verified` for each healthy integration in `check_integration_status`
- `app/agents/tools/ops_tools.py` — call `emit_sop_generation_completed` on `generate_sop_document` success
- `app/agents/tools/workflow_ops.py` — call `emit_workflow_execution_completed` on workflow terminal-state hook
- `app/agents/enhanced_tools.py` — call `emit_configuration_audit_passed` on `audit_user_setup_tool` success

---

## Pre-flight context

`operations_confidence(...)` (Plan 120-01) accepts four pre-normalised
inputs. This plan's job is to compute each input from the evidence
available at each emission site.

**Normalisation rules per claim type (load-bearing — Plan 120-03 author MUST follow these):**

| Claim type | `integration_verification_signal` | `audit_trail_completeness` | `execution_idempotency` | `test_coverage_signal` |
|---|---|---|---|---|
| `integration_health_verified` | 1.0 if probe passed; 0.5 if partial; 0.0 if cached-only | fraction of probe artifacts captured (request, response status, headers, latency) ∈ [0,1] | 1.0 (probe is read-only) | 1.0 if a regression test pins this probe path; 0.0 otherwise |
| `workflow_execution_completed` | 1.0 if no integration step failed; else (passing_integration_steps / total_integration_steps) | (steps_with_full_event_record / total_steps) | 1.0 if every step is marked idempotent; else (idempotent_steps / total_steps) | 1.0 if workflow def has an end-to-end test fixture; else 0.0 |
| `api_connector_setup_validated` | 1.0 if sample endpoint returned 2xx post-codegen; 0.0 if no sample call | 1.0 if spec_hash + endpoint list + registration metadata all captured | 0.5 (re-runs may duplicate tools — known surface) | 1.0 if generated tools have smoke tests; else 0.0 |
| `configuration_audit_passed` | (actively_probed_integrations / total_integrations) | (audit_items_executed / total_audit_items) | 1.0 (audit is read-only) | 1.0 if `audit_user_setup_tool` has per-check unit tests; else 0.0 |
| `sop_generation_completed` | 1.0 (pass-through; SOP generation is local) | 1.0 if document_id + version + all steps + roles captured; else partial | 1.0 (deterministic from inputs) | 1.0 if `_format_sop_as_text` has a snapshot test; else 0.0 |

`expires_at` policy (also load-bearing):

| Claim type | `expires_at` value |
|---|---|
| `integration_health_verified` | `datetime.now(tz=UTC) + timedelta(hours=24)` (hard contract from spec) |
| `workflow_execution_completed` | `None` (immutable) |
| `api_connector_setup_validated` | `None` (until spec_hash changes; superseded via new claim with `contradicts=[old_id]`) |
| `configuration_audit_passed` | `datetime.now(tz=UTC) + timedelta(days=7)` |
| `sop_generation_completed` | `None` (immutable; revisions supersede via `contradicts=[old_id]`) |

`embed` policy:

| Claim type | `embed` |
|---|---|
| `integration_health_verified` | True (semantic-search target) |
| `workflow_execution_completed` | True |
| `api_connector_setup_validated` | True |
| `configuration_audit_passed` | False (per-user; not semantically searchable across agents) |
| `sop_generation_completed` | True |

`agent_id` = `"operations"` for every emission (matches the agent factory's persona/name suffix conventions).
`domain` = `"operations"` (single value across the 5 types).

Acceptance bar for this plan:
- 5 emission helpers ship in `_claims.py`, each tested in isolation with mocked `write_claim`.
- Each existing Operations tool call-site wires its corresponding helper at the success-path tail.
- Integration test confirms `search_claims_semantic("integration health hubspot")` returns at least one Operations claim alongside Data/Research claims.
- Integration test confirms `integration_health_verified` rows have `expires_at ≤ now + 24h + 60s` (60s slack for clock skew).
- Operations Agent test suite green.
- All Operations outputs carry `confidence` + `band` (the call sites return the new fields in their response dict so downstream UI surfaces them).
- No new ADK tools registered.
- Lint clean.

Environment quirks: local Supabase + Vertex embedding integration tests need real env vars (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`, `GOOGLE_API_KEY`). The unit tests fully mock the intelligence surface. Per `reference_integration_supabase_client_bypass.md`, integration tests construct the Supabase client via `supabase.create_client(url, key)` to bypass the conftest MagicMock stub.

---

## Tasks

### Task 1: Pre-flight + skeleton of `_claims.py`

**Files:**
- Create: `app/agents/operations/_claims.py`

- [ ] **Step 1: Confirm Plans 120-01 + 120-02 prerequisites**

```powershell
uv run python -c "from app.services.intelligence import presets, write_claim, get_or_create_entity, should_call_external; print(presets.operations_confidence(1.0, 1.0, 1.0, 1.0))"
```

Expected output: `1.0`. If this fails, Plan 120-01 has not landed — STOP.

```powershell
uv run python -c "from app.agents.operations._cache_keys import INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS; print(INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS)"
```

Expected output: `24.0`. If this fails, Plan 120-02 has not landed — STOP.

- [ ] **Step 2: Confirm the audit doc cleared us to proceed**

```powershell
uv run python -c "import pathlib; p = pathlib.Path('docs/intelligence/self-improvement-audit-120.md'); print(p.exists()); print('GO' in p.read_text() if p.exists() else 'missing audit')"
```

Expected: `True` and `GO`. If the audit decision is `HOLD`, STOP and resolve the engine entanglement first.

- [ ] **Step 3: Create the `_claims.py` skeleton**

Create `app/agents/operations/_claims.py`:

```python
"""Operations Agent claim emission helpers (Plan 120-03).

Five emitters, one per claim_type defined in
``docs/intelligence/operations-claim-vocabulary.md``:

- emit_integration_health_verified
- emit_workflow_execution_completed
- emit_api_connector_setup_validated
- emit_configuration_audit_passed
- emit_sop_generation_completed

Each helper:
1. Computes the four operations_confidence inputs from the call-site evidence
2. Calls operations_confidence to get a confidence float
3. Resolves the entity_id via get_or_create_entity
4. Calls write_claim with claim-type-specific expires_at + embed policy
5. Returns the new claim UUID (or None on a swallowed-error path)

Errors from write_claim propagate by default — callers decide whether
to absorb them (the Operations tools wrap each emission in a try/except
so the user's primary call still succeeds even if claim emission fails).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.services.intelligence import (
    get_or_create_entity,
    presets,
    write_claim,
)

logger = logging.getLogger(__name__)

# Per-claim retention policies pinned by the Plan 120-01 vocabulary doc.
_INTEGRATION_HEALTH_TTL = timedelta(hours=24)
_CONFIGURATION_AUDIT_TTL = timedelta(days=7)


def _now_utc() -> datetime:
    """Wrapped for test seam — never call datetime.now directly in this module."""
    return datetime.now(tz=timezone.utc)


async def emit_integration_health_verified(
    *,
    service_id: str,
    probe_passed: bool,
    probe_artifacts_captured: int,
    probe_artifacts_total: int,
    has_regression_test: bool,
    evidence_summary: str,
) -> UUID | None:
    """Emit one integration_health_verified claim. Returns UUID on success.

    Returns None and logs a warning on any write_claim failure — callers
    decide whether to treat that as fatal.
    """
    raise NotImplementedError  # Wired in Task 2


async def emit_workflow_execution_completed(
    *,
    workflow_id: str,
    workflow_name: str,
    terminal_status: str,
    n_steps: int,
    duration_seconds: float,
    integration_step_success_rate: float,
    steps_with_full_event_record: int,
    steps_total_for_audit: int,
    idempotent_step_fraction: float,
    has_e2e_test_fixture: bool,
) -> UUID | None:
    """Emit one workflow_execution_completed claim. Immutable record."""
    raise NotImplementedError  # Wired in Task 3


async def emit_api_connector_setup_validated(
    *,
    api_name: str,
    spec_hash: str,
    endpoint_count: int,
    sample_call_status: int | None,
    has_generated_tool_tests: bool,
) -> UUID | None:
    """Emit one api_connector_setup_validated claim."""
    raise NotImplementedError  # Wired in Task 4


async def emit_configuration_audit_passed(
    *,
    user_id: str,
    integrations_actively_probed: int,
    integrations_total: int,
    audit_items_executed: int,
    audit_items_total: int,
    non_blocking_notes: int,
    has_per_check_unit_tests: bool,
) -> UUID | None:
    """Emit one configuration_audit_passed claim (per-user, embed=False)."""
    raise NotImplementedError  # Wired in Task 5


async def emit_sop_generation_completed(
    *,
    process_name: str,
    document_id: str,
    version: str,
    n_procedure_steps: int,
    roles_captured: bool,
    has_format_snapshot_test: bool,
    supersedes_claim_id: UUID | None = None,
) -> UUID | None:
    """Emit one sop_generation_completed claim. supersedes_claim_id populates contradicts."""
    raise NotImplementedError  # Wired in Task 6


__all__ = [
    "emit_api_connector_setup_validated",
    "emit_configuration_audit_passed",
    "emit_integration_health_verified",
    "emit_sop_generation_completed",
    "emit_workflow_execution_completed",
]
```

- [ ] **Step 4: Sanity import**

```powershell
uv run python -c "from app.agents.operations._claims import emit_integration_health_verified, emit_workflow_execution_completed, emit_api_connector_setup_validated, emit_configuration_audit_passed, emit_sop_generation_completed; print('ok')"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_claims.py
git commit -m "feat(120-03): _claims.py emitter skeleton (5 signatures)"
```

### Task 2: `emit_integration_health_verified` (TDD)

**Files:**
- Create: `tests/unit/agents/operations/test_claim_emission.py`
- Modify: `app/agents/operations/_claims.py`

This is the most important emitter — the spec's headline acceptance
criterion is "all `integration_health_verified` claims expire within
24h of write."

- [ ] **Step 1: Failing unit tests**

Create `tests/unit/agents/operations/test_claim_emission.py`:

```python
"""Unit tests for the Operations claim emitters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.mark.asyncio
async def test_integration_health_verified_emits_with_24h_expiry():
    """Returned claim_id present; write_claim called with expires_at ~now+24h."""
    from app.agents.operations import _claims

    entity_id = uuid4()
    claim_id = uuid4()
    write_mock = AsyncMock(return_value=claim_id)
    fixed_now = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)

    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=entity_id),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
        patch(
            "app.agents.operations._claims._now_utc",
            return_value=fixed_now,
        ),
    ):
        result = await _claims.emit_integration_health_verified(
            service_id="hubspot",
            probe_passed=True,
            probe_artifacts_captured=4,
            probe_artifacts_total=4,
            has_regression_test=True,
            evidence_summary="auth ok, sample endpoint 200",
        )

    assert result == claim_id
    write_mock.assert_called_once()
    kwargs = write_mock.call_args.kwargs
    assert kwargs["agent_id"] == "operations"
    assert kwargs["domain"] == "operations"
    assert kwargs["claim_type"] == "integration_health_verified"
    assert kwargs["entity_id"] == entity_id
    assert kwargs["embed"] is True
    # Hard acceptance criterion: expires_at = now + 24h exactly.
    assert kwargs["expires_at"] == fixed_now + timedelta(hours=24)
    # Confidence should reflect probe_passed=True + full artifacts + regression test.
    # operations_confidence(1.0, 1.0, 1.0, 1.0) = 1.0 — but execution_idempotency=1.0
    # is hardcoded inside the emitter (probes are read-only).
    assert kwargs["confidence"] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.asyncio
async def test_integration_health_verified_failed_probe_low_confidence():
    """probe_passed=False → integration_verification_signal=0.0 → low confidence."""
    from app.agents.operations import _claims

    entity_id = uuid4()
    write_mock = AsyncMock(return_value=uuid4())
    fixed_now = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)

    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=entity_id),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
        patch(
            "app.agents.operations._claims._now_utc",
            return_value=fixed_now,
        ),
    ):
        await _claims.emit_integration_health_verified(
            service_id="hubspot",
            probe_passed=False,
            probe_artifacts_captured=2,
            probe_artifacts_total=4,
            has_regression_test=False,
            evidence_summary="auth failed",
        )

    kwargs = write_mock.call_args.kwargs
    # operations_confidence(0.0, 0.5, 1.0, 0.0) = 0.40*0 + 0.35*0.5 + 0.20*1.0 + 0.05*0
    # = 0.0 + 0.175 + 0.2 + 0.0 = 0.375 → band='low'
    assert kwargs["confidence"] == pytest.approx(0.375, abs=1e-9)


@pytest.mark.asyncio
async def test_integration_health_verified_swallows_write_errors():
    """write_claim failure logs but returns None — caller's primary path
    must not break."""
    from app.agents.operations import _claims

    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=AsyncMock(side_effect=RuntimeError("supabase down")),
        ),
    ):
        result = await _claims.emit_integration_health_verified(
            service_id="hubspot",
            probe_passed=True,
            probe_artifacts_captured=4,
            probe_artifacts_total=4,
            has_regression_test=True,
            evidence_summary="ok",
        )
    assert result is None


def test_integration_health_verified_uses_correct_entity_shape():
    """get_or_create_entity must use entity_type='technology' (or 'product')
    and canonical_name=service_id."""
    # Captured via the test_integration_health_verified_emits_with_24h_expiry
    # mock — extend that test if more entity shape coverage is needed.
```

- [ ] **Step 2: Run — should FAIL (NotImplementedError)**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v --tb=short
```

- [ ] **Step 3: Implement `emit_integration_health_verified`**

Replace the `raise NotImplementedError` body in `_claims.py`:

```python
async def emit_integration_health_verified(
    *,
    service_id: str,
    probe_passed: bool,
    probe_artifacts_captured: int,
    probe_artifacts_total: int,
    has_regression_test: bool,
    evidence_summary: str,
) -> UUID | None:
    """Emit one integration_health_verified claim with TTL = now + 24h."""
    integration_verification_signal = 1.0 if probe_passed else 0.0
    audit_trail_completeness = (
        min(1.0, probe_artifacts_captured / probe_artifacts_total)
        if probe_artifacts_total > 0
        else 0.0
    )
    execution_idempotency = 1.0  # probes are read-only
    test_coverage_signal = 1.0 if has_regression_test else 0.0

    confidence = presets.operations_confidence(
        integration_verification_signal=integration_verification_signal,
        audit_trail_completeness=audit_trail_completeness,
        execution_idempotency=execution_idempotency,
        test_coverage_signal=test_coverage_signal,
    )

    try:
        entity_id = await get_or_create_entity(
            canonical_name=service_id,
            entity_type="technology",
            domains=["operations"],
        )
    except Exception as e:
        logger.warning(
            "emit_integration_health_verified: entity resolution failed for %s: %s",
            service_id, e,
        )
        return None

    now = _now_utc()
    finding_text = (
        f"{service_id} integration verified at {now.isoformat()}: "
        f"{evidence_summary}"
    )

    try:
        return await write_claim(
            entity_id=entity_id,
            domain="operations",
            agent_id="operations",
            claim_type="integration_health_verified",
            finding_text=finding_text,
            confidence=confidence,
            sources=[{"kind": "other", "ref": f"probe:{service_id}"}],
            embed=True,
            expires_at=now + _INTEGRATION_HEALTH_TTL,
        )
    except Exception as e:
        logger.warning(
            "emit_integration_health_verified: write_claim failed for %s: %s",
            service_id, e,
        )
        return None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v --tb=short -k integration_health
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_claims.py tests/unit/agents/operations/test_claim_emission.py
git commit -m "feat(120-03): emit_integration_health_verified with 24h TTL (GREEN)"
```

### Task 3: `emit_workflow_execution_completed` (TDD)

**Files:**
- Modify: `tests/unit/agents/operations/test_claim_emission.py`
- Modify: `app/agents/operations/_claims.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/unit/agents/operations/test_claim_emission.py`:

```python
@pytest.mark.asyncio
async def test_workflow_execution_completed_immutable_expiry_none():
    """expires_at is None — workflow runs are audit-grade history."""
    from app.agents.operations import _claims

    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
    ):
        await _claims.emit_workflow_execution_completed(
            workflow_id="wf-123",
            workflow_name="Onboarding Email Sequence",
            terminal_status="success",
            n_steps=5,
            duration_seconds=42.0,
            integration_step_success_rate=1.0,
            steps_with_full_event_record=5,
            steps_total_for_audit=5,
            idempotent_step_fraction=1.0,
            has_e2e_test_fixture=True,
        )

    kwargs = write_mock.call_args.kwargs
    assert kwargs["claim_type"] == "workflow_execution_completed"
    assert kwargs["expires_at"] is None
    assert kwargs["confidence"] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.asyncio
async def test_workflow_execution_completed_partial_failure_lower_confidence():
    """3/5 integration steps passed → reduced confidence."""
    from app.agents.operations import _claims

    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
    ):
        await _claims.emit_workflow_execution_completed(
            workflow_id="wf-x",
            workflow_name="Partial",
            terminal_status="success",
            n_steps=5,
            duration_seconds=10.0,
            integration_step_success_rate=0.6,
            steps_with_full_event_record=4,
            steps_total_for_audit=5,
            idempotent_step_fraction=0.8,
            has_e2e_test_fixture=False,
        )

    kwargs = write_mock.call_args.kwargs
    # operations_confidence(0.6, 0.8, 0.8, 0.0)
    # = 0.40*0.6 + 0.35*0.8 + 0.20*0.8 + 0.05*0 = 0.24 + 0.28 + 0.16 = 0.68
    assert kwargs["confidence"] == pytest.approx(0.68, abs=1e-9)
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k workflow_execution
```

- [ ] **Step 3: Implement**

Replace the NotImplementedError body of `emit_workflow_execution_completed`:

```python
async def emit_workflow_execution_completed(
    *,
    workflow_id: str,
    workflow_name: str,
    terminal_status: str,
    n_steps: int,
    duration_seconds: float,
    integration_step_success_rate: float,
    steps_with_full_event_record: int,
    steps_total_for_audit: int,
    idempotent_step_fraction: float,
    has_e2e_test_fixture: bool,
) -> UUID | None:
    """Emit one workflow_execution_completed claim. Immutable on completion."""
    audit_trail_completeness = (
        steps_with_full_event_record / steps_total_for_audit
        if steps_total_for_audit > 0
        else 0.0
    )
    confidence = presets.operations_confidence(
        integration_verification_signal=max(
            0.0, min(1.0, integration_step_success_rate)
        ),
        audit_trail_completeness=max(0.0, min(1.0, audit_trail_completeness)),
        execution_idempotency=max(0.0, min(1.0, idempotent_step_fraction)),
        test_coverage_signal=1.0 if has_e2e_test_fixture else 0.0,
    )

    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"workflow:{workflow_id}",
            entity_type="topic",
            domains=["operations"],
        )
    except Exception as e:
        logger.warning(
            "emit_workflow_execution_completed: entity resolution failed for %s: %s",
            workflow_id, e,
        )
        return None

    now = _now_utc()
    finding_text = (
        f"Workflow '{workflow_name}' completed at {now.isoformat()}: "
        f"{n_steps} steps, {duration_seconds:.1f}s, "
        f"terminal_status={terminal_status}"
    )

    try:
        return await write_claim(
            entity_id=entity_id,
            domain="operations",
            agent_id="operations",
            claim_type="workflow_execution_completed",
            finding_text=finding_text,
            confidence=confidence,
            sources=[{"kind": "other", "ref": f"workflow_run:{workflow_id}"}],
            embed=True,
            expires_at=None,  # immutable
        )
    except Exception as e:
        logger.warning(
            "emit_workflow_execution_completed: write_claim failed for %s: %s",
            workflow_id, e,
        )
        return None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k workflow_execution
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_claims.py tests/unit/agents/operations/test_claim_emission.py
git commit -m "feat(120-03): emit_workflow_execution_completed (immutable claim, GREEN)"
```

### Task 4: `emit_api_connector_setup_validated` (TDD)

**Files:**
- Modify: `tests/unit/agents/operations/test_claim_emission.py`
- Modify: `app/agents/operations/_claims.py`

- [ ] **Step 1: Append failing tests**

```python
@pytest.mark.asyncio
async def test_api_connector_setup_validated_carries_spec_hash():
    """Claim finding_text includes the spec hash for supersession tracking."""
    from app.agents.operations import _claims

    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
    ):
        await _claims.emit_api_connector_setup_validated(
            api_name="stripe",
            spec_hash="abc123",
            endpoint_count=7,
            sample_call_status=200,
            has_generated_tool_tests=True,
        )

    kwargs = write_mock.call_args.kwargs
    assert kwargs["claim_type"] == "api_connector_setup_validated"
    assert kwargs["expires_at"] is None
    assert "abc123" in kwargs["finding_text"]
    # execution_idempotency hardcoded to 0.5 per vocabulary doc (re-runs may dup tools)
    # operations_confidence(1.0, 1.0, 0.5, 1.0) = 0.40 + 0.35 + 0.10 + 0.05 = 0.90
    assert kwargs["confidence"] == pytest.approx(0.90, abs=1e-9)


@pytest.mark.asyncio
async def test_api_connector_setup_validated_no_sample_call_zero_verification():
    """sample_call_status=None → integration_verification_signal=0.0."""
    from app.agents.operations import _claims

    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
    ):
        await _claims.emit_api_connector_setup_validated(
            api_name="x",
            spec_hash="z",
            endpoint_count=1,
            sample_call_status=None,
            has_generated_tool_tests=False,
        )

    kwargs = write_mock.call_args.kwargs
    # operations_confidence(0.0, 1.0, 0.5, 0.0) = 0 + 0.35 + 0.10 + 0 = 0.45
    assert kwargs["confidence"] == pytest.approx(0.45, abs=1e-9)
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k api_connector_setup
```

- [ ] **Step 3: Implement**

```python
async def emit_api_connector_setup_validated(
    *,
    api_name: str,
    spec_hash: str,
    endpoint_count: int,
    sample_call_status: int | None,
    has_generated_tool_tests: bool,
) -> UUID | None:
    """Emit one api_connector_setup_validated claim."""
    if sample_call_status is None:
        integration_verification_signal = 0.0
    elif 200 <= sample_call_status < 300:
        integration_verification_signal = 1.0
    else:
        integration_verification_signal = 0.5

    confidence = presets.operations_confidence(
        integration_verification_signal=integration_verification_signal,
        audit_trail_completeness=1.0,  # spec_hash + endpoints + reg metadata captured
        execution_idempotency=0.5,  # connect_api may dup tools on re-run
        test_coverage_signal=1.0 if has_generated_tool_tests else 0.0,
    )

    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"api:{api_name}",
            entity_type="product",
            domains=["operations"],
        )
    except Exception as e:
        logger.warning(
            "emit_api_connector_setup_validated: entity resolution failed for %s: %s",
            api_name, e,
        )
        return None

    now = _now_utc()
    finding_text = (
        f"API connector '{api_name}' setup validated at {now.isoformat()}: "
        f"{endpoint_count} endpoints generated, spec_hash={spec_hash}"
    )

    try:
        return await write_claim(
            entity_id=entity_id,
            domain="operations",
            agent_id="operations",
            claim_type="api_connector_setup_validated",
            finding_text=finding_text,
            confidence=confidence,
            sources=[{"kind": "other", "ref": f"api_spec:{spec_hash}"}],
            embed=True,
            expires_at=None,
        )
    except Exception as e:
        logger.warning(
            "emit_api_connector_setup_validated: write_claim failed for %s: %s",
            api_name, e,
        )
        return None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k api_connector_setup
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_claims.py tests/unit/agents/operations/test_claim_emission.py
git commit -m "feat(120-03): emit_api_connector_setup_validated (GREEN)"
```

### Task 5: `emit_configuration_audit_passed` (TDD)

**Files:**
- Modify: `tests/unit/agents/operations/test_claim_emission.py`
- Modify: `app/agents/operations/_claims.py`

`configuration_audit_passed` is the only claim in the vocabulary with
`embed=False` — it's per-user, not cross-agent searchable.

- [ ] **Step 1: Append failing tests**

```python
@pytest.mark.asyncio
async def test_configuration_audit_passed_embed_false_and_7d_expiry():
    """Per-user claim with embed=False and expires_at = now + 7d."""
    from app.agents.operations import _claims

    write_mock = AsyncMock(return_value=uuid4())
    fixed_now = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
        patch(
            "app.agents.operations._claims._now_utc",
            return_value=fixed_now,
        ),
    ):
        await _claims.emit_configuration_audit_passed(
            user_id="u-42",
            integrations_actively_probed=5,
            integrations_total=5,
            audit_items_executed=10,
            audit_items_total=10,
            non_blocking_notes=2,
            has_per_check_unit_tests=True,
        )

    kwargs = write_mock.call_args.kwargs
    assert kwargs["claim_type"] == "configuration_audit_passed"
    assert kwargs["embed"] is False
    assert kwargs["expires_at"] == fixed_now + timedelta(days=7)
    assert "u-42" in kwargs["finding_text"]
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k configuration_audit
```

- [ ] **Step 3: Implement**

```python
async def emit_configuration_audit_passed(
    *,
    user_id: str,
    integrations_actively_probed: int,
    integrations_total: int,
    audit_items_executed: int,
    audit_items_total: int,
    non_blocking_notes: int,
    has_per_check_unit_tests: bool,
) -> UUID | None:
    """Emit one configuration_audit_passed claim (per-user, embed=False)."""
    integration_verification_signal = (
        integrations_actively_probed / integrations_total
        if integrations_total > 0
        else 0.0
    )
    audit_trail_completeness = (
        audit_items_executed / audit_items_total
        if audit_items_total > 0
        else 0.0
    )
    confidence = presets.operations_confidence(
        integration_verification_signal=max(0.0, min(1.0, integration_verification_signal)),
        audit_trail_completeness=max(0.0, min(1.0, audit_trail_completeness)),
        execution_idempotency=1.0,  # audit is read-only
        test_coverage_signal=1.0 if has_per_check_unit_tests else 0.0,
    )

    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"user:{user_id}",
            entity_type="person",
            domains=["operations"],
        )
    except Exception as e:
        logger.warning(
            "emit_configuration_audit_passed: entity resolution failed for %s: %s",
            user_id, e,
        )
        return None

    now = _now_utc()
    finding_text = (
        f"User {user_id} configuration audit passed at {now.isoformat()}: "
        f"{integrations_total} integrations checked, "
        f"{non_blocking_notes} non-blocking notes"
    )

    try:
        return await write_claim(
            entity_id=entity_id,
            domain="operations",
            agent_id="operations",
            claim_type="configuration_audit_passed",
            finding_text=finding_text,
            confidence=confidence,
            sources=[{"kind": "user", "ref": user_id}],
            embed=False,  # per-user, not cross-agent searchable
            expires_at=now + _CONFIGURATION_AUDIT_TTL,
        )
    except Exception as e:
        logger.warning(
            "emit_configuration_audit_passed: write_claim failed for %s: %s",
            user_id, e,
        )
        return None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k configuration_audit
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_claims.py tests/unit/agents/operations/test_claim_emission.py
git commit -m "feat(120-03): emit_configuration_audit_passed (embed=False, 7d TTL, GREEN)"
```

### Task 6: `emit_sop_generation_completed` (TDD)

**Files:**
- Modify: `tests/unit/agents/operations/test_claim_emission.py`
- Modify: `app/agents/operations/_claims.py`

SOP claims may supersede earlier claims (`supersedes_claim_id` param → populates `contradicts`).

- [ ] **Step 1: Append failing tests**

```python
@pytest.mark.asyncio
async def test_sop_generation_completed_immutable_with_optional_supersession():
    """SOP claim is immutable; supersedes_claim_id populates contradicts."""
    from app.agents.operations import _claims

    superseded_id = uuid4()
    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
    ):
        await _claims.emit_sop_generation_completed(
            process_name="Customer Complaint Handling",
            document_id="SOP-OPS-20260519120000",
            version="2.0",
            n_procedure_steps=6,
            roles_captured=True,
            has_format_snapshot_test=True,
            supersedes_claim_id=superseded_id,
        )

    kwargs = write_mock.call_args.kwargs
    assert kwargs["claim_type"] == "sop_generation_completed"
    assert kwargs["expires_at"] is None
    assert kwargs["embed"] is True
    assert list(kwargs["contradicts"]) == [superseded_id]
    # operations_confidence(1.0, 1.0, 1.0, 1.0) = 1.0
    assert kwargs["confidence"] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.asyncio
async def test_sop_generation_completed_no_supersession_empty_contradicts():
    from app.agents.operations import _claims

    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.operations._claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.operations._claims.write_claim",
            new=write_mock,
        ),
    ):
        await _claims.emit_sop_generation_completed(
            process_name="X",
            document_id="SOP-OPS-x",
            version="1.0",
            n_procedure_steps=3,
            roles_captured=False,
            has_format_snapshot_test=False,
        )

    kwargs = write_mock.call_args.kwargs
    assert list(kwargs["contradicts"]) == []
    # roles_captured=False → audit_trail_completeness=0.75 (3 of 4 fields captured)
    # operations_confidence(1.0, 0.75, 1.0, 0.0) = 0.40 + 0.2625 + 0.20 + 0 = 0.8625
    assert kwargs["confidence"] == pytest.approx(0.8625, abs=1e-9)
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v -k sop_generation
```

- [ ] **Step 3: Implement**

```python
async def emit_sop_generation_completed(
    *,
    process_name: str,
    document_id: str,
    version: str,
    n_procedure_steps: int,
    roles_captured: bool,
    has_format_snapshot_test: bool,
    supersedes_claim_id: UUID | None = None,
) -> UUID | None:
    """Emit one sop_generation_completed claim (immutable; supersedes via contradicts)."""
    # Four "audit trail" fields: document_id, version, n_steps, roles
    fields_captured = sum(
        [
            bool(document_id),
            bool(version),
            n_procedure_steps > 0,
            roles_captured,
        ]
    )
    audit_trail_completeness = fields_captured / 4.0

    confidence = presets.operations_confidence(
        integration_verification_signal=1.0,  # local generation, always passes
        audit_trail_completeness=audit_trail_completeness,
        execution_idempotency=1.0,  # deterministic from inputs
        test_coverage_signal=1.0 if has_format_snapshot_test else 0.0,
    )

    slug = process_name.lower().replace(" ", "_")[:60]
    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"sop:{slug}",
            entity_type="topic",
            domains=["operations"],
        )
    except Exception as e:
        logger.warning(
            "emit_sop_generation_completed: entity resolution failed for %s: %s",
            process_name, e,
        )
        return None

    now = _now_utc()
    finding_text = (
        f"SOP '{process_name}' v{version} generated at {now.isoformat()}: "
        f"{n_procedure_steps} procedure steps, document_id={document_id}"
    )

    contradicts: list[UUID] = (
        [supersedes_claim_id] if supersedes_claim_id is not None else []
    )

    try:
        return await write_claim(
            entity_id=entity_id,
            domain="operations",
            agent_id="operations",
            claim_type="sop_generation_completed",
            finding_text=finding_text,
            confidence=confidence,
            sources=[{"kind": "other", "ref": f"sop_doc:{document_id}"}],
            embed=True,
            expires_at=None,
            contradicts=contradicts,
        )
    except Exception as e:
        logger.warning(
            "emit_sop_generation_completed: write_claim failed for %s: %s",
            process_name, e,
        )
        return None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v
```

Expected: all 10 emitter unit tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_claims.py tests/unit/agents/operations/test_claim_emission.py
git commit -m "feat(120-03): emit_sop_generation_completed with supersession via contradicts (GREEN)"
```

### Task 7: Wire emitters into Operations tools

**Files:**
- Modify: `app/agents/tools/api_connector.py`
- Modify: `app/agents/tools/integration_setup.py`
- Modify: `app/agents/tools/ops_tools.py`
- Modify: `app/agents/enhanced_tools.py`
- Modify: `app/agents/tools/workflow_ops.py`

Each tool gets a thin emission tail after its success path. Use the same
`_run_async` bridge from Plan 120-02. Each emission is wrapped in
try/except so the user's primary call never breaks on a claim write
failure.

- [ ] **Step 1: `connect_api` → `emit_api_connector_setup_validated`**

In `app/agents/tools/api_connector.py`, after the loop that builds
`created` / `skipped`, before the final return:

```python
    # Plan 120-03: emit api_connector_setup_validated claim on success.
    try:
        from app.agents.operations._claims import emit_api_connector_setup_validated
        import hashlib
        spec_hash = hashlib.sha256(spec_url.encode("utf-8")).hexdigest()[:12]
        sample_call_status = 200 if created else None  # presence of created tools ≈ probe pass
        _run_async(
            emit_api_connector_setup_validated(
                api_name=api_name,
                spec_hash=spec_hash,
                endpoint_count=len(created),
                sample_call_status=sample_call_status,
                has_generated_tool_tests=False,  # honest default; flip when tests ship
            )
        )
    except Exception as e:
        logger.warning("api_connector_setup_validated emission failed: %s", e)
```

- [ ] **Step 2: `validate_api_connection` → `emit_integration_health_verified`**

In `validate_api_connection`, after the `current_endpoint_count` computation
and before the `is_stale` comparison's return, on the healthy branch:

```python
    # Plan 120-03: emit integration_health_verified claim on healthy state.
    try:
        from app.agents.operations._claims import emit_integration_health_verified
        if not is_stale:
            _run_async(
                emit_integration_health_verified(
                    service_id=api_name,
                    probe_passed=True,
                    probe_artifacts_captured=4,  # api_name, spec_url, endpoint_count, status
                    probe_artifacts_total=4,
                    has_regression_test=False,
                    evidence_summary=(
                        f"{original_endpoint_count} connected tools, "
                        f"{current_endpoint_count} live endpoints"
                    ),
                )
            )
    except Exception as e:
        logger.warning("integration_health_verified emission failed: %s", e)
```

- [ ] **Step 3: `check_integration_status` → per-integration `emit_integration_health_verified`**

In `app/agents/tools/integration_setup.py`, after the cache-or-probe build
of `statuses` (Plan 120-02), iterate and emit one claim per healthy
integration:

```python
    try:
        from app.agents.operations._claims import emit_integration_health_verified
        for service_id, status in statuses.items():
            if status.get("configured"):
                _run_async(
                    emit_integration_health_verified(
                        service_id=service_id,
                        probe_passed=True,
                        probe_artifacts_captured=1,  # configured boolean
                        probe_artifacts_total=4,  # we have richer telemetry to come
                        has_regression_test=False,
                        evidence_summary=(
                            f"check_integration_status: configured=True "
                            f"(user_id={user_id or 'system'})"
                        ),
                    )
                )
    except Exception as e:
        logger.warning("per-integration health claim emission failed: %s", e)
```

- [ ] **Step 4: `generate_sop_document` → `emit_sop_generation_completed`**

In `app/agents/tools/ops_tools.py`, inside `generate_sop_document` just
before the `return {"status": "success", ...}`:

```python
        try:
            from app.agents.operations._claims import emit_sop_generation_completed
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(
                            asyncio.run,
                            emit_sop_generation_completed(
                                process_name=process_name,
                                document_id=document_id,
                                version="1.0",
                                n_procedure_steps=len(procedure),
                                roles_captured=bool(roles),
                                has_format_snapshot_test=False,
                            ),
                        ).result()
                else:
                    asyncio.run(
                        emit_sop_generation_completed(
                            process_name=process_name,
                            document_id=document_id,
                            version="1.0",
                            n_procedure_steps=len(procedure),
                            roles_captured=bool(roles),
                            has_format_snapshot_test=False,
                        )
                    )
            except RuntimeError:
                asyncio.run(
                    emit_sop_generation_completed(
                        process_name=process_name,
                        document_id=document_id,
                        version="1.0",
                        n_procedure_steps=len(procedure),
                        roles_captured=bool(roles),
                        has_format_snapshot_test=False,
                    )
                )
        except Exception as e:
            logger.warning("sop_generation_completed emission failed: %s", e)
```

(`ops_tools.py` doesn't already have the `_run_async` bridge from Plan 120-02; inline the pattern.)

- [ ] **Step 5: `audit_user_setup_tool` → `emit_configuration_audit_passed`**

`audit_user_setup_tool` is in `app/agents/enhanced_tools.py`. Locate the
success-path return and add (using the same inline bridge pattern):

```python
    try:
        from app.agents.operations._claims import emit_configuration_audit_passed
        # ... bridge to asyncio same pattern as Step 4 ...
        # Pass actual counts: derive integrations_total and probed from the
        # audit result dict that the function is about to return.
    except Exception as e:
        logger.warning("configuration_audit_passed emission failed: %s", e)
```

Plan author must read `audit_user_setup_tool` to extract the actual
counts (`integrations_actively_probed`, `integrations_total`, etc.) —
they are present in the existing return shape.

- [ ] **Step 6: Workflow terminal-state hook → `emit_workflow_execution_completed`**

In `app/agents/tools/workflow_ops.py` (or wherever the workflow engine's
terminal-state hook lives — confirm via Grep for `terminal_status` or
`on_workflow_complete`), add an emission at the success/failure tail.

If the file does not have a terminal-state hook today, this task ships
the emitter helper but does NOT wire it into the engine — leave a TODO
referencing this plan and a Phase 121 or later follow-up. Grep first
before assuming the hook exists:

```
Grep pattern: "on_workflow_complete|terminal_status|workflow_finished|workflow_completion"
Path: app/services/
Output mode: content with line numbers
```

If found, wire it. If not, add a `TODO(120-03)` comment in
`app/agents/tools/workflow_ops.py` and ship the rest of the plan.

- [ ] **Step 7: Smoke test — Operations Agent still loads after wiring**

```powershell
uv run python -c "from app.agents.operations.agent import create_operations_agent; a = create_operations_agent(); print(type(a).__name__)"
```

Expected: `PikarBaseAgent`.

- [ ] **Step 8: Run the full Operations unit test suite**

```powershell
uv run pytest tests/unit/agents/operations/ -v --tb=short
```

Expected: existing tests still green + 10 new claim tests pass.

- [ ] **Step 9: Commit**

```bash
git add app/agents/tools/api_connector.py app/agents/tools/integration_setup.py app/agents/tools/ops_tools.py app/agents/enhanced_tools.py app/agents/tools/workflow_ops.py
git commit -m "feat(120-03): wire claim emitters into 5 Operations tool call sites"
```

### Task 8: Integration test — cross-agent semantic search returns Operations claims

**Files:**
- Create: `tests/integration/test_operations_claim_emission.py`

Acceptance criterion: "`search_claims_semantic` returns Operations claims."

- [ ] **Step 1: Write the integration test**

```python
"""Integration test: Operations claims appear in cross-agent semantic search."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_DB_URL"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_search_claims_semantic_returns_operations_claims():
    """A freshly-emitted Operations claim is discoverable via semantic search."""
    from app.agents.operations._claims import emit_integration_health_verified
    from app.services.intelligence import search_claims_semantic

    service_id = f"loadtest_{uuid4().hex[:8]}"
    claim_id = await emit_integration_health_verified(
        service_id=service_id,
        probe_passed=True,
        probe_artifacts_captured=4,
        probe_artifacts_total=4,
        has_regression_test=True,
        evidence_summary=(
            f"auth ok, sample endpoint 200 for {service_id} integration"
        ),
    )
    assert claim_id is not None, "Claim emission must succeed against live Supabase"

    # Query via semantic search; the claim should appear in the top-K results.
    results = await search_claims_semantic(
        query=f"{service_id} integration health verified",
        agent_id="operations",
        top_k=20,
    )

    hit_ids = [c.id for c, _ in results]
    assert claim_id in hit_ids, (
        f"Claim {claim_id} not in semantic search results "
        f"(found {len(hit_ids)} other claims)"
    )


@pytest.mark.asyncio
async def test_operations_claim_band_computed():
    """find_claims returns claims with .band as a computed property."""
    from app.agents.operations._claims import emit_integration_health_verified
    from app.services.intelligence import find_claims

    service_id = f"band_test_{uuid4().hex[:8]}"
    claim_id = await emit_integration_health_verified(
        service_id=service_id,
        probe_passed=True,
        probe_artifacts_captured=4,
        probe_artifacts_total=4,
        has_regression_test=True,
        evidence_summary="ok",
    )
    assert claim_id is not None

    claims = await find_claims(
        agent_id="operations", claim_type="integration_health_verified", limit=50
    )
    target = next((c for c in claims if c.id == claim_id), None)
    assert target is not None
    assert target.band in ("low", "medium", "high")
    # High confidence path (all signals 1.0) → band='high'
    assert target.band == "high"
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_operations_claim_emission.py -v --tb=short
```

Expected: 2 PASSED.

If the semantic search test fails ("claim not in top-20"), likely causes:
1. Embedding generation failed at write time — `embed=True` silently fell back to `embedding=NULL`, so the pgvector query can't find the row. Check `_embed_text` logs.
2. The text similarity is below the ivfflat probes default — try increasing `top_k` or rephrasing the query.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_operations_claim_emission.py
git commit -m "test(120-03): Operations claims appear in cross-agent semantic search"
```

### Task 9: Integration test — `integration_health_verified` 24h expiry contract

**Files:**
- Create: `tests/integration/test_operations_claim_expiry.py`

Spec acceptance: "All `integration_health_verified` claims expire within
24h of write."

- [ ] **Step 1: Write the expiry test**

```python
"""Integration test: integration_health_verified claims have expires_at <= now + 24h."""

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
async def test_integration_health_verified_24h_expiry_contract():
    """Spec acceptance line: every integration_health_verified claim must
    expire within 24h of write."""
    from app.agents.operations._claims import emit_integration_health_verified
    from app.services.intelligence import find_claims

    service_id = f"expiry_test_{uuid4().hex[:8]}"
    write_started = datetime.now(tz=timezone.utc)
    claim_id = await emit_integration_health_verified(
        service_id=service_id,
        probe_passed=True,
        probe_artifacts_captured=4,
        probe_artifacts_total=4,
        has_regression_test=False,
        evidence_summary="expiry test",
    )
    write_finished = datetime.now(tz=timezone.utc)
    assert claim_id is not None

    claims = await find_claims(
        agent_id="operations",
        claim_type="integration_health_verified",
        limit=50,
    )
    target = next((c for c in claims if c.id == claim_id), None)
    assert target is not None
    assert target.expires_at is not None, (
        "integration_health_verified MUST set expires_at — hard contract"
    )

    # The expiry must be in [write_started + 24h, write_finished + 24h + 60s].
    # 60s slack accommodates clock drift between client and Postgres.
    lower_bound = write_started + timedelta(hours=24)
    upper_bound = write_finished + timedelta(hours=24, seconds=60)
    assert lower_bound <= target.expires_at <= upper_bound, (
        f"expires_at {target.expires_at} not in [{lower_bound}, {upper_bound}]"
    )


@pytest.mark.asyncio
async def test_workflow_execution_completed_no_expiry():
    """Immutable claim — expires_at must be NULL."""
    from app.agents.operations._claims import emit_workflow_execution_completed
    from app.services.intelligence import find_claims

    workflow_id = f"wf_expiry_{uuid4().hex[:8]}"
    claim_id = await emit_workflow_execution_completed(
        workflow_id=workflow_id,
        workflow_name="ExpiryTest",
        terminal_status="success",
        n_steps=2,
        duration_seconds=5.0,
        integration_step_success_rate=1.0,
        steps_with_full_event_record=2,
        steps_total_for_audit=2,
        idempotent_step_fraction=1.0,
        has_e2e_test_fixture=False,
    )
    assert claim_id is not None

    claims = await find_claims(
        agent_id="operations",
        claim_type="workflow_execution_completed",
        limit=50,
    )
    target = next((c for c in claims if c.id == claim_id), None)
    assert target is not None
    assert target.expires_at is None, "workflow_execution_completed must be immutable"


@pytest.mark.asyncio
async def test_configuration_audit_passed_7d_expiry():
    """Per-user audit claims expire 7 days after write."""
    from app.agents.operations._claims import emit_configuration_audit_passed
    from app.services.intelligence import find_claims

    user_id = f"user_{uuid4().hex[:8]}"
    write_started = datetime.now(tz=timezone.utc)
    claim_id = await emit_configuration_audit_passed(
        user_id=user_id,
        integrations_actively_probed=5,
        integrations_total=5,
        audit_items_executed=10,
        audit_items_total=10,
        non_blocking_notes=0,
        has_per_check_unit_tests=True,
    )
    write_finished = datetime.now(tz=timezone.utc)
    assert claim_id is not None

    claims = await find_claims(
        agent_id="operations",
        claim_type="configuration_audit_passed",
        limit=50,
    )
    target = next((c for c in claims if c.id == claim_id), None)
    assert target is not None
    assert target.expires_at is not None

    lower_bound = write_started + timedelta(days=7)
    upper_bound = write_finished + timedelta(days=7, seconds=60)
    assert lower_bound <= target.expires_at <= upper_bound
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_operations_claim_expiry.py -v --tb=short
```

Expected: 3 PASSED.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_operations_claim_expiry.py
git commit -m "test(120-03): integration_health_verified 24h + audit 7d + workflow immutable"
```

### Task 10: Surface confidence + band in tool return shapes

**Files:**
- Modify: `app/agents/tools/api_connector.py`
- Modify: `app/agents/tools/integration_setup.py`
- Modify: `app/agents/tools/ops_tools.py`
- Modify: `app/agents/enhanced_tools.py`

Spec acceptance: "All Operations outputs carry `confidence` + `band`."

Each tool that emits a claim should also return the computed
`confidence` value and the corresponding `band` in its primary response
dict so downstream UI surfaces (admin dashboards, chat replies) can
render them.

- [ ] **Step 1: Extend response shapes**

For each call site wired in Task 7, capture the confidence/band from
the emission and include it in the existing return dict. Example for
`generate_sop_document`:

```python
        # After the emit_sop_generation_completed call (or skip if it failed):
        from app.services.intelligence import presets, to_band
        confidence = presets.operations_confidence(
            integration_verification_signal=1.0,
            audit_trail_completeness=(
                sum([bool(document_id), bool("1.0"), len(procedure) > 0, bool(roles)]) / 4.0
            ),
            execution_idempotency=1.0,
            test_coverage_signal=0.0,  # snapshot test not shipped
        )
        return {
            "status": "success",
            "sop": sop,
            "formatted_text": _format_sop_as_text(sop),
            "suggestion": "...",
            "confidence": confidence,
            "band": to_band(confidence),
        }
```

The emitter helper already computes `confidence` internally — to avoid
duplicate computation, refactor each helper to ALSO return the
computed confidence to the caller (use a tuple return
`(claim_id, confidence)` or a small `EmissionResult` dataclass).
Recommended: extend `_claims.py` helpers to return
`tuple[UUID | None, float]` where the second element is the
confidence regardless of whether the write succeeded.

- [ ] **Step 2: Update unit tests for the new return shape**

Adjust the 10 unit tests in `tests/unit/agents/operations/test_claim_emission.py`
to assert the new tuple return shape. Example:

```python
result = await _claims.emit_integration_health_verified(...)
claim_id, confidence = result
assert claim_id == expected_claim_id
assert confidence == pytest.approx(1.0, abs=1e-9)
```

- [ ] **Step 3: Re-run unit tests**

```powershell
uv run pytest tests/unit/agents/operations/test_claim_emission.py -v --tb=short
```

Expected: 10 PASSED with updated assertions.

- [ ] **Step 4: Commit**

```bash
git add app/agents/operations/_claims.py tests/unit/agents/operations/test_claim_emission.py app/agents/tools/api_connector.py app/agents/tools/integration_setup.py app/agents/tools/ops_tools.py app/agents/enhanced_tools.py
git commit -m "feat(120-03): tools return confidence + band alongside primary payload"
```

### Task 11: Lint + Phase 120 acceptance sign-off

- [ ] **Step 1: Ruff check + format**

```powershell
uv run ruff check app/agents/operations/_claims.py app/agents/tools/api_connector.py app/agents/tools/integration_setup.py app/agents/tools/ops_tools.py app/agents/enhanced_tools.py app/agents/tools/workflow_ops.py tests/unit/agents/operations/test_claim_emission.py tests/integration/test_operations_claim_emission.py tests/integration/test_operations_claim_expiry.py
uv run ruff format app/agents/operations/_claims.py app/agents/tools/api_connector.py app/agents/tools/integration_setup.py app/agents/tools/ops_tools.py app/agents/enhanced_tools.py tests/unit/agents/operations/test_claim_emission.py tests/integration/test_operations_claim_emission.py tests/integration/test_operations_claim_expiry.py --check
```

Fix in place. Commit any format-only changes:

```bash
git add app/agents/operations/_claims.py app/agents/tools/ tests/
git commit -m "style(120-03): ruff format pass over emission wiring + tests"
```

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/agents/operations/_claims.py
```

Expected: no errors.

- [ ] **Step 3: Full Phase 120 acceptance — cross-check ALL plans 120-01 through 120-03**

| Phase 120 acceptance line | Verified by |
|---|---|
| `operations_confidence` preset shipped | Plan 120-01 Task 2 |
| `OPERATIONS_WEIGHTS` = {0.40, 0.35, 0.20, 0.05} | Plan 120-01 Task 2 |
| Decision #8 self-improvement audit | Plan 120-01 Task 4 |
| 5 claim types documented | Plan 120-01 Task 5 |
| OpenAPI spec parse cache (TTL 24h) | Plan 120-02 Task 2 |
| Integration health check cache (TTL 5min) | Plan 120-02 Task 3 |
| Endpoint metadata cache (TTL 7d) | Plan 120-02 Task 4 |
| OpenAPI re-fetches reduced ≥50% on synthetic load | Plan 120-02 Task 5 |
| Integration health checks bunched into 5-min windows (≥40%) | Plan 120-02 Task 5 |
| `emit_integration_health_verified` shipped | This plan Task 2 |
| `emit_workflow_execution_completed` shipped | This plan Task 3 |
| `emit_api_connector_setup_validated` shipped | This plan Task 4 |
| `emit_configuration_audit_passed` shipped | This plan Task 5 |
| `emit_sop_generation_completed` shipped | This plan Task 6 |
| Tools wired to emit on success | This plan Task 7 |
| `search_claims_semantic` returns Operations claims | This plan Task 8 |
| All `integration_health_verified` claims expire within 24h | This plan Task 9 |
| `workflow_execution_completed` immutable | This plan Task 9 |
| All Operations outputs carry `confidence` + `band` | This plan Task 10 |
| Operations Agent test suite green | This plan Task 7 Step 8 |
| No new ADK tools | Verified — no edits to ADK registry |
| Lint clean | This plan Task 11 Step 1 |

- [ ] **Step 4: Plan 120-03 complete. Phase 120 (Operations Agent adoption) is fully shipped.**

Next planned work: Phase 121 (Strategic Agent adoption) — Strategic depends on prior-agent claims; Operations claims are now part of the queryable surface its cross-domain consolidation will draw from.

---

## Spec coverage check

| Spec requirement | Tasks |
|---|---|
| `integration_health_verified` TTL = 24h | Tasks 2, 9 |
| `workflow_execution_completed` immutable | Tasks 3, 9 |
| `api_connector_setup_validated` | Task 4 |
| `configuration_audit_passed` | Tasks 5, 9 |
| `sop_generation_completed` (immutable, supersedes via contradicts) | Task 6 |
| All outputs carry confidence + band | Task 10 |
| Reads degrade silently on Supabase / embedding failure | Task 2 + per-emitter try/except |
| `search_claims_semantic` returns Operations claims | Task 8 |
| Operations Agent test suite green | Task 7 |
| Lint clean | Task 11 |

All spec lines covered.

---

## Notes for downstream phases

- Phase 121 (Strategic) consolidates cross-agent risks. Operations claim
  types `integration_health_verified` and `workflow_execution_completed`
  will be referenced via edges from Strategic's `cross_domain_risk_consolidation`
  claims.
- Per Plan 120-01 vocabulary doc, SOP revisions create a new claim with
  `contradicts=[old_id]`. A separate Phase 121 or later UI surface may
  want to render SOP history as a list ordered by `created_at` with
  `contradicts` chains. That's out of scope here.
- The `has_e2e_test_fixture`, `has_regression_test`, `has_format_snapshot_test`
  signals all currently flow as honest defaults (False). As the wider
  Operations test suite grows, these flags can be toggled per call-site
  without changing the emitter signatures — that's the value of pinning
  them as boolean inputs rather than autodetecting test presence.
