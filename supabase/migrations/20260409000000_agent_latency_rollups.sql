-- Migration: 20260409000000_agent_latency_rollups.sql
-- Description: Agent latency rollups for observability dashboard (Phase 51 OBS-02).
--
-- WHY THIS TABLE EXISTS:
-- The ObservabilityMetricsService uses a hybrid latency strategy:
--   - Windows <= 24h: live Python-side percentile computation from agent_telemetry
--   - Windows > 24h: query pre-computed hourly buckets from this table
--   - Windows spanning the boundary: union both sources
--
-- The rollup job (POST /admin/observability/run-rollup) is triggered every hour
-- by Cloud Scheduler. It groups the previous hour's agent_telemetry rows by
-- (agent_name, status), computes p50/p95/p99 in Python, and upserts here.
--
-- This keeps the live 24-hour dashboard fast (direct agent_telemetry query is
-- fine at solopreneur scale) while enabling 7-day and 30-day trend charts without
-- a full table scan on every dashboard load.

CREATE TABLE IF NOT EXISTS agent_latency_rollups (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'timeout')),
    bucket_start TIMESTAMPTZ NOT NULL,
    bucket_end TIMESTAMPTZ NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    p50_ms DOUBLE PRECISION,
    p95_ms DOUBLE PRECISION,
    p99_ms DOUBLE PRECISION,
    error_count INTEGER NOT NULL DEFAULT 0,
    total_duration_ms BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Unique constraint for upsert idempotency — the rollup job can be re-run
-- safely for the same hour without creating duplicate rows.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'uix_agent_latency_rollups_agent_status_bucket') THEN
        CREATE UNIQUE INDEX uix_agent_latency_rollups_agent_status_bucket
            ON agent_latency_rollups (agent_name, status, bucket_start);
    END IF;
END $$;

-- Query index for dashboard time-range queries
-- (ORDER BY bucket_start DESC, filtered by bucket_start >= <window_start>)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_agent_latency_rollups_bucket_start') THEN
        CREATE INDEX idx_agent_latency_rollups_bucket_start
            ON agent_latency_rollups (bucket_start DESC);
    END IF;
END $$;

-- RLS: service role only — this is an internal observability table.
-- Only the Cloud Scheduler rollup job (service role) may write rows.
-- Admin dashboard reads go through the admin API which uses the service client.
ALTER TABLE agent_latency_rollups ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'agent_latency_rollups' AND policyname = 'service_role_agent_latency_rollups'
    ) THEN
        CREATE POLICY service_role_agent_latency_rollups ON agent_latency_rollups
            FOR ALL USING (auth.role() = 'service_role');
    END IF;
END $$;
