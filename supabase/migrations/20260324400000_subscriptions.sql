-- Migration: 20260324400000_subscriptions.sql
-- Description: Create subscriptions table for Stripe webhook-synced subscription state.
-- The frontend reads state from this table via Supabase RLS;
-- the webhook handler writes to it using the service_role key.

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    stripe_customer_id TEXT,                  -- Stripe cus_xxx
    stripe_subscription_id TEXT,              -- Stripe sub_xxx
    tier TEXT NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'solopreneur', 'startup', 'sme', 'enterprise')),
    price_id TEXT,                            -- Stripe price_xxx
    is_active BOOLEAN NOT NULL DEFAULT false,
    will_renew BOOLEAN NOT NULL DEFAULT true,
    period_type TEXT DEFAULT 'normal'
        CHECK (period_type IN ('normal', 'trial', 'intro')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    billing_issue_at TIMESTAMPTZ,            -- Non-null = payment failed (past_due)
    last_event_type TEXT,                     -- Last webhook event type
    last_event_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);

-- RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Users can read their own subscription.
CREATE POLICY "Users can view own subscription" ON subscriptions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Only service_role (webhook handler) can write.
CREATE POLICY "Service role manages subscriptions" ON subscriptions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Auto-update updated_at.
CREATE OR REPLACE FUNCTION update_subscriptions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_subscriptions_updated_at();
