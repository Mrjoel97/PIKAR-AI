-- Migration: External DB monitoring jobs table
-- Phase: 46-analytics-continuous-intelligence Plan 01
-- Shared with Plan 03 (INTEL track) — created here since Plan 01 runs first

-- monitoring_jobs: tracks competitor/market/topic monitoring tasks per user
CREATE TABLE IF NOT EXISTS public.monitoring_jobs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    topic               text NOT NULL,
    monitoring_type     text NOT NULL DEFAULT 'competitor'
                            CHECK (monitoring_type IN ('competitor', 'market', 'topic')),
    importance          text NOT NULL DEFAULT 'normal'
                            CHECK (importance IN ('critical', 'normal', 'low')),
    is_active           boolean NOT NULL DEFAULT true,
    pinned_urls         text[] NOT NULL DEFAULT '{}',
    excluded_urls       text[] NOT NULL DEFAULT '{}',
    keyword_triggers    text[] NOT NULL DEFAULT '{}',
    last_run_at         timestamptz,
    last_brief_id       uuid,
    previous_state_hash text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS monitoring_jobs_user_id_idx
    ON public.monitoring_jobs (user_id);

CREATE INDEX IF NOT EXISTS monitoring_jobs_user_active_idx
    ON public.monitoring_jobs (user_id, is_active)
    WHERE is_active = true;

-- updated_at auto-maintenance
CREATE OR REPLACE FUNCTION public.set_monitoring_jobs_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER monitoring_jobs_updated_at
    BEFORE UPDATE ON public.monitoring_jobs
    FOR EACH ROW EXECUTE FUNCTION public.set_monitoring_jobs_updated_at();

-- Row Level Security
ALTER TABLE public.monitoring_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own monitoring jobs"
    ON public.monitoring_jobs
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role full access"
    ON public.monitoring_jobs
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
