# Shared Intelligence Infrastructure — Plan 112-03: Claims Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the claims module — the kg_findings write/read API plus entity resolution: `write_claim`, `write_claims`, `find_claims`, `claim_freshness_hours`, `get_or_create_entity`, and the `Claim` / `ClaimSource` / `ClaimPayload` Pydantic schemas. No agent migrates onto these in this plan — that's Plan 112-05.

**Architecture:** Async functions against Supabase via the service-role client. Schemas use Pydantic v2 with `@computed_field` for `Claim.band` so band thresholds stay tunable in code (no DB rewrite needed). Writes raise on failure; reads return empty / None on failure (per the spec's "reads degrade silently, writes fail loudly" principle). `write_claim` is INSERT-not-UPSERT — matches the existing append-only finding model; `get_or_create_entity` is UPSERT on `(canonical_name, entity_type)` to prevent duplicate entities.

**Tech Stack:** Python 3.10+, Pydantic v2, async Supabase client, pytest with `pytest.mark.integration`, psycopg for direct DB queries.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Module specifications § claims.py

**Out of scope for this plan:** Cache module (Plan 112-04), Research Agent refactor (Plan 112-05), `search_claims_semantic` (Plan 113-04), `detect_contradictions` (Plan 113-05), embedding generation when `embed=True` is opt-in but the actual embedding call defers to `app/services/embeddings.py` which is already a project module.

---

## File structure

**Create:**
- `tests/integration/test_intelligence_claims.py` — integration tests against real Supabase
- `tests/unit/services/intelligence/test_schemas.py` — schema validation tests

**Modify:**
- `app/services/intelligence/schemas.py` — add `ClaimSource`, `Claim`, `ClaimPayload`
- `app/services/intelligence/claims.py` — new file (was not created in 112-02)
- `app/services/intelligence/__init__.py` — re-export new names

**Reference (read-only):**
- `app/agents/research/tools/graph_writer.py:32-136` — existing upsert pattern for entities and insert pattern for findings (we're lifting the structure, not the function itself; Plan 112-05 retires this file)
- `app/services/supabase_client.py` — service-role client factory
- Existing migration `supabase/migrations/20260321500000_knowledge_graph.sql` — table definitions
- Plan 112-01's migration adds `agent_id` + `claim_type` columns

---

## Pre-flight context

Schema we're writing against (post-112-01 migration applied):
```
kg_findings (
    id              UUID PK,
    entity_id       UUID FK -> kg_entities(id),
    edge_id         UUID FK -> kg_edges(id),
    domain          TEXT NOT NULL,
    finding_text    TEXT NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.5,
    sources         JSONB NOT NULL DEFAULT '[]',
    contradicts     JSONB NOT NULL DEFAULT '[]',
    embedding       VECTOR(768),
    freshness_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_id        TEXT NOT NULL,  -- added by 112-01
    claim_type      TEXT NOT NULL,  -- added by 112-01
    CHECK (entity_id IS NOT NULL OR edge_id IS NOT NULL)
)

kg_entities (
    id              UUID PK,
    canonical_name  TEXT NOT NULL,
    entity_type     TEXT CHECK (... 'company', 'person', 'regulation',
                                'market', 'technology', 'topic', 'metric',
                                'country', 'institution', 'product', 'event'),
    domains         TEXT[] NOT NULL DEFAULT '{}',
    properties      JSONB NOT NULL DEFAULT '{}',
    embedding       VECTOR(768),
    source_count    INT NOT NULL DEFAULT 1,
    freshness_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_name, entity_type)
)
```

Existing patterns in the codebase (from `app/agents/research/tools/graph_writer.py`):
```python
# Upsert entity (lines 73-77):
client.table("kg_entities").upsert(
    entity_data,
    on_conflict="canonical_name,entity_type",
).execute()

# Insert finding (lines 96-111):
client.table("kg_findings").insert(finding_data).execute()
```

Async client pattern per [[reference_supabase_async_patterns]]:
- Use `supabase_client` (the recommended module) + `execute_async` wrapper
- Direct `await .execute()` silently no-ops on the sync client — avoid

Environment quirks (carried from Plans 112-01, 112-02):
- `uv` only works via PowerShell
- Local Supabase running on http://127.0.0.1:54321; DB at port 54322
- Integration test conftest installs a MagicMock for `app.services.supabase_client` — our test fixture bypasses it with `create_client(url, key)` (same pattern as Plan 112-01)
- For local migration testing, use `docker exec -i supabase_db_Pikar-Ai psql -U postgres -d postgres -f /dev/stdin < <migration>`

---

## Tasks

### Task 1: Pre-flight + extend schemas.py

**Files:**
- Modify: `app/services/intelligence/schemas.py`

- [ ] **Step 1: Confirm Plan 112-01 + 112-02 are applied locally**

```bash
ls app/services/intelligence/{__init__.py,confidence.py,schemas.py,presets/research.py}
```

Expected: all four files exist (created by Plan 112-02). If missing, STOP — Plan 112-03 depends on 112-02 being implemented (not just planned).

Verify the kg_findings columns from Plan 112-01:
```powershell
docker exec supabase_db_Pikar-Ai psql -U postgres -d postgres -c "SELECT column_name FROM information_schema.columns WHERE table_name='kg_findings' AND column_name IN ('agent_id','claim_type');"
```

Expected: both columns present. If absent, run Plan 112-01 Task 3 first.

- [ ] **Step 2: Replace `app/services/intelligence/schemas.py` with the extended version**

```python
"""Shared Pydantic models and type aliases for the intelligence package."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.services.intelligence.confidence import to_band

ConfidenceBand = Literal["low", "medium", "high"]


class ClaimSource(BaseModel):
    """A source backing a claim. Domain-agnostic."""

    kind: Literal[
        "url",
        "supabase_row",
        "stripe_row",
        "shopify_row",
        "regulation",
        "user",
        "other",
    ]
    ref: str  # URL, row ID, citation, etc.
    score: float | None = None  # optional source-specific quality score


class Claim(BaseModel):
    """A row from kg_findings as returned by find_claims / search_claims_semantic.

    band is a computed property derived from confidence — keeps band thresholds
    tunable in code without DB migration.
    """

    id: UUID
    entity_id: UUID | None
    edge_id: UUID | None
    agent_id: str
    claim_type: str
    domain: str
    finding_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[ClaimSource]
    contradicts: list[UUID]
    freshness_at: datetime
    expires_at: datetime | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def band(self) -> ConfidenceBand:
        return to_band(self.confidence)


class ClaimPayload(BaseModel):
    """Input to write_claim / write_claims. Mirrors write_claim's kwargs.

    Distinct from Claim because input lacks DB-assigned fields
    (id, created_at, freshness_at) and carries the embed policy flag.
    """

    entity_id: UUID | None
    edge_id: UUID | None = None
    domain: str
    finding_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[ClaimSource]
    agent_id: str
    claim_type: str
    embed: bool = False
    expires_at: datetime | None = None
    contradicts: list[UUID] = Field(default_factory=list)
```

Note the import of `to_band` from `app.services.intelligence.confidence`. This introduces a soft import order: `schemas.py` depends on `confidence.py`. The package `__init__.py` must continue importing from `confidence` before `schemas` to avoid circular issues, or use deferred import inside the computed_field. We use a top-level import here because Python's lazy module loading handles this fine — `confidence.py` doesn't import from `schemas.py`.

- [ ] **Step 3: Confirm imports still work** (from PowerShell):

```powershell
uv run python -c "
from app.services.intelligence import ConfidenceBand, score_confidence, to_band, presets
from app.services.intelligence.schemas import Claim, ClaimSource, ClaimPayload
print('extended schemas import OK')
"
```

Expected: `extended schemas import OK`. ImportError likely means a circular dep — flag and stop.

- [ ] **Step 4: Commit the schema extension**

```bash
git add app/services/intelligence/schemas.py
git commit -m "feat(112-03): extend intelligence.schemas with Claim, ClaimSource, ClaimPayload"
```

---

### Task 2: Write failing schema unit tests

**Files:**
- Create: `tests/unit/services/intelligence/test_schemas.py`

- [ ] **Step 1: Create the schema test file**

```python
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
```

- [ ] **Step 2: Run the tests — they should PASS** (from PowerShell):

```powershell
uv run pytest tests/unit/services/intelligence/test_schemas.py -v --tb=short
```

Expected: all tests PASS. Schemas are pure data — no implementation gap. If any test fails, the schema definition (Task 1 Step 2) has a bug — fix.

- [ ] **Step 3: Commit the schema tests**

```bash
git add tests/unit/services/intelligence/test_schemas.py
git commit -m "test(112-03): add schema unit tests for Claim, ClaimSource, ClaimPayload"
```

---

### Task 3: Scaffold `claims.py` with stubs

**Files:**
- Create: `app/services/intelligence/claims.py`

- [ ] **Step 1: Create `app/services/intelligence/claims.py` with the stubs**

```python
"""Knowledge-graph claims: writes and reads against kg_findings.

Public surface:
- write_claim       — insert one Claim
- write_claims      — bulk insert of ClaimPayload
- find_claims       — structured filter query
- claim_freshness_hours — age of latest matching claim (for cache.py)
- get_or_create_entity  — upsert on kg_entities

All operations use the service-role Supabase client. Writes raise on
failure; reads return [] / None on failure with structured logging.

Embeddings are opt-in via embed=True. Generation defers to
app/services/embeddings.py (Vertex AI).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.services.intelligence.schemas import Claim, ClaimPayload

logger = logging.getLogger(__name__)


async def get_or_create_entity(
    *,
    canonical_name: str,
    entity_type: str,
    domains: Sequence[str] = (),
    properties: dict | None = None,
) -> UUID:
    """Stub — implemented in Task 4."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 4")


async def write_claim(
    *,
    entity_id: UUID | None,
    edge_id: UUID | None = None,
    domain: str,
    finding_text: str,
    confidence: float,
    sources: Sequence[dict],
    agent_id: str,
    claim_type: str,
    embed: bool = False,
    expires_at: datetime | None = None,
    contradicts: Sequence[UUID] = (),
) -> UUID:
    """Stub — implemented in Task 5."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 5")


async def write_claims(claims: Sequence[ClaimPayload]) -> list[UUID]:
    """Stub — implemented in Task 6."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 6")


async def find_claims(
    *,
    entity_id: UUID | None = None,
    agent_id: str | None = None,
    claim_type: str | None = None,
    domain: str | None = None,
    min_confidence: float = 0.0,
    fresh_since: datetime | None = None,
    limit: int = 50,
) -> list[Claim]:
    """Stub — implemented in Task 7."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 7")


async def claim_freshness_hours(
    *,
    entity_id: UUID,
    claim_type: str | None = None,
    agent_id: str | None = None,
) -> float | None:
    """Stub — implemented in Task 7."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 7")
```

- [ ] **Step 2: Verify stubs import cleanly**

```powershell
uv run python -c "
from app.services.intelligence.claims import (
    get_or_create_entity, write_claim, write_claims, find_claims, claim_freshness_hours
)
print('claims.py stub imports OK')
"
```

Expected: `claims.py stub imports OK`.

- [ ] **Step 3: Commit the stub**

```bash
git add app/services/intelligence/claims.py
git commit -m "feat(112-03): scaffold claims.py with NotImplementedError stubs"
```

---

### Task 4: Implement `get_or_create_entity` (TDD)

**Files:**
- Create: `tests/integration/test_intelligence_claims.py` (first section)
- Modify: `app/services/intelligence/claims.py`

- [ ] **Step 1: Create the integration test file with `get_or_create_entity` tests**

```python
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
    supabase_client, cleanup_entities,
):
    """Same canonical_name with different entity_type produces distinct rows."""
    from app.services.intelligence.claims import get_or_create_entity

    name = f"Acme Corp {uuid4()}"
    as_company = await get_or_create_entity(
        canonical_name=name, entity_type="company", domains=["test"],
    )
    as_topic = await get_or_create_entity(
        canonical_name=name, entity_type="topic", domains=["test"],
    )
    cleanup_entities.extend([as_company, as_topic])

    assert as_company != as_topic
```

- [ ] **Step 2: Install pytest-asyncio if not already** (from PowerShell):

```powershell
uv run python -c "import pytest_asyncio; print('pytest-asyncio', pytest_asyncio.__version__)" 2>&1
```

If missing:
```powershell
uv run uv add --dev pytest-asyncio
```

(Same `uv run uv add` workaround as prior plans.) Mark `pyproject.toml` to enable asyncio mode by adding to the `[tool.pytest.ini_options]` block:

```toml
asyncio_mode = "auto"
```

Check if that line already exists in pyproject.toml first — if so, skip. If the `[tool.pytest.ini_options]` block doesn't exist at all, add it:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3: Run the three entity tests — they should FAIL with NotImplementedError**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_intelligence_claims.py::test_get_or_create_entity_creates_new tests/integration/test_intelligence_claims.py::test_get_or_create_entity_idempotent tests/integration/test_intelligence_claims.py::test_get_or_create_entity_different_types_distinct -v
```

Expected: 3 FAILED with NotImplementedError.

- [ ] **Step 4: Implement `get_or_create_entity` in claims.py**

Replace the stub at the top of `app/services/intelligence/claims.py`:

```python
async def get_or_create_entity(
    *,
    canonical_name: str,
    entity_type: str,
    domains: Sequence[str] = (),
    properties: dict | None = None,
) -> UUID:
    """Upsert a knowledge-graph entity by (canonical_name, entity_type).

    Idempotent: repeated calls with the same canonical_name + entity_type
    return the same UUID. domains and properties update on each call.

    Args:
        canonical_name: Human-readable entity name (e.g., "Acme Corp",
                       "Q1 2026 Cohort").
        entity_type: Must be one of the kg_entities CHECK constraint values:
                    'company', 'person', 'regulation', 'market', 'technology',
                    'topic', 'metric', 'country', 'institution', 'product',
                    'event'.
        domains: List of domain tags (e.g., ['financial', 'data']).
        properties: Arbitrary JSONB metadata.

    Returns:
        UUID of the existing or newly created entity row.

    Raises:
        Exception (from Supabase client) if the upsert fails.
    """
    from app.services.supabase_client import get_supabase_client

    client = get_supabase_client()
    row = {
        "canonical_name": canonical_name,
        "entity_type": entity_type,
        "domains": list(domains),
        "properties": properties or {},
    }
    result = client.table("kg_entities").upsert(
        row,
        on_conflict="canonical_name,entity_type",
    ).execute()
    if not result.data:
        raise RuntimeError(
            f"Upsert returned no rows for entity ({canonical_name}, {entity_type})"
        )
    return UUID(result.data[0]["id"])
```

- [ ] **Step 5: Re-run the three entity tests — they should PASS**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
uv run pytest tests/integration/test_intelligence_claims.py -k "get_or_create_entity" -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit tests + implementation**

```bash
git add tests/integration/test_intelligence_claims.py \
        app/services/intelligence/claims.py pyproject.toml uv.lock
git commit -m "feat(112-03): implement get_or_create_entity with integration tests (GREEN)"
```

(If pyproject.toml/uv.lock weren't changed, omit them from the add.)

---

### Task 5: Implement `write_claim` (TDD)

**Files:**
- Modify: `tests/integration/test_intelligence_claims.py` (append)
- Modify: `app/services/intelligence/claims.py`

- [ ] **Step 1: Append `write_claim` tests** to `tests/integration/test_intelligence_claims.py`:

```python
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
```

- [ ] **Step 2: Run the new tests — they should FAIL with NotImplementedError**

```powershell
uv run pytest tests/integration/test_intelligence_claims.py -k "write_claim" -v
```

Expected: 3 FAILED.

- [ ] **Step 3: Implement `write_claim`** by replacing the stub in `app/services/intelligence/claims.py`:

```python
async def write_claim(
    *,
    entity_id: UUID | None,
    edge_id: UUID | None = None,
    domain: str,
    finding_text: str,
    confidence: float,
    sources: Sequence[dict],
    agent_id: str,
    claim_type: str,
    embed: bool = False,
    expires_at: datetime | None = None,
    contradicts: Sequence[UUID] = (),
) -> UUID:
    """Insert a single claim into kg_findings.

    Append-only — never updates existing rows. Each call creates a new row;
    historical claims are retained for audit. Use expires_at to set a
    retention horizon.

    Args:
        entity_id: kg_entities row to attach to (or None if edge_id supplied).
        edge_id: kg_edges row to attach to (or None if entity_id supplied).
        domain: Agent domain tag (e.g., 'data', 'research').
        finding_text: Human-readable claim text.
        confidence: [0.0, 1.0] — typically from a preset like data_confidence.
        sources: List of dicts matching ClaimSource shape (kind, ref, score?).
        agent_id: e.g., 'data', 'research', 'financial'.
        claim_type: Domain-specific type tag (e.g., 'cohort_retention').
        embed: If True, generate embedding via Vertex AI before insert.
        expires_at: Optional retention timestamp.
        contradicts: List of UUIDs of contradicting claims.

    Returns:
        UUID of the newly inserted kg_findings row.

    Raises:
        Exception on Supabase failure or DB constraint violation.
    """
    from app.services.supabase_client import get_supabase_client

    client = get_supabase_client()

    embedding: list[float] | None = None
    if embed and finding_text and len(finding_text) >= 20:
        embedding = await _embed_text(finding_text)

    row: dict = {
        "domain": domain,
        "finding_text": finding_text,
        "confidence": confidence,
        "sources": list(sources),
        "contradicts": [str(c) for c in contradicts],
        "agent_id": agent_id,
        "claim_type": claim_type,
    }
    if entity_id is not None:
        row["entity_id"] = str(entity_id)
    if edge_id is not None:
        row["edge_id"] = str(edge_id)
    if embedding is not None:
        row["embedding"] = embedding
    if expires_at is not None:
        row["expires_at"] = expires_at.isoformat()

    result = client.table("kg_findings").insert(row).execute()
    if not result.data:
        raise RuntimeError(f"Insert returned no rows for claim_type={claim_type}")
    return UUID(result.data[0]["id"])


async def _embed_text(text: str) -> list[float] | None:
    """Generate a Vertex AI embedding for the given text.

    Returns None and logs a warning on failure (caller treats as no-embedding).
    """
    try:
        from app.services.embeddings import generate_embedding  # type: ignore[import-not-found]

        return await generate_embedding(text)
    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return None
```

If `app/services/embeddings.py` doesn't expose `generate_embedding` with that exact signature, adjust the import to match the existing helper. Verify before implementing:
```bash
grep -E "^(async )?def (generate_embedding|embed)" app/services/embeddings.py
```

- [ ] **Step 4: Re-run write_claim tests — they should PASS**

```powershell
uv run pytest tests/integration/test_intelligence_claims.py -k "write_claim and not write_claims" -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_intelligence_claims.py \
        app/services/intelligence/claims.py
git commit -m "feat(112-03): implement write_claim with sources, embedding opt-in (GREEN)"
```

---

### Task 6: Implement `write_claims` (bulk)

**Files:**
- Modify: `tests/integration/test_intelligence_claims.py` (append)
- Modify: `app/services/intelligence/claims.py`

- [ ] **Step 1: Append bulk-insert tests**

```python
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
```

- [ ] **Step 2: Run — should FAIL** with NotImplementedError

```powershell
uv run pytest tests/integration/test_intelligence_claims.py -k "write_claims" -v
```

- [ ] **Step 3: Implement `write_claims`**

Replace the stub in `app/services/intelligence/claims.py`:

```python
async def write_claims(claims: Sequence[ClaimPayload]) -> list[UUID]:
    """Bulk-insert claims in a single statement.

    Returns IDs in input order. Embeddings are opt-in per-payload (the
    embed flag on ClaimPayload). For mixed embed/no-embed batches, embeddings
    are generated sequentially before the bulk insert.

    Args:
        claims: Sequence of ClaimPayload. Empty input returns []
                without hitting the DB.

    Returns:
        list[UUID] of the inserted row IDs, same order as input.

    Raises:
        Exception on Supabase failure or any single-row constraint violation.
        Partial inserts are NOT possible — the bulk INSERT is atomic.
    """
    if not claims:
        return []

    from app.services.supabase_client import get_supabase_client

    client = get_supabase_client()
    rows: list[dict] = []
    for c in claims:
        embedding: list[float] | None = None
        if c.embed and c.finding_text and len(c.finding_text) >= 20:
            embedding = await _embed_text(c.finding_text)

        row: dict = {
            "domain": c.domain,
            "finding_text": c.finding_text,
            "confidence": c.confidence,
            "sources": [s.model_dump(exclude_none=True) for s in c.sources],
            "contradicts": [str(x) for x in c.contradicts],
            "agent_id": c.agent_id,
            "claim_type": c.claim_type,
        }
        if c.entity_id is not None:
            row["entity_id"] = str(c.entity_id)
        if c.edge_id is not None:
            row["edge_id"] = str(c.edge_id)
        if embedding is not None:
            row["embedding"] = embedding
        if c.expires_at is not None:
            row["expires_at"] = c.expires_at.isoformat()
        rows.append(row)

    result = client.table("kg_findings").insert(rows).execute()
    if not result.data or len(result.data) != len(claims):
        raise RuntimeError(
            f"Bulk insert returned {len(result.data) if result.data else 0} rows, "
            f"expected {len(claims)}"
        )
    return [UUID(r["id"]) for r in result.data]
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/integration/test_intelligence_claims.py -k "write_claims" -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_intelligence_claims.py \
        app/services/intelligence/claims.py
git commit -m "feat(112-03): implement write_claims bulk insert (GREEN)"
```

---

### Task 7: Implement `find_claims` and `claim_freshness_hours`

**Files:**
- Modify: `tests/integration/test_intelligence_claims.py` (append)
- Modify: `app/services/intelligence/claims.py`

- [ ] **Step 1: Append read tests**

```python
# ---------------------------------------------------------------------------
# find_claims and claim_freshness_hours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_claims_by_entity(supabase_client, cleanup_entities):
    """find_claims with entity_id filter returns matching claims."""
    from app.services.intelligence.claims import (
        find_claims, get_or_create_entity, write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Find Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    await write_claim(
        entity_id=entity_id, domain="test",
        finding_text="findable claim",
        confidence=0.9,
        sources=[{"kind": "other", "ref": "x"}],
        agent_id="research", claim_type="research_finding",
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
        find_claims, get_or_create_entity, write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Conf Filter {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    await write_claim(
        entity_id=entity_id, domain="test",
        finding_text="low conf", confidence=0.30,
        sources=[], agent_id="test", claim_type="probe",
    )
    await write_claim(
        entity_id=entity_id, domain="test",
        finding_text="high conf", confidence=0.85,
        sources=[], agent_id="test", claim_type="probe",
    )

    high = await find_claims(entity_id=entity_id, min_confidence=0.75)
    assert all(c.confidence >= 0.75 for c in high)
    assert any(c.finding_text == "high conf" for c in high)
    assert not any(c.finding_text == "low conf" for c in high)


@pytest.mark.asyncio
async def test_claim_freshness_hours_returns_age(supabase_client, cleanup_entities):
    """claim_freshness_hours returns age of latest matching claim in hours."""
    from app.services.intelligence.claims import (
        claim_freshness_hours, get_or_create_entity, write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Fresh Test {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )
    cleanup_entities.append(entity_id)

    await write_claim(
        entity_id=entity_id, domain="test",
        finding_text="recent claim", confidence=0.5,
        sources=[], agent_id="data", claim_type="cohort_retention",
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
    supabase_client, cleanup_entities,
):
    """claim_freshness_hours returns None when no matching claim exists."""
    from app.services.intelligence.claims import claim_freshness_hours

    nonexistent = uuid4()
    age = await claim_freshness_hours(
        entity_id=nonexistent, claim_type="cohort_retention", agent_id="data",
    )
    assert age is None
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/integration/test_intelligence_claims.py -k "find_claims or freshness" -v
```

- [ ] **Step 3: Implement `find_claims` and `claim_freshness_hours`**

Replace the stubs:

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
) -> list[Claim]:
    """Structured filter query over kg_findings. All filters AND'd.

    Returns Claim Pydantic models, freshest first.
    Empty result returns []; DB failure logs and returns [].

    Args:
        entity_id: Restrict to claims about this entity.
        agent_id: Restrict to claims emitted by this agent.
        claim_type: Restrict to a single claim type.
        domain: Restrict to a single domain.
        min_confidence: Floor confidence (inclusive).
        fresh_since: Only claims with freshness_at >= this timestamp.
        limit: Max rows returned. Default 50.

    Returns:
        list[Claim] sorted by freshness_at DESC.
    """
    from app.services.intelligence.schemas import ClaimSource
    from app.services.supabase_client import get_supabase_client

    try:
        client = get_supabase_client()
        q = client.table("kg_findings").select("*")
        if entity_id is not None:
            q = q.eq("entity_id", str(entity_id))
        if agent_id is not None:
            q = q.eq("agent_id", agent_id)
        if claim_type is not None:
            q = q.eq("claim_type", claim_type)
        if domain is not None:
            q = q.eq("domain", domain)
        if min_confidence > 0:
            q = q.gte("confidence", min_confidence)
        if fresh_since is not None:
            q = q.gte("freshness_at", fresh_since.isoformat())
        q = q.order("freshness_at", desc=True).limit(limit)
        result = q.execute()

        claims: list[Claim] = []
        for r in result.data or []:
            sources_raw = r.get("sources") or []
            sources = [
                ClaimSource(**s) if isinstance(s, dict) else ClaimSource(kind="other", ref=str(s))
                for s in sources_raw
            ]
            claims.append(Claim(
                id=UUID(r["id"]),
                entity_id=UUID(r["entity_id"]) if r.get("entity_id") else None,
                edge_id=UUID(r["edge_id"]) if r.get("edge_id") else None,
                agent_id=r["agent_id"],
                claim_type=r["claim_type"],
                domain=r["domain"],
                finding_text=r["finding_text"],
                confidence=float(r["confidence"]),
                sources=sources,
                contradicts=[UUID(c) for c in (r.get("contradicts") or [])],
                freshness_at=datetime.fromisoformat(r["freshness_at"].replace("Z", "+00:00"))
                    if isinstance(r["freshness_at"], str) else r["freshness_at"],
                expires_at=datetime.fromisoformat(r["expires_at"].replace("Z", "+00:00"))
                    if r.get("expires_at") and isinstance(r["expires_at"], str) else r.get("expires_at"),
                created_at=datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                    if isinstance(r["created_at"], str) else r["created_at"],
            ))
        return claims
    except Exception as e:
        logger.warning("find_claims failed: %s", e)
        return []


async def claim_freshness_hours(
    *,
    entity_id: UUID,
    claim_type: str | None = None,
    agent_id: str | None = None,
) -> float | None:
    """Age in hours of the most recent matching claim, or None if no match.

    Used by cache.should_query_graph to decide whether to skip a fetch.
    """
    from app.services.supabase_client import get_supabase_client

    try:
        client = get_supabase_client()
        q = (
            client.table("kg_findings")
            .select("freshness_at")
            .eq("entity_id", str(entity_id))
        )
        if claim_type is not None:
            q = q.eq("claim_type", claim_type)
        if agent_id is not None:
            q = q.eq("agent_id", agent_id)
        q = q.order("freshness_at", desc=True).limit(1)
        result = q.execute()
        if not result.data:
            return None

        freshness_at_raw = result.data[0]["freshness_at"]
        from datetime import timezone
        if isinstance(freshness_at_raw, str):
            freshness_at = datetime.fromisoformat(freshness_at_raw.replace("Z", "+00:00"))
        else:
            freshness_at = freshness_at_raw
        now = datetime.now(timezone.utc)
        delta = now - freshness_at
        return delta.total_seconds() / 3600.0
    except Exception as e:
        logger.warning("claim_freshness_hours failed: %s", e)
        return None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/integration/test_intelligence_claims.py -v
```

Expected: all claim tests PASS (some may skip if env vars unset).

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_intelligence_claims.py \
        app/services/intelligence/claims.py
git commit -m "feat(112-03): implement find_claims + claim_freshness_hours (GREEN)"
```

---

### Task 8: Update `__init__.py` public surface

**Files:**
- Modify: `app/services/intelligence/__init__.py`

- [ ] **Step 1: Replace `__init__.py` to export the new names**

```python
"""Shared intelligence infrastructure used by agents.

Public surface:
- score_confidence / to_band — generic weighted scorer and band classifier
- presets — named confidence formulas per agent domain
- write_claim / write_claims / find_claims — kg_findings writers and reader
- claim_freshness_hours — cache.py helper for graph-tier freshness check
- get_or_create_entity — entity resolution with idempotent upsert
- Claim / ClaimPayload / ClaimSource / ConfidenceBand — schemas

Plan 112-04 will add adaptive cache (should_query_graph, should_call_external).
See the design at docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md.
"""

from app.services.intelligence import presets
from app.services.intelligence.claims import (
    claim_freshness_hours,
    find_claims,
    get_or_create_entity,
    write_claim,
    write_claims,
)
from app.services.intelligence.confidence import score_confidence, to_band
from app.services.intelligence.schemas import (
    Claim,
    ClaimPayload,
    ClaimSource,
    ConfidenceBand,
)

__all__ = [
    "Claim",
    "ClaimPayload",
    "ClaimSource",
    "ConfidenceBand",
    "claim_freshness_hours",
    "find_claims",
    "get_or_create_entity",
    "presets",
    "score_confidence",
    "to_band",
    "write_claim",
    "write_claims",
]
```

- [ ] **Step 2: Import test** (from PowerShell):

```powershell
uv run python -c "
from app.services.intelligence import (
    score_confidence, to_band, presets,
    write_claim, write_claims, find_claims, claim_freshness_hours,
    get_or_create_entity,
    Claim, ClaimPayload, ClaimSource, ConfidenceBand,
)
print('full public surface OK')
"
```

Expected: `full public surface OK`.

- [ ] **Step 3: Commit**

```bash
git add app/services/intelligence/__init__.py
git commit -m "feat(112-03): expose claims module in intelligence public surface"
```

---

### Task 9: Lint + acceptance sign-off

**Files:** modify only if lint flags issues.

- [ ] **Step 1: Lint pass** (from PowerShell):

```powershell
uv run ruff check app/services/intelligence/ tests/unit/services/intelligence/ tests/integration/test_intelligence_claims.py
uv run ruff format app/services/intelligence/ tests/unit/services/intelligence/ tests/integration/test_intelligence_claims.py --check
uv run ty check app/services/intelligence/
```

Expected: all clean. If issues, fix in place. Common ruff issues: `B905` zip without `strict=`, import ordering, line length. Common ty issues: missing return type annotations.

- [ ] **Step 2: Re-run all tests to confirm**

```powershell
uv run pytest tests/unit/services/intelligence/ -v
uv run pytest tests/integration/test_intelligence_claims.py -v -m integration
```

Expected: all PASS.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add app/services/intelligence/ tests/unit/services/intelligence/ tests/integration/test_intelligence_claims.py
git commit -m "style(112-03): lint and format fixes for claims module"
```

(Skip if no fixes needed.)

- [ ] **Step 4: Final acceptance check** — confirm spec lines met:

| Spec line | Where verified |
|---|---|
| `write_claim` is INSERT not UPSERT | `claims.py` impl uses `.insert()` |
| `write_claim` defaults `embed=False` | Function signature + `test_write_claim_skips_embedding_by_default` |
| `write_claims` bulk insert in one statement | `claims.py` impl uses `.insert([rows])` |
| `find_claims` ORDER BY freshness_at DESC | `claims.py` impl uses `.order("freshness_at", desc=True)` |
| `claim_freshness_hours` returns None on no match | `test_claim_freshness_hours_no_match_returns_none` |
| `get_or_create_entity` idempotent | `test_get_or_create_entity_idempotent` |
| `Claim.band` computed from confidence | `test_claim_band_*` tests |
| Public surface importable from `app.services.intelligence` | Task 8 Step 2 |
| Reads degrade silently on failure | `find_claims` and `claim_freshness_hours` wrap in try/except, return [] / None |
| Writes raise on failure | `write_claim` / `write_claims` / `get_or_create_entity` raise on `result.data` empty |
| No new ADK tools | Verify with `git diff --name-only spec-b-clean..HEAD | grep -E "tool_id|tools_manifest"` returns nothing |

- [ ] **Step 5: Plan 112-03 complete. Plan 112-04 (cache module) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `ClaimSource`, `Claim`, `ClaimPayload` Pydantic schemas | Task 1 |
| `Claim.band` as computed property | Task 1 + Task 2 tests |
| `write_claim` async, returns UUID | Task 5 |
| `write_claims` bulk async, returns list[UUID] in order | Task 6 |
| `find_claims` structured filter, sorted by freshness DESC | Task 7 |
| `claim_freshness_hours` returns float \| None | Task 7 |
| `get_or_create_entity` idempotent UPSERT | Task 4 |
| Embedding opt-in via `embed=False` default | Task 5 |
| Reads degrade silently / Writes fail loudly | Task 5, Task 6, Task 7 implementations |
| Public surface re-exported via `__init__.py` | Task 8 |
| Lint clean (ruff + ty) | Task 9 |
| All integration tests pass against real Supabase | All Tasks 4-7 |

All spec lines covered. No placeholders. No unmapped requirements.
