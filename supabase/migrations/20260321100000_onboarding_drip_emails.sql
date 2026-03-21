-- Post-onboarding drip email scheduling
-- Tracks persona-specific email sequences sent after onboarding completes

CREATE TABLE IF NOT EXISTS onboarding_drip_emails (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    email TEXT NOT NULL,
    first_name TEXT,
    persona TEXT NOT NULL CHECK (persona IN ('solopreneur', 'startup', 'sme', 'enterprise')),
    drip_key TEXT NOT NULL CHECK (drip_key IN ('welcome', 'tips', 'checkin')),
    drip_day INT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'skipped')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, drip_key)
);

-- Index for the cron query: find pending drips that are due
CREATE INDEX IF NOT EXISTS idx_drip_emails_pending_due
    ON onboarding_drip_emails (status, scheduled_at)
    WHERE status = 'pending';

-- Index for user lookup
CREATE INDEX IF NOT EXISTS idx_drip_emails_user
    ON onboarding_drip_emails (user_id);

-- RLS
ALTER TABLE onboarding_drip_emails ENABLE ROW LEVEL SECURITY;

-- Service role can manage all drip records
CREATE POLICY "service_role_drip_full"
    ON onboarding_drip_emails
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Users can view their own drip records
CREATE POLICY "users_view_own_drips"
    ON onboarding_drip_emails
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());


-- ─── In-app onboarding checklist ────────────────────────────────────────────
-- Tracks persona-specific guided actions shown inside the dashboard

CREATE TABLE IF NOT EXISTS onboarding_checklist (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    persona TEXT NOT NULL CHECK (persona IN ('solopreneur', 'startup', 'sme', 'enterprise')),
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    dismissed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Index for quick dashboard load
CREATE INDEX IF NOT EXISTS idx_checklist_user
    ON onboarding_checklist (user_id)
    WHERE dismissed_at IS NULL;

-- RLS
ALTER TABLE onboarding_checklist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_checklist_full"
    ON onboarding_checklist
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "users_manage_own_checklist"
    ON onboarding_checklist
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
