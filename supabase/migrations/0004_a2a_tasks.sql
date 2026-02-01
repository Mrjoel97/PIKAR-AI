-- Migration: 0004_a2a_tasks.sql
-- Description: Create table for persistent A2A task storage

CREATE TABLE IF NOT EXISTS a2a_tasks (
    task_id TEXT PRIMARY KEY, -- A2A uses string IDs (UUIDs usually)
    task_data JSONB NOT NULL, -- Serialized Task object
    status TEXT, -- Extracted status for querying
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE a2a_tasks ENABLE ROW LEVEL SECURITY;

-- Policy: Only authenticated users can access their own tasks?
-- OR: If the server uses Service Role, it bypasses RLS.
-- For safety, we'll allow Authenticated users to CRUD.
-- Note: 'task_data' might contain sensitive info.

-- We'll assume the server (using Service Role) manages this mostly, 
-- but if we want user-specific access, we need a user_id column.
-- The A2A Task object usually has context.
-- For now, we'll rely on Service Role for the backend API.

DO $$ BEGIN
    CREATE POLICY "Service Role manages tasks" ON a2a_tasks
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_a2a_tasks_status ON a2a_tasks(status);
