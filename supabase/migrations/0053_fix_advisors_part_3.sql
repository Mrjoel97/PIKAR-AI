-- Fix Unindexed Foreign Keys
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent_id_fkey ON public.agent_knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_agent_id_fkey ON public.ai_jobs(agent_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_user_id_fkey ON public.campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_audits_user_id_fkey ON public.compliance_audits(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_risks_user_id_fkey ON public.compliance_risks(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_agent_id_fkey ON public.embeddings(agent_id);
CREATE INDEX IF NOT EXISTS idx_financial_records_user_id_fkey ON public.financial_records(user_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_user_id_fkey ON public.form_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_connection_id_fkey ON public.generated_reports(connection_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_schedule_id_fkey ON public.generated_reports(schedule_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_user_id_fkey ON public.generated_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_inventory_product_id_fkey ON public.inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_invoices_order_id_fkey ON public.invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_landing_forms_page_id_fkey ON public.landing_forms(page_id);
CREATE INDEX IF NOT EXISTS idx_landing_forms_user_id_fkey ON public.landing_forms(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_user_id_fkey ON public.mcp_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id_fkey ON public.order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id_fkey ON public.order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_payment_links_page_id_fkey ON public.payment_links(page_id);
CREATE INDEX IF NOT EXISTS idx_payment_links_user_id_fkey ON public.payment_links(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_payment_link_id_fkey ON public.payment_transactions(payment_link_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id_fkey ON public.payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_recruitment_candidates_job_id_fkey ON public.recruitment_candidates(job_id);
CREATE INDEX IF NOT EXISTS idx_recruitment_candidates_user_id_fkey ON public.recruitment_candidates(user_id);
CREATE INDEX IF NOT EXISTS idx_recruitment_jobs_user_id_fkey ON public.recruitment_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_report_schedules_connection_id_fkey ON public.report_schedules(connection_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_fkey ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id_fkey ON public.support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_id_fkey ON public.workflow_executions(template_id);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_execution_id_fkey ON public.workflow_steps(execution_id);

-- Fix Service Role Policy for payment_transactions
DROP POLICY IF EXISTS "Service role has full access to payment_transactions" ON public.payment_transactions;
CREATE POLICY "Service role has full access to payment_transactions" ON public.payment_transactions TO service_role USING (true) WITH CHECK (true);

-- Fix Landing Pages Multiple Permissive Policies by Consolidating View Access
-- Combine "Anyone can view published landing pages" and "Users can view their own landing pages"
DROP POLICY IF EXISTS "Anyone can view published landing pages" ON public.landing_pages;
DROP POLICY IF EXISTS "Users can view their own landing pages" ON public.landing_pages;

CREATE POLICY "Public view access for landing pages" ON public.landing_pages FOR SELECT TO public USING (
    (published = true) OR 
    ((select auth.uid()) = user_id)
);
