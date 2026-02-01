-- Migration: 0015_add_onboarding_columns.sql
-- Description: Add persona and configuration columns to user_executive_agents table
-- Following supabase-best-practices: backward compatibility, default values

-- Add persona column to store user classification
ALTER TABLE user_executive_agents 
ADD COLUMN IF NOT EXISTS persona TEXT 
CHECK (persona IN ('solopreneur', 'startup', 'sme', 'enterprise'));

-- Add configuration column to store unified onboarding data structure
ALTER TABLE user_executive_agents 
ADD COLUMN IF NOT EXISTS configuration JSONB DEFAULT '{}'::jsonb;

-- Backfill legacy data into configuration
UPDATE user_executive_agents 
SET configuration = jsonb_build_object(
    'business_context', COALESCE(business_context, '{}'::jsonb), 
    'preferences', COALESCE(preferences, '{}'::jsonb)
)
WHERE configuration IS NULL OR configuration = '{}'::jsonb;

-- Enforce NOT NULL constraint
ALTER TABLE user_executive_agents 
ALTER COLUMN configuration SET NOT NULL;

-- Add index for persona filtering (optional performance optimization)
CREATE INDEX IF NOT EXISTS idx_user_executive_agents_persona 
ON user_executive_agents(persona);

-- Note: Existing business_context and preferences columns are preserved
-- for backward compatibility. New code should use the configuration column.
