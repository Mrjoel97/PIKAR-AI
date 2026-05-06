-- chat_widgets — durable storage for transient chat-generated widgets
-- (charts, image previews, etc.) that today live only in localStorage and
-- vanish on reload to a different browser/device or after cache wipe.
--
-- Distinct from workspace_items: workspace_items is for curated/durable
-- agent deliverables (bundle/deliverable refs, constrained item_type set);
-- chat_widgets stores any client-side WidgetDefinition keyed by the same
-- UUID that WidgetDisplayService.saveWidget() mints, so localStorage and
-- the table stay 1:1.
--
-- Mirror writes happen client-side as a fire-and-forget upsert after the
-- localStorage write succeeds — Supabase failures degrade to "widgets
-- still in localStorage but not synced", never blocking the UI.

CREATE TABLE IF NOT EXISTS public.chat_widgets (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    widget JSONB NOT NULL,
    is_minimized BOOLEAN NOT NULL DEFAULT FALSE,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Primary read path on session restore: list widgets for (user, session) by recency.
CREATE INDEX IF NOT EXISTS idx_chat_widgets_user_session_created
    ON public.chat_widgets (user_id, session_id, created_at DESC);

-- Pinned-widgets dashboard query — partial index keeps it small even for
-- users with thousands of session widgets.
CREATE INDEX IF NOT EXISTS idx_chat_widgets_user_pinned
    ON public.chat_widgets (user_id, created_at DESC)
    WHERE is_pinned = TRUE;

ALTER TABLE public.chat_widgets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users manage own chat widgets" ON public.chat_widgets;
CREATE POLICY "Users manage own chat widgets" ON public.chat_widgets
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access to chat_widgets" ON public.chat_widgets;
CREATE POLICY "Service role full access to chat_widgets" ON public.chat_widgets
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
