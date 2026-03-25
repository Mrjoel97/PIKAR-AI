-- =============================================================================
-- Phase 14: Billing Dashboard — admin_agent_permissions seed rows
--
-- Seeds 7 permission rows for billing tools used by AdminAgent.
-- Autonomy tiers:
--   - get_billing_metrics: auto (read-only Stripe query)
--   - get_plan_distribution: auto (read-only DB query, no Stripe budget)
--   - detect_analytics_anomalies: auto (read-only stats computation)
--   - generate_executive_summary: auto (read-only narrative generation)
--   - forecast_revenue: auto (read-only trend projection)
--   - assess_refund_risk: auto (read-only risk scoring)
--   - issue_refund: confirm (mutates Stripe billing state, high risk)
-- =============================================================================

INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('billing', 'get_billing_metrics',          'auto',    'low',  'Fetch live MRR, ARR, and active subscription count from Stripe'),
    ('billing', 'get_plan_distribution',         'auto',    'low',  'Retrieve subscription tier breakdown from database without Stripe API call'),
    ('billing', 'detect_analytics_anomalies',    'auto',    'low',  'Flag metrics deviating more than 2 standard deviations from 30-day baseline'),
    ('billing', 'generate_executive_summary',    'auto',    'low',  'Generate narrative business summary with actionable recommendations'),
    ('billing', 'forecast_revenue',              'auto',    'low',  'Project next-month MRR using linear extrapolation from subscription history'),
    ('billing', 'assess_refund_risk',            'auto',    'low',  'Score refund risk by cross-referencing LTV, usage, and tenure'),
    ('billing', 'issue_refund',                  'confirm', 'high', 'Issue a Stripe refund for a charge — requires admin confirmation')
ON CONFLICT (action_category, action_name) DO NOTHING;
