-- Webhook Infrastructure: inbound events, outbound endpoints, delivery log
-- Phase 39 Plan 02

-- ============================================================================
-- 1. Inbound webhook events (system-level, NO RLS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    provider text NOT NULL,
    event_id text NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'pending',
    processed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_webhook_events_provider_event UNIQUE (provider, event_id)
);

-- Index for worker queries that fetch pending events
CREATE INDEX IF NOT EXISTS idx_webhook_events_status ON webhook_events (status);

COMMENT ON TABLE webhook_events IS 'Inbound webhook events from third-party providers. Deduplicated by (provider, event_id).';

-- ============================================================================
-- 2. Outbound webhook endpoint configuration (user-scoped, RLS enabled)
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    url text NOT NULL,
    secret text NOT NULL,
    events text[] NOT NULL DEFAULT '{}',
    active boolean NOT NULL DEFAULT true,
    consecutive_failures integer NOT NULL DEFAULT 0,
    disabled_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Index for delivery worker queries
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON webhook_endpoints (active);

-- Row Level Security: users can only see their own endpoints
ALTER TABLE webhook_endpoints ENABLE ROW LEVEL SECURITY;

CREATE POLICY webhook_endpoints_select ON webhook_endpoints
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY webhook_endpoints_insert ON webhook_endpoints
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY webhook_endpoints_update ON webhook_endpoints
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY webhook_endpoints_delete ON webhook_endpoints
    FOR DELETE USING (auth.uid() = user_id);

COMMENT ON TABLE webhook_endpoints IS 'User-configured outbound webhook endpoints with HMAC signing secrets.';

-- ============================================================================
-- 3. Outbound webhook delivery log (system-level, NO RLS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    endpoint_id uuid NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    event_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'pending',
    attempts integer NOT NULL DEFAULT 0,
    next_retry_at timestamptz NOT NULL DEFAULT now(),
    response_code integer,
    response_body text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Index for delivery worker tick: fetch pending/failed deliveries due for retry
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status_retry
    ON webhook_deliveries (status, next_retry_at);

-- Index for per-endpoint delivery lookups
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint
    ON webhook_deliveries (endpoint_id);

COMMENT ON TABLE webhook_deliveries IS 'Outbound webhook delivery attempts. Retries with exponential backoff; moves to dead letter after 5 failures.';
