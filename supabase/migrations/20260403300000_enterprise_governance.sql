-- Enterprise Governance Phase 36
-- Migration: governance_audit_log, approval_chains, approval_chain_steps
-- Phase 36, Plan 01
-- Creates the governance data model: audit trail, portfolio health inputs,
-- and multi-level approval chain support.

-- ---------------------------------------------------------------------------
-- Auto-update trigger function (reused by approval_chains)
-- Create only if it doesn't already exist from the teams migration.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION _governance_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------------
-- governance_audit_log
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS governance_audit_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL,
    action_type     TEXT        NOT NULL,
    resource_type   TEXT        NOT NULL,
    resource_id     TEXT,
    details         JSONB       NOT NULL DEFAULT '{}',
    ip_address      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_governance_audit_log_user_id
    ON governance_audit_log (user_id);

CREATE INDEX IF NOT EXISTS idx_governance_audit_log_action_type
    ON governance_audit_log (action_type);

CREATE INDEX IF NOT EXISTS idx_governance_audit_log_created_at
    ON governance_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_governance_audit_log_user_created
    ON governance_audit_log (user_id, created_at DESC);

ALTER TABLE governance_audit_log ENABLE ROW LEVEL SECURITY;

-- Users can SELECT their own audit log rows
CREATE POLICY "governance_audit_log_owner_select"
    ON governance_audit_log
    FOR SELECT
    USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- approval_chains
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS approval_chains (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL,
    action_type     TEXT        NOT NULL,
    resource_id     TEXT,
    resource_label  TEXT,
    status          TEXT        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approval_chains_user_id
    ON approval_chains (user_id);

CREATE INDEX IF NOT EXISTS idx_approval_chains_status
    ON approval_chains (status);

CREATE INDEX IF NOT EXISTS idx_approval_chains_user_status
    ON approval_chains (user_id, status);

ALTER TABLE approval_chains ENABLE ROW LEVEL SECURITY;

-- Users can SELECT their own approval chains
CREATE POLICY "approval_chains_owner_select"
    ON approval_chains
    FOR SELECT
    USING (auth.uid() = user_id);

-- Auto-update updated_at on approval_chains
CREATE TRIGGER approval_chains_updated_at
    BEFORE UPDATE ON approval_chains
    FOR EACH ROW
    EXECUTE FUNCTION _governance_set_updated_at();

-- ---------------------------------------------------------------------------
-- approval_chain_steps
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS approval_chain_steps (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id            UUID        NOT NULL REFERENCES approval_chains(id) ON DELETE CASCADE,
    step_order          INTEGER     NOT NULL,
    role_label          TEXT        NOT NULL,
    approver_user_id    UUID,
    status              TEXT        NOT NULL DEFAULT 'pending'
                                    CHECK (status IN ('pending', 'approved', 'rejected', 'skipped')),
    decided_at          TIMESTAMPTZ,
    comment             TEXT,
    UNIQUE (chain_id, step_order)
);

CREATE INDEX IF NOT EXISTS idx_approval_chain_steps_chain_id
    ON approval_chain_steps (chain_id);

ALTER TABLE approval_chain_steps ENABLE ROW LEVEL SECURITY;

-- Users can SELECT steps for chains they own (join to approval_chains)
CREATE POLICY "approval_chain_steps_owner_select"
    ON approval_chain_steps
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM approval_chains
            WHERE approval_chains.id = approval_chain_steps.chain_id
              AND approval_chains.user_id = auth.uid()
        )
    );
