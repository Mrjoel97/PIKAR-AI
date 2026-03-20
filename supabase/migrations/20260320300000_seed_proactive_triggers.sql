-- Migration: Seed pilot proactive triggers for autonomous departments
-- Also relaxes decision_log constraints to match actual runner output types.

-- ============================================================================
-- 1. Widen department_decision_logs constraints
--    The DepartmentRunner emits more decision_type and outcome values than
--    the original CHECK constraints allowed. Drop and re-add them.
-- ============================================================================

-- decision_type: add inter_dept_acknowledged, notification_sent, trigger_error,
--               workflow_missing, workflow_failed
ALTER TABLE department_decision_logs DROP CONSTRAINT IF EXISTS department_decision_logs_decision_type_check;
ALTER TABLE department_decision_logs ADD CONSTRAINT department_decision_logs_decision_type_check
    CHECK (decision_type IN (
        'trigger_matched', 'trigger_skipped', 'workflow_launched', 'workflow_completed',
        'kpi_alert', 'escalated', 'inter_dept_request', 'no_action', 'error',
        'inter_dept_acknowledged', 'notification_sent', 'trigger_error',
        'workflow_missing', 'workflow_failed'
    ));

-- outcome: add acknowledged, cooldown, condition_unmet, rate_limited, executed,
--          launched, escalated, notified, completed, removed, cancelled
ALTER TABLE department_decision_logs DROP CONSTRAINT IF EXISTS department_decision_logs_outcome_check;
ALTER TABLE department_decision_logs ADD CONSTRAINT department_decision_logs_outcome_check
    CHECK (outcome IN (
        'success', 'pending', 'failed', 'skipped',
        'acknowledged', 'cooldown', 'condition_unmet', 'rate_limited',
        'executed', 'launched', 'escalated', 'notified', 'completed',
        'removed', 'cancelled', 'error'
    ));

-- action_taken was TEXT but runner sends JSONB objects. Change to JSONB.
-- Preserve any existing text data by casting.
ALTER TABLE department_decision_logs
    ALTER COLUMN action_taken TYPE JSONB USING
        CASE
            WHEN action_taken IS NULL THEN NULL
            WHEN action_taken::text ~ '^\s*\{' THEN action_taken::jsonb
            ELSE to_jsonb(action_taken::text)
        END;

-- ============================================================================
-- 2. Fix escalate action: inter_dept_requests uses "context" not "payload"
--    (runtime code fix is in department_runner.py, but also add "escalation"
--    to request_type check for completeness)
-- ============================================================================
ALTER TABLE inter_dept_requests DROP CONSTRAINT IF EXISTS inter_dept_requests_request_type_check;
ALTER TABLE inter_dept_requests ADD CONSTRAINT inter_dept_requests_request_type_check
    CHECK (request_type IN ('investigate', 'verify', 'review', 'execute', 'escalation'));

-- ============================================================================
-- 3. Seed pilot proactive triggers
-- ============================================================================

-- SALES trigger 1: Pipeline low
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'Low Pipeline Alert',
    'Triggers when open deal count drops below threshold',
    'metric_threshold',
    '{"metric_key": "metrics.open_deals", "operator": "lt", "threshold": 10}'::jsonb,
    'notify',
    '{"message": "Sales pipeline below 10 deals. Consider launching outreach campaign.", "severity": "warning"}'::jsonb,
    24, 1
FROM departments d WHERE d.type = 'SALES'
ON CONFLICT DO NOTHING;

-- SALES trigger 2: High-value deal detected
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'High-Value Deal Alert',
    'Triggers when a deal exceeds $100k threshold',
    'metric_threshold',
    '{"metric_key": "metrics.max_deal_value", "operator": "gte", "threshold": 100000}'::jsonb,
    'escalate',
    '{"target_department_id": null, "to_department_type": "STRATEGIC", "request_type": "review", "payload": {"reason": "High-value deal requires strategic review"}, "priority": 2}'::jsonb,
    48, 1
FROM departments d WHERE d.type = 'SALES'
ON CONFLICT DO NOTHING;

-- SUPPORT trigger: Ticket surge
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'Ticket Volume Surge',
    'Triggers when unresolved ticket count exceeds threshold',
    'event_count',
    '{"event_key": "metrics.unresolved_tickets", "min_count": 20}'::jsonb,
    'escalate',
    '{"target_department_id": null, "to_department_type": "OPERATIONS", "request_type": "investigate", "payload": {"reason": "Support ticket surge detected, may need process review"}, "priority": 1}'::jsonb,
    12, 2
FROM departments d WHERE d.type = 'SUPPORT'
ON CONFLICT DO NOTHING;

-- MARKETING trigger: Campaign underperformance
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'Campaign Underperformance',
    'Triggers when campaign CTR drops below minimum',
    'metric_threshold',
    '{"metric_key": "metrics.campaign_ctr", "operator": "lt", "threshold": 0.02}'::jsonb,
    'notify',
    '{"message": "Campaign CTR below 2%. Review targeting and creative assets.", "severity": "warning"}'::jsonb,
    24, 1
FROM departments d WHERE d.type = 'MARKETING'
ON CONFLICT DO NOTHING;

-- FINANCIAL trigger: Budget overspend
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'Budget Overspend Alert',
    'Triggers when monthly spend exceeds 90% of budget',
    'metric_threshold',
    '{"metric_key": "metrics.budget_utilization", "operator": "gte", "threshold": 0.9}'::jsonb,
    'escalate',
    '{"target_department_id": null, "to_department_type": "STRATEGIC", "request_type": "review", "payload": {"reason": "Budget utilization above 90%, review spending priorities"}, "priority": 2}'::jsonb,
    168, 1
FROM departments d WHERE d.type = 'FINANCIAL'
ON CONFLICT DO NOTHING;

-- OPERATIONS trigger: System latency alert
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'System Latency Alert',
    'Triggers when average response time exceeds threshold',
    'metric_threshold',
    '{"metric_key": "metrics.avg_response_ms", "operator": "gte", "threshold": 5000}'::jsonb,
    'notify',
    '{"message": "Average response time above 5s. Investigate system bottlenecks.", "severity": "critical"}'::jsonb,
    6, 3
FROM departments d WHERE d.type = 'OPERATIONS'
ON CONFLICT DO NOTHING;

-- HR trigger: Low employee satisfaction
INSERT INTO proactive_triggers (department_id, name, description, condition_type, condition_config, action_type, action_config, cooldown_hours, max_triggers_per_day)
SELECT d.id,
    'Employee Satisfaction Drop',
    'Triggers when employee NPS drops below threshold',
    'metric_threshold',
    '{"metric_key": "metrics.employee_nps", "operator": "lt", "threshold": 30}'::jsonb,
    'notify',
    '{"message": "Employee NPS below 30. Schedule pulse survey and 1:1 check-ins.", "severity": "warning"}'::jsonb,
    168, 1
FROM departments d WHERE d.type = 'HR'
ON CONFLICT DO NOTHING;
