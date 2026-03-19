CREATE TABLE IF NOT EXISTS email_triage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    gmail_message_id TEXT NOT NULL,
    thread_id TEXT,

    -- Email metadata
    sender TEXT NOT NULL,
    sender_name TEXT,
    subject TEXT,
    snippet TEXT,
    received_at TIMESTAMPTZ,

    -- AI classification
    priority TEXT NOT NULL CHECK (priority IN ('urgent', 'important', 'normal', 'low')),
    action_type TEXT NOT NULL CHECK (action_type IN ('needs_reply', 'needs_review', 'fyi', 'auto_handle', 'spam')),
    category TEXT CHECK (category IN ('meeting', 'deal', 'task', 'report', 'personal', 'newsletter', 'notification')),
    confidence FLOAT NOT NULL,
    classification_reasoning TEXT,

    -- Draft response
    draft_reply TEXT,
    draft_confidence FLOAT,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'sent', 'dismissed', 'auto_handled')),
    auto_action_taken TEXT,
    user_action TEXT,
    acted_at TIMESTAMPTZ,

    -- Briefing association
    briefing_date DATE NOT NULL DEFAULT CURRENT_DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, gmail_message_id)
);

CREATE INDEX IF NOT EXISTS idx_email_triage_user_date ON email_triage(user_id, briefing_date);
CREATE INDEX IF NOT EXISTS idx_email_triage_status ON email_triage(user_id, status);
CREATE INDEX IF NOT EXISTS idx_email_triage_gmail_id ON email_triage(gmail_message_id);

ALTER TABLE email_triage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own triage items"
    ON email_triage FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own triage items"
    ON email_triage FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to email_triage"
    ON email_triage FOR ALL
    USING (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION update_email_triage_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER email_triage_updated_at
    BEFORE UPDATE ON email_triage
    FOR EACH ROW
    EXECUTE FUNCTION update_email_triage_updated_at();

ALTER PUBLICATION supabase_realtime ADD TABLE email_triage;

-- RPC to get provider refresh token from auth.sessions (service role only)
CREATE OR REPLACE FUNCTION get_user_provider_refresh_token(p_user_id UUID)
RETURNS TABLE(provider_refresh_token TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT s.provider_refresh_token
    FROM auth.sessions s
    WHERE s.user_id = p_user_id
      AND s.provider_refresh_token IS NOT NULL
    ORDER BY s.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
