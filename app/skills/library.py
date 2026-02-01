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

"""Skills Library - Domain-specific knowledge and capabilities.

This module defines pre-built skills that enhance agent capabilities
with specialized domain knowledge and executable functions.
"""

from typing import Any

from app.skills.registry import AgentID, Skill, skills_registry


# =============================================================================
# Finance Skills
# =============================================================================

analyze_financial_statement = Skill(
    name="analyze_financial_statement",
    description="Framework for analyzing financial statements including balance sheets, income statements, and cash flow statements.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.EXEC],
    knowledge="""
## Financial Statement Analysis Framework

### Balance Sheet Analysis
1. **Liquidity Ratios**
   - Current Ratio = Current Assets / Current Liabilities (ideal: 1.5-2.0)
   - Quick Ratio = (Current Assets - Inventory) / Current Liabilities (ideal: 1.0+)

2. **Solvency Ratios**
   - Debt-to-Equity = Total Debt / Shareholders' Equity
   - Interest Coverage = EBIT / Interest Expense

3. **Efficiency Ratios**
   - Asset Turnover = Revenue / Average Total Assets
   - Inventory Turnover = COGS / Average Inventory

### Income Statement Analysis
1. **Profitability Ratios**
   - Gross Margin = (Revenue - COGS) / Revenue × 100
   - Operating Margin = Operating Income / Revenue × 100
   - Net Profit Margin = Net Income / Revenue × 100

2. **Growth Metrics**
   - Revenue Growth Rate = (Current - Previous) / Previous × 100
   - EPS Growth = (Current EPS - Previous EPS) / Previous EPS × 100

### Red Flags to Watch
- Declining gross margins over consecutive quarters
- Increasing accounts receivable without revenue growth
- Negative operating cash flow with positive net income
- High debt-to-equity with declining interest coverage
""",
)

forecast_revenue_growth = Skill(
    name="forecast_revenue_growth",
    description="Methodology for forecasting revenue growth using various projection techniques.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.DATA, AgentID.STRAT],
    knowledge="""
## Revenue Forecasting Framework

### 1. Historical Trend Analysis
- Calculate CAGR (Compound Annual Growth Rate)
- CAGR = (End Value / Start Value)^(1/n) - 1
- Apply moving averages to smooth volatility

### 2. Seasonal Decomposition
- Identify seasonal patterns (monthly/quarterly)
- Adjust forecasts for cyclical behavior
- Formula: Y = Trend × Seasonal × Residual

### 3. Growth Driver Analysis
- Market size growth rate
- Market share trajectory
- New product/service contributions
- Geographic expansion impact

### 4. Scenario Modeling
| Scenario | Assumptions | Probability |
|----------|-------------|-------------|
| Bull Case | Best-case growth drivers materialize | 20% |
| Base Case | Conservative, realistic growth | 60% |
| Bear Case | Economic headwinds, challenges | 20% |

### 5. Weighted Forecast
Final Forecast = (Bull × 0.2) + (Base × 0.6) + (Bear × 0.2)

### Validation Checks
- Compare against industry benchmarks
- Validate against capacity constraints
- Cross-check with management guidance
""",
)

calculate_burn_rate = Skill(
    name="calculate_burn_rate",
    description="Calculate monthly burn rate and runway for startups and cash-conscious companies.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.EXEC],
    knowledge="""
## Burn Rate Calculation

### Gross Burn Rate
Total monthly cash outflows (all expenses)
Formula: Gross Burn = Total Operating Expenses / Month

### Net Burn Rate
Cash outflows minus cash inflows
Formula: Net Burn = (Beginning Cash - Ending Cash) / # Months

### Runway Calculation
How long until cash runs out
Formula: Runway (months) = Current Cash Balance / Net Burn Rate

### Healthy Benchmarks
- Early Stage: 18-24 months runway minimum
- Growth Stage: 12-18 months runway
- Burn Multiple: Net Burn / Net New ARR (ideal < 2.0)

### Cost Categories to Track
- Personnel (typically 60-70% of burn)
- Infrastructure/hosting
- Marketing/customer acquisition
- General & Administrative
""",
)


# =============================================================================
# HR Skills
# =============================================================================

resume_screening = Skill(
    name="resume_screening",
    description="Structured approach for screening resumes and evaluating candidates.",
    category="hr",
    agent_ids=[AgentID.HR],
    knowledge="""
## Resume Screening Framework

### 1. Initial Screen (30 seconds)
- [ ] Does candidate have required years of experience?
- [ ] Are core required skills present?
- [ ] Is location/remote status compatible?
- [ ] Any obvious red flags (gaps, job hopping)?

### 2. Skill Match Scoring
| Requirement | Weight | Score (1-5) | Weighted |
|-------------|--------|-------------|----------|
| Technical skills | 30% | | |
| Industry experience | 20% | | |
| Role-specific experience | 25% | | |
| Education/Certifications | 15% | | |
| Soft skill indicators | 10% | | |

### 3. Experience Quality Indicators
✓ Quantified achievements (%, $, #)
✓ Progressive responsibility
✓ Relevant company caliber
✓ Domain depth vs breadth balance

### 4. Red Flags
- Unexplained employment gaps > 6 months
- Multiple jobs < 1 year tenure
- Vague descriptions lacking specifics
- Skills list mismatch with experience
- Inconsistent timeline

### 5. Tiering Candidates
- **Tier 1**: Move to phone screen immediately
- **Tier 2**: Strong, but needs clarification
- **Tier 3**: Maybe pile, revisit if needed
- **Tier 4**: Does not meet requirements
""",
)

interview_question_generator = Skill(
    name="interview_question_generator",
    description="Generate structured behavioral and technical interview questions.",
    category="hr",
    agent_ids=[AgentID.HR],
    knowledge="""
## Interview Question Framework

### Behavioral Questions (STAR Method)
Ask about specific past situations to predict future behavior.

**Leadership**
- "Tell me about a time you had to lead a team through a difficult project."
- "Describe a situation where you had to influence someone without authority."

**Problem Solving**
- "Walk me through the most complex problem you solved in your last role."
- "Describe a time when you had to make a decision with incomplete information."

**Collaboration**
- "Tell me about a conflict with a colleague and how you resolved it."
- "Describe a successful cross-functional project you led or contributed to."

**Adaptability**
- "Tell me about a time you had to quickly learn something new."
- "Describe a situation where you had to change your approach mid-project."

### Technical Assessment
- "Explain [concept] as if I were a non-technical stakeholder."
- "Walk me through how you would design/build [relevant system]."
- "What's your debugging process when facing [type of issue]?"

### Culture Fit
- "What type of work environment helps you do your best work?"
- "What's something you're learning right now outside of work?"
- "How do you prefer to receive feedback?"

### Scorecard Template
| Competency | Rating (1-5) | Evidence/Notes |
|------------|--------------|----------------|
| Technical Skills | | |
| Problem Solving | | |
| Communication | | |
| Culture Fit | | |
| Overall Recommendation | | |
""",
)

employee_turnover_analysis = Skill(
    name="employee_turnover_analysis",
    description="Framework for calculating and analyzing employee turnover metrics.",
    category="hr",
    agent_ids=[AgentID.HR, AgentID.DATA],
    knowledge="""
## Employee Turnover Analysis

### Core Metrics
**Turnover Rate** = (# Departures / Avg Headcount) × 100
- Monthly: (Departures / Avg Employees) × 100
- Annual: Sum monthly rates or annualize

**Voluntary vs Involuntary**
- Voluntary: Employee-initiated departures
- Involuntary: Company-initiated (layoffs, terminations)

**Regretted vs Non-Regretted**
- Regretted: High performers you wanted to keep
- Non-Regretted: Performance issues, planned exits

### Healthy Benchmarks by Industry
| Industry | Annual Turnover |
|----------|-----------------|
| Tech | 13-15% |
| Retail | 60-65% |
| Healthcare | 18-20% |
| Finance | 10-12% |
| Hospitality | 70-75% |

### Cost of Turnover
Per employee: 50-200% of annual salary
- Recruiting costs
- Onboarding/training
- Productivity ramp-up
- Knowledge loss

### Exit Interview Themes to Track
- Compensation satisfaction
- Career development
- Manager relationship
- Work-life balance
- Company culture
""",
)


# =============================================================================
# Marketing Skills
# =============================================================================

campaign_ideation = Skill(
    name="campaign_ideation",
    description="Creative framework for generating marketing campaign ideas.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.CONT],
    knowledge="""
## Campaign Ideation Framework

### 1. Objective Definition
What outcome are we driving?
- Awareness → Top-of-funnel metrics (reach, impressions)
- Consideration → Mid-funnel (engagement, time on site)
- Conversion → Bottom-funnel (leads, sales, sign-ups)

### 2. Audience Insight Mining
- What pain points resonate most?
- What motivates action?
- Where do they spend time online?
- What content formats do they prefer?

### 3. Campaign Theme Generators
**The Provocative Question**
- "What if [industry assumption] was wrong?"
- "Why are you still [outdated practice]?"

**The Bold Promise**
- "[Result] in [Timeframe], Guaranteed"
- "The Last [Product] You'll Ever Need"

**The Story Arc**
- Customer journey: Before → Struggle → Discovery → Transformation

**The Trend Hijack**
- Connect your message to cultural moments
- Leverage seasonal relevance

### 4. Channel Strategy Matrix
| Channel | Best For | Content Type |
|---------|----------|--------------|
| LinkedIn | B2B, Thought Leadership | Articles, Case Studies |
| Instagram | Visual Products, Lifestyle | Stories, Reels |
| Email | Nurturing, Retention | Sequences, Newsletters |
| Google Ads | Intent Capture | Search, Display |
| TikTok | Gen Z, Viral Potential | Short-form Video |

### 5. Campaign Structure
- Hook (0-3 seconds attention grab)
- Problem agitation
- Solution positioning
- Social proof
- Clear CTA
""",
)

seo_checklist = Skill(
    name="seo_checklist",
    description="Comprehensive SEO audit and optimization checklist.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.CONT],
    knowledge="""
## SEO Optimization Checklist

### Technical SEO
- [ ] Page loads in < 3 seconds (Core Web Vitals)
- [ ] Mobile-responsive design
- [ ] SSL certificate installed (HTTPS)
- [ ] XML sitemap submitted to Google Search Console
- [ ] Robots.txt properly configured
- [ ] No broken links (404 errors)
- [ ] Canonical tags implemented
- [ ] Structured data/Schema markup

### On-Page SEO
- [ ] Title tag: 50-60 characters, keyword at start
- [ ] Meta description: 150-160 characters, compelling
- [ ] H1 tag: One per page, contains primary keyword
- [ ] H2-H6 tags: Logical hierarchy
- [ ] URL structure: Short, descriptive, hyphenated
- [ ] Image alt text: Descriptive, keyword-relevant
- [ ] Internal linking: Contextual links to related pages
- [ ] Content length: 1,500+ words for pillar content

### Content Quality
- [ ] Targets specific search intent (informational/transactional)
- [ ] Provides comprehensive coverage of topic
- [ ] Includes relevant LSI keywords
- [ ] Updated within last 12 months
- [ ] No duplicate content issues
- [ ] Readable (Flesch score 60+)

### Off-Page SEO
- [ ] Quality backlinks from authoritative sites
- [ ] Consistent NAP (Name, Address, Phone) for local
- [ ] Active social media presence
- [ ] Brand mentions and citations
- [ ] Guest posting strategy

### Monitoring
- [ ] Google Analytics configured
- [ ] Google Search Console connected
- [ ] Keyword ranking tracking
- [ ] Backlink monitoring
""",
)

social_media_guide = Skill(
    name="social_media_guide",
    description="Best practices guide for social media content and strategy.",
    category="marketing",
    agent_ids=[AgentID.MKT, AgentID.CONT],
    knowledge="""
## Social Media Best Practices

### Platform-Specific Guidelines

**LinkedIn**
- Post frequency: 1-2x per day
- Best times: Tue-Thu, 7-8am, 12pm, 5-6pm
- Content: Industry insights, career advice, company news
- Format: Text posts (long-form), carousels, native video
- Engagement: Comment on others' posts, join groups

**Twitter/X**
- Post frequency: 3-5x per day
- Best times: 8-10am, 12pm, 7-9pm
- Content: News commentary, threads, polls
- Format: Short text, images, video clips
- Engagement: Quote tweets, replies, spaces

**Instagram**
- Post frequency: 1x per day (feed), 5-7x (stories)
- Best times: 6-9am, 12-2pm, 7-9pm
- Content: Behind-the-scenes, product showcases, user content
- Format: Reels (priority), carousels, stories
- Engagement: Respond to DMs, story mentions

**TikTok**
- Post frequency: 1-3x per day
- Best times: 7-9am, 12-3pm, 7-11pm
- Content: Educational, entertaining, trend-based
- Format: Short-form video (15-60 seconds optimal)
- Engagement: Duets, stitches, comment replies

### Content Pillars (Choose 3-5)
1. Educational value
2. Entertainment
3. Inspiration
4. Behind-the-scenes
5. User-generated content
6. Product/service highlights

### Engagement Rules
- Respond within 1 hour during business hours
- Never ignore negative comments (address professionally)
- Save and reshare positive mentions
- Use emojis appropriately for brand voice
""",
)


# =============================================================================
# Sales Skills
# =============================================================================

lead_qualification_framework = Skill(
    name="lead_qualification_framework",
    description="Structured frameworks for qualifying sales leads (BANT, MEDDIC, CHAMP).",
    category="sales",
    agent_ids=[AgentID.SALES],
    knowledge="""
## Lead Qualification Frameworks

### BANT (Traditional)
**B**udget: Do they have budget allocated?
**A**uthority: Are you talking to the decision-maker?
**N**eed: Do they have a genuine need you can solve?
**T**iming: When do they need to make a decision?

### MEDDIC (Enterprise Sales)
**M**etrics: What quantifiable outcomes do they need?
**E**conomic Buyer: Who controls the budget?
**D**ecision Criteria: How will they evaluate solutions?
**D**ecision Process: What steps to purchase?
**I**dentify Pain: What problem are they solving?
**C**hampion: Who internally will advocate for you?

### CHAMP (Customer-Centric)
**CH**allenges: What problems do they face?
**A**uthority: Who is involved in the decision?
**M**oney: Is there budget?
**P**riority: How urgent is solving this?

### Lead Scoring Matrix
| Criteria | Weight | Score (1-5) |
|----------|--------|-------------|
| Company size/fit | 25% | |
| Budget confirmed | 20% | |
| Decision timeline | 20% | |
| Pain severity | 20% | |
| Champion identified | 15% | |

**Total Score Thresholds:**
- 4.0-5.0: Hot lead (immediate follow-up)
- 3.0-3.9: Warm lead (nurture sequence)
- 2.0-2.9: Cool lead (long-term nurture)
- <2.0: Unqualified (disqualify or park)
""",
)

objection_handling = Skill(
    name="objection_handling",
    description="Techniques and scripts for handling common sales objections.",
    category="sales",
    agent_ids=[AgentID.SALES],
    knowledge="""
## Objection Handling Framework

### The LAER Method
**L**isten: Let them fully express the objection
**A**cknowledge: Show you understand their concern
**E**xplore: Ask questions to understand the root cause
**R**espond: Address the specific concern

### Common Objections & Responses

**"It's too expensive"**
→ "I understand budget is a concern. Can you help me understand what you're comparing us to?"
→ "Let's break down the ROI you'd see in the first 90 days..."
→ "If price weren't a factor, would this solve your problem?"

**"We're happy with our current solution"**
→ "That's great! What do you like most about it?"
→ "Many of our customers said the same thing. What made them switch was..."
→ "If you could improve one thing about your current setup, what would it be?"

**"I need to think about it"**
→ "Absolutely, it's a big decision. What specifically are you weighing?"
→ "What information would help you feel confident moving forward?"
→ "Is there anyone else you'd want to include in this decision?"

**"Send me more information"**
→ "Happy to! To make sure I send the right info, can I ask..."
→ "Of course. What specifically would be most helpful to review?"

**"We don't have time right now"**
→ "When would be a better time? I can schedule a follow-up."
→ "Totally understand. What would need to change for this to become a priority?"

### Objection Prevention
- Set clear agenda at call start
- Qualify thoroughly before demo
- Address common objections proactively
- Use social proof throughout
""",
)

competitive_analysis = Skill(
    name="competitive_analysis",
    description="Framework for analyzing competitors and positioning against them.",
    category="sales",
    agent_ids=[AgentID.SALES, AgentID.MKT, AgentID.STRAT],
    knowledge="""
## Competitive Intelligence Framework

### Competitor Profiling
**Direct Competitors**: Same product/service, same market
**Indirect Competitors**: Different solution, same problem
**Replacement Competitors**: What happens if they do nothing

### Information to Gather
- Pricing structure and tiers
- Key features and capabilities
- Target customer segment
- Recent product launches
- Market positioning/messaging
- Customer reviews (G2, Capterra)
- Employee reviews (Glassdoor)
- Financial health (if public)

### Competitive Battle Card Template
| Our Advantage | Their Weakness | Talking Points |
|---------------|----------------|----------------|
| | | |

| Their Advantage | How to Counter |
|-----------------|----------------|
| | |

### Win/Loss Analysis
After every deal:
- Why did we win/lose?
- Who else was in the running?
- What were the deciding factors?
- What could we have done differently?

### Positioning Against Competitors
**When they're cheaper:**
→ Focus on total cost of ownership, hidden costs, ROI

**When they're feature-rich:**
→ Emphasize ease of use, implementation speed, support

**When they're the incumbent:**
→ Highlight innovation, technical debt, switching ease
""",
)


# =============================================================================
# Compliance Skills
# =============================================================================

gdpr_audit_checklist = Skill(
    name="gdpr_audit_checklist",
    description="Comprehensive GDPR compliance audit checklist.",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge="""
## GDPR Compliance Audit Checklist

### Lawful Basis for Processing
- [ ] Identified lawful basis for each processing activity
- [ ] Consent is freely given, specific, informed, unambiguous
- [ ] Legitimate interest assessments documented
- [ ] Processing is necessary for stated purpose

### Data Subject Rights
- [ ] Right to access (respond within 30 days)
- [ ] Right to rectification process in place
- [ ] Right to erasure ("right to be forgotten")
- [ ] Right to data portability
- [ ] Right to object to processing
- [ ] Right to restrict processing
- [ ] Automated decision-making opt-out available

### Privacy Documentation
- [ ] Privacy policy is clear and accessible
- [ ] Cookie policy and consent mechanism
- [ ] Data Processing Agreements with vendors
- [ ] Records of Processing Activities (ROPA)
- [ ] Data Protection Impact Assessments (DPIAs)

### Technical Measures
- [ ] Data encryption at rest and in transit
- [ ] Access controls and authentication
- [ ] Audit logging of data access
- [ ] Data backup and recovery procedures
- [ ] Pseudonymization where appropriate

### Organizational Measures
- [ ] DPO appointed (if required)
- [ ] Staff training on data protection
- [ ] Breach notification process (72 hours)
- [ ] Vendor due diligence process
- [ ] Data retention schedule

### Cross-Border Transfers
- [ ] Standard Contractual Clauses in place
- [ ] Transfer Impact Assessments completed
- [ ] Adequacy decisions documented
""",
)

risk_assessment_matrix = Skill(
    name="risk_assessment_matrix",
    description="Framework for assessing and prioritizing organizational risks.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.EXEC, AgentID.STRAT],
    knowledge="""
## Risk Assessment Framework

### Risk Identification
Common risk categories:
- Operational risks
- Financial risks
- Compliance/regulatory risks
- Strategic risks
- Reputational risks
- Cybersecurity risks
- Third-party/vendor risks

### Risk Scoring Matrix
**Likelihood Scale:**
1 = Rare (< 10% chance)
2 = Unlikely (10-25%)
3 = Possible (25-50%)
4 = Likely (50-75%)
5 = Almost Certain (> 75%)

**Impact Scale:**
1 = Negligible (< $10K, minimal disruption)
2 = Minor ($10K-$100K, some disruption)
3 = Moderate ($100K-$1M, significant impact)
4 = Major ($1M-$10M, severe impact)
5 = Catastrophic (> $10M, existential threat)

### Risk Score = Likelihood × Impact

| Score | Priority | Action |
|-------|----------|--------|
| 20-25 | Critical | Immediate mitigation required |
| 12-19 | High | Active management plan |
| 6-11 | Medium | Monitoring and controls |
| 1-5 | Low | Accept or periodic review |

### Mitigation Strategies
- **Avoid**: Eliminate the activity causing risk
- **Transfer**: Insurance, contracts, outsourcing
- **Mitigate**: Reduce likelihood or impact
- **Accept**: Acknowledge and monitor

### Risk Register Template
| Risk | Category | Likelihood | Impact | Score | Mitigation | Owner | Status |
|------|----------|------------|--------|-------|------------|-------|--------|
| | | | | | | | |
""",
)


# =============================================================================
# Content Skills
# =============================================================================

blog_writing = Skill(
    name="blog_writing",
    description="Framework and best practices for creating engaging blog content.",
    category="content",
    agent_ids=[AgentID.CONT],
    knowledge="""
## Blog Writing Framework

### Content Structure
1. **Headline** (5-10 words)
   - Include primary keyword
   - Create curiosity or promise value
   - Use numbers when appropriate ("7 Ways to...")

2. **Introduction** (100-150 words)
   - Hook in first sentence
   - Establish the problem/opportunity
   - Promise what reader will learn

3. **Body** (organized with H2/H3)
   - One main idea per section
   - Use bullet points for scannability
   - Include examples and data
   - Add internal and external links

4. **Conclusion** (50-100 words)
   - Summarize key points
   - Clear call-to-action
   - Invite engagement (comments, shares)

### Writing Best Practices
- Short paragraphs (2-3 sentences max)
- Active voice over passive
- Write at 8th-grade reading level
- Use "you" to address reader directly
- Break up text with images/charts

### SEO Integration
- Primary keyword in title, H1, first paragraph
- Secondary keywords in H2 headers
- Keyword density: 1-2% naturally
- Meta description with CTA
- Alt text on all images

### Content Length Guidelines
- Short-form: 500-800 words (quick tips)
- Standard: 1,000-1,500 words (how-to)
- Long-form: 2,000-3,000 words (comprehensive guides)
- Pillar content: 3,000+ words (definitive resources)
""",
)

social_content = Skill(
    name="social_content",
    description="Templates and frameworks for creating engaging social media content.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge="""
## Social Content Creation Framework

### Hook Formulas (First Line)
- "Most people get this wrong about [topic]..."
- "I just discovered a hack for [pain point]..."
- "Unpopular opinion: [contrarian view]"
- "Here's what nobody tells you about [topic]..."
- "[Number] lessons from [experience]:"

### Content Formats

**Thread Structure (Twitter/LinkedIn)**
1. Hook (promise value)
2. Context (why this matters)
3. Main points (3-7 tweets/sections)
4. Summary/takeaway
5. CTA (follow, like, comment)

**Carousel Structure (LinkedIn/Instagram)**
- Slide 1: Bold statement/question
- Slides 2-8: One point per slide
- Final slide: Summary + CTA

**Short Video Script (TikTok/Reels)**
- Hook (0-3 seconds): "Stop scrolling if..."
- Setup (3-10 seconds): The problem
- Solution (10-50 seconds): Your content
- CTA (last 5 seconds): Follow/comment

### Engagement Boosters
- Ask questions at the end
- Use polls and quizzes
- Tag relevant people/brands
- Respond to every comment within 1 hour
- End with "Agree? 👇" or "Save this for later"

### Content Mix (Per Week)
- 40% Educational (teach something)
- 30% Storytelling (personal experiences)
- 20% Promotional (products/services)
- 10% Curated (reshare others' content)
""",
)


# =============================================================================
# Data Analysis Skills
# =============================================================================

anomaly_detection = Skill(
    name="anomaly_detection",
    description="Techniques for identifying data anomalies and outliers.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.OPS],
    knowledge="""
## Anomaly Detection Framework

### Types of Anomalies
1. **Point Anomalies**: Single data point deviates significantly
2. **Contextual Anomalies**: Normal in one context, abnormal in another
3. **Collective Anomalies**: Group of data points abnormal together

### Detection Methods

**Statistical Methods**
- Z-Score: Flag if |z| > 3 (beyond 3 standard deviations)
- IQR Method: Flag if value < Q1 - 1.5*IQR or > Q3 + 1.5*IQR
- Moving Average: Compare current value to rolling mean

**Machine Learning Methods**
- Isolation Forest: Efficient for high-dimensional data
- DBSCAN: Density-based clustering for spatial data
- Autoencoders: Neural network reconstruction error

### Alert Thresholds
| Severity | Deviation | Action |
|----------|-----------|--------|
| Low | 2-3 sigma | Log and monitor |
| Medium | 3-4 sigma | Alert team |
| High | 4-5 sigma | Immediate investigation |
| Critical | >5 sigma | Escalate + incident response |

### Investigation Checklist
- [ ] Verify data source integrity
- [ ] Check for data entry/collection errors
- [ ] Compare with external benchmarks
- [ ] Review recent changes (systems, processes)
- [ ] Document findings and resolution
""",
)

trend_analysis = Skill(
    name="trend_analysis",
    description="Framework for identifying and analyzing data trends.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.FIN, AgentID.STRAT],
    knowledge="""
## Trend Analysis Framework

### Trend Types
- **Upward Trend**: Consistent increase over time
- **Downward Trend**: Consistent decrease over time
- **Horizontal/Flat**: No significant change
- **Seasonal**: Regular patterns that repeat
- **Cyclical**: Longer-term recurring patterns

### Analysis Techniques

**Moving Averages**
- Simple Moving Average (SMA): Equal weight to all periods
- Exponential Moving Average (EMA): More weight to recent data
- Window size: 7-day for short-term, 30-day for medium, 90-day for long

**Trend Lines**
- Linear regression for simple trends
- Polynomial regression for curved trends
- R² value: How well the line fits (>0.7 is good)

**Decomposition**
Trend + Seasonality + Residual = Observed Value
- Isolate each component
- Analyze trend independent of cyclical patterns

### Reporting Structure
1. **Summary**: Key trend in one sentence
2. **Visualization**: Chart showing trend + moving average
3. **Context**: What's driving the trend?
4. **Forecast**: Expected continuation
5. **Recommendations**: Actions based on trend

### Trend Strength Indicators
| Change | Interpretation |
|--------|----------------|
| <5% | No significant trend |
| 5-15% | Moderate trend |
| 15-30% | Strong trend |
| >30% | Very strong trend |
""",
)


# =============================================================================
# Customer Support Skills
# =============================================================================

ticket_sentiment_analysis = Skill(
    name="ticket_sentiment_analysis",
    description="Framework for analyzing customer sentiment in support tickets.",
    category="support",
    agent_ids=[AgentID.SUPP],
    knowledge="""
## Ticket Sentiment Analysis Framework

### Sentiment Classification
**Positive Indicators**
- Expressions of gratitude ("thank you", "appreciate")
- Compliments ("great service", "helpful")
- Emojis: 😊 👍 ❤️

**Neutral Indicators**
- Straightforward questions
- Information requests
- No strong emotional language

**Negative Indicators**
- Frustration words ("frustrated", "annoyed", "disappointed")
- Urgency/escalation language ("immediately", "urgent")
- Emojis: 😡 👎 😤
- ALL CAPS or excessive punctuation!!!

### Urgency Scoring
| Score | Criteria |
|-------|----------|
| 1 | General inquiry, no time pressure |
| 2 | Mild inconvenience, can wait |
| 3 | Impacting productivity, needs same-day |
| 4 | Significant blocker, needs hours |
| 5 | Critical outage, immediate attention |

### Priority Matrix
| Sentiment | Urgency | Priority |
|-----------|---------|----------|
| Negative | High | Critical (escalate) |
| Negative | Low | High (respond first) |
| Neutral | High | High |
| Neutral/Positive | Low | Normal queue |

### Response Templates by Sentiment
**Negative Sentiment Opening:**
"I completely understand how frustrating this must be, and I sincerely apologize for the inconvenience..."

**Neutral Sentiment Opening:**
"Thank you for reaching out. I'd be happy to help you with..."

**Positive Sentiment Opening:**
"Thank you for your kind words! I'm glad to hear..."
""",
)

churn_risk_indicators = Skill(
    name="churn_risk_indicators",
    description="Framework for identifying customers at risk of churning.",
    category="support",
    agent_ids=[AgentID.SUPP, AgentID.SALES],
    knowledge="""
## Customer Churn Risk Framework

### Behavioral Indicators
**High Risk Signals**
- Declining product usage (>30% decrease)
- Fewer logins over last 30 days
- Not adopting new features
- Support tickets with negative sentiment
- Billing disputes or payment failures
- Key champion left the organization

**Medium Risk Signals**
- Usage plateaued (no growth)
- Delayed responses to communications
- Not attending QBRs or check-ins
- Competitive mentions in conversations

### Health Score Components
| Factor | Weight | Calculation |
|--------|--------|-------------|
| Product Usage | 30% | Active days / expected days |
| Feature Adoption | 20% | Features used / available |
| Engagement | 20% | Email opens, call attendance |
| Support Experience | 15% | Ticket resolution, CSAT |
| Contract Status | 15% | Renewal timing, expansion |

### Risk Tiers
- **Green** (80-100): Healthy, focus on expansion
- **Yellow** (60-79): Monitor, proactive outreach
- **Orange** (40-59): At risk, intervention plan
- **Red** (<40): High churn risk, executive attention

### Intervention Playbook
1. Immediate outreach from CSM
2. Understand root cause (survey/call)
3. Create success plan with milestones
4. Offer training/enablement resources
5. Executive sponsor engagement if needed
6. Track weekly until health improves
""",
)


# =============================================================================
# Operations Skills
# =============================================================================

process_bottleneck_analysis = Skill(
    name="process_bottleneck_analysis",
    description="Framework for identifying and resolving process bottlenecks.",
    category="operations",
    agent_ids=[AgentID.OPS],
    knowledge="""
## Process Bottleneck Analysis Framework

### Bottleneck Identification
**Signs of a Bottleneck:**
- Work piling up at a specific stage
- Long wait times between stages
- Resource consistently at 100% utilization
- Downstream processes starved for input

### Analysis Steps
1. **Map the Process**: Document each step and hand-off
2. **Measure Cycle Times**: Time taken at each stage
3. **Calculate Throughput**: Units completed per time period
4. **Identify Constraints**: Lowest throughput = bottleneck

### Theory of Constraints (TOC)
1. **IDENTIFY** the constraint
2. **EXPLOIT** it (maximize efficiency at bottleneck)
3. **SUBORDINATE** everything else (don't overproduce upstream)
4. **ELEVATE** (invest to increase capacity at bottleneck)
5. **REPEAT** (find new constraint)

### Common Bottleneck Causes
| Type | Examples |
|------|----------|
| Capacity | Insufficient resources, equipment |
| Skill | Specialized knowledge required |
| Policy | Approval workflows, compliance |
| Information | Waiting for inputs/decisions |
| Technology | System limitations, integrations |

### Resolution Strategies
- Add parallel capacity
- Automate manual steps
- Batch similar activities
- Remove unnecessary approvals
- Cross-train team members
- Upgrade technology

### Metrics to Track
- Lead Time: Start to finish
- Cycle Time: Time at each stage
- Wait Time: Time between stages
- Throughput: Volume completed
- Work in Progress (WIP): Items in system
""",
)

sop_generation = Skill(
    name="sop_generation",
    description="Template and guidelines for creating Standard Operating Procedures.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.HR],
    knowledge="""
## Standard Operating Procedure (SOP) Template

### SOP Document Structure

**Header Information**
- Title: [Process Name] SOP
- Document ID: SOP-[DEPT]-[NUMBER]
- Version: X.X
- Effective Date: [Date]
- Owner: [Role/Name]
- Last Review: [Date]

**1. Purpose**
One paragraph explaining why this SOP exists and what it achieves.

**2. Scope**
- Who this applies to
- What situations trigger this procedure
- What is NOT covered

**3. Definitions**
Define any technical terms or acronyms.

**4. Prerequisites**
- Required access/permissions
- Tools or systems needed
- Prior training requirements

**5. Procedure Steps**
Numbered, action-oriented steps:
1. [Actor] performs [action]
   - Sub-step detail if needed
   - Expected outcome
2. [Actor] performs [action]
   - Decision point: If X, go to step Y

**6. Verification**
How to confirm the procedure was executed correctly.

**7. Exceptions**
When and how to deviate from standard process.

**8. Related Documents**
Links to related SOPs, policies, or training materials.

### Writing Guidelines
- Use active voice ("Click Submit" not "Submit should be clicked")
- One action per step
- Include screenshots for complex steps
- Highlight warnings and cautions
- Version control all changes
""",
)


# =============================================================================
# Image/Video Generation Skills (Stubs)
# =============================================================================

def generate_image_stub(prompt: str, size: str = "1024x1024") -> dict:
    """Stub implementation for image generation.
    
    In production, this would integrate with DALL-E, Stability AI, or similar.
    
    Args:
        prompt: Text description of the image to generate.
        size: Image dimensions (default: 1024x1024).
        
    Returns:
        Dictionary with generation result (simulated).
    """
    return {
        "success": True,
        "status": "generated",
        "prompt": prompt,
        "size": size,
        "image_url": f"[STUB] Image would be generated for: {prompt}",
        "note": "This is a placeholder. Configure DALLE_API_KEY or STABILITY_API_KEY for real generation."
    }

def generate_video_stub(prompt: str, duration: int = 15) -> dict:
    """Stub implementation for short video generation.
    
    In production, this would integrate with RunwayML, Pika, or similar.
    
    Args:
        prompt: Text description of the video to generate.
        duration: Video duration in seconds (default: 15).
        
    Returns:
        Dictionary with generation result (simulated).
    """
    return {
        "success": True,
        "status": "generated",
        "prompt": prompt,
        "duration_seconds": duration,
        "video_url": f"[STUB] Video would be generated for: {prompt}",
        "note": "This is a placeholder. Configure video generation API keys for real generation."
    }


image_generation = Skill(
    name="image_generation",
    description="Generate images from text prompts using AI image generation.",
    category="content",
    agent_ids=[AgentID.CONT],
    implementation=generate_image_stub,
)

video_generation = Skill(
    name="video_generation",
    description="Generate short videos from text prompts using AI video generation.",
    category="content",
    agent_ids=[AgentID.CONT],
    implementation=generate_video_stub,
)


# =============================================================================
# Register All Skills
# =============================================================================

def register_all_skills() -> None:
    """Register all skills from this library in the global registry."""
    all_skills = [
        # Finance
        analyze_financial_statement,
        forecast_revenue_growth,
        calculate_burn_rate,
        # HR
        resume_screening,
        interview_question_generator,
        employee_turnover_analysis,
        # Marketing
        campaign_ideation,
        seo_checklist,
        social_media_guide,
        # Sales
        lead_qualification_framework,
        objection_handling,
        competitive_analysis,
        # Compliance
        gdpr_audit_checklist,
        risk_assessment_matrix,
        # Content
        blog_writing,
        social_content,
        image_generation,
        video_generation,
        # Data
        anomaly_detection,
        trend_analysis,
        # Support
        ticket_sentiment_analysis,
        churn_risk_indicators,
        # Operations
        process_bottleneck_analysis,
        sop_generation,
    ]
    
    for skill in all_skills:
        skills_registry.register(skill)


# Auto-register skills when module is imported
register_all_skills()

# Import external skills to register them as well
# This adds 37 additional skills from external repositories
import app.skills.external_skills  # noqa: F401, E402
