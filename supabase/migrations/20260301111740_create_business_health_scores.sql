-- Migration: 20260301111740_create_business_health_scores.sql
-- Description: Persist business health score snapshots for trend analysis

CREATE TABLE IF NOT EXISTS business_health_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    overall_score INTEGER NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    revenue_score INTEGER CHECK (revenue_score >= 0 AND revenue_score <= 100),
    pipeline_score INTEGER CHECK (pipeline_score >= 0 AND pipeline_score <= 100),
    traffic_score INTEGER CHECK (traffic_score >= 0 AND traffic_score <= 100),
    progress_score INTEGER CHECK (progress_score >= 0 AND progress_score <= 100),
    health_label TEXT NOT NULL,
    metrics JSONB DEFAULT '{}'::jsonb,
    dimension_payload JSONB DEFAULT '{}'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    score_version TEXT DEFAULT 'v1',
    trigger TEXT DEFAULT 'manual' CHECK (trigger IN ('manual', 'auto', 'agent', 'scheduled', 'ephemeral', 'system')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_business_health_scores_user_created
    ON business_health_scores(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_business_health_scores_created
    ON business_health_scores(created_at DESC);

ALTER TABLE business_health_scores ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users can view own business health scores" ON business_health_scores
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role manages business health scores" ON business_health_scores
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
