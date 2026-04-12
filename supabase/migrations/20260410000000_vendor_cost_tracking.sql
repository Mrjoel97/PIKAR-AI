-- Vendor/SaaS subscription tracking for Operations Agent
-- Provides storage for OPS-03: SaaS subscription and vendor cost consolidation

CREATE TABLE IF NOT EXISTS vendor_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    -- Categories: project_management, communication, analytics, marketing,
    --   design, development, crm, accounting, storage, security, other
    monthly_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    billing_cycle TEXT NOT NULL DEFAULT 'monthly',
    -- Cycles: monthly, quarterly, annual
    annual_cost NUMERIC(10,2),
    renewal_date DATE,
    trial_end_date DATE,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    integration_provider TEXT,
    -- Links to integration_credentials.provider if applicable
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vendor_subscriptions_user
    ON vendor_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_vendor_subscriptions_trial
    ON vendor_subscriptions(trial_end_date)
    WHERE trial_end_date IS NOT NULL AND is_active = true;

ALTER TABLE vendor_subscriptions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users manage their own subscriptions"
        ON vendor_subscriptions
        USING (user_id = (SELECT auth.uid()))
        WITH CHECK (user_id = (SELECT auth.uid()));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role manages all vendor subscriptions"
        ON vendor_subscriptions
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TRIGGER update_vendor_subscriptions_updated_at
    BEFORE UPDATE ON vendor_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
