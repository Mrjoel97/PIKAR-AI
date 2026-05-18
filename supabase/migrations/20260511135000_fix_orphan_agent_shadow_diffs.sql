-- Migration: fix orphan agent_shadow_diffs table
-- Reason: The table existed on the remote (rbdowedrdhtlbngapexj) with a
-- different shape than the committed 20260511140000_agent_shadow_diffs.sql
-- migration expects — the migration's CREATE INDEX failed on a missing
-- created_at column.  The local schema was created out-of-band before the
-- migration was authored; no committed migration references the legacy
-- shape, so the table was never canonical.
--
-- supabase inspect db table-stats showed 0 rows on this table at the time
-- of this migration, so DROP CASCADE is safe.  After this runs, the
-- subsequent 20260511140000 migration creates the canonical schema
-- including all indexes and policies.

DROP TABLE IF EXISTS public.agent_shadow_diffs CASCADE;
