-- Brain Dump Sessions — tracks voice brainstorming session lifecycle
-- Spec: docs/superpowers/specs/2026-03-17-braindump-voice-session-enhancements-design.md

CREATE TABLE braindump_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    session_type TEXT DEFAULT 'voice' CHECK (session_type IN ('voice')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'timed_out', 'abandoned')),
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    turn_count INTEGER DEFAULT 0,
    transcript_doc_id UUID REFERENCES vault_documents(id) ON DELETE SET NULL,
    analysis_doc_id UUID REFERENCES vault_documents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_braindump_sessions_user_id ON braindump_sessions(user_id);
CREATE INDEX idx_braindump_sessions_status ON braindump_sessions(status);

ALTER TABLE braindump_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY braindump_sessions_user_policy ON braindump_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_braindump_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER braindump_sessions_updated_at
    BEFORE UPDATE ON braindump_sessions
    FOR EACH ROW EXECUTE FUNCTION update_braindump_sessions_updated_at();
