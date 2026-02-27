-- Migration: Add atomic event insertion stored procedure
-- Fixes race condition in session event indexing
-- Version: 1.0.0

-- Create function to atomically insert session event with proper versioning
-- This prevents race conditions when multiple concurrent requests try to add events

CREATE OR REPLACE FUNCTION insert_session_event(
    p_app_name TEXT,
    p_user_id UUID,
    p_session_id UUID,
    p_event_data JSONB,
    p_operation TEXT DEFAULT 'create'
)
RETURNS TABLE (
    id UUID,
    event_index INTEGER,
    version INTEGER,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_event_index INTEGER;
    v_version INTEGER;
    v_result RECORD;
BEGIN
    -- Lock the sessions row for this app/user/session combination
    -- Using FOR UPDATE prevents concurrent modifications
    UPDATE sessions
    SET updated_at = NOW()
    WHERE app_name = p_app_name
      AND user_id = p_user_id
      AND session_id = p_session_id;

    -- Get current max version and count for this session in a single query
    -- Using COALESCE to handle the case where no events exist yet
    SELECT 
        COALESCE(MAX(version), 0) + 1,
        COALESCE(COUNT(*), 0)
    INTO v_version, v_event_index
    FROM session_events
    WHERE app_name = p_app_name
      AND user_id = p_user_id
      AND session_id = p_session_id;

    -- Insert the new event with calculated index and version
    INSERT INTO session_events (
        app_name,
        user_id,
        session_id,
        event_data,
        event_index,
        version,
        operation
    )
    VALUES (
        p_app_name,
        p_user_id,
        p_session_id,
        p_event_data,
        v_event_index,
        v_version,
        p_operation
    )
    RETURNING id, event_index, version, created_at
    INTO v_result;

    -- Update the session's current version
    UPDATE sessions
    SET current_version = v_version,
        updated_at = NOW()
    WHERE app_name = p_app_name
      AND user_id = p_user_id
      AND session_id = p_session_id;

    -- Return the inserted event data
    RETURN QUERY SELECT 
        v_result.id,
        v_result.event_index,
        v_result.version,
        v_result.created_at;
END;
$$;

-- Add index on session_events for efficient version lookups
-- This improves performance of the atomic insert function
CREATE INDEX IF NOT EXISTS idx_session_events_version_lookup 
ON session_events (app_name, user_id, session_id, version DESC);

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION insert_session_event(TEXT, UUID, UUID, JSONB, TEXT) 
TO service_role;

COMMENT ON FUNCTION insert_session_event IS 
'Atomically inserts a session event with proper version and index tracking. 
Prevents race conditions in concurrent event insertion by using row-level locking.
Returns the inserted event''s id, event_index, version, and created_at timestamp.';
