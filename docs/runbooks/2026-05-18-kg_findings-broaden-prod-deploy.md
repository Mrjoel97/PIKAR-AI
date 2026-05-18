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

This rollback was verified locally during Plan 112-01 Task 4 — applied cleanly
and the integration tests returned to the pre-migration red state.

## Caveats

- Do not apply this migration via `supabase db push` to production while
  `kg_findings` is large — that path uses transactional `CREATE INDEX` which
  will lock writes for the duration of all three index builds.
- This runbook supersedes the default `supabase db push` path for prod.
- Per `[[project_branch_pollution_2026_05_09]]`: ship the migration on a
  clean branch off main; cherry-pick to a fresh push branch.
- Local-dev note: `supabase db push --local` on this workstation currently
  has drift issues — many migrations applied directly to the local DB
  without being tracked. Local migration testing uses
  `docker exec -i supabase_db_<project> psql -U postgres -d postgres -f /dev/stdin < <migration>`
  as a fallback. This does not affect production deploys, which use the
  procedure documented above.
