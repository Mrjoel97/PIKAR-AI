-- Landing page P1 enhancements:
-- 1. Make form_id and user_id nullable on form_submissions (allows direct anonymous page submissions)
-- 2. RPC for listing pages with submission counts

-- Fix: allow form submissions without a form or user (direct page submissions from anonymous visitors)
ALTER TABLE form_submissions ALTER COLUMN form_id DROP NOT NULL;
ALTER TABLE form_submissions ALTER COLUMN user_id DROP NOT NULL;

-- RPC: get user's landing pages with submission counts
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
    FROM landing_pages lp
    LEFT JOIN form_submissions fs ON fs.page_id = lp.id
    WHERE lp.user_id = p_user_id
    GROUP BY lp.id
    ORDER BY lp.updated_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
