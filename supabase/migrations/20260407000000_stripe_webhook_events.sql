-- Migration: 20260407000000_stripe_webhook_events.sql
-- Description: Idempotency ledger for Stripe webhook deliveries.
--
-- WHY THIS TABLE EXISTS (BILL-02):
-- Stripe delivers each webhook event at-least-once and will retry on any
-- non-2xx response or timeout for up to 3 days. Without dedupe, retries
-- can replay stale state over fresh state. The Next.js handler at
--   frontend/src/app/api/webhooks/stripe/route.ts
-- uses a SELECT-then-process-then-UPSERT pattern keyed on event_id:
--   1. SELECT row by event_id.
--   2. If status='processed', short-circuit (duplicate replay, no writes).
--   3. Otherwise run the handler inside try/catch.
--   4. On success: UPSERT row with status='processed' + processed_at.
--   5. On error:   UPSERT row with status='error' + error_message (Stripe
--                  will retry, and step 2 allows 'error' rows to re-process).
--
-- We do NOT store the full webhook payload — only a SHA-256 hex digest
-- (payload_hash) for privacy and size reasons (Stripe payloads can be
-- several KB). Dedupe must happen BEFORE user_id is known for events like
-- invoice.payment_failed which require a Stripe API round-trip to resolve
-- the owning user, so this ledger must be keyed purely on event_id and
-- cannot live as a column on the subscriptions table.

CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    event_id TEXT PRIMARY KEY,                    -- Stripe evt_xxx (unique across Stripe account)
    type TEXT NOT NULL,                           -- Stripe event.type (e.g. customer.subscription.updated)
    status TEXT NOT NULL
        CHECK (status IN ('processed', 'skipped', 'error')),
    payload_hash TEXT,                            -- SHA-256 hex digest of raw request body
    error_message TEXT,                           -- Truncated error string if status='error'
    user_id UUID REFERENCES auth.users(id),       -- Resolved Supabase user (nullable — some events pre-resolve)
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- When the ledger row was first written
    processed_at TIMESTAMPTZ                      -- When the handler finished (null if in-flight / unprocessed)
);

-- Debug index: "show me all recent events of type X"
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_type_received
    ON stripe_webhook_events (type, received_at DESC);

-- Ops index: "show me all recent errors"
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_status_received
    ON stripe_webhook_events (status, received_at DESC);

-- RLS — this is an internal ops table. Only the service_role webhook
-- handler may read or write. No user-facing read policy.
ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages webhook events" ON stripe_webhook_events
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
