-- Security Fixes

-- 1. Fix Security Definer View
ALTER VIEW public.revenue_summary SET (security_invoker = true);

-- 2. Fix Mutable Search Path in Functions
ALTER FUNCTION public.get_revenue_stats(uuid, text) SET search_path = '';
ALTER FUNCTION public.update_updated_at_column() SET search_path = '';

-- 3. Enable RLS on financial_records_test
ALTER TABLE public.financial_records_test ENABLE ROW LEVEL SECURITY;

-- Performance Fixes (RLS InitPlan)

-- agent_google_docs
ALTER POLICY "Service role can insert agent Google Docs" ON public.agent_google_docs 
WITH CHECK (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

ALTER POLICY "Users can view their own agent Google Docs" ON public.agent_google_docs 
USING ((select auth.uid()) = user_id);

-- financial_records
ALTER POLICY "Users can delete own financial records" ON public.financial_records 
USING (user_id = (select auth.uid()));

ALTER POLICY "Users can insert own financial records" ON public.financial_records 
WITH CHECK (user_id = (select auth.uid()));

ALTER POLICY "Users can update own financial records" ON public.financial_records 
USING (user_id = (select auth.uid()))
WITH CHECK (user_id = (select auth.uid()));

ALTER POLICY "Users can view own financial records" ON public.financial_records 
USING (user_id = (select auth.uid()));

-- form_submissions
ALTER POLICY "Users can view submissions to their forms" ON public.form_submissions 
USING ((select auth.uid()) = user_id);

ALTER POLICY "Service role has full access to form_submissions" ON public.form_submissions 
USING (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

-- landing_forms
ALTER POLICY "Service role has full access to landing_forms" ON public.landing_forms 
USING (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

ALTER POLICY "Users can manage their own forms" ON public.landing_forms 
USING ((select auth.uid()) = user_id);

-- landing_pages
ALTER POLICY "Service role has full access to landing_pages" ON public.landing_pages 
USING (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

ALTER POLICY "Users can create their own landing pages" ON public.landing_pages 
WITH CHECK ((select auth.uid()) = user_id);

ALTER POLICY "Users can delete their own landing pages" ON public.landing_pages 
USING ((select auth.uid()) = user_id);

ALTER POLICY "Users can update their own landing pages" ON public.landing_pages 
USING ((select auth.uid()) = user_id);

ALTER POLICY "Users can view their own landing pages" ON public.landing_pages 
USING ((select auth.uid()) = user_id);

-- media_assets
ALTER POLICY "Service role has full access to media_assets" ON public.media_assets 
USING (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

ALTER POLICY "Users can manage their own media assets" ON public.media_assets 
USING ((select auth.uid()) = user_id);

-- payment_links
ALTER POLICY "Service role has full access to payment_links" ON public.payment_links 
USING (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

ALTER POLICY "Users can manage their own payment links" ON public.payment_links 
USING ((select auth.uid()) = user_id);

-- payment_transactions
ALTER POLICY "Allow transaction inserts" ON public.payment_transactions 
WITH CHECK ((user_id = (select auth.uid())) OR (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text));

ALTER POLICY "Service role has full access to payment_transactions" ON public.payment_transactions 
USING (((select current_setting('request.jwt.claims'::text, true))::json ->> 'role'::text) = 'service_role'::text);

ALTER POLICY "Users can view their own transactions" ON public.payment_transactions 
USING ((select auth.uid()) = user_id);

-- user_configurations
ALTER POLICY "Users can delete own configurations" ON public.user_configurations 
USING ((select auth.uid()) = user_id);

ALTER POLICY "Users can insert own configurations" ON public.user_configurations 
WITH CHECK ((select auth.uid()) = user_id);

ALTER POLICY "Users can update own configurations" ON public.user_configurations 
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);

ALTER POLICY "Users can view own configurations" ON public.user_configurations 
USING ((select auth.uid()) = user_id);

-- user_reports
ALTER POLICY "Users can manage own reports" ON public.user_reports 
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);

-- vault_documents
ALTER POLICY "Users can CRUD their own vault documents" ON public.vault_documents 
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);
