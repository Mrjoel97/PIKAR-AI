-- Enable Realtime for session events (live chat updates)
ALTER PUBLICATION supabase_realtime ADD TABLE session_events;

-- Enable Realtime for workflow executions (live workflow status)
ALTER PUBLICATION supabase_realtime ADD TABLE workflow_executions;

-- Enable Realtime for workflow steps (live step progress)
ALTER PUBLICATION supabase_realtime ADD TABLE workflow_steps;

-- Enable Realtime for user executive agents (persona changes)
ALTER PUBLICATION supabase_realtime ADD TABLE user_executive_agents;

-- Note: notifications table already has Realtime enabled in 0006_notifications.sql
