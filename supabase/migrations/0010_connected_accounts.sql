-- Migration: 0010_connected_accounts.sql
-- Description: Store OAuth tokens for social media platform connections

CREATE TABLE IF NOT EXISTS connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('twitter', 'linkedin', 'facebook', 'instagram', 'tiktok', 'youtube')),
    platform_user_id TEXT,
    platform_username TEXT,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    connected_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
    UNIQUE(user_id, platform)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_connected_accounts_user ON connected_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_connected_accounts_platform ON connected_accounts(platform);

-- RLS
ALTER TABLE connected_accounts ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users manage own accounts" ON connected_accounts
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Trigger for updated_at (reuse existing function)
CREATE OR REPLACE FUNCTION update_connected_accounts_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_used_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_connected_accounts_timestamp
    BEFORE UPDATE ON connected_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_connected_accounts_timestamp();
