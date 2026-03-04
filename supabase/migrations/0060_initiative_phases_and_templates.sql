-- Migration: Expand initiatives table with phase tracking, templates, and status alignment
-- Also creates initiative_templates table for predefined initiative blueprints

-- =============================================================================
-- 1. Expand initiatives table
-- =============================================================================

-- Add phase tracking columns
ALTER TABLE initiatives
  ADD COLUMN IF NOT EXISTS phase TEXT DEFAULT 'ideation',
  ADD COLUMN IF NOT EXISTS phase_progress JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS template_id UUID,
  ADD COLUMN IF NOT EXISTS workflow_execution_id UUID,
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Migrate existing status values to unified vocabulary
-- Old: draft -> not_started, active -> in_progress, on_hold -> on_hold, completed -> completed
UPDATE initiatives SET status = 'not_started' WHERE status = 'draft';
UPDATE initiatives SET status = 'in_progress' WHERE status = 'active';

-- Add comment for status vocabulary reference
COMMENT ON COLUMN initiatives.status IS 'Unified statuses: not_started, in_progress, completed, blocked, on_hold';
COMMENT ON COLUMN initiatives.phase IS 'Initiative framework phase: ideation, validation, prototype, build, scale';
COMMENT ON COLUMN initiatives.phase_progress IS 'Per-phase progress JSON: {"ideation": 100, "validation": 60, ...}';
COMMENT ON COLUMN initiatives.metadata IS 'Flexible metadata: OKRs, milestones, KPIs, notes';

-- =============================================================================
-- 2. Create initiative_templates table
-- =============================================================================

CREATE TABLE IF NOT EXISTS initiative_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    persona TEXT NOT NULL,  -- solopreneur, startup, sme, enterprise
    category TEXT DEFAULT 'general',
    icon TEXT DEFAULT '🚀',
    priority TEXT DEFAULT 'medium',
    phases JSONB NOT NULL DEFAULT '[]',  -- Pre-configured phase definitions
    suggested_workflows JSONB DEFAULT '[]',  -- Workflow template names to suggest per phase
    kpis JSONB DEFAULT '[]',  -- KPI definitions to track
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS for initiative_templates (read-only for all authenticated users)
ALTER TABLE initiative_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "initiative_templates_read" ON initiative_templates
    FOR SELECT TO authenticated
    USING (true);

-- Index for persona filtering
CREATE INDEX IF NOT EXISTS idx_initiative_templates_persona ON initiative_templates(persona);
CREATE INDEX IF NOT EXISTS idx_initiative_templates_category ON initiative_templates(category);

-- =============================================================================
-- 3. Seed initiative templates (20 templates, 5 per persona)
-- =============================================================================

INSERT INTO initiative_templates (title, description, persona, category, icon, priority, phases, suggested_workflows, kpis) VALUES

-- SOLOPRENEUR templates
('Podcast Launch', 'Launch a professional podcast from concept to first 10 episodes', 'solopreneur', 'content', '🎙️', 'high',
 '[{"name":"ideation","steps":["Define podcast niche and target audience","Research competing podcasts","Choose format (interview, solo, panel)","Name and brand the podcast"]},{"name":"validation","steps":["Survey potential listeners","Test concept with 3 pilot episodes","Gather feedback from beta listeners","Refine format based on feedback"]},{"name":"prototype","steps":["Set up recording equipment and software","Record and edit 3 pilot episodes","Create cover art and intro/outro","Set up hosting platform"]},{"name":"build","steps":["Record first 10 episodes","Create show notes and transcripts","Set up distribution (Apple, Spotify, etc.)","Build landing page"]},{"name":"scale","steps":["Launch marketing campaign","Grow subscriber base","Monetize with sponsors/ads","Expand to video format"]}]',
 '["Content Creation Workflow","Social Media Campaign"]',
 '["Episodes published","Downloads per episode","Subscriber count","Listener retention rate"]'),

('Online Course Launch', 'Create and launch a profitable online course', 'solopreneur', 'product', '📚', 'high',
 '[{"name":"ideation","steps":["Identify expertise area and market demand","Define target student persona","Outline course learning outcomes","Research pricing strategy"]},{"name":"validation","steps":["Pre-sell to waitlist","Survey potential students","Analyze competitor courses","Validate willingness to pay"]},{"name":"prototype","steps":["Create course outline","Record first module as pilot","Build landing page with signup","Test with beta students"]},{"name":"build","steps":["Record all course modules","Create supplementary materials","Set up course platform","Build sales funnel"]},{"name":"scale","steps":["Launch with promotional pricing","Collect testimonials","Create affiliate program","Expand course catalog"]}]',
 '["Content Creation Workflow","Email Sequence Workflow","Lead Generation Workflow"]',
 '["Students enrolled","Course completion rate","Revenue","Student satisfaction score"]'),

('Personal Brand Building', 'Establish yourself as a thought leader in your niche', 'solopreneur', 'marketing', '⭐', 'medium',
 '[{"name":"ideation","steps":["Define unique value proposition","Identify target audience","Choose primary platforms","Create brand voice guide"]},{"name":"validation","steps":["Audit current online presence","Research industry thought leaders","Test content themes","Gather audience feedback"]},{"name":"prototype","steps":["Create content calendar","Build professional website/portfolio","Set up social media profiles","Publish first content series"]},{"name":"build","steps":["Execute 90-day content plan","Network with industry peers","Guest post on established platforms","Build email list"]},{"name":"scale","steps":["Monetize personal brand","Launch speaking engagements","Create brand partnerships","Expand to new platforms"]}]',
 '["Social Media Campaign","Content Creation Workflow"]',
 '["Followers/connections","Engagement rate","Website traffic","Inbound opportunities"]'),

('Freelance Service Launch', 'Launch and grow a profitable freelance service business', 'solopreneur', 'service', '💼', 'high',
 '[{"name":"ideation","steps":["Define service offerings","Identify ideal client profile","Set pricing structure","Create service packages"]},{"name":"validation","steps":["Research market rates","Interview potential clients","Test pricing with early clients","Validate service-market fit"]},{"name":"prototype","steps":["Create portfolio with case studies","Build service proposal templates","Set up contracts and invoicing","Deliver first 3 client projects"]},{"name":"build","steps":["Build client acquisition funnel","Create onboarding process","Establish delivery workflow","Set up project management system"]},{"name":"scale","steps":["Hire subcontractors","Automate administrative tasks","Create referral program","Expand service offerings"]}]',
 '["Lead Generation Workflow","Content Creation Workflow"]',
 '["Monthly revenue","Client retention rate","Average project value","Referral rate"]'),

('Blog Content Strategy', 'Build a traffic-generating blog with SEO-optimized content', 'solopreneur', 'content', '✍️', 'medium',
 '[{"name":"ideation","steps":["Define blog niche and topics","Research keyword opportunities","Create content pillars","Plan monetization strategy"]},{"name":"validation","steps":["Analyze competitor blogs","Validate keyword search volume","Test content ideas on social media","Survey target readers"]},{"name":"prototype","steps":["Write and publish 5 pillar articles","Set up SEO tracking","Create email opt-in","Test content promotion channels"]},{"name":"build","steps":["Execute 3-month content calendar","Build internal linking structure","Optimize for featured snippets","Grow email subscriber list"]},{"name":"scale","steps":["Monetize with affiliates/ads","Guest posting for backlinks","Repurpose content across platforms","Hire content writers"]}]',
 '["Content Creation Workflow","SEO Optimization Audit"]',
 '["Monthly organic traffic","Email subscribers","Domain authority","Revenue per visitor"]'),

-- STARTUP templates
('MVP Launch', 'Build and launch a minimum viable product to validate your startup idea', 'startup', 'product', '🚀', 'critical',
 '[{"name":"ideation","steps":["Define core problem and solution","Map user personas","Identify must-have features vs nice-to-have","Create product vision document"]},{"name":"validation","steps":["Conduct 20 customer discovery interviews","Build landing page with signup","Run smoke test ads","Analyze competitor solutions"]},{"name":"prototype","steps":["Design wireframes and user flows","Build clickable prototype","Run usability tests with 10 users","Iterate based on feedback"]},{"name":"build","steps":["Define technical architecture","Sprint 1: Core feature development","Sprint 2: Integration and testing","Beta launch to waitlist"]},{"name":"scale","steps":["Analyze usage metrics","Implement feedback loop","Optimize onboarding funnel","Plan Series A features"]}]',
 '["Product Launch Workflow","A/B Testing Workflow"]',
 '["Signups","Activation rate","Daily active users","Net Promoter Score"]'),

('Seed Fundraising', 'Raise seed funding from angels and early-stage VCs', 'startup', 'finance', '💰', 'critical',
 '[{"name":"ideation","steps":["Define funding needs and use of funds","Research target investors","Create fundraising timeline","Prepare team bios and credentials"]},{"name":"validation","steps":["Build financial model with projections","Validate market size (TAM/SAM/SOM)","Gather traction metrics","Get warm introductions to 5 investors"]},{"name":"prototype","steps":["Create pitch deck (15 slides)","Prepare data room","Practice pitch with advisors","Create one-pager for cold outreach"]},{"name":"build","steps":["Begin investor meetings (target 30+)","Track pipeline in CRM","Negotiate term sheets","Complete due diligence"]},{"name":"scale","steps":["Close round and wire funds","Send investor update template","Set up cap table management","Plan next milestones for Series A"]}]',
 '["Lead Generation Workflow","Competitor Analysis Workflow"]',
 '["Investors contacted","Meetings held","Term sheets received","Amount raised"]'),

('Product-Market Fit Validation', 'Systematically validate that your product solves a real problem', 'startup', 'strategy', '🎯', 'critical',
 '[{"name":"ideation","steps":["Define PMF hypothesis","Identify key assumptions to test","Create experiment roadmap","Set success/failure criteria"]},{"name":"validation","steps":["Run Sean Ellis survey (40% threshold)","Analyze retention cohorts","Conduct user interviews","Map customer journey pain points"]},{"name":"prototype","steps":["A/B test core value proposition","Build feature usage analytics","Create feedback collection system","Test pricing sensitivity"]},{"name":"build","steps":["Double down on what works","Remove low-usage features","Optimize activation funnel","Build referral mechanism"]},{"name":"scale","steps":["Document PMF playbook","Scale acquisition channels","Hire for growth","Plan next product iteration"]}]',
 '["A/B Testing Workflow","Lead Generation Workflow"]',
 '["Sean Ellis score","Retention rate (D7, D30)","NPS score","Organic growth rate"]'),

('Growth Hacking Experiments', 'Run systematic growth experiments to find scalable acquisition channels', 'startup', 'marketing', '📈', 'high',
 '[{"name":"ideation","steps":["Audit current growth channels","Brainstorm 20 experiment ideas","Prioritize using ICE framework","Define experiment templates"]},{"name":"validation","steps":["Run 5 quick experiments per week","Measure results with statistical significance","Interview power users","Analyze viral coefficient"]},{"name":"prototype","steps":["Build growth experiment dashboard","Create A/B testing infrastructure","Set up attribution tracking","Test referral program V1"]},{"name":"build","steps":["Scale top 3 performing channels","Automate experiment workflows","Build growth team rituals","Create experiment documentation"]},{"name":"scale","steps":["Optimize CAC across channels","Build compound growth loops","Hire growth specialists","Expand to international markets"]}]',
 '["A/B Testing Workflow","Social Media Campaign","Email Sequence Workflow"]',
 '["Experiments run per week","Conversion rate","Customer acquisition cost","Monthly growth rate"]'),

('Product Hunt Launch', 'Execute a successful Product Hunt launch to gain visibility and early users', 'startup', 'marketing', '🏆', 'high',
 '[{"name":"ideation","steps":["Research top PH launches in category","Define launch day strategy","Identify hunter and supporters","Create launch timeline"]},{"name":"validation","steps":["Build pre-launch community","Collect 100+ committed upvoters","Test messaging with beta users","Prepare press kit"]},{"name":"prototype","steps":["Create PH assets (logo, screenshots, video)","Write compelling tagline and description","Set up special offer for PH users","Prepare FAQ and responses"]},{"name":"build","steps":["Schedule launch date","Brief support team","Prepare social media blitz","Set up analytics tracking"]},{"name":"scale","steps":["Launch and engage all day","Respond to every comment","Follow up with leads","Write launch retrospective"]}]',
 '["Product Launch Workflow","Social Media Campaign","Content Creation Workflow"]',
 '["Upvotes","Website traffic on launch day","Signups from PH","Press mentions"]'),

-- SME templates
('New Market Expansion', 'Expand your business into a new geographic or vertical market', 'sme', 'strategy', '🌍', 'high',
 '[{"name":"ideation","steps":["Identify target markets","Assess internal readiness","Define expansion goals","Create market entry criteria"]},{"name":"validation","steps":["Conduct market size analysis","Research local regulations","Analyze competitive landscape","Interview potential partners"]},{"name":"prototype","steps":["Run pilot program in target market","Test localized messaging","Build local partnerships","Gather market feedback"]},{"name":"build","steps":["Hire local team","Adapt product for market","Set up operations and logistics","Launch marketing campaigns"]},{"name":"scale","steps":["Optimize market-specific KPIs","Expand product offerings","Build brand awareness","Plan next market entry"]}]',
 '["Competitor Analysis Workflow","Lead Generation Workflow"]',
 '["Market share","Revenue from new market","Customer acquisition cost","Brand awareness"]'),

('Brand Refresh', 'Modernize your brand identity to stay competitive', 'sme', 'marketing', '🎨', 'medium',
 '[{"name":"ideation","steps":["Audit current brand perception","Define brand refresh objectives","Research industry trends","Create mood boards"]},{"name":"validation","steps":["Survey customers and employees","Focus group testing","Competitive brand analysis","Validate new direction"]},{"name":"prototype","steps":["Design new visual identity","Create brand guidelines","Test with key stakeholders","Refine based on feedback"]},{"name":"build","steps":["Roll out across all touchpoints","Update marketing materials","Train team on brand guidelines","Launch announcement campaign"]},{"name":"scale","steps":["Monitor brand perception metrics","Ensure consistency across channels","Gather ongoing feedback","Plan brand evolution roadmap"]}]',
 '["Content Creation Workflow","Social Media Campaign"]',
 '["Brand awareness score","Customer perception shift","Employee brand alignment","Social media engagement"]'),

('CRM Migration', 'Migrate to a new CRM system without losing data or momentum', 'sme', 'operations', '🔄', 'high',
 '[{"name":"ideation","steps":["Assess current CRM pain points","Define requirements for new CRM","Research CRM options","Create selection criteria"]},{"name":"validation","steps":["Demo top 3 CRM platforms","Calculate total cost of ownership","Pilot test with small team","Validate data migration feasibility"]},{"name":"prototype","steps":["Set up test environment","Migrate sample data","Configure workflows and automations","Train pilot team"]},{"name":"build","steps":["Full data migration","Configure all integrations","Train all users","Run parallel systems for 2 weeks"]},{"name":"scale","steps":["Decommission old system","Optimize new workflows","Build custom reports","Ongoing training program"]}]',
 '["Vendor Onboarding","Data Pipeline Setup"]',
 '["Data migration accuracy","User adoption rate","Sales cycle time","System uptime"]'),

('Employee Wellness Program', 'Launch a comprehensive employee wellness initiative', 'sme', 'hr', '💚', 'medium',
 '[{"name":"ideation","steps":["Survey employee wellness needs","Research wellness program options","Define program objectives","Create budget proposal"]},{"name":"validation","steps":["Benchmark against industry programs","Interview wellness providers","Pilot test 2-3 program elements","Gather employee interest data"]},{"name":"prototype","steps":["Launch pilot with one department","Offer 3 wellness activities","Collect participation data","Gather feedback surveys"]},{"name":"build","steps":["Roll out company-wide","Set up wellness portal","Launch incentive program","Train HR on program management"]},{"name":"scale","steps":["Measure health outcomes","Expand program offerings","Calculate ROI (reduced turnover, absenteeism)","Share success stories"]}]',
 '["Employee Onboarding","Performance Review"]',
 '["Participation rate","Employee satisfaction","Absenteeism reduction","Turnover reduction"]'),

('Customer Success Playbook', 'Build a systematic customer success program to reduce churn', 'sme', 'support', '🤝', 'high',
 '[{"name":"ideation","steps":["Analyze current churn reasons","Define customer health metrics","Map customer lifecycle stages","Identify at-risk signals"]},{"name":"validation","steps":["Interview churned customers","Benchmark retention rates","Test health scoring model","Validate intervention strategies"]},{"name":"prototype","steps":["Build customer health dashboard","Create playbooks for each lifecycle stage","Test automated alerts","Run rescue campaigns for at-risk accounts"]},{"name":"build","steps":["Hire/train CS team","Implement CS platform","Launch QBR process","Build knowledge base"]},{"name":"scale","steps":["Automate routine touchpoints","Expand to proactive outreach","Create customer advocacy program","Optimize lifetime value"]}]',
 '["Customer Onboarding","Churn Prevention","Support Ticket Resolution"]',
 '["Churn rate","Net revenue retention","Customer health score","NPS"]'),

-- ENTERPRISE templates
('Digital Transformation', 'Lead a comprehensive digital transformation across the organization', 'enterprise', 'strategy', '🔮', 'critical',
 '[{"name":"ideation","steps":["Assess digital maturity","Identify transformation opportunities","Define vision and success metrics","Secure executive sponsorship"]},{"name":"validation","steps":["Benchmark against industry leaders","Evaluate technology options","Assess organizational readiness","Calculate business case and ROI"]},{"name":"prototype","steps":["Select pilot department","Implement proof of concept","Measure early results","Document lessons learned"]},{"name":"build","steps":["Create transformation roadmap","Establish PMO","Roll out in waves","Manage change and training"]},{"name":"scale","steps":["Measure enterprise-wide impact","Optimize and iterate","Build center of excellence","Plan next transformation wave"]}]',
 '["Strategic Planning Cycle","Data Pipeline Setup","Cloud Migration Strategy"]',
 '["Digital maturity score","Process automation rate","Employee adoption","Cost savings"]'),

('M&A Integration', 'Successfully integrate an acquired company post-merger', 'enterprise', 'strategy', '🏢', 'critical',
 '[{"name":"ideation","steps":["Define integration vision and principles","Identify synergy opportunities","Assess cultural differences","Create integration team"]},{"name":"validation","steps":["Due diligence deep dive","Map systems and processes overlap","Identify retention-critical talent","Validate synergy estimates"]},{"name":"prototype","steps":["Pilot integration in one function","Test combined processes","Run joint team workshops","Measure early synergies"]},{"name":"build","steps":["Execute 100-day integration plan","Consolidate systems","Align compensation and benefits","Communicate continuously"]},{"name":"scale","steps":["Realize cost and revenue synergies","Fully integrate culture","Measure against targets","Document playbook for future M&A"]}]',
 '["Merger & Acquisition (M&A)","Strategic Planning Cycle"]',
 '["Synergy realization rate","Employee retention","System consolidation","Revenue impact"]'),

('AI Governance Framework', 'Establish responsible AI governance across the enterprise', 'enterprise', 'compliance', '🤖', 'high',
 '[{"name":"ideation","steps":["Inventory AI/ML use cases","Define AI ethics principles","Identify regulatory requirements","Create governance charter"]},{"name":"validation","steps":["Benchmark AI governance frameworks","Assess current risk exposure","Consult legal and compliance","Validate with industry experts"]},{"name":"prototype","steps":["Create AI risk assessment template","Pilot governance process","Test bias detection tools","Build model documentation standards"]},{"name":"build","steps":["Establish AI review board","Implement model monitoring","Create training program","Deploy governance tools"]},{"name":"scale","steps":["Audit all AI systems","Continuous monitoring","Update for new regulations","Share framework externally"]}]',
 '["GDPR Compliance Audit","Data Governance Audit"]',
 '["AI systems audited","Compliance rate","Bias incidents","Model documentation coverage"]'),

('Global Compliance Audit', 'Conduct a comprehensive multi-jurisdiction compliance review', 'enterprise', 'compliance', '⚖️', 'critical',
 '[{"name":"ideation","steps":["Map all jurisdictions and regulations","Define audit scope and objectives","Assemble audit team","Create audit timeline"]},{"name":"validation","steps":["Review current compliance status","Identify high-risk areas","Benchmark against peers","Validate audit methodology"]},{"name":"prototype","steps":["Pilot audit in one jurisdiction","Test compliance checklists","Validate evidence collection","Refine audit processes"]},{"name":"build","steps":["Execute full audit program","Collect and analyze evidence","Document findings and gaps","Create remediation plans"]},{"name":"scale","steps":["Implement remediation actions","Build continuous monitoring","Report to board","Plan next audit cycle"]}]',
 '["GDPR Compliance Audit","Contract Review","Compliance Training"]',
 '["Compliance score","Findings resolved","Audit coverage","Regulatory penalties avoided"]'),

('Innovation Lab Launch', 'Create an internal innovation lab to drive R&D and new ventures', 'enterprise', 'product', '🔬', 'high',
 '[{"name":"ideation","steps":["Define innovation lab mission","Research successful corporate labs","Identify focus areas","Secure funding and sponsorship"]},{"name":"validation","steps":["Interview internal stakeholders","Assess available talent and skills","Benchmark innovation metrics","Validate governance model"]},{"name":"prototype","steps":["Set up physical/virtual lab space","Recruit initial team","Run first innovation sprint","Demo results to leadership"]},{"name":"build","steps":["Establish processes and rituals","Build partnerships (academia, startups)","Launch idea pipeline","Create measurement framework"]},{"name":"scale","steps":["Spin out successful projects","Expand team and budget","Build innovation culture","Track commercial impact"]}]',
 '["Feature Development","User Research Sprint","Beta Testing Program"]',
 '["Ideas generated","Prototypes built","Projects commercialized","Revenue from innovation"]')

ON CONFLICT DO NOTHING;
