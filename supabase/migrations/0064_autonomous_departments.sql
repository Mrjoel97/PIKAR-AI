-- Migration: 0064_autonomous_departments.sql
-- Description: Tables for autonomous department operations: proactive triggers,
--              decision logging, and inter-department request coordination.

-- ============================================================================
-- 1. proactive_triggers
-- ============================================================================
CREATE TABLE IF NOT EXISTS proactive_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    condition_type TEXT NOT NULL CHECK (condition_type IN ('metric_threshold', 'initiative_phase', 'time_based', 'event_count')),
    condition_config JSONB NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('launch_workflow', 'create_task', 'escalate', 'notify')),
    action_config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    cooldown_hours INT DEFAULT 24,
    max_triggers_per_day INT DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES auth.users(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_proactive_triggers_dept_enabled
    ON proactive_triggers(department_id) WHERE enabled = true;

-- RLS
ALTER TABLE proactive_triggers ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service Role manages all" ON proactive_triggers
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Trigger for updated_at (reuse existing function from 0007)
CREATE TRIGGER update_proactive_triggers_updated_at
    BEFORE UPDATE ON proactive_triggers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 2. department_decision_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS department_decision_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    cycle_timestamp TIMESTAMPTZ NOT NULL,
    decision_type TEXT NOT NULL CHECK (decision_type IN (
        'trigger_matched', 'trigger_skipped', 'workflow_launched', 'workflow_completed',
        'kpi_alert', 'escalated', 'inter_dept_request', 'no_action', 'error'
    )),
    decision_logic TEXT NOT NULL,
    input_data JSONB,
    action_taken TEXT,
    action_details JSONB,
    outcome TEXT DEFAULT 'pending' CHECK (outcome IN ('success', 'pending', 'failed', 'skipped')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_decision_logs_dept_cycle
    ON department_decision_logs(department_id, cycle_timestamp DESC);

-- RLS
ALTER TABLE department_decision_logs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service Role manages all" ON department_decision_logs
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================================
-- 3. inter_dept_requests
-- ============================================================================
CREATE TABLE IF NOT EXISTS inter_dept_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_department_id UUID NOT NULL REFERENCES departments(id),
    to_department_id UUID NOT NULL REFERENCES departments(id),
    request_type TEXT NOT NULL CHECK (request_type IN ('investigate', 'verify', 'review', 'execute')),
    context JSONB NOT NULL,
    priority INT DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    deadline TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'acknowledged', 'in_progress', 'completed', 'failed', 'expired')),
    assigned_workflow_id UUID,
    response_data JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_inter_dept_requests_to_status
    ON inter_dept_requests(to_department_id, status)
    WHERE status IN ('pending', 'in_progress');

-- RLS
ALTER TABLE inter_dept_requests ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service Role manages all" ON inter_dept_requests
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
