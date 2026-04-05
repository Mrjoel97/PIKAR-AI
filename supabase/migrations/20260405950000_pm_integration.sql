-- PM Integration: Phase 44
-- synced_tasks: stores PM tool tasks (Linear/Asana) mirrored into Pikar.
-- pm_status_mappings: per-user custom mapping of external workflow states to Pikar statuses.

-- =============================================================================
-- 1. synced_tasks (bidirectional task mirror for Linear and Asana)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.synced_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('linear', 'asana')),
    external_project_id TEXT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('none', 'low', 'medium', 'high', 'urgent')),
    assignee TEXT,
    labels TEXT[] DEFAULT '{}',
    external_url TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT synced_tasks_user_provider_external_unique UNIQUE (user_id, provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_synced_tasks_user ON public.synced_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_synced_tasks_user_provider ON public.synced_tasks(user_id, provider);
CREATE INDEX IF NOT EXISTS idx_synced_tasks_user_provider_status ON public.synced_tasks(user_id, provider, status);

ALTER TABLE public.synced_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "synced_tasks_select_own" ON public.synced_tasks
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "synced_tasks_insert_own" ON public.synced_tasks
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "synced_tasks_update_own" ON public.synced_tasks
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "synced_tasks_delete_own" ON public.synced_tasks
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "synced_tasks_service_role" ON public.synced_tasks
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER synced_tasks_updated_at
    BEFORE UPDATE ON public.synced_tasks
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);

-- =============================================================================
-- 2. pm_status_mappings (per-user external state → Pikar status mapping)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pm_status_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('linear', 'asana')),
    external_state_id TEXT NOT NULL,
    external_state_name TEXT NOT NULL,
    pikar_status TEXT NOT NULL CHECK (pikar_status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pm_status_mappings_user_provider_state_unique UNIQUE (user_id, provider, external_state_id)
);

CREATE INDEX IF NOT EXISTS idx_pm_status_mappings_user_provider ON public.pm_status_mappings(user_id, provider);

ALTER TABLE public.pm_status_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pm_status_mappings_select_own" ON public.pm_status_mappings
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "pm_status_mappings_insert_own" ON public.pm_status_mappings
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "pm_status_mappings_update_own" ON public.pm_status_mappings
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "pm_status_mappings_delete_own" ON public.pm_status_mappings
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "pm_status_mappings_service_role" ON public.pm_status_mappings
    FOR ALL USING (auth.role() = 'service_role');
