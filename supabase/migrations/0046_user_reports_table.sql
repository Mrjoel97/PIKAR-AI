-- User-facing reports: workflow outcomes, initiative summaries, scheduled reports. Used by Reports page.
CREATE TABLE IF NOT EXISTS user_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    status TEXT NOT NULL DEFAULT 'Completed' CHECK (status IN ('Completed', 'Processing', 'Failed')),
    summary TEXT,
    content TEXT,
    source_type TEXT NOT NULL DEFAULT 'manual' CHECK (source_type IN ('workflow', 'initiative', 'scheduled', 'manual')),
    source_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_reports_user_created ON user_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_reports_user_category ON user_reports(user_id, category);
CREATE INDEX IF NOT EXISTS idx_user_reports_source ON user_reports(source_type, source_id) WHERE source_id IS NOT NULL;

ALTER TABLE user_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own reports"
    ON user_reports FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE user_reports IS 'Reports shown on Reports page: auto-saved workflow/initiative summaries and manual/scheduled reports';
