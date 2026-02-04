-- Migration: 0019_create_skills.sql
-- Description: Create table for Agent Skills.

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    content TEXT NOT NULL, -- Full markdown of the skill
    category TEXT, -- 'communication', 'technical', 'creative', etc.
    metadata JSONB DEFAULT '{}', -- Parsed frontmatter or extra tags
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_category ON skills(category);

-- RLS
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;

-- Everyone (authenticated) can view skills
CREATE POLICY "Authenticated users can view skills" ON skills
    FOR SELECT
    TO authenticated
    USING (true);

-- Only service role can manage skills (seeded from repo)
-- No INSERT/UPDATE/DELETE policies for authenticated users.
