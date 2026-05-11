-- supabase/migrations/20260511120600_persona_policies.sql
--
-- Agent Operating Model — Foundation 7/7
-- Normalized storage for per-persona policy:
--   allow/deny tool lists, action thresholds, rate limits,
--   prompt fragments, classifier default mode, blocked phases.
-- Loaded by app/agents/runtime/persona_gate.load_persona_policy.

CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.persona_policies (
    persona_id TEXT PRIMARY KEY,
    allowed_tool_ids JSONB NOT NULL DEFAULT '"*"'::jsonb,
    denied_tool_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_thresholds JSONB NOT NULL DEFAULT '{}'::jsonb,
    rate_limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt_fragments JSONB NOT NULL DEFAULT '[]'::jsonb,
    classifier_default_mode TEXT
        CHECK (classifier_default_mode IS NULL OR classifier_default_mode IN ('direct','initiative')),
    initiative_phases_blocked JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS persona_policies_updated_at ON public.persona_policies;
CREATE TRIGGER persona_policies_updated_at
    BEFORE UPDATE ON public.persona_policies
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

ALTER TABLE public.persona_policies ENABLE ROW LEVEL SECURITY;

-- Policies are server-side configuration; only service_role mutates.
-- Authenticated users may read so the front end can render policy badges.
DROP POLICY IF EXISTS "persona_policies_authenticated_read"
    ON public.persona_policies;
CREATE POLICY "persona_policies_authenticated_read"
    ON public.persona_policies
    FOR SELECT TO authenticated USING (true);

GRANT SELECT ON public.persona_policies TO authenticated;
GRANT ALL ON public.persona_policies TO service_role;
