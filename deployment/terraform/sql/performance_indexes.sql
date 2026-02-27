-- Performance Indexes Migration
-- Adds missing indexes for query optimization

-- Index for workflow_executions(user_id, status)
CREATE INDEX IF NOT EXISTS idx_workflow_executions_user_status 
ON workflow_executions(user_id, status);

-- Index for session_events(app_name, user_id, session_id, version)
CREATE INDEX IF NOT EXISTS idx_session_events_lookup 
ON session_events(app_name, user_id, session_id, version);

-- Index for agent_knowledge(user_id, source_type)
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_user_source 
ON agent_knowledge(user_id, source_type);

-- Index for skill_usage_log composite for analytics
CREATE INDEX IF NOT EXISTS idx_skill_usage_analytics 
ON skill_usage_log(skill_id, used_at DESC);

-- Partial index for active sessions
CREATE INDEX IF NOT EXISTS idx_sessions_active 
ON sessions(user_id, updated_at DESC) 
WHERE status = 'active';

-- Index for user_executive_agents lookup
CREATE INDEX IF NOT EXISTS idx_user_executive_agents_user 
ON user_executive_agents(user_id);

-- Index for approval_requests status lookup
CREATE INDEX IF NOT EXISTS idx_approval_requests_status 
ON approval_requests(status, created_at DESC);

-- Composite index for report scheduling
CREATE INDEX IF NOT EXISTS idx_report_schedules_next_run 
ON report_schedules(enabled, next_run_at) 
WHERE enabled = true;
