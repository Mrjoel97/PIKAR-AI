-- Migration: 0031_fix_session_version_function.sql
-- Description: Fix get_next_session_version function parameter type mismatch.
--              Migration 0022 changed session_events.user_id from TEXT to UUID,
--              but this function still has TEXT parameters, causing:
--              "operator does not exist: uuid = text" (code 42883)
--              This broke the agent chat SSE stream entirely.

-- Drop the old TEXT-parameter version
DROP FUNCTION IF EXISTS public.get_next_session_version(TEXT, TEXT, TEXT);

-- Recreate with correct UUID type for p_user_id
CREATE OR REPLACE FUNCTION public.get_next_session_version(
    p_app_name TEXT,
    p_user_id UUID,
    p_session_id TEXT
)
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
    SELECT COALESCE(MAX(version), 0) + 1
    FROM session_events
    WHERE app_name = p_app_name
      AND user_id = p_user_id
      AND session_id = p_session_id;
$$;

-- Grant execute to service_role (backend uses service role key)
GRANT EXECUTE ON FUNCTION public.get_next_session_version(TEXT, UUID, TEXT) TO service_role;

COMMENT ON FUNCTION public.get_next_session_version(TEXT, UUID, TEXT) IS
'Returns the next version number for a session. Fixed in 0031 to use UUID for user_id parameter (was TEXT, causing type mismatch after 0022 migration).';
