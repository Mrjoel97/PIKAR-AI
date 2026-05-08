-- Phase 101 (AUTH-01): Re-assert connected_accounts RLS policies idempotently.
-- Mirrors 20260415113000_harden_connected_accounts_rls.sql exactly so any
-- environment that missed the prior migration ends up in the correct state.
-- Safe to re-apply: every CREATE is preceded by DROP IF EXISTS.

ALTER TABLE public.connected_accounts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users manage own accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can view own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can insert own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can update own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can delete own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Service Role manages all" ON public.connected_accounts;

CREATE POLICY "Users can view own connected accounts"
ON public.connected_accounts
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert own connected accounts"
ON public.connected_accounts
FOR INSERT
TO authenticated
WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update own connected accounts"
ON public.connected_accounts
FOR UPDATE
TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete own connected accounts"
ON public.connected_accounts
FOR DELETE
TO authenticated
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Service Role manages all"
ON public.connected_accounts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
