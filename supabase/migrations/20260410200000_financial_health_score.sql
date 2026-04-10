-- Migration: 20260410200000_financial_health_score.sql
-- Description: Persist daily financial health score snapshots (0-100) with factor breakdown

CREATE TABLE IF NOT EXISTS financial_health_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
    color TEXT NOT NULL CHECK (color IN ('green', 'yellow', 'red')),
    explanation TEXT NOT NULL,
    factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_financial_health_snapshots_user_computed
    ON financial_health_snapshots(user_id, computed_at DESC);

-- updated_at trigger
CREATE OR REPLACE FUNCTION update_financial_health_snapshots_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_financial_health_snapshots_updated_at ON financial_health_snapshots;
CREATE TRIGGER trg_financial_health_snapshots_updated_at
    BEFORE UPDATE ON financial_health_snapshots
    FOR EACH ROW EXECUTE FUNCTION update_financial_health_snapshots_updated_at();

-- RLS
ALTER TABLE financial_health_snapshots ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users can view own health snapshots" ON financial_health_snapshots
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Users can insert own health snapshots" ON financial_health_snapshots
        FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role manages health snapshots" ON financial_health_snapshots
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
