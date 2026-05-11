-- Restore ad_budget_caps table.
--
-- The original migration 20260405900000_ad_budget_caps.sql is recorded
-- as applied in supabase_migrations.schema_migrations on production, but
-- the table itself is missing — likely lost in a branch reset or restore.
-- Symptom: every render of /dashboard/configuration hits
-- /integrations/{google_ads,meta_ads}/budget-cap which calls
-- AdBudgetCapService.get_cap() → PostgREST returns PGRST205
-- "Could not find the table 'public.ad_budget_caps' in the schema cache".
--
-- This migration mirrors 20260405900000_ad_budget_caps.sql exactly, but
-- with idempotency safeguards (CREATE TABLE IF NOT EXISTS already; DROP
-- POLICY IF EXISTS / DROP TRIGGER IF EXISTS added) so it's safe to re-run
-- on environments where the table happens to exist.
--
-- Mirrors the pattern documented in memory project_admin_scheduler_jobs_paused:
-- restore migration 20260506190000 created 6 missing tables under the same
-- "log says applied, schema disagrees" failure mode.

-- moddatetime extension is referenced by the trigger below. On this prod
-- DB the extension was also missing (presumably lost in the same restore
-- that dropped the table). Idempotent.
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.ad_budget_caps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('google_ads', 'meta_ads')),
    monthly_cap DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ad_budget_caps_user_platform_unique UNIQUE (user_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_ad_budget_caps_user ON public.ad_budget_caps(user_id);

ALTER TABLE public.ad_budget_caps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ad_budget_caps_select_own" ON public.ad_budget_caps;
DROP POLICY IF EXISTS "ad_budget_caps_insert_own" ON public.ad_budget_caps;
DROP POLICY IF EXISTS "ad_budget_caps_update_own" ON public.ad_budget_caps;
DROP POLICY IF EXISTS "ad_budget_caps_delete_own" ON public.ad_budget_caps;
DROP POLICY IF EXISTS "ad_budget_caps_service_role" ON public.ad_budget_caps;

CREATE POLICY "ad_budget_caps_select_own" ON public.ad_budget_caps
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "ad_budget_caps_insert_own" ON public.ad_budget_caps
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "ad_budget_caps_update_own" ON public.ad_budget_caps
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "ad_budget_caps_delete_own" ON public.ad_budget_caps
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "ad_budget_caps_service_role" ON public.ad_budget_caps
    FOR ALL USING (auth.role() = 'service_role');

DROP TRIGGER IF EXISTS ad_budget_caps_updated_at ON public.ad_budget_caps;
-- Schema-qualified: migration runner's search_path does not include
-- `extensions`, so unqualified moddatetime() fails to resolve here even
-- though it works at runtime via the role's search_path.
CREATE TRIGGER ad_budget_caps_updated_at
    BEFORE UPDATE ON public.ad_budget_caps
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);
