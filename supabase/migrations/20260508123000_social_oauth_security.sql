-- Persist OAuth PKCE verifier state outside process memory and document
-- encrypted storage expectations for social account tokens.

CREATE TABLE IF NOT EXISTS public.oauth_pkce_states (
    state TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    code_verifier TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oauth_pkce_states_user_platform
    ON public.oauth_pkce_states (user_id, platform);

CREATE INDEX IF NOT EXISTS idx_oauth_pkce_states_expires_at
    ON public.oauth_pkce_states (expires_at);

ALTER TABLE public.oauth_pkce_states ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages oauth pkce states"
    ON public.oauth_pkce_states;

CREATE POLICY "Service role manages oauth pkce states"
    ON public.oauth_pkce_states
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE public.oauth_pkce_states IS
    'Short-lived OAuth PKCE verifier state used by server-side social callbacks.';

COMMENT ON COLUMN public.oauth_pkce_states.code_verifier IS
    'Fernet-encrypted PKCE verifier. Rows are consumed and deleted during OAuth callback handling.';

COMMENT ON COLUMN public.connected_accounts.access_token IS
    'Fernet-encrypted OAuth access token. Legacy plaintext values are tolerated by the app until accounts reconnect or refresh.';

COMMENT ON COLUMN public.connected_accounts.refresh_token IS
    'Fernet-encrypted OAuth refresh token. Legacy plaintext values are tolerated by the app until accounts reconnect or refresh.';
