-- Migration: Teams RBAC — workspaces, workspace_members, workspace_invites
-- Phase 35, Plan 01
-- Creates the workspace data model with role-based access control.
-- Application-layer isolation: workspace_members defines who shares data;
-- existing tables (initiatives, campaigns, etc.) are NOT modified here.

-- ---------------------------------------------------------------------------
-- Helper functions
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION is_workspace_member(ws_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1 FROM workspace_members
    WHERE workspace_id = ws_id
      AND user_id = auth.uid()
  );
$$;

CREATE OR REPLACE FUNCTION get_workspace_role(ws_id UUID)
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT role FROM workspace_members
  WHERE workspace_id = ws_id
    AND user_id = auth.uid()
  LIMIT 1;
$$;

-- ---------------------------------------------------------------------------
-- workspaces
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workspaces (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL DEFAULT 'My Workspace',
    slug        TEXT        UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspaces_owner_id ON workspaces (owner_id);

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- Owner can do everything
CREATE POLICY "workspaces_owner_all"
    ON workspaces
    FOR ALL
    USING (auth.uid() = owner_id)
    WITH CHECK (auth.uid() = owner_id);

-- Workspace members can SELECT the workspace record
CREATE POLICY "workspaces_member_select"
    ON workspaces
    FOR SELECT
    USING (is_workspace_member(id));

-- ---------------------------------------------------------------------------
-- workspace_members
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workspace_members (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role            TEXT        NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace_id ON workspace_members (workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id      ON workspace_members (user_id);

ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

-- Members can SELECT all members in workspaces they belong to
CREATE POLICY "workspace_members_member_select"
    ON workspace_members
    FOR SELECT
    USING (is_workspace_member(workspace_id));

-- Only admins can INSERT new members
CREATE POLICY "workspace_members_admin_insert"
    ON workspace_members
    FOR INSERT
    WITH CHECK (get_workspace_role(workspace_id) = 'admin');

-- Only admins can UPDATE member roles
CREATE POLICY "workspace_members_admin_update"
    ON workspace_members
    FOR UPDATE
    USING  (get_workspace_role(workspace_id) = 'admin')
    WITH CHECK (get_workspace_role(workspace_id) = 'admin');

-- Only admins can DELETE members
CREATE POLICY "workspace_members_admin_delete"
    ON workspace_members
    FOR DELETE
    USING (get_workspace_role(workspace_id) = 'admin');

-- ---------------------------------------------------------------------------
-- workspace_invites
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workspace_invites (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    token           TEXT        NOT NULL UNIQUE,
    role            TEXT        NOT NULL DEFAULT 'viewer'
                                CHECK (role IN ('editor', 'viewer')),
    created_by      UUID        NOT NULL REFERENCES auth.users(id),
    expires_at      TIMESTAMPTZ NOT NULL,
    accepted_by     UUID        REFERENCES auth.users(id),
    accepted_at     TIMESTAMPTZ,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_invites_token        ON workspace_invites (token);
CREATE INDEX IF NOT EXISTS idx_workspace_invites_workspace_id ON workspace_invites (workspace_id);

ALTER TABLE workspace_invites ENABLE ROW LEVEL SECURITY;

-- Workspace admins can CRUD invites for their workspace
CREATE POLICY "workspace_invites_admin_all"
    ON workspace_invites
    FOR ALL
    USING  (get_workspace_role(workspace_id) = 'admin')
    WITH CHECK (get_workspace_role(workspace_id) = 'admin');

-- Anyone (including unauthenticated) can SELECT an invite by token
-- (needed for the accept-invite flow before the user joins)
CREATE POLICY "workspace_invites_public_select"
    ON workspace_invites
    FOR SELECT
    USING (TRUE);

-- ---------------------------------------------------------------------------
-- Auto-update updated_at for workspaces
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION _workspaces_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION _workspaces_set_updated_at();
