-- supabase/migrations/20260508120000_agent_memory.sql
--
-- v12.0 Phase 100 — agent_memory
--
-- Per-user, per-agent structured memory facts. One row per (user_id, agent_name)
-- holds an arbitrary JSONB facts blob the agent can read/update across
-- conversations. Distinct from session_summaries (per-session conversation
-- recap) and workspace_items (curated deliverables) — this is durable
-- agent-scoped knowledge about the user.

-- moddatetime is required for the updated_at trigger below; idempotent.
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    facts JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_user_agent
    ON public.agent_memory (user_id, agent_name);

-- Auto-update updated_at on row mutation.
-- Pattern matches supabase/migrations/20260505120000_document_editor.sql.
DROP TRIGGER IF EXISTS agent_memory_updated_at ON public.agent_memory;
CREATE TRIGGER agent_memory_updated_at
    BEFORE UPDATE ON public.agent_memory
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

ALTER TABLE public.agent_memory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_memory_owner_select" ON public.agent_memory;
CREATE POLICY "agent_memory_owner_select" ON public.agent_memory
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "agent_memory_owner_insert" ON public.agent_memory;
CREATE POLICY "agent_memory_owner_insert" ON public.agent_memory
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "agent_memory_owner_update" ON public.agent_memory;
CREATE POLICY "agent_memory_owner_update" ON public.agent_memory
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "agent_memory_owner_delete" ON public.agent_memory;
CREATE POLICY "agent_memory_owner_delete" ON public.agent_memory
    FOR DELETE USING (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_memory TO authenticated;
