-- ============================================================
-- Competitive Monitoring: tracked competitors + change log
-- Run this migration in Supabase SQL Editor
-- ============================================================

CREATE TABLE public.monitored_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    industry TEXT,

    -- Monitoring config
    check_frequency_hours INT NOT NULL DEFAULT 168,  -- weekly by default
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Last check state
    last_checked_at TIMESTAMPTZ,
    last_content_hash TEXT,  -- MD5 of scraped content for diff detection
    last_snapshot TEXT,      -- abbreviated content snapshot

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_competitors_user ON public.monitored_competitors(user_id);
CREATE INDEX idx_competitors_active ON public.monitored_competitors(user_id, is_active);

ALTER TABLE public.monitored_competitors ENABLE ROW LEVEL SECURITY;

CREATE POLICY comp_select ON public.monitored_competitors
    FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()));
CREATE POLICY comp_insert ON public.monitored_competitors
    FOR INSERT TO authenticated WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY comp_update ON public.monitored_competitors
    FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY comp_delete ON public.monitored_competitors
    FOR DELETE TO authenticated USING (user_id = (SELECT auth.uid()));

-- Change detection log
CREATE TABLE public.competitor_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID NOT NULL REFERENCES public.monitored_competitors(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    change_type TEXT NOT NULL,  -- 'content_update', 'new_page', 'pricing_change', 'feature_launch'
    summary TEXT NOT NULL,      -- AI-generated summary of what changed
    old_snapshot TEXT,
    new_snapshot TEXT,
    significance TEXT DEFAULT 'low',  -- low, medium, high

    detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_comp_changes_competitor ON public.competitor_changes(competitor_id, detected_at DESC);
CREATE INDEX idx_comp_changes_user ON public.competitor_changes(user_id, detected_at DESC);

ALTER TABLE public.competitor_changes ENABLE ROW LEVEL SECURITY;

CREATE POLICY comp_changes_select ON public.competitor_changes
    FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()));
CREATE POLICY comp_changes_insert ON public.competitor_changes
    FOR INSERT TO authenticated WITH CHECK (user_id = (SELECT auth.uid()));

-- Auto-update
CREATE OR REPLACE FUNCTION public.update_competitors_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;

CREATE TRIGGER trg_competitors_updated_at
    BEFORE UPDATE ON public.monitored_competitors
    FOR EACH ROW EXECUTE FUNCTION public.update_competitors_updated_at();
