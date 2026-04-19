-- Reconcile scheduled job runtime expectations with the live schema.
-- This complements the existing scheduled improvement and notification
-- migrations for production environments where they were not fully applied.

-- ============================================================================
-- 1. user_briefing_preferences compatibility for triage + briefing routes
-- ============================================================================

ALTER TABLE public.user_briefing_preferences
    ADD COLUMN IF NOT EXISTS preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS email_triage_enabled BOOLEAN NOT NULL DEFAULT false;

UPDATE public.user_briefing_preferences
SET
    preferences = jsonb_strip_nulls(
        jsonb_build_object(
            'email_digest_enabled', email_digest_enabled,
            'email_digest_frequency', email_digest_frequency,
            'email_triage_enabled', COALESCE(email_triage_enabled, email_digest_enabled, false),
            'auto_act_enabled', auto_act_enabled,
            'auto_act_daily_cap', auto_act_daily_cap,
            'auto_act_categories', COALESCE(to_jsonb(auto_act_categories), '[]'::jsonb),
            'vip_senders', COALESCE(to_jsonb(vip_senders), '[]'::jsonb),
            'ignored_senders', COALESCE(to_jsonb(ignored_senders), '[]'::jsonb),
            'timezone', timezone,
            'briefing_time', briefing_time::text
        )
    ),
    email_triage_enabled = COALESCE(email_triage_enabled, email_digest_enabled, false)
WHERE preferences = '{}'::jsonb
   OR preferences IS NULL
   OR email_triage_enabled IS DISTINCT FROM COALESCE(email_triage_enabled, email_digest_enabled, false);


-- ============================================================================
-- 2. skill_scores compatibility for newer self-improvement runtime fields
-- ============================================================================

ALTER TABLE public.skill_scores
    ADD COLUMN IF NOT EXISTS period_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS period_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMPTZ;

UPDATE public.skill_scores
SET
    evaluated_at = COALESCE(evaluated_at, created_at),
    period_start = COALESCE(period_start, created_at),
    period_end = COALESCE(period_end, created_at)
WHERE evaluated_at IS NULL
   OR period_start IS NULL
   OR period_end IS NULL;

CREATE INDEX IF NOT EXISTS idx_skill_scores_evaluated_at
    ON public.skill_scores(evaluated_at DESC);


-- ============================================================================
-- 3. improvement_actions compatibility for execution + approval flow
-- ============================================================================

ALTER TABLE public.improvement_actions
    ADD COLUMN IF NOT EXISTS executed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS result_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    ALTER TABLE public.improvement_actions
        DROP CONSTRAINT IF EXISTS improvement_actions_status_check;

    ALTER TABLE public.improvement_actions
        ADD CONSTRAINT improvement_actions_status_check
        CHECK (status IN (
            'pending',
            'applied',
            'validated',
            'reverted',
            'pending_approval',
            'declined',
            'failed'
        ));
END $$;

CREATE INDEX IF NOT EXISTS idx_improvement_actions_executed_at
    ON public.improvement_actions(executed_at DESC);
