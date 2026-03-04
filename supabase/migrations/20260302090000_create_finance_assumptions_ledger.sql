-- Migration: 20260302090000_create_finance_assumptions_ledger.sql
-- Description: Persist finance reporting assumptions, scenario inputs, and benchmark sets

CREATE TABLE IF NOT EXISTS finance_assumptions_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    assumption_type TEXT NOT NULL CHECK (assumption_type IN ('reporting_rule', 'scenario_assumption', 'benchmark_set')),
    assumption_key TEXT NOT NULL,
    label TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'global',
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT NOT NULL,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    effective_start TIMESTAMPTZ,
    effective_end TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_finance_assumptions_ledger_user_type
    ON finance_assumptions_ledger(user_id, assumption_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_finance_assumptions_ledger_user_scope
    ON finance_assumptions_ledger(user_id, scope, created_at DESC);

ALTER TABLE finance_assumptions_ledger ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users can view own finance assumptions" ON finance_assumptions_ledger
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Users can insert own finance assumptions" ON finance_assumptions_ledger
        FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role manages finance assumptions" ON finance_assumptions_ledger
        USING (true)
        WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
