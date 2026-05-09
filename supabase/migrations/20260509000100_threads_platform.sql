-- Migration: 20260509000100_threads_platform.sql
-- Description: Add 'threads' to the connected_accounts platform CHECK
-- constraint (HYGIENE-01 / Plan 108-01).
--
-- Idempotent drop-and-recreate -- mirrors 20260320000000_social_analytics_listening.sql:91-103.
-- Plan 108-02 (Pinterest) will further extend this list when it ships.

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'connected_accounts'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%platform%IN%';

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE connected_accounts DROP CONSTRAINT ' || constraint_name;
    END IF;

    ALTER TABLE connected_accounts ADD CONSTRAINT connected_accounts_platform_check
        CHECK (platform IN (
            'twitter', 'linkedin', 'facebook', 'instagram',
            'tiktok', 'youtube', 'google_search_console', 'google_analytics',
            'threads'
        ));
END $$;
