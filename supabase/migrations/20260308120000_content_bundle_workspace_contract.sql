-- Migration: 20260308120000_content_bundle_workspace_contract.sql
-- Description: Add normalized content bundle, deliverable, and workspace item tables.

CREATE TABLE IF NOT EXISTS public.content_bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT 'agent_media',
    title TEXT,
    prompt TEXT,
    bundle_type TEXT NOT NULL DEFAULT 'mixed' CHECK (bundle_type IN ('image', 'video', 'audio', 'mixed', 'campaign')),
    status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('draft', 'processing', 'ready', 'failed', 'archived')),
    session_id TEXT,
    workflow_execution_id UUID REFERENCES public.workflow_executions(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_bundles_user_created ON public.content_bundles(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_bundles_session ON public.content_bundles(session_id);
CREATE INDEX IF NOT EXISTS idx_content_bundles_workflow_execution ON public.content_bundles(workflow_execution_id);

ALTER TABLE public.content_bundles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own content bundles" ON public.content_bundles;
CREATE POLICY "Users can manage their own content bundles" ON public.content_bundles
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to content_bundles" ON public.content_bundles;
CREATE POLICY "Service role has full access to content_bundles" ON public.content_bundles
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE TABLE IF NOT EXISTS public.content_bundle_deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bundle_id UUID NOT NULL REFERENCES public.content_bundles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_key TEXT NOT NULL UNIQUE,
    deliverable_key TEXT NOT NULL DEFAULT 'primary',
    asset_type TEXT NOT NULL CHECK (asset_type IN ('image_spec', 'video_spec', 'design', 'image', 'video', 'audio')),
    media_asset_id UUID REFERENCES public.media_assets(id) ON DELETE SET NULL,
    title TEXT,
    prompt TEXT,
    file_url TEXT,
    thumbnail_url TEXT,
    editable_url TEXT,
    platform_profile TEXT,
    variant_label TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_bundle_deliverables_bundle ON public.content_bundle_deliverables(bundle_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_bundle_deliverables_user ON public.content_bundle_deliverables(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_bundle_deliverables_media_asset ON public.content_bundle_deliverables(media_asset_id);

ALTER TABLE public.content_bundle_deliverables ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own content bundle deliverables" ON public.content_bundle_deliverables;
CREATE POLICY "Users can manage their own content bundle deliverables" ON public.content_bundle_deliverables
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to content_bundle_deliverables" ON public.content_bundle_deliverables;
CREATE POLICY "Service role has full access to content_bundle_deliverables" ON public.content_bundle_deliverables
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE TABLE IF NOT EXISTS public.workspace_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bundle_id UUID REFERENCES public.content_bundles(id) ON DELETE CASCADE,
    deliverable_id UUID REFERENCES public.content_bundle_deliverables(id) ON DELETE CASCADE,
    source_key TEXT NOT NULL UNIQUE,
    session_id TEXT,
    workflow_execution_id UUID REFERENCES public.workflow_executions(id) ON DELETE SET NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('image', 'video', 'video_spec', 'bundle')),
    widget_type TEXT NOT NULL,
    title TEXT,
    layout_mode TEXT NOT NULL DEFAULT 'focus' CHECK (layout_mode IN ('embedded', 'focus', 'grid', 'split', 'compare')),
    widget_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_items_user_session ON public.workspace_items(user_id, session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_items_bundle ON public.workspace_items(bundle_id);
CREATE INDEX IF NOT EXISTS idx_workspace_items_workflow_execution ON public.workspace_items(workflow_execution_id);

ALTER TABLE public.workspace_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own workspace items" ON public.workspace_items;
CREATE POLICY "Users can manage their own workspace items" ON public.workspace_items
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to workspace_items" ON public.workspace_items;
CREATE POLICY "Service role has full access to workspace_items" ON public.workspace_items
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);
