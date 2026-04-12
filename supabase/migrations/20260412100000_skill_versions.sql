-- Migration: skill_versions
-- Purpose: Persist versioned skill refinements for the SelfImprovementEngine.
-- Each refinement writes a new row with is_active=true; the unique partial index
-- guarantees at most one active version per skill_name.  Revert restores the
-- previous version by flipping is_active flags.
--
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards).

-- -----------------------------------------------------------------------
-- 1. Table
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name      TEXT NOT NULL,
    version         TEXT NOT NULL,
    knowledge       TEXT,
    previous_version_id UUID REFERENCES skill_versions(id),
    source_action_id    UUID REFERENCES improvement_actions(id),
    created_by      TEXT NOT NULL DEFAULT 'system:self-improvement-engine',
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    is_active       BOOLEAN DEFAULT FALSE NOT NULL,
    metadata        JSONB DEFAULT '{}'
);

-- -----------------------------------------------------------------------
-- 2. Indexes
-- -----------------------------------------------------------------------

-- Enforce exactly one active version per skill_name
CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_versions_active
    ON skill_versions (skill_name) WHERE is_active = true;

-- Fast lookups by name + recency
CREATE INDEX IF NOT EXISTS idx_skill_versions_name
    ON skill_versions (skill_name, created_at DESC);

-- Fast active-version lookups
CREATE INDEX IF NOT EXISTS idx_skill_versions_active_lookup
    ON skill_versions (skill_name, is_active);

-- -----------------------------------------------------------------------
-- 3. Row Level Security
-- -----------------------------------------------------------------------
ALTER TABLE skill_versions ENABLE ROW LEVEL SECURITY;

-- Read access for authenticated and service_role
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_policies
        WHERE tablename = 'skill_versions'
          AND policyname = 'skill_versions_read_access'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY skill_versions_read_access ON skill_versions
                FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'service_role')
        $policy$;
    END IF;
END
$$;

-- Full write access for service_role only
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_policies
        WHERE tablename = 'skill_versions'
          AND policyname = 'skill_versions_write_access'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY skill_versions_write_access ON skill_versions
                FOR ALL USING (auth.role() = 'service_role')
        $policy$;
    END IF;
END
$$;
