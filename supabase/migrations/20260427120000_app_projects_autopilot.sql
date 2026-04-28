-- 20260427120000_app_projects_autopilot.sql
-- Adds autopilot state columns to app_projects.
-- See docs/superpowers/specs/2026-04-27-app-builder-autopilot-design.md

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_status TEXT NOT NULL DEFAULT 'idle';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'app_projects_autopilot_status_check'
    ) THEN
        ALTER TABLE app_projects
            ADD CONSTRAINT app_projects_autopilot_status_check
            CHECK (autopilot_status IN (
                'idle',
                'running',
                'paused_brief',
                'paused_variant',
                'paused_screen',
                'paused_ship',
                'failed',
                'done'
            ));
    END IF;
END $$;

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_session_id TEXT;

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_error TEXT;

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_events JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_app_projects_autopilot_status
  ON app_projects (autopilot_status)
  WHERE autopilot_status NOT IN ('idle', 'done');

COMMENT ON COLUMN app_projects.autopilot_status IS
  'Autopilot state machine state. See AppBuilderOrchestrator.';
COMMENT ON COLUMN app_projects.autopilot_session_id IS
  'Chat session that initiated autopilot — used to address narration events.';
COMMENT ON COLUMN app_projects.autopilot_error IS
  'Error message when autopilot_status=failed; nullable otherwise.';
COMMENT ON COLUMN app_projects.autopilot_events IS
  'Append-only narration log: [{ts, kind, message, payload?}, ...]';
