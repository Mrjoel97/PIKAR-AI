-- Migration: 0032_fix_users_profile_rls_and_session_function.sql
-- Description: Harden users_profile RLS policies and fix get_session_at_version user_id type.

-- 1) Tighten users_profile RLS: authenticated-only, wrap auth.uid() in SELECT
ALTER POLICY "Users can view their own profile"
  ON public.users_profile
  TO authenticated
  USING (user_id = (SELECT auth.uid()));

ALTER POLICY "Users can update their own profile"
  ON public.users_profile
  TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));

ALTER POLICY "Users can insert their own profile"
  ON public.users_profile
  TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()));

-- 2) Fix get_session_at_version signature to use UUID for user_id
DROP FUNCTION IF EXISTS public.get_session_at_version(text, text, text, integer);

CREATE OR REPLACE FUNCTION public.get_session_at_version(
    p_app_name text,
    p_user_id uuid,
    p_session_id text,
    p_version integer
)
RETURNS TABLE(
    id uuid,
    event_data jsonb,
    event_index integer,
    version integer,
    operation text,
    created_at timestamp with time zone
)
LANGUAGE plpgsql
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    se.id,
    se.event_data,
    se.event_index,
    se.version,
    se.operation,
    se.created_at
  FROM session_events se
  WHERE se.app_name = p_app_name
    AND se.user_id = p_user_id
    AND se.session_id = p_session_id
    AND se.version <= p_version
    AND se.superseded_by IS NULL
    AND se.operation != 'delete'
  ORDER BY se.event_index;
END;
$function$;

GRANT EXECUTE ON FUNCTION public.get_session_at_version(text, uuid, text, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_session_at_version(text, uuid, text, integer) TO service_role;
