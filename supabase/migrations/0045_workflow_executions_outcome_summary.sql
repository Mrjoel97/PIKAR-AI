-- Migration: 0045_workflow_executions_outcome_summary.sql
-- Add outcome_summary to workflow_executions for post-completion summary (steps, tools, summary text).

ALTER TABLE workflow_executions
  ADD COLUMN IF NOT EXISTS outcome_summary JSONB DEFAULT NULL;

COMMENT ON COLUMN workflow_executions.outcome_summary IS 'Summary when execution completed: steps_completed, tools_used, summary text for user visibility';
