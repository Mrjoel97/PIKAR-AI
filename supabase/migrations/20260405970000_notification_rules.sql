-- Notification Infrastructure: Phase 45
-- notification_rules: per-user rules routing event types to provider channels.
-- notification_channel_config: per-user provider-level settings (daily briefing, etc.).

-- =============================================================================
-- 1. notification_rules
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('slack', 'teams')),
    event_type TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT NOT NULL DEFAULT '',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT notification_rules_user_provider_event_channel_unique
        UNIQUE (user_id, provider, event_type, channel_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_user
    ON public.notification_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_rules_user_provider
    ON public.notification_rules(user_id, provider);

ALTER TABLE public.notification_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notification_rules_select_own" ON public.notification_rules
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "notification_rules_insert_own" ON public.notification_rules
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "notification_rules_update_own" ON public.notification_rules
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "notification_rules_delete_own" ON public.notification_rules
    FOR DELETE USING (auth.uid() = user_id);

CREATE TRIGGER set_notification_rules_updated_at
    BEFORE UPDATE ON public.notification_rules
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

-- =============================================================================
-- 2. notification_channel_config
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.notification_channel_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('slack', 'teams')),
    daily_briefing BOOLEAN NOT NULL DEFAULT false,
    briefing_channel_id TEXT,
    briefing_channel_name TEXT NOT NULL DEFAULT '',
    briefing_time_utc TEXT NOT NULL DEFAULT '08:00',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT notification_channel_config_user_provider_unique
        UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_notification_channel_config_user
    ON public.notification_channel_config(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_channel_config_user_provider
    ON public.notification_channel_config(user_id, provider);

ALTER TABLE public.notification_channel_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notification_channel_config_select_own" ON public.notification_channel_config
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "notification_channel_config_insert_own" ON public.notification_channel_config
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "notification_channel_config_update_own" ON public.notification_channel_config
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "notification_channel_config_delete_own" ON public.notification_channel_config
    FOR DELETE USING (auth.uid() = user_id);

CREATE TRIGGER set_notification_channel_config_updated_at
    BEFORE UPDATE ON public.notification_channel_config
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);
