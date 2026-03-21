-- Migration: 20260321200000_security_fixes.sql
-- Description: Security and integrity fixes for get_revenue_stats, a2a_tasks,
--              notifications, a2a_agent_registry, and moddatetime extension.

-- =============================================================================
-- Fix #37: Ensure moddatetime extension is available
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

-- =============================================================================
-- Fix #7: Add auth.uid() identity guard to get_revenue_stats
-- The original function (from 20260313103000_schema_truth_alignment) accepts an
-- arbitrary p_user_id with no caller-identity check.  Re-create it with a
-- permission gate so only the owning user can invoke it.
-- =============================================================================
CREATE OR REPLACE FUNCTION public.get_revenue_stats(
    p_user_id UUID,
    p_period TEXT DEFAULT 'current_month'
)
RETURNS TABLE (
    revenue NUMERIC,
    currency TEXT,
    transaction_count BIGINT,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_start_date TIMESTAMPTZ;
    v_end_date TIMESTAMPTZ;
BEGIN
    -- Identity guard: callers may only query their own data
    IF auth.uid() IS DISTINCT FROM p_user_id THEN
        RAISE EXCEPTION 'permission denied';
    END IF;

    CASE p_period
        WHEN 'current_month' THEN
            v_start_date := date_trunc('month', now());
            v_end_date := date_trunc('month', now()) + INTERVAL '1 month' - INTERVAL '1 second';
        WHEN 'last_month' THEN
            v_start_date := date_trunc('month', now() - INTERVAL '1 month');
            v_end_date := date_trunc('month', now()) - INTERVAL '1 second';
        WHEN 'current_quarter' THEN
            v_start_date := date_trunc('quarter', now());
            v_end_date := date_trunc('quarter', now()) + INTERVAL '3 months' - INTERVAL '1 second';
        WHEN 'current_year' THEN
            v_start_date := date_trunc('year', now());
            v_end_date := date_trunc('year', now()) + INTERVAL '1 year' - INTERVAL '1 second';
        WHEN 'all_time' THEN
            v_start_date := '1970-01-01'::timestamptz;
            v_end_date := now();
        ELSE
            v_start_date := date_trunc('month', now());
            v_end_date := date_trunc('month', now()) + INTERVAL '1 month' - INTERVAL '1 second';
    END CASE;

    RETURN QUERY
    SELECT
        COALESCE(SUM(fr.amount), 0) AS revenue,
        COALESCE(MAX(fr.currency), 'USD') AS currency,
        COUNT(*) AS transaction_count,
        v_start_date AS period_start,
        v_end_date AS period_end
    FROM public.financial_records fr
    WHERE fr.user_id = p_user_id
      AND fr.transaction_type = 'revenue'
      AND fr.transaction_date >= v_start_date
      AND fr.transaction_date <= v_end_date;
END;
$$;

-- =============================================================================
-- Fix #8: Restrict a2a_tasks to service_role only
-- The original policy (from 0004_a2a_tasks) grants access to anon/public.
-- =============================================================================
DROP POLICY IF EXISTS "Service Role manages tasks" ON a2a_tasks;
CREATE POLICY "Service Role manages tasks" ON a2a_tasks
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- =============================================================================
-- Fix #41: Add FK, GDPR cascade-delete, and DELETE policy for notifications
-- =============================================================================
DO $$ BEGIN
    ALTER TABLE notifications
        ADD CONSTRAINT notifications_user_id_fk
        FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Add DELETE policy so authenticated users can clear their own notifications
DO $$ BEGIN
    CREATE POLICY "Users can delete own notifications"
        ON notifications
        FOR DELETE TO authenticated
        USING (user_id = auth.uid());
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================================
-- Fix #38: Replace deprecated auth.role() with TO service_role in
-- a2a_agent_registry RLS policy
-- =============================================================================
DROP POLICY IF EXISTS "Service role manages agent registry" ON a2a_agent_registry;
CREATE POLICY "Service role manages agent registry" ON a2a_agent_registry
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
