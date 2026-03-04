-- AGENT-MEM-06: episodic memory for decisions, approvals, and accepted workflow outcomes

CREATE TABLE IF NOT EXISTS public.memory_episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scope TEXT NOT NULL DEFAULT 'global',
    agent_id TEXT,
    episode_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    related_entity_type TEXT,
    related_entity_id TEXT,
    source_kind TEXT NOT NULL DEFAULT 'workflow',
    source_ref TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.9,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_episodes_user_id
    ON public.memory_episodes(user_id);

CREATE INDEX IF NOT EXISTS idx_memory_episodes_occurred_at
    ON public.memory_episodes(user_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_episodes_episode_type
    ON public.memory_episodes(episode_type);

CREATE INDEX IF NOT EXISTS idx_memory_episodes_related_entity
    ON public.memory_episodes(related_entity_type, related_entity_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_episodes_user_scope_source_ref
    ON public.memory_episodes(user_id, scope, source_ref);

ALTER TABLE public.memory_episodes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can CRUD their own memory episodes" ON public.memory_episodes;
CREATE POLICY "Users can CRUD their own memory episodes" ON public.memory_episodes
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.update_memory_episodes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS memory_episodes_updated_at ON public.memory_episodes;
CREATE TRIGGER memory_episodes_updated_at
    BEFORE UPDATE ON public.memory_episodes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_memory_episodes_updated_at();
