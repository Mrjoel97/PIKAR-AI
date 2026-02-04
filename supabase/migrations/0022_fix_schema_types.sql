-- Migration: 0022_fix_schema_types.sql
-- Description: Fix type misalignments between database schema and application code

-- Step -2: Drop dependent views
DROP VIEW IF EXISTS session_version_history;

-- Step -1: Cleanup invalid data
DELETE FROM sessions WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
DELETE FROM session_events WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Step 0: Drop conflicting policies and constraints
DROP POLICY IF EXISTS "Users can view their own sessions" ON sessions;
DROP POLICY IF EXISTS "Users can delete their own sessions" ON sessions;
DROP POLICY IF EXISTS "Users can view their own session events" ON session_events;

ALTER TABLE session_events DROP CONSTRAINT IF EXISTS fk_session;

-- Step 1: Add missing current_version column
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS current_version INTEGER DEFAULT 1;

-- Step 2: Convert sessions.user_id to UUID
ALTER TABLE sessions ALTER COLUMN user_id TYPE UUID USING user_id::uuid;
-- Check if backing constraint exists before adding to avoid error on rerun
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sessions_user') THEN
        ALTER TABLE sessions ADD CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Step 3: Convert session_events.user_id to UUID
ALTER TABLE session_events ALTER COLUMN user_id TYPE UUID USING user_id::uuid;

-- Step 3.1: Recreate FK on session_events
ALTER TABLE session_events ADD CONSTRAINT fk_session 
    FOREIGN KEY (app_name, user_id, session_id) 
    REFERENCES sessions(app_name, user_id, session_id) 
    ON DELETE CASCADE;

-- Step 4: Add JSONB validation constraint
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'configuration_valid_structure') THEN
        ALTER TABLE user_executive_agents 
        ADD CONSTRAINT configuration_valid_structure CHECK (
            jsonb_typeof(configuration) = 'object' AND
            (configuration ? 'business_context' OR configuration = '{}'::jsonb) AND
            (configuration ? 'preferences' OR configuration = '{}'::jsonb)
        );
    END IF;
END $$;

-- Step 5: Add performance indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_updated ON sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_user_session ON session_events(user_id, session_id);

-- Step 6: Recreate policies with UUID support
CREATE POLICY "Users can view their own sessions" ON sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can delete their own sessions" ON sessions FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "Users can view their own session events" ON session_events FOR SELECT USING (auth.uid() = user_id);

-- Step 7: Recreate dependent views
CREATE OR REPLACE VIEW session_version_history AS
 SELECT app_name,
    user_id,
    session_id,
    version,
    operation,
    min(created_at) AS version_created_at,
    count(*) AS events_in_version
   FROM session_events
  WHERE superseded_by IS NULL
  GROUP BY app_name, user_id, session_id, version, operation
  ORDER BY app_name, user_id, session_id, version DESC;
