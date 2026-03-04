-- Migration: 20260302090100_create_user_memory_facts.sql
-- Description: Durable structured user memory for facts, preferences, goals, and constraints

CREATE TABLE IF NOT EXISTS user_memory_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scope TEXT NOT NULL DEFAULT 'global',
    agent_id TEXT NOT NULL DEFAULT '',
    memory_type TEXT NOT NULL DEFAULT 'fact',
    key TEXT NOT NULL,
    value_json JSONB NOT NULL DEFAULT 'null'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.90,
    source_kind TEXT NOT NULL DEFAULT 'conversation',
    source_ref TEXT,
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_user_memory_scope
        CHECK (scope IN ('global', 'agent', 'workspace', 'initiative')),
    CONSTRAINT chk_user_memory_type
        CHECK (memory_type IN ('fact', 'preference', 'goal', 'constraint')),
    CONSTRAINT chk_user_memory_confidence
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT uq_user_memory_fact_key
        UNIQUE (user_id, scope, agent_id, key)
);

CREATE INDEX IF NOT EXISTS idx_user_memory_facts_user_id
ON user_memory_facts(user_id);

CREATE INDEX IF NOT EXISTS idx_user_memory_facts_user_scope
ON user_memory_facts(user_id, scope);

CREATE INDEX IF NOT EXISTS idx_user_memory_facts_memory_type
ON user_memory_facts(memory_type);

CREATE INDEX IF NOT EXISTS idx_user_memory_facts_updated_at
ON user_memory_facts(updated_at DESC);

ALTER TABLE user_memory_facts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own memory facts" ON user_memory_facts;
CREATE POLICY "Users can view own memory facts"
ON user_memory_facts FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own memory facts" ON user_memory_facts;
CREATE POLICY "Users can insert own memory facts"
ON user_memory_facts FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own memory facts" ON user_memory_facts;
CREATE POLICY "Users can update own memory facts"
ON user_memory_facts FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own memory facts" ON user_memory_facts;
CREATE POLICY "Users can delete own memory facts"
ON user_memory_facts FOR DELETE
TO authenticated
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access to memory facts" ON user_memory_facts;
CREATE POLICY "Service role full access to memory facts"
ON user_memory_facts FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE OR REPLACE FUNCTION update_user_memory_facts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_user_memory_facts_updated_at ON user_memory_facts;
CREATE TRIGGER trigger_user_memory_facts_updated_at
    BEFORE UPDATE ON user_memory_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_user_memory_facts_updated_at();

COMMENT ON TABLE user_memory_facts IS 'Durable structured memory for user facts, preferences, goals, and constraints.';
COMMENT ON COLUMN user_memory_facts.scope IS 'Memory scope: global, agent, workspace, or initiative.';
COMMENT ON COLUMN user_memory_facts.agent_id IS 'Agent namespace for agent-scoped memory; empty string for non-agent memory.';
COMMENT ON COLUMN user_memory_facts.value_json IS 'Structured memory value stored as JSONB.';
COMMENT ON COLUMN user_memory_facts.source_kind IS 'Where the memory came from, such as conversation, file, or tool output.';
