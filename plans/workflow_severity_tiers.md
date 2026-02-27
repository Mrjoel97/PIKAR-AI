# Workflow Severity Tiers

Purpose: define implementation and operational priority for workflow hardening.

## Tier Definitions

### Tier P0 (Critical)
Use when failure can cause direct financial loss, legal/compliance breach, payroll/payment error, or customer contract risk.

Required controls:
- Approval gates where applicable
- Strong idempotency
- Strict runtime checks enabled
- Integration health checks + rollback plan
- On-call alerting and runbook coverage

### Tier P1 (High)
Use for customer-facing or revenue-influencing workflows where failure materially impacts conversion, churn, or delivery quality.

Required controls:
- End-to-end smoke test
- Retry/cancel validation
- Actionable user-facing failure messages
- Metrics and dashboard visibility

### Tier P2 (Standard)
Use for internal productivity workflows with lower external impact.

Required controls:
- Happy-path + failure-path tests
- Basic observability
- Documented owner and fallback handling

## Initial Tiering Guidance

### Suggested P0
- Payroll Processing
- Invoice Processing
- Expense Reimbursement
- Cash Flow Management
- Account Renewal
- Contract Review
- Deal Closing
- GDPR Compliance Audit
- Tax Filing Prep
- Data Governance Audit
- Employee Onboarding
- Offboarding

### Suggested P1
- Lead Generation Workflow
- Product Launch Workflow
- A/B Testing Workflow
- Email Sequence Workflow
- Social Media Campaign Workflow
- Analytics Implementation
- Dashboard Creation
- Sales Training
- Support Ticket Resolution
- Customer Onboarding

### Suggested P2
- Remaining non-critical internal planning/ops/content workflows

## Ownership Requirement
- Every workflow must have a named engineering owner and product owner before production rollout.

