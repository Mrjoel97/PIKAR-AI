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

-- 5. Confidence-filtered claim_type browse. Partial index keeps it lean --
--    audit-trail queries for low-confidence rows can sequential-scan.
CREATE INDEX IF NOT EXISTS idx_kg_findings_claim_type_confidence
    ON kg_findings (claim_type, confidence DESC)
    WHERE confidence >= 0.5;

COMMIT;
