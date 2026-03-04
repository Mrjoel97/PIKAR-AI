-- Migration: 20260220141554_create_insert_session_event.sql
-- Description: Create atomic function to insert session events to prevent race conditions.

-- Function to safely insert a session event by locking the parent session and calculating next index/version.
CREATE OR REPLACE FUNCTION public.insert_session_event(
    p_app_name TEXT,
    p_user_id UUID,
    p_session_id TEXT,
    p_event_data JSONB,
    p_operation TEXT -- Expected 'create' normally, reserved for future operation types
)
RETURNS TABLE (
    event_index INTEGER,
    version INTEGER
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_next_index INTEGER;
    v_next_version INTEGER;
BEGIN
    -- Lock the session row to ensure atomic generation of event_index and version
    PERFORM 1 FROM sessions 
    WHERE app_name = p_app_name 
      AND user_id = p_user_id 
      AND session_id = p_session_id 
    FOR NO KEY UPDATE;
    
    -- Calculate next indices
    SELECT COALESCE(MAX(e.event_index), -1) + 1 INTO v_next_index
    FROM session_events e
    WHERE e.app_name = p_app_name
      AND e.user_id = p_user_id
      AND e.session_id = p_session_id;
      
    SELECT COALESCE(MAX(e.version), 0) + 1 INTO v_next_version
    FROM session_events e
    WHERE e.app_name = p_app_name
      AND e.user_id = p_user_id
      AND e.session_id = p_session_id;
      
    -- Insert the new event
    INSERT INTO session_events (
        app_name, user_id, session_id, event_data, event_index, version
    ) VALUES (
        p_app_name, p_user_id, p_session_id, p_event_data, v_next_index, v_next_version
    );
    
    -- Update the session's updated_at timestamp as well, just in case the trigger didn't catch it
    UPDATE sessions
    SET updated_at = now()
    WHERE app_name = p_app_name AND user_id = p_user_id AND session_id = p_session_id;

    -- Return the values needed by the client
    RETURN QUERY SELECT v_next_index, v_next_version;
END;
$$;

-- Grant execute to service_role (backend uses service role key)
GRANT EXECUTE ON FUNCTION public.insert_session_event(TEXT, UUID, TEXT, JSONB, TEXT) TO service_role;

COMMENT ON FUNCTION public.insert_session_event(TEXT, UUID, TEXT, JSONB, TEXT) IS
'Inserts an event atomically, locking the session row to guarantee strict monotonic increase of event_index and version.';
