-- Proactive Alert Log
-- Stores dispatched proactive alerts for deduplication and audit.
-- Phase 57, Plan 01: Proactive Intelligence Layer

CREATE TABLE IF NOT EXISTS proactive_alert_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    alert_key TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    dispatched_channels JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Deduplication constraint: one alert per (user_id, alert_type, alert_key)
ALTER TABLE proactive_alert_log
    ADD CONSTRAINT uq_proactive_alert_user_type_key
    UNIQUE (user_id, alert_type, alert_key);

-- Fast lookup by user + recency
CREATE INDEX IF NOT EXISTS idx_proactive_alert_log_user_created
    ON proactive_alert_log (user_id, created_at DESC);

-- RLS
ALTER TABLE proactive_alert_log ENABLE ROW LEVEL SECURITY;

-- Service-role bypass (used by ProactiveAlertService via AdminService)
CREATE POLICY "Service role full access on proactive_alert_log"
    ON proactive_alert_log
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Users can read their own alert log
CREATE POLICY "Users can read own proactive_alert_log"
    ON proactive_alert_log
    FOR SELECT
    USING (auth.uid() = user_id);

-- Prune alerts older than 90 days (to be called by a scheduled job or pg_cron)
-- NOTE: Automatic pruning via pg_cron can be added later; for now this is a
-- utility function that can be called from a scheduler endpoint.
CREATE OR REPLACE FUNCTION prune_proactive_alert_log(retention_days INT DEFAULT 90)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM proactive_alert_log
    WHERE created_at < now() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;
