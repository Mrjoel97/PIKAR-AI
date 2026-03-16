-- ============================================================================
-- Public waitlist signups for prelaunch demand capture
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.waitlist_signups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    full_name TEXT,
    company_or_role TEXT,
    biggest_bottleneck TEXT,
    source TEXT NOT NULL DEFAULT 'landing_page',
    page_path TEXT,
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    user_agent TEXT,
    ip_address TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_waitlist_signups_email_unique
ON public.waitlist_signups (LOWER(email));

CREATE INDEX IF NOT EXISTS idx_waitlist_signups_created_at
ON public.waitlist_signups (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_waitlist_signups_source
ON public.waitlist_signups (source);

ALTER TABLE public.waitlist_signups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can join waitlist" ON public.waitlist_signups;
CREATE POLICY "Anyone can join waitlist"
ON public.waitlist_signups FOR INSERT
WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role has full access to waitlist_signups" ON public.waitlist_signups;
CREATE POLICY "Service role has full access to waitlist_signups"
ON public.waitlist_signups FOR ALL
USING ((current_setting('request.jwt.claims', true)::json ->> 'role') = 'service_role')
WITH CHECK ((current_setting('request.jwt.claims', true)::json ->> 'role') = 'service_role');

COMMENT ON TABLE public.waitlist_signups IS 'Public landing-page waitlist signups captured before product launch.';
