-- session_summaries — cached conversation summaries for sessions whose
-- event history exceeds SESSION_MAX_EVENTS (80) on load.
--
-- The agent's effective context window is the latest 80 events, so older
-- turns silently disappear from its view ("agent forgets after a few
-- messages"). When that boundary is crossed, the SupabaseSessionService
-- summarizes the dropped events via Gemini and prepends the summary as a
-- synthetic event so the agent retains the gist of earlier context.
--
-- Cached here so we don't pay the Gemini call on every session load —
-- regenerated only when many new events accumulate beyond the previous
-- summary point. Failures fall back to truncation-without-summary, so
-- this table is best-effort and the agent never blocks on it.

CREATE TABLE IF NOT EXISTS public.session_summaries (
    session_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    -- Event index up to which this summary covers. When new events
    -- accumulate well past this, we regenerate.
    last_summarized_event_index INTEGER NOT NULL,
    -- Total events folded into this summary (for diagnostics / regen heuristic).
    summarized_event_count INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_summaries_user_updated
    ON public.session_summaries (user_id, updated_at DESC);

ALTER TABLE public.session_summaries ENABLE ROW LEVEL SECURITY;

-- Users can read their own summaries (used by the frontend if it wants
-- to surface "Earlier in this chat: ..." UX). Writes are service-role
-- only since the backend agent owns summary generation.
DROP POLICY IF EXISTS "Users read own summaries" ON public.session_summaries;
CREATE POLICY "Users read own summaries" ON public.session_summaries
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access to session_summaries" ON public.session_summaries;
CREATE POLICY "Service role full access to session_summaries" ON public.session_summaries
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
