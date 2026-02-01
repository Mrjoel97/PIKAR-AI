-- Migration: 0009_seed_workflows.sql
-- Description: Seed initial workflow templates

BEGIN;


            DELETE FROM workflow_templates WHERE name = 'A/B Testing Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'A/B Testing Workflow',
                'Optimization through experimentation',
                'data',
                '[{"name": "Hypothesis", "steps": [{"name": "Define Hypothesis", "tool": "get_trend_analysis_framework", "description": "Formulate testable hypothesis", "required_approval": true}]}, {"name": "Design", "steps": [{"name": "Create Variants", "tool": "mcp_stitch_generate_screen_from_text", "description": "Generate UI/Content variants", "required_approval": false}]}, {"name": "Configure", "steps": [{"name": "Setup Experiment", "tool": "setup_ab_test", "description": "Configure traffic split and metrics", "required_approval": false}]}, {"name": "Run", "steps": [{"name": "Execute Test", "tool": "start_experiment", "description": "Launch the experiment", "required_approval": false}]}, {"name": "Collect", "steps": [{"name": "Gather Data", "tool": "query_events", "description": "Collect experiment data", "required_approval": false}]}, {"name": "Analyze", "steps": [{"name": "Statistical Analysis", "tool": "analyze_results", "description": "Determine statistical significance", "required_approval": false}]}, {"name": "Decide", "steps": [{"name": "Pick Winner", "tool": "update_initiative_status", "description": "Implement winning variant", "required_approval": true}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Competitor Analysis Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Competitor Analysis Workflow',
                'Deep dive into competitor strategies',
                'strategy',
                '[{"name": "Identify", "steps": [{"name": "List Competitors", "tool": "mcp_web_search", "description": "Find key market players", "required_approval": false}]}, {"name": "Research", "steps": [{"name": "Analyze Presence", "tool": "mcp_web_scrape", "description": "Scrape websites and social", "required_approval": false}]}, {"name": "Analyze", "steps": [{"name": "SWOT Analysis", "tool": "create_swot", "description": "Identify strengths/weaknesses", "required_approval": false}]}, {"name": "Compare", "steps": [{"name": "Feature Matrix", "tool": "compare_features", "description": "Head-to-head comparison", "required_approval": false}]}, {"name": "Report", "steps": [{"name": "Generate Report", "tool": "create_report", "description": "Compile findings", "required_approval": false}]}, {"name": "Recommend", "steps": [{"name": "Action Items", "tool": "create_task", "description": "Create tasks based on gaps", "required_approval": true}]}, {"name": "Monitor", "steps": [{"name": "Track Changes", "tool": "setup_monitoring", "description": "Ongoing competitor tracking", "required_approval": false}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Content Creation Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Content Creation Workflow',
                'Blog, article, and resource creation',
                'content',
                '[{"name": "Ideate", "steps": [{"name": "Generate Ideas", "tool": "generate_content_ideas", "description": "Brainstorm topics", "required_approval": false}]}, {"name": "Research", "steps": [{"name": "Gather Info", "tool": "mcp_web_search", "description": "Research topic depth", "required_approval": false}]}, {"name": "Outline", "steps": [{"name": "Create Outline", "tool": "get_blog_writing_framework", "description": "Structure the content", "required_approval": true}]}, {"name": "Draft", "steps": [{"name": "Write Content", "tool": "generate_content", "description": "Write the first draft", "required_approval": false}]}, {"name": "Edit", "steps": [{"name": "Refine & Polish", "tool": "edit_content", "description": "Grammar and style check", "required_approval": false}]}, {"name": "Approve", "steps": [{"name": "Final Review", "tool": "display_content", "description": "Human sign-off", "required_approval": true}]}, {"name": "Publish", "steps": [{"name": "Distribute", "tool": "publish_content", "description": "Publish to CMS", "required_approval": false}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Email Sequence Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Email Sequence Workflow',
                'Design and execute email marketing campaigns',
                'marketing',
                '[{"name": "Design", "steps": [{"name": "Structure Sequence", "tool": "get_campaign_framework", "description": "Define sequence logic and timing", "required_approval": false}]}, {"name": "Write", "steps": [{"name": "Draft Content", "tool": "get_blog_writing_framework", "description": "Write email content (subject + body)", "required_approval": false}]}, {"name": "Review", "steps": [{"name": "Human Approval", "tool": "display_content", "description": "Review email drafts", "required_approval": true}]}, {"name": "Schedule", "steps": [{"name": "Setup Campaign", "tool": "create_campaign", "description": "Configure sending schedule", "required_approval": false}]}, {"name": "Send", "steps": [{"name": "Execute Send", "tool": "send_email_campaign", "description": "Dispatch emails to list", "required_approval": false}]}, {"name": "Track", "steps": [{"name": "Monitor Metrics", "tool": "record_campaign_metrics", "description": "Track opens, clicks, and replies", "required_approval": false}]}, {"name": "Optimize", "steps": [{"name": "Analyze Results", "tool": "get_trend_analysis_framework", "description": "A/B test analysis and adjustments", "required_approval": false}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Initiatives Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Initiatives Workflow',
                'From brain dump to scalable execution',
                'strategy',
                '[{"name": "Capture", "steps": [{"name": "Ingest Brain Dump", "tool": "add_business_knowledge", "description": "Capture the initial idea or context", "required_approval": false}]}, {"name": "Structure", "steps": [{"name": "Create Structure", "tool": "create_initiative", "description": "Convert brain dump into structured initiative", "required_approval": false}]}, {"name": "Validate", "steps": [{"name": "Review Structure", "tool": "list_initiatives", "description": "Human review of the created initiative", "required_approval": true}]}, {"name": "Plan", "steps": [{"name": "Define OKRs", "tool": "update_initiative_status", "description": "Add OKRs and goals to the initiative", "required_approval": true}]}, {"name": "Execute", "steps": [{"name": "Create Tasks", "tool": "create_task", "description": "Break down initiative into actionable tasks", "required_approval": false}]}, {"name": "Monitor", "steps": [{"name": "Track Progress", "tool": "query_events", "description": "Monitor task completion and metrics", "required_approval": false}]}, {"name": "Scale", "steps": [{"name": "Analyze Bottlenecks", "tool": "analyze_process_bottlenecks", "description": "Identify scaling issues", "required_approval": true}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Lead Generation Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Lead Generation Workflow',
                'End-to-end lead discovery and enrichment',
                'sales',
                '[{"name": "Research", "steps": [{"name": "Market Analysis", "tool": "mcp_web_search", "description": "Analyze market trends and competitor targets", "required_approval": false}]}, {"name": "Identify", "steps": [{"name": "Find Leads", "tool": "get_lead_qualification_framework", "description": "Identify potential leads matching criteria", "required_approval": false}]}, {"name": "Qualify", "steps": [{"name": "Score Leads", "tool": "score_leads", "description": "Apply BANT scoring to identified leads", "required_approval": false}]}, {"name": "Enrich", "steps": [{"name": "Enrich Data", "tool": "mcp_web_scrape", "description": "Gather additional contact info and context", "required_approval": false}]}, {"name": "Outreach", "steps": [{"name": "Draft Outreach", "tool": "generate_campaign_ideas", "description": "Create initial outreach messaging", "required_approval": true}]}, {"name": "Nurture", "steps": [{"name": "Start Sequence", "tool": "create_campaign", "description": "Add leads to nurture sequence", "required_approval": true}]}, {"name": "Convert", "steps": [{"name": "Handoff", "tool": "create_task", "description": "Create sales task for high-score leads", "required_approval": true}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Product Launch Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Product Launch Workflow',
                'From concept to market launch',
                'strategy',
                '[{"name": "Research", "steps": [{"name": "Market Fit", "tool": "mcp_web_search", "description": "Validate market need and competition", "required_approval": false}]}, {"name": "Plan", "steps": [{"name": "Launch Timeline", "tool": "create_initiative", "description": "Create initiative with key milestones", "required_approval": true}]}, {"name": "Create", "steps": [{"name": "Generate Assets", "tool": "generate_image", "description": "Create marketing images and copy", "required_approval": false}]}, {"name": "Test", "steps": [{"name": "Beta Test", "tool": "run_ab_test", "description": "Run limited beta or preview", "required_approval": false}]}, {"name": "Launch", "steps": [{"name": "Go Live", "tool": "trigger_launch", "description": "Activate product/feature", "required_approval": true}]}, {"name": "Promote", "steps": [{"name": "Landing Page", "tool": "mcp_generate_landing_page", "description": "Publish launch landing page", "required_approval": true}]}, {"name": "Measure", "steps": [{"name": "Launch Report", "tool": "create_report", "description": "Analyze launch performance", "required_approval": false}]}]'::jsonb
            );
            

            DELETE FROM workflow_templates WHERE name = 'Social Media Campaign Workflow';
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                'Social Media Campaign Workflow',
                'End-to-end social media management',
                'marketing',
                '[{"name": "Strategy", "steps": [{"name": "Define Goals", "tool": "get_campaign_framework", "description": "Set campaign objectives and KPI", "required_approval": false}]}, {"name": "Content", "steps": [{"name": "Create Posts", "tool": "generate_social_content", "description": "accurate and engaging post creation", "required_approval": false}]}, {"name": "Schedule", "steps": [{"name": "Calendar Setup", "tool": "create_campaign", "description": "Schedule posts for optimal times", "required_approval": false}]}, {"name": "Publish", "steps": [{"name": "Post Content", "tool": "publish_post", "description": "publish posts to platforms", "required_approval": false}]}, {"name": "Engage", "steps": [{"name": "Reply to Comments", "tool": "manage_comments", "description": "Community management", "required_approval": false}]}, {"name": "Analyze", "steps": [{"name": "Campaign Report", "tool": "record_campaign_metrics", "description": "Analyze engagement and reach", "required_approval": false}]}, {"name": "Iterate", "steps": [{"name": "Optimize Strategy", "tool": "update_strategy", "description": "Adjust strategy based on data", "required_approval": true}]}]'::jsonb
            );
            
COMMIT;