-- Unified Action History
-- Cross-agent chronological feed of all AI-performed actions.
-- Part of CROSS-02: unified action history requirement.

CREATE TABLE IF NOT EXISTS unified_action_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name text NOT NULL,
    action_type text NOT NULL,
    description text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    source_id text,          -- optional link to workflow_execution_id, interaction_log_id, etc.
    source_type text,        -- 'interaction', 'workflow', 'tool_call', 'decision'
    created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_uah_user_created ON unified_action_history(user_id, created_at DESC);
CREATE INDEX idx_uah_agent ON unified_action_history(agent_name);
CREATE INDEX idx_uah_action_type ON unified_action_history(action_type);

ALTER TABLE unified_action_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own action history"
    ON unified_action_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert action history"
    ON unified_action_history FOR INSERT
    WITH CHECK (true);
