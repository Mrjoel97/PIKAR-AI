-- ============================================================================
-- Add category classification to waitlist signups
-- Lets us segment leads by company size/type at signup time.
-- ============================================================================

ALTER TABLE public.waitlist_signups
    ADD COLUMN IF NOT EXISTS category TEXT;

-- Enum-like validation via CHECK constraint (easier to evolve than native ENUM).
-- Values are lowercase slugs; the form UI renders friendly labels.
ALTER TABLE public.waitlist_signups
    DROP CONSTRAINT IF EXISTS waitlist_signups_category_check;

ALTER TABLE public.waitlist_signups
    ADD CONSTRAINT waitlist_signups_category_check
    CHECK (category IS NULL OR category IN ('solopreneur', 'startup', 'sme', 'enterprise'));

CREATE INDEX IF NOT EXISTS idx_waitlist_signups_category
ON public.waitlist_signups (category);

COMMENT ON COLUMN public.waitlist_signups.category IS
    'Self-reported signup category: solopreneur | startup | sme | enterprise. Nullable for pre-existing rows.';
