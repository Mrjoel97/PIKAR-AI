-- Reduce low-risk Supabase security advisor noise by:
-- 1. Adding explicit service-role policies to RLS-enabled tables that currently
--    have no policies.
-- 2. Replacing service-role policies that currently use TRUE with explicit
--    auth.role() checks.

-- ---------------------------------------------------------------------------
-- 1. Add explicit service-role policies to service-managed tables.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'admin_agent_permissions',
        'admin_audit_log',
        'admin_chat_messages',
        'admin_chat_sessions',
        'admin_config_history',
        'admin_integrations',
        'admin_role_permissions',
        'api_health_checks',
        'api_incidents',
        'content_batches',
        'freebie_downloads',
        'freebie_mentions',
        'lead_magnets',
        'newsletter_editions',
        'social_posts',
        'user_roles',
        'video_scripts'
    ]
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL THEN
            EXECUTE format(
                'DROP POLICY IF EXISTS %I ON public.%I',
                table_name || '_service_role_all',
                table_name
            );

            EXECUTE format(
                'CREATE POLICY %I ON public.%I FOR ALL TO public USING ((SELECT auth.role()) = ''service_role'') WITH CHECK ((SELECT auth.role()) = ''service_role'')',
                table_name || '_service_role_all',
                table_name
            );
        END IF;
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 2. Replace always-true service-role policies with explicit role checks.
-- ---------------------------------------------------------------------------

ALTER POLICY "Service Role manages all"
    ON public.department_decision_logs
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access on inbound_emails"
    ON public.inbound_emails
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service Role manages all"
    ON public.inter_dept_requests
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access on oauth_tokens"
    ON public.oauth_tokens
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access on post_metrics"
    ON public.post_metrics
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access on posting_log"
    ON public.posting_log
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service Role manages all"
    ON public.proactive_triggers
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access"
    ON public.social_webhook_events
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role can insert action history"
    ON public.unified_action_history
    WITH CHECK ((SELECT auth.role()) = 'service_role');
