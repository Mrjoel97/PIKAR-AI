# Workflow Risk Matrix Baseline (2026-02-18)

This file freezes the initial workflow risk classification baseline for the 68 seeded templates.

## Classification Precedence
- `human-gated` if any step requires approval (`required_approval=true`)
- else `degraded-simulation-prone` if any degraded/simulation-prone tool is used
- else `integration-dependent` if any integration/high-risk tool is used
- else `fully autonomous`

## Summary Counts
- Fully autonomous: `22`
- Human-gated: `8`
- Integration-dependent: `11`
- Degraded-simulation-prone: `27`
- Total workflows: `68`

## Fully Autonomous (22)
- Content Creation Workflow
- Customer Onboarding
- Email Nurture Sequence
- Financial Reporting
- GDPR Compliance Audit
- IP Filing
- Knowledge Base Update
- Market Entry Strategy
- Outbound Prospecting
- Partnership Development
- Performance Review
- Policy Update
- Product Launch Campaign
- Quarterly Business Review (QBR)
- Roadmap Planning
- SEO Optimization Audit
- Social Media Calendar
- Strategic Planning Cycle
- Support Ticket Resolution
- User Research Sprint
- Webinar Hosting
- Win/Loss Analysis

## Human-Gated (8)
- A/B Testing Workflow
- Competitor Analysis Workflow
- Content Creation Workflow (Extended)
- Email Sequence Workflow
- Initiative Framework
- Lead Generation Workflow
- Product Launch Workflow
- Social Media Campaign Workflow

## Integration-Dependent (11)
- Account Renewal
- Analytics Implementation
- Benefits Enrollment
- Dashboard Creation
- Data Pipeline Setup
- Deal Closing
- Feature Development
- Influencer Outreach
- Machine Learning Pipeline
- Payroll Processing
- Sales Training

## Degraded-Simulation-Prone (27)
- Ad Campaign Management
- Beta Testing Program
- Budget Planning
- Bug Triage
- Cash Flow Management
- Churn Prevention
- Contract Review
- Crisis Management Response
- Data Governance Audit
- Employee Onboarding
- Expense Reimbursement
- Fundraising Round
- Incident Investigation
- Inventory Management
- Invoice Processing
- IT Asset Provisioning
- Lead Qualification
- Merger & Acquisition (M&A)
- Offboarding
- Office Move/Expansion
- Pipeline Review
- Quality Assurance Audit
- Recruitment Pipeline
- Tax Filing Prep
- Travel Policy Management
- Upsell Campaign
- Vendor Onboarding

