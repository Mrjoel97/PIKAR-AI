-- Integration Infrastructure: credential storage and sync state tracking
-- Phase 39-01: Foundation for all external integration phases (40-47)

-- ============================================================================
-- Trigger function for updated_at (reusable)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- ============================================================================
-- integration_credentials: Fernet-encrypted OAuth tokens per user per provider
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.integration_credentials (
    id            uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider      text        NOT NULL,
    access_token  text        NOT NULL,          -- Fernet ciphertext
    refresh_token text,                           -- Fernet ciphertext, nullable for API-key providers
    token_type    text        NOT NULL DEFAULT 'bearer',
    scopes        text        NOT NULL DEFAULT '',
    expires_at    timestamptz,                    -- nullable for non-expiring tokens
    account_name  text        NOT NULL DEFAULT '',
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_integration_credentials_user_provider
        UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_integration_credentials_user_provider
    ON public.integration_credentials (user_id, provider);

-- RLS policies
ALTER TABLE public.integration_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own integration credentials"
    ON public.integration_credentials FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own integration credentials"
    ON public.integration_credentials FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own integration credentials"
    ON public.integration_credentials FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own integration credentials"
    ON public.integration_credentials FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for OAuth callback (no user JWT in popup callback)
CREATE POLICY "Service role full access to integration credentials"
    ON public.integration_credentials FOR ALL
    USING (auth.role() = 'service_role');

-- updated_at trigger
CREATE TRIGGER set_integration_credentials_updated_at
    BEFORE UPDATE ON public.integration_credentials
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- integration_sync_state: tracks sync progress per user per provider
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.integration_sync_state (
    id            uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider      text        NOT NULL,
    last_sync_at  timestamptz,
    sync_cursor   jsonb       DEFAULT '{}'::jsonb,   -- pagination token, provider-specific
    error_count   integer     NOT NULL DEFAULT 0,
    last_error    text,
    backoff_until timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_integration_sync_state_user_provider
        UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_integration_sync_state_user_provider
    ON public.integration_sync_state (user_id, provider);

-- RLS policies
ALTER TABLE public.integration_sync_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own sync state"
    ON public.integration_sync_state FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sync state"
    ON public.integration_sync_state FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sync state"
    ON public.integration_sync_state FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own sync state"
    ON public.integration_sync_state FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for background sync operations
CREATE POLICY "Service role full access to integration sync state"
    ON public.integration_sync_state FOR ALL
    USING (auth.role() = 'service_role');

-- updated_at trigger
CREATE TRIGGER set_integration_sync_state_updated_at
    BEFORE UPDATE ON public.integration_sync_state
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
