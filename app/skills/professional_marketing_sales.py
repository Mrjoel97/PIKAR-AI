# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Professional Marketing & Sales Skills Library.

High-fidelity, actionable skills for Marketing and Sales agents covering
campaign planning, email sequences, performance reporting, competitive
analysis, SEO audits, account research, outreach, call prep, pipeline
management, forecasting, battlecards, and sales asset creation.
"""

from app.skills.registry import AgentID, Skill, skills_registry

# =============================================================================
# MARKETING SKILLS
# =============================================================================

campaign_planning = Skill(
    name="campaign_planning",
    description="End-to-end campaign brief creation covering objectives, audience, messaging, channels, budget, and measurement.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.STRAT],
    knowledge_summary=(
        "Full campaign brief framework: SMART objectives by funnel stage, audience segmentation "
        "(demographics, psychographics, behavioral, lookalike), messaging hierarchy, channel strategy "
        "matrix (owned/earned/paid), 70/20/10 budget allocation, and measurement plan with attribution."
    ),
    knowledge="""
## Campaign Planning Framework

### 1. Campaign Objectives by Funnel Stage

| Stage | Objective | Example KPIs |
|-------|-----------|-------------|
| Awareness | Increase brand visibility | Impressions, reach, share of voice |
| Consideration | Drive engagement and education | CTR, time on site, content downloads |
| Conversion | Generate leads/sales | Conversion rate, CPA, ROAS |
| Retention | Increase loyalty and LTV | Repeat purchase rate, NPS, churn reduction |

### 2. SMART Goal Setting
- **Specific:** "Increase marketing-qualified leads from paid social" not "get more leads"
- **Measurable:** Attach a number — "by 25%"
- **Achievable:** Based on historical benchmarks and budget
- **Relevant:** Tied to business objective (revenue, pipeline)
- **Time-bound:** "Within Q3 2025"

**Template:** "Increase [metric] from [baseline] to [target] by [date] through [channel/tactic]."

### 3. Audience Definition

**Demographics:** Age, gender, income, education, job title, company size, industry, geography.

**Psychographics:** Values, interests, attitudes, lifestyle, motivations, pain points, aspirations.

**Behavioral Segments:**
- Purchase history (frequency, recency, AOV)
- Content engagement (topics, formats, channels)
- Product usage (features used, login frequency)
- Intent signals (search queries, competitor visits)

**Lookalike Criteria:**
- Seed audience: top 10% customers by LTV
- Match rate target: 1-3% for precision, 5-10% for reach
- Refresh cadence: monthly

### 4. Messaging Framework

**Key Message:** Single sentence that captures the core value proposition.

**Supporting Points (3 max):**
1. Functional benefit + proof point
2. Emotional benefit + proof point
3. Differentiator + proof point

**CTA Hierarchy:**
- Primary CTA: The one action you most want (e.g., "Start Free Trial")
- Secondary CTA: Lower commitment (e.g., "Watch Demo")
- Tertiary CTA: Passive engagement (e.g., "Learn More")

**Message Testing Matrix:**
| Variant | Hook | Value Prop | CTA | Test Priority |
|---------|------|-----------|-----|--------------|
| A | Pain point | Feature-led | Direct | High |
| B | Outcome | Benefit-led | Soft | High |
| C | Social proof | Comparison | Urgency | Medium |

### 5. Channel Strategy Matrix

|  | Top of Funnel | Mid Funnel | Bottom Funnel |
|--|--------------|-----------|--------------|
| **Owned** | Blog, SEO, social organic | Email nurture, webinars | Product pages, case studies |
| **Earned** | PR, influencer, guest posts | Reviews, community, UGC | Testimonials, referrals |
| **Paid** | Display, social ads, video | Retargeting, sponsored content | Search ads, remarketing |

**Channel Selection Criteria:**
- Where does our audience spend time? (reach)
- What is the cost to reach them? (efficiency)
- Can we measure outcomes? (attribution)
- Do we have creative assets for this channel? (feasibility)

### 6. Content Calendar Template

| Week | Channel | Content Type | Topic | Owner | Status | CTA |
|------|---------|-------------|-------|-------|--------|-----|
| W1 | Blog | Thought leadership | Problem awareness | Content | Draft | Learn More |
| W1 | LinkedIn | Carousel | Key stats | Social | Scheduled | Download |
| W2 | Email | Nurture #1 | Pain + solution | Email | In Review | Watch Demo |
| W2 | Paid Social | Video ad | Customer story | Paid | Creative | Free Trial |
| W3 | Webinar | Live event | Deep dive | Events | Confirmed | Register |
| W4 | Email | Nurture #2 | Case study | Email | Planned | Book Call |

### 7. Budget Allocation — 70/20/10 Rule

- **70% Proven:** Channels/tactics with demonstrated ROI (search ads, email, SEO)
- **20% Promising:** Emerging tactics with early positive signals (new social platform, ABM)
- **10% Experimental:** Unproven but high-potential (AI personalization, new format, partnership)

**Budget Template:**
| Channel | Allocation % | Monthly Budget | Expected CPA | Expected Leads |
|---------|-------------|---------------|-------------|---------------|
| Paid Search | 30% | $X | $Y | Z |
| Paid Social | 25% | $X | $Y | Z |
| Content/SEO | 15% | $X | $Y | Z |
| Email | 10% | $X | $Y | Z |
| Events | 10% | $X | $Y | Z |
| Experimental | 10% | $X | $Y | Z |

### 8. Measurement Plan

**KPIs per Channel:**
- Paid Search: CPC, CTR, conversion rate, CPA, ROAS
- Paid Social: CPM, CTR, engagement rate, CPA, ROAS
- Email: Open rate, click rate, conversion rate, unsubscribe rate
- Content/SEO: Organic traffic, keyword rankings, time on page, conversions
- Events: Registrations, attendance rate, pipeline generated

**Attribution Model Selection:**
- First-touch: Best for awareness campaigns
- Last-touch: Best for conversion optimization
- Linear: Best for balanced multi-channel
- Time-decay: Best for long sales cycles
- Position-based (U-shaped): Best for B2B with clear first/last touchpoints

**Reporting Cadence:**
- Weekly: Channel metrics, spend pacing, quick wins/flags
- Monthly: Full funnel analysis, budget reallocation, creative refresh needs
- Quarterly: Strategic review, goal progress, next quarter planning

### 9. Launch Checklist
- [ ] Campaign brief approved by stakeholders
- [ ] Creative assets produced and approved
- [ ] Landing pages live and tested (mobile + desktop)
- [ ] Tracking pixels and UTM parameters configured
- [ ] Email sequences built and tested (deliverability check)
- [ ] Ad accounts funded and campaigns in review
- [ ] Analytics dashboards configured
- [ ] Team roles and escalation path confirmed
- [ ] Launch comms sent to internal stakeholders
- [ ] Day-1 monitoring plan in place

### 10. Post-Campaign Analysis Template
1. **Executive Summary:** One paragraph — did we hit our goal?
2. **Goal vs. Actual:** Table comparing targets to results
3. **Channel Performance:** What worked, what didn't, why
4. **Audience Insights:** Who responded best, surprises
5. **Creative Insights:** Top-performing assets and messaging
6. **Budget Efficiency:** CPA, ROAS, spend vs. plan
7. **Lessons Learned:** 3 things to repeat, 3 things to change
8. **Recommendations:** Next campaign adjustments
""",
)

email_sequence_design = Skill(
    name="email_sequence_design",
    description="Multi-email sequence architecture covering welcome, nurture, onboarding, re-engagement, and abandonment flows.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.SALES, AgentID.CONT],
    knowledge_summary=(
        "Email sequence design patterns for 7 sequence types with entry triggers, cadence timing, "
        "branching logic, A/B testing methodology, deliverability best practices (SPF/DKIM/DMARC), "
        "and industry benchmarks. Includes full 5-email welcome sequence example."
    ),
    knowledge="""
## Email Sequence Design Framework

### 1. Sequence Types and When to Use

| Sequence | Trigger | Goal | Typical Length |
|----------|---------|------|---------------|
| Welcome | New subscriber/signup | Build relationship, set expectations | 3-7 emails over 2 weeks |
| Nurture | Lead enters pipeline | Educate, build trust, move to MQL | 5-12 emails over 4-8 weeks |
| Onboarding | Product signup/purchase | Drive activation, reduce churn | 5-10 emails over 30 days |
| Re-engagement | Inactive 30-90 days | Win back or clean list | 3-5 emails over 2-3 weeks |
| Abandonment | Cart/form abandoned | Recover conversion | 3 emails over 3-5 days |
| Post-purchase | Purchase complete | Upsell, loyalty, review | 4-6 emails over 30 days |
| Event | Webinar/event registration | Drive attendance and follow-up | 4-6 emails: pre, during, post |

### 2. Sequence Architecture

**Entry Trigger:** The specific event that enrolls a contact (form submit, tag added, behavior).

**Email Cadence/Timing:**
- Welcome: Email 1 immediately, then every 2-3 days
- Nurture: Every 3-5 days (avoid fatigue)
- Abandonment: 1 hour, 24 hours, 72 hours after event
- Re-engagement: Day 1, Day 5, Day 10, Day 14 (final)

**Branching Logic:**
- Opened email 2? -> Send case study (Email 3A)
- Did NOT open email 2? -> Resend with new subject (Email 2B)
- Clicked CTA? -> Skip to conversion email
- Visited pricing page? -> Trigger sales handoff

**Exit Conditions:**
- Converted (purchased, booked demo, etc.)
- Unsubscribed
- Bounced (hard bounce = immediate remove)
- Completed all emails in sequence
- Moved to another sequence (priority rules)

### 3. Email Framework per Position

**Email 1 — Welcome/Introduction:**
- Subject: Personalized, sets expectation ("Welcome to [Brand] — here's what's next")
- Body: Thank them, deliver promised value, set expectations, single CTA
- CTA: Lowest friction action (complete profile, read guide)

**Email 2 — Value Delivery:**
- Subject: Benefit-focused ("The #1 mistake [audience] make with [topic]")
- Body: Educational content, establish expertise, subtle product mention
- CTA: Content engagement (read, watch, download)

**Email 3 — Social Proof:**
- Subject: Story-driven ("How [customer] achieved [result]")
- Body: Case study or testimonial, relatable pain point, measurable outcome
- CTA: See more stories or start trial

**Email 4 — Differentiation:**
- Subject: Comparison or unique angle ("Why [approach] beats [alternative]")
- Body: Position against alternatives, address objections preemptively
- CTA: Book demo or start trial

**Email 5 — Conversion Push:**
- Subject: Urgency or direct ask ("Ready to [achieve outcome]?")
- Body: Summarize value, overcome final objections, strong CTA
- CTA: Primary conversion action with deadline or incentive

### 4. Subject Line Formulas
- **How-to:** "How to [achieve outcome] in [timeframe]"
- **Number:** "[X] ways to [solve problem]"
- **Question:** "Are you making this [topic] mistake?"
- **Personal:** "[Name], your [item] is waiting"
- **Curiosity:** "The [topic] secret most [audience] miss"
- **Social proof:** "[X] companies switched to [solution] this month"
- **Urgency:** "Last chance: [offer] ends [date]"

### 5. Personalization Variables
- **Basic:** First name, company name, industry
- **Behavioral:** Last page visited, content downloaded, product used
- **Contextual:** Industry benchmarks, company size tier, role-specific pain
- **Dynamic:** Recommended content based on engagement history

### 6. A/B Testing Methodology
- **Subject Line:** Test 2 variants to 20% of list, send winner to 80%
- **Send Time:** Test morning vs. afternoon, weekday vs. weekend
- **CTA:** Button text, color, placement (above fold vs. end)
- **Content Length:** Short (< 100 words) vs. long (300+ words)
- **Statistical significance:** Minimum 1,000 recipients per variant, 95% confidence

### 7. Deliverability Best Practices
- **Warm-up:** New domain/IP: start with 50-100/day, increase 20% daily over 4-6 weeks
- **List Hygiene:** Remove hard bounces immediately, soft bounces after 3 attempts, inactive > 6 months
- **Authentication:** SPF (authorize sending IPs), DKIM (sign emails cryptographically), DMARC (policy for failures)
- **Content:** Avoid spam trigger words, maintain text-to-image ratio > 60:40, include plain-text version
- **Infrastructure:** Dedicated sending domain, proper reverse DNS, feedback loop registration

### 8. Performance Benchmarks by Industry

| Industry | Open Rate | Click Rate | Unsubscribe |
|----------|-----------|-----------|-------------|
| SaaS/Tech | 20-25% | 2-3% | < 0.5% |
| E-commerce | 15-20% | 2-3% | < 0.3% |
| Professional Services | 22-28% | 3-4% | < 0.3% |
| Education | 25-30% | 3-5% | < 0.2% |
| Healthcare | 22-26% | 3-4% | < 0.3% |

### 9. Example: 5-Email Welcome Sequence

**Email 1 (Immediately):** "Welcome to [Brand]!"
- Deliver lead magnet / confirm signup
- Set expectations (what they'll receive, how often)
- CTA: Complete profile or quick win action

**Email 2 (Day 2):** "Start here: [Quick Win]"
- Actionable tip they can implement today
- Establish expertise and helpfulness
- CTA: Read the full guide

**Email 3 (Day 5):** "How [Customer] achieved [Result]"
- Customer story with specific metrics
- Connect their pain to the solution
- CTA: See how it works (demo/trial)

**Email 4 (Day 8):** "[X] things I wish I knew about [Topic]"
- Educational, personality-driven content
- Address common misconceptions
- CTA: Download resource or join community

**Email 5 (Day 12):** "Ready to [Outcome]?"
- Recap value delivered in sequence
- Clear next step with incentive if appropriate
- CTA: Start trial / book call / purchase
""",
)

marketing_performance_report = Skill(
    name="marketing_performance_report",
    description="Marketing performance reporting with executive dashboards, funnel analysis, attribution, and action frameworks.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.DATA, AgentID.EXEC],
    knowledge_summary=(
        "Marketing reporting framework covering executive metrics (CAC, LTV, ROAS), channel performance, "
        "full-funnel conversion analysis, attribution model selection, and narrative structure (wins, misses, "
        "priorities) with weekly/monthly/quarterly cadence."
    ),
    knowledge="""
## Marketing Performance Reporting Framework

### 1. Executive Dashboard Metrics

| Metric | Formula | Benchmark | Frequency |
|--------|---------|-----------|-----------|
| CAC | Total Marketing Spend / New Customers | Varies by industry | Monthly |
| LTV | Avg Revenue per Customer x Avg Lifespan | 3-5x CAC | Quarterly |
| LTV:CAC Ratio | LTV / CAC | > 3:1 healthy, > 5:1 may be under-investing | Quarterly |
| ROAS | Revenue from Ads / Ad Spend | > 4:1 for most channels | Weekly |
| Pipeline Contribution | Marketing-Sourced Pipeline / Total Pipeline | 40-60% | Monthly |
| Marketing-Sourced Revenue | Closed-won from marketing leads | Track trend | Monthly |

### 2. Channel Performance Framework

**Per-Channel Metrics Table:**
| Channel | Impressions | Clicks | CTR | Conversions | CPA | ROAS | Trend |
|---------|------------|--------|-----|-------------|-----|------|-------|
| Paid Search | | | | | | | |
| Paid Social | | | | | | | |
| Organic Search | | | | | | | |
| Email | | | | | | | |
| Direct | | | | | | | |
| Referral | | | | | | | |

**Channel Health Scoring:** Rate each channel 1-5 on efficiency (CPA vs target), scale (volume of conversions), trend (improving/declining), and strategic fit.

### 3. Funnel Analysis

**Full Funnel Conversion:**
| Stage | Volume | Conversion Rate | Benchmark | Status |
|-------|--------|----------------|-----------|--------|
| Visitors | X | - | - | - |
| Leads (MQL) | X | Visit-to-Lead: Y% | 2-5% | |
| SQL | X | MQL-to-SQL: Y% | 20-30% | |
| Opportunity | X | SQL-to-Opp: Y% | 50-60% | |
| Closed Won | X | Opp-to-Close: Y% | 20-30% | |

**Leak Detection:** Identify the stage with the largest drop-off. If MQL-to-SQL is below 20%, investigate lead quality or sales follow-up speed.

### 4. Trend Analysis Methodology
- **WoW (Week-over-Week):** Operational — catch issues early
- **MoM (Month-over-Month):** Tactical — are campaigns improving?
- **QoQ (Quarter-over-Quarter):** Strategic — are we trending toward goals?
- **YoY (Year-over-Year):** Contextual — account for seasonality

**Seasonality Notes:** Always compare same period YoY. Flag holiday weeks, industry events, budget cycles. Include a "seasonality adjusted" view when presenting QoQ.

### 5. Cohort Analysis for Campaign Effectiveness
- Group customers by acquisition month and campaign source
- Track cohort revenue over 3, 6, 12 months
- Identify which campaigns produce highest LTV customers (not just lowest CAC)
- Use cohort data to reallocate budget toward quality-producing channels

### 6. Attribution Models

| Model | How It Works | Best For |
|-------|-------------|---------|
| First-Touch | 100% credit to first interaction | Measuring awareness channels |
| Last-Touch | 100% credit to final interaction | Measuring conversion channels |
| Linear | Equal credit across all touchpoints | Balanced view, simple analysis |
| Time-Decay | More credit to recent touchpoints | Long sales cycles |
| Position-Based | 40% first, 40% last, 20% middle | B2B with clear entry and conversion |

**Recommendation:** Use position-based as primary model for B2B. Run first-touch in parallel to evaluate top-of-funnel investments.

### 7. Narrative Structure: Wins, Misses, Priorities

**Section 1 — Wins (What Worked):**
- Top 3 successes with data
- Why they worked (insight, not just result)
- How to scale them

**Section 2 — Misses (What Didn't Work):**
- Top 3 underperformers with data
- Root cause analysis (creative fatigue? wrong audience? timing?)
- Decision: iterate, pause, or kill

**Section 3 — Priorities (What's Next):**
- Top 3 action items ranked by impact
- Owner and deadline for each
- Resource needs or dependencies

### 8. Action Item Framework
- **Double Down:** Channels/campaigns beating targets — increase budget 20-30%
- **Pause:** Channels below 50% of target for 2+ weeks — reallocate budget
- **Test Next:** One new channel, creative, or audience per reporting cycle

### 9. Reporting Cadence

**Weekly Pulse (15 min review):**
- Spend pacing vs. budget
- Top-line leads and conversion
- Any alerts or anomalies
- One action item

**Monthly Deep-Dive (60 min review):**
- Full funnel analysis
- Channel performance with trends
- Creative performance review
- Budget reallocation decisions
- Next month priorities

**Quarterly Strategic Review (90 min):**
- Goal progress and forecast
- LTV:CAC and unit economics
- Competitive landscape shifts
- Strategic adjustments for next quarter
- Budget and headcount planning
""",
)

competitive_brief_generation = Skill(
    name="competitive_brief_generation",
    description="Competitive analysis brief creation with SWOT, positioning maps, messaging differentiation, and sales battlecard format.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.SALES, AgentID.STRAT],
    knowledge_summary=(
        "Competitive intelligence framework covering competitor identification (direct/indirect/aspirational), "
        "information gathering (product, pricing, positioning, content, SEO), SWOT analysis, 2x2 positioning "
        "maps, messaging differentiation, and sales battlecard format with quarterly refresh cadence."
    ),
    knowledge="""
## Competitive Analysis Brief Framework

### 1. Competitor Identification

**Direct Competitors:** Same product, same market, same customer. They show up in your deals.
**Indirect Competitors:** Different product solving the same problem. Customers consider them as alternatives.
**Aspirational Competitors:** Market leaders you benchmark against for positioning and features.

**Identification Methods:**
- Sales team feedback: "Who do we see in deals?"
- Customer interviews: "What else did you evaluate?"
- Search: Who ranks for your target keywords?
- Review sites: G2, Capterra, TrustRadius — who's in your category?
- Job postings: Who is hiring for your market?

### 2. Information Gathering Framework

**Product Comparison Matrix:**
| Feature | Us | Competitor A | Competitor B |
|---------|------|-------------|-------------|
| Feature 1 | Strong | Strong | Weak |
| Feature 2 | Moderate | Weak | Strong |
| Feature 3 | Unique | None | Partial |

Rating: Strong / Moderate / Weak / None / Unique

**Pricing Analysis:**
- Pricing model (per user, per usage, flat, tiered, freemium)
- Entry price, mid-market price, enterprise price
- Contract terms (monthly, annual, multi-year discounts)
- Free trial or freemium availability
- Known discounting patterns

**Positioning Map:**
- How they describe themselves (tagline, homepage headline, boilerplate)
- Target audience messaging (who they say they're for)
- Key differentiators they claim
- Brand tone and personality

**Messaging Audit:**
- Homepage value proposition
- Key benefit claims
- Social proof used (customer logos, metrics, testimonials)
- Content themes on blog and social

**Content Strategy Analysis:**
- Blog frequency and topics
- Content formats (blog, video, podcast, webinar)
- SEO keyword focus areas
- Social media channels and engagement levels
- Gated vs. ungated content strategy

**SEO Overlap Analysis:**
- Shared keywords and ranking positions
- Keywords they rank for that we don't (content gaps)
- Backlink overlap and unique referring domains
- Domain authority comparison

**Technology Stack:**
- Built-with analysis (BuiltWith, Wappalyzer)
- Integration ecosystem
- API availability and documentation quality

### 3. SWOT per Competitor

| | Positive | Negative |
|--|---------|---------|
| **Internal** | **Strengths:** What they do well, advantages, resources | **Weaknesses:** Gaps, limitations, complaints |
| **External** | **Opportunities:** Market trends in their favor, expansion paths | **Threats:** Our advantages, market shifts against them |

**Sources for SWOT Data:**
- Strengths: Their marketing, G2 reviews (positive)
- Weaknesses: G2 reviews (negative), support forums, social complaints
- Opportunities: Industry reports, their job postings, investor materials
- Threats: Our roadmap, regulatory changes, market consolidation

### 4. Competitive Positioning Map (2x2 Matrix)

**Choosing Axes:**
Pick two dimensions that matter most to buyers and where you differentiate:
- Ease of Use vs. Feature Depth
- SMB Focus vs. Enterprise Focus
- Price vs. Capability
- Specialist vs. Platform
- Self-Serve vs. High-Touch

**Plotting:** Place each competitor on the map. Identify whitespace (unoccupied quadrants = opportunity).

### 5. Messaging Differentiation Framework

**Where We Win:** List 3-5 areas with proof points (benchmarks, testimonials, features).
- "We win on [X] because [evidence]. Use this when prospect cares about [scenario]."

**Where We Lose:** List 2-3 areas with mitigation.
- "We lose on [X] because [gap]. Mitigate by [reframing, roadmap, workaround]."

**Where It's a Tie:** List 2-3 areas with differentiation opportunities.
- "Both products offer [X]. Differentiate by [unique angle, better support, integration]."

### 6. Content Gap Analysis
- Topics competitors cover that we don't (opportunity for new content)
- Topics we cover better (amplify and promote)
- Keywords they rank for that we don't target
- Content formats they use that we haven't tried

### 7. Sales Battlecard Format

**Quick Facts:**
- Founded: [year] | HQ: [city] | Employees: [count] | Funding: [amount]
- Revenue estimate: [range] | Key customers: [logos]

**Strengths to Acknowledge:**
"Yes, they're strong at [X]. However, our approach to [X] means [differentiator]."

**Weaknesses to Exploit:**
"Ask the prospect about [pain point] — this is where [Competitor] consistently falls short."

**Landmines to Set:**
Questions that plant seeds of doubt about the competitor:
- "Have you asked them about [specific limitation]?"
- "What's their approach to [area where they're weak]?"
- "How does their pricing scale as you grow?"

**Traps to Avoid:**
Topics where the competitor is stronger — don't bring these up:
- "[Topic] — if the prospect asks, pivot to [our strength]."

**Knockout Questions:**
Questions that end competitive evaluations in our favor:
- "Can you show me how [Competitor] handles [our unique capability]?"

### 8. Update Cadence
- **Quarterly Refresh:** Full competitive brief update with fresh data
- **Event-Triggered Updates:** Competitor product launch, pricing change, funding round, acquisition, key executive change, major customer win/loss
- **Living Battlecard:** Sales team can flag inaccuracies in real-time for immediate correction
""",
)

brand_voice_review = Skill(
    name="brand_voice_review",
    description="Content compliance review against brand voice guidelines with scoring rubric and feedback templates.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.CONT],
    knowledge_summary=(
        "Brand voice compliance framework with voice dimensions (tone, humor, formality, enthusiasm), "
        "consistency checklist, 1-5 scoring rubric across 5 criteria, common deviation patterns, "
        "style guide enforcement rules, and escalation criteria for publication blocking."
    ),
    knowledge="""
## Brand Voice Review Framework

### 1. Brand Voice Dimensions

Define your brand's position on each spectrum:

| Dimension | Scale | Example Position |
|-----------|-------|-----------------|
| Tone | Formal -------- Casual | 3/5 (professional but approachable) |
| Humor | Serious -------- Playful | 2/5 (occasional wit, never slapstick) |
| Formality | Academic -------- Conversational | 3.5/5 (clear, not stiff) |
| Enthusiasm | Reserved -------- Excited | 3/5 (confident, not hyperbolic) |
| Authority | Peer -------- Expert | 4/5 (knowledgeable, not condescending) |

**Voice Statement Template:** "We sound like a [role] who is [adjective], [adjective], and [adjective]. We never sound [adjective] or [adjective]."

Example: "We sound like a trusted advisor who is confident, clear, and helpful. We never sound corporate or condescending."

### 2. Voice Consistency Checklist

**Vocabulary Alignment:**
- [ ] Uses approved terminology (check glossary)
- [ ] Industry jargon used appropriately for audience
- [ ] Acronyms spelled out on first use
- [ ] Product names match official capitalization and spelling

**Banned Words/Phrases:**
- Hyperbolic: "revolutionary", "game-changing", "world-class", "best-in-class"
- Jargon without context: "synergy", "paradigm shift", "leverage" (as verb)
- Hedging: "arguably", "it could be said", "some might say"
- Cliches: "at the end of the day", "move the needle", "low-hanging fruit"

**Required Disclaimers:**
- Forward-looking statements: financial projections, product roadmap
- Regulatory: healthcare, financial, legal content
- Data claims: source and date required for all statistics

**Trademark Usage:**
- Company name: always [Brand] with proper capitalization
- Product names: per trademark guide
- Competitor names: use official name, no disparagement

**Competitor Mention Policy:**
- Never mention by name in ads or promotional content
- In comparison content: factual, sourced, fair
- When referenced: use "other solutions" or "alternatives" in most contexts

### 3. Review Rubric (1-5 Scoring)

| Criteria | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) |
|----------|----------|----------------|---------------|
| Voice Match | Unrecognizable as our brand | Mostly on-brand with minor slips | Perfectly captures our voice |
| Clarity | Confusing, unclear structure | Clear main point, some rough spots | Crystal clear, scannable, logical |
| Audience Fit | Wrong tone for target reader | Generally appropriate | Precisely calibrated for audience |
| Brand Alignment | Conflicts with brand values | Neutral, doesn't conflict | Reinforces and embodies brand |
| CTA Effectiveness | No clear action, or misleading | CTA present but could be stronger | Compelling, clear, well-placed CTA |

**Scoring Guide:**
- 25/25: Publish immediately
- 20-24: Minor edits, publish same day
- 15-19: Moderate revision needed, 1-2 day turnaround
- 10-14: Major rewrite required
- Below 10: Reject and reassign

### 4. Common Deviations and Corrections

**Too Formal:**
- Before: "We would like to inform you that our platform has been updated."
- After: "We've updated the platform — here's what's new."

**Too Casual:**
- Before: "Hey! So we just dropped this crazy cool feature!"
- After: "We just launched a new feature we think you'll love."

**Too Salesy:**
- Before: "Don't miss this incredible, limited-time opportunity!"
- After: "This offer is available through [date]."

**Too Vague:**
- Before: "Our solution helps businesses grow."
- After: "Our platform helped [Customer] increase pipeline by 40% in 6 months."

**Inconsistent Tense/Person:**
- Before: "Users can set up their dashboard. You will then see..."
- After: "You can set up your dashboard. You'll then see..."

### 5. Style Guide Enforcement

**AP Style vs. Chicago (pick one and enforce):**
- Numbers: Spell out one through nine (AP) or one through one hundred (Chicago)
- Dates: March 15, 2025 (no ordinal: not "March 15th")
- Time: 3 p.m. (AP) or 3:00 PM (house style)
- Titles: capitalize principal words in headlines

**Number Formatting:**
- Below 10: spell out ("five features")
- 10 and above: numerals ("15 customers")
- Always numeral for: percentages (5%), money ($3), measurements, data points

**Capitalization Rules:**
- Product features: Title Case when proper noun, lowercase when generic
- Headlines: Title Case for H1, sentence case for H2+
- Buttons/CTAs: Title Case

**Punctuation Preferences:**
- Serial comma: Yes (red, white, and blue)
- Em dash: with spaces ( — ) or without (—) — pick one
- Exclamation marks: maximum one per piece (ideally zero)
- Ellipsis: avoid in professional content

### 6. Feedback Template for Content Creators

**Overall Score: [X/25]**

**Strengths:**
- [What the piece does well — be specific]

**Areas for Improvement:**
- [Specific issue #1]: [Example from text] -> [Suggested revision]
- [Specific issue #2]: [Example from text] -> [Suggested revision]

**Priority Fixes (must address before publish):**
1. [Critical fix]

**Nice-to-Have (if time allows):**
1. [Enhancement suggestion]

### 7. Escalation Criteria

**Block Publication When:**
- Brand voice score below 15/25
- Contains banned words or unapproved claims
- Missing required disclaimers
- Incorrect product naming or trademark usage
- Disparaging competitor mention
- Unverified statistics or data claims
- Tone inappropriate for channel or audience (e.g., casual tone in legal content)

**Escalation Path:**
Content Creator -> Brand Manager -> Marketing Director -> Legal (if compliance issue)
""",
)

seo_audit_comprehensive = Skill(
    name="seo_audit_comprehensive",
    description="Comprehensive SEO audit covering technical, on-page, content, off-page analysis and prioritized action plans.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.CONT, AgentID.DATA],
    knowledge_summary=(
        "Full SEO audit framework: technical (crawlability, Core Web Vitals, structured data), on-page "
        "(title tags, meta, headings, internal linking), content (gap analysis, topic clusters, freshness), "
        "off-page (backlinks, DA, toxic links), keyword research methodology, and prioritized action plan."
    ),
    knowledge="""
## Comprehensive SEO Audit Framework

### 1. Technical SEO

**Crawlability:**
- Robots.txt: correctly allows/blocks pages; no accidental disallow of important sections
- XML Sitemap: present, submitted to Search Console, all important pages included, no 404s in sitemap
- Crawl budget: check for excessive redirect chains, parameter URLs, faceted navigation bloat
- JavaScript rendering: critical content accessible without JS; test with "View Source" vs. rendered DOM

**Indexation:**
- site: search shows expected page count (significant discrepancy = indexation issue)
- Noindex tags: verify only intentionally excluded pages have noindex
- Canonical tags: self-referencing on primary pages, correct cross-domain if applicable
- Index Coverage report in Search Console: check excluded pages for errors

**Site Speed / Core Web Vitals:**
| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | < 2.5s | 2.5-4.0s | > 4.0s |
| INP (Interaction to Next Paint) | < 200ms | 200-500ms | > 500ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1-0.25 | > 0.25 |

**Speed Optimization Checklist:**
- [ ] Images: WebP/AVIF format, lazy loading, proper sizing
- [ ] CSS: critical CSS inlined, non-critical deferred
- [ ] JavaScript: minified, deferred/async, code splitting
- [ ] Server: HTTP/2 or HTTP/3, CDN, GZIP/Brotli compression
- [ ] Caching: browser cache headers, service worker for repeat visits

**Mobile-Friendliness:**
- Responsive design (not separate mobile site)
- Tap targets: minimum 48x48px with adequate spacing
- Font size: minimum 16px body text
- No horizontal scrolling
- Mobile-first indexing compliance

**Structured Data / Schema Markup:**
- Organization schema on homepage
- Article/BlogPosting on content pages
- Product schema on product pages (price, availability, reviews)
- FAQ schema where applicable
- BreadcrumbList for navigation
- Validate with Google Rich Results Test

**Other Technical:**
- HTTPS everywhere (no mixed content)
- Hreflang for multi-language/region sites
- 404 page: custom, helpful, links to key pages
- Redirect audit: minimize chains (max 1 hop), no loops, 301 for permanent

### 2. On-Page SEO

**Title Tags:**
- Length: 50-60 characters (display limit)
- Structure: Primary Keyword — Secondary Keyword | Brand
- Unique per page (no duplicates)
- Front-load keywords when natural

**Meta Descriptions:**
- Length: 150-160 characters
- Include primary keyword and CTA
- Unique per page
- Compelling (drives click-through, not just keyword stuffing)

**Heading Hierarchy (H1-H6):**
- One H1 per page containing primary keyword
- H2s for main sections (include secondary keywords)
- H3-H6 for subsections (natural hierarchy, not skipping levels)
- Headings should be descriptive, not generic ("Our Services" -> "Enterprise Cloud Migration Services")

**Keyword Optimization:**
- Primary keyword in: title, H1, first 100 words, URL, meta description
- Secondary keywords in: H2s, body content, image alt text
- Keyword density: 1-2% (natural, not forced)
- Semantic/LSI keywords: related terms and phrases throughout

**Internal Linking:**
- Every page reachable within 3 clicks from homepage
- Contextual internal links in body content (not just navigation)
- Descriptive anchor text (not "click here")
- Link to high-priority pages from high-authority pages
- Fix orphan pages (pages with no internal links pointing to them)

**Image Optimization:**
- Alt text: descriptive, includes keyword when relevant, under 125 characters
- File names: descriptive-keyword-filename.webp (not IMG_2847.jpg)
- File size: compress without visible quality loss
- Dimensions: specify width/height to prevent CLS

**URL Structure:**
- Short, descriptive, lowercase
- Include primary keyword
- Use hyphens (not underscores)
- Avoid parameters, session IDs, unnecessary folders
- Consistent pattern: /category/page-name

### 3. Content Analysis

**Content Gap Identification:**
- What topics do competitors rank for that we don't cover?
- What questions does our audience ask that we haven't answered?
- What stages of the buyer journey lack content?
- Use "People Also Ask" and "Related Searches" for expansion ideas

**Topic Cluster Mapping:**
- Pillar page: comprehensive guide on broad topic (2,000-5,000 words)
- Cluster pages: focused articles on subtopics (800-2,000 words)
- Internal links: every cluster page links to pillar and vice versa
- Example: Pillar "Email Marketing Guide" -> Clusters: "Subject Line Tips", "Segmentation", "Automation"

**Thin Content Detection:**
- Pages under 300 words with no unique value
- Decision: expand, consolidate, noindex, or remove
- Check for auto-generated or boilerplate-heavy pages

**Duplicate Content:**
- Internal: similar pages competing for same keyword (cannibalization)
- External: content scraped or syndicated without canonical
- Fix: canonical tags, consolidation, unique content creation

**Content Freshness Scoring:**
| Age | Action |
|-----|--------|
| < 6 months | No action needed |
| 6-12 months | Review for accuracy, update stats |
| 12-24 months | Significant refresh: new data, examples, sections |
| > 24 months | Full rewrite or consolidate |

### 4. Off-Page SEO

**Backlink Profile Analysis:**
- Total backlinks and referring domains (more domains > more links from few)
- Quality indicators: Domain Authority of linking sites, relevance, editorial vs. directory
- Growth trend: gaining or losing links over time?

**Domain Authority:**
- Current DA/DR score
- Compare to top 3 competitors
- DA growth rate over past 12 months

**Referring Domains:**
- Unique referring domains (more important than total link count)
- Top referring domains by authority
- Competitor link gap: who links to them but not us?

**Anchor Text Distribution:**
- Branded: 30-40% (company name, URL)
- Natural/generic: 20-30% ("click here", "this article", "learn more")
- Keyword-rich: 10-20% (target keywords)
- Topic-related: 15-25% (related terms)
- Avoid: over-optimized exact-match anchors (> 20% = risk)

**Toxic Link Detection:**
- Links from: PBNs, link farms, irrelevant foreign-language sites, adult/gambling
- Disavow file: submit to Google if significant toxic link profile
- Monitor with regular backlink audits (monthly)

### 5. Keyword Research Methodology

**Seed Keywords:** Start with 5-10 core terms from business offering, customer language, and competitor analysis.

**Long-Tail Expansion:**
- Autocomplete suggestions
- People Also Ask
- Related Searches
- Question modifiers (how, what, why, when, best, vs.)
- Answer the Public, AlsoAsked

**Search Intent Mapping:**
| Intent | Signal | Content Type |
|--------|--------|-------------|
| Informational | "how to", "what is", "guide" | Blog, guide, video |
| Navigational | Brand name, product name | Homepage, product page |
| Transactional | "buy", "pricing", "discount" | Product page, pricing page |
| Commercial | "best", "vs", "review", "top" | Comparison, review, listicle |

**Prioritization Matrix:**
| Keyword | Volume | Difficulty | Intent | Current Rank | Priority |
|---------|--------|-----------|--------|-------------|----------|
| [term] | [monthly] | [1-100] | [type] | [position] | [H/M/L] |

Priority = High volume + Low difficulty + High intent alignment + Not yet ranking

### 6. Competitive SEO Gap Analysis
- Keywords where competitors rank on page 1 and we don't rank at all
- Keywords where we rank page 2-3 (striking distance — quick wins)
- Content types competitors publish that we don't (video, tools, calculators)
- Technical advantages competitors have (faster site, better mobile, richer schema)

### 7. Prioritized Action Plan

**Quick Wins (1-2 weeks, low effort):**
- Fix broken internal links and 404s
- Add missing meta descriptions and title tags
- Optimize images (compress, add alt text)
- Fix canonical tag issues
- Update thin pages with 300+ words of value

**Medium Effort (1-3 months):**
- Create content for top 10 keyword gaps
- Build topic clusters for 3 core themes
- Improve Core Web Vitals (LCP, INP, CLS)
- Implement schema markup on key page types
- Internal linking optimization pass

**Strategic Investments (3-6 months):**
- Link building campaign (guest posts, digital PR, partnerships)
- Content refresh program (update all pages > 12 months old)
- Technical infrastructure (CDN, server upgrade, new sitemap strategy)
- Internationalization (hreflang, localized content)
- Advanced schema (FAQ, HowTo, Video markup)
""",
)


# =============================================================================
# SALES SKILLS
# =============================================================================

account_research = Skill(
    name="account_research",
    description="Company and prospect research framework for sales including trigger events, stakeholder mapping, and synthesis templates.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.MKT],
    knowledge_summary=(
        "Sales research framework: company analysis (business model, revenue, tech stack, org structure), "
        "prospect research (LinkedIn, career trajectory, content engagement), trigger event identification, "
        "and research synthesis template with conversation starters and risk factors."
    ),
    knowledge="""
## Account Research Framework for Sales

### 1. Company Research Framework

**Business Model:**
- What do they sell? (products/services)
- Who do they sell to? (target market, segments)
- How do they make money? (revenue model: subscription, transactional, marketplace, advertising)
- What's their go-to-market? (direct sales, self-serve, channel, PLG)

**Revenue & Growth:**
- Annual revenue (public: 10-K; private: estimate from employee count, funding, industry data)
- Revenue growth rate (accelerating, decelerating, flat)
- Profitability (public: operating margin; private: last funding runway)
- Employee headcount and growth (LinkedIn, job postings as proxy)

**Recent News & Press:**
- Last 90 days: press releases, news articles, blog posts
- Key themes: product launches, partnerships, executive changes, funding, expansion
- Sentiment: positive momentum or challenges?

**Key Initiatives:**
- What are they investing in? (job postings reveal priorities)
- Strategic priorities mentioned in earnings calls, CEO letters, conference presentations
- Digital transformation, efficiency, growth, or compliance focus?

**Tech Stack:**
- Current tools (BuiltWith, Wappalyzer, job descriptions, case studies)
- Integration requirements
- Contract renewal timing (if discoverable)
- Technology pain points (G2 reviews, Reddit, community forums)

**Organizational Structure:**
- Reporting hierarchy (LinkedIn org chart, company page)
- Decision-making: centralized (C-suite decides) or distributed (department heads)?
- Procurement process: formal RFP, informal evaluation, executive mandate?

**Pain Points by Role:**
| Role | Typical Pain Points |
|------|-------------------|
| CEO/Founder | Growth, efficiency, competitive threat, investor pressure |
| VP Sales | Pipeline, conversion rates, rep productivity, forecasting accuracy |
| VP Marketing | Lead quality, attribution, CAC, content scale |
| CTO/VP Eng | Technical debt, hiring, security, scalability |
| CFO | Cost control, visibility, compliance, ROI on spend |

### 2. Prospect Research

**LinkedIn Profile Analysis:**
- Current role and tenure (new in role = change agent)
- Career trajectory (promoted internally = aligned with company, job hopper = may leave soon)
- Skills and endorsements (reveals priorities and expertise)
- Groups and follows (industry interests)
- Activity: posts, comments, shares (topics they care about)

**Shared Connections:**
- Mutual connections for warm introduction
- Former colleagues at your customer companies
- Shared alumni networks

**Content Engagement:**
- Articles they've published or shared
- Comments on industry topics
- Conference speaking or panel participation
- Podcast appearances

**Role Responsibilities:**
- Map their likely KPIs based on title
- Understand their team size and scope
- Identify who they report to and who reports to them

### 3. Trigger Events

| Trigger | Signal | Why It Matters |
|---------|--------|---------------|
| New Funding | Press release, Crunchbase | Budget to invest, growth mandate |
| Leadership Change | LinkedIn, press | New leader = new priorities, willing to change |
| Expansion | Job postings, office announcements | Need to scale tools and processes |
| Acquisition | Press | Integration needs, consolidation, new budget |
| Product Launch | Press, product page | Need marketing/sales support |
| Regulatory Change | Industry news | Compliance pressure creates urgency |
| Competitor Loss | News, social | Frustration, open to alternatives |
| Poor Earnings | SEC filing, press | Cost-cutting, efficiency focus |
| Tech Migration | Job postings for new stack | Evaluating new tools |

### 4. Research Synthesis Template

**Company Snapshot:**
- Name, industry, HQ, size, revenue, stage
- One-line description of what they do

**Key Stakeholders:**
| Name | Title | Role in Decision | Priority |
|------|-------|-----------------|----------|
| | | Champion / Economic Buyer / Technical / Blocker | |

**Pain Hypothesis:**
"Based on [trigger/research], [Company] likely struggles with [pain point] because [evidence]. Our [capability] addresses this by [value]."

**Value Proposition Alignment:**
- Their priority: [what research shows they care about]
- Our strength: [how we specifically address it]
- Proof: [customer similar to them who saw results]

**Conversation Starters:**
1. "[Trigger event] — how is that affecting [their area]?"
2. "I noticed [content they published] — we see similar themes with our customers in [industry]."
3. "[Mutual connection] suggested we connect because [reason]."

**Risk Factors:**
- Existing vendor lock-in
- Budget constraints or freeze
- Long procurement cycle
- Champion leaving or low influence
- Competitive threat (active evaluation with competitor)

### 5. Research Sources

| Source | What to Find | Free/Paid |
|--------|-------------|-----------|
| LinkedIn | People, org structure, news, activity | Free + Sales Nav |
| Crunchbase | Funding, leadership, competitors | Free + Pro |
| G2/Capterra | Tech stack, reviews, satisfaction | Free |
| 10-K/Annual Reports | Revenue, strategy, risks | Free (SEC) |
| Job Postings | Priorities, tech stack, growth | Free |
| Patent Filings | Innovation direction | Free (USPTO) |
| Conference Attendance | Interests, network | Free (event sites) |
| Press/News | Triggers, momentum | Free (Google News) |
| Social Media | Culture, priorities, voice | Free |
| Industry Reports | Market trends, benchmarks | Paid (Gartner, Forrester) |
""",
)

outreach_drafting = Skill(
    name="outreach_drafting",
    description="Personalized sales outreach with frameworks (AIDA, PAS, BAB), multi-channel cadence, and follow-up sequences.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.MKT],
    knowledge_summary=(
        "Sales outreach framework covering AIDA/PAS/BAB/QVC templates, cold email structure, "
        "personalization playbook (company news, shared connections, metrics), multi-channel 12-day "
        "cadence, subject line formulas, and response handling for all scenarios."
    ),
    knowledge="""
## Personalized Sales Outreach Framework

### 1. Outreach Frameworks

**AIDA (Attention-Interest-Desire-Action):**
- Attention: Hook with relevant insight or personalization
- Interest: Connect to their specific pain/goal
- Desire: Show the outcome they can achieve
- Action: Clear, specific, low-friction CTA

**PAS (Problem-Agitate-Solve):**
- Problem: Name their specific challenge
- Agitate: Describe the consequences of not solving it
- Solve: Position your offering as the path forward

**BAB (Before-After-Bridge):**
- Before: Their current painful state
- After: The ideal state they want
- Bridge: How you help them get there

**QVC (Question-Value-CTA):**
- Question: Ask about a challenge you know they face
- Value: Share a relevant insight or data point
- CTA: Offer a specific next step

### 2. Cold Email Template Structure

**Subject Line:** 3-5 words, lowercase feels personal, avoid spam triggers.
Examples:
- "quick question about [initiative]"
- "[mutual connection] suggested I reach out"
- "idea for [their specific goal]"

**Opening (1-2 sentences):** Personalized hook referencing research. Never start with "I" or "My name is."
- "Saw [Company]'s announcement about [initiative] — congrats on [achievement]."
- "[Mutual connection] mentioned you're focused on [priority] this quarter."
- "Your recent [post/talk] on [topic] resonated — we see the same pattern with [industry] teams."

**Body (2-3 sentences):** Connect their pain to your value. One specific, relevant benefit.
- "Teams like [similar company] were spending [X hours] on [pain]. After [solution], they [specific result]."
- "We help [role] at [company type] [achieve outcome] by [mechanism]. [Customer] saw [metric] in [timeframe]."

**CTA (1 sentence):** Specific, low-friction ask. One CTA only.
- "Worth a 15-minute call next Tuesday or Wednesday?"
- "Can I send over a 2-minute video showing how this works for [industry]?"
- "Would it help if I shared the [case study/analysis] we did for [similar company]?"

### 3. Personalization Playbook

**Tier 1 — Deep Personalization (high-value targets):**
- Reference specific company news from last 30 days
- Mention their content (article, podcast, LinkedIn post)
- Name a mutual connection
- Cite a metric from their industry or their company specifically

**Tier 2 — Role Personalization (mid-tier):**
- Reference industry-specific challenge for their role
- Mention a company in their peer set who is a customer
- Reference a trend affecting their industry

**Tier 3 — Segment Personalization (volume outreach):**
- Industry-specific pain point
- Company size or stage-specific challenge
- Role-specific metric or benchmark

### 4. Multi-Channel Cadence

| Day | Channel | Action | Content Angle |
|-----|---------|--------|--------------|
| 1 | Email | Cold email #1 | Personalized hook + value prop |
| 3 | LinkedIn | Connection request | Short note referencing email |
| 5 | Email | Follow-up #1 | New angle: social proof/case study |
| 7 | LinkedIn | Engage with their content | Like/comment on recent post |
| 8 | Email | Follow-up #2 | Value-add: share relevant resource |
| 10 | Phone | Call attempt | Reference emails, ask for 2 minutes |
| 12 | Email | Breakup email | Polite close, leave door open |

### 5. Subject Line Formulas with Examples
- **Mutual connection:** "[Name] suggested we connect"
- **Trigger event:** "congrats on [funding/launch/expansion]"
- **Question:** "quick question about [initiative]"
- **Value offer:** "[metric] improvement for [company type]"
- **Curiosity:** "idea for [their goal]"
- **Direct:** "[their pain point] at [Company]"
- **Breakup:** "should I close your file?"

### 6. Follow-Up Sequences

**Follow-Up #1 (Day 3-5):** New angle, not "just checking in."
- "Forgot to mention — [Customer] in [their industry] just [achieved result]. Thought it'd be relevant."

**Follow-Up #2 (Day 7-8):** Add value, no ask.
- "Came across this [report/article] on [their challenge] — thought you'd find it useful. [link]"

**Follow-Up #3 (Day 10-12):** Breakup — polite, leaves door open.
- "I don't want to be a pest. If [pain point] isn't a priority right now, no worries. If it becomes one, here's my calendar link for whenever it makes sense."

### 7. Response Handling

**Positive Response:** ("Sure, let's chat")
- Reply within 1 hour
- Propose 2-3 specific times
- Include calendar link
- Confirm agenda: "I'll share how [similar company] addressed [pain] — should take 15 minutes."

**Neutral Response:** ("Send me more info")
- Send a concise one-pager or 2-minute video (not a full deck)
- Include one clear CTA: "After you review, worth a 15-minute call?"
- Follow up in 3 days if no reply

**Objection Response:** ("We already use X" / "Not in budget")
- Acknowledge: "Makes sense — [Competitor] is solid for [strength]."
- Differentiate: "Where we tend to add value is [specific gap]. [Customer] switched because [reason]."
- CTA: "Worth a quick comparison? No commitment — just want to make sure you have the full picture."

**Not Now Response:** ("Maybe next quarter")
- Accept gracefully: "Completely understand."
- Set reminder: "I'll follow up in [timeframe]. In the meantime, here's [resource] that might be useful."
- Add to nurture sequence
""",
)

call_preparation = Skill(
    name="call_preparation",
    description="Sales call preparation framework with research checklists, agenda templates, discovery questions, and objection handling.",
    category="sales",
    agent_ids=[AgentID.SALES],
    knowledge_summary=(
        "Pre-call prep framework: research checklist (account history, competitive situation), structured "
        "agenda template (rapport 2min, discovery 15min, solution 10min), discovery question bank by stage, "
        "objection anticipation, stakeholder mapping, and post-call action plan."
    ),
    knowledge="""
## Sales Call Preparation Framework

### 1. Pre-Call Research Checklist

- [ ] **Account History:** Review CRM — prior interactions, emails, notes, opportunities
- [ ] **Recent Interactions:** Last touchpoint, what was discussed, any open items
- [ ] **Open Opportunities:** Current deal stage, amount, timeline, next steps from last meeting
- [ ] **Competitive Situation:** Are they evaluating alternatives? Which ones?
- [ ] **Attendee Roles:** Who's on the call? Title, role in decision, priorities
- [ ] **Company News:** Anything in last 30 days (funding, product launch, leadership change)
- [ ] **Trigger:** What caused this meeting? (inbound request, outbound cadence, referral, renewal)
- [ ] **Goal for This Call:** One clear objective (qualify, advance, close, expand)

### 2. Agenda Template

| Time | Section | Purpose |
|------|---------|---------|
| 0-2 min | Rapport & Context | Build connection, confirm agenda and time |
| 2-7 min | Situation Review | Understand current state, validate assumptions |
| 7-22 min | Discovery Questions | Uncover pain, impact, urgency, decision process |
| 22-32 min | Solution Discussion | Connect capabilities to their specific needs |
| 32-35 min | Next Steps | Agree on actions, timeline, and follow-up |

**Opening Script:** "Thanks for making time, [Name]. I want to make sure this is valuable for you. I'd like to start by understanding [their situation], share how we've helped similar teams, and then figure out if there's a fit. Sound good? Also — I have us for [X] minutes. Does that still work?"

### 3. Discovery Question Bank by Sales Stage

**Qualification (BANT+):**
- "What's driving the need to solve this now?" (urgency)
- "Who else is involved in evaluating solutions?" (authority)
- "Do you have budget allocated for this, or would we need to build a case?" (budget)
- "What does your ideal timeline look like?" (timeline)
- "What happens if you don't solve this?" (consequence/pain)

**Needs Analysis:**
- "Walk me through your current process for [activity]." (current state)
- "Where does that process break down or create friction?" (pain)
- "What does success look like for you in 6-12 months?" (desired state)
- "How are you measuring [relevant KPI] today?" (metrics)
- "What have you tried before to address this?" (prior attempts)

**Technical Evaluation:**
- "What does your current tech stack look like for [area]?" (integration)
- "Are there specific requirements or constraints we should know about?" (requirements)
- "Who on your team would be using this day-to-day?" (users)
- "What does your data migration or onboarding look like?" (implementation)
- "What's your IT review or security approval process?" (procurement)

**Commercial Negotiation:**
- "What's the decision-making process from here?" (process)
- "Are there other stakeholders who need to weigh in?" (consensus)
- "What would make this a clear yes for you?" (close criteria)
- "Is there anything that would be a dealbreaker?" (risks)
- "What timeline are you working toward for a decision?" (close date)

### 4. Objection Anticipation

Before every call, list the 3 most likely objections and prepare responses:

| Likely Objection | Response Framework |
|-----------------|-------------------|
| "Too expensive" | "I understand. Let me walk through the ROI. [Customer] saw [metric] which more than covered the investment in [timeframe]." |
| "We already have a solution" | "That makes sense. Most of our customers came from [competitor/manual process]. Where we tend to add value is [specific differentiator]." |
| "Not a priority right now" | "Completely fair. What would need to change for this to become a priority? I want to make sure I'm reaching out at the right time." |
| "Need to think about it" | "Of course. To help you think it through — what are the main factors you'll be weighing? I can send materials that address those specifically." |
| "We had a bad experience before" | "I appreciate you sharing that. Can you tell me what went wrong? I want to make sure we address those concerns directly." |

### 5. Stakeholder Map

**Before the call, identify:**

| Role | Name | Priority | Approach |
|------|------|----------|----------|
| Champion | [person who wants this] | Keep engaged, arm with ammunition | |
| Economic Buyer | [person who approves budget] | Demonstrate ROI, minimize risk | |
| Technical Evaluator | [person who assesses fit] | Prove capability, address integration | |
| Coach | [internal ally who guides you] | Ask for intel, process advice | |
| Blocker | [person who may resist] | Understand objections, neutralize or convert | |

### 6. Meeting Logistics

- [ ] Confirm meeting time and timezone 24 hours before
- [ ] Test video/screen share link
- [ ] Prepare screen shares (demo, deck, ROI calculator) — have them loaded and ready
- [ ] Have backup materials accessible (case studies, one-pagers, pricing)
- [ ] Quiet environment, good audio, camera on
- [ ] CRM open for note-taking during call
- [ ] Calendar open for scheduling next meeting on the spot

### 7. Post-Call Action Plan Template

**Within 1 hour of call:**
- [ ] Log call notes in CRM
- [ ] Send follow-up email (recap, action items, next steps)
- [ ] Update deal stage if appropriate
- [ ] Update close date and amount if new info
- [ ] Schedule any promised follow-up (materials, intro, next meeting)

**Within 24 hours:**
- [ ] Deliver any materials promised
- [ ] Brief internal team on call outcome
- [ ] Send calendar invite for next meeting
- [ ] Update forecast if deal stage changed

**If no next meeting scheduled:**
- [ ] Set follow-up task for 3 business days
- [ ] Add to appropriate nurture sequence if no near-term opportunity
""",
)

call_summary_processing = Skill(
    name="call_summary_processing",
    description="Sales call transcript processing with extraction frameworks, follow-up templates, CRM update checklists, and escalation triggers.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.EXEC],
    knowledge_summary=(
        "Call transcript processing: extraction framework (decisions, action items, objections, signals), "
        "follow-up email template, internal brief template, CRM update checklist, and escalation triggers "
        "(deal at risk, executive sponsor needed, legal review)."
    ),
    knowledge="""
## Sales Call Summary Processing Framework

### 1. Extraction Framework

When processing a call transcript or notes, extract the following:

**Key Decisions Made:**
- What was agreed upon during the call?
- Any approvals, rejections, or directional choices?
- Changes to scope, timeline, or approach?

**Action Items:**
| Action | Owner | Deadline | Priority |
|--------|-------|----------|----------|
| [specific task] | [name] | [date] | High/Med/Low |

**Objections Raised and Responses:**
| Objection | Our Response | Resolved? | Follow-Up Needed? |
|-----------|-------------|-----------|------------------|
| [what they said] | [how we addressed it] | Yes/Partial/No | [what to send/do] |

**Competitive Mentions:**
- Which competitors were named?
- In what context? (currently using, evaluating, mentioned by reference)
- What was said about them? (positive, negative, neutral)

**Budget/Timeline/Authority Signals:**
- Budget: Any numbers mentioned? Allocated or need approval? Fiscal year timing?
- Timeline: Target decision date? Implementation deadline? External drivers?
- Authority: Who makes final call? Who else needs to approve? What's the process?

**Next Steps Agreed:**
- Specific next meeting date/time
- Materials to send
- People to involve
- Milestones before next conversation

**Sentiment/Engagement Level:**
- Enthusiasm: High (asking detailed questions, sharing internal info) / Medium (polite, engaged) / Low (distracted, short answers, pushing back)
- Champion strength: Strong (advocating internally), Moderate (interested but cautious), Weak (passive)
- Risk signals: Mentioned other options, pushed timeline, reduced scope, mentioned budget pressure

### 2. Follow-Up Email Template

Subject: "Great connecting — recap and next steps"

Hi [Name],

Thanks for your time today. Here's a quick recap of our conversation:

**Key Points Discussed:**
- [Point 1 — their pain/goal]
- [Point 2 — how we can help]
- [Point 3 — specific interest area]

**Agreed Next Steps:**
- [ ] [Action — Owner — By Date]
- [ ] [Action — Owner — By Date]
- [ ] [Action — Owner — By Date]

**Attached:** [relevant materials promised during call]

**Next Meeting:** [date/time] — I've sent a calendar invite.

[If no next meeting:] "Would [day] at [time] work for our next conversation?"

Looking forward to [specific next milestone].

Best,
[Name]

### 3. Internal Brief Template

**Deal:** [Company Name] — [Deal Name]
**Date:** [Call Date]
**Attendees:** [Names and Roles]
**Call Type:** [Discovery / Demo / Technical Review / Negotiation / Exec]

**TL;DR:** [One sentence summary of call outcome]

**Deal Stage Update:**
- Previous: [stage] -> Current: [stage]
- Confidence: [High/Medium/Low] — because [reason]

**Qualification Update (MEDDPICC):**
- Metrics: [what success looks like for them]
- Economic Buyer: [identified? engaged?]
- Decision Criteria: [what they'll evaluate on]
- Decision Process: [steps from here to close]
- Paper Process: [legal, procurement, security review?]
- Identified Pain: [confirmed pain points]
- Champion: [who is championing internally? how strong?]
- Competition: [who else is in the mix?]

**Key Intelligence:**
- [Insight about their priorities, budget, timeline, internal dynamics]
- [Anything that changes our approach or risk assessment]

**Resource Needs:**
- [ ] [SE support for technical deep-dive]
- [ ] [Executive alignment call]
- [ ] [Custom demo environment]
- [ ] [Legal review of terms]
- [ ] [Custom pricing approval]

### 4. CRM Update Checklist

After every call, update the following:

- [ ] **Log Activity:** Call type, duration, attendees, summary
- [ ] **Update Deal Stage:** Only move forward if criteria genuinely met
- [ ] **Update Close Date:** Adjust based on new timeline information
- [ ] **Update Amount:** Adjust if scope or pricing discussed
- [ ] **Add Notes:** Key quotes, objections, insights (searchable later)
- [ ] **Update Next Step:** Specific action with date (not "follow up")
- [ ] **Update Contacts:** Add any new stakeholders to the opportunity
- [ ] **Update Competitor Field:** If competitive information gathered
- [ ] **Update Custom Fields:** Champion, decision process, technical requirements

### 5. Escalation Triggers

**Deal at Risk (notify manager):**
- Champion went silent or left the company
- New competitor entered evaluation late
- Budget was cut or reallocated
- Timeline pushed by more than 4 weeks
- Key stakeholder expressed serious concern
- Prospect cancelled or rescheduled 2+ meetings

**Executive Sponsor Needed:**
- Economic buyer wants to speak with our leadership
- Deal > $X threshold (per company policy)
- Strategic account or named account
- Competitive threat from vendor with exec relationships

**Legal Review Needed:**
- Custom contract terms requested
- Data processing agreement required
- Non-standard SLA requested
- Customer in regulated industry with specific compliance needs

**Custom Pricing Request:**
- Multi-year deal
- Volume discount beyond standard tiers
- Bundle request outside standard packages
- Competitive pricing pressure requiring exception
""",
)

pipeline_review = Skill(
    name="pipeline_review",
    description="Sales pipeline health analysis with metrics, hygiene checks, deal prioritization, and risk categorization.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.EXEC],
    knowledge_summary=(
        "Pipeline analysis framework: core metrics (coverage ratio 3-4x, velocity, win rate by stage), "
        "hygiene checks (stale deals, missing fields, stuck stages), deal prioritization matrix, risk "
        "categorization (at-risk vs healthy signals), and weekly review template."
    ),
    knowledge="""
## Sales Pipeline Health Analysis Framework

### 1. Pipeline Metrics

| Metric | Formula | Healthy Benchmark |
|--------|---------|------------------|
| Total Pipeline Value | Sum of all open opportunity amounts | N/A (track trend) |
| Weighted Pipeline | Sum of (amount x probability) per deal | Closer to forecast |
| Pipeline Coverage Ratio | Total Pipeline / Quota | 3-4x quarterly target |
| Average Deal Size | Total Pipeline / Number of Deals | Track trend, segment by type |
| Win Rate by Stage | Won Deals / Total Deals Entering Stage | Varies by stage (see below) |
| Sales Cycle Length | Avg days from creation to close (won) | Track by segment |
| Pipeline Velocity | (# Deals x Avg Deal Size x Win Rate) / Sales Cycle | Higher = healthier |

**Win Rate Benchmarks by Stage:**
| Stage | Expected Win Rate |
|-------|------------------|
| Discovery/Qualification | 5-15% |
| Needs Analysis/Demo | 15-30% |
| Proposal/Quote | 30-50% |
| Negotiation | 50-75% |
| Verbal Commit | 75-95% |

### 2. Pipeline Hygiene Checks

Run these checks weekly. Flag deals that fail:

**Stale Deals (No Activity):**
- No activity in >7 days (early stage): Yellow flag
- No activity in >14 days (any stage): Red flag
- Action: Rep must update with next step or move to closed-lost

**Past Expected Close Date:**
- Close date passed by 1-2 weeks: Push date and add note explaining why
- Close date passed by >2 weeks: Re-qualify the deal — is it still real?
- Close date passed by >30 days: Move to closed-lost unless strong evidence

**Missing Key Fields:**
- [ ] Close date populated
- [ ] Amount populated
- [ ] Next step defined (specific, not "follow up")
- [ ] Champion identified
- [ ] Decision criteria documented
- [ ] Competitive info captured
- [ ] MEDDPICC fields updated

**Stuck in Stage:**
- Deal in current stage > 2x average for that stage
- Action: Diagnose — missing stakeholder? unresolved objection? no champion? Develop unsticking plan.

### 3. Deal Prioritization Matrix

**Score each deal on two axes:**

**Probability (vertical):**
- High (70-100%): Verbal commit, contract in legal, clear timeline
- Medium (40-69%): Proposal sent, active evaluation, budget confirmed
- Low (10-39%): Early stage, no budget confirmed, single-threaded

**Value (horizontal):**
- High: Above average deal size
- Medium: Average deal size
- Low: Below average deal size

**Quadrant Actions:**
| | High Value | Medium Value | Low Value |
|--|-----------|-------------|-----------|
| **High Prob** | Close NOW — all resources | Close this week | Quick close, don't over-invest |
| **Med Prob** | Accelerate — executive sponsor, SE support | Standard process, push for next step | Efficiency play, templatize |
| **Low Prob** | Invest in qualification — worth the effort | Nurture, check back monthly | Deprioritize or disqualify |

**Time-Decay Adjustment:** Reduce effective probability by 5% for each week past expected close date.

### 4. Risk Categorization

**At-Risk Signals:**
- No identified champion (or champion left)
- Single-threaded (only one contact engaged)
- Competitive threat (active evaluation of competitor)
- Budget uncertainty (no confirmed budget or budget reallocation risk)
- Timeline slip (pushed close date 2+ times)
- Reduced engagement (fewer attendees, shorter meetings, slower replies)
- Scope reduction (started enterprise, now discussing smaller tier)

**Healthy Signals:**
- Multi-threaded (3+ contacts engaged across functions)
- Clear next steps with dates
- Validated budget with economic buyer
- Mutual action plan in place
- Champion actively selling internally
- Technical evaluation passed
- References requested (late-stage buying signal)

**Risk Mitigation Playbook:**
| Risk | Mitigation Action |
|------|------------------|
| No champion | Identify potential champion, provide ammunition for internal selling |
| Single-threaded | Request intro to other stakeholders via main contact |
| Competitor | Deliver battlecard content, set competitive landmines |
| Budget uncertain | Build ROI case, connect with economic buyer |
| Timeline slip | Identify external deadline, create urgency (end-of-quarter pricing, implementation timeline) |

### 5. Weekly Pipeline Review Template

**New Pipeline Added This Week:**
| Deal | Amount | Stage | Source | Expected Close |
|------|--------|-------|--------|---------------|
| | | | | |

**Total new pipeline: $X (vs. target: $Y)**

**Pipeline Moved Forward:**
| Deal | Previous Stage | Current Stage | Amount | Key Event |
|------|---------------|--------------|--------|-----------|
| | | | | |

**Pipeline Lost/Slipped:**
| Deal | Amount | Reason | Win-Back Plan? |
|------|--------|--------|---------------|
| | | | |

**Forecast Changes:**
| Deal | Previous Forecast | Updated Forecast | Reason |
|------|------------------|-----------------|--------|
| | | | |

**Top 5 Deals — Focus This Week:**
| # | Deal | Amount | Stage | Key Action This Week | Risk Level |
|---|------|--------|-------|---------------------|-----------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

### 6. Pipeline Trend Analysis

**Track Weekly:**
- New pipeline created (amount and count)
- Pipeline advanced (stage progressions)
- Pipeline lost (closed-lost amount and count)
- Net pipeline change (created - lost)

**Track Monthly:**
- Pipeline coverage ratio trend
- Average deal size trend
- Win rate trend by stage
- Sales cycle length trend
- Conversion rate between stages

**Red Flags in Trends:**
- Coverage ratio dropping below 3x (not enough pipeline being created)
- Win rate declining (qualification issue or competitive pressure)
- Sales cycle lengthening (deals getting stuck, market conditions)
- Average deal size shrinking (discounting too much or targeting wrong segment)
""",
)

sales_forecasting = Skill(
    name="sales_forecasting",
    description="Weighted sales forecast methodology with categories, scenario modeling, historical accuracy analysis, and risk adjustments.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.FIN, AgentID.EXEC],
    knowledge_summary=(
        "Forecast methodology: four categories (commit >90%, best case 60-90%, upside 30-60%, pipeline <30%), "
        "stage-based weighting, three-scenario modeling (worst/likely/best), historical accuracy tracking, "
        "risk adjustments (deal-level and macro), and weekly/monthly/quarterly forecast cadence."
    ),
    knowledge="""
## Weighted Sales Forecast Methodology

### 1. Forecast Categories

| Category | Confidence | Criteria | Typical Close Rate |
|----------|-----------|---------|-------------------|
| Commit | > 90% | Verbal agreement, contract in process, clear close date | 85-95% |
| Best Case | 60-90% | Proposal accepted, active negotiation, budget confirmed | 50-70% |
| Upside | 30-60% | Active evaluation, multiple meetings, some qualification gaps | 25-40% |
| Pipeline | < 30% | Early stage, discovery, no confirmed budget or timeline | 5-15% |

**Category Assignment Rules:**
- Commit: Economic buyer has said "yes", procurement/legal in process, no open blockers
- Best Case: Proposal/pricing shared, positive feedback, expected decision this quarter
- Upside: Qualified opportunity, active engagement, but missing 1-2 key criteria (budget, timeline, authority)
- Pipeline: In discovery or qualification, insufficient data to forecast with confidence

### 2. Weighting Methodology (Stage-Based)

| Stage | Weight | Rationale |
|-------|--------|-----------|
| Discovery | 10% | Very early, most will not progress |
| Qualification | 25% | Confirmed need, but many unknowns remain |
| Proposal/Quote | 50% | Active evaluation, solution mapped to need |
| Negotiation | 75% | Terms being discussed, high intent |
| Verbal Commit | 90% | Agreement in principle, paperwork pending |

**Weighted Pipeline = Sum of (Deal Amount x Stage Weight)**

**Example:**
| Deal | Amount | Stage | Weight | Weighted |
|------|--------|-------|--------|----------|
| Acme Corp | $100K | Negotiation | 75% | $75K |
| Beta Inc | $50K | Proposal | 50% | $25K |
| Gamma Ltd | $200K | Discovery | 10% | $20K |
| **Total** | **$350K** | | | **$120K** |

### 3. Three-Scenario Modeling

**Worst Case (Floor):**
- Commits only
- Formula: Sum of all Commit deals
- Use when: Conservative planning, board reporting, expense budgeting

**Likely Case (Expected):**
- Commits + 50% of Best Case
- Formula: Sum(Commit) + 0.5 x Sum(Best Case)
- Use when: Operations planning, hiring, resource allocation

**Best Case (Ceiling):**
- Commits + Best Case + 30% of Upside
- Formula: Sum(Commit) + Sum(Best Case) + 0.3 x Sum(Upside)
- Use when: Stretch targets, investment justification, upside scenarios

**Scenario Summary Table:**
| Scenario | Formula | This Quarter | % of Target |
|----------|---------|-------------|-------------|
| Worst | Commits | $X | Y% |
| Likely | Commits + 50% Best | $X | Y% |
| Best | Commits + Best + 30% Upside | $X | Y% |
| Target | Quota | $X | 100% |

### 4. Historical Accuracy Analysis

**Compare Prior Forecasts to Actuals:**
| Period | Forecasted (Likely) | Actual | Variance | Accuracy |
|--------|-------------------|--------|----------|----------|
| Q1 | $X | $Y | +/-$Z | Y/X % |
| Q2 | $X | $Y | +/-$Z | Y/X % |
| Q3 | $X | $Y | +/-$Z | Y/X % |
| Q4 | $X | $Y | +/-$Z | Y/X % |

**Forecast Bias Calculation:**
- Optimism Bias: Forecast consistently > Actual (reduce future forecasts by bias %)
- Pessimism Bias: Forecast consistently < Actual (increase future forecasts by bias %)
- Formula: Average Bias = Mean of (Forecast - Actual) / Forecast across periods

**Rep-Level Accuracy:**
- Track forecast accuracy per rep over 4+ quarters
- Adjust individual forecasts by their historical accuracy rate
- "Rep A forecasts $100K but historically closes at 80% of forecast = adjusted $80K"

### 5. Risk Adjustments

**Deal-Level Adjustments:**
| Factor | Adjustment |
|--------|-----------|
| Large deal (>2x avg) | Reduce weight by 10-15% (larger deals more volatile) |
| New customer | Reduce weight by 10% (vs. expansion of existing) |
| Competitive deal | Reduce weight by 15-20% (risk of loss to competitor) |
| Single-threaded | Reduce weight by 15% (champion dependency) |
| No identified champion | Reduce weight by 25% (no internal advocate) |
| Push from prior quarter | Reduce weight by 20% (pattern of slippage) |

**Macro Adjustments:**
| Factor | Adjustment |
|--------|-----------|
| Seasonality (strong quarter) | Increase by 5-10% based on historical pattern |
| Seasonality (weak quarter) | Decrease by 5-10% |
| Market conditions (recession) | Apply blanket 10-20% reduction |
| Budget cycle timing | Increase if aligned with buyer fiscal year-end |
| Rep track record | Multiply by rep's historical accuracy % |

### 6. Forecast Presentation Template

**Executive Summary:**
"This quarter we forecast $[Likely] against a target of $[Quota], representing [X]% attainment. Our Commit is $[Commit] ([Y]% of target) with $[Best Case] in Best Case and $[Upside] in Upside."

**Forecast Summary Table:**
| Category | Deal Count | Total Value | Weighted Value |
|----------|-----------|------------|---------------|
| Commit | X | $X | $X |
| Best Case | X | $X | $X |
| Upside | X | $X | $X |
| Pipeline | X | $X | $X |
| **Total** | **X** | **$X** | **$X** |

**Waterfall from Prior Forecast:**
- Prior forecast: $X
- Deals won since last forecast: +$X
- Deals lost since last forecast: -$X
- New deals added: +$X
- Deals pushed to next quarter: -$X
- Amount changes (up/down): +/-$X
- **Current forecast: $X**

**Key Deal Movements:**
| Deal | Change | Impact | Reason |
|------|--------|--------|--------|
| [name] | Moved to Commit | +$X | Contract received |
| [name] | Pushed to Q+1 | -$X | Budget delayed |
| [name] | Lost | -$X | Went with competitor |

**Risk Factors:**
1. [Specific risk with quantified impact]
2. [Specific risk with quantified impact]
3. [Specific risk with quantified impact]

**Confidence Assessment:** [High/Medium/Low] — [one sentence justification]

### 7. Forecast Cadence

**Weekly Update (15 min):**
- Each rep updates deal stages and categories
- Manager reviews top deals and changes
- Flag any deals that moved categories
- Quick pipeline coverage check

**Monthly Formal Forecast (60 min):**
- Full forecast review with scenario modeling
- Historical accuracy comparison
- Risk adjustment application
- Resource allocation decisions
- Formal submission to leadership

**Quarterly Strategic Forecast (90 min):**
- Full year forecast update
- Territory and segment analysis
- Capacity planning (do we have enough reps?)
- Strategic investment decisions
- Board-ready forecast materials
""",
)

competitive_intelligence_battlecard = Skill(
    name="competitive_intelligence_battlecard",
    description="Interactive competitive battlecard creation with product comparison, sales plays, objection handling, and win/loss analysis.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.MKT],
    knowledge_summary=(
        "Battlecard framework: quick facts section, feature comparison matrix with win/loss indicators, "
        "competitive positioning (where we win/lose/tie with proof points), sales plays (landmines, traps, "
        "knockout questions), top 5 objection responses, and win/loss analysis with update triggers."
    ),
    knowledge="""
## Competitive Intelligence Battlecard Framework

### 1. Battlecard Structure

**Quick Facts:**
| Field | Details |
|-------|---------|
| Company | [Name] |
| Founded | [Year] |
| HQ | [City, Country] |
| Employees | [Count] |
| Funding | [Total raised, last round] |
| Revenue (est.) | [Range] |
| Key Customers | [3-5 logos] |
| Target Market | [Who they sell to] |
| Pricing Model | [Per user, flat, usage-based] |
| Key Integration | [Notable integrations] |

**Product Comparison Matrix:**
| Capability | Us | Competitor | Winner |
|-----------|-----|-----------|--------|
| Feature A | Full support | Partial | Us |
| Feature B | Partial | Full support | Them |
| Feature C | Unique | Not available | Us |
| Feature D | Roadmap | Full support | Them |
| Ease of Use | High | Medium | Us |
| API/Integrations | Extensive | Limited | Us |
| Support | 24/7 + CSM | Business hours | Us |
| Pricing | Mid-market | Lower | Them |

Use indicators: Strong (full capability), Partial (some capability), Weak (limited), None (not available), Unique (only we have it), Roadmap (planned).

**Pricing Comparison:**
| Tier | Us | Competitor | Notes |
|------|-----|-----------|-------|
| Entry/SMB | $X/mo | $Y/mo | They're cheaper at entry |
| Mid-Market | $X/mo | $Y/mo | Similar pricing |
| Enterprise | $X/mo | $Y/mo | We include more at enterprise |
| Free Trial | 14 days | 7 days | Longer trial = more evaluation time |
| Annual Discount | 20% | 15% | Better long-term value |

**Target Market Overlap:**
- Where we both compete: [segment, company size, industry]
- Where they're stronger: [specific segment]
- Where we're stronger: [specific segment]
- Where they don't compete: [our unique market]

### 2. Competitive Positioning

**Where We Win (use these actively in deals):**

1. **[Advantage 1]:** [Description]
   - Proof: "[Customer] chose us specifically because [reason]."
   - Data: "[Metric] improvement vs. their solution."
   - When to use: When prospect cares about [scenario].

2. **[Advantage 2]:** [Description]
   - Proof: "[Customer quote or case study reference]."
   - Data: "[Benchmark or comparison data]."
   - When to use: When prospect mentions [pain point].

3. **[Advantage 3]:** [Description]
   - Proof: "[Third-party validation — G2 review, analyst report]."
   - Data: "[Specific metric]."
   - When to use: In [specific sales stage or scenario].

**Where We Lose (mitigate, don't avoid):**

1. **[Disadvantage 1]:** [Description]
   - Mitigation: "[How to reframe or workaround]."
   - Context: "This matters most when [scenario]. For most customers, [why it's less important]."
   - Roadmap: "[If on roadmap, when expected]."

2. **[Disadvantage 2]:** [Description]
   - Mitigation: "[Alternative approach]."
   - Context: "In practice, [why this gap is smaller than it appears]."

**Where It's Neutral (differentiate here):**

1. **[Shared Capability]:** Both products offer [X].
   - Differentiation: "Our approach to [X] is [unique angle]."
   - Proof: "[Why our implementation is better in practice]."

### 3. Sales Plays

**Landmines to Set (questions that expose competitor weaknesses):**

Plant these early in the evaluation before the competitor can prepare:

1. "When you evaluate [Competitor], ask them about [specific weakness]. Most customers find that [consequence]."
2. "Make sure to test [specific scenario] — it's where the differences really show up."
3. "Ask about their roadmap for [capability they lack]. The timeline might surprise you."
4. "Request a reference from a company your size — their sweet spot is [different segment]."
5. "Ask about their implementation timeline and resource requirements — be specific about [complex scenario]."

**Traps to Avoid (topics where competitor is stronger):**

Do NOT bring up these topics unprompted:

1. **[Topic]:** If prospect asks, respond: "[Acknowledge their strength]. Where we focus instead is [our strength], which [why it matters more]."
2. **[Topic]:** If prospect asks, respond: "[Reframe]. Most customers find that [alternative perspective]."
3. **[Topic]:** Pivot to: "The more important question is [redirect to our strength]."

**Knockout Questions (questions that end competitive evaluations in our favor):**

Use these when you have a strong position and want to accelerate the decision:

1. "Can [Competitor] show you how they handle [our unique capability] in a live demo?"
2. "Have them walk you through [complex scenario] — that's where the real differences emerge."
3. "Ask them for a customer reference in [specific vertical/use case] — we can provide [X] references today."

### 4. Handling Competitive Objections

**Objection 1: "[Competitor] is cheaper."**
Response: "That's fair — their list price is lower. Two things to consider: (1) total cost of ownership including [implementation, add-ons, support tiers], and (2) the ROI difference. [Customer] calculated that our [capability] saved them [hours/$] per month, which more than offset the price difference in [timeframe]."

**Objection 2: "[Competitor] has feature X that you don't."**
Response: "You're right, they do offer [feature X]. We've taken a different approach — [our alternative]. The reason is [rationale]. Customers like [name] found that [our approach] actually [specific benefit]. Happy to walk you through it."

**Objection 3: "We already use [Competitor] and switching is risky."**
Response: "Completely understand — switching costs are real. Let me share why [X] customers made the switch in the last year: [top 2-3 reasons]. We also have a dedicated migration team that handles [specific migration support]. [Customer] was fully migrated in [timeline] with zero downtime."

**Objection 4: "[Competitor] is more established / bigger."**
Response: "They've been around longer, that's true. What we hear from customers who switched is that [specific advantage of being newer/smaller]: faster innovation cycle, more responsive support, and willingness to partner on [customization/features]. [Customer] moved from [Competitor] because [reason]."

**Objection 5: "Their reviews are better."**
Response: "Depends on where you look and what you filter by. On [platform], filter by [your segment/size/use case] — our ratings are [score]. We also have [X] reviews from companies like yours. Happy to connect you with [reference] who evaluated both."

### 5. Win/Loss Analysis Summary

**Why We Win Against [Competitor]:**
1. [Reason with data — e.g., "Better UX — mentioned in 60% of competitive wins"]
2. [Reason with data]
3. [Reason with data]

**Why We Lose Against [Competitor]:**
1. [Reason with data — e.g., "Price — mentioned in 45% of competitive losses"]
2. [Reason with data]
3. [Reason with data]

**Common Evaluation Criteria (what buyers weigh):**
| Criteria | Weight | Our Score | Their Score |
|----------|--------|-----------|-------------|
| Ease of use | High | 9/10 | 7/10 |
| Feature depth | High | 8/10 | 8/10 |
| Price | Medium | 6/10 | 8/10 |
| Support quality | Medium | 9/10 | 6/10 |
| Integration ecosystem | Medium | 8/10 | 7/10 |
| Brand/reputation | Low | 6/10 | 8/10 |

### 6. Update Triggers

**Refresh the battlecard when:**
- Competitor launches new product or major feature
- Competitor changes pricing or packaging
- Competitor gets acquired or acquires another company
- Key executive joins or leaves competitor
- Significant win or loss against this competitor
- New G2/analyst report published
- Quarterly scheduled refresh (minimum cadence)

**Feedback Loop:**
- Sales team flags inaccuracies via [Slack channel / form / CRM field]
- Competitive intel team reviews weekly
- Major updates communicated via email + Slack with diff summary
""",
)

sales_asset_creation = Skill(
    name="sales_asset_creation",
    description="Creating tailored sales collateral including one-pagers, case studies, ROI calculators, proposals, and mutual action plans.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.CONT],
    knowledge_summary=(
        "Sales collateral framework: when to use each asset type (one-pager, case study, ROI calculator, "
        "proposal, mutual action plan, executive summary), detailed templates for each including structure, "
        "key sections, formatting guidelines, and examples."
    ),
    knowledge="""
## Sales Asset Creation Framework

### 1. Asset Types and When to Use

| Asset | Sales Stage | Purpose | Audience |
|-------|-----------|---------|----------|
| One-Pager | Early (Awareness/Discovery) | Quick overview of value proposition | Any stakeholder |
| Case Study | Mid (Evaluation) | Proof that it works for similar companies | Champion, Economic Buyer |
| ROI Calculator | Mid-Late (Justification) | Financial case for investment | Economic Buyer, CFO |
| Proposal | Late (Decision) | Formal offer with terms | Decision-making committee |
| Mutual Action Plan | Late (Complex deals) | Shared timeline to close and implement | All stakeholders |
| Executive Summary | Any (C-level engagement) | Strategic overview for senior leaders | C-suite |

### 2. One-Pager Template

**Layout:** Single page, scannable, visually clean.

**Section 1 — Headline Value Prop (top 20% of page):**
- Bold headline: "[Outcome] for [Audience]"
- Subhead: One sentence expanding on how
- Example: "Close Deals 40% Faster with AI-Powered Pipeline Intelligence"

**Section 2 — Three Key Benefits (middle 50%):**
Each benefit block:
- Icon or number
- Benefit headline (outcome-focused, not feature-focused)
- 2-3 sentences explaining the benefit
- Proof point (metric, customer quote, or data)

Example:
- **1. See Your Pipeline Clearly** — Real-time dashboard showing deal health, risk factors, and next best actions. Customers report 35% fewer surprise losses.
- **2. Forecast With Confidence** — AI-weighted forecasting with 92% accuracy, replacing spreadsheet guesswork. VP Sales at [Customer]: "First quarter we hit forecast within 5%."
- **3. Coach Reps Effectively** — Call analysis and deal scoring surface coaching opportunities. New reps ramp 30% faster.

**Section 3 — Social Proof (bottom 20%):**
- Customer logo bar (5-8 recognizable logos)
- One compelling stat ("Trusted by 500+ sales teams")

**Section 4 — CTA:**
- Single CTA button/link: "Book a Demo" or "See It In Action"
- Contact info

**Formatting Rules:**
- Maximum 200 words total
- No jargon without context
- Benefits, not features
- One clear CTA

### 3. Case Study Framework

**Structure: Challenge -> Solution -> Results**

**Title:** "How [Customer] [Achieved Outcome] with [Product]"

**Customer Profile (sidebar or header):**
- Company: [Name]
- Industry: [Industry]
- Size: [Employees / Revenue]
- Use Case: [Specific application]

**The Challenge (1-2 paragraphs):**
- What problem were they facing?
- What was the business impact? (quantify: lost revenue, wasted time, missed opportunities)
- What had they tried before?
- Why was the status quo no longer acceptable?

**The Solution (1-2 paragraphs):**
- Why did they choose us? (evaluation criteria, what differentiated us)
- How was it implemented? (timeline, effort, integration)
- What features/capabilities were most valuable?
- How did the team adopt it? (change management, training)

**The Results (most important section):**
Present 3-4 specific, quantified results:
- **[Metric 1]:** [X]% improvement in [what] (e.g., "40% reduction in sales cycle length")
- **[Metric 2]:** [X] [unit] saved/gained (e.g., "15 hours per rep per week saved on data entry")
- **[Metric 3]:** $[X] in [outcome] (e.g., "$2.3M additional pipeline in first quarter")
- **[Metric 4]:** [Qualitative benefit] (e.g., "Sales team NPS increased from 32 to 71")

**Customer Quote:**
"[Impactful quote from champion or executive that captures the transformation]."
— [Name], [Title], [Company]

**CTA:** "See how [Product] can deliver similar results for your team. [Link/Contact]"

### 4. ROI Calculator Structure

**Current State Costs (Pain Quantification):**
| Cost Category | Calculation | Monthly Cost |
|--------------|-------------|-------------|
| Labor (manual tasks) | [hours/week] x [hourly rate] x 4 | $X |
| Lost opportunities | [deals lost/month] x [avg deal size] x [win rate impact] | $X |
| Tool costs (current) | [license] + [maintenance] + [integration] | $X |
| Error/rework costs | [error rate] x [cost per error] x [volume] | $X |
| **Total Current Cost** | | **$X/month** |

**Proposed Solution Costs:**
| Cost Category | Amount |
|--------------|--------|
| License fee | $X/month |
| Implementation (one-time, amortized) | $X/month |
| Training (one-time, amortized) | $X/month |
| Ongoing support | Included |
| **Total Solution Cost** | **$X/month** |

**Savings / Gains:**
| Category | Current | With Solution | Improvement |
|----------|---------|-------------|------------|
| Time saved | X hrs/week | Y hrs/week | Z hrs/week |
| Revenue impact | $X/quarter | $Y/quarter | +$Z/quarter |
| Cost reduction | $X/month | $Y/month | -$Z/month |

**Payback Period:** Total implementation cost / Monthly savings = [X] months

**3-Year TCO Comparison:**
| Year | Current State | With Solution | Net Savings |
|------|-------------|-------------|------------|
| Year 1 | $X | $Y (incl. implementation) | $Z |
| Year 2 | $X | $Y | $Z |
| Year 3 | $X | $Y | $Z |
| **Total** | **$X** | **$Y** | **$Z** |

**ROI:** (3-Year Net Savings / Total Investment) x 100 = [X]%

### 5. Proposal Template

**Cover Page:**
- "Proposal for [Company Name]"
- Prepared by [Your Name], [Date]
- Confidential

**Section 1 — Executive Summary (1 page):**
- One paragraph: Why we're the right partner
- Key outcomes they can expect
- Investment summary (high level)

**Section 2 — Understanding of Needs (1-2 pages):**
- Restate their challenges (shows you listened)
- Business impact of these challenges (their words, quantified)
- Desired outcomes and success criteria

**Section 3 — Proposed Solution (2-3 pages):**
- How our solution addresses each need
- Feature-to-need mapping table
- Architecture or workflow diagram (if technical)
- Differentiators relevant to their evaluation criteria

**Section 4 — Implementation Plan (1 page):**
| Phase | Duration | Activities | Deliverables |
|-------|----------|-----------|-------------|
| Kickoff | Week 1 | Onboarding, access setup | Project plan |
| Configuration | Week 2-3 | Setup, data migration | Configured environment |
| Training | Week 4 | Team training, documentation | Trained team |
| Go-Live | Week 5 | Launch, monitoring | Production deployment |
| Optimization | Week 6-8 | Tuning, feedback | Performance report |

**Section 5 — Investment (1 page):**
| Component | Cost |
|-----------|------|
| License (annual) | $X |
| Implementation | $X |
| Training | $X |
| **Total Year 1** | **$X** |
| **Annual Renewal** | **$X** |

**Section 6 — Your Team:**
- Account Executive: [name, contact]
- Solutions Engineer: [name]
- Customer Success: [name]
- Executive Sponsor: [name]

**Section 7 — Timeline:**
Visual timeline from signature to go-live.

**Section 8 — Terms:**
- Validity period (30 days standard)
- Payment terms
- Contract length options
- SLA summary

### 6. Mutual Action Plan Template

**Purpose:** Shared document between buyer and seller outlining every step from current state to go-live. Creates accountability and reveals hidden steps.

| # | Milestone | Owner | Target Date | Status | Notes |
|---|-----------|-------|-------------|--------|-------|
| 1 | Technical evaluation complete | [Prospect Tech Lead] | [Date] | | Demo + sandbox access |
| 2 | Security/compliance review | [Prospect Security] | [Date] | | Send security questionnaire |
| 3 | Business case approved | [Prospect VP] | [Date] | | ROI calculator provided |
| 4 | Executive sponsor alignment | [Both] | [Date] | | Schedule exec call |
| 5 | Vendor selection decision | [Prospect] | [Date] | | |
| 6 | Contract terms agreed | [Both Legal] | [Date] | | Send MSA draft |
| 7 | Procurement/PO issued | [Prospect Procurement] | [Date] | | |
| 8 | Contract signed | [Both] | [Date] | | DocuSign |
| 9 | Kickoff meeting | [Both] | [Date] | | Introduce implementation team |
| 10 | Go-live | [Both] | [Date] | | Target production date |

**Status Options:** Not Started, In Progress, Complete, Blocked, At Risk

**Mutual Action Plan Best Practices:**
- Co-create with the champion (don't just send it)
- Include steps for BOTH sides (not just their tasks)
- Update weekly during active evaluation
- Use to surface hidden requirements early (legal, security, procurement)
- If they won't engage with a MAP, deal risk is high
""",
)


# =============================================================================
# Registration
# =============================================================================


def register_marketing_sales_skills() -> None:
    """Register all professional marketing and sales skills in the global registry."""
    all_skills = [
        # Marketing
        campaign_planning,
        email_sequence_design,
        marketing_performance_report,
        competitive_brief_generation,
        brand_voice_review,
        seo_audit_comprehensive,
        # Sales
        account_research,
        outreach_drafting,
        call_preparation,
        call_summary_processing,
        pipeline_review,
        sales_forecasting,
        competitive_intelligence_battlecard,
        sales_asset_creation,
    ]

    for skill in all_skills:
        skills_registry.register(skill)


# Auto-register when module is imported
register_marketing_sales_skills()
