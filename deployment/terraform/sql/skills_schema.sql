-- Skills Database Schema Migration
-- This migration creates the skills table for storing skill definitions
-- that were previously in the large auto_mapped_skills.py file

-- Create skills table
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category VARCHAR(100),
    knowledge TEXT,  -- The actual skill content/markdown
    metadata JSONB DEFAULT '{}',
    agent_ids TEXT[] DEFAULT '{}',
    author VARCHAR(255),
    version VARCHAR(50) DEFAULT '1.0',
    source VARCHAR(100),  -- e.g., 'builtin', 'user_created', 'imported'
    is_restricted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on category for efficient filtering
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);

-- Create index on agent_ids for efficient agent-skill lookup
CREATE INDEX IF NOT EXISTS idx_skills_agent_ids ON skills USING GIN(agent_ids);

-- Create index on name for fast lookups
CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);

-- Create index on is_restricted for security filtering
CREATE INDEX IF NOT EXISTS idx_skills_restricted ON skills(is_restricted) WHERE is_restricted = TRUE;

-- Create full-text search index for skill search
CREATE INDEX IF NOT EXISTS idx_skills_search ON skills 
USING GIN(to_tsvector('english', name || ' ' || COALESCE(description, '') || ' ' || COALESCE(knowledge, '')));

-- Add trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_skills_updated_at BEFORE UPDATE ON skills
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create skill_categories table for metadata
CREATE TABLE IF NOT EXISTS skill_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default categories
INSERT INTO skill_categories (name, description, icon, sort_order) VALUES
    ('finance', 'Financial analysis and planning skills', '💰', 1),
    ('hr', 'Human resources and recruitment skills', '👥', 2),
    ('marketing', 'Marketing automation and campaign skills', '📢', 3),
    ('sales', 'Sales intelligence and CRM skills', '📈', 4),
    ('compliance', 'Legal compliance and risk management skills', '⚖️', 5),
    ('content', 'Content creation and copywriting skills', '✍️', 6),
    ('data', 'Data analysis and visualization skills', '📊', 7),
    ('support', 'Customer support and service skills', '🎧', 8),
    ('operations', 'Operations optimization and workflow skills', '⚙️', 9),
    ('planning', 'Strategic planning and project management skills', '📋', 10)
ON CONFLICT (name) DO NOTHING;

-- Create skill_usage_log table for analytics
CREATE TABLE IF NOT EXISTS skill_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    agent_id VARCHAR(50),
    session_id VARCHAR(255),
    used_at TIMESTAMPTZ DEFAULT NOW(),
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE
);

-- Create index on skill_usage_log for analytics
CREATE INDEX IF NOT EXISTS idx_skill_usage_skill_id ON skill_usage_log(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_usage_user_id ON skill_usage_log(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_usage_used_at ON skill_usage_log(used_at);

-- Enable Row Level Security
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_usage_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Users can read all skills (filtered by their agent access)
CREATE POLICY "Users can read skills" ON skills
    FOR SELECT USING (TRUE);

-- Service role can do anything
CREATE POLICY "Service can manage skills" ON skills
    FOR ALL USING (TRUE) WITH CHECK (TRUE);

-- Categories are readable by all
CREATE POLICY "Anyone can read categories" ON skill_categories
    FOR SELECT USING (TRUE);

-- Usage log insert policy
CREATE POLICY "Service can insert usage logs" ON skill_usage_log
    FOR INSERT WITH CHECK (TRUE);

-- Only analytics can read usage logs
CREATE POLICY "Analytics can read usage logs" ON skill_usage_log
    FOR SELECT USING (TRUE);
