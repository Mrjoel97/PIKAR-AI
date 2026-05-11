-- Migration: 20260511130000_workflow_run_view.sql
-- Adds columns + indices for the Live Workspace Workflow View.
-- Spec: docs/superpowers/specs/2026-05-11-live-workspace-workflow-view-design.md

ALTER TABLE workflow_executions
    ADD COLUMN IF NOT EXISTS goal TEXT;
COMMENT ON COLUMN workflow_executions.goal IS
    'User-facing goal for this run (e.g. the original chat request). Populated at start.';

ALTER TABLE workflow_steps
    ADD COLUMN IF NOT EXISTS outcome_text TEXT,
    ADD COLUMN IF NOT EXISTS outcome_source TEXT
        CHECK (outcome_source IS NULL OR outcome_source IN ('tool', 'llm', 'status'));
COMMENT ON COLUMN workflow_steps.outcome_text IS
    'One-sentence human-readable summary of what the step accomplished.';
COMMENT ON COLUMN workflow_steps.outcome_source IS
    'Provenance of outcome_text: tool=returned by tool, llm=synthesized post-hoc, status=deterministic fallback.';

ALTER TABLE workspace_items
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
COMMENT ON COLUMN workspace_items.archived_at IS
    'When the item was moved off the active canvas. NULL = still active.';

CREATE INDEX IF NOT EXISTS idx_workflow_steps_outcome_pending
    ON workflow_steps (execution_id)
    WHERE status = 'completed' AND outcome_text IS NULL;

CREATE INDEX IF NOT EXISTS idx_workspace_items_active
    ON workspace_items (user_id)
    WHERE archived_at IS NULL;
