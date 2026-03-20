-- Telemetry schema for agent and tool usage tracking (Phase 1)

-- Agent delegation events
CREATE TABLE IF NOT EXISTS agent_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_name TEXT NOT NULL,
    delegated_from TEXT,
    user_id UUID,
    session_id TEXT,
    task_summary TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'timeout')),
    duration_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tool usage events
CREATE TABLE IF NOT EXISTS tool_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tool_name TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    user_id UUID,
    session_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'error')),
    duration_ms INTEGER,
    error_type TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_agent_telemetry_agent_created
    ON agent_telemetry(agent_name, created_at);
CREATE INDEX IF NOT EXISTS idx_tool_telemetry_tool_created
    ON tool_telemetry(tool_name, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_telemetry_user
    ON agent_telemetry(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_telemetry_errors
    ON agent_telemetry(status, created_at)
    WHERE status = 'error';

-- RLS: service role only (telemetry is backend-written, not user-facing)
ALTER TABLE agent_telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_telemetry ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "service_role_agent_telemetry" ON agent_telemetry
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_tool_telemetry" ON tool_telemetry
    FOR ALL USING (auth.role() = 'service_role');

-- Data retention: scheduled cleanup (run weekly via pg_cron or Supabase function)
-- Keeps 90 days of telemetry data
CREATE OR REPLACE FUNCTION cleanup_telemetry_data()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_telemetry WHERE created_at < now() - interval '90 days';
    DELETE FROM tool_telemetry WHERE created_at < now() - interval '90 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
