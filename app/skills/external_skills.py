# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""External Skills Library - Skills installed from external repositories.

This module defines skills installed from:
- coreyhaines31/marketingskills (23 skills)
- obra/superpowers (14 skills)
- vercel-labs/agent-skills
- anthropics/skills
- callstackincubator/agent-skills
- nextlevelbuilder/ui-ux-pro-max-skill

Total: 37 external skills mapped to appropriate agents based on domain expertise.
"""

from app.skills.registry import AgentID, Skill, skills_registry


# =============================================================================
# Marketing & CRO Skills (from coreyhaines31/marketingskills)
# =============================================================================

analytics_tracking = Skill(
    name="analytics_tracking",
    description="Set up and optimize analytics tracking for conversion funnels, user behavior, and marketing attribution.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.DATA],
    knowledge="""
## Analytics Tracking Framework
- Event tracking setup for key user actions
- Conversion funnel analysis
- Attribution modeling (first-touch, last-touch, multi-touch)
- UTM parameter management
- Goal and conversion setup in analytics platforms
""",
)

competitor_alternatives = Skill(
    name="competitor_alternatives",
    description="Analyze competitors and position your product as the better alternative.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.STRAT, AgentID.SALES],
    knowledge="""
## Competitor Analysis Framework
- Feature comparison matrices
- Pricing positioning strategies
- Unique value proposition development
- Switching cost analysis
- Competitor weakness identification
""",
)

copy_editing = Skill(
    name="copy_editing",
    description="Polish and improve marketing copy with the Seven Sweeps framework.",
    category="copywriting",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Copy Editing Seven Sweeps
1. Clarity sweep - Remove jargon, simplify language
2. Brevity sweep - Cut unnecessary words
3. Specificity sweep - Replace vague with concrete
4. Active voice sweep - Convert passive constructions
5. Rhythm sweep - Vary sentence length
6. Emotional sweep - Strengthen emotional appeal
7. CTA sweep - Ensure clear calls-to-action
""",
)

copywriting = Skill(
    name="copywriting",
    description="Write compelling marketing copy for landing pages, websites, and campaigns.",
    category="copywriting",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Copywriting Principles
- Clarity over cleverness
- Benefits over features
- Specificity over vagueness
- Customer language over company jargon
- One idea per section
- Headline formulas: outcome without pain, specific transformation
- CTA formulas: Action verb + What they get
""",
)

email_sequence = Skill(
    name="email_sequence",
    description="Design and write effective email sequences for onboarding, nurturing, and conversion.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.SALES, AgentID.CONT],
    knowledge="""
## Email Sequence Framework
- Welcome sequence (3-5 emails)
- Onboarding sequence with activation milestones
- Nurture sequence for lead warming
- Re-engagement sequence for dormant users
- Subject line formulas and A/B testing
- Timing and frequency optimization
""",
)

form_cro = Skill(
    name="form_cro",
    description="Optimize forms for higher completion rates and better user experience.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.OPS],
    knowledge="""
## Form CRO Best Practices
- Reduce field count (remove unnecessary fields)
- Use smart defaults and autofill
- Progressive disclosure for complex forms
- Inline validation with helpful error messages
- Multi-step forms with progress indicators
- Mobile optimization
""",
)

free_tool_strategy = Skill(
    name="free_tool_strategy",
    description="Create free tools as lead generation and marketing assets.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.STRAT],
    knowledge="""
## Free Tool Strategy
- Identify high-value, low-friction tool ideas
- Design for virality and sharing
- Lead capture integration
- SEO optimization for tool pages
- Conversion path from free tool to paid product
""",
)

launch_strategy = Skill(
    name="launch_strategy",
    description="Plan and execute effective product launches with maximum impact.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.STRAT, AgentID.SALES],
    knowledge="""
## Launch Strategy Framework
- Pre-launch: build waitlist, generate buzz
- Launch day: coordinated announcements
- Post-launch: momentum maintenance
- Channel selection: Product Hunt, social, email
- Press and influencer outreach
- Launch metrics and success criteria
""",
)

marketing_ideas = Skill(
    name="marketing_ideas",
    description="Generate creative marketing ideas and campaign concepts.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.CONT, AgentID.STRAT],
    knowledge="""
## Marketing Ideas Framework
- Content marketing angles
- Viral marketing concepts
- Partnership opportunities
- Community building tactics
- User-generated content strategies
- Unconventional marketing channels
""",
)

marketing_psychology = Skill(
    name="marketing_psychology",
    description="Apply psychological principles to improve marketing effectiveness.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.SALES, AgentID.CONT],
    knowledge="""
## Marketing Psychology Principles
- Social proof and authority
- Scarcity and urgency
- Reciprocity and commitment
- Loss aversion framing
- Anchoring and contrast
- Cognitive ease and fluency
- FOMO and exclusivity
""",
)

onboarding_cro = Skill(
    name="onboarding_cro",
    description="Optimize user onboarding flows for activation and retention.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.OPS, AgentID.SUPP],
    knowledge="""
## Onboarding CRO Framework
- Identify activation milestones
- Reduce time-to-value
- Progressive profiling
- Contextual tooltips and guides
- Gamification elements
- Personalization based on user segments
""",
)

page_cro = Skill(
    name="page_cro",
    description="Optimize landing pages and marketing pages for higher conversions.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.CONT],
    knowledge="""
## Page CRO Framework
- Value proposition clarity (5-second test)
- Headline effectiveness
- CTA placement and copy
- Visual hierarchy and scannability
- Trust signals and social proof
- Objection handling
- Friction point reduction
""",
)

paid_ads = Skill(
    name="paid_ads",
    description="Create and optimize paid advertising campaigns across platforms.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.DATA],
    knowledge="""
## Paid Ads Framework
- Campaign structure best practices
- Ad copy formulas and variations
- Audience targeting strategies
- Bidding and budget optimization
- A/B testing methodology
- ROAS and CAC tracking
""",
)

paywall_upgrade_cro = Skill(
    name="paywall_upgrade_cro",
    description="Optimize paywall and upgrade flows for better conversion.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.SALES],
    knowledge="""
## Paywall CRO Framework
- Value demonstration before paywall
- Pricing presentation optimization
- Trial-to-paid conversion tactics
- Feature gating strategies
- Upgrade trigger identification
- Churn prevention at paywall
""",
)

popup_cro = Skill(
    name="popup_cro",
    description="Design and optimize popups for lead capture without hurting UX.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.CONT],
    knowledge="""
## Popup CRO Framework
- Exit-intent timing
- Scroll-based triggers
- Time-delay optimization
- Mobile-friendly designs
- Value exchange optimization
- Frequency capping
""",
)

pricing_strategy = Skill(
    name="pricing_strategy",
    description="Develop effective pricing strategies and structures.",
    category="marketing_cro",
    agent_ids=[AgentID.STRAT, AgentID.FIN, AgentID.SALES],
    knowledge="""
## Pricing Strategy Framework
- Value-based pricing
- Competitive positioning
- Tier structure optimization
- Psychological pricing tactics
- Usage-based vs flat-rate models
- Freemium conversion optimization
""",
)

programmatic_seo = Skill(
    name="programmatic_seo",
    description="Scale SEO efforts through programmatic page generation.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.DATA, AgentID.CONT],
    knowledge="""
## Programmatic SEO Framework
- Template-based page generation
- Dynamic content optimization
- Internal linking at scale
- Schema markup automation
- Keyword clustering and mapping
- Quality control for generated pages
""",
)

referral_program = Skill(
    name="referral_program",
    description="Design and optimize referral programs for viral growth.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.SALES, AgentID.STRAT],
    knowledge="""
## Referral Program Framework
- Incentive structure design
- Double-sided rewards
- Viral loop optimization
- Share mechanism optimization
- Referral tracking and attribution
- Program promotion strategies
""",
)

schema_markup = Skill(
    name="schema_markup",
    description="Implement schema markup for enhanced search visibility.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.DATA],
    knowledge="""
## Schema Markup Framework
- JSON-LD implementation
- Organization schema
- Product/Service schema
- FAQ schema for featured snippets
- Review/Rating schema
- Event and LocalBusiness schema
""",
)

seo_audit = Skill(
    name="seo_audit",
    description="Conduct comprehensive SEO audits with actionable recommendations.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.DATA],
    knowledge="""
## SEO Audit Framework
- Technical SEO (crawlability, indexing)
- On-page optimization review
- Content quality assessment
- Backlink profile analysis
- Site speed and Core Web Vitals
- Mobile-friendliness check
- Competitor gap analysis
""",
)

signup_flow_cro = Skill(
    name="signup_flow_cro",
    description="Optimize signup and registration flows for maximum conversion.",
    category="marketing_cro",
    agent_ids=[AgentID.MKT, AgentID.OPS],
    knowledge="""
## Signup Flow CRO Framework
- Single vs multi-step signup
- Social login options
- Progressive profiling
- Email verification optimization
- Password requirements UX
- Error handling and recovery
""",
)

social_media_strategy = Skill(
    name="social_media_strategy",
    description="Create engaging social media content strategies across platforms.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Social Media Strategy Framework
- Platform-specific content formats
- Hook and engagement optimization
- Visual content best practices
- Hashtag strategies
- Posting schedule optimization
- Community engagement tactics
- Content calendar planning
""",
)


# =============================================================================
# Development & Workflow Skills (from obra/superpowers)
# =============================================================================

brainstorming = Skill(
    name="brainstorming",
    description="Facilitate effective brainstorming sessions for idea generation.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.CONT, AgentID.MKT, AgentID.OPS],
    knowledge="""
## Brainstorming Framework
- Divergent thinking phase (quantity over quality)
- Convergent thinking phase (evaluate and select)
- Mind mapping techniques
- SCAMPER method
- Six Thinking Hats
- Constraint removal exercises
""",
)

dispatching_parallel_agents = Skill(
    name="dispatching_parallel_agents",
    description="Coordinate multiple AI agents working in parallel on complex tasks.",
    category="development",
    agent_ids=[AgentID.EXEC, AgentID.OPS, AgentID.DATA],
    knowledge="""
## Parallel Agent Dispatch Framework
- Task decomposition for parallelization
- Agent role assignment
- Result aggregation strategies
- Dependency management
- Error handling and retry logic
- Progress monitoring
""",
)

executing_plans = Skill(
    name="executing_plans",
    description="Execute structured plans with systematic task completion.",
    category="planning",
    agent_ids=[AgentID.EXEC, AgentID.OPS, AgentID.STRAT],
    knowledge="""
## Plan Execution Framework
- Task prioritization and sequencing
- Milestone tracking
- Blockers identification and resolution
- Progress reporting
- Plan adaptation when needed
- Completion verification
""",
)

subagent_driven_development = Skill(
    name="subagent_driven_development",
    description="Use specialized sub-agents for different aspects of development.",
    category="development",
    agent_ids=[AgentID.EXEC, AgentID.OPS],
    knowledge="""
## Subagent Development Framework
- Spec reviewer for requirements clarity
- Implementer for code generation
- Code quality reviewer for standards
- Test writer for coverage
- Documentation generator
- Integration coordinator
""",
)

systematic_debugging = Skill(
    name="systematic_debugging",
    description="Debug issues systematically with structured approaches.",
    category="development",
    agent_ids=[AgentID.OPS, AgentID.DATA],
    knowledge="""
## Systematic Debugging Framework
- Root cause tracing methodology
- Condition-based waiting patterns
- Defense in depth strategies
- Isolation techniques
- Binary search debugging
- Logging and monitoring setup
""",
)

test_driven_development = Skill(
    name="test_driven_development",
    description="Implement features using TDD with red-green-refactor cycle.",
    category="development",
    agent_ids=[AgentID.OPS, AgentID.DATA],
    knowledge="""
## TDD Framework
- Write failing test first (RED)
- Write minimal code to pass (GREEN)
- Refactor while keeping tests green
- No production code without failing test
- Test one behavior at a time
- Verification checklist before completion
""",
)

using_superpowers = Skill(
    name="using_superpowers",
    description="Leverage AI agent superpowers effectively for complex tasks.",
    category="meta",
    agent_ids=[AgentID.EXEC, AgentID.OPS, AgentID.DATA],
    knowledge="""
## AI Superpower Framework
- Parallel task processing
- Comprehensive research capabilities
- Pattern recognition at scale
- Code generation and review
- Documentation synthesis
- Multi-domain expertise application
""",
)

verification_before_completion = Skill(
    name="verification_before_completion",
    description="Verify work quality before marking tasks complete.",
    category="meta",
    agent_ids=[AgentID.EXEC, AgentID.OPS, AgentID.LEGAL],
    knowledge="""
## Verification Framework
- Output quality checklist
- Edge case verification
- Documentation completeness
- Test coverage confirmation
- Stakeholder requirements match
- No assumptions without confirmation
""",
)

writing_plans = Skill(
    name="writing_plans",
    description="Create comprehensive, actionable plans for complex projects.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.EXEC, AgentID.OPS],
    knowledge="""
## Plan Writing Framework
- Goal and scope definition
- Task breakdown structure
- Dependency mapping
- Resource requirements
- Risk identification
- Timeline estimation
- Success metrics
""",
)

writing_skills = Skill(
    name="writing_skills",
    description="Create new AI skills with proper structure and documentation.",
    category="meta",
    agent_ids=[AgentID.EXEC, AgentID.CONT],
    knowledge="""
## Skill Writing Framework
- Clear trigger conditions (when to use)
- Comprehensive knowledge base
- Example-driven documentation
- Edge case handling
- Related skills references
- Testable outputs
""",
)


# =============================================================================
# UI/UX & Frontend Skills (from various sources)
# =============================================================================

frontend_design = Skill(
    name="frontend_design",
    description="Design frontend interfaces with modern best practices.",
    category="design",
    agent_ids=[AgentID.CONT, AgentID.MKT, AgentID.OPS],
    knowledge="""
## Frontend Design Framework
- Component-based architecture
- Responsive design patterns
- Accessibility (WCAG) compliance
- Performance optimization
- Design system integration
- Animation and microinteractions
""",
)

react_native_best_practices = Skill(
    name="react_native_best_practices",
    description="Build React Native apps following best practices.",
    category="development",
    agent_ids=[AgentID.OPS, AgentID.DATA],
    knowledge="""
## React Native Best Practices
- Navigation patterns
- State management approaches
- Performance optimization
- Native module integration
- Testing strategies
- Release and deployment
""",
)

ui_ux_pro_max = Skill(
    name="ui_ux_pro_max",
    description="Design exceptional user interfaces and experiences.",
    category="design",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## UI/UX Pro Framework
- User research methodologies
- Information architecture
- Interaction design patterns
- Visual hierarchy principles
- Usability testing
- Design system development
- Accessibility standards
""",
)

vercel_react_best_practices = Skill(
    name="vercel_react_best_practices",
    description="Build React applications following Vercel's best practices.",
    category="development",
    agent_ids=[AgentID.OPS, AgentID.DATA],
    knowledge="""
## Vercel React Best Practices
- Server components usage
- App Router patterns
- Edge runtime optimization
- Image optimization
- Font optimization
- API routes design
- Caching strategies
""",
)

web_design_guidelines = Skill(
    name="web_design_guidelines",
    description="Apply web design guidelines for professional results.",
    category="design",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Web Design Guidelines
- Grid systems and layout
- Typography best practices
- Color theory application
- White space usage
- Visual consistency
- Brand alignment
- Mobile-first design
""",
)


# =============================================================================
# Document & Content Creation Skills (from Anthropics/Baoyu)
# =============================================================================

xlsx = Skill(
    name="xlsx",
    description="Create, read, and manipulate Excel spreadsheets.",
    category="document",
    agent_ids=[AgentID.EXEC, AgentID.CONT, AgentID.DATA, AgentID.FIN],
    knowledge="""
## Excel Skill Capabilities
- Create new .xlsx workbooks with multiple sheets
- Read and analyze existing spreadsheets
- Apply formulas and functions
- Format cells and ranges
- Create charts and visualizations
""",
)

docx = Skill(
    name="docx",
    description="Create, read, and edit Word documents.",
    category="document",
    agent_ids=[AgentID.EXEC, AgentID.CONT, AgentID.LEGAL, AgentID.HR],
    knowledge="""
## Word Document Skill Capabilities
- Create professional documents from templates
- Edit existing .docx files
- Manage headers, footers, and page layout
- Handle tables and images within documents
""",
)

pdf = Skill(
    name="pdf",
    description="Read, analyze, and manipulate PDF documents.",
    category="document",
    agent_ids=[AgentID.EXEC, AgentID.CONT, AgentID.LEGAL],
    knowledge="""
## PDF Skill Capabilities
- Extract text and metadata from PDFs
- Merge and split PDF files
- Analyze PDF content structure
""",
)

pptx = Skill(
    name="pptx",
    description="Create and edit PowerPoint presentations.",
    category="document",
    agent_ids=[AgentID.EXEC, AgentID.CONT, AgentID.STRAT, AgentID.SALES],
    knowledge="""
## PowerPoint Skill Capabilities
- Generate slide decks from outlines
- Apply themes and layouts
- Add images, text, and charts to slides
""",
)

doc_coauthoring = Skill(
    name="doc_coauthoring",
    description="Collaboratively author and refine documents with users.",
    category="document",
    agent_ids=[AgentID.EXEC, AgentID.CONT],
    knowledge="""
## Doc Co-Authoring Capabilities
- Iterative document refinement
- Suggesting edits and improvements
- Tracking changes and versions
- maintaining context across document sections
""",
)

html_to_pdf = Skill(
    name="html_to_pdf",
    description="Convert HTML content to high-quality PDF files.",
    category="document",
    agent_ids=[AgentID.EXEC, AgentID.CONT],
    knowledge="""
## HTML to PDF Capabilities
- Render web pages or HTML snippets to PDF
- Support for CSS styling and layout
- Handle pagination and breaks
""",
)

baoyu_article_illustrator = Skill(
    name="baoyu_article_illustrator",
    description="Generate professional illustrations for articles and content.",
    category="creative",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Article Illustrator Capabilities
- Analyze article content for visual opportunities
- Generate relevant image prompts
- Create style-consistent illustrations
""",
)

baoyu_comic = Skill(
    name="baoyu_comic",
    description="Create comic strips and visual storytelling sequences.",
    category="creative",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Comic Creation Capabilities
- Storyboard comic sequences
- Generate character consistency
- Create panel layouts and dialogue
""",
)


# Marketing & CRO Skills
skills_registry.register(analytics_tracking)
skills_registry.register(competitor_alternatives)
skills_registry.register(copy_editing)
skills_registry.register(copywriting)
skills_registry.register(email_sequence)
skills_registry.register(form_cro)
skills_registry.register(free_tool_strategy)
skills_registry.register(launch_strategy)
skills_registry.register(marketing_ideas)
skills_registry.register(marketing_psychology)
skills_registry.register(onboarding_cro)
skills_registry.register(page_cro)
skills_registry.register(paid_ads)
skills_registry.register(paywall_upgrade_cro)
skills_registry.register(popup_cro)
skills_registry.register(pricing_strategy)
skills_registry.register(programmatic_seo)
skills_registry.register(referral_program)
skills_registry.register(schema_markup)
skills_registry.register(seo_audit)
skills_registry.register(signup_flow_cro)
skills_registry.register(social_media_strategy)

# Development & Workflow Skills
skills_registry.register(brainstorming)
skills_registry.register(dispatching_parallel_agents)
skills_registry.register(executing_plans)
skills_registry.register(subagent_driven_development)
skills_registry.register(systematic_debugging)
skills_registry.register(test_driven_development)
skills_registry.register(using_superpowers)
skills_registry.register(verification_before_completion)
skills_registry.register(writing_plans)
skills_registry.register(writing_skills)

# UI/UX & Frontend Skills
skills_registry.register(frontend_design)
skills_registry.register(react_native_best_practices)
skills_registry.register(ui_ux_pro_max)
skills_registry.register(vercel_react_best_practices)
skills_registry.register(web_design_guidelines)


# Export list of all external skills for reference
EXTERNAL_SKILLS = [
    # Marketing & CRO
    analytics_tracking,
    competitor_alternatives,
    copy_editing,
    copywriting,
    email_sequence,
    form_cro,
    free_tool_strategy,
    launch_strategy,
    marketing_ideas,
    marketing_psychology,
    onboarding_cro,
    page_cro,
    paid_ads,
    paywall_upgrade_cro,
    popup_cro,
    pricing_strategy,
    programmatic_seo,
    referral_program,
    schema_markup,
    seo_audit,
    signup_flow_cro,
    social_media_strategy,
    # Development & Workflow
    brainstorming,
    dispatching_parallel_agents,
    executing_plans,
    subagent_driven_development,
    systematic_debugging,
    test_driven_development,
    using_superpowers,
    verification_before_completion,
    writing_plans,
    writing_skills,
    # UI/UX & Frontend
    frontend_design,
    react_native_best_practices,
    ui_ux_pro_max,
    vercel_react_best_practices,
    web_design_guidelines,
    # Document & Creative
    xlsx,
    docx,
    pdf,
    pptx,
    doc_coauthoring,
    html_to_pdf,
    baoyu_article_illustrator,
    baoyu_comic,
]

