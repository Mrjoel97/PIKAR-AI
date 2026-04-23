-- Migration: add invited_email to workspace_invites and allow admin invite roles
-- Phase 53, Plan 01

ALTER TABLE workspace_invites
    ADD COLUMN IF NOT EXISTS invited_email TEXT;

ALTER TABLE workspace_invites
    DROP CONSTRAINT IF EXISTS workspace_invites_role_check;

ALTER TABLE workspace_invites
    ADD CONSTRAINT workspace_invites_role_check
    CHECK (role IN ('admin', 'editor', 'viewer'));
