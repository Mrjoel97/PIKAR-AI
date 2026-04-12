-- Migration: compliance_deadlines table for tracking regulatory deadlines
-- Plan 66-01: Compliance Health Score foundation + Calendar feature (Plan 03)

-- =============================================================================
-- Table: compliance_deadlines
-- =============================================================================

CREATE TABLE IF NOT EXISTS compliance_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    recurrence TEXT DEFAULT 'none',       -- 'none', 'monthly', 'quarterly', 'annual'
    category TEXT DEFAULT 'custom',       -- 'sox', 'gdpr', 'hipaa', 'license', 'policy_review', 'custom'
    status TEXT DEFAULT 'upcoming',       -- 'upcoming', 'completed', 'overdue', 'snoozed'
    reminder_days_before INTEGER DEFAULT 14,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_deadlines_user_id ON compliance_deadlines(user_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_due_date ON compliance_deadlines(due_date);

-- =============================================================================
-- Row Level Security
-- =============================================================================

ALTER TABLE compliance_deadlines ENABLE ROW LEVEL SECURITY;

-- Users can CRUD their own deadlines
CREATE POLICY "Users can CRUD their own deadlines"
    ON compliance_deadlines
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Service-role bypass for ProactiveAlertService access
CREATE POLICY "Service role can access all deadlines"
    ON compliance_deadlines
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
