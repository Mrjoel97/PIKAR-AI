-- Migration: 0030_create_users_profile.sql
-- Description: Create central users_profile table for user context, persona, and storage linkage.
-- Migrates data from user_executive_agents (legacy) to users_profile.

CREATE TABLE IF NOT EXISTS users_profile (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    full_name TEXT,
    persona TEXT CHECK (persona IN ('solopreneur', 'startup', 'sme', 'enterprise')),
    business_context JSONB DEFAULT '{}'::jsonb NOT NULL,
    preferences JSONB DEFAULT '{}'::jsonb NOT NULL,
    storage_bucket_id TEXT, -- e.g., 'user-content'
    storage_path_prefix TEXT, -- e.g., '{user_id}/'
    rag_knowledge_vault_id UUID, -- distinct vault ID if not using user_id default
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_profile_persona ON users_profile(persona);

-- RLS
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile" ON users_profile
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile" ON users_profile
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile" ON users_profile
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Data Migration
-- Copy existing configuration from user_executive_agents to users_profile
INSERT INTO users_profile (user_id, persona, business_context, preferences, storage_bucket_id, storage_path_prefix, created_at, updated_at)
SELECT 
    user_id,
    persona,
    COALESCE((configuration->>'business_context')::jsonb, '{}'::jsonb),
    COALESCE((configuration->>'preferences')::jsonb, '{}'::jsonb),
    'user-content', -- Default bucket
    user_id::text || '/', -- Default path prefix
    created_at,
    updated_at
FROM user_executive_agents
ON CONFLICT (user_id) DO NOTHING;

-- Note: We do NOT delete from user_executive_agents as it still holds agent_name and system_prompt_override
-- However, future persona/context updates should go to users_profile.
