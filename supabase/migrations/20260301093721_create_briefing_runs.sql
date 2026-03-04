-- Voice daily briefing runs and archive

CREATE TABLE IF NOT EXISTS briefing_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trigger TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'generated',
    greeting TEXT,
    headline TEXT,
    pending_approvals JSONB NOT NULL DEFAULT '[]'::jsonb,
    online_agents INTEGER NOT NULL DEFAULT 0,
    agents JSONB NOT NULL DEFAULT '[]'::jsonb,
    system_status TEXT,
    summary_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    sections JSONB NOT NULL DEFAULT '[]'::jsonb,
    script_text TEXT,
    voice_handoff JSONB NOT NULL DEFAULT '{}'::jsonb,
    preferences_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_briefing_runs_user_generated_at
ON briefing_runs(user_id, generated_at DESC);

ALTER TABLE briefing_runs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'briefing_runs'
          AND policyname = 'Users can view own briefing runs'
    ) THEN
        CREATE POLICY "Users can view own briefing runs"
        ON briefing_runs FOR SELECT
        TO authenticated
        USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'briefing_runs'
          AND policyname = 'Service role manages briefing runs'
    ) THEN
        CREATE POLICY "Service role manages briefing runs"
        ON briefing_runs FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
    END IF;
END $$;

COMMENT ON TABLE briefing_runs IS 'Persisted daily briefings and voice handoff payloads for each user.';
