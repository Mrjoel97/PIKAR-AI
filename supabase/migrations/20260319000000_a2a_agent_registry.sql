-- A2A Agent Registry
-- Stores registered external A2A agents for multi-agent orchestration.

CREATE TABLE IF NOT EXISTS a2a_agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    auth_token TEXT,  -- encrypted at rest by Supabase
    agent_card JSONB,
    capabilities JSONB DEFAULT '{}',
    skills TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    status TEXT DEFAULT 'registered' CHECK (status IN ('registered', 'active', 'unreachable', 'error', 'disabled')),
    last_health_check TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_a2a_registry_status ON a2a_agent_registry(status);
CREATE INDEX IF NOT EXISTS idx_a2a_registry_tags ON a2a_agent_registry USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_a2a_registry_skills ON a2a_agent_registry USING GIN (skills);

-- RLS
ALTER TABLE a2a_agent_registry ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages agent registry"
    ON a2a_agent_registry
    FOR ALL
    USING (auth.role() = 'service_role');
