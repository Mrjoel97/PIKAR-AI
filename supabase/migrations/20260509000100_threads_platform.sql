-- Migration: 20260509000100_threads_platform.sql
-- Description: Add 'threads' to the connected_accounts platform CHECK
-- constraint (HYGIENE-01 / Plan 108-01).
--
-- Idempotent drop-and-recreate -- mirrors 20260320000000_social_analytics_listening.sql:91-103.
-- Plan 108-02 (Pinterest) will further extend this list when it ships.

-- 2026-05-11: Original DO block used `pg_get_constraintdef ... LIKE
-- '%platform%IN%'` to locate the existing constraint by pattern, but
-- Postgres normalizes the stored CHECK expression to `= ANY (ARRAY[...])`
-- on this database, so the LIKE didn't match. The constraint name is
-- canonical (`connected_accounts_platform_check`) — drop by name directly.
ALTER TABLE connected_accounts
    DROP CONSTRAINT IF EXISTS connected_accounts_platform_check;

ALTER TABLE connected_accounts
    ADD CONSTRAINT connected_accounts_platform_check
    CHECK (platform IN (
        'twitter', 'linkedin', 'facebook', 'instagram',
        'tiktok', 'youtube', 'google_search_console', 'google_analytics',
        'threads'
    ));
