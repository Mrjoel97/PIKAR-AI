-- Workflow Chaining: add on_complete JSONB to workflow_templates
-- Allows templates to define a follow-up workflow that auto-starts on completion.
--
-- Example on_complete value:
-- {
--   "trigger_workflow": {
--     "template_id": "uuid-here",        -- OR template_name
--     "template_name": "follow-up-wf",
--     "context_overrides": { "key": "val" },
--     "execution_name": "Chain: Follow-up"
--   }
-- }

ALTER TABLE workflow_templates
    ADD COLUMN IF NOT EXISTS on_complete JSONB DEFAULT NULL;

-- Add run_source 'workflow_chain' to workflow_executions status check
-- (run_source is a free-text field, no constraint to alter)

COMMENT ON COLUMN workflow_templates.on_complete IS
    'Optional chaining config. trigger_workflow.template_id or template_name starts a new workflow on completion.';
