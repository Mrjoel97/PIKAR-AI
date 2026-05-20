-- Migration: skill_experiments
-- Purpose: A/B eval harness for the SelfImprovementEngine.  Refined skills enter
-- an experiment instead of being promoted immediately.  Traffic is split per-user
-- (sticky hash of user_id + experiment_id) between the current active version
-- (control) and the candidate version (treatment).  The evaluator promotes or
-- reverts based on a two-proportion z-test over the interaction-level quality
-- signal.
--
-- Idempotent: safe to run multiple times.

-- ============================================================================
-- 1. skill_experiments table
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_experiments (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name            TEXT NOT NULL,
    control_version_id    UUID NOT NULL REFERENCES skill_versions(id),
    candidate_version_id  UUID NOT NULL REFERENCES skill_versions(id),
    source_action_id      UUID REFERENCES improvement_actions(id),
    state                 TEXT NOT NULL DEFAULT 'running'
                          CHECK (state IN ('running','promoted','reverted','aborted')),
    min_samples_per_arm   INTEGER NOT NULL DEFAULT 50,
    max_samples_per_arm   INTEGER NOT NULL DEFAULT 500,
    max_duration_days     INTEGER NOT NULL DEFAULT 14,
    alpha                 REAL    NOT NULL DEFAULT 0.05,
    min_effect_size       REAL    NOT NULL DEFAULT 0.05,
    started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at            TIMESTAMPTZ,
    decision_reason       TEXT,
    metadata              JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- At most one live experiment per skill_name (mirrors the active-version pattern
-- used by skill_versions).
CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_experiments_one_running
    ON skill_experiments (skill_name) WHERE state = 'running';

CREATE INDEX IF NOT EXISTS idx_skill_experiments_state
    ON skill_experiments (state, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_skill_experiments_skill_name
    ON skill_experiments (skill_name, started_at DESC);

-- RLS: service-role writes; authenticated reads (dashboard surface).
ALTER TABLE skill_experiments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_policies
        WHERE tablename = 'skill_experiments'
          AND policyname = 'skill_experiments_read_access'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY skill_experiments_read_access ON skill_experiments
                FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'service_role')
        $policy$;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_policies
        WHERE tablename = 'skill_experiments'
          AND policyname = 'skill_experiments_write_access'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY skill_experiments_write_access ON skill_experiments
                FOR ALL USING (auth.role() = 'service_role')
        $policy$;
    END IF;
END
$$;

-- ============================================================================
-- 2. Extend interaction_logs with experiment attribution
-- ============================================================================
ALTER TABLE interaction_logs
    ADD COLUMN IF NOT EXISTS skill_version_id UUID REFERENCES skill_versions(id),
    ADD COLUMN IF NOT EXISTS experiment_id    UUID REFERENCES skill_experiments(id),
    ADD COLUMN IF NOT EXISTS variant          TEXT;

DO $$
BEGIN
    ALTER TABLE interaction_logs
        DROP CONSTRAINT IF EXISTS interaction_logs_variant_check;

    ALTER TABLE interaction_logs
        ADD CONSTRAINT interaction_logs_variant_check
        CHECK (variant IS NULL OR variant IN ('control','treatment'));
END
$$;

-- Drives per-experiment aggregation queries (the evaluator's hot path).
CREATE INDEX IF NOT EXISTS idx_interaction_logs_experiment
    ON interaction_logs (experiment_id, variant, created_at DESC)
    WHERE experiment_id IS NOT NULL;

-- Per-version forensics + ad-hoc joins.
CREATE INDEX IF NOT EXISTS idx_interaction_logs_skill_version
    ON interaction_logs (skill_version_id)
    WHERE skill_version_id IS NOT NULL;

-- ============================================================================
-- 3. Relax improvement_actions.status CHECK to allow 'experimenting' + 'deferred'
-- ============================================================================
DO $$
BEGIN
    ALTER TABLE improvement_actions
        DROP CONSTRAINT IF EXISTS improvement_actions_status_check;

    ALTER TABLE improvement_actions
        ADD CONSTRAINT improvement_actions_status_check
        CHECK (status IN (
            'pending',
            'applied',
            'validated',
            'reverted',
            'pending_approval',
            'declined',
            'failed',
            'experimenting',
            'deferred'
        ));
END
$$;
