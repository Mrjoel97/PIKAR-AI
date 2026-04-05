-- Ad Budget Caps: Phase 43
-- Per-user, per-platform monthly spending caps for ad platform integrations.
-- Enforced by AdBudgetCapService before any budget-modifying operations.

-- =============================================================================
-- 1. Ad Budget Caps (monthly cap per user per ad platform)
-- =============================================================================
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

CREATE TRIGGER ad_budget_caps_updated_at
    BEFORE UPDATE ON public.ad_budget_caps
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
