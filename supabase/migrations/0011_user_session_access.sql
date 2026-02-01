-- Migration: 0011_user_session_access.sql
-- Description: Allow users to view their own sessions and events (Frontend History)
-- Reference: supabase-best-practices (rls-explicit-auth-check)

-- 1. Policies for SESSIONS table
-- Allow users to see their own session list
CREATE POLICY "Users can view their own sessions" ON sessions
    FOR SELECT
    USING (auth.uid()::text = user_id);

-- Optional: Allow users to delete their own sessions (cleanup)
CREATE POLICY "Users can delete their own sessions" ON sessions
    FOR DELETE
    USING (auth.uid()::text = user_id);

-- 2. Policies for SESSION_EVENTS table
-- Allow users to see events for their own sessions
CREATE POLICY "Users can view their own session events" ON session_events
    FOR SELECT
    USING (auth.uid()::text = user_id);

-- Note: We generally don't allow users to INSERT/UPDATE sessions directly.
-- That should be handled by the Backend (AI Agent) via Service Role.
