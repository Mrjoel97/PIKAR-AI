-- Fix: Ensure transaction_type is NOT NULL in financial_records.
-- The CREATE TABLE path declares it NOT NULL, but the ADD COLUMN IF NOT EXISTS
-- path (for existing DBs) leaves it nullable. This corrective migration
-- backfills any NULL values and enforces NOT NULL.

UPDATE public.financial_records
SET transaction_type = 'unknown'
WHERE transaction_type IS NULL;

ALTER TABLE public.financial_records
    ALTER COLUMN transaction_type SET DEFAULT 'unknown',
    ALTER COLUMN transaction_type SET NOT NULL;
