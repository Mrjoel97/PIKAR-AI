-- Migration: Populate workflow_readiness.required_integrations
-- Maps each workflow template to its external API dependencies so the
-- journey_readiness view can show users what they need to configure.

BEGIN;

-- Workflows requiring Tavily (web search/research)
UPDATE workflow_readiness SET required_integrations = '["tavily"]'::jsonb
WHERE template_name IN (
  'Lead Generation Workflow',
  'Content Creation Workflow',
  'Competitor Analysis Workflow',
  'A/B Testing Workflow',
  'SEO Optimization Audit',
  'Email Sequence Workflow',
  'Social Media Campaign Workflow',
  'Product Launch Workflow',
  'Product Launch Campaign',
  'Outbound Prospecting',
  'Deal Closing',
  'Pipeline Review',
  'Win/Loss Analysis',
  'Influencer Outreach',
  'Partnership Development',
  'Strategic Planning Cycle',
  'Roadmap Planning',
  'Initiative Framework',
  'Fundraising Round',
  'Dashboard Creation',
  'Data Pipeline Setup',
  'Analytics Implementation'
);

-- Workflows requiring Tavily + Firecrawl (research + scraping)
UPDATE workflow_readiness SET required_integrations = '["tavily","firecrawl"]'::jsonb
WHERE template_name IN (
  'SEO Optimization Audit',
  'Competitor Analysis Workflow',
  'Lead Generation Workflow'
);

-- Workflows requiring Stitch (landing page generation)
UPDATE workflow_readiness SET required_integrations = required_integrations || '["stitch"]'::jsonb
WHERE template_name IN (
  'A/B Testing Workflow'
)
AND NOT (required_integrations @> '"stitch"');

-- Workflows with NO external API requirements (pure internal tools)
-- These are already [] by default, but let's be explicit
UPDATE workflow_readiness SET required_integrations = '[]'::jsonb
WHERE template_name IN (
  'Customer Onboarding',
  'Employee Onboarding',
  'Benefits Enrollment',
  'Payroll Processing',
  'Performance Review',
  'Recruitment Pipeline',
  'Contract Review',
  'GDPR Compliance Audit',
  'Data Governance Audit',
  'Quality Assurance Audit',
  'IP Filing',
  'Policy Update',
  'IT Asset Provisioning',
  'Vendor Onboarding',
  'Office Move/Expansion',
  'Crisis Management Response',
  'Incident Investigation',
  'Knowledge Base Update',
  'Financial Reporting',
  'Budget Planning',
  'Cash Flow Management',
  'Tax Filing Prep',
  'Account Renewal',
  'Churn Prevention',
  'Upsell Campaign',
  'Social Media Calendar',
  'Email Nurture Sequence',
  'Ad Campaign Management',
  'Webinar Hosting',
  'Merger & Acquisition (M&A)',
  'Feature Development',
  'Quarterly Business Review (QBR)',
  'Idea-to-Venture',
  'Landing Page to Launch'
);

COMMIT;
