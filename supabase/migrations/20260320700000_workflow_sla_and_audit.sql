-- SLA tracking and audit trail enhancements for workflow system (Phase 4)

-- Add SLA columns to workflow_executions
DO $$ BEGIN
    ALTER TABLE workflow_executions
        ADD COLUMN IF NOT EXISTS sla_deadline TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS sla_status TEXT DEFAULT 'on_track';
EXCEPTION WHEN others THEN NULL;
END $$;

-- Add SLA columns to workflow_steps
DO $$ BEGIN
    ALTER TABLE workflow_steps
        ADD COLUMN IF NOT EXISTS sla_hours NUMERIC,
        ADD COLUMN IF NOT EXISTS sla_deadline TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS sla_status TEXT DEFAULT 'on_track',
        ADD COLUMN IF NOT EXISTS escalation TEXT DEFAULT 'notify',
        ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
EXCEPTION WHEN others THEN NULL;
END $$;

-- Add step_name to audit trail for step-level events
DO $$ BEGIN
    ALTER TABLE workflow_execution_audit
        ADD COLUMN IF NOT EXISTS step_name TEXT;
EXCEPTION WHEN others THEN NULL;
END $$;

-- Index for step-level audit queries
CREATE INDEX IF NOT EXISTS idx_audit_step
    ON workflow_execution_audit(execution_id, step_name, created_at);

-- Index for SLA status monitoring
CREATE INDEX IF NOT EXISTS idx_workflow_steps_sla
    ON workflow_steps(sla_status, sla_deadline)
    WHERE sla_deadline IS NOT NULL;
