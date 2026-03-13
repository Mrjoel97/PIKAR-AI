-- Migration: 0054_fix_advisor_issues_v4.sql
-- Description: Fix security and performance issues flagged by Supabase Advisors.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'workflow_phases_have_tools'
          AND pg_get_function_identity_arguments(p.oid) = 'jsonb'
    ) THEN
        ALTER FUNCTION public.workflow_phases_have_tools(jsonb) SET search_path = public;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'financial_records_test') THEN
        ALTER TABLE public.financial_records_test ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Service role has full access to financial_records_test" ON public.financial_records_test;
        CREATE POLICY "Service role has full access to financial_records_test"
        ON public.financial_records_test
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);

        DROP POLICY IF EXISTS "Users can manage their own financial_records_test" ON public.financial_records_test;
        CREATE POLICY "Users can manage their own financial_records_test"
        ON public.financial_records_test
        FOR ALL
        TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid());
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_template_audit') THEN
        ALTER TABLE public.workflow_template_audit ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Service role has full access to workflow_template_audit" ON public.workflow_template_audit;
        CREATE POLICY "Service role has full access to workflow_template_audit"
        ON public.workflow_template_audit
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);

        DROP POLICY IF EXISTS "Users can view their own template audit logs" ON public.workflow_template_audit;
        CREATE POLICY "Users can view their own template audit logs"
        ON public.workflow_template_audit
        FOR SELECT
        TO authenticated
        USING (actor_user_id = auth.uid());
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_execution_audit') THEN
        ALTER TABLE public.workflow_execution_audit ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Service role has full access to workflow_execution_audit" ON public.workflow_execution_audit;
        CREATE POLICY "Service role has full access to workflow_execution_audit"
        ON public.workflow_execution_audit
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);

        DROP POLICY IF EXISTS "Users can view their own execution audit logs" ON public.workflow_execution_audit;
        CREATE POLICY "Users can view their own execution audit logs"
        ON public.workflow_execution_audit
        FOR SELECT
        TO authenticated
        USING (actor_user_id = auth.uid());
    END IF;
END $$;

DROP POLICY IF EXISTS "form_submissions_user_policy" ON public.form_submissions;
DROP POLICY IF EXISTS "Users can view submissions to their forms" ON public.form_submissions;

CREATE POLICY "Users can view submissions to their forms"
ON public.form_submissions
FOR SELECT
TO authenticated
USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1
    FROM public.landing_forms lf
    JOIN public.landing_pages lp ON lp.id = lf.page_id
    WHERE lf.id = form_submissions.form_id
      AND lp.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users can update submissions to their forms" ON public.form_submissions;
CREATE POLICY "Users can update submissions to their forms"
ON public.form_submissions
FOR UPDATE
TO authenticated
USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1
    FROM public.landing_forms lf
    JOIN public.landing_pages lp ON lp.id = lf.page_id
    WHERE lf.id = form_submissions.form_id
      AND lp.user_id = auth.uid()
  )
)
WITH CHECK (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1
    FROM public.landing_forms lf
    JOIN public.landing_pages lp ON lp.id = lf.page_id
    WHERE lf.id = form_submissions.form_id
      AND lp.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users can delete submissions to their forms" ON public.form_submissions;
CREATE POLICY "Users can delete submissions to their forms"
ON public.form_submissions
FOR DELETE
TO authenticated
USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1
    FROM public.landing_forms lf
    JOIN public.landing_pages lp ON lp.id = lf.page_id
    WHERE lf.id = form_submissions.form_id
      AND lp.user_id = auth.uid()
  )
);

COMMIT;
