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
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Skills Library - Domain-specific knowledge and capabilities.

This module defines pre-built skills that enhance agent capabilities
with specialized domain knowledge and executable functions.
"""

from app.skills.registry import AgentID, Skill, skills_registry

# =============================================================================
# Finance Skills
# =============================================================================

analyze_financial_statement = Skill(
    name="analyze_financial_statement",
    description="Framework for analyzing financial statements including balance sheets, income statements, and cash flow statements.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.EXEC],
    knowledge_summary="Covers liquidity ratios (current, quick), solvency ratios (D/E, interest coverage), efficiency ratios (asset/inventory turnover), profitability ratios (gross/operating/net margin), and red flags like declining margins or negative operating cash flow.",
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
    knowledge_summary="Revenue forecasting via CAGR, seasonal decomposition, growth driver analysis, and weighted bull/base/bear scenario modeling.",
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
    knowledge_summary="Gross burn = total monthly expenses. Net burn = (beginning cash - ending cash) / months. Runway = cash balance / net burn. Healthy runway: 18-24mo early stage, 12-18mo growth. Burn multiple < 2.0.",
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
    knowledge_summary="Checklist covering lawful basis, data subject rights (access/erasure/portability), privacy docs (ROPA, DPIAs), technical measures (encryption, audit logs), organizational measures (DPO, breach notification 72h), and cross-border transfers (SCCs).",
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

ccpa_compliance_checklist = Skill(
    name="ccpa_compliance_checklist",
    description="California Consumer Privacy Act (CCPA/CPRA) compliance audit checklist.",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge_summary="CCPA/CPRA checklist: consumer rights (know, delete, opt-out, correct, limit), notice at collection, do-not-sell/share, service provider contracts, financial incentives, and 45-day response window.",
    knowledge="""
## CCPA/CPRA Compliance Audit Checklist

### Consumer Rights
- [ ] Right to Know — disclose categories and specific pieces of PI collected
- [ ] Right to Delete — process deletion requests within 45 days
- [ ] Right to Opt-Out of Sale/Sharing — "Do Not Sell or Share My Personal Information" link
- [ ] Right to Correct inaccurate personal information
- [ ] Right to Limit Use of Sensitive Personal Information
- [ ] Right to Non-Discrimination for exercising privacy rights

### Notice Requirements
- [ ] Notice at Collection — disclosed before or at point of collection
- [ ] Privacy Policy updated within 12 months, includes all CCPA categories
- [ ] Financial incentive notice for loyalty/rewards programs

### Data Inventory
- [ ] Categories of PI collected mapped to business purpose
- [ ] Sources of PI documented
- [ ] Categories of PI sold or shared identified
- [ ] Retention periods defined per category

### Service Provider / Contractor Agreements
- [ ] Written contracts with service providers include CCPA-required terms
- [ ] Contracts prohibit selling/sharing received PI
- [ ] Contracts require notification of consumer requests

### Verification & Response
- [ ] Identity verification process for consumer requests
- [ ] 45-day response window (extendable by 45 days with notice)
- [ ] Toll-free number and at least one other method for requests
- [ ] Response tracking and documentation

### Sensitive PI (CPRA Addition)
- [ ] Identified sensitive PI categories (SSN, precise geolocation, race, health, biometric)
- [ ] "Limit the Use of My Sensitive Personal Information" link if applicable
- [ ] Purpose limitation enforced for sensitive PI
""",
)

sox_compliance_framework = Skill(
    name="sox_compliance_framework",
    description="Sarbanes-Oxley (SOX) compliance framework for internal controls over financial reporting.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.FIN],
    knowledge_summary="SOX framework: Section 302 (CEO/CFO certification), Section 404 (internal controls assessment), COSO framework (5 components, 17 principles), control testing methodology, and deficiency classification.",
    knowledge="""
## SOX Compliance Framework

### Key Sections
- **Section 302**: CEO/CFO must certify accuracy of financial statements
- **Section 404**: Management assessment of internal controls over financial reporting (ICFR)
- **Section 906**: Criminal penalties for false certification

### COSO Framework (5 Components)
1. **Control Environment** — tone at the top, ethics, governance
2. **Risk Assessment** — identify risks to reliable financial reporting
3. **Control Activities** — policies/procedures that mitigate risks
4. **Information & Communication** — relevant info flows to right people
5. **Monitoring Activities** — ongoing evaluation of control effectiveness

### Internal Control Categories
| Type | Examples |
|------|----------|
| Preventive | Segregation of duties, approval workflows, access controls |
| Detective | Reconciliations, variance analysis, exception reports |
| IT General | Change management, access provisioning, backup/recovery |
| IT Application | Input validation, automated calculations, interface controls |

### Control Testing Methodology
1. **Identify** significant accounts and assertions
2. **Document** process flows and key controls (narratives, flowcharts)
3. **Design Assessment** — does the control address the risk?
4. **Operating Effectiveness** — test via inquiry, observation, inspection, re-performance
5. **Sample sizes**: Daily controls 25+, weekly 5+, monthly 2+, quarterly 2, annual 1

### Deficiency Classification
| Level | Definition | Action |
|-------|-----------|--------|
| Deficiency | Control doesn't prevent/detect misstatement | Remediate, no disclosure |
| Significant Deficiency | Reasonable possibility of material misstatement | Report to audit committee |
| Material Weakness | Reasonable possibility of material misstatement NOT prevented/detected | Disclose in 10-K filing |

### SOX IT Compliance
- [ ] Change management process documented and followed
- [ ] User access reviews performed quarterly
- [ ] Privileged access limited and monitored
- [ ] System interfaces validated
- [ ] Automated controls tested annually
""",
)

hipaa_compliance_checklist = Skill(
    name="hipaa_compliance_checklist",
    description="HIPAA Privacy and Security Rule compliance checklist for handling protected health information (PHI).",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge_summary="HIPAA checklist: Privacy Rule (minimum necessary, TPO, authorizations, NPP), Security Rule (administrative/physical/technical safeguards), Breach Notification (60-day rule, HHS reporting), and BAA requirements.",
    knowledge="""
## HIPAA Compliance Checklist

### Privacy Rule
- [ ] Minimum Necessary standard applied — only access/disclose PHI needed for purpose
- [ ] Treatment, Payment, Operations (TPO) uses documented
- [ ] Valid authorization obtained for non-TPO disclosures
- [ ] Notice of Privacy Practices (NPP) provided to patients
- [ ] Patient rights implemented: access, amendment, accounting of disclosures, restriction requests
- [ ] De-identification methods documented (Safe Harbor or Expert Determination)

### Security Rule — Administrative Safeguards
- [ ] Security Officer designated
- [ ] Risk Analysis conducted (annually or after significant change)
- [ ] Risk Management plan in place
- [ ] Workforce training on security policies
- [ ] Contingency plan: data backup, disaster recovery, emergency operations
- [ ] Business Associate Agreements (BAAs) with all vendors handling ePHI

### Security Rule — Physical Safeguards
- [ ] Facility access controls (locked areas, visitor logs)
- [ ] Workstation use and security policies
- [ ] Device and media controls (disposal, re-use, data wiping)

### Security Rule — Technical Safeguards
- [ ] Access controls: unique user IDs, emergency access, auto-logoff, encryption
- [ ] Audit controls: logging of ePHI access and modifications
- [ ] Integrity controls: mechanisms to ensure ePHI not improperly altered
- [ ] Transmission security: encryption for ePHI in transit

### Breach Notification Rule
- [ ] Breach assessment process: risk of compromise analysis (4-factor test)
- [ ] Individual notification within 60 days of discovery
- [ ] HHS notification: >500 individuals = immediate; <500 = annual log
- [ ] Media notification for breaches >500 in a state/jurisdiction
- [ ] Breach documentation retained 6 years

### Business Associate Requirements
- [ ] BAA executed before sharing ePHI
- [ ] BAA includes permitted uses, safeguard requirements, breach notification obligations
- [ ] Subcontractor BAAs required (downstream)
- [ ] BAA termination process for material breach
""",
)

risk_assessment_matrix = Skill(
    name="risk_assessment_matrix",
    description="Framework for assessing and prioritizing organizational risks.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.EXEC, AgentID.STRAT],
    knowledge_summary="5×5 likelihood-impact scoring matrix. Score 20-25 = critical (immediate action), 12-19 = high, 6-11 = medium, 1-5 = low. Strategies: avoid, transfer, mitigate, accept. Includes risk register template.",
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
    knowledge_summary="Identify bottlenecks via cycle time mapping, throughput measurement, and Theory of Constraints (TOC). Resolution: exploit → subordinate → elevate → repeat.",
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
        "note": "This is a placeholder. Configure DALLE_API_KEY or STABILITY_API_KEY for real generation.",
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
        "note": "This is a placeholder. Configure video generation API keys for real generation.",
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
# Cross-cutting / Reference Skills
# =============================================================================

widget_usage_guide = Skill(
    name="widget_usage_guide",
    description="Complete reference for rendering interactive UI widgets in the workspace. Use when you need to display tables, charts, boards, forms, or dashboards.",
    category="reference",
    agent_ids=[],  # Available to ALL agents
    knowledge="""
## Widget Rendering — Full Reference

### Available Widget Tools
- `create_table_widget`: Display any data in table format (leads, employees, transactions, tasks, etc.)
- `create_kanban_board_widget`: Show task boards, project pipelines, and status tracking
- `create_initiative_dashboard_widget`: Display strategic initiatives with progress, status, and metrics
- `create_revenue_chart_widget`: Visualize financial data, revenue trends, and growth metrics
- `create_form_widget`: Collect structured input from users (feedback, requests, surveys)
- `create_calendar_widget`: Show schedules, events, and timeline views
- `create_workflow_builder_widget`: Display process flows and diagrams
- `create_product_launch_widget`: Track product launch milestones
- `create_morning_briefing_widget`: Show daily briefing with approvals and status
- `create_boardroom_widget`: Display discussion transcripts and verdicts
- `create_suggested_workflows_widget`: Show AI-suggested workflow templates
- `display_workflow`: Show a running workflow's status and progress

### User Intent → Widget Mapping
- "Show my initiatives/projects" → `create_initiative_dashboard_widget`
- "Display revenue/sales data" → `create_revenue_chart_widget`
- "Show me a table of X" → `create_table_widget`
- "Put my tasks on a board" → `create_kanban_board_widget`
- "Show my calendar/schedule" → `create_calendar_widget`
- "I need a form for X" → `create_form_widget`
- "Show the workflow" → `create_workflow_builder_widget` or `display_workflow`

### Rules
1. When a user asks to "show", "display", "visualize", "view", or "see" something, ALWAYS use the appropriate widget tool.
2. The widget renders directly in the user's workspace — you ARE capable of this.
3. NEVER say you cannot display or show things. You CAN render widgets.
4. After rendering a widget, briefly describe what you displayed and offer to adjust it.
""",
)

initiative_framework_guide = Skill(
    name="initiative_framework_guide",
    description="Phase-by-phase guide with recommended skills, tools, workflows, and deliverables for each initiative phase (ideation → validation → prototype → build → scale).",
    category="strategy",
    agent_ids=[AgentID.EXEC, AgentID.STRAT],
    knowledge="""
## Initiative Framework — Phase Skill Map

### Phase 1: Ideation & Empathy
**Goal:** Understand the problem space and validate the idea is worth pursuing.
**Skills:** `comprehensive_business_strategy`, `competitive_analysis`
**Tools:** `mcp_web_search`, `create_initiative_dashboard_widget`
**Deliverables:**
- Problem statement defined
- Target audience persona
- Initial competitive landscape
- Empathy map completed

### Phase 2: Validation & Research
**Goal:** Market validation, feasibility analysis, and evidence gathering.
**Skills:** `competitive_analysis`, `seo_checklist`, `trend_analysis`
**Tools:** `mcp_web_search`, `create_table_widget` (for comparison matrices)
**Deliverables:**
- Market size estimate (TAM/SAM/SOM)
- Competitor comparison matrix
- Customer interview insights (3-5 interviews)
- Go/No-Go decision

### Phase 3: Prototype & Test
**Goal:** Build MVP, test with real users, iterate.
**Skills:** `blog_writing` (landing page copy), `social_content` (for launch)
**Tools:** `mcp_generate_landing_page`, `create_kanban_board_widget`
**Deliverables:**
- MVP feature list
- Landing page / test page
- User testing results (5-10 users)
- Iteration notes

### Phase 4: Build Product/Service
**Goal:** Full implementation, resource allocation, execution.
**Skills:** `process_bottleneck_analysis`, `sop_generation`
**Tools:** `create_workflow_builder_widget`, `create_kanban_board_widget`
**Deliverables:**
- Product/service built
- SOPs documented
- Team trained
- Launch checklist

### Phase 5: Scale Business
**Goal:** Growth strategy, marketing, optimization.
**Skills:** `campaign_ideation`, `seo_checklist`, `social_content`, `lead_qualification_framework`
**Tools:** `create_campaign`, `create_revenue_chart_widget`
**Deliverables:**
- Marketing strategy
- Sales pipeline configured
- Growth metrics dashboard
- First month targets set
""",
)


# =============================================================================
# Additional Customer Support Skills
# =============================================================================

kb_article_templates = Skill(
    name="kb_article_templates",
    description="Templates and frameworks for creating effective knowledge base articles, FAQs, and self-service documentation.",
    category="support",
    agent_ids=[AgentID.SUPP],
    knowledge_summary="KB article templates: how-to guides, troubleshooting trees, FAQ format, writing guidelines for clarity and searchability.",
    knowledge="""
## Knowledge Base Article Templates

### Article Types

#### 1. How-To Guide
**Structure:**
- **Title**: "How to [action] [object]" (e.g., "How to Reset Your Password")
- **Overview**: 1-2 sentences explaining what this guide covers
- **Prerequisites**: What the user needs before starting
- **Steps**: Numbered, clear, with screenshots where helpful
- **Expected Result**: What success looks like
- **Troubleshooting**: Common issues at each step
- **Related Articles**: Links to related topics

#### 2. Troubleshooting Article
**Structure:**
- **Symptom**: What the user is experiencing
- **Possible Causes**: Ranked by likelihood
- **Solutions**: Step-by-step for each cause, from simplest to complex
- **Escalation**: When to contact support
- **Decision Tree**:
  ```
  Issue → Check A → Yes → Fix 1
                   → No  → Check B → Yes → Fix 2
                                    → No  → Escalate
  ```

#### 3. FAQ Article
**Structure:**
- **Question**: Written as the user would ask it
- **Short Answer**: 1-2 sentence direct answer
- **Detailed Explanation**: Fuller context if needed
- **Related Questions**: Links to similar FAQs

### Writing Guidelines
- Use plain language (8th grade reading level)
- Active voice ("Click the button" not "The button should be clicked")
- One idea per sentence
- Use bullet points and numbered lists
- Include search keywords in title and first paragraph
- Update date and version info on every edit
- Tag articles by product area, issue type, and difficulty level
""",
)

escalation_framework = Skill(
    name="escalation_framework",
    description="Framework for support ticket escalation including tiers, SLAs, criteria, and handoff procedures.",
    category="support",
    agent_ids=[AgentID.SUPP],
    knowledge_summary="3-tier escalation model with SLAs, escalation triggers, handoff checklist, and de-escalation techniques.",
    knowledge="""
## Support Escalation Framework

### Escalation Tiers

| Tier | Handler | Scope | SLA |
|------|---------|-------|-----|
| L1 | Front-line / AI | FAQ, password resets, basic troubleshooting | 4 hours |
| L2 | Senior Support | Complex issues, account problems, bugs | 8 hours |
| L3 | Engineering / Specialist | System outages, data issues, security | 24 hours |
| Executive | Management | VIP escalations, legal threats, PR risk | 2 hours |

### Escalation Triggers
**Automatic Escalation (L1 → L2):**
- Ticket open > 24 hours without resolution
- Customer sentiment score < 30 (very negative)
- 3+ back-and-forth messages without resolution
- Customer explicitly requests escalation
- Issue involves billing discrepancy > $500

**Automatic Escalation (L2 → L3):**
- Requires code changes or system access
- Affects multiple customers (potential outage)
- Data integrity or security concern
- Ticket open > 72 hours at L2

**Executive Escalation:**
- Customer threatens legal action
- Social media complaint going viral
- Enterprise account with > $100K ARR
- Regulatory or compliance issue

### Handoff Checklist
When escalating, ALWAYS include:
1. **Summary**: One paragraph of the issue
2. **Timeline**: Key dates and interactions
3. **Steps Taken**: What was already tried
4. **Customer Impact**: Severity and business effect
5. **Customer Sentiment**: Current emotional state
6. **Requested Outcome**: What the customer wants
7. **Internal Notes**: Any relevant context

### De-escalation Techniques
- Acknowledge the frustration explicitly
- Take ownership ("I will personally ensure...")
- Set clear expectations on next steps and timeline
- Provide a direct contact for follow-up
- Offer interim workaround if available
""",
)

first_response_templates = Skill(
    name="first_response_templates",
    description="Templates for initial customer support responses across different channels and issue types.",
    category="support",
    agent_ids=[AgentID.SUPP],
    knowledge_summary="First-response templates for email, chat, and phone across issue categories: billing, technical, feature requests, and complaints.",
    knowledge="""
## First Response Templates

### General Principles
- Respond within SLA (email: 4h, chat: 2min, phone: immediate)
- Acknowledge the issue in the first sentence
- Set expectations for resolution timeline
- Personalize — use the customer's name and reference their specific issue

### Email Templates

**Technical Issue:**
Subject: Re: [Original Subject] — We're on it

Hi {name},

Thank you for reporting this. I can see that {specific issue description} is affecting your {workflow/account}.

I've reproduced the issue on our end and here's what I recommend:
1. {First troubleshooting step}
2. {Second step if needed}

If that doesn't resolve it, I'll escalate to our technical team. Expected resolution: {timeframe}.

**Billing Inquiry:**
Hi {name},

Thanks for reaching out about your billing. I've reviewed your account and here's what I found:

{Specific finding about their billing question}

{Action taken or explanation}

If you have any other questions about your account, I'm happy to help.

**Feature Request:**
Hi {name},

Thank you for this suggestion! I've logged your request for {feature description} in our product feedback system.

Our product team reviews all feedback quarterly. While I can't guarantee a timeline, your input directly influences our roadmap.

In the meantime, here's a workaround that might help: {workaround if available}

### Chat Templates

**Opening (Known Issue):**
"Hi {name}! I see you're experiencing {issue}. We're aware of this and actively working on a fix. Current ETA: {timeframe}. Can I help you with a workaround in the meantime?"

**Opening (New Issue):**
"Hi {name}! Thanks for reaching out. Let me look into {issue} for you. Could you confirm: {clarifying question}?"

**Closing:**
"Glad I could help! Is there anything else I can assist with today? If this issue comes back, reference ticket #{ticket_id} and we'll pick up right where we left off."
""",
)


# =============================================================================
# Additional HR Skills
# =============================================================================

onboarding_checklist = Skill(
    name="onboarding_checklist",
    description="Comprehensive new employee onboarding framework with pre-boarding, first day, first week, and 30-60-90 day plans.",
    category="hr",
    agent_ids=[AgentID.HR],
    knowledge_summary="Structured onboarding: pre-boarding prep, Day 1 agenda, Week 1 goals, 30-60-90 day milestones, buddy system, and feedback checkpoints.",
    knowledge="""
## Employee Onboarding Framework

### Pre-boarding (Before Day 1)
- [ ] Offer letter signed and background check cleared
- [ ] IT equipment ordered and configured (laptop, monitors, peripherals)
- [ ] Email, Slack, and tool accounts created
- [ ] Building access / badge arranged
- [ ] Welcome package sent (company swag, org chart, team intro)
- [ ] Buddy/mentor assigned from same team
- [ ] First week calendar pre-populated with key meetings

### Day 1 Checklist
- [ ] Welcome meeting with manager (30 min) — role expectations, team context
- [ ] IT setup — verify all accounts and tools work
- [ ] HR paperwork — benefits enrollment, tax forms, policies acknowledgment
- [ ] Office tour / virtual workspace orientation
- [ ] Lunch with team or buddy
- [ ] End-of-day check-in with manager — questions, first impressions

### Week 1 Goals
- Complete all compliance training modules
- Meet 1:1 with each direct team member
- Read team documentation and key project READMEs
- Shadow 2-3 team meetings
- Complete first small task or ticket
- Buddy check-in (informal coffee/chat)

### 30-60-90 Day Plan
| Milestone | Goals | Success Criteria |
|-----------|-------|-----------------|
| 30 Days | Learn systems, processes, team norms | Can independently handle routine tasks |
| 60 Days | Own small projects, contribute to team goals | Delivering work with minimal guidance |
| 90 Days | Full contributor, identified improvement areas | Positive peer feedback, meeting role expectations |

### Manager Check-in Cadence
- Week 1: Daily 15-min check-ins
- Weeks 2-4: Twice weekly 30-min check-ins
- Month 2-3: Weekly 1:1 meetings
- After 90 days: Standard team cadence
""",
)

performance_review_framework = Skill(
    name="performance_review_framework",
    description="Framework for conducting fair, structured performance reviews including self-assessment, manager evaluation, calibration, and development planning.",
    category="hr",
    agent_ids=[AgentID.HR],
    knowledge_summary="Performance review cycle: self-assessment templates, manager evaluation rubric, calibration process, rating scales, and development plan templates.",
    knowledge="""
## Performance Review Framework

### Review Cycle Timeline
| Phase | Duration | Activities |
|-------|----------|------------|
| Self-Assessment | 2 weeks | Employee completes self-review |
| Manager Review | 2 weeks | Manager drafts evaluations |
| Calibration | 1 week | Leadership aligns on ratings |
| Delivery | 2 weeks | 1:1 review conversations |
| Development Planning | Ongoing | Create/update growth plans |

### Rating Scale (5-Point)
| Rating | Label | Description |
|--------|-------|-------------|
| 5 | Exceptional | Consistently exceeds in all areas, role model |
| 4 | Exceeds | Regularly exceeds expectations in key areas |
| 3 | Meets | Consistently meets all role expectations |
| 2 | Developing | Meets some expectations, improvement needed |
| 1 | Below | Does not meet expectations, PIP consideration |

### Evaluation Dimensions
1. **Job Performance** (40%): Quality and quantity of work output
2. **Competencies** (25%): Skills relevant to role (technical + soft)
3. **Goals Achievement** (20%): Progress on OKRs/KPIs
4. **Values & Culture** (15%): Alignment with company values, collaboration

### Self-Assessment Template
- Top 3 accomplishments this period (with measurable impact)
- Areas where I grew or developed new skills
- Challenges I faced and how I addressed them
- Areas I want to improve in the next period
- Support or resources I need from my manager

### Manager Evaluation Template
- Summary of employee's contributions and impact
- Strengths demonstrated (with specific examples)
- Development areas (with specific examples)
- Rating per dimension with justification
- Overall rating recommendation
- Recommended next steps (promotion, lateral move, PIP, etc.)

### Calibration Guidelines
- Forced distribution is NOT required, but aim for bell curve awareness
- Discuss outliers (all 5s and all 1-2s) in calibration session
- Compare across similar roles and levels for consistency
- Document rationale for any rating changes post-calibration
""",
)

compensation_benchmarking = Skill(
    name="compensation_benchmarking",
    description="Framework for benchmarking compensation including salary bands, equity, benefits comparison, and market data analysis.",
    category="hr",
    agent_ids=[AgentID.HR],
    knowledge_summary="Compensation benchmarking: salary band design, market data sources, equity benchmarks, total comp analysis, and pay equity audit methodology.",
    knowledge="""
## Compensation Benchmarking Framework

### Salary Band Design
| Component | Method |
|-----------|--------|
| Market Data | 50th percentile = band midpoint (competitive) |
| Band Width | ±15-20% of midpoint for individual contributors |
| Band Width | ±20-25% of midpoint for management roles |
| Progression | 10-15% midpoint increase between adjacent levels |

### Market Data Sources
- **Paid surveys**: Radford, Mercer, Culpepper, Pave, Levels.fyi
- **Free benchmarks**: Glassdoor, LinkedIn Salary, Payscale, BLS
- **Best practice**: Use 3+ sources, weight paid surveys more heavily
- **Refresh**: Update benchmarks annually or when filling critical roles

### Total Compensation Components
1. **Base Salary**: Fixed cash compensation
2. **Variable Pay**: Bonuses, commissions (target % of base)
3. **Equity**: RSUs, options, ESPP (annualized value)
4. **Benefits**: Health, dental, vision, 401k match, PTO
5. **Perks**: WFH stipend, learning budget, wellness, meals

### Benchmarking Process
1. Define comparison peer group (industry, size, geography, stage)
2. Map internal roles to standard survey job codes
3. Pull market data for each role at appropriate percentile
4. Calculate compa-ratio: (actual pay / band midpoint) × 100
5. Identify outliers: compa-ratio < 85% (underpaid) or > 115% (overpaid)
6. Develop adjustment plan with budget impact analysis

### Pay Equity Audit
- Compare compensation across gender, race, and other protected categories
- Control for: level, function, tenure, location, performance rating
- Flag unexplained gaps > 5% for investigation
- Document findings and remediation actions
- Conduct annually as part of compensation planning cycle
""",
)


# =============================================================================
# Additional Finance Skills
# =============================================================================

cash_flow_forecasting = Skill(
    name="cash_flow_forecasting",
    description="Framework for cash flow forecasting including direct method, indirect method, 13-week rolling forecasts, and scenario modeling.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.EXEC],
    knowledge_summary="Cash flow forecasting methods (direct vs indirect), 13-week rolling forecast template, scenario modeling, and working capital optimization levers.",
    knowledge="""
## Cash Flow Forecasting Framework

### Methods

#### Direct Method (Short-term, 13-week)
- Forecast actual cash receipts and disbursements
- Start with opening cash balance
- Add: customer collections, other inflows
- Subtract: payroll, vendor payments, rent, debt service, taxes
- Result: ending cash balance per week

#### Indirect Method (Long-term, monthly/quarterly)
- Start with net income
- Adjust for non-cash items (depreciation, amortization, stock comp)
- Adjust for working capital changes (AR, AP, inventory)
- Subtract: capital expenditures, debt repayment
- Result: free cash flow

### 13-Week Rolling Forecast Template
| Week | Opening Balance | Collections | Payroll | Vendors | Other | Net Flow | Closing |
|------|----------------|-------------|---------|---------|-------|----------|---------|
| W1   | $X             | $X          | ($X)    | ($X)    | ($X)  | $X       | $X      |
| ...  | ...            | ...         | ...     | ...     | ...   | ...      | ...     |
| W13  | $X             | $X          | ($X)    | ($X)    | ($X)  | $X       | $X      |

### Scenario Modeling
- **Base Case**: Expected collections and expenses
- **Best Case**: Accelerated collections, delayed non-critical spend
- **Worst Case**: Delayed collections (15-30 day slip), unexpected expenses
- **Stress Test**: Major customer default, market downturn impact

### Working Capital Optimization
| Lever | Target | Impact |
|-------|--------|--------|
| Days Sales Outstanding (DSO) | Reduce by 5-10 days | Faster cash inflow |
| Days Payable Outstanding (DPO) | Extend by 5-10 days | Slower cash outflow |
| Inventory Turns | Increase by 1-2x | Less cash tied up |
| Billing Frequency | Weekly vs monthly | Smoother cash flow |

### Red Flags
- Cash runway < 6 months
- Negative operating cash flow for 3+ consecutive months
- AR aging > 90 days growing as % of total
- Vendor payment delays becoming habitual
""",
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
        cash_flow_forecasting,
        # HR
        resume_screening,
        interview_question_generator,
        employee_turnover_analysis,
        onboarding_checklist,
        performance_review_framework,
        compensation_benchmarking,
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
        ccpa_compliance_checklist,
        sox_compliance_framework,
        hipaa_compliance_checklist,
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
        kb_article_templates,
        escalation_framework,
        first_response_templates,
        # Operations
        process_bottleneck_analysis,
        sop_generation,
        # Reference
        widget_usage_guide,
        initiative_framework_guide,
    ]

    for skill in all_skills:
        skills_registry.register(skill)


# Auto-register skills when module is imported
register_all_skills()

# Import external skills to register them as well
# This adds 37 additional skills from external repositories
import app.skills.external_skills  # noqa: F401, E402

# Warmup skill embeddings for semantic search (non-blocking, graceful failure)
try:
    from app.skills.skill_embeddings import warmup_skill_embeddings

    warmup_skill_embeddings(skills_registry.list_all())
except Exception as _warmup_err:
    import logging as _logging

    _logging.getLogger(__name__).warning(
        "Skill embedding warmup skipped: %s", _warmup_err
    )
