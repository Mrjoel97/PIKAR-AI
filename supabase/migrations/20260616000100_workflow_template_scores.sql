-- Migration: workflow_template_scores
-- Purpose: Per-version effectiveness scoring for workflow templates.
-- Mirrors skill_scores: rolling-window aggregation of run telemetry into
-- composite scores, trend tracking, and dashboard visibility.
--
-- Pillar 2 of the self-improvement eval harness — scoring only; no
-- auto-refinement of workflow templates yet.
--
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS workflow_template_scores (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Template + version under evaluation.  template_version_id is the
    -- preferred grain — when a version is pinned at run start we attribute
    -- run outcomes to that specific snapshot.  template_id is kept for
    -- joining and for legacy runs whose template_version_id is NULL.
    template_id             UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,
    template_version_id     UUID REFERENCES workflow_template_versions(id) ON DELETE SET NULL,

    -- Bucket label (mirror skill_scores.evaluation_period).
    evaluation_period       TEXT NOT NULL,
    period_start            TIMESTAMPTZ NOT NULL,
    period_end              TIMESTAMPTZ NOT NULL,

    -- Counts
    total_runs              INTEGER NOT NULL DEFAULT 0,
    unique_users            INTEGER NOT NULL DEFAULT 0,

    -- Rates derived from workflow_executions + workflow_steps.
    -- All in [0.0, 1.0]; the composite uses the weights documented in
    -- app/services/workflow_template_scoring.py.
    completion_rate         REAL NOT NULL DEFAULT 0.0,
    error_rate              REAL NOT NULL DEFAULT 0.0,
    retry_rate              REAL NOT NULL DEFAULT 0.0,
    escalation_rate         REAL NOT NULL DEFAULT 0.0,

    -- Weighted composite (the "val_bpb" analogue for workflows).
    effectiveness_score     REAL NOT NULL DEFAULT 0.0,

    -- Trend against the previous row for the same (template_id, template_version_id).
    score_delta             REAL,
    trend                   TEXT CHECK (trend IN ('improving','stable','declining','new')),

    metadata                JSONB NOT NULL DEFAULT '{}'::jsonb,
    evaluated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (template_id, template_version_id, evaluation_period)
);

CREATE INDEX IF NOT EXISTS idx_workflow_template_scores_template
    ON workflow_template_scores (template_id, evaluated_at DESC);

CREATE INDEX IF NOT EXISTS idx_workflow_template_scores_version
    ON workflow_template_scores (template_version_id, evaluated_at DESC)
    WHERE template_version_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workflow_template_scores_effectiveness
    ON workflow_template_scores (effectiveness_score DESC);

-- RLS: service-role write; authenticated read for dashboards.
ALTER TABLE workflow_template_scores ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_policies
        WHERE tablename = 'workflow_template_scores'
          AND policyname = 'workflow_template_scores_read_access'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY workflow_template_scores_read_access ON workflow_template_scores
                FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'service_role')
        $policy$;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_policies
        WHERE tablename = 'workflow_template_scores'
          AND policyname = 'workflow_template_scores_write_access'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY workflow_template_scores_write_access ON workflow_template_scores
                FOR ALL USING (auth.role() = 'service_role')
        $policy$;
    END IF;
END
$$;
