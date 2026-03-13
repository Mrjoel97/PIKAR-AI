-- Supabase Advisor Fixes Migration

-- 1. Security Definer View (ERROR)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'health_score_trend'
    ) THEN
        ALTER VIEW public.health_score_trend SET (security_invoker = true);
    END IF;
END $$;

-- 2. RLS Policy Always True (WARN)
DROP POLICY IF EXISTS page_analytics_insert_anon ON public.page_analytics;
CREATE POLICY page_analytics_insert_anon ON public.page_analytics
    FOR INSERT TO anon
    WITH CHECK (user_id IS NOT NULL);

-- 3. Auth RLS Initialization Plan (WARN - Performance)
DROP POLICY IF EXISTS "Users can view own briefing runs" ON public.briefing_runs;
CREATE POLICY "Users can view own briefing runs" ON public.briefing_runs
    FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- 4. Unindexed Foreign Keys (INFO - Performance)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'workflow_template_marketplace_versions'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_versions_template_id
        ON public.workflow_template_marketplace_versions(template_id);
    END IF;
END $$;

-- 5. Multiple Permissive Policies (WARN - Performance)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_template_marketplace') THEN
        DROP POLICY IF EXISTS "Users can view active workflow marketplace listings" ON public.workflow_template_marketplace;
        DROP POLICY IF EXISTS "Users can manage their own workflow marketplace listings" ON public.workflow_template_marketplace;
        DROP POLICY IF EXISTS "Users can view workflow marketplace listings" ON public.workflow_template_marketplace;
        DROP POLICY IF EXISTS "Users can insert their own workflow marketplace listings" ON public.workflow_template_marketplace;
        DROP POLICY IF EXISTS "Users can update their own workflow marketplace listings" ON public.workflow_template_marketplace;
        DROP POLICY IF EXISTS "Users can delete their own workflow marketplace listings" ON public.workflow_template_marketplace;

        CREATE POLICY "Users can view workflow marketplace listings" ON public.workflow_template_marketplace
            FOR SELECT
            USING (is_active = true OR owner_user_id = (SELECT auth.uid()));

        CREATE POLICY "Users can insert their own workflow marketplace listings" ON public.workflow_template_marketplace
            FOR INSERT TO authenticated
            WITH CHECK ((SELECT auth.uid()) = owner_user_id);

        CREATE POLICY "Users can update their own workflow marketplace listings" ON public.workflow_template_marketplace
            FOR UPDATE TO authenticated
            USING ((SELECT auth.uid()) = owner_user_id);

        CREATE POLICY "Users can delete their own workflow marketplace listings" ON public.workflow_template_marketplace
            FOR DELETE TO authenticated
            USING ((SELECT auth.uid()) = owner_user_id);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_template_marketplace_versions') THEN
        DROP POLICY IF EXISTS "Users can view active workflow marketplace listing versions" ON public.workflow_template_marketplace_versions;
        DROP POLICY IF EXISTS "Users can manage their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions;
        DROP POLICY IF EXISTS "Users can view workflow marketplace listing versions" ON public.workflow_template_marketplace_versions;
        DROP POLICY IF EXISTS "Users can insert their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions;
        DROP POLICY IF EXISTS "Users can update their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions;
        DROP POLICY IF EXISTS "Users can delete their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions;

        CREATE POLICY "Users can view workflow marketplace listing versions" ON public.workflow_template_marketplace_versions
            FOR SELECT
            USING (
              EXISTS (
                SELECT 1
                FROM workflow_template_marketplace listing
                WHERE listing.id = listing_id
                  AND (listing.is_active = true OR listing.owner_user_id = (SELECT auth.uid()))
              )
            );

        CREATE POLICY "Users can insert their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions
            FOR INSERT TO authenticated
            WITH CHECK (
              EXISTS (
                SELECT 1
                FROM workflow_template_marketplace listing
                WHERE listing.id = listing_id
                  AND listing.owner_user_id = (SELECT auth.uid())
              )
            );

        CREATE POLICY "Users can update their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions
            FOR UPDATE TO authenticated
            USING (
              EXISTS (
                SELECT 1
                FROM workflow_template_marketplace listing
                WHERE listing.id = listing_id
                  AND listing.owner_user_id = (SELECT auth.uid())
              )
            );

        CREATE POLICY "Users can delete their own workflow marketplace listing versions" ON public.workflow_template_marketplace_versions
            FOR DELETE TO authenticated
            USING (
              EXISTS (
                SELECT 1
                FROM workflow_template_marketplace listing
                WHERE listing.id = listing_id
                  AND listing.owner_user_id = (SELECT auth.uid())
              )
            );
    END IF;

    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'workflow_template_marketplace_reviews') THEN
        DROP POLICY IF EXISTS "Users can view workflow marketplace reviews" ON public.workflow_template_marketplace_reviews;
        DROP POLICY IF EXISTS "Users can manage their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews;
        DROP POLICY IF EXISTS "Users can view workflow marketplace reviews_select" ON public.workflow_template_marketplace_reviews;
        DROP POLICY IF EXISTS "Users can insert their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews;
        DROP POLICY IF EXISTS "Users can update their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews;
        DROP POLICY IF EXISTS "Users can delete their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews;

        CREATE POLICY "Users can view workflow marketplace reviews_select" ON public.workflow_template_marketplace_reviews
            FOR SELECT
            USING (true);

        CREATE POLICY "Users can insert their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews
            FOR INSERT TO authenticated
            WITH CHECK ((SELECT auth.uid()) = user_id);

        CREATE POLICY "Users can update their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews
            FOR UPDATE TO authenticated
            USING ((SELECT auth.uid()) = user_id);

        CREATE POLICY "Users can delete their own workflow marketplace reviews" ON public.workflow_template_marketplace_reviews
            FOR DELETE TO authenticated
            USING ((SELECT auth.uid()) = user_id);
    END IF;
END $$;
