-- Migration: 0009_seed_workflows.sql
-- Description: Seed initial workflow templates (Expanded to 60+ workflows)

BEGIN;

-- Clear valid existing templates to avoid duplicates during re-seeding
DELETE FROM workflow_templates;

INSERT INTO workflow_templates (name, description, category, phases)
VALUES 
    -- STRATEGY & PLANNING (7)
    (
        'Strategic Planning Cycle',
        'Annual strategic planning and goal setting',
        'strategy',
        '[{"name": "Assess", "steps": [{"name": "Market Analysis", "tool": "mcp_web_search"}, {"name": "Internal Review", "tool": "query_events"}]}, {"name": "Define", "steps": [{"name": "Set Objectives", "tool": "create_initiative"}, {"name": "Key Results", "tool": "update_initiative_status"}]}, {"name": "Align", "steps": [{"name": "Dept Alignment", "tool": "create_task"}]}]'::jsonb
    ),
    (
        'Quarterly Business Review (QBR)',
        'Review performance and adjust strategy',
        'strategy',
        '[{"name": "Gather", "steps": [{"name": "Collect Data", "tool": "query_events"}]}, {"name": "Analyze", "steps": [{"name": "Performance Gap", "tool": "analyze_results"}]}, {"name": "Present", "steps": [{"name": "Create Deck", "tool": "generate_content"}]}]'::jsonb
    ),
    (
        'Market Entry Strategy',
        'Plan for entering a new geographic or demographic market',
        'strategy',
        '[{"name": "Research", "steps": [{"name": "Competitor Map", "tool": "mcp_web_search"}]}, {"name": "Strategy", "steps": [{"name": "Go-to-Market", "tool": "create_initiative"}]}, {"name": "Launch", "steps": [{"name": "Execute Pilot", "tool": "create_campaign"}]}]'::jsonb
    ),
    (
        'Partnership Development',
        'Identify, negotiate, and launch strategic partnerships',
        'strategy',
        '[{"name": "Identify", "steps": [{"name": "Scout Partners", "tool": "mcp_web_search"}]}, {"name": "Outreach", "steps": [{"name": "Contact", "tool": "send_email"}]}, {"name": "Sign", "steps": [{"name": "Contract", "tool": "create_document"}]}]'::jsonb
    ),
    (
        'Fundraising Round',
        'Manage investor relations and fundraising process',
        'strategy',
        '[{"name": "Prep", "steps": [{"name": "Pitch Deck", "tool": "generate_content"}]}, {"name": "Outreach", "steps": [{"name": "Investor List", "tool": "mcp_web_search"}]}, {"name": "Close", "steps": [{"name": "Due Diligence", "tool": "create_folder"}]}]'::jsonb
    ),
    (
        'Merger & Acquisition (M&A)',
        'Evaluate and execute M&A targets',
        'strategy',
        '[{"name": "Screen", "steps": [{"name": "Target List", "tool": "mcp_web_search"}]}, {"name": "Valuate", "steps": [{"name": "Financial Model", "tool": "create_spreadsheet"}]}, {"name": "Integrate", "steps": [{"name": "Merge Systems", "tool": "create_project"}]}]'::jsonb
    ),
     (
        'Crisis Management Response',
        'Handle PR or operational crises',
        'strategy',
        '[{"name": "Assess", "steps": [{"name": "Impact Analysis", "tool": "analyze_sentiment"}]}, {"name": "Respond", "steps": [{"name": "Public Statement", "tool": "generate_content"}]}, {"name": "Recover", "steps": [{"name": "Monitor", "tool": "setup_monitoring"}]}]'::jsonb
    ),

    -- MARKETING (8)
    (
        'Content Creation Workflow',
        'End-to-end content production from ideation to publish',
        'marketing',
        '[{"name": "Ideate", "steps": [{"name": "Brainstorm", "tool": "generate_ideas"}]}, {"name": "Draft", "steps": [{"name": "Write Copy", "tool": "generate_content"}]}, {"name": "Publish", "steps": [{"name": "Distribute", "tool": "publish_content"}]}]'::jsonb
    ),
    (
        'Social Media Calendar',
        'Weekly social media planning and posting',
        'marketing',
        '[{"name": "Plan", "steps": [{"name": "Schedule", "tool": "create_calendar_events"}]}, {"name": "Create", "steps": [{"name": "Design Assets", "tool": "generate_image"}]}, {"name": "Engage", "steps": [{"name": "Reply", "tool": "manage_comments"}]}]'::jsonb
    ),
    (
        'Email Nurture Sequence',
        'Automated email flows for lead nurturing',
        'marketing',
        '[{"name": "Segment", "steps": [{"name": "List Logic", "tool": "filter_users"}]}, {"name": "Write", "steps": [{"name": "Email Copy", "tool": "generate_content"}]}, {"name": "Automate", "steps": [{"name": "Activate", "tool": "create_campaign"}]}]'::jsonb
    ),
    (
        'Product Launch Campaign',
        'Marketing push for new product release',
        'marketing',
        '[{"name": "Tease", "steps": [{"name": "Social Teasers", "tool": "generate_social_content"}]}, {"name": "Launch", "steps": [{"name": "Press Release", "tool": "generate_content"}]}, {"name": "Sustain", "steps": [{"name": "Follow-up", "tool": "create_campaign"}]}]'::jsonb
    ),
    (
        'Webinar Hosting',
        'Plan, promote, and host webinars',
        'marketing',
        '[{"name": "Topic", "steps": [{"name": "Select Topic", "tool": "mcp_web_search"}]}, {"name": "Promote", "steps": [{"name": "Invites", "tool": "send_email_campaign"}]}, {"name": "Host", "steps": [{"name": "Live Event", "tool": "record_video"}]}]'::jsonb
    ),
    (
        'SEO Optimization Audit',
        'Improve website ranking and traffic',
        'marketing',
        '[{"name": "Audit", "steps": [{"name": "Site Crawl", "tool": "mcp_web_scrape"}]}, {"name": "Optimize", "steps": [{"name": "Update Keywords", "tool": "generate_content"}]}, {"name": "Linkbuild", "steps": [{"name": "Outreach", "tool": "send_email"}]}]'::jsonb
    ),
    (
        'Influencer Outreach',
        'Connect with brand ambassadors',
        'marketing',
        '[{"name": "Find", "steps": [{"name": "Search Content", "tool": "mcp_web_search"}]}, {"name": "Contact", "steps": [{"name": "DM/Email", "tool": "send_message"}]}, {"name": "Manage", "steps": [{"name": "Track Posts", "tool": "record_metrics"}]}]'::jsonb
    ),
    (
        'Ad Campaign Management',
        'Paid media strategy and execution',
        'marketing',
        '[{"name": "Design", "steps": [{"name": "Ad Creative", "tool": "generate_image"}]}, {"name": "Target", "steps": [{"name": "Audience Setup", "tool": "configure_ads"}]}, {"name": "Optimize", "steps": [{"name": "Bid Adjust", "tool": "optimize_spend"}]}]'::jsonb
    ),

    -- SALES (7)
    (
        'Lead Qualification',
        'Filter and score incoming leads',
        'sales',
        '[{"name": "Ingest", "steps": [{"name": "Capture Lead", "tool": "create_contact"}]}, {"name": "Score", "steps": [{"name": "BANT Check", "tool": "score_lead"}]}, {"name": "Assign", "steps": [{"name": "Route to Rep", "tool": "assign_task"}]}]'::jsonb
    ),
    (
        'Outbound Prospecting',
        'Cold outreach to potential clients',
        'sales',
        '[{"name": "List", "steps": [{"name": "Build List", "tool": "mcp_web_search"}]}, {"name": "Enrich", "steps": [{"name": "Get Emails", "tool": "mcp_web_scrape"}]}, {"name": "Reachout", "steps": [{"name": "Sequence", "tool": "send_email_campaign"}]}]'::jsonb
    ),
    (
        'Deal Closing',
        'Finalize contracts and close sales',
        'sales',
        '[{"name": "Demo", "steps": [{"name": "Product Demo", "tool": "schedule_meeting"}]}, {"name": "Negotiate", "steps": [{"name": "Update Quote", "tool": "create_document"}]}, {"name": "Sign", "steps": [{"name": "E-Sign", "tool": "send_contract"}]}]'::jsonb
    ),
    (
        'Account Renewal',
        'Retain existing customers',
        'sales',
        '[{"name": "Review", "steps": [{"name": "Usage Check", "tool": "query_metrics"}]}, {"name": "Proposal", "steps": [{"name": "Renewal Offer", "tool": "create_document"}]}, {"name": "Close", "steps": [{"name": "Process Order", "tool": "process_payment"}]}]'::jsonb
    ),
    (
        'Sales Training',
        'Onboard new sales representatives',
        'sales',
        '[{"name": "Learn", "steps": [{"name": "Shadow Calls", "tool": "listen_call"}]}, {"name": "Practice", "steps": [{"name": "Mock Demo", "tool": "record_video"}]}, {"name": "Live", "steps": [{"name": "First Call", "tool": "start_call"}]}]'::jsonb
    ),
    (
        'Pipeline Review',
        'Weekly sales pipeline analysis',
        'sales',
        '[{"name": "Inspect", "steps": [{"name": "Deal Health", "tool": "query_crm"}]}, {"name": "Forecast", "steps": [{"name": "Predict Rev", "tool": "generate_forecast"}]}, {"name": "Clean", "steps": [{"name": "Update Stages", "tool": "update_crm"}]}]'::jsonb
    ),
    (
        'Win/Loss Analysis',
        'Analyze closed deals for learning',
        'sales',
        '[{"name": "Interview", "steps": [{"name": "Client Call", "tool": "schedule_meeting"}]}, {"name": "Tag", "steps": [{"name": "Reason Code", "tool": "update_crm"}]}, {"name": "Report", "steps": [{"name": "Share Insights", "tool": "create_report"}]}]'::jsonb
    ),

    -- OPERATIONS (6)
    (
        'Vendor Onboarding',
        'Bring new suppliers into the system',
        'operations',
        '[{"name": "Vet", "steps": [{"name": "Due Diligence", "tool": "mcp_web_search"}]}, {"name": "Setup", "steps": [{"name": "Payment Info", "tool": "create_vendor"}]}, {"name": "Train", "steps": [{"name": "Portal Access", "tool": "send_email"}]}]'::jsonb
    ),
    (
        'Inventory Management',
        'Track and restock physical goods',
        'operations',
        '[{"name": "Audit", "steps": [{"name": "Count Stock", "tool": "update_inventory"}]}, {"name": "Order", "steps": [{"name": "PO Generation", "tool": "create_po"}]}, {"name": "Receive", "steps": [{"name": "Stock In", "tool": "log_shipment"}]}]'::jsonb
    ),
    (
        'Office Move/Expansion',
        'Manage physical location changes',
        'operations',
        '[{"name": "Plan", "steps": [{"name": "Space Plain", "tool": "create_document"}]}, {"name": "Logistics", "steps": [{"name": "hire Movers", "tool": "mcp_web_search"}]}, {"name": "Execute", "steps": [{"name": "Day of Move", "tool": "create_task_list"}]}]'::jsonb
    ),
    (
        'IT Asset Provisioning',
        'Setup equipment for employees',
        'operations',
        '[{"name": "Procure", "steps": [{"name": "Buy Laptop", "tool": "create_po"}]}, {"name": "Configure", "steps": [{"name": "Install SW", "tool": "run_script"}]}, {"name": "Assign", "steps": [{"name": "Handover", "tool": "update_asset_log"}]}]'::jsonb
    ),
    (
        'Travel Policy Management',
        'Handle corporate travel bookings',
        'operations',
        '[{"name": "Request", "steps": [{"name": "Approve Trip", "tool": "approve_request"}]}, {"name": "Book", "steps": [{"name": "Book Flight", "tool": "book_travel"}]}, {"name": "Expense", "steps": [{"name": "Reimburse", "tool": "process_expense"}]}]'::jsonb
    ),
    (
        'Quality Assurance Audit',
        'Regular operational quality checks',
        'operations',
        '[{"name": "Inspect", "steps": [{"name": "Check Process", "tool": "run_checklist"}]}, {"name": "Report", "steps": [{"name": "Log Issues", "tool": "create_ticket"}]}, {"name": "Fix", "steps": [{"name": "Corrective Action", "tool": "create_task"}]}]'::jsonb
    ),

    -- HR (6)
    (
        'Employee Onboarding',
        'Welcome and setup new hires',
        'hr',
        '[{"name": "Pre-boarding", "steps": [{"name": "Send Offer", "tool": "send_contract"}]}, {"name": "Day 1", "steps": [{"name": "Welcome", "tool": "send_email"}]}, {"name": "Training", "steps": [{"name": "Assign Course", "tool": "assign_training"}]}]'::jsonb
    ),
    (
        'Recruitment Pipeline',
        'Hire for open roles',
        'hr',
        '[{"name": "Source", "steps": [{"name": "Post Job", "tool": "post_job_board"}]}, {"name": "Interview", "steps": [{"name": "Screening", "tool": "schedule_interview"}]}, {"name": "Offer", "steps": [{"name": "Generate Offer", "tool": "create_document"}]}]'::jsonb
    ),
    (
        'Performance Review',
        'Annual or quarterly employee reviews',
        'hr',
        '[{"name": "Self-Review", "steps": [{"name": "Submit Feedback", "tool": "submit_form"}]}, {"name": "Manager Review", "steps": [{"name": "Evaluate", "tool": "submit_form"}]}, {"name": "Discussion", "steps": [{"name": "Meeting", "tool": "schedule_meeting"}]}]'::jsonb
    ),
    (
        'Payroll Processing',
        'Monthly salary disbursement',
        'hr',
        '[{"name": "Calc", "steps": [{"name": "Time-tracking", "tool": "query_timesheets"}]}, {"name": "Verify", "steps": [{"name": "Check Totals", "tool": "create_report"}]}, {"name": "Pay", "steps": [{"name": "Transfer", "tool": "execute_payroll"}]}]'::jsonb
    ),
    (
        'Benefits Enrollment',
        'Manage health and perks enrollment',
        'hr',
        '[{"name": "Announce", "steps": [{"name": "Open Enrollment", "tool": "send_email"}]}, {"name": "Collect", "steps": [{"name": "Gather Forms", "tool": "process_forms"}]}, {"name": "Submit", "steps": [{"name": "Update Provider", "tool": "send_file"}]}]'::jsonb
    ),
    (
        'Offboarding',
        'Exit process for departing employees',
        'hr',
        '[{"name": "Resign", "steps": [{"name": "Log Exit", "tool": "update_hris"}]}, {"name": "Recover", "steps": [{"name": "Return Assets", "tool": "create_checklist"}]}, {"name": "Interview", "steps": [{"name": "Exit Interview", "tool": "record_notes"}]}]'::jsonb
    ),

    -- PRODUCT (5)
    (
        'Feature Development',
        'Build new software features',
        'product',
        '[{"name": "Spec", "steps": [{"name": "Write PRD", "tool": "create_document"}]}, {"name": "Build", "steps": [{"name": "Code", "tool": "create_pr"}]}, {"name": "Ship", "steps": [{"name": "Deploy", "tool": "run_deployment"}]}]'::jsonb
    ),
    (
        'User Research Sprint',
        'Gather user insights',
        'product',
        '[{"name": "Recruit", "steps": [{"name": "Find Users", "tool": "send_email_campaign"}]}, {"name": "Interview", "steps": [{"name": "Conduct Calls", "tool": "record_video"}]}, {"name": "Synthesize", "steps": [{"name": "Insights", "tool": "create_report"}]}]'::jsonb
    ),
    (
        'Bug Triage',
        'Manage incoming defect reports',
        'product',
        '[{"name": "Verify", "steps": [{"name": "Reproduce", "tool": "test_scenario"}]}, {"name": "Prioritize", "steps": [{"name": "Rank", "tool": "update_ticket"}]}, {"name": "Fix", "steps": [{"name": "Assign Dev", "tool": "assign_task"}]}]'::jsonb
    ),
    (
        'Roadmap Planning',
        'Prioritize future work',
        'product',
        '[{"name": "Collect", "steps": [{"name": "Feature Requests", "tool": "query_feedback"}]}, {"name": "Score", "steps": [{"name": "RICE Score", "tool": "calculate_score"}]}, {"name": "Map", "steps": [{"name": "Update Roadmap", "tool": "update_gantt"}]}]'::jsonb
    ),
    (
        'Beta Testing Program',
        'Test pre-release software',
        'product',
        '[{"name": "Invite", "steps": [{"name": "Send Access", "tool": "send_email"}]}, {"name": "Monitor", "steps": [{"name": "Track Usage", "tool": "query_analytics"}]}, {"name": "Feedback", "steps": [{"name": "Survey", "tool": "create_form"}]}]'::jsonb
    ),

    -- CUSTOMER SUCCESS (5)
    (
        'Customer Onboarding',
        'Get new clients to value',
        'support',
        '[{"name": "Kickoff", "steps": [{"name": "Intro Call", "tool": "schedule_meeting"}]}, {"name": "Setup", "steps": [{"name": "Config Account", "tool": "update_settings"}]}, {"name": "Training", "steps": [{"name": "Walkthrough", "tool": "send_guide"}]}]'::jsonb
    ),
    (
        'Support Ticket Resolution',
        'Handle helpdesk requests',
        'support',
        '[{"name": "Triage", "steps": [{"name": "Categorize", "tool": "update_ticket"}]}, {"name": "Solve", "steps": [{"name": "Reply", "tool": "send_email"}]}, {"name": "Close", "steps": [{"name": "CSAT Survey", "tool": "send_form"}]}]'::jsonb
    ),
    (
        'Churn Prevention',
        'Save at-risk accounts',
        'support',
        '[{"name": "Alert", "steps": [{"name": "Risk Flag", "tool": "create_alert"}]}, {"name": "Engage", "steps": [{"name": "Reach Out", "tool": "schedule_call"}]}, {"name": "Resolve", "steps": [{"name": "Fix Issue", "tool": "create_task"}]}]'::jsonb
    ),
    (
        'Upsell Campaign',
        'Expand account revenue',
        'support',
        '[{"name": "Identify", "steps": [{"name": "Find Opps", "tool": "query_usage"}]}, {"name": "Pitch", "steps": [{"name": "Send Offer", "tool": "send_email"}]}, {"name": "Close", "steps": [{"name": "Upgrade", "tool": "update_subscription"}]}]'::jsonb
    ),
    (
        'Knowledge Base Update',
        'Maintain help documentation',
        'support',
        '[{"name": "Review", "steps": [{"name": "Check Old Docs", "tool": "read_docs"}]}, {"name": "Update", "steps": [{"name": "Edit Article", "tool": "update_cms"}]}, {"name": "Publish", "steps": [{"name": "Live", "tool": "publish_page"}]}]'::jsonb
    ),

    -- FINANCE (6)
    (
        'Expense Reimbursement',
        'Process employee expenses',
        'finance',
        '[{"name": "Submit", "steps": [{"name": "Upload Receipt", "tool": "upload_file"}]}, {"name": "Approve", "steps": [{"name": "Manager Check", "tool": "approve_request"}]}, {"name": "Pay", "steps": [{"name": "Reimburse", "tool": "process_payment"}]}]'::jsonb
    ),
    (
        'Invoice Processing',
        'Pay vendor bills',
        'finance',
        '[{"name": "Receive", "steps": [{"name": "Scan Bill", "tool": "ocr_document"}]}, {"name": "Match", "steps": [{"name": "Match PO", "tool": "verify_po"}]}, {"name": "Pay", "steps": [{"name": "Wire Transfer", "tool": "send_payment"}]}]'::jsonb
    ),
     (
        'Budget Planning',
        'Annual budgeting process',
        'finance',
        '[{"name": "Forecast", "steps": [{"name": "Project Rev", "tool": "generate_forecast"}]}, {"name": "Allocate", "steps": [{"name": "Set Limits", "tool": "update_budget"}]}, {"name": "Track", "steps": [{"name": "Monitor burn", "tool": "query_ledger"}]}]'::jsonb
    ),
    (
        'Tax Filing Prep',
        'Prepare for tax season',
        'finance',
        '[{"name": "Gather", "steps": [{"name": "Collect Reports", "tool": "generate_report"}]}, {"name": "Audit", "steps": [{"name": "Verify Data", "tool": "run_audit"}]}, {"name": "File", "steps": [{"name": "Submit Return", "tool": "upload_document"}]}]'::jsonb
    ),
    (
        'Financial Reporting',
        'Monthly P&L and Balance Sheet',
        'finance',
        '[{"name": "Close Books", "steps": [{"name": "Reconcile", "tool": "update_ledger"}]}, {"name": "Generate", "steps": [{"name": "Create P&L", "tool": "create_spreadsheet"}]}, {"name": "Distribute", "steps": [{"name": "Send Board Deck", "tool": "send_email"}]}]'::jsonb
    ),
    (
        'Cash Flow Management',
        'Monitor liquidity',
        'finance',
        '[{"name": "Monitor", "steps": [{"name": "Check Balances", "tool": "query_bank"}]}, {"name": "Project", "steps": [{"name": "Forecast Cash", "tool": "create_forecast"}]}, {"name": "Optimize", "steps": [{"name": "Move Funds", "tool": "transfer_money"}]}]'::jsonb
    ),

    -- LEGAL & COMPLIANCE (5)
    (
        'Contract Review',
        'Legal review of agreements',
        'legal',
        '[{"name": "Intake", "steps": [{"name": "Upload Doc", "tool": "upload_file"}]}, {"name": "Review", "steps": [{"name": "redline", "tool": "edit_document"}]}, {"name": "Approve", "steps": [{"name": "Sign Off", "tool": "approve_request"}]}]'::jsonb
    ),
    (
        'GDPR Compliance Audit',
        'Ensure data privacy',
        'legal',
        '[{"name": "Map Data", "steps": [{"name": "Scan Systems", "tool": "scan_database"}]}, {"name": "Assess", "steps": [{"name": "Check Policy", "tool": "review_policy"}]}, {"name": "Remediate", "steps": [{"name": "Fix Gaps", "tool": "create_task"}]}]'::jsonb
    ),
    (
        'IP Filing',
        'Register patents or trademarks',
        'legal',
        '[{"name": "Search", "steps": [{"name": "Prior Art", "tool": "mcp_web_search"}]}, {"name": "Draft", "steps": [{"name": "Write Application", "tool": "create_document"}]}, {"name": "File", "steps": [{"name": "Submit", "tool": "send_file"}]}]'::jsonb
    ),
    (
        'Policy Update',
        'Update employee handbook',
        'legal',
        '[{"name": "Draft", "steps": [{"name": "Write Policy", "tool": "generate_content"}]}, {"name": "Review", "steps": [{"name": "Legal Check", "tool": "approve_document"}]}, {"name": "Distribute", "steps": [{"name": "Notify All", "tool": "send_email"}]}]'::jsonb
    ),
    (
        'Incident Investigation',
        'Investigate workplace incidents',
        'legal',
        '[{"name": "Report", "steps": [{"name": "Log Incident", "tool": "create_record"}]}, {"name": "Investigate", "steps": [{"name": "Interview", "tool": "record_notes"}]}, {"name": "Resolution", "steps": [{"name": "Close Case", "tool": "update_record"}]}]'::jsonb
    ),

    -- DATA (5)
    (
        'Data Pipeline Setup',
        'Create new ETL process',
        'data',
        '[{"name": "Connect", "steps": [{"name": "Source Auth", "tool": "create_connection"}]}, {"name": "Transform", "steps": [{"name": "Write SQL", "tool": "create_query"}]}, {"name": "Load", "steps": [{"name": "Target Table", "tool": "create_table"}]}]'::jsonb
    ),
    (
        'Dashboard Creation',
        'Build BI dashboard',
        'data',
        '[{"name": "Reqs", "steps": [{"name": "Gather Metrics", "tool": "create_document"}]}, {"name": "Build", "steps": [{"name": "Visualize", "tool": "create_chart"}]}, {"name": "Publish", "steps": [{"name": "Share", "tool": "grant_access"}]}]'::jsonb
    ),
    (
        'Data Governance Audit',
        'Check data quality and access',
        'data',
        '[{"name": "Scan", "steps": [{"name": "Check Access", "tool": "audit_logs"}]}, {"name": "Validate", "steps": [{"name": "Data Quality", "tool": "run_test"}]}, {"name": "Report", "steps": [{"name": "Findings", "tool": "create_report"}]}]'::jsonb
    ),
    (
        'Machine Learning Pipeline',
        'Train and deploy ML model',
        'data',
        '[{"name": "Prep", "steps": [{"name": "Clean Data", "tool": "process_data"}]}, {"name": "Train", "steps": [{"name": "Run Model", "tool": "train_model"}]}, {"name": "Deploy", "steps": [{"name": "Productionize", "tool": "deploy_service"}]}]'::jsonb
    ),
    (
        'Analytics Implementation',
        'Add tracking to app',
        'data',
        '[{"name": "Plan", "steps": [{"name": "Define Events", "tool": "create_tracking_plan"}]}, {"name": "Code", "steps": [{"name": "Add Tags", "tool": "update_code"}]}, {"name": "Verify", "steps": [{"name": "Test Events", "tool": "check_logs"}]}]'::jsonb
    );

COMMIT;
