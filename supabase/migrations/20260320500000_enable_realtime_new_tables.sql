-- Enable Supabase Realtime for new department and credential tables
-- so frontend components can subscribe to live changes.

ALTER PUBLICATION supabase_realtime ADD TABLE proactive_triggers;
ALTER PUBLICATION supabase_realtime ADD TABLE department_decision_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE inter_dept_requests;
ALTER PUBLICATION supabase_realtime ADD TABLE api_credentials;
