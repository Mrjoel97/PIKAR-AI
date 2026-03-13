-- ============================================================================
-- Media Assets and Payment Links Tables
-- ============================================================================
-- Created: 2025-02-10
-- Description: Tables for media asset management and Stripe payment integration
-- ============================================================================

-- Media Assets table (for nano-banana, remotion, and Canva creations)
CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('image_spec', 'video_spec', 'design', 'image', 'video', 'audio')),
    title TEXT NOT NULL,
    description TEXT,
    file_url TEXT,
    thumbnail_url TEXT,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backfill missing media asset columns when an older table already exists
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS asset_type TEXT;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS file_url TEXT;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE media_assets
SET asset_type = CASE
    WHEN asset_type IS NOT NULL THEN asset_type
    WHEN COALESCE(file_type, '') LIKE 'video/%' THEN 'video'
    WHEN COALESCE(file_type, '') LIKE 'audio/%' THEN 'audio'
    ELSE 'image'
END
WHERE asset_type IS NULL;

UPDATE media_assets
SET title = COALESCE(NULLIF(title, ''), NULLIF(filename, ''), NULLIF(category, ''), 'Untitled media asset')
WHERE title IS NULL OR title = '';

ALTER TABLE media_assets ALTER COLUMN asset_type SET DEFAULT 'image';
ALTER TABLE media_assets ALTER COLUMN title SET DEFAULT 'Untitled media asset';
ALTER TABLE media_assets ALTER COLUMN asset_type SET NOT NULL;
ALTER TABLE media_assets ALTER COLUMN title SET NOT NULL;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'media_assets_asset_type_check') THEN
        ALTER TABLE media_assets
        ADD CONSTRAINT media_assets_asset_type_check
        CHECK (asset_type IN ('image_spec', 'video_spec', 'design', 'image', 'video', 'audio'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_media_assets_user 
ON media_assets(user_id);

CREATE INDEX IF NOT EXISTS idx_media_assets_type 
ON media_assets(asset_type);

CREATE INDEX IF NOT EXISTS idx_media_assets_created 
ON media_assets(created_at DESC);

-- Payment Links table (Stripe integration)
CREATE TABLE IF NOT EXISTS payment_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    page_id UUID REFERENCES landing_pages(id) ON DELETE SET NULL,
    stripe_payment_link_id TEXT NOT NULL,
    stripe_product_id TEXT,
    stripe_price_id TEXT,
    product_name TEXT NOT NULL,
    price_amount INTEGER NOT NULL, -- in cents
    currency TEXT DEFAULT 'usd',
    payment_link_url TEXT NOT NULL,
    is_subscription BOOLEAN DEFAULT FALSE,
    billing_interval TEXT, -- month, year, etc.
    metadata JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_links_user 
ON payment_links(user_id);

CREATE INDEX IF NOT EXISTS idx_payment_links_page 
ON payment_links(page_id);

CREATE INDEX IF NOT EXISTS idx_payment_links_stripe 
ON payment_links(stripe_payment_link_id);

-- Payment Transactions table
CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    payment_link_id UUID REFERENCES payment_links(id) ON DELETE SET NULL,
    stripe_charge_id TEXT,
    stripe_session_id TEXT,
    amount INTEGER NOT NULL, -- in cents
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded')),
    customer_email TEXT,
    customer_name TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_user 
ON payment_transactions(user_id);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_link 
ON payment_transactions(payment_link_id);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_status 
ON payment_transactions(status);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_created 
ON payment_transactions(created_at DESC);

-- ============================================================================
-- Row Level Security
-- ============================================================================

ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_transactions ENABLE ROW LEVEL SECURITY;

-- Media Assets policies
DROP POLICY IF EXISTS "Users can manage their own media assets" ON media_assets;
CREATE POLICY "Users can manage their own media assets"
ON media_assets FOR ALL
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to media_assets" ON media_assets;
CREATE POLICY "Service role has full access to media_assets"
ON media_assets FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Payment Links policies
DROP POLICY IF EXISTS "Users can manage their own payment links" ON payment_links;
CREATE POLICY "Users can manage their own payment links"
ON payment_links FOR ALL
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to payment_links" ON payment_links;
CREATE POLICY "Service role has full access to payment_links"
ON payment_links FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Payment Transactions policies
DROP POLICY IF EXISTS "Users can view their own transactions" ON payment_transactions;
CREATE POLICY "Users can view their own transactions"
ON payment_transactions FOR SELECT
USING (auth.uid() = user_id);

-- Webhooks can insert transactions
DROP POLICY IF EXISTS "Allow transaction inserts" ON payment_transactions;
CREATE POLICY "Allow transaction inserts"
ON payment_transactions FOR INSERT
WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role has full access to payment_transactions" ON payment_transactions;
CREATE POLICY "Service role has full access to payment_transactions"
ON payment_transactions FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- ============================================================================
-- Updated At Trigger for Media Assets
-- ============================================================================

CREATE OR REPLACE FUNCTION update_media_assets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_media_assets_updated_at ON media_assets;
CREATE TRIGGER trigger_media_assets_updated_at
BEFORE UPDATE ON media_assets
FOR EACH ROW
EXECUTE FUNCTION update_media_assets_updated_at();
