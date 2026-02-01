-- Migration: 0006_notifications.sql
-- Description: Create notifications table for system alerts and user updates

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL, -- Scoped to user
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('info', 'success', 'warning', 'error', 'task_update', 'system')),
    link TEXT, -- Optional link to resource (e.g., /tasks/123)
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Metadata for extra context
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id) WHERE is_read = FALSE;

-- RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Policies
-- We assume backend uses Service Role, but if we have authenticated users:
CREATE POLICY "Users can view their own notifications" ON notifications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications" ON notifications
    FOR UPDATE USING (auth.uid() = user_id);

-- Service Role full access (always true)
DO $$ BEGIN
    CREATE POLICY "Service Role manages notifications" ON notifications
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Realtime
-- Enable realtime for this table so frontend gets updates
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
