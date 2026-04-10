-- Decision Journal table for logging and querying past business decisions.
-- Part of Phase 59 Cross-Agent Intelligence (CROSS-03).

CREATE TABLE IF NOT EXISTS decision_journal (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic text NOT NULL,
    decision_text text NOT NULL,
    rationale text,
    agent_name text,
    outcome text,
    tags text[] DEFAULT '{}',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX idx_dj_user_created ON decision_journal(user_id, created_at DESC);
CREATE INDEX idx_dj_topic ON decision_journal USING gin(to_tsvector('english', topic));

ALTER TABLE decision_journal ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own decisions"
    ON decision_journal FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage decisions"
    ON decision_journal FOR ALL
    USING (true)
    WITH CHECK (true);
