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
