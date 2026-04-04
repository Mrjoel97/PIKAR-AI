-- Financial Integrations: Expand financial_records for Stripe sync.
--
-- Changes:
-- 1. Add external_id column for idempotent Stripe transaction imports
-- 2. Create partial UNIQUE index on external_id (WHERE NOT NULL)
-- 3. Drop old transaction_type CHECK, add expanded one with 'fee', 'payout', 'unknown'
-- 4. Add composite index on (user_id, source_type, transaction_date) for provider queries

-- 1. Add external_id column
ALTER TABLE public.financial_records
    ADD COLUMN IF NOT EXISTS external_id TEXT;

-- 2. Partial unique index for idempotent imports
CREATE UNIQUE INDEX IF NOT EXISTS idx_financial_records_external_id
    ON public.financial_records (external_id)
    WHERE external_id IS NOT NULL;

-- 3. Expand transaction_type CHECK constraint to include new Stripe types.
--    The inline CHECK from the CREATE TABLE is auto-named
--    "financial_records_transaction_type_check" by PostgreSQL.
ALTER TABLE public.financial_records
    DROP CONSTRAINT IF EXISTS financial_records_transaction_type_check;

ALTER TABLE public.financial_records
    ADD CONSTRAINT financial_records_transaction_type_check
    CHECK (transaction_type IN ('revenue', 'expense', 'refund', 'adjustment', 'fee', 'payout', 'unknown'));

-- 4. Composite index for provider-specific queries
CREATE INDEX IF NOT EXISTS idx_financial_records_source_type
    ON public.financial_records (user_id, source_type, transaction_date DESC)
    WHERE source_type IS NOT NULL;


-- ============================================================================
-- Phase 41 Plan 02: Shopify E-commerce Tables
-- ============================================================================

-- Shopify Orders
CREATE TABLE IF NOT EXISTS shopify_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
    shopify_order_id TEXT NOT NULL,
    order_number TEXT,
    email TEXT,
    financial_status TEXT,
    fulfillment_status TEXT,
    total_price NUMERIC(15,2) DEFAULT 0,
    subtotal_price NUMERIC(15,2) DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    line_items JSONB DEFAULT '[]'::jsonb,
    customer JSONB DEFAULT '{}'::jsonb,
    created_at_shopify TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, shopify_order_id)
);

ALTER TABLE shopify_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "shopify_orders_select_own"
    ON shopify_orders FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "shopify_orders_insert_own"
    ON shopify_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "shopify_orders_update_own"
    ON shopify_orders FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "shopify_orders_delete_own"
    ON shopify_orders FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "shopify_orders_service_role"
    ON shopify_orders FOR ALL
    USING (auth.role() = 'service_role');

CREATE INDEX idx_shopify_orders_user_date
    ON shopify_orders (user_id, created_at_shopify DESC);

CREATE TRIGGER set_shopify_orders_updated_at
    BEFORE UPDATE ON shopify_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- Shopify Products
CREATE TABLE IF NOT EXISTS shopify_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
    shopify_product_id TEXT NOT NULL,
    title TEXT NOT NULL,
    vendor TEXT,
    product_type TEXT,
    status TEXT,
    variants JSONB DEFAULT '[]'::jsonb,
    image_url TEXT,
    inventory_quantity INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, shopify_product_id)
);

ALTER TABLE shopify_products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "shopify_products_select_own"
    ON shopify_products FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "shopify_products_insert_own"
    ON shopify_products FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "shopify_products_update_own"
    ON shopify_products FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "shopify_products_delete_own"
    ON shopify_products FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "shopify_products_service_role"
    ON shopify_products FOR ALL
    USING (auth.role() = 'service_role');

CREATE INDEX idx_shopify_products_user_inventory
    ON shopify_products (user_id, inventory_quantity);

CREATE TRIGGER set_shopify_products_updated_at
    BEFORE UPDATE ON shopify_products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
