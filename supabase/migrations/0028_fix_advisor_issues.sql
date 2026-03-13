-- Migration: 0028_fix_advisor_issues.sql
-- Description: Addresses Security and Performance issues flagged by Supabase Advisors.
--              Guarded for clean local rebuilds where some advisor targets are created later.

-- ============================================================================
-- 1. Security: Set Search Path for Functions
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'toggle_edge_function_webhook'
          AND pg_get_function_identity_arguments(p.oid) = 'text, boolean'
    ) THEN
        ALTER FUNCTION public.toggle_edge_function_webhook(TEXT, BOOLEAN) SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'trigger_execute_workflow'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        ALTER FUNCTION public.trigger_execute_workflow() SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'trigger_send_notification'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        ALTER FUNCTION public.trigger_send_notification() SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'call_edge_function'
          AND pg_get_function_identity_arguments(p.oid) = 'text, jsonb, text'
    ) THEN
        ALTER FUNCTION public.call_edge_function(TEXT, JSONB, TEXT) SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'fail_ai_job'
          AND pg_get_function_identity_arguments(p.oid) = 'uuid, text'
    ) THEN
        ALTER FUNCTION public.fail_ai_job(UUID, TEXT) SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_edge_function_url'
          AND pg_get_function_identity_arguments(p.oid) = 'text, text'
    ) THEN
        ALTER FUNCTION public.update_edge_function_url(TEXT, TEXT) SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'get_next_session_version'
          AND pg_get_function_identity_arguments(p.oid) = 'text, text, text'
    ) THEN
        ALTER FUNCTION public.get_next_session_version(TEXT, TEXT, TEXT) SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'prune_session_versions'
          AND pg_get_function_identity_arguments(p.oid) = 'integer'
    ) THEN
        ALTER FUNCTION public.prune_session_versions(INT) SET search_path = public;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'complete_ai_job'
          AND pg_get_function_identity_arguments(p.oid) = 'uuid, jsonb'
    ) THEN
        ALTER FUNCTION public.complete_ai_job(UUID, JSONB) SET search_path = public;
    END IF;
END $$;

-- ============================================================================
-- 2. Security: View Security
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'session_version_history'
    ) THEN
        ALTER VIEW public.session_version_history SET (security_invoker = true);
    END IF;
END $$;

-- ============================================================================
-- 3. Performance: Indexes for Foreign Keys
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'order_items') THEN
        CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.order_items(order_id);
        CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON public.order_items(product_id);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_executions') THEN
        CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_id ON public.workflow_executions(template_id);
    END IF;
END $$;

-- ============================================================================
-- 4. Performance and Service Role Policy Fixes
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_executions') THEN
        DROP POLICY IF EXISTS "Users can manage their own executions" ON public.workflow_executions;
        CREATE POLICY "Users can manage their own executions" ON public.workflow_executions
            TO authenticated
            USING (user_id = (SELECT auth.uid()))
            WITH CHECK (user_id = (SELECT auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_steps') THEN
        DROP POLICY IF EXISTS "Users can manage their own steps" ON public.workflow_steps;
        CREATE POLICY "Users can manage their own steps" ON public.workflow_steps
            TO authenticated
            USING (EXISTS (SELECT 1 FROM workflow_executions we WHERE we.id = workflow_steps.execution_id AND we.user_id = (SELECT auth.uid())))
            WITH CHECK (EXISTS (SELECT 1 FROM workflow_executions we WHERE we.id = workflow_steps.execution_id AND we.user_id = (SELECT auth.uid())));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'spreadsheet_connections') THEN
        DROP POLICY IF EXISTS "Users can view their own spreadsheet connections" ON public.spreadsheet_connections;
        CREATE POLICY "Users can view their own spreadsheet connections" ON public.spreadsheet_connections
            FOR SELECT TO authenticated
            USING (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Users can insert their own spreadsheet connections" ON public.spreadsheet_connections;
        CREATE POLICY "Users can insert their own spreadsheet connections" ON public.spreadsheet_connections
            FOR INSERT TO authenticated
            WITH CHECK (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Users can update their own spreadsheet connections" ON public.spreadsheet_connections;
        CREATE POLICY "Users can update their own spreadsheet connections" ON public.spreadsheet_connections
            FOR UPDATE TO authenticated
            USING (user_id = (SELECT auth.uid()))
            WITH CHECK (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Users can delete their own spreadsheet connections" ON public.spreadsheet_connections;
        CREATE POLICY "Users can delete their own spreadsheet connections" ON public.spreadsheet_connections
            FOR DELETE TO authenticated
            USING (user_id = (SELECT auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'notifications') THEN
        DROP POLICY IF EXISTS "Users can view their own notifications" ON public.notifications;
        CREATE POLICY "Users can view their own notifications" ON public.notifications
            FOR SELECT TO authenticated
            USING (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Users can update their own notifications" ON public.notifications;
        CREATE POLICY "Users can update their own notifications" ON public.notifications
            FOR UPDATE TO authenticated
            USING (user_id = (SELECT auth.uid()))
            WITH CHECK (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Service Role manages notifications" ON public.notifications;
        CREATE POLICY "Service Role manages notifications" ON public.notifications
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'report_schedules') THEN
        DROP POLICY IF EXISTS "Users can view their own report schedules" ON public.report_schedules;
        CREATE POLICY "Users can view their own report schedules" ON public.report_schedules
            FOR SELECT TO authenticated
            USING (EXISTS (SELECT 1 FROM spreadsheet_connections sc WHERE sc.id = report_schedules.connection_id AND sc.user_id = (SELECT auth.uid())));

        DROP POLICY IF EXISTS "Users can insert their own report schedules" ON public.report_schedules;
        CREATE POLICY "Users can insert their own report schedules" ON public.report_schedules
            FOR INSERT TO authenticated
            WITH CHECK (EXISTS (SELECT 1 FROM spreadsheet_connections sc WHERE sc.id = report_schedules.connection_id AND sc.user_id = (SELECT auth.uid())));

        DROP POLICY IF EXISTS "Users can update their own report schedules" ON public.report_schedules;
        CREATE POLICY "Users can update their own report schedules" ON public.report_schedules
            FOR UPDATE TO authenticated
            USING (EXISTS (SELECT 1 FROM spreadsheet_connections sc WHERE sc.id = report_schedules.connection_id AND sc.user_id = (SELECT auth.uid())))
            WITH CHECK (EXISTS (SELECT 1 FROM spreadsheet_connections sc WHERE sc.id = report_schedules.connection_id AND sc.user_id = (SELECT auth.uid())));

        DROP POLICY IF EXISTS "Users can delete their own report schedules" ON public.report_schedules;
        CREATE POLICY "Users can delete their own report schedules" ON public.report_schedules
            FOR DELETE TO authenticated
            USING (EXISTS (SELECT 1 FROM spreadsheet_connections sc WHERE sc.id = report_schedules.connection_id AND sc.user_id = (SELECT auth.uid())));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'generated_reports') THEN
        DROP POLICY IF EXISTS "Users can view their own generated reports" ON public.generated_reports;
        CREATE POLICY "Users can view their own generated reports" ON public.generated_reports
            FOR SELECT TO authenticated
            USING (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Users can insert their own generated reports" ON public.generated_reports;
        CREATE POLICY "Users can insert their own generated reports" ON public.generated_reports
            FOR INSERT TO authenticated
            WITH CHECK (user_id = (SELECT auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'media_assets') THEN
        DROP POLICY IF EXISTS "Users can CRUD their own media assets" ON public.media_assets;
        CREATE POLICY "Users can CRUD their own media assets" ON public.media_assets
            TO authenticated
            USING (user_id = (SELECT auth.uid()))
            WITH CHECK (user_id = (SELECT auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'sessions') THEN
        DROP POLICY IF EXISTS "Users can view their own sessions" ON public.sessions;
        CREATE POLICY "Users can view their own sessions" ON public.sessions
            FOR SELECT TO authenticated
            USING (user_id = (SELECT auth.uid()));

        DROP POLICY IF EXISTS "Users can delete their own sessions" ON public.sessions;
        CREATE POLICY "Users can delete their own sessions" ON public.sessions
            FOR DELETE TO authenticated
            USING (user_id = (SELECT auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'session_events') THEN
        DROP POLICY IF EXISTS "Users can view their own session events" ON public.session_events;
        CREATE POLICY "Users can view their own session events" ON public.session_events
            FOR SELECT TO authenticated
            USING (user_id = (SELECT auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'connected_accounts') THEN
        DROP POLICY IF EXISTS "Service Role manages all" ON public.connected_accounts;
        CREATE POLICY "Service Role manages all" ON public.connected_accounts
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'inventory') THEN
        DROP POLICY IF EXISTS "Service Role manages all" ON public.inventory;
        CREATE POLICY "Service Role manages all" ON public.inventory
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'invoices') THEN
        DROP POLICY IF EXISTS "Service Role manages all" ON public.invoices;
        CREATE POLICY "Service Role manages all" ON public.invoices
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'order_items') THEN
        DROP POLICY IF EXISTS "Service Role manages all" ON public.order_items;
        CREATE POLICY "Service Role manages all" ON public.order_items
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'orders') THEN
        DROP POLICY IF EXISTS "Service Role manages all" ON public.orders;
        CREATE POLICY "Service Role manages all" ON public.orders
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'products') THEN
        DROP POLICY IF EXISTS "Service Role manages all" ON public.products;
        CREATE POLICY "Service Role manages all" ON public.products
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;
