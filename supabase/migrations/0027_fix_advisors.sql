-- Security Fixes

CREATE OR REPLACE FUNCTION public._migration_exec_if_relation_exists(target_schema TEXT, target_name TEXT, ddl TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = target_schema
          AND c.relname = target_name
    ) THEN
        EXECUTE ddl;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public._migration_exec_if_function_exists(target_schema TEXT, target_name TEXT, identity_args TEXT, ddl TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = target_schema
          AND p.proname = target_name
          AND pg_get_function_identity_arguments(p.oid) = identity_args
    ) THEN
        EXECUTE ddl;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public._migration_exec_if_policy_exists(target_schema TEXT, target_table TEXT, target_policy TEXT, ddl TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_policy p
        JOIN pg_class c ON c.oid = p.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = target_schema
          AND c.relname = target_table
          AND p.polname = target_policy
    ) THEN
        EXECUTE ddl;
    END IF;
END;
$$;

-- 1. Fix Security Definer View
SELECT public._migration_exec_if_relation_exists(
    'public',
    'revenue_summary',
    'ALTER VIEW public.revenue_summary SET (security_invoker = true)'
);

-- 2. Fix Mutable Search Path in Functions
SELECT public._migration_exec_if_function_exists(
    'public',
    'get_revenue_stats',
    'uuid, text',
    'ALTER FUNCTION public.get_revenue_stats(uuid, text) SET search_path = '''''
);

SELECT public._migration_exec_if_function_exists(
    'public',
    'update_updated_at_column',
    '',
    'ALTER FUNCTION public.update_updated_at_column() SET search_path = '''''
);

-- 3. Enable RLS on financial_records_test
SELECT public._migration_exec_if_relation_exists(
    'public',
    'financial_records_test',
    'ALTER TABLE public.financial_records_test ENABLE ROW LEVEL SECURITY'
);

-- Performance Fixes (RLS InitPlan)
SELECT public._migration_exec_if_policy_exists(
    'public', 'agent_google_docs', 'Service role can insert agent Google Docs',
    'ALTER POLICY "Service role can insert agent Google Docs" ON public.agent_google_docs WITH CHECK (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'agent_google_docs', 'Users can view their own agent Google Docs',
    'ALTER POLICY "Users can view their own agent Google Docs" ON public.agent_google_docs USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'financial_records', 'Users can delete own financial records',
    'ALTER POLICY "Users can delete own financial records" ON public.financial_records USING (user_id = (select auth.uid()))'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'financial_records', 'Users can insert own financial records',
    'ALTER POLICY "Users can insert own financial records" ON public.financial_records WITH CHECK (user_id = (select auth.uid()))'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'financial_records', 'Users can update own financial records',
    'ALTER POLICY "Users can update own financial records" ON public.financial_records USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()))'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'financial_records', 'Users can view own financial records',
    'ALTER POLICY "Users can view own financial records" ON public.financial_records USING (user_id = (select auth.uid()))'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'form_submissions', 'Users can view submissions to their forms',
    'ALTER POLICY "Users can view submissions to their forms" ON public.form_submissions USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'form_submissions', 'Service role has full access to form_submissions',
    'ALTER POLICY "Service role has full access to form_submissions" ON public.form_submissions USING (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_forms', 'Service role has full access to landing_forms',
    'ALTER POLICY "Service role has full access to landing_forms" ON public.landing_forms USING (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_forms', 'Users can manage their own forms',
    'ALTER POLICY "Users can manage their own forms" ON public.landing_forms USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_pages', 'Service role has full access to landing_pages',
    'ALTER POLICY "Service role has full access to landing_pages" ON public.landing_pages USING (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_pages', 'Users can create their own landing pages',
    'ALTER POLICY "Users can create their own landing pages" ON public.landing_pages WITH CHECK ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_pages', 'Users can delete their own landing pages',
    'ALTER POLICY "Users can delete their own landing pages" ON public.landing_pages USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_pages', 'Users can update their own landing pages',
    'ALTER POLICY "Users can update their own landing pages" ON public.landing_pages USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'landing_pages', 'Users can view their own landing pages',
    'ALTER POLICY "Users can view their own landing pages" ON public.landing_pages USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'media_assets', 'Service role has full access to media_assets',
    'ALTER POLICY "Service role has full access to media_assets" ON public.media_assets USING (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'media_assets', 'Users can manage their own media assets',
    'ALTER POLICY "Users can manage their own media assets" ON public.media_assets USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'payment_links', 'Service role has full access to payment_links',
    'ALTER POLICY "Service role has full access to payment_links" ON public.payment_links USING (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'payment_links', 'Users can manage their own payment links',
    'ALTER POLICY "Users can manage their own payment links" ON public.payment_links USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'payment_transactions', 'Allow transaction inserts',
    'ALTER POLICY "Allow transaction inserts" ON public.payment_transactions WITH CHECK ((user_id = (select auth.uid())) OR (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text))'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'payment_transactions', 'Service role has full access to payment_transactions',
    'ALTER POLICY "Service role has full access to payment_transactions" ON public.payment_transactions USING (((select current_setting(''request.jwt.claims''::text, true))::json ->> ''role''::text) = ''service_role''::text)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'payment_transactions', 'Users can view their own transactions',
    'ALTER POLICY "Users can view their own transactions" ON public.payment_transactions USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'user_configurations', 'Users can delete own configurations',
    'ALTER POLICY "Users can delete own configurations" ON public.user_configurations USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'user_configurations', 'Users can insert own configurations',
    'ALTER POLICY "Users can insert own configurations" ON public.user_configurations WITH CHECK ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'user_configurations', 'Users can update own configurations',
    'ALTER POLICY "Users can update own configurations" ON public.user_configurations USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'user_configurations', 'Users can view own configurations',
    'ALTER POLICY "Users can view own configurations" ON public.user_configurations USING ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'user_reports', 'Users can manage own reports',
    'ALTER POLICY "Users can manage own reports" ON public.user_reports USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id)'
);

SELECT public._migration_exec_if_policy_exists(
    'public', 'vault_documents', 'Users can CRUD their own vault documents',
    'ALTER POLICY "Users can CRUD their own vault documents" ON public.vault_documents USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id)'
);

DROP FUNCTION public._migration_exec_if_policy_exists(TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION public._migration_exec_if_function_exists(TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION public._migration_exec_if_relation_exists(TEXT, TEXT, TEXT);
