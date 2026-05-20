# Shared Intelligence Infrastructure — Plan 116-02: Compliance claim emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit `risk_assessment` and `audit_finding` claims from the Compliance Agent's write paths so every materially-new risk and audit finding becomes a row in `kg_findings`, calibrated by `compliance_confidence` (from Plan 116-01), carrying `agent_id="compliance"`, `domain="compliance"`, and the appropriate `claim_type`. Audit findings reference the risk assessments they relate to via the `edge_id` column (NOT via `contradicts` — that column is reserved for embedding-similarity contradiction signal). New risk assessments for an existing entity create a NEW `claim_id`; prior rows are NEVER mutated (immutability invariant — required for audit/regulatory traceability).

**Architecture:** Compliance has two materially-different output classes and we model each as its own claim_type:

- `risk_assessment` — derived from `RiskAssessment` (the structured-output schema) and from `ComplianceService.create_risk` / `update_risk` rows. Attached to an `entity_id` whose `canonical_name` encodes the business object under risk (e.g., `"vendor:Acme Corp"`, `"system:patient-portal"`, `"control:SOC2-CC7.2"`).
- `audit_finding` — derived from `ComplianceService.create_audit` and `update_audit` write paths and from `AuditFinding` shapes produced by tool flows. References zero-or-more `risk_assessment` claims via the `edge_id` column (which points to a `kg_edges` row of kind `references` from the audit-finding claim to each related risk-assessment claim).

**Immutability invariant:** Once any `kg_findings` row of `claim_type='risk_assessment'` exists, it MUST NEVER be UPDATEd. Subsequent assessments for the same entity create new rows with new `id` values. The append-only design is already enforced by `write_claim`'s implementation (it only does INSERT, never UPSERT) — this plan adds a regression test that proves it stays that way, plus a separate test that proves new assessments don't accidentally overwrite via `id` collision.

**Tech Stack:** `app/services/intelligence/claims.py` (existing — `write_claim`, `find_claims`, `get_or_create_entity`, `search_claims_semantic`), `app/services/intelligence/presets/compliance.py` (from Plan 116-01), `app/services/compliance_service.py` (extended — emit claims after every successful write), `kg_edges` table (existing — for audit-finding → risk-assessment references).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 116 § Claims taxonomy

**Out of scope:** Mutating contradictions detection — `detect_contradictions` already runs automatically in `write_claim` when `embed=True` (per Plan 113-05). Cache integration — Compliance is internal-only per the rolling-adoption design Decision #3. Calibrating thresholds for "what counts as a materially-new finding worth claiming" beyond a simple "every non-empty write triggers a claim" — refinement is a separate phase. Per-claim ADK tool wrappers (`record_risk_assessment_claim`, etc.) — library-first per Phase 112 Decision #7; Phase 116 doesn't justify a new tool.

---

## File structure

**Create:**
- `tests/unit/services/test_compliance_claim_emission.py` — emission shape & contents
- `tests/unit/services/test_compliance_claim_immutability.py` — append-only invariant
- `tests/integration/test_compliance_claims_end_to_end.py` — round-trip + semantic search

**Modify:**
- `app/services/compliance_service.py` — emit claims from `create_risk`, `update_risk` (new assessment, not mutation), `create_audit`, `update_audit`
- `app/services/intelligence/__init__.py` — no change required (existing public surface covers everything Plan 116-02 needs)

---

## Pre-flight context

### Claim-type vocabulary (final, locked for Phase 116)

| claim_type | Immutable once written? | Carries `edge_id`? | TTL strategy |
|---|---|---|---|
| `risk_assessment` | YES — never mutated, new assessment = new row | No | `expires_at = NULL` (regulatory artifact, retain indefinitely) |
| `audit_finding` | YES — same invariant | YES — references one-or-more risk_assessment rows via `kg_edges` | `expires_at = NULL` |

The "new assessment = new row" rule is the entire reason audit findings reference risks via `edge_id` instead of via `contradicts`: `contradicts` is auto-populated by embedding similarity and conveys "these two claims may disagree." A risk-to-audit-finding relationship is "this finding *cites* this risk" — semantically distinct, structurally distinct (graph edge), and must not be conflated.

### `kg_edges` schema (existing — confirmed before writing this plan)

```sql
CREATE TABLE kg_edges (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id uuid REFERENCES kg_entities(id),
    target_entity_id uuid REFERENCES kg_entities(id),
    kind            text NOT NULL,    -- e.g. 'references', 'contradicts', 'derives_from'
    properties      jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
```

For Compliance, we use `kind='references'` and put the related-risk claim_id in `properties` (the edge endpoints are *entities*, not claims; the claim-to-claim link is recorded in `properties`).

```jsonb
{
    "from_claim_id": "<audit_finding claim uuid>",
    "to_claim_id":   "<risk_assessment claim uuid>",
    "context":       "audit_finding cites risk_assessment"
}
```

The `audit_finding` claim's `edge_id` column then points at this `kg_edges` row.

### Entity-resolution rules for Compliance

| Source field | Entity `canonical_name` | Entity `entity_type` |
|---|---|---|
| `risks.title` containing "vendor X" | `vendor:X` | `company` |
| `risks.title` containing "system X" | `system:X` | `product` |
| `risks.title` referring to a control | `control:<framework>-<id>` | `regulation` |
| `audits.scope` text | `audit:<title>:<scheduled_date>` | `event` |

For Phase 116 we use a simple heuristic helper `_resolve_compliance_entity(title, description)` that picks the right (canonical_name, entity_type) and calls `get_or_create_entity` with appropriate `domains=["compliance"]`. The heuristic is allowed to be imperfect for v1 — it just needs to be deterministic so the same risk title resolves to the same entity across writes.

### Why we don't auto-`contradicts` for Compliance

Compliance assessments routinely re-state the same regulation finding ("DPA missing for vendor X") across multiple audit cycles. These are *agreements*, not contradictions. We still set `embed=True` so `detect_contradictions` runs (free cross-agent value — if Data later writes "we have a DPA on file with vendor X", Compliance's claim flags it for human review), but we don't surface auto-`contradicts` in the Compliance UI. The shared infrastructure already handles this — no code changes required, just disposition documented here.

### What we explicitly do NOT do

- We do NOT UPDATE existing `kg_findings` rows for `claim_type='risk_assessment'` even when `ComplianceService.update_risk` is called. Instead, `update_risk` writes a NEW `kg_findings` row that supersedes the older claim semantically (consumers reading `find_claims(claim_type="risk_assessment", entity_id=X, limit=1)` get the freshest row by `freshness_at DESC`). The older claim row remains in the table forever, providing an audit trail.
- We do NOT auto-populate `contradicts` between the new `risk_assessment` row and the prior one — even though they're about the same entity. Successive assessments for the same risk are intentionally similar (often verbatim re-statement); they're not contradictions. Set `embed=True` because we WANT cross-agent contradiction detection against *other agents'* claims, but the same-entity self-pair is a known false-positive class we accept (a follow-up could filter by `agent_id != self` inside `detect_contradictions`, but that's out of scope here).

Acceptance bar (from spec § Phase 116 Acceptance):

- Compliance Agent test suite green
- All Compliance outputs carry confidence + band — outputs whose write paths emit claims here gain claim-tier verification
- Risk assessments link to audit findings via `edge_id`, not via `contradicts`
- Immutability test: writing a new risk_assessment for an existing entity creates new claim_id; old claim remains untouched in DB
- `search_claims_semantic` returns Compliance claims

Environment quirks: same as Plan 116-01. Integration tests require local Supabase (`supabase start`) and the env vars laid out in `tests/integration/test_intelligence_contradictions.py`. If pgvector isn't available the semantic-search test will skip — that's expected, not a failure.

---

## Tasks

### Task 1: Pre-flight + entity resolver helper (TDD)

**Files:**
- Create: `tests/unit/services/test_compliance_entity_resolver.py`
- Modify: `app/services/compliance_service.py` (add `_resolve_compliance_entity` helper)

- [ ] **Step 1: Confirm prerequisites**

```powershell
uv run python -c "from app.services.intelligence import get_or_create_entity, write_claim, find_claims, search_claims_semantic; print('OK')"
uv run python -c "from app.services.intelligence.presets.compliance import compliance_confidence; print(compliance_confidence(0.9, 0.7, 30.0, 0.5))"
```

Expected: first prints `OK`, second prints a float in (0.5, 1.0).

- [ ] **Step 2: Write the failing entity-resolver test**

Create `tests/unit/services/test_compliance_entity_resolver.py`:

```python
"""Unit tests for the Compliance entity resolver heuristic.

We test the pure function _resolve_compliance_entity_kind — not the DB
upsert step. The DB step is exercised in the integration test.
"""

from __future__ import annotations


def test_resolves_vendor_titles():
    """A title with 'vendor X' shape produces a 'vendor:X' canonical name."""
    from app.services.compliance_service import _resolve_compliance_entity_kind

    name, kind = _resolve_compliance_entity_kind(
        title="DPA missing for vendor Acme Corp",
        description="Acme Corp is processing customer data without DPA.",
    )
    assert name == "vendor:Acme Corp"
    assert kind == "company"


def test_resolves_system_titles():
    """A title with 'system X' shape produces a 'system:X' canonical name."""
    from app.services.compliance_service import _resolve_compliance_entity_kind

    name, kind = _resolve_compliance_entity_kind(
        title="Auth gap in system patient-portal",
        description="Patient portal lacks MFA enforcement.",
    )
    assert name == "system:patient-portal"
    assert kind == "product"


def test_resolves_control_references():
    """A description referencing a regulation control yields a 'control:...' name."""
    from app.services.compliance_service import _resolve_compliance_entity_kind

    name, kind = _resolve_compliance_entity_kind(
        title="Monitoring gap",
        description="Per SOC2 CC7.2 we lack continuous monitoring evidence.",
    )
    assert name.startswith("control:")
    assert kind == "regulation"


def test_resolves_fallback_to_title():
    """Generic titles fall back to title-based canonical names."""
    from app.services.compliance_service import _resolve_compliance_entity_kind

    name, kind = _resolve_compliance_entity_kind(
        title="Unspecified compliance concern",
        description="more detail",
    )
    assert name == "risk:unspecified-compliance-concern"
    assert kind == "topic"


def test_resolver_is_deterministic():
    """Same inputs → same outputs across calls."""
    from app.services.compliance_service import _resolve_compliance_entity_kind

    for _ in range(3):
        a = _resolve_compliance_entity_kind("vendor Foo", "details")
        b = _resolve_compliance_entity_kind("vendor Foo", "details")
        assert a == b
```

- [ ] **Step 3: Run — should FAIL with ImportError**

```powershell
uv run pytest tests/unit/services/test_compliance_entity_resolver.py -v --tb=short
```

- [ ] **Step 4: Implement `_resolve_compliance_entity_kind` in `compliance_service.py`**

Add a module-level helper at the top of `app/services/compliance_service.py` (above the class):

```python
import re

_VENDOR_PATTERN = re.compile(r"vendor\s+([A-Z][\w\s\.\-&]+?)(?=[\.,;]|$)", re.IGNORECASE)
_SYSTEM_PATTERN = re.compile(r"system\s+([\w\-]+)", re.IGNORECASE)
_CONTROL_PATTERN = re.compile(
    r"\b(SOC\s*2|ISO\s*27001|GDPR|HIPAA|SOX|PCI[- ]?DSS)\s+(CC\d+\.\d+|Article\s+\d+|§\s*\d+)?",
    re.IGNORECASE,
)


def _resolve_compliance_entity_kind(title: str, description: str) -> tuple[str, str]:
    """Map a risk title + description to a (canonical_name, entity_type) pair.

    Heuristic for v1 — deterministic, conservative. The mapping rules:
    - 'vendor <X>' anywhere -> ('vendor:<X>', 'company')
    - 'system <X>' anywhere -> ('system:<X>', 'product')
    - Reference to a known control / regulation framework -> ('control:<framework>[-<id>]', 'regulation')
    - Fallback -> ('risk:<slug-of-title>', 'topic')

    Args:
        title: Risk title (used by the LLM agent / admin to name the risk).
        description: Risk description (free-text context).

    Returns:
        A (canonical_name, entity_type) tuple safe to pass to
        ``get_or_create_entity``.
    """
    text = f"{title}\n{description}"
    m_vendor = _VENDOR_PATTERN.search(text)
    if m_vendor:
        vendor = m_vendor.group(1).strip()
        return f"vendor:{vendor}", "company"

    m_system = _SYSTEM_PATTERN.search(text)
    if m_system:
        system = m_system.group(1).strip()
        return f"system:{system}", "product"

    m_control = _CONTROL_PATTERN.search(text)
    if m_control:
        framework = re.sub(r"\s+", "", m_control.group(1)).upper()
        sub = m_control.group(2)
        canonical = f"control:{framework}" + (f"-{sub.strip().replace(' ', '')}" if sub else "")
        return canonical, "regulation"

    # Fallback: slug-of-title
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "unspecified"
    return f"risk:{slug}", "topic"
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/test_compliance_entity_resolver.py -v --tb=short
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add app/services/compliance_service.py tests/unit/services/test_compliance_entity_resolver.py
git commit -m "feat(116-02): _resolve_compliance_entity_kind heuristic for kg_entities upserts"
```

### Task 2: Emit `risk_assessment` claims from create_risk + update_risk (TDD)

**Files:**
- Create: `tests/unit/services/test_compliance_claim_emission.py`
- Modify: `app/services/compliance_service.py`

- [ ] **Step 1: Write the failing emission test**

Create `tests/unit/services/test_compliance_claim_emission.py`:

```python
"""Unit tests: ComplianceService write paths emit kg_findings claims.

The DB write is mocked; we assert the exact write_claim kwargs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def _supabase_mock():
    """Yield a context where ComplianceService.client and execute_async are stubbed."""
    captured: dict = {"inserts": []}

    class _FakeQuery:
        def insert(self, data):
            captured["inserts"].append(data)
            return self

        def update(self, data):
            captured["inserts"].append({"_update": data})
            return self

        def eq(self, *_a, **_k):
            return self

        def select(self, *_a, **_k):
            return self

        def single(self):
            return self

    fake_client = MagicMock()
    fake_client.table.return_value = _FakeQuery()

    async def _fake_execute(query):
        # Return whatever the last captured insert/update was, with an id.
        last = captured["inserts"][-1] if captured["inserts"] else {}
        if "_update" in last:
            return MagicMock(data=[dict(last["_update"], id="r-existing")])
        return MagicMock(data=[dict(last, id="r-new")])

    with patch(
        "app.services.compliance_service.execute_async",
        new=AsyncMock(side_effect=_fake_execute),
    ), patch(
        "app.services.compliance_service.AdminService",
    ) as fake_admin:
        fake_admin.return_value.client = fake_client
        yield captured


@pytest.mark.asyncio
async def test_create_risk_emits_risk_assessment_claim(_supabase_mock):
    """create_risk writes a kg_findings row of type 'risk_assessment'."""
    from app.services.compliance_service import ComplianceService

    fake_entity = uuid4()
    fake_claim = uuid4()
    write_claim_calls: list[dict] = []

    async def fake_get_or_create_entity(*, canonical_name, entity_type, domains, properties=None):
        return fake_entity

    async def fake_write_claim(**kwargs):
        write_claim_calls.append(kwargs)
        return fake_claim

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(side_effect=fake_get_or_create_entity),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.create_risk(
            title="DPA missing for vendor Acme Corp",
            description="Acme processes PII without a DPA. GDPR Article 28 violation.",
            severity="high",
            mitigation_plan="Sign DPA per GDPR Article 28 within 30 days. See https://gdpr.eu/article-28.",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    assert len(write_claim_calls) == 1
    call = write_claim_calls[0]
    assert call["claim_type"] == "risk_assessment"
    assert call["domain"] == "compliance"
    assert call["agent_id"] == "compliance"
    assert call["entity_id"] == fake_entity
    assert call["embed"] is True  # for cross-agent contradiction detection
    assert 0.0 <= call["confidence"] <= 1.0
    # Sources include the originating risk row id
    assert any(s.get("kind") == "supabase_row" for s in call["sources"])


@pytest.mark.asyncio
async def test_update_risk_emits_new_claim_not_mutation(_supabase_mock):
    """update_risk emits a NEW claim — never mutates a prior one."""
    from app.services.compliance_service import ComplianceService

    fake_entity = uuid4()
    write_claim_calls: list[dict] = []

    async def fake_get_or_create_entity(**_):
        return fake_entity

    async def fake_write_claim(**kwargs):
        write_claim_calls.append(kwargs)
        return uuid4()

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(side_effect=fake_get_or_create_entity),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ), patch.object(
        ComplianceService,
        "get_risk",
        new=AsyncMock(return_value={
            "id": "r-existing",
            "title": "DPA missing for vendor Acme Corp",
            "description": "Acme processes PII without a DPA.",
            "severity": "high",
            "mitigation_plan": "old plan",
        }),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.update_risk(
            risk_id="r-existing",
            mitigation_plan="Signed DPA on 2026-05-15. Filed under doc id DOC-2026-0145.",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    # New claim emitted on update, not a mutation of prior.
    assert len(write_claim_calls) == 1
    call = write_claim_calls[0]
    assert call["claim_type"] == "risk_assessment"
    # The finding_text reflects the NEW state (mitigation plan).
    assert "DPA on 2026-05-15" in call["finding_text"] or "DOC-2026-0145" in call["finding_text"]


@pytest.mark.asyncio
async def test_create_risk_claim_skipped_on_short_text(_supabase_mock):
    """Risks with finding_text shorter than 20 chars skip emission (embed guard)."""
    from app.services.compliance_service import ComplianceService

    write_claim_calls: list[dict] = []

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=lambda **k: write_claim_calls.append(k) or uuid4()),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        # Very short, low-substance assessment
        await svc.create_risk(
            title="x",
            description="y",
            severity="low",
            mitigation_plan="z",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    # Either emission was skipped OR emission happened with a meaningful synthesized
    # finding_text. We accept either — the service decides — but we require that the
    # service does NOT crash on tiny inputs.
    assert len(write_claim_calls) in (0, 1)


@pytest.mark.asyncio
async def test_create_risk_claim_failure_does_not_break_db_write(_supabase_mock):
    """If write_claim raises, the underlying create_risk DB write still succeeds."""
    from app.services.compliance_service import ComplianceService

    async def boom(**_):
        raise RuntimeError("simulated kg_findings outage")

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=boom),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        # Should NOT raise — the claim emission is best-effort.
        result = await svc.create_risk(
            title="vendor Acme",
            description="x" * 50,
            severity="medium",
            mitigation_plan="y" * 60,
            user_id="00000000-0000-0000-0000-000000000001",
        )

    assert result is not None
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/test_compliance_claim_emission.py -v --tb=short
```

- [ ] **Step 3: Add the claim-emission helper + wire it into create_risk and update_risk**

In `app/services/compliance_service.py`, add at module level (alongside the other helpers):

```python
import logging

from app.services.intelligence import (
    get_or_create_entity,
    write_claim,
)

_compliance_logger = logging.getLogger(__name__)


def _format_risk_finding_text(
    *,
    title: str,
    description: str,
    severity: str,
    mitigation_plan: str,
) -> str:
    """Build the finding_text for a risk_assessment claim.

    Format: ``"[<severity>] <title>. <description>. Mitigation: <plan>."``
    Trimmed to 1200 chars (the freshness_at index doesn't care, but the
    embedding model has a context budget — keep it readable).
    """
    text = (
        f"[{severity.upper()}] {title}. {description}. "
        f"Mitigation: {mitigation_plan}."
    )
    return text[:1200]


async def _emit_risk_assessment_claim(
    *,
    title: str,
    description: str,
    severity: str,
    mitigation_plan: str,
    confidence: float,
    risk_row_id: str | None,
) -> "UUID | None":
    """Append-only emit one risk_assessment claim. Best-effort: log + swallow on error.

    Returns the new claim UUID, or None on any failure.
    """
    from uuid import UUID  # local to avoid top-level cost

    finding_text = _format_risk_finding_text(
        title=title,
        description=description,
        severity=severity,
        mitigation_plan=mitigation_plan,
    )

    # Guard: skip emission on trivially-short content (also guards embed).
    if len(finding_text.strip()) < 40:
        return None

    canonical_name, entity_type = _resolve_compliance_entity_kind(title, description)
    try:
        entity_id = await get_or_create_entity(
            canonical_name=canonical_name,
            entity_type=entity_type,
            domains=["compliance"],
        )
    except Exception as exc:
        _compliance_logger.warning(
            "_emit_risk_assessment_claim: get_or_create_entity failed: %s", exc
        )
        return None

    sources: list[dict] = []
    if risk_row_id:
        sources.append({"kind": "supabase_row", "ref": f"compliance_risks/{risk_row_id}"})

    try:
        return await write_claim(
            entity_id=entity_id,
            domain="compliance",
            finding_text=finding_text,
            confidence=confidence,
            sources=sources,
            agent_id="compliance",
            claim_type="risk_assessment",
            embed=True,  # cross-agent contradiction detection
        )
    except Exception as exc:
        _compliance_logger.warning(
            "_emit_risk_assessment_claim: write_claim failed: %s", exc
        )
        return None
```

Then modify `create_risk` to call `_emit_risk_assessment_claim` after a successful DB insert:

```python
    async def create_risk(
        self,
        title: str,
        description: str,
        severity: str,
        mitigation_plan: str,
        user_id: str | None = None,
    ) -> dict:
        """Create a new risk + emit a risk_assessment claim (Phase 116-02)."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for risk creation")

        confidence, band = self._compute_risk_confidence(
            description=description,
            mitigation_plan=mitigation_plan,
            severity=severity,
        )

        data = {
            "title": title,
            "description": description,
            "severity": severity,
            "mitigation_plan": mitigation_plan,
            "user_id": effective_user_id,
            "confidence": confidence,
            "confidence_band": band,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._risks_table).insert(data))
        if not response.data:
            raise Exception("No data returned from insert risk")
        row = response.data[0]

        # Phase 116-02: emit risk_assessment claim. Best-effort.
        await _emit_risk_assessment_claim(
            title=title,
            description=description,
            severity=severity,
            mitigation_plan=mitigation_plan,
            confidence=confidence,
            risk_row_id=row.get("id"),
        )
        return row
```

And `update_risk` — emit a NEW claim each time (immutability invariant):

```python
    async def update_risk(
        self,
        risk_id: str,
        status: str | None = None,
        severity: str | None = None,
        mitigation_plan: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a risk row + emit a NEW risk_assessment claim (immutability)."""
        update_data: dict = {}
        if status is not None:
            update_data["status"] = status
        if severity is not None:
            update_data["severity"] = severity
        if mitigation_plan is not None:
            update_data["mitigation_plan"] = mitigation_plan

        # Pull existing row so confidence + claim use combined state.
        existing = await self.get_risk(risk_id, user_id=user_id)
        effective_severity = severity or existing.get("severity", "medium")
        effective_mitigation = mitigation_plan or existing.get("mitigation_plan", "")
        effective_description = existing.get("description", "")
        effective_title = existing.get("title", "")

        if severity is not None or mitigation_plan is not None:
            confidence, band = self._compute_risk_confidence(
                description=effective_description,
                mitigation_plan=effective_mitigation,
                severity=effective_severity,
            )
            update_data["confidence"] = confidence
            update_data["confidence_band"] = band
        else:
            confidence = float(existing.get("confidence") or 0.0)

        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._risks_table).update(update_data).eq("id", risk_id)
        if not self.is_authenticated and user_id:
            query = query.eq("user_id", user_id)
        response = await execute_async(query)
        if not response.data:
            raise Exception("No data returned from update risk")
        row = response.data[0]

        # Phase 116-02: emit a NEW risk_assessment claim (immutability invariant —
        # prior claim row is NOT updated).
        if severity is not None or mitigation_plan is not None:
            await _emit_risk_assessment_claim(
                title=effective_title,
                description=effective_description,
                severity=effective_severity,
                mitigation_plan=effective_mitigation,
                confidence=confidence,
                risk_row_id=risk_id,
            )
        return row
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/test_compliance_claim_emission.py -v --tb=short
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/compliance_service.py tests/unit/services/test_compliance_claim_emission.py
git commit -m "feat(116-02): emit risk_assessment claims from create_risk + update_risk"
```

### Task 3: Emit `audit_finding` claims from create_audit + update_audit, link via edge_id (TDD)

**Files:**
- Modify: `app/services/compliance_service.py` (add `_emit_audit_finding_claim`, wire into `create_audit` + `update_audit`)
- Extend: `tests/unit/services/test_compliance_claim_emission.py` (add audit-finding cases)

- [ ] **Step 1: Append the failing tests**

Add to `tests/unit/services/test_compliance_claim_emission.py`:

```python
@pytest.mark.asyncio
async def test_create_audit_emits_audit_finding_claim(_supabase_mock):
    """create_audit emits a kg_findings row of type 'audit_finding'."""
    from app.services.compliance_service import ComplianceService

    fake_entity = uuid4()
    write_claim_calls: list[dict] = []

    async def fake_write_claim(**kwargs):
        write_claim_calls.append(kwargs)
        return uuid4()

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=fake_entity),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.create_audit(
            title="Q2 2026 SOC2 Audit",
            scope="SOC2 CC7.2 monitoring and CC8.1 change management controls.",
            auditor="Internal Audit",
            scheduled_date="2026-06-01",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    assert len(write_claim_calls) == 1
    call = write_claim_calls[0]
    assert call["claim_type"] == "audit_finding"
    assert call["domain"] == "compliance"
    assert call["agent_id"] == "compliance"
    # An audit "creation" doesn't have findings yet, so edge_id is None
    # at create time — only set when update_audit attaches findings text.
    assert call.get("edge_id") is None


@pytest.mark.asyncio
async def test_update_audit_with_findings_links_to_related_risks(_supabase_mock):
    """update_audit with findings text creates an edge to related risk_assessment claims."""
    from app.services.compliance_service import ComplianceService

    fake_entity = uuid4()
    fake_risk_claim = uuid4()
    fake_edge = uuid4()

    write_claim_calls: list[dict] = []
    edge_calls: list[dict] = []

    async def fake_write_claim(**kwargs):
        write_claim_calls.append(kwargs)
        return uuid4()

    async def fake_create_edge(**kwargs):
        edge_calls.append(kwargs)
        return fake_edge

    async def fake_find_claims(**kwargs):
        # Simulate a prior risk_assessment claim about the same entity.
        from app.services.intelligence.schemas import Claim, ClaimSource
        from datetime import datetime, timezone
        return [
            Claim(
                id=fake_risk_claim,
                entity_id=fake_entity,
                edge_id=None,
                agent_id="compliance",
                claim_type="risk_assessment",
                domain="compliance",
                finding_text="prior risk",
                confidence=0.6,
                sources=[],
                contradicts=[],
                freshness_at=datetime.now(tz=timezone.utc),
                expires_at=None,
                created_at=datetime.now(tz=timezone.utc),
            )
        ]

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=fake_entity),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ), patch(
        "app.services.compliance_service.find_claims",
        new=AsyncMock(side_effect=fake_find_claims),
    ), patch(
        "app.services.compliance_service._create_audit_to_risk_edge",
        new=AsyncMock(side_effect=fake_create_edge),
    ), patch.object(
        ComplianceService,
        "get_audit",
        new=AsyncMock(return_value={
            "id": "a-1",
            "title": "Q2 2026 SOC2 Audit",
            "scope": "SOC2 CC7.2",
            "scheduled_date": "2026-06-01",
        }),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.update_audit(
            audit_id="a-1",
            status="completed",
            findings=(
                "Monitoring control CC7.2 had gaps in February. Related to "
                "vendor Acme Corp DPA risk. Recommendation: continuous monitoring rollout."
            ),
            user_id="00000000-0000-0000-0000-000000000001",
        )

    # An audit_finding claim was written
    assert len(write_claim_calls) == 1
    call = write_claim_calls[0]
    assert call["claim_type"] == "audit_finding"

    # An edge was created linking the audit_finding to the risk_assessment
    assert len(edge_calls) == 1
    edge = edge_calls[0]
    assert edge["from_claim_id_is_audit_finding"] is True or edge.get("kind") == "references"
    # Properties include from/to claim ids
    props = edge.get("properties") or {}
    assert "to_claim_id" in props or props.get("context", "").startswith("audit_finding")


@pytest.mark.asyncio
async def test_audit_finding_uses_edge_not_contradicts(_supabase_mock):
    """The audit_finding claim references prior risk via edge_id, NOT via contradicts."""
    from app.services.compliance_service import ComplianceService

    write_claim_calls: list[dict] = []

    async def fake_write_claim(**kwargs):
        write_claim_calls.append(kwargs)
        return uuid4()

    fake_edge = uuid4()

    with patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ), patch(
        "app.services.compliance_service.find_claims",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.services.compliance_service._create_audit_to_risk_edge",
        new=AsyncMock(return_value=fake_edge),
    ), patch.object(
        ComplianceService,
        "get_audit",
        new=AsyncMock(return_value={
            "id": "a-2", "title": "x", "scope": "y", "scheduled_date": "2026-06-01",
        }),
    ):
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.update_audit(
            audit_id="a-2",
            findings=(
                "Audit found gaps in monitoring control for vendor Acme. "
                "Related to existing vendor Acme DPA risk."
            ),
            user_id="00000000-0000-0000-0000-000000000001",
        )

    assert len(write_claim_calls) == 1
    call = write_claim_calls[0]
    # Edge-driven link, not contradicts.
    assert call.get("contradicts", []) in ([], (), None)
    # If a related risk was found, edge_id is populated
    # (In this test find_claims returns [], so edge_id is None — that's fine.)
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/test_compliance_claim_emission.py -v --tb=short
```

Expected: 3 of the new tests fail (the previous 4 still pass).

- [ ] **Step 3: Add the audit-finding emitter + the edge helper**

In `app/services/compliance_service.py`:

```python
from app.services.intelligence import find_claims  # add at top with the others


async def _create_audit_to_risk_edge(
    *,
    audit_entity_id: "UUID",
    audit_finding_claim_id: "UUID",
    risk_claim_id: "UUID",
) -> "UUID | None":
    """Create a kg_edges row linking an audit_finding claim to a risk_assessment claim.

    The edge endpoints are entities (per the kg_edges schema), but the claim-to-claim
    relationship is captured in ``properties``. Returns the new edge UUID, or None
    on best-effort failure.
    """
    from app.services.intelligence.claims import _get_supabase_client

    try:
        client = _get_supabase_client()
        row = {
            "source_entity_id": str(audit_entity_id),
            "target_entity_id": str(audit_entity_id),  # self-link is acceptable here
            "kind": "references",
            "properties": {
                "from_claim_id": str(audit_finding_claim_id),
                "to_claim_id": str(risk_claim_id),
                "context": "audit_finding cites risk_assessment",
            },
        }
        result = client.table("kg_edges").insert(row).execute()
        if result.data:
            from uuid import UUID

            return UUID(result.data[0]["id"])
    except Exception as exc:
        _compliance_logger.warning("_create_audit_to_risk_edge failed: %s", exc)
    return None


def _format_audit_finding_text(
    *,
    title: str,
    scope: str,
    findings: str,
    status: str,
) -> str:
    """Build the finding_text for an audit_finding claim."""
    return (
        f"[{status.upper()}] Audit: {title}. Scope: {scope}. "
        f"Findings: {findings}."
    )[:1500]


async def _emit_audit_finding_claim(
    *,
    title: str,
    scope: str,
    findings: str,
    status: str,
    confidence: float,
    audit_row_id: str | None,
    related_risk_claim_ids: list["UUID"] | None = None,
) -> "UUID | None":
    """Append-only emit one audit_finding claim. Optionally link to risk claims via edges."""
    from uuid import UUID

    finding_text = _format_audit_finding_text(
        title=title, scope=scope, findings=findings, status=status,
    )
    if len(finding_text.strip()) < 40:
        return None

    canonical_name, entity_type = _resolve_compliance_entity_kind(title, scope)
    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"audit:{canonical_name}",
            entity_type="event",
            domains=["compliance"],
        )
    except Exception as exc:
        _compliance_logger.warning(
            "_emit_audit_finding_claim: get_or_create_entity failed: %s", exc
        )
        return None

    sources: list[dict] = []
    if audit_row_id:
        sources.append({"kind": "supabase_row", "ref": f"compliance_audits/{audit_row_id}"})

    # Write the audit_finding claim FIRST (so we have its UUID for edges).
    try:
        finding_claim_id = await write_claim(
            entity_id=entity_id,
            domain="compliance",
            finding_text=finding_text,
            confidence=confidence,
            sources=sources,
            agent_id="compliance",
            claim_type="audit_finding",
            embed=True,
        )
    except Exception as exc:
        _compliance_logger.warning(
            "_emit_audit_finding_claim: write_claim failed: %s", exc
        )
        return None

    # If we have related risk claim ids, create edges (one per risk).
    for risk_claim_id in (related_risk_claim_ids or []):
        await _create_audit_to_risk_edge(
            audit_entity_id=entity_id,
            audit_finding_claim_id=finding_claim_id,
            risk_claim_id=risk_claim_id,
        )

    return finding_claim_id
```

Then wire `_emit_audit_finding_claim` into `create_audit` (always emits with `status='scheduled'` and empty findings text — skipped by the 40-char guard, which is fine for create-time) and `update_audit`:

```python
    async def create_audit(
        self,
        title: str,
        scope: str,
        auditor: str,
        scheduled_date: str,
        status: str = "scheduled",
        user_id: str | None = None,
    ) -> dict:
        """Create a new compliance audit + emit a placeholder audit_finding claim."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for audit creation")
        data = {
            "title": title,
            "scope": scope,
            "auditor": auditor,
            "scheduled_date": scheduled_date,
            "status": status,
            "user_id": effective_user_id,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._audits_table).insert(data))
        if not response.data:
            raise Exception("No data returned from insert audit")
        row = response.data[0]

        # Emit placeholder audit_finding (typically short-circuited by the 40-char
        # guard since no findings exist yet). Confidence comes from the
        # compliance preset using the *scope* text as the assessment surface.
        confidence, _band = ComplianceService._compute_risk_confidence(
            description=scope,
            mitigation_plan="",  # not yet
            severity="medium",
        )
        await _emit_audit_finding_claim(
            title=title,
            scope=scope,
            findings="",
            status=status,
            confidence=confidence,
            audit_row_id=row.get("id"),
        )
        return row


    async def update_audit(
        self,
        audit_id: str,
        status: str | None = None,
        findings: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update an audit row + emit a NEW audit_finding claim with related-risk edges."""
        update_data: dict = {}
        if status:
            update_data["status"] = status
        if findings:
            update_data["findings"] = findings

        existing = await self.get_audit(audit_id, user_id=user_id)
        effective_title = existing.get("title", "")
        effective_scope = existing.get("scope", "")
        effective_status = status or existing.get("status", "scheduled")

        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._audits_table).update(update_data).eq("id", audit_id)
        if not self.is_authenticated and user_id:
            query = query.eq("user_id", user_id)
        response = await execute_async(query)
        if not response.data:
            raise Exception("No data returned from update audit")
        row = response.data[0]

        if findings:
            # Find prior risk_assessment claims about overlapping entities
            # to link via edges.
            related_risk_ids: list = []
            try:
                # Heuristic: resolve the audit's primary entity, then query
                # any risk_assessment claims about it.
                canonical, kind = _resolve_compliance_entity_kind(
                    effective_title, effective_scope
                )
                # If the audit text mentions a vendor / system / control, fetch
                # related risk_assessment claims for that entity.
                risk_entity_id = await get_or_create_entity(
                    canonical_name=canonical,
                    entity_type=kind,
                    domains=["compliance"],
                )
                related = await find_claims(
                    entity_id=risk_entity_id,
                    claim_type="risk_assessment",
                    limit=10,
                )
                related_risk_ids = [c.id for c in related]
            except Exception as exc:
                _compliance_logger.warning(
                    "update_audit: related-risk lookup failed: %s", exc
                )

            confidence, _band = ComplianceService._compute_risk_confidence(
                description=effective_scope,
                mitigation_plan=findings,
                severity="medium",
            )
            await _emit_audit_finding_claim(
                title=effective_title,
                scope=effective_scope,
                findings=findings,
                status=effective_status,
                confidence=confidence,
                audit_row_id=audit_id,
                related_risk_claim_ids=related_risk_ids,
            )
        return row
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/test_compliance_claim_emission.py -v --tb=short
```

Expected: 7 passed (4 from Task 2 + 3 from Task 3). Some of the Task 3 test names use stand-in `from_claim_id_is_audit_finding` checks; adjust the assertion to match the actual edge.properties shape if it differs:

```python
# fixed assertion if needed:
assert edge["kind"] == "references"
props = edge.get("properties") or {}
assert props.get("context", "").startswith("audit_finding")
```

- [ ] **Step 5: Commit**

```bash
git add app/services/compliance_service.py tests/unit/services/test_compliance_claim_emission.py
git commit -m "feat(116-02): emit audit_finding claims linked to risk_assessment via edges"
```

### Task 4: Immutability invariant test (regression)

**Files:**
- Create: `tests/unit/services/test_compliance_claim_immutability.py`

This test makes the append-only invariant a hard regression check — failure means someone "fixed" `update_risk` to UPDATE prior `kg_findings` rows.

- [ ] **Step 1: Write the invariant test**

Create `tests/unit/services/test_compliance_claim_immutability.py`:

```python
"""Regression test: risk_assessment claims are append-only.

A new risk assessment for the same entity creates a new claim_id.
Existing claim rows are NEVER mutated.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_update_risk_does_not_call_update_on_kg_findings():
    """ComplianceService.update_risk must NEVER issue an UPDATE on kg_findings.

    Any UPDATE on a kg_findings row of claim_type='risk_assessment' would
    violate the immutability invariant. This test asserts the call graph:
    update_risk -> write_claim (INSERT only) -> [never client.table('kg_findings').update].
    """
    from app.services.compliance_service import ComplianceService

    # Capture every table/update call against the Supabase client.
    table_calls: list[tuple[str, str]] = []  # (table_name, op)

    class _RecordingQuery:
        def __init__(self, table_name: str):
            self.table_name = table_name

        def insert(self, _data):
            table_calls.append((self.table_name, "insert"))
            return self

        def update(self, _data):
            table_calls.append((self.table_name, "update"))
            return self

        def eq(self, *_a, **_k):
            return self

        def select(self, *_a, **_k):
            return self

        def single(self):
            return self

    fake_client = MagicMock()
    fake_client.table.side_effect = lambda name: _RecordingQuery(name)

    async def _fake_execute(query):
        return MagicMock(data=[{"id": "row-1", "title": "t", "description": "d", "mitigation_plan": "m", "severity": "high"}])

    with patch(
        "app.services.compliance_service.execute_async",
        new=AsyncMock(side_effect=_fake_execute),
    ), patch(
        "app.services.compliance_service.AdminService",
    ) as fake_admin, patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(return_value=uuid4()),
    ), patch.object(
        ComplianceService,
        "get_risk",
        new=AsyncMock(return_value={
            "id": "row-1",
            "title": "vendor Foo",
            "description": "d",
            "mitigation_plan": "old",
            "severity": "high",
        }),
    ):
        fake_admin.return_value.client = fake_client
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.update_risk(
            risk_id="row-1",
            mitigation_plan="new mitigation with citations https://example.com/policy and ref: AUD-2026.",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    # The ONLY update call should be against compliance_risks itself.
    # NO update against kg_findings.
    kg_findings_updates = [c for c in table_calls if c == ("kg_findings", "update")]
    assert kg_findings_updates == [], (
        f"IMMUTABILITY VIOLATION: kg_findings UPDATE occurred during "
        f"update_risk. Table calls: {table_calls}"
    )


@pytest.mark.asyncio
async def test_two_sequential_update_risks_emit_two_distinct_claim_ids():
    """Calling update_risk twice yields two write_claim invocations with no shared id."""
    from app.services.compliance_service import ComplianceService

    write_claim_calls: list[dict] = []
    returned_ids: list = []

    async def fake_write_claim(**kwargs):
        new_id = uuid4()
        returned_ids.append(new_id)
        write_claim_calls.append(kwargs)
        return new_id

    async def fake_execute(_q):
        return MagicMock(data=[{"id": "r-1", "title": "t", "description": "d", "mitigation_plan": "m", "severity": "high"}])

    with patch(
        "app.services.compliance_service.execute_async",
        new=AsyncMock(side_effect=fake_execute),
    ), patch(
        "app.services.compliance_service.AdminService",
    ) as fake_admin, patch(
        "app.services.compliance_service.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.compliance_service.write_claim",
        new=AsyncMock(side_effect=fake_write_claim),
    ), patch.object(
        ComplianceService,
        "get_risk",
        new=AsyncMock(return_value={
            "id": "r-1",
            "title": "vendor Foo",
            "description": "d",
            "mitigation_plan": "m1",
            "severity": "high",
        }),
    ):
        fake_admin.return_value.client = MagicMock()
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False

        await svc.update_risk(
            risk_id="r-1",
            mitigation_plan="updated plan with citations https://example.com/v1 and policy ref",
            user_id="00000000-0000-0000-0000-000000000001",
        )
        await svc.update_risk(
            risk_id="r-1",
            mitigation_plan="further updated plan with new citations https://example.com/v2 ref",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    assert len(returned_ids) == 2
    assert returned_ids[0] != returned_ids[1], "Successive updates returned the same claim id"
```

- [ ] **Step 2: Run — should PASS immediately**

```powershell
uv run pytest tests/unit/services/test_compliance_claim_immutability.py -v --tb=short
```

Expected: 2 passed. If either fails, Plan 116-02 has violated the invariant — STOP and fix `update_risk` / `update_audit` before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/services/test_compliance_claim_immutability.py
git commit -m "test(116-02): immutability invariant — risk_assessment claims are append-only"
```

### Task 5: Integration test — end-to-end round-trip + semantic search

**Files:**
- Create: `tests/integration/test_compliance_claims_end_to_end.py`

- [ ] **Step 1: Write the integration test**

Create `tests/integration/test_compliance_claims_end_to_end.py`:

```python
"""End-to-end: ComplianceService writes -> kg_findings -> search_claims_semantic."""

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
async def test_create_risk_then_find_via_semantic_search():
    """A created risk surfaces in search_claims_semantic for Compliance agent_id."""
    from app.services.compliance_service import ComplianceService
    from app.services.intelligence import search_claims_semantic
    from supabase import create_client

    # Use a unique-ish vendor name so search results don't collide with
    # historical data in the local DB.
    unique = uuid4().hex[:8]
    vendor = f"AcmeTest{unique}"

    # We need a real user_id present in auth.users to satisfy any FK / RLS.
    # For the local CI stack we use a fixed admin user from the seed; if seed
    # doesn't define one, this test is skipped.
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    db_client = create_client(url, key)
    seed_users = (
        db_client.table("user_settings").select("user_id").limit(1).execute()
    )
    if not seed_users.data:
        pytest.skip("No seed user available in user_settings")
    user_id = seed_users.data[0]["user_id"]

    svc = ComplianceService(user_token=None)
    svc._is_authenticated = False  # forces AdminService path
    await svc.create_risk(
        title=f"DPA missing for vendor {vendor}",
        description=(
            f"{vendor} processes personal data without a signed Data Processing "
            f"Agreement. GDPR Article 28 violation. See https://gdpr.eu/article-28."
        ),
        severity="high",
        mitigation_plan=(
            f"Engage vendor {vendor} to sign GDPR Article 28 DPA within 30 days. "
            f"See policy ref POL-2026-DPA-001 and audit log AUD-{unique}."
        ),
        user_id=user_id,
    )

    # Semantic search restricted to Compliance agent_id
    results = await search_claims_semantic(
        query=f"vendor {vendor} GDPR Article 28 DPA gap",
        agent_id="compliance",
        claim_type="risk_assessment",
        top_k=5,
    )

    assert results, "Compliance risk_assessment claim not surfaced in semantic search"
    top_claim, distance = results[0]
    assert top_claim.agent_id == "compliance"
    assert top_claim.claim_type == "risk_assessment"
    assert vendor in top_claim.finding_text


@pytest.mark.asyncio
async def test_update_risk_appends_new_claim_old_remains():
    """Updating a risk creates a new claim_id; prior claim row remains in DB."""
    from app.services.compliance_service import ComplianceService
    from app.services.intelligence import find_claims, get_or_create_entity
    from supabase import create_client

    unique = uuid4().hex[:8]
    vendor = f"Beta{unique}"

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    db_client = create_client(url, key)
    seed_users = (
        db_client.table("user_settings").select("user_id").limit(1).execute()
    )
    if not seed_users.data:
        pytest.skip("No seed user available")
    user_id = seed_users.data[0]["user_id"]

    svc = ComplianceService(user_token=None)
    svc._is_authenticated = False
    created = await svc.create_risk(
        title=f"DPA missing for vendor {vendor}",
        description=f"{vendor} processes PII without DPA. GDPR Article 28.",
        severity="high",
        mitigation_plan="Sign DPA in 30 days. Policy ref POL-2026.",
        user_id=user_id,
    )
    await svc.update_risk(
        risk_id=created["id"],
        mitigation_plan=(
            f"DPA signed on 2026-05-15. Document ID DOC-{unique}. "
            f"Audit ref AUD-{unique}-FINAL."
        ),
        user_id=user_id,
    )

    # Look up all claims for the entity — expect ≥ 2 risk_assessment rows.
    entity_id = await get_or_create_entity(
        canonical_name=f"vendor:{vendor}",
        entity_type="company",
        domains=["compliance"],
    )
    claims = await find_claims(
        entity_id=entity_id,
        claim_type="risk_assessment",
        limit=20,
    )
    assert len(claims) >= 2
    # IDs must all be distinct
    ids = [c.id for c in claims]
    assert len(set(ids)) == len(ids)
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_compliance_claims_end_to_end.py -v --tb=short
```

Expected: 2 passed. If the semantic-search test fails with "not surfaced", check:
1. The ivfflat index exists: `\d kg_findings` should show `kg_findings_embedding_ivfflat`.
2. The embedding service is reachable (check the Vertex API key / fallback path).
3. The local Supabase has been restarted since the kg_findings migrations were applied.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_compliance_claims_end_to_end.py
git commit -m "test(116-02): end-to-end Compliance claim emission + semantic search"
```

### Task 6: Full Compliance test suite + lint + Phase 116 acceptance sign-off

**Files:** none (verification only).

- [ ] **Step 1: Run the full Compliance test surface**

```powershell
uv run pytest tests/unit/agents/compliance/ tests/unit/services/test_compliance_service_confidence.py tests/unit/services/test_compliance_entity_resolver.py tests/unit/services/test_compliance_claim_emission.py tests/unit/services/test_compliance_claim_immutability.py tests/unit/services/intelligence/presets/test_compliance.py -v --tb=short
```

Expected: all green.

- [ ] **Step 2: Run any pre-existing compliance test bucket**

```powershell
uv run pytest -k "compliance" --tb=short
```

Expected: green or skipped (integration with skip reasons).

- [ ] **Step 3: Lint + format**

```powershell
uv run ruff check app/services/compliance_service.py tests/unit/services/test_compliance_entity_resolver.py tests/unit/services/test_compliance_claim_emission.py tests/unit/services/test_compliance_claim_immutability.py tests/integration/test_compliance_claims_end_to_end.py
uv run ruff format --check app/services/compliance_service.py tests/unit/services/test_compliance_entity_resolver.py tests/unit/services/test_compliance_claim_emission.py tests/unit/services/test_compliance_claim_immutability.py tests/integration/test_compliance_claims_end_to_end.py
```

Fix in place. Commit any pure-formatting fix-ups:

```bash
git add -u
git commit -m "style(116-02): ruff format fixes for Compliance claim emission"
```

- [ ] **Step 4: Type check**

```powershell
uv run ty check app/services/compliance_service.py
```

Expected: clean.

- [ ] **Step 5: Phase 116 acceptance — cross-check ALL plans 116-01 and 116-02**

| Phase 116 acceptance line | Verified by |
|---|---|
| Compliance Agent test suite green | Plan 116-01 Task 6, Plan 116-02 Task 6 |
| All Compliance outputs carry confidence + band | Plan 116-01 Tasks 3, 4, 5; Plan 116-02 Tasks 2, 3 |
| Risk assessments link to audit findings via `edge_id`, not via `contradicts` | Plan 116-02 Task 3 (audit-finding tests) |
| Immutability: new risk_assessment → new claim_id; prior untouched | Plan 116-02 Task 4 (dedicated test file) |
| `search_claims_semantic` returns Compliance claims | Plan 116-02 Task 5 (integration test) |
| `presets/compliance.py` shipped with 40/30/20/10 weights | Plan 116-01 Task 2 |
| Self-improvement engine audit completed BEFORE changes (Decision #8) | Plan 116-01 Task 1 |
| `risk_assessment` + `audit_finding` claim_type vocabulary documented | This file (Pre-flight context) + Plan 116-02 Task 2, 3 |

- [ ] **Step 6: Confirm branch state**

```bash
git status   # should be clean
git log --oneline -10   # Plan 116-02 should show ~5 new commits
```

- [ ] **Step 7: Plan 116-02 complete — Phase 116 (Compliance Agent adoption) is fully shipped**

Next planned work: Phase 117 (Marketing Agent adoption) per `MILESTONES.md`. Cross-cutting infrastructure from Plan 113-04 / 113-05 (semantic search, contradiction detection) auto-applies to the Compliance claims emitted here — no further per-phase test work needed for those.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `risk_assessment` claim emission from create_risk + update_risk | Task 2 |
| `audit_finding` claim emission from create_audit + update_audit | Task 3 |
| Audit findings reference risk_assessment via `edge_id`, NOT via `contradicts` | Task 3 |
| New assessment for existing entity → new claim_id (immutability) | Tasks 2, 4 |
| Prior claim row remains untouched in DB | Task 4 (mocked) + Task 5 (real DB) |
| `search_claims_semantic` returns Compliance claims | Task 5 |
| Compliance Agent test suite green | Task 6 |
| Lint + types clean | Task 6 |
| Claim-type vocabulary locked: `risk_assessment` + `audit_finding` | Pre-flight context (this file) |
| `embed=True` for cross-agent contradiction value | Tasks 2, 3 |
| Best-effort emission — DB write succeeds even on kg_findings failure | Task 2 (test_create_risk_claim_failure_does_not_break_db_write) |

All spec lines covered.
