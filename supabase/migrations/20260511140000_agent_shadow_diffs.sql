-- supabase/migrations/20260511140000_agent_shadow_diffs.sql
--
-- Agent Operating Model — W3 Section B (B-Alpha-Plus)
-- Shadow-traffic divergence records: one row per shadow turn comparing a
-- primary agent variant against a candidate variant. Powers an offline
-- review of how the manifest path diverges from the legacy executive
-- path (and any future A/B comparisons we wire through the shadow
-- router).
--
-- Reads are admin/service-role only in v1; no user-facing surface yet.

CREATE TABLE IF NOT EXISTS public.agent_shadow_diffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_id TEXT NOT NULL,
    request_id UUID,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    primary_variant TEXT NOT NULL,
    candidate_variant TEXT NOT NULL,
    primary_text TEXT,
    candidate_text TEXT,
    primary_tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
    candidate_tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
    primary_artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    candidate_artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    divergence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0
        CHECK (divergence_score >= 0.0 AND divergence_score <= 1.0),
    divergence_kind TEXT NOT NULL
        CHECK (divergence_kind IN ('identical','text','tool_calls','artifacts','multiple')),
    primary_latency_ms INTEGER,
    candidate_latency_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_asd_created
    ON public.agent_shadow_diffs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_asd_agent_created
    ON public.agent_shadow_diffs (agent_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_asd_kind_created
    ON public.agent_shadow_diffs (divergence_kind, created_at DESC)
    WHERE divergence_kind <> 'identical';

ALTER TABLE public.agent_shadow_diffs ENABLE ROW LEVEL SECURITY;

-- No authenticated-user reads in v1. Service role bypasses RLS and is
-- the only writer (background fire-and-forget task in run_sse). When a
-- user-facing admin view lands, add a policy gated on a role check.
DROP POLICY IF EXISTS "agent_shadow_diffs_service_only"
    ON public.agent_shadow_diffs;
CREATE POLICY "agent_shadow_diffs_service_only"
    ON public.agent_shadow_diffs
    FOR ALL
    USING (false)
    WITH CHECK (false);
