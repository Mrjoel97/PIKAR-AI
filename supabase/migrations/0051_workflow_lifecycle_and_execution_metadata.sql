-- Migration: 0051_workflow_lifecycle_and_execution_metadata.sql
-- Description: Add template lifecycle/versioning fields and execution/step metadata fields.

-- -----------------------------------------------------------------------------
-- workflow_templates lifecycle + versioning
-- -----------------------------------------------------------------------------
ALTER TABLE workflow_templates
  ADD COLUMN IF NOT EXISTS template_key TEXT,
  ADD COLUMN IF NOT EXISTS version INTEGER,
  ADD COLUMN IF NOT EXISTS lifecycle_status TEXT,
  ADD COLUMN IF NOT EXISTS is_generated BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS personas_allowed JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS created_by UUID,
  ADD COLUMN IF NOT EXISTS published_by UUID,
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

-- Backfill existing rows.
UPDATE workflow_templates
SET
  template_key = COALESCE(template_key, lower(regexp_replace(name, '[^a-zA-Z0-9]+', '_', 'g'))),
  version = COALESCE(version, 1),
  lifecycle_status = COALESCE(lifecycle_status, 'published'),
  personas_allowed = COALESCE(personas_allowed, '[]'::jsonb),
  is_generated = COALESCE(is_generated, false);

-- Enforce constraints.
ALTER TABLE workflow_templates
  ALTER COLUMN template_key SET NOT NULL,
  ALTER COLUMN version SET NOT NULL,
  ALTER COLUMN lifecycle_status SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_templates_lifecycle_status_chk'
      AND conrelid = 'workflow_templates'::regclass
  ) THEN
    ALTER TABLE workflow_templates
      ADD CONSTRAINT workflow_templates_lifecycle_status_chk
      CHECK (lifecycle_status IN ('draft', 'published', 'archived'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_templates_template_key_version_key'
      AND conrelid = 'workflow_templates'::regclass
  ) THEN
    ALTER TABLE workflow_templates
      ADD CONSTRAINT workflow_templates_template_key_version_key
      UNIQUE (template_key, version);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_workflow_templates_template_key ON workflow_templates(template_key);
CREATE INDEX IF NOT EXISTS idx_workflow_templates_lifecycle_status ON workflow_templates(lifecycle_status);

-- -----------------------------------------------------------------------------
-- workflow_executions metadata
-- -----------------------------------------------------------------------------
ALTER TABLE workflow_executions
  ADD COLUMN IF NOT EXISTS template_version INTEGER,
  ADD COLUMN IF NOT EXISTS started_by UUID,
  ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS cancel_reason TEXT,
  ADD COLUMN IF NOT EXISTS run_source TEXT DEFAULT 'user_ui';

UPDATE workflow_executions
SET run_source = COALESCE(run_source, 'user_ui');

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_executions_run_source_chk'
      AND conrelid = 'workflow_executions'::regclass
  ) THEN
    ALTER TABLE workflow_executions
      ADD CONSTRAINT workflow_executions_run_source_chk
      CHECK (run_source IN ('user_ui', 'agent_ui', 'system'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_version ON workflow_executions(template_version);

-- -----------------------------------------------------------------------------
-- workflow_steps metadata
-- -----------------------------------------------------------------------------
ALTER TABLE workflow_steps
  ADD COLUMN IF NOT EXISTS phase_index INTEGER,
  ADD COLUMN IF NOT EXISTS step_index INTEGER,
  ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS tool_name TEXT,
  ADD COLUMN IF NOT EXISTS tool_input_hash TEXT,
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT,
  ADD COLUMN IF NOT EXISTS approval_request_id UUID;

UPDATE workflow_steps
SET attempt_count = COALESCE(attempt_count, 1);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_idempotency_key ON workflow_steps(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_tool_name ON workflow_steps(tool_name);

-- -----------------------------------------------------------------------------
-- Optional audit table for workflow template lifecycle
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflow_template_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,
  template_key TEXT NOT NULL,
  version INTEGER NOT NULL,
  action TEXT NOT NULL,
  actor_user_id UUID,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_template_audit_template_id ON workflow_template_audit(template_id);
CREATE INDEX IF NOT EXISTS idx_workflow_template_audit_template_key_version ON workflow_template_audit(template_key, version);

-- -----------------------------------------------------------------------------
-- execution audit trail
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflow_execution_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
  actor_user_id UUID,
  action TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_execution_audit_execution_id ON workflow_execution_audit(execution_id);
