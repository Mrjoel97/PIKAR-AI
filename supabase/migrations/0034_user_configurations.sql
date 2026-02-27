-- Migration: User Configurations Table
-- Created: 2026-02-10
-- Description: Stores user-specific configuration values for MCP tools and integrations

-- ============================================================================
-- User Configurations Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    config_key TEXT NOT NULL,
    config_value TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint per user per key
    UNIQUE(user_id, config_key)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_configurations_user_id 
ON user_configurations(user_id);

CREATE INDEX IF NOT EXISTS idx_user_configurations_key 
ON user_configurations(config_key);

-- ============================================================================
-- Row Level Security
-- ============================================================================

ALTER TABLE user_configurations ENABLE ROW LEVEL SECURITY;

-- Users can only view their own configurations
CREATE POLICY "Users can view own configurations"
ON user_configurations FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Users can insert their own configurations
CREATE POLICY "Users can insert own configurations"
ON user_configurations FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Users can update their own configurations
CREATE POLICY "Users can update own configurations"
ON user_configurations FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can delete their own configurations
CREATE POLICY "Users can delete own configurations"
ON user_configurations FOR DELETE
TO authenticated
USING (auth.uid() = user_id);

-- Service role has full access
CREATE POLICY "Service role full access to configurations"
ON user_configurations FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- Auto-update timestamp trigger
-- ============================================================================

CREATE OR REPLACE FUNCTION update_user_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_configurations_updated_at
    BEFORE UPDATE ON user_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_user_configurations_updated_at();

-- ============================================================================
-- Add platform_user_id to connected_accounts if not exists
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'connected_accounts' 
        AND column_name = 'platform_user_id'
    ) THEN
        ALTER TABLE connected_accounts ADD COLUMN platform_user_id TEXT;
    END IF;
END $$;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE user_configurations IS 'Stores user-specific configuration values for MCP tools, integrations, and preferences';
COMMENT ON COLUMN user_configurations.config_key IS 'Configuration key (e.g., TAVILY_API_KEY, SENDGRID_API_KEY)';
COMMENT ON COLUMN user_configurations.config_value IS 'Configuration value (encrypted for sensitive keys)';
COMMENT ON COLUMN user_configurations.is_sensitive IS 'Whether this configuration contains sensitive data (API keys, secrets)';
