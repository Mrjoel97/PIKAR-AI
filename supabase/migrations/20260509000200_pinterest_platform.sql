-- Migration: 20260509000200_pinterest_platform.sql
-- Description: Add 'pinterest' (and 'threads' for safety) to the
--              connected_accounts platform CHECK constraint (HYGIENE-02).
--
-- Sequencing: this migration runs AFTER 20260509000100_threads_platform.sql
-- (Plan 108-01). The plan originally called for timestamp 20260509000100,
-- but that slot was taken by 108-01's Threads migration when both plans
-- shipped concurrently in wave 1; bumped to ...000200 so Pinterest runs
-- AFTER Threads and the canonical end-state IN list (this file's) wins.
--
-- The IN list includes BOTH 'threads' and 'pinterest' so that even if a
-- future ops re-run replays only this migration on a fresh DB the constraint
-- stays consistent with what 108-01 established.

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
            'twitter','linkedin','facebook','instagram','tiktok','youtube',
            'google_search_console','google_analytics','threads','pinterest'
        ));
END $$;
