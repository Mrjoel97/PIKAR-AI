-- Phase 65-04 (HR-06): Training assignments table for real assign_training tool.
-- Replaces degraded assign_training placeholder with real database-backed records.

CREATE TABLE IF NOT EXISTS training_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    training_name TEXT NOT NULL,
    assignee TEXT NOT NULL,
    description TEXT,
    due_date DATE,
    status TEXT DEFAULT 'assigned',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE training_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own training assignments" ON training_assignments
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_training_assignments_user_id ON training_assignments(user_id);
CREATE INDEX idx_training_assignments_assignee ON training_assignments(assignee);
