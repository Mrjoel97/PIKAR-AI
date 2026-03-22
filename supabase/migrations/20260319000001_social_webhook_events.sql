-- Migration: 20260319000000_social_webhook_events.sql
-- Description: Store inbound webhook events from social platforms (LinkedIn, etc.)
--              for async processing by the agent system.

CREATE TABLE IF NOT EXISTS social_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL CHECK (platform IN ('linkedin', 'twitter', 'facebook', 'instagram', 'tiktok', 'youtube')),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    linkedin_org_id TEXT,
    user_id UUID,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed', 'ignored')),
    error_message TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_social_webhook_events_platform ON social_webhook_events(platform);
CREATE INDEX IF NOT EXISTS idx_social_webhook_events_status ON social_webhook_events(status);
CREATE INDEX IF NOT EXISTS idx_social_webhook_events_user ON social_webhook_events(user_id);
CREATE INDEX IF NOT EXISTS idx_social_webhook_events_type ON social_webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_social_webhook_events_received ON social_webhook_events(received_at DESC);

-- RLS
ALTER TABLE social_webhook_events ENABLE ROW LEVEL SECURITY;

-- Service role can manage all events; users can read their own
DO $$ BEGIN
    CREATE POLICY "Service role full access" ON social_webhook_events
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMENT ON TABLE social_webhook_events IS 'Inbound webhook events from social platforms for async processing';
COMMENT ON COLUMN social_webhook_events.platform IS 'Source platform (linkedin, twitter, etc.)';
COMMENT ON COLUMN social_webhook_events.event_type IS 'Platform-specific event type string';
COMMENT ON COLUMN social_webhook_events.payload IS 'Full JSON payload from the webhook';
COMMENT ON COLUMN social_webhook_events.linkedin_org_id IS 'LinkedIn organization URN if applicable';
COMMENT ON COLUMN social_webhook_events.status IS 'Processing lifecycle: pending → processing → processed/failed/ignored';
