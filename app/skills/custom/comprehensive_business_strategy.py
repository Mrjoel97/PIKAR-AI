# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import textwrap

from app.skills.registry import AgentID, Skill

# Define the comprehensive business strategy prompt as the skill's knowledge
COMPREHENSIVE_BUSINESS_STRATEGY_KNOWLEDGE = textwrap.dedent("""
    Act as an elite cross-functional business strategy team consisting of:
    - A McKinsey-level market analyst
    - A senior strategy consultant at Bain & Company
    - A world-class consumer research expert
    - A senior analyst at Goldman Sachs Research
    - A Harvard Business School strategy professor
    - A Fortune 500 pricing strategy consultant
    - A Chief Strategy Officer with 20+ B2B/B2C product launches
    - A top-tier customer experience (CX) strategist
    - A VP of Finance at a high-growth startup
    - A risk management partner at Deloitte
    - A global expansion strategist who has entered 30+ new markets

    The user needs a comprehensive, end-to-end business strategy, financial model, and operational playbook for their business.

    Please provide a detailed report structured into the following 11 sections. Format this as an executive briefing using clear headings, bold text, bullet points, and comparison tables where appropriate.

    Section 1: Market Sizing & TAM Analysis
    - Top-down approach: Start from the global market and narrow down to the specific segment.
    - Bottom-up approach: Calculate from unit economics × potential customers.
    - TAM, SAM, SOM breakdown: Provide specific dollar figures for Total Addressable Market, Serviceable Available Market, and Serviceable Obtainable Market.
    - Growth rate projections: Provide the Compound Annual Growth Rate (CAGR) for the next 5 years.
    - Key assumptions: List the critical assumptions behind each estimate.
    - Comparison: Compare findings to 3 analyst reports or market research firms.
    - Format: Present as an investor-ready market sizing slide with clear methodology.

    Section 2: Competitive Landscape Deep Dive
    - Direct competitors: Top 10 players ranked by market share, revenue, and funding.
    - Indirect competitors: 5 adjacent companies that could enter this market.
    - Competitor Analysis: For each, provide pricing model, key features, target audience, strengths, weaknesses, and recent strategic moves.
    - Market positioning map: Describe a price vs. value matrix.
    - Competitive moats: What makes each player defensible.
    - White space analysis: Gaps no competitor is filling.
    - Threat assessment: Rate each competitor (low/medium/high).

    Section 3: Customer Persona & Segmentation
    - Build 4 detailed personas, each with: Demographics, psychographics, top 5 daily pain points, goals & aspirations, buying behavior, media consumption, top 3 objections, trigger events, and willingness to pay (price sensitivity).
    - Provide segment sizing (% of total market) and a prioritization matrix.

    Section 4: Industry Trend Analysis
    - Macro trends: 5 global forces shaping the industry (economic, regulatory, tech, social, environmental).
    - Micro trends: 7 emerging patterns from the last 12 months.
    - Tech & Regulation: Upcoming tech disruptions and regulatory policy changes.
    - Market Shifts: Consumer behavior changes and investment signals (VC, M&A, IPOs).
    - Timeline & Impact: Map trends to short (0-1yr), mid (1-3yr), and long-term (3-5yr). Provide impact ratings (1-10) and a "So what" analysis for the specific company.

    Section 5: SWOT & Porter's Five Forces
    - SWOT: 7 strengths (with evidence), 7 weaknesses (honest assessment), 7 opportunities, and 7 threats. Include Cross-analysis (Match SO strategies and WT risks).
    - Porter's Five Forces: Analyze Supplier power, Buyer power, Competitive rivalry, Threat of substitution, and Threat of new entry.
    - Rate each force (1-10) and provide an overall industry attractiveness score.

    Section 6: Pricing Strategy Analysis
    - Competitor audit: Map competitor prices, tiers, and packaging.
    - Pricing Models: Calculate a value-based pricing model and a cost-plus analysis floor price.
    - Tactics & Strategy: Estimate price elasticity, recommend psychological pricing tactics, and design 3 pricing tiers with feature allocation. Provide a discount strategy.
    - Financial Impact: Model 3 revenue scenarios (aggressive, moderate, conservative) and list monetization opportunities (upsells, cross-sells). Include specific dollar recommendations.

    Section 7: Go-To-Market (GTM) Strategy
    - Launch phasing: Pre-launch (60 days), Launch (week 1), Post-launch (90 days).
    - Channels & Budget: Rank the top 7 acquisition channels by ROI and allocate marketing budget across them.
    - Messaging & Content: Core value prop, 3 supporting messages, proof points, and full-funnel content strategy.
    - Execution: 5 strategic partnership opportunities, 10 KPI metrics with benchmarks, top 5 launch risks + contingencies, and 3 "quick wins" for traction in the first 14 days. Format as a playbook with timelines/owners.

    Section 8: Customer Journey Mapping
    - Map the full lifecycle: Awareness, Consideration, Decision, Onboarding (first 7 days), Engagement, Loyalty, and Churn.
    - For each stage, provide: Customer actions/thoughts/emotions, digital/physical touchpoints, pain points, delight opportunities, key metrics, and recommended optimization tools.
    - Describe an emotional curve visualization in the text.

    Section 9: Financial Modeling & Unit Economics
    - Unit Economics: CAC by channel, LTV calculation with assumptions, LTV:CAC ratio, payback period, gross margin, and contribution margin.
    - 3-Year Projection: Revenue model (monthly yr 1, quarterly yrs 2-3), fixed vs. variable costs, break-even analysis (when/volume), cash flow forecast with burn rate, and sensitivity analysis.
    - Provide a key assumptions table with justifications, benchmark comparisons, and "Red flags" that should trigger action.

    Section 10: Risk Assessment & Scenario Planning
    - Risk Identification: List 15 risks across Market, Operational, Financial, Regulatory, and Reputational categories.
    - Risk Matrix: For each risk, provide probability (1-5), impact (1-5), Risk Score (prob × impact), early warning indicators, mitigation strategies, and contingencies.
    - Scenario Planning: Outline Best case, Base case, Worst case, and Black Swan scenarios. Include revenue impact, timeline, and strategic response for each. Format with a prioritized risk matrix.

    Section 11: Market Entry & Expansion Strategy
    - Attractiveness Scoring: Score (1-10) market size/growth, competitive intensity, regulatory environment, accessibility, and infrastructure readiness with a weighted total.
    - Entry Mode: Recommend between direct entry, partnership/JV, acquisition, licensing, or digital-first (include pros, cons, costs, timeline).
    - Localization: Product adaptations, local pricing, cultural marketing, legal compliance, and talent needs.
    - Execution: 12-month month-by-month roadmap, budget estimate, and KPIs for 6 and 12 months.

    PACING INSTRUCTION: Because this request is extremely comprehensive, please DO NOT generate the entire response at once. Start by asking the user if they are ready, and then generate only Section 1. Wait for their approval ("Continue"), then generate Section 2, and so on, until all 11 sections are complete.
""").strip()

# Create the Skill instance format required by the registry
comprehensive_business_strategy_skill = Skill(
    name="comprehensive_business_strategy",
    description="Generates an end-to-end business strategy, financial model, and operational playbook across 11 detailed sections, paced section-by-section upon user approval.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.EXEC],
    knowledge=COMPREHENSIVE_BUSINESS_STRATEGY_KNOWLEDGE,
)
