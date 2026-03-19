CREATE TABLE IF NOT EXISTS user_briefing_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    briefing_time TIME NOT NULL DEFAULT '07:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    email_digest_enabled BOOLEAN NOT NULL DEFAULT true,
    email_digest_frequency TEXT NOT NULL DEFAULT 'daily' CHECK (email_digest_frequency IN ('daily', 'weekdays', 'off')),
    auto_act_enabled BOOLEAN NOT NULL DEFAULT false,
    auto_act_daily_cap INTEGER NOT NULL DEFAULT 10,
    auto_act_categories TEXT[] DEFAULT '{}',
    vip_senders TEXT[] DEFAULT '{}',
    ignored_senders TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE user_briefing_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own preferences"
    ON user_briefing_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
    ON user_briefing_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON user_briefing_preferences FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to briefing preferences"
    ON user_briefing_preferences FOR ALL
    USING (auth.role() = 'service_role');

CREATE TRIGGER briefing_preferences_updated_at
    BEFORE UPDATE ON user_briefing_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_email_triage_updated_at();
