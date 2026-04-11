-- ============================================================================
-- Phase 63-04: Add metadata JSONB to email_sequence_steps for A/B testing
-- ============================================================================
--
-- MKT-05 requires storing A/B variant linkage (ab_test_id, variant_label,
-- split_pct, is_variant) on each sequence step. The existing table has no
-- free-form metadata field, so this migration adds a nullable JSONB column
-- defaulting to an empty object. All existing rows become {} on apply.
--
-- No new indexes required -- A/B test queries filter on (sequence_id,
-- metadata->>ab_test_id) which Supabase plans will evaluate against the
-- existing sequence_id index and then filter in memory. Volumes are low
-- (one A/B test per step, two rows per test).
--
-- Scope: additive column only. No existing code reads/writes metadata on
-- email_sequence_steps today, so this is safe to apply.
-- ============================================================================

ALTER TABLE public.email_sequence_steps
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
