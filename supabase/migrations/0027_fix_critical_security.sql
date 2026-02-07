-- Migration: 0027_fix_critical_security.sql
-- Description: Enables RLS on _edge_function_config table with service-role-only policies
--              and documents the security model for session_version_history view.
-- Created: 2026-02-06
-- 
-- SECURITY FIX: The _edge_function_config table was created without RLS, exposing
-- sensitive webhook URLs and service role keys. This migration adds restrictive
-- policies allowing only the service role to access this configuration table.

-- ============================================================================
-- SECTION 1: Enable RLS on _edge_function_config Table
-- ============================================================================

ALTER TABLE _edge_function_config ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- SECTION 2: Create Service-Role-Only Policies for _edge_function_config
-- ============================================================================
-- These policies ensure only the service role (backend, edge functions) can access
-- the sensitive configuration data. Regular authenticated users and anon users
-- will receive 0 rows when querying this table.

-- SELECT Policy: Allow service role to read all configuration entries
CREATE POLICY edge_function_config_service_select
    ON _edge_function_config
    FOR SELECT
    USING ((SELECT auth.role()) = 'service_role');

-- INSERT Policy: Allow service role to create new configurations
CREATE POLICY edge_function_config_service_insert
    ON _edge_function_config
    FOR INSERT
    WITH CHECK ((SELECT auth.role()) = 'service_role');

-- UPDATE Policy: Allow service role to modify configurations
CREATE POLICY edge_function_config_service_update
    ON _edge_function_config
    FOR UPDATE
    USING ((SELECT auth.role()) = 'service_role')
    WITH CHECK ((SELECT auth.role()) = 'service_role');

-- DELETE Policy: Allow service role to remove configurations
CREATE POLICY edge_function_config_service_delete
    ON _edge_function_config
    FOR DELETE
    USING ((SELECT auth.role()) = 'service_role');

-- ============================================================================
-- SECTION 3: Document session_version_history View Security Model
-- ============================================================================
-- The session_version_history view queries session_events which already has RLS
-- enabled with user-scoped policies. The view inherits these protections - users
-- can only see their own session history.

COMMENT ON VIEW session_version_history IS 
'Aggregates session events by version. Security: Inherits RLS from session_events table - users can only see their own session history via auth.uid() = user_id policy.';

-- Optional: Create a security-aware function wrapper for explicit access control
CREATE OR REPLACE FUNCTION get_session_version_history(
    p_app_name TEXT,
    p_session_id TEXT
)
RETURNS TABLE (
    app_name TEXT,
    session_id TEXT,
    event_count BIGINT,
    first_event TIMESTAMPTZ,
    last_event TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT 
        app_name,
        session_id,
        COUNT(*) as event_count,
        MIN(created_at) as first_event,
        MAX(created_at) as last_event
    FROM session_events
    WHERE app_name = p_app_name
      AND session_id = p_session_id
      AND user_id = (SELECT auth.uid())  -- Explicit user scope check
    GROUP BY app_name, session_id;
$$;

-- Grant execute to authenticated users only
GRANT EXECUTE ON FUNCTION get_session_version_history(TEXT, TEXT) TO authenticated;

COMMENT ON FUNCTION get_session_version_history(TEXT, TEXT) IS
'Security-aware wrapper for session version history. Uses SECURITY DEFINER with explicit user_id = auth.uid() check for additional security layer.';

-- ============================================================================
-- SECTION 4: Document Performance Indexes
-- ============================================================================
-- Index already exists via PRIMARY KEY on function_name, documented for completeness

COMMENT ON CONSTRAINT _edge_function_config_pkey ON _edge_function_config IS 
'Primary key index on function_name provides O(1) lookup performance for edge function configuration retrieval.';

-- ============================================================================
-- SECTION 5: Verification Queries
-- ============================================================================
-- Run these queries to verify RLS is properly configured:

-- Verify RLS is enabled on _edge_function_config
-- Expected: rowsecurity = true
/*
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename = '_edge_function_config';
*/

-- Verify all policies exist
-- Expected: 4 policies (SELECT, INSERT, UPDATE, DELETE)
/*
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = '_edge_function_config'
ORDER BY cmd;
*/

-- Verify service role can access (run with service role key)
-- Expected: Returns configuration rows
/*
SELECT * FROM _edge_function_config;
*/

-- ============================================================================
-- SECTION 6: Testing Instructions
-- ============================================================================
/*
TEST 1: Service Role Access
- Connect with service role key (default in SQL Editor)
- Execute: SELECT * FROM _edge_function_config;
- Expected: Returns all configuration rows

TEST 2: Authenticated User Access
- Connect with authenticated user token via API
- Execute: SELECT * FROM _edge_function_config;
- Expected: Returns 0 rows (policy blocks access)

TEST 3: Anonymous Access
- Connect with anon key
- Execute: SELECT * FROM _edge_function_config;
- Expected: Returns 0 rows (policy blocks access)

TEST 4: Insert Attempt by Authenticated User
- Connect with authenticated user token
- Execute: INSERT INTO _edge_function_config (function_name, base_url) VALUES ('test', 'http://test');
- Expected: Policy violation error or row not inserted

TEST 5: View Security
- Connect with authenticated user (user A)
- Execute: SELECT * FROM session_version_history;
- Expected: Returns only user A's session history

TEST 6: Edge Function Webhook Still Works
- Trigger a notification with send_immediately flag
- Verify call_edge_function can still read from _edge_function_config
- Expected: Webhook fires successfully (function uses SECURITY DEFINER)
*/

-- ============================================================================
-- SECTION 7: Rollback Instructions
-- ============================================================================
/*
ROLLBACK (if needed):

DROP FUNCTION IF EXISTS get_session_version_history(TEXT, TEXT);
DROP POLICY IF EXISTS edge_function_config_service_select ON _edge_function_config;
DROP POLICY IF EXISTS edge_function_config_service_insert ON _edge_function_config;
DROP POLICY IF EXISTS edge_function_config_service_update ON _edge_function_config;
DROP POLICY IF EXISTS edge_function_config_service_delete ON _edge_function_config;
ALTER TABLE _edge_function_config DISABLE ROW LEVEL SECURITY;

-- Note: The COMMENT statements don't need rollback as they don't affect functionality
*/
