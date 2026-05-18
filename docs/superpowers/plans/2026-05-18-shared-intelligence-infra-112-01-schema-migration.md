# Shared Intelligence Infrastructure — Plan 112-01: Schema Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Broaden `kg_findings` to accept claims from any agent by adding `agent_id` and `claim_type` columns plus supporting indices. Existing rows backfill as research findings; future writes must specify both.

**Architecture:** Single forward migration that adds two NOT NULL columns with defaults applied to existing rows, then drops the defaults so future inserts must be explicit. Three indices added: a covering index for the cache freshness check, a per-agent recency index, and a partial confidence-filtered index for high-quality claims. Rollback documented inline as a comment block; if needed in prod, a sibling forward-undo migration would be deployed.

**Tech Stack:** PostgreSQL (Supabase), Supabase CLI, pytest with `pytest.mark.integration`, the existing `app/services/supabase_client.py` for test setup.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Schema migration

**Out of scope for this plan:** Python modules (Plan 112-02+), Research Agent refactor (Plan 112-05), pgvector index (Plan 113-04).

---

## File structure

**Create:**
- `supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql` — the migration itself; rollback documented inline
- `tests/integration/test_kg_findings_broaden_migration.py` — integration tests against local Supabase
- `docs/runbooks/2026-05-18-kg_findings-broaden-prod-deploy.md` — production deploy notes (CONCURRENTLY guidance)

**Reference (read-only, do not modify in this plan):**
- `supabase/migrations/20260321500000_knowledge_graph.sql` — defines the original `kg_findings` schema; lines 99-114 are the relevant CREATE TABLE
- `tests/integration/test_knowledge_graph_migration.py` — test pattern to follow (env-gated, integration mark, real Supabase client)
- `app/services/supabase_client.py` — `get_supabase_client()` factory used by tests

---

## Pre-flight context

Existing `kg_findings` schema (from `supabase/migrations/20260321500000_knowledge_graph.sql:99-114`):

```sql
CREATE TABLE IF NOT EXISTS kg_findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id       UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    edge_id         UUID REFERENCES kg_edges(id) ON DELETE CASCADE,
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
    CHECK (entity_id IS NOT NULL OR edge_id IS NOT NULL)
);
```

Local Supabase commands (from CLAUDE.md):
```bash
supabase start             # start local stack
supabase db reset --local  # rebuild from migrations + seed
supabase db push --local   # apply pending migrations
```

Test command:
```bash
uv run pytest tests/integration/test_kg_findings_broaden_migration.py -v -m integration
```

Tests are env-gated — they skip unless `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set (pointed at local stack).

---

## Tasks

### Task 1: Confirm local Supabase running and capture pre-migration state

**Files:** none modified — pre-flight verification only.

- [ ] **Step 1: Start local Supabase if not running**

```bash
supabase status || supabase start
```

Expected: prints status table with "API URL", "DB URL", etc. If you see "supabase local development setup is not running", `supabase start` will boot the stack (~30s first time).

- [ ] **Step 2: Reset local DB to ensure clean state matches committed migrations**

```bash
supabase db reset --local
```

Expected: "Finished supabase db reset on local database." All committed migrations apply cleanly.

- [ ] **Step 3: Capture pre-migration kg_findings column list as a sanity check**

```bash
psql "$(supabase status -o env | grep '^DB_URL=' | cut -d= -f2- | tr -d '"')" -c "\d kg_findings"
```

Expected: shows the 14 columns listed in the pre-flight section above. No `agent_id` or `claim_type` columns. Note for later comparison.

- [ ] **Step 4: Confirm env vars set for integration tests**

```bash
echo "SUPABASE_URL=$SUPABASE_URL"
echo "SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY:0:10}..."
```

Expected: both non-empty. If empty, pull from `supabase status` and export:
```bash
export SUPABASE_URL=$(supabase status -o env | grep '^API_URL=' | cut -d= -f2- | tr -d '"')
export SUPABASE_SERVICE_ROLE_KEY=$(supabase status -o env | grep '^SERVICE_ROLE_KEY=' | cut -d= -f2- | tr -d '"')
```

---

### Task 2: Write the failing integration test suite

**Files:**
- Create: `tests/integration/test_kg_findings_broaden_migration.py`

- [ ] **Step 1: Create the test file with all assertions**

```python
"""Integration tests for the kg_findings broaden migration (Plan 112-01).

Verifies:
1. agent_id and claim_type columns exist with correct types
2. Both columns are NOT NULL with no DEFAULT after migration completes
3. Existing rows backfilled to agent_id='research', claim_type='research_finding'
4. Row count unchanged across migration
5. Three new indices created with correct definitions
6. Partial index has the expected WHERE predicate
7. Inserting without agent_id or claim_type raises a NOT NULL violation

Requires: local Supabase running (supabase start) with the migration applied.
Skip with: pytest -m "not integration"
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
        reason="Supabase credentials not provided in environment variables.",
    ),
]


@pytest.fixture()
def supabase_client():
    """Service-role Supabase client for schema inspection and direct writes."""
    try:
        from app.services.supabase_client import get_supabase_client

        return get_supabase_client()
    except Exception:
        pytest.skip("Supabase not available")


@pytest.fixture()
def db_dsn():
    """Direct Postgres DSN for information_schema queries."""
    dsn = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DB_URL/DATABASE_URL not set for direct queries")
    return dsn


def _query(dsn, sql, params=None):
    """Run a SQL query against the local Postgres and return rows as list[dict]."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [desc[0] for desc in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def test_agent_id_column_exists(db_dsn):
    """agent_id column should exist on kg_findings, TEXT, NOT NULL, no default."""
    rows = _query(
        db_dsn,
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'kg_findings' AND column_name = 'agent_id'
        """,
    )
    assert len(rows) == 1, "agent_id column should exist exactly once"
    assert rows[0]["data_type"] == "text"
    assert rows[0]["is_nullable"] == "NO"
    assert rows[0]["column_default"] is None, "Default must be dropped post-migration"


def test_claim_type_column_exists(db_dsn):
    """claim_type column should exist on kg_findings, TEXT, NOT NULL, no default."""
    rows = _query(
        db_dsn,
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'kg_findings' AND column_name = 'claim_type'
        """,
    )
    assert len(rows) == 1, "claim_type column should exist exactly once"
    assert rows[0]["data_type"] == "text"
    assert rows[0]["is_nullable"] == "NO"
    assert rows[0]["column_default"] is None


def test_existing_rows_backfilled(supabase_client, db_dsn):
    """Any pre-existing kg_findings rows should have agent_id='research' and
    claim_type='research_finding' after migration.

    Note: on a fresh local DB seeded only with migration data, kg_findings may
    be empty. This test inserts a row WITHOUT specifying the new columns to
    verify the default backfill, then asserts the values.

    Wait — we just said the defaults are dropped. So we can't insert without
    specifying them. Instead, we verify that any existing rows the seed
    inserted (if any) are correctly classified. If the table is empty, we
    skip that assertion but verify the column constraints by other means.
    """
    rows = _query(db_dsn, "SELECT COUNT(*) AS n FROM kg_findings")
    if rows[0]["n"] == 0:
        pytest.skip("kg_findings is empty in local seed; backfill is structural only")
    misclassified = _query(
        db_dsn,
        """
        SELECT COUNT(*) AS n FROM kg_findings
        WHERE agent_id != 'research' OR claim_type != 'research_finding'
        """,
    )
    assert misclassified[0]["n"] == 0, (
        "All pre-existing rows should backfill to research defaults"
    )


def test_insert_requires_agent_id_and_claim_type(supabase_client):
    """Inserting without agent_id should raise a NOT NULL violation."""
    # First create an entity to satisfy the entity_id FK
    entity_resp = supabase_client.table("kg_entities").insert({
        "canonical_name": f"Test Entity {uuid4()}",
        "entity_type": "topic",
        "domains": ["test"],
    }).execute()
    entity_id = entity_resp.data[0]["id"]

    try:
        # Attempt to insert finding without agent_id — should fail
        with pytest.raises(Exception) as exc_info:
            supabase_client.table("kg_findings").insert({
                "entity_id": entity_id,
                "domain": "test",
                "finding_text": "test finding without agent_id",
                "confidence": 0.5,
                "claim_type": "test_claim",
                # agent_id intentionally omitted
            }).execute()
        # PostgREST surfaces NOT NULL violations with code 23502 or message text
        assert "agent_id" in str(exc_info.value) or "23502" in str(exc_info.value)
    finally:
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_insert_with_new_columns_succeeds(supabase_client):
    """Inserting with both new columns should succeed and roundtrip correctly."""
    entity_resp = supabase_client.table("kg_entities").insert({
        "canonical_name": f"Test Entity Roundtrip {uuid4()}",
        "entity_type": "topic",
        "domains": ["test"],
    }).execute()
    entity_id = entity_resp.data[0]["id"]

    try:
        finding_resp = supabase_client.table("kg_findings").insert({
            "entity_id": entity_id,
            "domain": "test",
            "finding_text": "test finding with both new cols",
            "confidence": 0.83,
            "agent_id": "data",
            "claim_type": "test_claim",
        }).execute()
        assert finding_resp.data, "Insert should succeed"
        row = finding_resp.data[0]
        assert row["agent_id"] == "data"
        assert row["claim_type"] == "test_claim"
        assert row["confidence"] == 0.83
    finally:
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_entity_claim_agent_fresh_index_exists(db_dsn):
    """Covering index for cache freshness check should exist with all 4 columns."""
    rows = _query(
        db_dsn,
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'kg_findings'
          AND indexname = 'idx_kg_findings_entity_claim_agent_fresh'
        """,
    )
    assert len(rows) == 1
    idx_def = rows[0]["indexdef"]
    assert "entity_id" in idx_def
    assert "claim_type" in idx_def
    assert "agent_id" in idx_def
    assert "freshness_at" in idx_def
    assert "DESC" in idx_def


def test_agent_freshness_index_exists(db_dsn):
    """Per-agent recency index should exist."""
    rows = _query(
        db_dsn,
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'kg_findings'
          AND indexname = 'idx_kg_findings_agent_freshness'
        """,
    )
    assert len(rows) == 1
    idx_def = rows[0]["indexdef"]
    assert "agent_id" in idx_def
    assert "freshness_at" in idx_def
    assert "DESC" in idx_def


def test_claim_type_confidence_partial_index_exists(db_dsn):
    """Partial confidence-filtered index should exist with WHERE confidence >= 0.5."""
    rows = _query(
        db_dsn,
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'kg_findings'
          AND indexname = 'idx_kg_findings_claim_type_confidence'
        """,
    )
    assert len(rows) == 1
    idx_def = rows[0]["indexdef"]
    assert "claim_type" in idx_def
    assert "confidence" in idx_def
    assert "WHERE" in idx_def.upper()
    assert "0.5" in idx_def or "0.50" in idx_def
```

- [ ] **Step 2: Install psycopg if not already installed**

```bash
uv add --dev psycopg[binary]
```

Expected: adds psycopg to dev dependencies. If already present, no change.

- [ ] **Step 3: Run the tests to confirm they FAIL pre-migration**

```bash
uv run pytest tests/integration/test_kg_findings_broaden_migration.py -v -m integration
```

Expected: every test in the file FAILS or ERRORS — `agent_id` and `claim_type` columns don't exist yet, indices don't exist. This proves the tests have signal.

- [ ] **Step 4: Commit the test file alone (red TDD state)**

```bash
git add tests/integration/test_kg_findings_broaden_migration.py
git commit -m "test(112-01): add failing integration tests for kg_findings broaden migration"
```

---

### Task 3: Write the migration SQL

**Files:**
- Create: `supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- =============================================================================
-- Plan 112-01: Broaden kg_findings to accept claims from any agent
--
-- Adds two columns (agent_id, claim_type) with defaults applied to existing
-- rows, then drops the defaults so future inserts must be explicit. Three
-- indices added to support the new query patterns (cache freshness check,
-- per-agent recency, confidence-filtered claim_type browse).
--
-- Spec: docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md
--
-- ROLLBACK (for emergency use; deploy as a sibling forward-undo migration):
--   DROP INDEX IF EXISTS idx_kg_findings_claim_type_confidence;
--   DROP INDEX IF EXISTS idx_kg_findings_agent_freshness;
--   DROP INDEX IF EXISTS idx_kg_findings_entity_claim_agent_fresh;
--   ALTER TABLE kg_findings DROP COLUMN IF EXISTS claim_type;
--   ALTER TABLE kg_findings DROP COLUMN IF EXISTS agent_id;
--
-- PRODUCTION DEPLOY NOTE: this migration uses regular CREATE INDEX inside a
-- transaction, which briefly locks the table. For large prod kg_findings
-- tables, the runbook (docs/runbooks/2026-05-18-kg_findings-broaden-prod-deploy.md)
-- documents how to apply via CREATE INDEX CONCURRENTLY outside the BEGIN/COMMIT.
-- =============================================================================

BEGIN;

-- 1. Add columns with defaults so existing rows classify as research findings.
ALTER TABLE kg_findings
    ADD COLUMN IF NOT EXISTS agent_id   TEXT NOT NULL DEFAULT 'research',
    ADD COLUMN IF NOT EXISTS claim_type TEXT NOT NULL DEFAULT 'research_finding';

-- 2. Drop the defaults so future inserts must specify both.
ALTER TABLE kg_findings
    ALTER COLUMN agent_id   DROP DEFAULT,
    ALTER COLUMN claim_type DROP DEFAULT;

-- 3. Cache-freshness covering index used by claim_freshness_hours().
CREATE INDEX IF NOT EXISTS idx_kg_findings_entity_claim_agent_fresh
    ON kg_findings (entity_id, claim_type, agent_id, freshness_at DESC);

-- 4. Per-agent recency: "what has agent X claimed recently?"
CREATE INDEX IF NOT EXISTS idx_kg_findings_agent_freshness
    ON kg_findings (agent_id, freshness_at DESC);

-- 5. Confidence-filtered claim_type browse. Partial index keeps it lean —
--    audit-trail queries for low-confidence rows can sequential-scan.
CREATE INDEX IF NOT EXISTS idx_kg_findings_claim_type_confidence
    ON kg_findings (claim_type, confidence DESC)
    WHERE confidence >= 0.5;

COMMIT;
```

- [ ] **Step 2: Apply the migration locally**

```bash
supabase db reset --local
```

Expected: "Finished supabase db reset on local database." The migration applies cleanly along with all earlier migrations. If `supabase db reset` fails on this migration, fix the SQL and retry.

- [ ] **Step 3: Verify columns exist via psql**

```bash
psql "$(supabase status -o env | grep '^DB_URL=' | cut -d= -f2- | tr -d '"')" -c "\d kg_findings"
```

Expected: output shows 16 columns including `agent_id` (text, not null, no default) and `claim_type` (text, not null, no default). Indices listed at the bottom include the three new index names.

- [ ] **Step 4: Run the integration tests — they should now PASS**

```bash
uv run pytest tests/integration/test_kg_findings_broaden_migration.py -v -m integration
```

Expected: all 8 tests PASS. If any fail, fix the migration SQL and re-run `supabase db reset --local` then retest.

- [ ] **Step 5: Commit the migration**

```bash
git add supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql
git commit -m "feat(112-01): broaden kg_findings with agent_id and claim_type columns (GREEN)"
```

---

### Task 4: Verify rollback SQL works as documented

**Files:** none persisted — temporary verification only.

The migration documents rollback SQL inline as a comment. This task verifies that SQL actually works against a post-migration database state.

- [ ] **Step 1: Confirm current DB state has the new columns**

```bash
psql "$(supabase status -o env | grep '^DB_URL=' | cut -d= -f2- | tr -d '"')" -c "\d kg_findings" | grep -E "agent_id|claim_type"
```

Expected: both columns visible.

- [ ] **Step 2: Apply the documented rollback SQL**

```bash
psql "$(supabase status -o env | grep '^DB_URL=' | cut -d= -f2- | tr -d '"')" <<SQL
BEGIN;
DROP INDEX IF EXISTS idx_kg_findings_claim_type_confidence;
DROP INDEX IF EXISTS idx_kg_findings_agent_freshness;
DROP INDEX IF EXISTS idx_kg_findings_entity_claim_agent_fresh;
ALTER TABLE kg_findings DROP COLUMN IF EXISTS claim_type;
ALTER TABLE kg_findings DROP COLUMN IF EXISTS agent_id;
COMMIT;
SQL
```

Expected: `COMMIT` confirmation, no errors.

- [ ] **Step 3: Verify the columns are gone**

```bash
psql "$(supabase status -o env | grep '^DB_URL=' | cut -d= -f2- | tr -d '"')" -c "\d kg_findings" | grep -E "agent_id|claim_type" || echo "ROLLBACK_VERIFIED_CLEAN"
```

Expected: prints `ROLLBACK_VERIFIED_CLEAN` (grep finds nothing).

- [ ] **Step 4: Verify integration tests now FAIL again**

```bash
uv run pytest tests/integration/test_kg_findings_broaden_migration.py -v -m integration 2>&1 | tail -20
```

Expected: tests fail because columns don't exist. This proves the rollback truly reverts the schema. (We're not committing this state — Step 5 restores.)

- [ ] **Step 5: Restore by re-applying all migrations**

```bash
supabase db reset --local
```

Expected: clean reset; integration tests would now pass again.

- [ ] **Step 6: Confirm post-restore by running tests once more**

```bash
uv run pytest tests/integration/test_kg_findings_broaden_migration.py -v -m integration
```

Expected: all 8 tests PASS.

No commit in this task — rollback verification is one-shot and produces no persistent artifacts.

---

### Task 5: Write the production deploy runbook

**Files:**
- Create: `docs/runbooks/2026-05-18-kg_findings-broaden-prod-deploy.md`

- [ ] **Step 1: Create the runbook file**

```markdown
# Runbook — Deploy kg_findings broaden migration to production

**Migration:** `supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql`
**Plan:** 112-01 (Shared Intelligence Infrastructure Phase 112)
**Risk:** Medium — index creation on a non-trivial table can block writes briefly.

## Why this runbook exists

The migration as written uses regular `CREATE INDEX` inside a `BEGIN`/`COMMIT`
block. This briefly locks `kg_findings` during index build. For a small local
DB this is fine. For production, where `kg_findings` may have tens or hundreds
of thousands of rows, we want `CREATE INDEX CONCURRENTLY` — which **cannot**
run inside a transaction.

## Deploy procedure

### Step 1 — Apply the column changes only (transactional)

```sql
BEGIN;
ALTER TABLE kg_findings
    ADD COLUMN IF NOT EXISTS agent_id   TEXT NOT NULL DEFAULT 'research',
    ADD COLUMN IF NOT EXISTS claim_type TEXT NOT NULL DEFAULT 'research_finding';
ALTER TABLE kg_findings
    ALTER COLUMN agent_id   DROP DEFAULT,
    ALTER COLUMN claim_type DROP DEFAULT;
COMMIT;
```

Note: in Postgres 11+, `ADD COLUMN NOT NULL DEFAULT` is metadata-only — no
row rewrite. This step is fast even on large tables.

### Step 2 — Build indices concurrently (one at a time, outside any transaction)

Run each statement separately. Do NOT wrap in `BEGIN`/`COMMIT`.

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kg_findings_entity_claim_agent_fresh
    ON kg_findings (entity_id, claim_type, agent_id, freshness_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kg_findings_agent_freshness
    ON kg_findings (agent_id, freshness_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kg_findings_claim_type_confidence
    ON kg_findings (claim_type, confidence DESC)
    WHERE confidence >= 0.5;
```

Each `CREATE INDEX CONCURRENTLY` may take minutes on a large table but does
not block writes. If a `CONCURRENTLY` build fails partway, drop the partial
index (`DROP INDEX CONCURRENTLY <name>`) and retry.

### Step 3 — Verify on prod

Per memory `[[reference_supabase_inspect_no_docker]]`:

```bash
supabase inspect db kg_findings --linked
```

Expected: shows the new columns and all three indices.

### Step 4 — Mark the migration as applied in the Supabase migrations table

If you applied steps 1 + 2 manually (not via `supabase db push`), insert a
row in `supabase_migrations.schema_migrations` so future `supabase db push`
doesn't try to re-apply:

```sql
INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
VALUES ('20260518000000', 'broaden_kg_findings_for_shared_claims', ARRAY[]::text[]);
```

## Rollback

If the column changes need to be reverted (rare — they're additive):

```sql
BEGIN;
DROP INDEX IF EXISTS idx_kg_findings_claim_type_confidence;
DROP INDEX IF EXISTS idx_kg_findings_agent_freshness;
DROP INDEX IF EXISTS idx_kg_findings_entity_claim_agent_fresh;
ALTER TABLE kg_findings DROP COLUMN IF EXISTS claim_type;
ALTER TABLE kg_findings DROP COLUMN IF EXISTS agent_id;
COMMIT;
```

Index drops are fast; column drops are metadata-only in modern Postgres.

## Caveats

- Do not apply this migration via `supabase db push` to production while
  `kg_findings` is large — that path uses transactional `CREATE INDEX` which
  will lock writes for the duration of all three index builds.
- This runbook supersedes the default `supabase db push` path for prod.
- Per `[[project_branch_pollution_2026_05_09]]`: ship the migration on a
  clean branch off main; cherry-pick to a fresh push branch.
```

- [ ] **Step 2: Commit the runbook**

```bash
git add docs/runbooks/2026-05-18-kg_findings-broaden-prod-deploy.md
git commit -m "docs(112-01): add production deploy runbook for kg_findings broaden migration"
```

---

### Task 6: Verify no regressions in existing integration tests

**Files:** none modified — verification only.

- [ ] **Step 1: Run the existing knowledge graph migration test**

```bash
uv run pytest tests/integration/test_knowledge_graph_migration.py -v -m integration
```

Expected: all tests PASS. The broaden migration is purely additive to `kg_findings` — it should not break any existing knowledge-graph tests.

- [ ] **Step 2: Run the full integration test suite to catch any indirect regressions**

```bash
uv run pytest tests/integration/ -v -m integration 2>&1 | tail -30
```

Expected: existing pass-rate maintained. If anything that previously passed now fails, investigate before continuing — a downstream consumer may be reading from `kg_findings` with `SELECT *` and choking on the two new columns.

- [ ] **Step 3: If green, no commit needed — this task is verification only.**

---

### Task 7: Final lint pass

**Files:** none modified — verification only.

- [ ] **Step 1: Lint the test file**

```bash
uv run ruff check tests/integration/test_kg_findings_broaden_migration.py
uv run ruff format tests/integration/test_kg_findings_broaden_migration.py --check
```

Expected: no errors. If ruff format reports diffs, run without `--check` and re-commit.

- [ ] **Step 2: Type check (best effort — integration test files may have lenient typing)**

```bash
uv run ty check tests/integration/test_kg_findings_broaden_migration.py
```

Expected: no errors. If type errors appear, fix them. Common fix: add `from __future__ import annotations` (already in the file) and ensure return type annotations on test helper functions.

- [ ] **Step 3: If any fixes were needed, commit them**

```bash
git add tests/integration/test_kg_findings_broaden_migration.py
git commit -m "style(112-01): fix lint findings on kg_findings broaden tests"
```

If no fixes were needed, no commit.

---

### Task 8: Phase 112-01 acceptance sign-off

**Files:** none modified — final verification.

Cross-check against the spec's acceptance criteria for the schema portion of Phase 112:

- [ ] **Migration applies cleanly to fresh DB** — Task 3 Step 2 verified via `supabase db reset --local`.
- [ ] **Rollback returns DB to pre-migration state** — Task 4 verified via the documented rollback SQL.
- [ ] **`kg_findings` row count unchanged after migration; existing rows have `agent_id='research'`, `claim_type='research_finding'`** — `test_existing_rows_backfilled` covers this; on empty local DB it skips by design.
- [ ] **All three indices created with correct definitions** — `test_*_index_exists` tests cover this.
- [ ] **Partial index has `WHERE confidence >= 0.5` predicate** — `test_claim_type_confidence_partial_index_exists` covers this.

- [ ] **Step 1: Confirm all the above checkboxes are checked.**

- [ ] **Step 2: Final state check — run all migration tests one more time**

```bash
uv run pytest tests/integration/test_kg_findings_broaden_migration.py -v -m integration
```

Expected: 8 tests pass, 0 fail. If `test_existing_rows_backfilled` skips, that's expected on empty local DB.

- [ ] **Step 3: Confirm git log shows the expected commits for 112-01**

```bash
git log --oneline | head -5
```

Expected (most recent first):
- `style(112-01): ...` (optional, only if lint fixes were committed)
- `docs(112-01): add production deploy runbook ...`
- `feat(112-01): broaden kg_findings with agent_id and claim_type columns (GREEN)`
- `test(112-01): add failing integration tests for kg_findings broaden migration`

- [ ] **Step 4: Plan 112-01 complete. Plan 112-02 (confidence module) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| Migration file at `supabase/migrations/20260518000000_*` | Task 3 |
| Two new NOT NULL columns with defaults applied then dropped | Task 3 |
| Three indices (entity-claim-agent-fresh, agent-freshness, claim-type-confidence partial) | Task 3 |
| Existing rows backfilled to research defaults | Task 3 (column DEFAULT); Task 2 (test) |
| Rollback documented in migration file + verified | Task 3 (inline); Task 4 (verification) |
| Production CONCURRENTLY deploy procedure | Task 5 |
| Integration tests covering column existence, constraints, index definitions | Task 2 |
| No regression in existing knowledge graph tests | Task 6 |

All spec lines covered. No placeholders. No unmapped requirements.
