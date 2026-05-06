-- =============================================================================
-- Admin overview performance indexes.
--
-- Hardens the GET /admin/overview path after a Cloudflare 524 was traced to
-- a fan-out of slow Supabase reads. App-side fixes (per-card 5s timeout,
-- N+1 collapsed into asyncio.gather) ship in app/routers/admin/overview.py.
-- This migration covers the storage-layer half.
--
-- Two indexes:
--
-- 1. api_health_checks (endpoint, checked_at DESC)
--    Already declared in 20260321300001_health_monitoring_index.sql, but the
--    2026-04-27 cross-project Supabase migration left several DDL migrations
--    "applied" in schema_migrations without physically creating the objects
--    (see 20260506190000_restore_admin_tables.sql for the broader pattern).
--    Re-asserted idempotently here so the live DB matches the registry.
--    Powers the per-endpoint "latest status" lookup in _system_status_card.
--
-- 2. agent_telemetry (created_at) -- BRIN
--    agent_telemetry is append-only and physically ordered by created_at, so
--    a BRIN index is roughly two orders of magnitude smaller than B-tree and
--    answers "rows in time window" in a few page reads. The existing partial
--    btree on (status, created_at) WHERE status='error' already covers the
--    errors-only count; the missing case is the total-count query for the
--    "all agents" path used by _agent_health_card / compute_error_rate.
--
-- Both statements are idempotent and safe to re-apply.
-- =============================================================================

CREATE INDEX IF NOT EXISTS api_health_checks_endpoint_checked_at
    ON public.api_health_checks (endpoint, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_telemetry_created_at_brin
    ON public.agent_telemetry USING BRIN (created_at);
