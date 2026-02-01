-- Migration: 0005_sessions.sql
-- Description: Create table for persistent session storage (replacing InMemorySessionService)

-- Sessions table stores conversation threads
CREATE TABLE IF NOT EXISTS sessions (
    -- Composite primary key for multi-tenant isolation
    app_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    
    -- Session state (JSON key-value store)
    state JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Primary key
    PRIMARY KEY (app_name, user_id, session_id)
);

-- Events table stores conversation history
CREATE TABLE IF NOT EXISTS session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to session
    app_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    
    -- Event data
    event_data JSONB NOT NULL,
    
    -- Ordering
    event_index INTEGER NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Composite foreign key
    CONSTRAINT fk_session FOREIGN KEY (app_name, user_id, session_id) 
        REFERENCES sessions(app_name, user_id, session_id) ON DELETE CASCADE
);

-- Enable RLS
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_events ENABLE ROW LEVEL SECURITY;

-- Service Role has full access (backend API)
DO $$ BEGIN
    CREATE POLICY "Service Role manages sessions" ON sessions
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service Role manages events" ON session_events
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_session ON session_events(app_name, user_id, session_id, event_index);

-- Function to update session timestamp on changes
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update timestamp
DROP TRIGGER IF EXISTS sessions_updated_at ON sessions;
CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_timestamp();
