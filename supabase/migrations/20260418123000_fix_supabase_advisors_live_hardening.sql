-- Fix the highest-value live Supabase advisor findings without changing
-- end-user data access patterns.
--
-- Scope:
-- 1. Enable RLS on public webhook event tables that were exposed through PostgREST.
-- 2. Add explicit service-role policies for those system tables.
-- 3. Pin flagged functions to a fixed search_path.
-- 4. Remove a confirmed duplicate support_tickets index.
-- 5. Remove broad listing access from the public stitch-assets bucket.

-- ---------------------------------------------------------------------------
-- 1. Webhook system tables must not remain publicly exposed via PostgREST.
-- ---------------------------------------------------------------------------

ALTER TABLE IF EXISTS public.webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.webhook_deliveries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS webhook_events_service_role_all ON public.webhook_events;
CREATE POLICY webhook_events_service_role_all
    ON public.webhook_events
    FOR ALL
    TO public
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

DROP POLICY IF EXISTS webhook_deliveries_service_role_all ON public.webhook_deliveries;
CREATE POLICY webhook_deliveries_service_role_all
    ON public.webhook_deliveries
    FOR ALL
    TO public
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

-- ---------------------------------------------------------------------------
-- 2. Pin mutable function search_path values to the public schema.
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'cleanup_telemetry_data'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.cleanup_telemetry_data() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_support_tickets_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_support_tickets_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = '_governance_set_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public._governance_set_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_inbound_emails_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_inbound_emails_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'is_workspace_member'
          AND pg_get_function_identity_arguments(p.oid) = 'ws_id uuid'
    ) THEN
        EXECUTE 'ALTER FUNCTION public.is_workspace_member(uuid) SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'set_monitoring_jobs_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.set_monitoring_jobs_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_community_posts_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_community_posts_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_subscriptions_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_subscriptions_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'set_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.set_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = '_workspaces_set_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public._workspaces_set_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_email_triage_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_email_triage_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'is_admin'
          AND pg_get_function_identity_arguments(p.oid) = 'user_id_param uuid'
    ) THEN
        EXECUTE 'ALTER FUNCTION public.is_admin(uuid) SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_post_reply_count'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_post_reply_count() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'get_workspace_role'
          AND pg_get_function_identity_arguments(p.oid) = 'ws_id uuid'
    ) THEN
        EXECUTE 'ALTER FUNCTION public.get_workspace_role(uuid) SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_updated_at_column'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_updated_at_column() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_brand_profiles_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_brand_profiles_updated_at() SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'get_user_provider_refresh_token'
          AND pg_get_function_identity_arguments(p.oid) = 'p_user_id uuid'
    ) THEN
        EXECUTE 'ALTER FUNCTION public.get_user_provider_refresh_token(uuid) SET search_path = public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'update_learning_progress_updated_at'
          AND pg_get_function_identity_arguments(p.oid) = ''
    ) THEN
        EXECUTE 'ALTER FUNCTION public.update_learning_progress_updated_at() SET search_path = public';
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- 3. Remove a duplicate support_tickets index.
-- ---------------------------------------------------------------------------

DROP INDEX IF EXISTS public.idx_support_tickets_user_id_fkey;

-- ---------------------------------------------------------------------------
-- 4. Public buckets do not need a broad SELECT policy for direct object access.
-- Dropping this policy prevents bucket-wide listing through storage.objects.
-- ---------------------------------------------------------------------------

DROP POLICY IF EXISTS stitch_assets_public_read ON storage.objects;
