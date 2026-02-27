-- Migration: 0038_seed_yaml_workflows.sql
-- Description: Seed the 8 YAML-defined workflow templates into the DB
-- These templates are NOT in the original 0009 migration and add ~8 more templates

-- Ensure unique template names so ON CONFLICT works (idempotent re-runs)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'workflow_templates_name_key'
        AND conrelid = 'workflow_templates'::regclass
    ) THEN
        ALTER TABLE workflow_templates ADD CONSTRAINT workflow_templates_name_key UNIQUE (name);
    END IF;
END $$;

INSERT INTO workflow_templates (name, description, category, phases)
VALUES
(
    'A/B Testing Workflow',
    'Optimization through experimentation',
    'data',
    '[{"name":"Hypothesis","steps":[{"name":"Define Hypothesis","tool":"quick_research","description":"Formulate testable hypothesis","required_approval":true}]},{"name":"Design","steps":[{"name":"Create Variants","tool":"save_content","description":"Generate UI/Content variants","required_approval":false}]},{"name":"Configure","steps":[{"name":"Setup Experiment","tool":"create_task","description":"Configure traffic split and metrics","required_approval":false}]},{"name":"Run","steps":[{"name":"Execute Test","tool":"track_event","description":"Launch the experiment","required_approval":false}]},{"name":"Collect","steps":[{"name":"Gather Data","tool":"query_events","description":"Collect experiment data","required_approval":false}]},{"name":"Analyze","steps":[{"name":"Statistical Analysis","tool":"create_report","description":"Determine statistical significance","required_approval":false}]},{"name":"Decide","steps":[{"name":"Pick Winner","tool":"update_initiative","description":"Implement winning variant","required_approval":true}]}]'::jsonb
),
(
    'Competitor Analysis Workflow',
    'Deep dive into competitor strategies',
    'strategy',
    '[{"name":"Identify","steps":[{"name":"List Competitors","tool":"mcp_web_search","description":"Find key market players","required_approval":false}]},{"name":"Research","steps":[{"name":"Analyze Presence","tool":"mcp_web_scrape","description":"Scrape websites and social","required_approval":false}]},{"name":"Analyze","steps":[{"name":"SWOT Analysis","tool":"competitor_research","description":"Identify strengths/weaknesses","required_approval":false}]},{"name":"Compare","steps":[{"name":"Feature Matrix","tool":"quick_research","description":"Head-to-head comparison","required_approval":false}]},{"name":"Report","steps":[{"name":"Generate Report","tool":"create_report","description":"Compile findings","required_approval":false}]},{"name":"Recommend","steps":[{"name":"Action Items","tool":"create_task","description":"Create tasks based on gaps","required_approval":true}]},{"name":"Monitor","steps":[{"name":"Track Changes","tool":"track_event","description":"Ongoing competitor tracking","required_approval":false}]}]'::jsonb
),
(
    'Email Sequence Workflow',
    'Design and execute email marketing campaigns',
    'marketing',
    '[{"name":"Design","steps":[{"name":"Structure Sequence","tool":"quick_research","description":"Define sequence logic and timing","required_approval":false}]},{"name":"Write","steps":[{"name":"Draft Content","tool":"save_content","description":"Write email content (subject + body)","required_approval":false}]},{"name":"Review","steps":[{"name":"Human Approval","tool":"list_content","description":"Review email drafts","required_approval":true}]},{"name":"Schedule","steps":[{"name":"Setup Campaign","tool":"create_campaign","description":"Configure sending schedule","required_approval":false}]},{"name":"Send","steps":[{"name":"Execute Send","tool":"update_campaign","description":"Dispatch emails to list","required_approval":false}]},{"name":"Track","steps":[{"name":"Monitor Metrics","tool":"record_campaign_metrics","description":"Track opens, clicks, and replies","required_approval":false}]},{"name":"Optimize","steps":[{"name":"Analyze Results","tool":"query_events","description":"A/B test analysis and adjustments","required_approval":false}]}]'::jsonb
),
(
    'Initiative Framework',
    '5-phase initiative framework: Ideation to Validation to Prototype to Build to Scale',
    'strategy',
    '[{"name":"Ideation and Empathy","phase_key":"ideation","steps":[{"name":"Capture Initial Idea","tool":"add_business_knowledge","description":"Record the raw idea","required_approval":false},{"name":"Create Initiative Record","tool":"create_initiative","description":"Create a structured initiative","required_approval":false},{"name":"Define Target Audience","tool":"deep_research","description":"Research the target audience","required_approval":false},{"name":"Empathy Mapping","tool":"quick_research","description":"Map user perspective","required_approval":false},{"name":"Review Ideation Phase","tool":"list_initiatives","description":"Review before validation","required_approval":true}]},{"name":"Validation and Research","phase_key":"validation","steps":[{"name":"Market Research","tool":"market_research","description":"Comprehensive market research","required_approval":false},{"name":"Competitor Analysis","tool":"competitor_research","description":"Analyze competitors","required_approval":false},{"name":"Web Research","tool":"mcp_web_search","description":"Search for trends and data","required_approval":false},{"name":"Feasibility Assessment","tool":"quick_research","description":"Assess feasibility","required_approval":false},{"name":"Track Validation Metrics","tool":"track_event","description":"Record findings","required_approval":false},{"name":"Validation Approval Gate","tool":"list_initiatives","description":"Decide whether to proceed","required_approval":true}]},{"name":"Prototype and Test","phase_key":"prototype","steps":[{"name":"Create MVP Specification","tool":"save_content","description":"Document the MVP spec","required_approval":false},{"name":"Build Prototype Tasks","tool":"create_task","description":"Break down into tasks","required_approval":false},{"name":"User Testing Plan","tool":"save_content","description":"Create testing plan","required_approval":false},{"name":"Collect Feedback","tool":"track_event","description":"Record feedback","required_approval":false},{"name":"Iterate on Prototype","tool":"update_initiative","description":"Update with learnings","required_approval":false},{"name":"Prototype Approval Gate","tool":"list_initiatives","description":"Review and decide","required_approval":true}]},{"name":"Build Product or Service","phase_key":"build","steps":[{"name":"Full Task Breakdown","tool":"create_task","description":"Detailed task breakdown","required_approval":false},{"name":"Resource Allocation","tool":"quick_research","description":"Allocate resources","required_approval":false},{"name":"Timeline and Milestones","tool":"update_initiative","description":"Set milestones","required_approval":false},{"name":"Execution Tracking","tool":"track_event","description":"Track progress","required_approval":false},{"name":"Quality Review","tool":"query_events","description":"Review metrics","required_approval":false},{"name":"Build Approval Gate","tool":"list_initiatives","description":"Approve for launch","required_approval":true}]},{"name":"Scale Business","phase_key":"scale","steps":[{"name":"Growth Strategy","tool":"deep_research","description":"Define growth strategy","required_approval":false},{"name":"Marketing Campaign","tool":"create_campaign","description":"Launch marketing","required_approval":false},{"name":"Metrics Monitoring","tool":"query_events","description":"Monitor growth metrics","required_approval":false},{"name":"Financial Analysis","tool":"get_revenue_stats","description":"Analyze revenue","required_approval":false},{"name":"Bottleneck Analysis","tool":"quick_research","description":"Address bottlenecks","required_approval":false},{"name":"Create Scale Report","tool":"create_report","description":"Generate report","required_approval":false},{"name":"Scale Review","tool":"list_initiatives","description":"Final review","required_approval":true}]}]'::jsonb
),
(
    'Lead Generation Workflow',
    'End-to-end lead discovery and enrichment',
    'sales',
    '[{"name":"Research","steps":[{"name":"Market Analysis","tool":"mcp_web_search","description":"Analyze market trends","required_approval":false}]},{"name":"Identify","steps":[{"name":"Find Leads","tool":"quick_research","description":"Identify potential leads","required_approval":false}]},{"name":"Qualify","steps":[{"name":"Score Leads","tool":"quick_research","description":"Apply scoring to leads","required_approval":false}]},{"name":"Enrich","steps":[{"name":"Enrich Data","tool":"mcp_web_scrape","description":"Gather additional contact info","required_approval":false}]},{"name":"Outreach","steps":[{"name":"Draft Outreach","tool":"save_content","description":"Create outreach messaging","required_approval":true}]},{"name":"Nurture","steps":[{"name":"Start Sequence","tool":"create_campaign","description":"Add leads to nurture sequence","required_approval":true}]},{"name":"Convert","steps":[{"name":"Handoff","tool":"create_task","description":"Create sales task for high-score leads","required_approval":true}]}]'::jsonb
),
(
    'Product Launch Workflow',
    'From concept to market launch',
    'strategy',
    '[{"name":"Research","steps":[{"name":"Market Fit","tool":"mcp_web_search","description":"Validate market need","required_approval":false}]},{"name":"Plan","steps":[{"name":"Launch Timeline","tool":"create_initiative","description":"Create initiative with milestones","required_approval":true}]},{"name":"Create","steps":[{"name":"Generate Assets","tool":"save_content","description":"Create marketing images and copy","required_approval":false}]},{"name":"Test","steps":[{"name":"Beta Test","tool":"track_event","description":"Run limited beta","required_approval":false}]},{"name":"Launch","steps":[{"name":"Go Live","tool":"create_task","description":"Activate product/feature","required_approval":true}]},{"name":"Promote","steps":[{"name":"Campaign","tool":"create_campaign","description":"Launch promotion campaign","required_approval":true}]},{"name":"Measure","steps":[{"name":"Launch Report","tool":"create_report","description":"Analyze launch performance","required_approval":false}]}]'::jsonb
),
(
    'Social Media Campaign Workflow',
    'End-to-end social media management',
    'marketing',
    '[{"name":"Strategy","steps":[{"name":"Define Goals","tool":"quick_research","description":"Set campaign objectives and KPIs","required_approval":false}]},{"name":"Content","steps":[{"name":"Create Posts","tool":"save_content","description":"Create engaging post content","required_approval":false}]},{"name":"Schedule","steps":[{"name":"Calendar Setup","tool":"create_campaign","description":"Schedule posts for optimal times","required_approval":false}]},{"name":"Publish","steps":[{"name":"Post Content","tool":"update_campaign","description":"Publish posts to platforms","required_approval":false}]},{"name":"Engage","steps":[{"name":"Reply to Comments","tool":"list_content","description":"Community management","required_approval":false}]},{"name":"Analyze","steps":[{"name":"Campaign Report","tool":"record_campaign_metrics","description":"Analyze engagement and reach","required_approval":false}]},{"name":"Iterate","steps":[{"name":"Optimize Strategy","tool":"quick_research","description":"Adjust strategy based on data","required_approval":true}]}]'::jsonb
),
(
    'Content Creation Workflow (Extended)',
    'Blog, article, and resource creation with AI assistance',
    'content',
    '[{"name":"Ideate","steps":[{"name":"Generate Ideas","tool":"quick_research","description":"Brainstorm content topics","required_approval":false}]},{"name":"Research","steps":[{"name":"Gather Info","tool":"mcp_web_search","description":"Research topic depth","required_approval":false}]},{"name":"Outline","steps":[{"name":"Create Outline","tool":"save_content","description":"Structure the content","required_approval":true}]},{"name":"Draft","steps":[{"name":"Write Content","tool":"save_content","description":"Write the first draft","required_approval":false}]},{"name":"Edit","steps":[{"name":"Refine and Polish","tool":"update_content","description":"Grammar and style check","required_approval":false}]},{"name":"Approve","steps":[{"name":"Final Review","tool":"list_content","description":"Human sign-off","required_approval":true}]},{"name":"Publish","steps":[{"name":"Distribute","tool":"update_content","description":"Publish to platform","required_approval":false}]}]'::jsonb
)
ON CONFLICT (name) DO NOTHING;
