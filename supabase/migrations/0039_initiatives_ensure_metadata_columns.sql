-- Ensure initiatives has phase tracking and metadata columns (idempotent).
-- Run this if you see: Could not find the 'metadata' column of 'initiatives' in the schema cache

ALTER TABLE initiatives
  ADD COLUMN IF NOT EXISTS phase TEXT DEFAULT 'ideation',
  ADD COLUMN IF NOT EXISTS phase_progress JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS template_id UUID,
  ADD COLUMN IF NOT EXISTS workflow_execution_id UUID,
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

COMMENT ON COLUMN initiatives.phase IS 'Initiative framework phase: ideation, validation, prototype, build, scale';
COMMENT ON COLUMN initiatives.phase_progress IS 'Per-phase progress JSON: {"ideation": 100, "validation": 60, ...}';
COMMENT ON COLUMN initiatives.metadata IS 'Flexible metadata: OKRs, milestones, KPIs, notes';
