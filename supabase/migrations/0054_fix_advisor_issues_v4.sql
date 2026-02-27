-- Migration: 0054_fix_advisor_issues_v4.sql
-- Description: Fix security and performance issues flagged by Supabase Advisors.

BEGIN;

-- 1. Fix mutable search_path in function
ALTER FUNCTION public.workflow_phases_have_tools(jsonb) SET search_path = public;

-- 2. Fix RLS enabled but no policy on financial_records_test
ALTER TABLE public.financial_records_test ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to financial_records_test"
ON public.financial_records_test
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Users can manage their own financial_records_test"
ON public.financial_records_test
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- 3. Fix RLS disabled in public tables
-- workflow_template_audit
ALTER TABLE public.workflow_template_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to workflow_template_audit"
ON public.workflow_template_audit
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Users can view their own template audit logs"
ON public.workflow_template_audit
FOR SELECT
TO authenticated
USING (actor_user_id = auth.uid());

-- workflow_execution_audit
ALTER TABLE public.workflow_execution_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to workflow_execution_audit"
ON public.workflow_execution_audit
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Users can view their own execution audit logs"
ON public.workflow_execution_audit
FOR SELECT
TO authenticated
USING (actor_user_id = auth.uid());

-- 4. Fix multiple permissive policies on form_submissions
-- Drop overlapping/redundant policies
DROP POLICY IF EXISTS "form_submissions_user_policy" ON public.form_submissions;
DROP POLICY IF EXISTS "Users can view submissions to their forms" ON public.form_submissions;

-- Create granular policies for authenticated users
CREATE POLICY "Users can view submissions to their forms"
ON public.form_submissions
FOR SELECT
TO authenticated
USING (
  user_id = auth.uid() 
  OR 
  form_id IN (SELECT id::text FROM landing_pages WHERE user_id = auth.uid())
);

CREATE POLICY "Users can update submissions to their forms"
ON public.form_submissions
FOR UPDATE
TO authenticated
USING (
  user_id = auth.uid() 
  OR 
  form_id IN (SELECT id::text FROM landing_pages WHERE user_id = auth.uid())
)
WITH CHECK (
  user_id = auth.uid() 
  OR 
  form_id IN (SELECT id::text FROM landing_pages WHERE user_id = auth.uid())
);

CREATE POLICY "Users can delete submissions to their forms"
ON public.form_submissions
FOR DELETE
TO authenticated
USING (
  user_id = auth.uid() 
  OR 
  form_id IN (SELECT id::text FROM landing_pages WHERE user_id = auth.uid())
);

-- Note: INSERT is handled by "Anyone can submit forms" which applies to public (including authenticated)

COMMIT;
