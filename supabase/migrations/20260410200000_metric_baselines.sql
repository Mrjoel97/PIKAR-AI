-- metric_baselines: rolling statistics per user per metric for anomaly detection
-- Phase 57-02: Proactive Intelligence Layer

CREATE TABLE IF NOT EXISTS metric_baselines (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    metric_key  TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Prevent duplicate daily entries per user per metric
    CONSTRAINT uq_metric_baselines_user_metric_day
        UNIQUE (user_id, metric_key, (recorded_at::date))
);

-- Fast lookups: most recent values for a user+metric pair
CREATE INDEX IF NOT EXISTS idx_metric_baselines_user_metric_time
    ON metric_baselines (user_id, metric_key, recorded_at DESC);

-- RLS: only service-role can read/write (anomaly detection is a server-side process)
ALTER TABLE metric_baselines ENABLE ROW LEVEL SECURITY;

-- Service-role bypass policy
CREATE POLICY "service_role_all"
    ON metric_baselines
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

COMMENT ON TABLE metric_baselines IS
    'Rolling metric values per user for anomaly detection baseline computation (Phase 57-02)';
