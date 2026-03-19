-- Fix: set immutable search_path on get_user_pages_with_counts to satisfy security advisor
-- See: https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
CREATE OR REPLACE FUNCTION get_user_pages_with_counts(p_user_id UUID)
RETURNS TABLE(
    id UUID,
    title TEXT,
    slug TEXT,
    published BOOLEAN,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    metadata JSONB,
    submission_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        lp.id, lp.title, lp.slug, lp.published,
        lp.published_at, lp.created_at, lp.updated_at,
        lp.metadata,
        COALESCE(COUNT(fs.id), 0) AS submission_count
    FROM public.landing_pages lp
    LEFT JOIN public.form_submissions fs ON fs.page_id = lp.id
    WHERE lp.user_id = p_user_id
    GROUP BY lp.id
    ORDER BY lp.updated_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = '';
