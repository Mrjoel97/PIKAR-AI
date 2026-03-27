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

"""Professional PM, Productivity, and Content Creation Skills.

This module defines professional-grade skills for Product Management,
Productivity, and Content Creation domains. Skills are registered into
the global skills_registry on import.
"""

from app.skills.registry import AgentID, Skill, skills_registry

# =============================================================================
# Product Management Skills (category="planning")
# =============================================================================

product_spec_writing = Skill(
    name="product_spec_writing",
    description="Framework for writing feature specs and PRDs with structured templates, user stories, and prioritization methods.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.EXEC],
    knowledge_summary="PRD template with problem statement, user stories (Given/When/Then), MoSCoW and RICE prioritization, spec review checklist, and common anti-patterns like solution-first specs.",
    knowledge="""
## Product Spec & PRD Writing Framework

### PRD Template Structure

**1. Problem Statement**
Use the structured problem framework:
- **Who** has the problem: Define the specific user segment or persona
- **What** the problem is: Describe the pain point in observable terms
- **Why** it matters: Business impact, user impact, strategic alignment
- **How** we know it's a problem: Supporting data (support tickets, analytics, user research, churn data)

Example: "Mid-market SaaS administrators (who) cannot bulk-manage user permissions across workspaces (what), causing 3+ hours of manual work per week and driving 12% of enterprise churn (why), as evidenced by 340 support tickets in Q3 and exit survey data (how)."

**2. User Stories**
Format: "As a [persona], I want [action], so that [outcome]."

Each user story MUST include acceptance criteria using Given/When/Then:
- **Given** [precondition/context]
- **When** [action is performed]
- **Then** [expected outcome]

Example:
- Story: "As a workspace admin, I want to apply permission templates to multiple users at once, so that I can onboard new teams in minutes instead of hours."
- AC1: Given I have a saved permission template, When I select 15 users and apply the template, Then all 15 users receive the correct permissions within 30 seconds.
- AC2: Given I apply a template that conflicts with existing permissions, When the operation completes, Then I see a conflict report listing each user and the specific conflicts.

**3. Success Metrics**
Define 2-4 measurable outcomes:
- Primary metric: The one number that proves this feature succeeded
- Secondary metrics: Supporting indicators
- Guardrail metrics: Things that must NOT get worse

Example:
- Primary: Reduce average permission setup time from 3.2 hours to 15 minutes per team
- Secondary: Increase admin NPS from 32 to 50
- Guardrail: No increase in permission-related security incidents

**4. Scope Definition**

| In Scope | Out of Scope |
|----------|-------------|
| Bulk permission templates | Custom RBAC engine rewrite |
| CSV import of user lists | SSO/SAML integration changes |
| Audit log of bulk changes | Cross-tenant permissions |
| Conflict detection & report | Automated permission suggestions |

**5. Requirements**

*Functional Requirements:*
- FR-1: System shall support creating, editing, and deleting permission templates
- FR-2: System shall allow selecting up to 500 users for bulk operations
- FR-3: System shall generate a conflict report before applying changes

*Non-Functional Requirements:*
- NFR-1: Bulk operations must complete within 60 seconds for up to 500 users
- NFR-2: All bulk changes must be logged in the audit trail
- NFR-3: System must support rollback of bulk operations within 24 hours

**6. Technical Constraints**
- Must use existing permission model (no schema migration)
- Must be backward-compatible with API v2
- Must work with current rate limits

**7. Dependencies**
- Depends on: User service v3.2+, Audit logging service
- Blocked by: Nothing currently
- Blocks: Phase 2 automated permission suggestions

**8. Timeline & Milestones**
- Design review: Week 1
- Implementation: Weeks 2-4
- QA & bug fixes: Week 5
- Beta rollout (10% of admins): Week 6
- GA: Week 7

**9. Risks**
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Bulk ops cause DB contention | Medium | High | Implement batching with 50-user chunks |
| Permission conflicts confuse users | High | Medium | Build conflict preview before apply |
| Rollback fails for partial applies | Low | High | Use transactions, test extensively |

### Requirements Prioritization

**MoSCoW Method:**
- **Must Have**: Required for launch. Without these, the feature is not viable.
- **Should Have**: Important but not critical. Can launch without, but plan for next iteration.
- **Could Have**: Nice to have. Include if time permits.
- **Won't Have (this time)**: Explicitly excluded to prevent scope creep.

**RICE Scoring:**
- **Reach**: How many users will this impact in a quarter? (e.g., 500 admins)
- **Impact**: How much will it impact each user? (3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal)
- **Confidence**: How sure are we about estimates? (100%=high, 80%=medium, 50%=low)
- **Effort**: Person-months required (e.g., 2)
- **Score**: (Reach x Impact x Confidence) / Effort

| Feature | Reach | Impact | Confidence | Effort | RICE Score |
|---------|-------|--------|------------|--------|------------|
| Bulk permissions | 500 | 3 | 80% | 2 | 600 |
| Permission templates | 500 | 2 | 100% | 1 | 1000 |
| Audit trail | 200 | 1 | 100% | 0.5 | 400 |

### Spec Review Checklist
- [ ] Problem is validated with data (not assumptions)
- [ ] Success metrics are defined and measurable
- [ ] Edge cases are documented (empty states, errors, limits)
- [ ] Dependencies are identified and owners confirmed
- [ ] No solution bias in requirements (describe WHAT, not HOW)
- [ ] Scope boundaries are explicit (in/out table complete)
- [ ] Stakeholders have reviewed and signed off
- [ ] Technical feasibility confirmed with engineering
- [ ] Accessibility requirements included
- [ ] Rollback/migration plan exists

### Anti-Patterns to Avoid
1. **Solution-first specs**: Writing "build a dropdown" instead of "user needs to select from options"
2. **Unmeasurable success criteria**: "Users will be happier" -- always quantify
3. **Scope creep indicators**: Requirements added after sign-off without re-prioritization
4. **Missing stakeholder input**: No engineering, design, or support review
5. **Assumption-driven**: "We think users want X" without research data
6. **Kitchen sink PRD**: Trying to solve everything in one spec -- split into phases
""",
)

user_research_synthesis = Skill(
    name="user_research_synthesis",
    description="Framework for synthesizing user research data into actionable insights, personas, and journey maps.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.EXEC],
    knowledge_summary="Covers affinity mapping, insight statement format, persona creation from behavioral patterns, journey mapping with pain points, research repository templates, and bias awareness.",
    knowledge="""
## User Research Synthesis Framework

### Research Data Types & When to Use Each

| Method | Best For | Sample Size | Effort |
|--------|----------|-------------|--------|
| User interviews | Deep understanding of motivations | 5-15 | High |
| Surveys | Quantifying known patterns | 100-1000+ | Medium |
| Usability tests | Finding interaction problems | 5-8 per round | Medium |
| Analytics review | Understanding actual behavior | All users | Low |
| Support ticket analysis | Identifying pain points at scale | 50-200 tickets | Low |
| NPS/CSAT feedback | Tracking satisfaction trends | Ongoing | Low |

### Synthesis Framework: From Data to Insight

**Step 1: Affinity Mapping**
1. Extract individual observations from all research sources (one per sticky note/card)
2. Cluster observations into themes (bottom-up, not top-down)
3. Name each cluster with a descriptive theme label
4. Identify relationships between clusters
5. Prioritize themes by frequency (how many sources mention it) and impact (severity of the problem)

Example clusters:
- "Onboarding confusion" (14 observations from 3 sources)
- "Feature discoverability" (9 observations from 2 sources)
- "Pricing transparency" (7 observations from 4 sources)

**Step 2: Insight Statements**
Format: "We observed [behavior/pattern] among [user segment], which suggests [interpretation], indicating an opportunity to [action]."

Examples:
- "We observed that 68% of new users abandon the setup wizard at step 3 (team invitations) among solo users, which suggests the mandatory team step creates friction for individual use cases, indicating an opportunity to make team setup optional with a 'skip for now' path."
- "We observed repeated mentions of 'I didn't know that existed' in usability tests among power users, which suggests feature discoverability degrades as the product grows, indicating an opportunity to implement contextual feature education."

**Step 3: Prioritize Insights**

| Insight | Frequency | Impact | Actionability | Priority |
|---------|-----------|--------|---------------|----------|
| Onboarding drop-off | High (68% of users) | High (direct churn) | High (clear fix) | P0 |
| Feature discoverability | Medium (power users) | Medium (engagement) | Medium (needs design) | P1 |
| Pricing confusion | Low (7 mentions) | High (revenue) | High (copy change) | P1 |

### Persona Creation from Research

**Behavioral Persona Template:**
- **Name & Photo**: Realistic but fictional
- **Role & Context**: Job title, company size, industry
- **Behavioral Patterns**: How they actually use the product (from data, not assumptions)
- **Goals**: What they're trying to achieve (primary and secondary)
- **Frustrations**: What gets in their way (with quotes from research)
- **Key Quotes**: 2-3 verbatim quotes that capture their experience
- **Scenarios**: 2-3 common use cases they perform
- **Metrics**: How they measure their own success

Important: Personas must be grounded in research data, not stereotypes. Each trait should trace back to at least 3 research observations.

### Journey Mapping

**Journey Map Template:**
For each stage of the user journey:

| Stage | Awareness | Consideration | Onboarding | Active Use | Expansion |
|-------|-----------|---------------|------------|------------|-----------|
| **Actions** | Reads blog post | Starts free trial | Completes setup | Daily usage | Invites team |
| **Thoughts** | "Could this solve my problem?" | "Is this worth my time?" | "How does this work?" | "This saves me time" | "My team needs this" |
| **Emotions** | Curious | Cautious/Hopeful | Frustrated/Excited | Satisfied | Confident |
| **Pain Points** | Hard to find pricing | Trial requires credit card | Setup wizard too long | Missing key integration | No bulk invite |
| **Opportunities** | Clearer value prop | Freemium option | Streamline to 3 steps | Integration marketplace | Team onboarding flow |

### Research Repository Template

| Field | Content |
|-------|---------|
| Study ID | RES-2024-015 |
| Date | 2024-03-15 |
| Method | Moderated usability test |
| Participants | 8 mid-market admins, 3-12 months tenure |
| Research Questions | Can users complete bulk permission setup in <5 min? |
| Key Findings | 6/8 failed to find bulk actions menu; avg time 12 min |
| Insights | Bulk actions hidden under "Advanced" -- needs promotion |
| Recommendations | Move bulk actions to primary toolbar; add onboarding tooltip |
| Raw Data Link | [link to recordings/transcripts] |
| Status | Findings shared; design sprint scheduled |

### Bias Awareness Checklist
- [ ] **Confirmation bias**: Am I only noting data that supports my hypothesis?
- [ ] **Leading questions**: Did interview questions suggest a "right" answer?
- [ ] **Small sample generalization**: Am I drawing conclusions from <5 data points?
- [ ] **Recency bias**: Am I overweighting the last interview I conducted?
- [ ] **Survivor bias**: Am I only talking to active users, missing churned ones?
- [ ] **Authority bias**: Am I prioritizing stakeholder opinions over user data?

### Communicating Research Effectively
1. **1-Page Summary**: For executives -- key insight, data point, recommendation
2. **Stakeholder Presentation**: Problem, research approach, findings (with video clips), recommendations, next steps
3. **Actionable Recommendations**: Each recommendation has an owner, priority, and timeline
4. **Share raw data access**: Let teams explore the data themselves
""",
)

stakeholder_update = Skill(
    name="stakeholder_update",
    description="Templates and frameworks for stakeholder communication including weekly updates, monthly reviews, and board reporting.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.EXEC],
    knowledge_summary="Update types (weekly/monthly/quarterly/board), audience calibration for execs vs engineering vs sales, escalation framework, and metric reporting with actuals vs targets.",
    knowledge="""
## Stakeholder Communication Framework

### Update Types & Cadence

| Type | Audience | Length | Cadence | Focus |
|------|----------|--------|---------|-------|
| Weekly Status | Direct team + manager | 1 page | Every Monday | Execution progress |
| Monthly Review | Department heads | 3-5 pages | First week of month | Outcomes + metrics |
| Quarterly Strategic | VP+ leadership | 10-15 pages | End of quarter | Strategy + roadmap |
| Board Update | Board of directors | Exec summary + appendix | Quarterly | Business health |

### Weekly Update Template

**Subject: [Product/Project] Weekly Update -- [Date]**

**Highlights (3 wins this week):**
1. Launched bulk permissions beta to 10% of admins -- 0 critical bugs
2. Completed user research round 2 -- key insight on onboarding friction
3. Reduced API p99 latency from 800ms to 340ms

**Lowlights (2-3 risks or blockers):**
1. [RED] Design review for Phase 2 delayed -- designer out sick, rescheduled to Thursday
2. [YELLOW] QA capacity at 95% -- may need to delay non-critical test cases to next sprint

**Key Metrics:**
| Metric | This Week | Last Week | Target | Trend |
|--------|-----------|-----------|--------|-------|
| Beta activation rate | 34% | 28% | 40% | Up |
| Avg setup time | 8 min | 12 min | 5 min | Improving |
| Support tickets (bulk) | 12 | 18 | <10 | Improving |

**Next Week Priorities:**
1. Fix top 3 beta feedback items
2. Begin Phase 2 design sprint
3. Prepare monthly stakeholder review

**Asks (decisions or resources needed):**
- Need: Decision on whether to extend beta by 1 week (recommend yes, data insufficient)
- Need: Additional QA contractor for 2 weeks (estimated cost: $4,000)

### Audience Calibration

**For Executives (VP+, C-suite):**
- Lead with outcomes and business impact, not tasks completed
- Use metrics with trend indicators (up/down arrows)
- Highlight decisions needed from them specifically
- Keep to one page; offer appendix for details
- Frame risks as "what could impact the timeline/revenue" not technical details

**For Engineering:**
- Include technical details, architecture decisions, and trade-offs
- Reference PRs, ADRs, and technical specs
- Highlight dependencies and integration points
- Discuss technical debt and its impact
- Share performance benchmarks and test results

**For Sales:**
- Focus on customer impact and competitive positioning
- Provide timeline for customer-facing features
- Include competitive win/loss context
- Give them talk tracks for prospects asking about features
- Flag any changes that affect existing customer commitments

**For Board:**
- Strategic progress against annual goals
- Market context and competitive landscape changes
- Financial metrics (ARR, burn, runway)
- Key risks with mitigation plans
- Major decisions or pivots with rationale

### Metric Reporting Best Practices

Always include:
1. **Actual vs Target**: Show the gap
2. **Trend direction**: Is it improving or declining?
3. **Narrative explanation**: For any significant change (>10% deviation), explain WHY
4. **Leading indicators**: Don't just report lagging metrics

Example:
"Activation rate dropped from 34% to 28% this week. Investigation shows this correlates with a 40% increase in signups from a new marketing campaign targeting a different persona (small business vs. mid-market). These users have different onboarding needs. Recommend: separate onboarding flow for small business segment."

### Escalation Framework

**When to Escalate:**
- Blocked for more than 2 business days with no resolution path
- Timeline at risk of slipping by more than 1 week
- Scope change requested that affects committed deliverables
- Resource conflict that cannot be resolved at your level
- Customer commitment at risk

**How to Escalate:**
1. **State the problem**: One sentence, factual, no blame
2. **Quantify the impact**: Timeline, revenue, customers affected
3. **Present options**: 2-3 alternatives with trade-offs
4. **Make a recommendation**: "I recommend Option B because..."
5. **Specify the ask**: What decision do you need, by when?

Example escalation:
"The data migration is blocked because the legacy team cannot provide API access until April (2 weeks past our deadline). Impact: Phase 2 launch delays by 3 weeks, affecting 200 beta customers. Options: (A) Wait -- delays launch to April 21; (B) Build a CSV bridge -- 1 week effort, launches on time but manual; (C) Descope migration from Phase 2 -- launches on time, migration in Phase 3. Recommendation: Option B -- preserves timeline and customer commitments. Need: Decision by Thursday to begin implementation Friday."

### Communication Cadence Best Practices
- Send updates at the same time each week (builds trust and expectation)
- No surprises rule: If something is going wrong, escalate immediately -- don't wait for the weekly update
- Keep a running document of decisions made (who decided, when, context)
- Archive all updates for retrospective reference
- Ask for feedback on your updates quarterly: "Is this the right level of detail?"
""",
)

sprint_planning = Skill(
    name="sprint_planning",
    description="Sprint planning methodology including capacity calculation, estimation, goal setting, and anti-patterns.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.OPS],
    knowledge_summary="Sprint capacity calculation with focus factor, story point estimation methods, sprint goal definition, velocity tracking with rolling averages, and definition of done checklist.",
    knowledge="""
## Sprint Planning Methodology

### Sprint Capacity Calculation

**Formula:**
Available Capacity = Team Members x Available Days x Focus Factor (0.7)

**Detailed calculation:**
1. List each team member
2. Subtract PTO, holidays, company events
3. Subtract recurring meetings (standups, 1:1s, all-hands)
4. Apply focus factor (0.7 for typical teams, 0.6 for interrupt-heavy, 0.8 for dedicated teams)

| Team Member | Available Days | Focus Factor | Capacity (points) |
|-------------|---------------|--------------|-------------------|
| Alice (Sr) | 9/10 | 0.7 | ~8 pts |
| Bob (Mid) | 10/10 | 0.7 | ~7 pts |
| Carol (Jr) | 8/10 | 0.6 | ~4 pts |
| **Total** | | | **~19 pts** |

**Adjustments:**
- First sprint with new team member: reduce their capacity by 50%
- Sprint with major release: reduce total capacity by 20% for release activities
- Sprint after a long break: reduce by 15% for context switching

### Story Point Estimation

**Planning Poker:**
1. Product owner presents the story
2. Team asks clarifying questions
3. Each member privately selects a point value (1, 2, 3, 5, 8, 13, 21)
4. All reveal simultaneously
5. Highest and lowest explain their reasoning
6. Re-vote until consensus (within 1 level)
7. If no consensus after 2 rounds, take the higher estimate

**T-Shirt Sizing (for roadmap-level):**
| Size | Points | Duration | Example |
|------|--------|----------|---------|
| XS | 1 | < 1 day | Config change, copy update |
| S | 2-3 | 1-2 days | Simple feature, bug fix |
| M | 5 | 3-5 days | Standard feature with tests |
| L | 8-13 | 1-2 weeks | Complex feature, new integration |
| XL | 21+ | 2+ weeks | Epic -- must be broken down |

**Reference Story Calibration:**
Pick 3 completed stories that everyone agrees on:
- "Adding a new column to the users table" = 2 points (baseline small)
- "Building the notification preferences page" = 5 points (baseline medium)
- "Implementing OAuth with 3 providers" = 13 points (baseline large)
All future estimates are relative to these reference stories.

### Sprint Goal Definition

A sprint goal is ONE clear outcome statement that the sprint delivers.

**Good sprint goals:**
- "Users can bulk-manage permissions for up to 100 users with conflict detection"
- "Reduce checkout abandonment by implementing saved payment methods"
- "Complete API v3 migration for all read endpoints"

**Bad sprint goals:**
- "Complete sprint backlog" (not an outcome)
- "Work on permissions and checkout and API migration" (too many things)
- "Make progress on Q2 goals" (not specific)

**Test:** Can your sprint demo clearly show this goal was achieved? If not, it's too vague.

### Backlog Refinement Prerequisites

Before a story enters sprint planning, it MUST have:
- [ ] Clear acceptance criteria (Given/When/Then format)
- [ ] Technical approach discussed with engineering (not just product)
- [ ] Dependencies identified and unblocked (or explicit plan to unblock)
- [ ] Design ready (mockups/wireframes reviewed and approved)
- [ ] Story is sized at 8 points or less (larger stories must be split)
- [ ] Edge cases documented (error states, empty states, limits)

### Sprint Planning Meeting Format (60 minutes)

| Time | Activity | Who |
|------|----------|-----|
| 0-5 min | Review sprint goal | Product Owner |
| 5-10 min | Capacity check | Scrum Master |
| 10-50 min | Select stories, discuss tasks, estimate | Full Team |
| 50-55 min | Commitment check: "Can we deliver this?" | Full Team |
| 55-60 min | Identify risks and dependencies | Full Team |

### Velocity Tracking

- Track completed points per sprint (only fully DONE stories count)
- Use **rolling 3-sprint average** for forecasting
- NEVER use velocity as a performance target (this incentivizes gaming)
- Velocity naturally varies 20-30% between sprints -- this is normal
- If velocity drops >30%, investigate (don't pressure the team)

| Sprint | Planned | Completed | Velocity | 3-Sprint Avg |
|--------|---------|-----------|----------|-------------|
| S21 | 22 | 19 | 19 | -- |
| S22 | 20 | 21 | 21 | -- |
| S23 | 21 | 18 | 18 | 19.3 |
| S24 | 19 | 20 | 20 | 19.7 |

### Sprint Anti-Patterns

1. **Overcommitment**: Planning 25 points when velocity is 19 -- always plan to 85-90% of average velocity
2. **No sprint goal**: Just pulling stories off the backlog without a unifying outcome
3. **Too many WIP items**: More stories in progress than team members -- enforce WIP limits (2 per person max)
4. **Carrying over >20%**: If you regularly carry over stories, you're overcommitting or stories are too large
5. **Sprint scope change**: Adding stories mid-sprint without removing something -- protect the sprint commitment
6. **Skipping retro**: The retrospective is where improvement happens -- never skip it
7. **Hero sprints**: One person doing 60% of the work -- redistribute and cross-train

### Definition of Done Checklist

A story is DONE when ALL of these are true:
- [ ] Code complete and self-reviewed
- [ ] Unit tests written and passing (>80% coverage for new code)
- [ ] Integration tests passing
- [ ] Code reviewed by at least one peer
- [ ] Documentation updated (API docs, user guides, README)
- [ ] Product owner has accepted the implementation
- [ ] Deployed to staging environment
- [ ] No known critical or high-severity bugs
- [ ] Performance within acceptable thresholds
- [ ] Accessibility requirements met
""",
)

product_roadmap_management = Skill(
    name="product_roadmap_management",
    description="Product roadmap creation, maintenance, prioritization frameworks, and stakeholder communication strategies.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.EXEC],
    knowledge_summary="Roadmap types (now/next/later, timeline, outcome-based), RICE and opportunity scoring prioritization, stakeholder communication strategies, and anti-patterns like feature factory thinking.",
    knowledge="""
## Product Roadmap Management Framework

### Roadmap Types

**1. Now / Next / Later (Discovery-Friendly)**
Best for: Early-stage products, high-uncertainty environments
- **Now** (committed, 0-6 weeks): In progress or about to start. High confidence.
- **Next** (planned, 6-12 weeks): Validated and scoped. Medium confidence.
- **Later** (exploring, 3-6 months): Research phase. Low confidence, themes only.

**2. Timeline Roadmap (Date-Committed)**
Best for: Enterprise products with contractual commitments
- Shows specific features mapped to quarters or months
- Risk: Creates false precision. Use sparingly and add confidence indicators.
- Always include a disclaimer: "Dates are targets, not commitments. Priorities may shift."

**3. Outcome-Based Roadmap (Metrics-Driven)**
Best for: Mature products focused on optimization
- Instead of "Build feature X," state "Reduce onboarding time from 12 min to 5 min"
- Teams have autonomy to choose solutions
- Progress measured by metric movement, not feature delivery

**4. Kanban Roadmap (Continuous Flow)**
Best for: Platform teams, infrastructure, continuous delivery
- Columns: Exploring | Designing | Building | Shipping | Measuring
- No fixed timeline. Items flow based on capacity and priority.

### Roadmap Input Sources

| Source | Signal | Weight |
|--------|--------|--------|
| Strategy/Vision | Aligns to company goals | High |
| User Research | Validated pain points | High |
| Competitive Analysis | Market parity gaps | Medium |
| Technical Debt | Engineering velocity impact | Medium |
| Sales Requests | Revenue opportunity | Medium (validate first) |
| Support Trends | Volume and severity of issues | Medium |
| Customer Advisory Board | Strategic customer input | Medium |
| Stakeholder Requests | Internal team needs | Low (validate first) |

### Prioritization Frameworks

**RICE Scoring:**
Score = (Reach x Impact x Confidence) / Effort
- Reach: Users affected per quarter
- Impact: 3 (massive), 2 (high), 1 (medium), 0.5 (low), 0.25 (minimal)
- Confidence: 100% (high), 80% (medium), 50% (low)
- Effort: Person-months

**Opportunity Scoring (Importance vs Satisfaction):**
Plot features on a 2x2:
- High Importance + Low Satisfaction = **Top priority** (underserved needs)
- High Importance + High Satisfaction = **Table stakes** (maintain quality)
- Low Importance + Low Satisfaction = **Ignore** (not worth fixing)
- Low Importance + High Satisfaction = **Over-served** (reduce investment)

**Cost of Delay:**
Quantify the weekly cost of NOT building a feature:
- Revenue impact: Lost deals, churn risk
- Cost impact: Manual workarounds, support load
- Strategic impact: Competitive disadvantage

**Value vs Complexity:**
Simple 2x2 for quick decisions:
- High Value + Low Complexity = **Quick wins** (do first)
- High Value + High Complexity = **Strategic bets** (plan carefully)
- Low Value + Low Complexity = **Fill-ins** (do if time permits)
- Low Value + High Complexity = **Avoid** (not worth it)

### Roadmap Communication

**Internal (Full Team):**
- Detailed features with technical context
- Dependencies and integration points
- Quarterly planning sessions to align
- Accessible in shared tool (Jira, Linear, Notion)

**Customer-Facing:**
- Themes and outcomes, NOT specific features
- "We're investing in collaboration tools" not "We're building real-time editing"
- Never commit to dates publicly unless contractually required
- Update quarterly, share via blog post or changelog

**Board/Executive:**
- Strategic outcomes tied to company OKRs
- Market context: Why these priorities over alternatives
- Resource allocation: Where are we investing and why
- Risk register: What could go wrong

### Roadmap Review Cadence

| Frequency | Activity | Participants |
|-----------|----------|-------------|
| Weekly | Progress check on "Now" items | PM + Engineering leads |
| Monthly | Priority reassessment, new input review | PM + Design + Eng + stakeholders |
| Quarterly | Strategic alignment, OKR review | Leadership + PM + Department heads |
| Annually | Vision refresh, 12-month themes | Executive team |

### Handling Feature Requests

Framework: "Thank you for the input. Here's how we evaluate and prioritize."

1. **Acknowledge**: "Thanks for sharing this. I can see why that would be valuable."
2. **Understand**: "Can you help me understand the problem you're solving?"
3. **Document**: Log the request with context, requester, and use case
4. **Evaluate**: Run through prioritization framework
5. **Respond**: "This is now in our backlog. Based on current priorities, it's in the 'Next' bucket. I'll update you when it moves to 'Now.'"

### Saying No Constructively

1. **Acknowledge the need**: "I understand that X is important for your team."
2. **Explain the trade-off**: "If we build X now, we'd need to delay Y, which impacts Z customers."
3. **Offer an alternative**: "In the meantime, here's a workaround / here's what we ARE building that partially addresses this."
4. **Document for future**: "I've added this to our backlog with your context for future consideration."

### Roadmap Anti-Patterns

1. **Feature factory**: Building features without validating outcomes. Measure impact, not output.
2. **Date-driven vs outcome-driven**: Shipping on time is meaningless if the feature doesn't move metrics.
3. **No pruning**: Old items that will never be built clutter the roadmap. Archive ruthlessly every quarter.
4. **Stakeholder-driven roadmap**: Building whatever the loudest person requests. Use data and frameworks.
5. **Invisible roadmap**: If the team can't see the roadmap, they can't align. Make it accessible and updated.
6. **Roadmap as promise**: Treating future items as commitments. Only "Now" is committed.
""",
)

product_metrics_review = Skill(
    name="product_metrics_review",
    description="Product metrics analysis framework with North Star metrics, cohort analysis, funnel optimization, and experiment evaluation.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.DATA, AgentID.EXEC],
    knowledge_summary="North Star metric framework, common product metrics (acquisition through revenue), cohort and funnel analysis, A/B experiment evaluation with statistical significance, and metric anti-patterns.",
    knowledge="""
## Product Metrics Analysis Framework

### Metric Framework: North Star + Supporting Metrics

**North Star Metric**: The ONE metric that best captures the core value your product delivers to customers.

Examples by business type:
- **SaaS**: Weekly active teams performing core action
- **Marketplace**: Weekly transactions completed
- **Media**: Total time spent consuming content
- **E-commerce**: Weekly purchases per active customer

**Supporting Metrics (Input Metrics):**
These are the levers that drive the North Star:
- Acquisition: How users find you
- Activation: How users experience core value
- Engagement: How often users return
- Retention: How long users stay
- Revenue: How users pay

**Leading vs Lagging Indicators:**
- Leading: Predict future outcomes (e.g., feature adoption predicts retention)
- Lagging: Confirm past outcomes (e.g., monthly churn rate)
- Always track both. Leading indicators give you time to react.

### Common Product Metrics

**Acquisition:**
| Metric | Formula | Benchmark |
|--------|---------|-----------|
| Signup rate | Signups / Visitors | 2-5% (B2B), 5-15% (B2C) |
| Activation rate | Users completing core action / Signups | 20-40% |
| CAC | Total acquisition cost / New customers | Varies by industry |
| Organic vs Paid ratio | Organic signups / Total signups | >60% organic is healthy |

**Engagement:**
| Metric | Formula | Benchmark |
|--------|---------|-----------|
| DAU/MAU ratio | Daily active / Monthly active | >20% good, >50% excellent |
| Feature adoption | Users using feature / Total active users | Varies per feature |
| Session duration | Avg time per session | Depends on product type |
| Actions per session | Core actions / Sessions | Higher is better |

**Retention:**
| Metric | Formula | Benchmark |
|--------|---------|-----------|
| D1 retention | Users returning Day 1 / New users | >40% |
| D7 retention | Users returning Day 7 / New users | >20% |
| D30 retention | Users returning Day 30 / New users | >10% |
| Monthly churn | Customers lost / Start-of-month customers | <5% (B2B), <10% (B2C) |

**Revenue:**
| Metric | Formula | Benchmark |
|--------|---------|-----------|
| ARPU | Revenue / Active users | Varies |
| Expansion revenue | Upsell + cross-sell revenue | >20% of new ARR |
| LTV | ARPU x Avg customer lifespan | LTV:CAC > 3:1 |
| Net Revenue Retention | (Start ARR + Expansion - Churn) / Start ARR | >110% excellent |

**Satisfaction:**
| Metric | Formula | Benchmark |
|--------|---------|-----------|
| NPS | % Promoters - % Detractors | >50 excellent, >30 good |
| CSAT | Satisfied responses / Total responses | >80% |
| CES | Effort score on 1-7 scale | <3 is good (low effort) |

### Metrics Review Format

For each metric in your review:
1. **Metric name**: Clear, consistent naming
2. **Current value**: This period's actual
3. **Target**: What we're aiming for
4. **Trend**: Direction over last 3-4 periods
5. **Insight**: Why is it moving this way?
6. **Action**: What are we doing about it?

Example:
"Activation rate: 28% (target: 40%, down from 34% last month). The drop correlates with the new marketing campaign bringing in a different persona. Action: Create a separate onboarding flow for small business users by Sprint 24."

### Cohort Analysis

**User Cohorts by Signup Date:**
Track how groups of users behave over time:

| Cohort | Month 1 | Month 2 | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|---------|----------|
| Jan 2024 | 100% | 45% | 32% | 22% | 15% |
| Feb 2024 | 100% | 48% | 35% | 25% | -- |
| Mar 2024 | 100% | 52% | 38% | -- | -- |

If retention is improving cohort over cohort, product changes are working.

**Feature Adoption Cohort:**
- Users who adopted Feature X vs those who didn't
- Compare retention, expansion, and satisfaction
- Proves (or disproves) feature value

### Funnel Analysis

1. **Define stages**: Visitor > Signup > Activation > Engaged > Paying > Expansion
2. **Measure conversion** between each stage
3. **Identify biggest drop-off**: Where is the largest absolute loss?
4. **Hypothesize why**: Use qualitative data (recordings, surveys, interviews)
5. **Experiment to improve**: A/B test changes at the worst drop-off point

| Stage | Users | Conversion | Drop-off |
|-------|-------|------------|----------|
| Visitors | 10,000 | -- | -- |
| Signups | 500 | 5.0% | 9,500 |
| Activated | 150 | 30.0% | 350 |
| Engaged (Week 2) | 90 | 60.0% | 60 |
| Paying | 45 | 50.0% | 45 |

Biggest opportunity: Signup > Activated (70% drop-off, 350 users lost)

### Experiment Analysis (A/B Testing)

**Before Running:**
1. **Hypothesis**: "Changing X will improve Y by Z% because [reason]"
2. **Primary metric**: One metric to judge success
3. **Guardrail metrics**: Metrics that must not degrade
4. **Sample size**: Calculate required sample for statistical power
5. **Duration**: Minimum 1-2 business cycles (usually 2 weeks)

**After Running:**
1. **Statistical significance**: p-value < 0.05 (95% confidence)
2. **Practical significance**: Is the effect size meaningful? (A 0.1% improvement may be statistically significant but not worth the complexity)
3. **Segment analysis**: Does the effect vary by user segment?
4. **Guardrail check**: Did any guardrail metrics degrade?
5. **Decision**: Ship, iterate, or kill

### Metric Anti-Patterns

1. **Vanity metrics**: Total signups (ever) instead of active users. Always use rates and ratios.
2. **Measuring too many things**: Focus on 3-5 key metrics per team. More causes paralysis.
3. **Gaming metrics**: If a metric becomes a target, people optimize for the metric, not the outcome.
4. **Ignoring leading indicators**: Only tracking revenue (lagging) instead of activation (leading).
5. **No baseline**: Setting targets without knowing the current state.
6. **Cherry-picking timeframes**: Showing the best week instead of the trend.
""",
)

product_competitive_brief = Skill(
    name="product_competitive_brief",
    description="Competitive analysis framework with landscape mapping, feature comparison, positioning, win/loss analysis, and response playbooks.",
    category="planning",
    agent_ids=[AgentID.STRAT, AgentID.SALES, AgentID.MKT],
    knowledge_summary="Competitive landscape mapping (direct/indirect/potential), feature comparison matrix, positioning statements, win/loss analysis framework, and competitive response playbooks.",
    knowledge="""
## Product Competitive Analysis Framework

### Competitive Landscape Mapping

**Categories of Competitors:**

1. **Direct Competitors** (Same problem, same solution approach)
   - They solve the exact same problem for the same audience
   - These are who your prospects compare you against
   - Example: Slack vs Microsoft Teams vs Discord (for work)

2. **Indirect Competitors** (Same problem, different solution)
   - They address the same underlying need differently
   - Often overlooked but can disrupt your category
   - Example: Slack vs Email vs In-person standups

3. **Potential Competitors** (Adjacent market players)
   - Currently serve an adjacent market but could expand
   - Often have distribution advantage
   - Example: Salesforce expanding into team collaboration

**Landscape Map Template:**

| Competitor | Type | Target Market | Key Strength | Key Weakness | Threat Level |
|-----------|------|---------------|-------------|-------------|-------------|
| Competitor A | Direct | Enterprise | Brand + integrations | Expensive, slow | High |
| Competitor B | Direct | SMB | Low price, easy UX | Limited features | Medium |
| Competitor C | Indirect | Mid-market | Existing distribution | Not purpose-built | Medium |
| Startup D | Potential | Developer-first | Technical innovation | No enterprise sales | Low (rising) |

### Feature Comparison Matrix

| Feature / Capability | Our Product | Comp A | Comp B | Comp C | Buyer Importance |
|---------------------|------------|--------|--------|--------|-----------------|
| Bulk user management | Full | Partial | None | Full | Must-have |
| SSO/SAML | Full | Full | Paid add-on | Full | Must-have |
| Real-time collaboration | Full | Full | Basic | None | Differentiator |
| API / Integrations | 50+ | 200+ | 10 | 30 | Differentiator |
| Mobile app | iOS + Android | iOS only | Both | None | Nice-to-have |
| Pricing (per user/mo) | $12 | $25 | $5 | $15 | Decision factor |
| Free tier | Yes (5 users) | No | Yes (unlimited) | Yes (3 users) | Nice-to-have |

**Rating:** Full = complete capability; Partial = exists but limited; Basic = minimal; None = not available

### Competitive Positioning

**Value Proposition Canvas (per competitor):**

For each major competitor, document:
- **Their value prop**: What they promise customers
- **Their ideal customer**: Who they serve best
- **Their weakness**: Where they fall short
- **Our advantage**: Why we win against them specifically

**Positioning Statement Template:**
"For [target customer] who [need/problem], [our product] is a [category] that [key benefit]. Unlike [primary competitor], we [key differentiation]."

Example:
"For mid-market SaaS companies who need to manage complex team permissions at scale, PermissionHub is a workspace management platform that reduces admin overhead by 80%. Unlike Enterprise Suite Corp, we offer intuitive bulk management without requiring a dedicated admin team or six-figure contract."

**Positioning Map:**
Plot competitors on two axes that matter most to buyers:
- X-axis: Ease of use (simple --> complex)
- Y-axis: Feature completeness (basic --> comprehensive)
- Find the open space where you can own a position

### Win/Loss Analysis Framework

**Interview Template (15-20 minutes, post-decision):**

For WINS:
1. What problem were you trying to solve?
2. What alternatives did you evaluate?
3. What was the deciding factor in choosing us?
4. What almost made you choose someone else?
5. How would you describe us to a colleague?

For LOSSES:
1. What problem were you trying to solve?
2. What did we do well during the evaluation?
3. What was the primary reason you chose the other solution?
4. Was there anything we could have done differently?
5. What would make you reconsider in the future?

**Pattern Identification:**
After 20+ interviews, look for:
- **Common win themes**: "Ease of setup," "pricing transparency," "responsive support"
- **Common loss themes**: "Missing integration X," "too expensive for our size," "competitor had existing relationship"
- **Competitive displacement rate**: How often do we win vs lose against each competitor?
- **Deal stage losses**: At which stage do we lose most? (Demo? Pricing? Security review?)

**Win/Loss Dashboard:**

| Competitor | Wins | Losses | Win Rate | Top Win Reason | Top Loss Reason |
|-----------|------|--------|----------|----------------|-----------------|
| Comp A | 12 | 8 | 60% | Better UX | Fewer integrations |
| Comp B | 15 | 3 | 83% | More features | Price |
| Comp C | 5 | 7 | 42% | Modern architecture | Their existing contract |

### Market Share Estimation

**Bottom-Up (from known data):**
- Count known customers of each competitor (job postings, case studies, review sites)
- Estimate average deal size per segment
- Calculate estimated revenue: customers x avg deal size

**Top-Down (from market size):**
- Total addressable market (TAM) from analyst reports
- Estimated market share: competitor revenue / TAM
- Cross-reference with G2/Gartner/Forrester rankings

### Competitive Response Playbook

**When competitor launches a feature you have:**
- Action: Highlight your version's maturity and depth in marketing
- Sales: Arm with comparison talking points
- Timeline: Within 1 week

**When competitor launches a feature you don't have:**
- Action: Assess demand (customer requests, deal impact), prioritize if warranted
- Sales: Acknowledge the gap, redirect to your strengths
- Marketing: Publish content on your alternative approach
- Timeline: Assessment within 2 weeks, decision within 1 month

**When competitor changes pricing (lower):**
- Action: Do NOT automatically match. Analyze the impact on deals.
- Sales: Reframe on value, not price. "We cost more because..."
- Product: Consider a lighter tier if demand exists
- Timeline: Monitor for 1 month before reacting

**When competitor gets acquired:**
- Action: Contact their unhappy customers (they will exist)
- Marketing: Position stability and independence as benefits
- Sales: Reach out to in-progress deals with the competitor
- Timeline: Immediately

**When new entrant appears:**
- Action: Monitor, don't panic. Most startups fail.
- Product: Note their unique angle -- is it resonating?
- Marketing: If they get traction, address their narrative
- Timeline: Review quarterly unless they win your deals
""",
)


# =============================================================================
# Productivity Skills (category="operations", available to ALL agents)
# =============================================================================

task_prioritization = Skill(
    name="task_prioritization",
    description="Task and work prioritization frameworks including Eisenhower Matrix, time-boxing, weekly planning, and energy management.",
    category="operations",
    agent_ids=[],  # Available to ALL agents
    knowledge_summary="Eisenhower Matrix (urgent/important quadrants), Pomodoro and deep work time-boxing, weekly planning templates, context switching costs, meeting audit framework, and energy management.",
    knowledge="""
## Task & Work Prioritization Framework

### Eisenhower Matrix (Urgent vs Important)

| | Urgent | Not Urgent |
|-|--------|-----------|
| **Important** | **DO NOW**: Crises, deadlines, critical bugs, customer escalations. Handle immediately, limit to 1-2 hours/day. | **SCHEDULE**: Strategy, planning, relationship building, skill development, proactive improvements. This is where high-impact work lives. Block 60% of your time here. |
| **Not Important** | **DELEGATE**: Most emails, routine requests, some meetings, status updates. If someone else can do 80% as well, delegate. Move to async when possible. | **ELIMINATE**: Time-wasters, unnecessary meetings, excessive social media, over-engineering, perfectionism on low-stakes tasks. Ruthlessly cut these. |

**Weekly allocation target:**
- Quadrant 1 (Do Now): 15-20% of time
- Quadrant 2 (Schedule): 55-65% of time
- Quadrant 3 (Delegate): 10-15% of time
- Quadrant 4 (Eliminate): <5% of time

### Time-Boxing Methodology

**Pomodoro Technique (25/5 Pattern):**
1. Choose a task
2. Set a timer for 25 minutes
3. Work with full focus (no email, no Slack, no context switching)
4. Take a 5-minute break (stand, stretch, water)
5. After 4 Pomodoros, take a 15-30 minute break

Best for: Routine tasks, email processing, documentation, code review

**Deep Work Blocks (90-Minute Sessions):**
1. Block 90 minutes on your calendar (treat as a meeting)
2. Close all communication tools (email, Slack, phone on DND)
3. Work on ONE high-value task
4. Take a 20-minute break
5. Maximum 2-3 deep work blocks per day

Best for: Strategy, writing, complex problem-solving, architecture, creative work

**Time-Boxing Rules:**
- Assign a fixed time to each task BEFORE starting
- When the time is up, stop (even if not finished). Assess: continue or switch?
- If a task keeps exceeding its time box, it needs to be broken down smaller
- Review time estimates weekly to calibrate

### Weekly Planning Template

**Review Prior Week (10 minutes, Friday or Sunday):**
- **Wins**: 3 things accomplished. Celebrate progress.
- **Incomplete**: What didn't get done? Why? Carry forward or drop?
- **Learnings**: One thing learned or improved this week.

**Plan This Week (15 minutes, Sunday or Monday morning):**
- **Top 3 Priorities**: The three things that, if completed, make this a successful week
- **Scheduled Commitments**: Meetings, deadlines, events (non-negotiable time)
- **Buffer for Reactive Work**: Block 20-30% of time for unexpected tasks
- **One Investment Task**: Something that compounds over time (learning, process improvement, relationship building)

**Template:**
```
WEEK OF: [Date]

TOP 3 PRIORITIES:
1. [ ] ___________________________ (due: ___)
2. [ ] ___________________________ (due: ___)
3. [ ] ___________________________ (due: ___)

SCHEDULED:
- Mon: [meetings/deadlines]
- Tue: [meetings/deadlines]
- Wed: [meetings/deadlines]
- Thu: [meetings/deadlines]
- Fri: [meetings/deadlines]

INVESTMENT TASK:
- [ ] ___________________________

BUFFER BLOCKED: [X hours for unexpected work]
```

### Daily Standup Format (2 Minutes Max Per Person)

1. **Yesterday**: What I completed (not "worked on" -- completed)
2. **Today**: What I will complete today (one specific commitment)
3. **Blockers**: Anything preventing progress (need help/decision/access)

Anti-patterns: Long stories, status updates that should be async, problem-solving in standup (take it offline).

### Context Switching Cost Awareness

**The science:** Every task switch costs 15-25 minutes of refocus time. Switching 10 times a day = 2.5-4 hours of lost productivity.

**Batch similar tasks:**
- Email: Process 2-3 times per day, not continuously
- Slack: Check every 60-90 minutes, not every ping
- Code reviews: Batch in one block, not scattered
- Meetings: Cluster on specific days if possible

**Protect flow state:**
- Block "no meeting" days (many companies do Tues/Thurs)
- Turn off notifications during deep work
- Use status indicators ("Heads down until 2pm")
- It's okay to not respond immediately to non-urgent messages

### Meeting Audit Framework

Before accepting any meeting, ask:
1. **Does this need a meeting?** Can it be resolved via Slack, email, or a Loom video?
2. **Do I need to be there?** Can I send input async and get notes after?
3. **What's the decision?** If there's no decision to make, it's probably an FYI (async).
4. **Is 30 minutes enough?** Default to 25 min (not 30), 50 min (not 60).

**Meeting audit results (typical):**
- 30% of meetings can be eliminated (converted to async)
- 20% of meetings can be shortened by half
- 20% of attendees in each meeting don't need to be there

### Energy Management

**Map your energy throughout the day:**
- **Peak energy hours** (usually morning): Reserve for important, creative, strategic work
- **Medium energy hours** (usually early afternoon): Meetings, collaboration, code review
- **Low energy hours** (usually late afternoon): Routine tasks, email, admin, planning

**Energy management tips:**
- Don't schedule your hardest work during your lowest energy period
- Take real breaks (walk outside, not scroll social media)
- Protect sleep -- one hour of lost sleep costs more than one hour of work
- Eat lunch away from your desk at least 3x per week
- Exercise is a productivity tool, not a time cost

### Saying No / Later / Delegate Decision Tree

When a new request comes in:
1. Is this aligned with my top 3 priorities? YES -> Consider doing it. NO -> Continue.
2. Is this urgent AND important? YES -> Do it now. NO -> Continue.
3. Can someone else do this 80% as well? YES -> Delegate. NO -> Continue.
4. Can this wait until next week? YES -> Schedule it for next week. NO -> Continue.
5. What will I NOT do if I do this? -> Make the trade-off explicit and decide.

**How to say no:**
- "I can't take this on this week, but I can help next Thursday."
- "This isn't my area of expertise. [Name] would be better suited."
- "I'm focused on [priority]. If this is more important, let's discuss reprioritizing."
""",
)

meeting_management = Skill(
    name="meeting_management",
    description="Effective meeting practices including meeting types, facilitation techniques, note templates, and async alternatives.",
    category="operations",
    agent_ids=[],  # Available to ALL agents
    knowledge_summary="Meeting types (decision/brainstorm/status/1:1), pre-meeting requirements, facilitation techniques (timekeeper, parking lot, round-robin), meeting notes template, and async alternatives.",
    knowledge="""
## Effective Meeting Management Framework

### Meeting Types & Formats

**1. Decision Meeting (30 min max)**
- Purpose: Make a specific decision with the right stakeholders
- Format: Present options (5 min) > Discuss trade-offs (15 min) > Decide (5 min) > Document (5 min)
- Attendees: Decision maker + 2-4 informed perspectives
- Output: Written decision with rationale and next steps
- Rule: If no decision is made, schedule a follow-up with a deadline

**2. Brainstorm Meeting (45 min)**
- Purpose: Generate ideas without judgment, then converge
- Format: Define challenge (5 min) > Diverge/ideate (20 min) > Converge/cluster (10 min) > Prioritize (10 min)
- Attendees: 4-8 diverse perspectives (too few = limited ideas, too many = chaos)
- Output: Prioritized list of 3-5 ideas to explore
- Rule: No criticism during divergence phase. "Yes, and..." not "No, but..."

**3. Status Update (Should be ASYNC)**
- Purpose: Share progress, surface blockers
- Better format: Written update via Slack/email/project tool
- If meeting is truly needed: 15 min max, round-robin, only discuss blockers
- Output: Updated project tracker, blockers assigned to owners
- Rule: If no blockers, skip the meeting this week

**4. One-on-One (30 min weekly)**
- Purpose: Coaching, feedback, career development, relationship building
- Format: Report's agenda first (15 min) > Manager's agenda (10 min) > Action items (5 min)
- This is the report's meeting, not the manager's
- Output: Action items documented, follow-up on previous items
- Rule: Never cancel. Move if needed, but never skip. This builds trust.

**5. Retrospective (60 min)**
- Purpose: Continuous improvement after a milestone
- Format: What went well (15 min) > What didn't (15 min) > Root causes (15 min) > Action items (15 min)
- Attendees: Full team that executed the work
- Output: 2-3 specific process improvements with owners
- Rule: Focus on systems, not blame. "How do we prevent this?" not "Whose fault was it?"

### Pre-Meeting Requirements

Every meeting invitation MUST include:
1. **Clear purpose statement**: "We need to decide X" or "We need to align on Y"
2. **Agenda with time allocations**: "5 min: context, 15 min: discussion, 5 min: decision"
3. **Required pre-reads**: Distributed at least 24 hours ahead. "Please review [doc] before the meeting."
4. **Right attendees only**: Ask "Does [person] need to be here?" If their role is FYI, send notes after.
5. **Expected outcome**: "By end of meeting, we will have decided X"

**If a meeting invite lacks purpose and agenda: Decline or request them.**

### Meeting Facilitation Techniques

**Timekeeper Role:**
- Assign someone (not the facilitator) to track time
- Give warnings: "5 minutes left on this topic"
- The facilitator focuses on content; timekeeper focuses on flow

**Parking Lot:**
- Create a visible "parking lot" for off-topic items
- When someone raises an unrelated point: "Great thought -- adding to the parking lot"
- Review parking lot at end: assign owners or schedule separate discussion
- This prevents derailing without dismissing contributions

**Round-Robin for Quiet Participants:**
- Go around the table/room and give each person 60 seconds
- "Let's hear from everyone. Sarah, what's your take?"
- Prevents dominant voices from monopolizing
- Give introverts a heads-up before the meeting if possible

**Explicit Decision-Making Method:**
Choose BEFORE the meeting starts:
- **Consensus**: Everyone agrees (slow but high buy-in)
- **Majority**: Vote, >50% wins (faster, moderate buy-in)
- **RAPID**: One person decides after input (fastest, clear ownership)
  - R=Recommend, A=Agree, P=Perform, I=Input, D=Decide

**Silent Brainstorming:**
- Everyone writes ideas on sticky notes for 5 minutes silently
- Then share and cluster
- Prevents anchoring bias and gives introverts equal voice

### Meeting Notes Template

```
MEETING: [Title]
DATE: [Date] | TIME: [Start-End]
ATTENDEES: [Names]
FACILITATOR: [Name]
NOTE-TAKER: [Name]

PURPOSE: [Why we met]

DECISIONS MADE:
1. [Decision] -- Decided by [who], rationale: [why]
2. [Decision] -- Decided by [who], rationale: [why]

ACTION ITEMS:
| Action | Owner | Deadline |
|--------|-------|----------|
| [Task] | [Name] | [Date] |
| [Task] | [Name] | [Date] |

OPEN QUESTIONS:
- [Question] -- Owner: [Name], follow up by [Date]

PARKING LOT (for future discussion):
- [Topic]

NEXT MEETING: [Date, time, purpose]
```

**Share notes within 2 hours of meeting end.** If you can't commit to this, assign a dedicated note-taker.

### Async Alternatives

| Meeting Type | Async Alternative | Tool |
|-------------|-------------------|------|
| Status update | Written update post | Slack, Notion, email |
| Demo/showcase | Recorded Loom video | Loom, YouTube unlisted |
| Decision (low-stakes) | Written proposal + comments | Google Docs, Notion |
| Brainstorm | Async ideation board | FigJam, Miro, Slack thread |
| FYI/announcement | Written memo | Email, Slack, Notion |
| Feedback on work | Inline comments | Figma, Google Docs, PR review |

**Async decision template:**
```
PROPOSAL: [What I'm proposing]
CONTEXT: [Why, 2-3 sentences]
OPTIONS: [A, B, C with trade-offs]
RECOMMENDATION: [My suggestion and why]
DEADLINE: [Respond by date]
SILENCE = APPROVAL: [Yes/No]
```

### Meeting Hygiene Rules

1. **Start and end on time**: Respect everyone's calendar. Start even if someone is late.
2. **No laptops unless presenting**: If the meeting doesn't warrant attention, you shouldn't be in it.
3. **Standing meetings for <15 min**: Creates natural urgency to be concise.
4. **Default to 25 or 50 minutes**: Give people a 5-10 min buffer between meetings.
5. **Meeting-free blocks**: Protect at least one 3-hour block per day for deep work.
6. **Camera on for remote**: Builds connection and accountability (but respect burnout -- camera-optional Fridays).
7. **One meeting = one decision**: If you need multiple decisions, split into multiple (shorter) meetings.
8. **Rotate facilitator**: Don't let one person always run meetings. Build the skill across the team.
""",
)

goal_setting_framework = Skill(
    name="goal_setting_framework",
    description="Goal setting and tracking methodology with OKRs, SMART goals, quarterly planning cycles, and retrospective formats.",
    category="operations",
    agent_ids=[],  # Available to ALL agents
    knowledge_summary="OKR framework with scoring (0.7 target), SMART goals with examples, goal cascade from company to individual, quarterly planning cycle, goal tracking template, and common mistakes.",
    knowledge="""
## Goal Setting & Tracking Framework

### OKR Framework (Objectives & Key Results)

**Objective:** A qualitative, inspirational statement of what you want to achieve.
- Time-bound (quarterly or annually)
- Ambitious but achievable
- Aligned to company/team strategy
- Written in plain language (not metric-speak)

**Key Results:** 3-5 measurable outcomes that prove the objective was achieved.
- Must be quantifiable (number, percentage, yes/no)
- Outcome-based (not activity-based)
- Scoring: 0.0-1.0 scale, with 0.7 as the target (stretch goals)
  - 0.0-0.3: Failed to make meaningful progress
  - 0.4-0.6: Made progress but fell short
  - 0.7-0.8: Hit the target (aspirational goals should land here)
  - 0.9-1.0: Exceeded expectations (if this happens consistently, goals aren't ambitious enough)

**Example OKR:**
Objective: "Become the go-to platform for mid-market team collaboration"

| Key Result | Target | Q1 Actual | Score |
|-----------|--------|-----------|-------|
| Increase mid-market activation rate from 28% to 45% | 45% | 41% | 0.76 |
| Achieve NPS of 50+ among mid-market accounts | 50 | 47 | 0.70 |
| Reduce time-to-value from 14 days to 5 days | 5 days | 7 days | 0.67 |
| Win 3 competitive displacements against Enterprise Suite Corp | 3 | 2 | 0.67 |

Overall Objective Score: 0.70 (on target)

**OKR Writing Anti-Patterns:**
- "Launch feature X" -- This is a task, not a key result. What outcome does the feature drive?
- "Increase revenue" -- By how much? From what baseline? By when?
- "Improve customer satisfaction" -- Unmeasurable. Use NPS, CSAT, or CES with a target number.

### SMART Goals

Each goal must be:
- **Specific**: Clear, unambiguous. "Reduce checkout abandonment" not "improve sales."
- **Measurable**: Has a number. "from 67% to 45%" not "significantly reduce."
- **Achievable**: Challenging but realistic with available resources.
- **Relevant**: Aligned to team and company priorities.
- **Time-bound**: Has a deadline. "by end of Q2" not "eventually."

**Example Transformation:**
- Vague: "Get more customers"
- SMART: "Increase monthly new customer signups from 120 to 200 by June 30, 2024, through improved onboarding conversion and targeted Google Ads campaigns"

### Goal Cascade (Alignment)

**Company Level (Annual):**
- CEO sets 3-5 company OKRs
- Example: "Achieve $10M ARR by year end"

**Department Level (Quarterly):**
- Each department creates OKRs that contribute to company OKRs
- Example (Product): "Reduce churn by improving core product experience"

**Team Level (Quarterly):**
- Each team creates OKRs that contribute to department OKRs
- Example (Growth Team): "Increase activation rate from 28% to 40%"

**Individual Level (Quarterly):**
- Each person has 2-3 OKRs aligned to team goals
- Example (PM): "Ship new onboarding flow that achieves 40% activation in A/B test"

**Alignment check:** Can every individual OKR trace up to a company OKR? If not, it may be misaligned work.

### Quarterly Planning Cycle

| Week | Activity | Participants |
|------|----------|-------------|
| Week 1 | Draft OKRs: Each team proposes their objectives and key results | Team leads + members |
| Week 2 | Cross-functional alignment: Share drafts, identify dependencies, resolve conflicts | All team leads together |
| Week 3 | Finalize and communicate: Lock OKRs, share company-wide, kick off execution | Leadership + all teams |
| Weekly | Check-in: 15-min review of KR progress, surface blockers | Team leads |
| Mid-Quarter | Score and adjust: Preliminary scoring, adjust approach if off-track (but don't change the OKR) | Team leads + leadership |
| End of Quarter | Score, retrospective, and planning: Final scores, learnings, draft next quarter | Full team |

### Goal Tracking Template

| Goal | Metric | Baseline | Target | Current | Status | Owner | Key Initiatives |
|------|--------|----------|--------|---------|--------|-------|-----------------|
| Improve activation | Activation rate | 28% | 40% | 34% | On Track | PM Lead | New onboarding, in-app tips |
| Reduce support load | Tickets/user/mo | 0.8 | 0.4 | 0.6 | At Risk | Support Lead | Help center, chatbot |
| Expand mid-market | Mid-market ARR | $1.2M | $2.0M | $1.5M | On Track | Sales Lead | Enterprise features, pricing tier |

**Status definitions:**
- **On Track**: Progress at or above expected pace
- **At Risk**: Below expected pace but recoverable with intervention
- **Behind**: Significantly below pace, likely to miss without major change
- **Complete**: Target achieved

### Common Goal-Setting Mistakes

1. **Too many goals**: More than 3-5 OKRs per team creates dilution. Prioritize ruthlessly.
2. **Sandbagging**: Setting easy targets to guarantee "success." If you always score 1.0, goals are too easy.
3. **No connection to strategy**: Goals that don't ladder up to company priorities waste effort.
4. **Measuring activity, not outcomes**: "Ship 5 features" is activity. "Improve retention by 10%" is an outcome.
5. **Setting and forgetting**: Goals need weekly check-ins. Set a recurring 15-min review.
6. **No owner**: Every goal needs exactly one person accountable. "The team" is not an owner.
7. **Changing goals mid-quarter**: Undermines commitment. Change the approach, not the goal (unless strategy shifts).
8. **Punishing misses**: If missing a stretch goal has consequences, people will sandbar. Celebrate learning from ambitious targets.

### Retrospective Format (End of Quarter)

**1. What Went Well (15 min)**
- List wins and contributing factors
- "We hit activation target because we invested in onboarding research first"

**2. What Didn't Go Well (15 min)**
- List misses and contributing factors (systems, not blame)
- "We missed the support ticket goal because we underestimated chatbot development time"

**3. What to Change (15 min)**
- Specific, actionable improvements for next quarter
- "Start OKR planning 2 weeks earlier to allow for cross-team alignment"

**4. Scores & Learnings (15 min)**
- Score each KR on 0.0-1.0
- Identify patterns: What types of goals do we consistently miss?
- Carry forward insights to next quarter's planning
""",
)

project_status_tracking = Skill(
    name="project_status_tracking",
    description="Project status tracking and reporting with health indicators, risk management, dependency tracking, and retrospective templates.",
    category="operations",
    agent_ids=[],  # Available to ALL agents
    knowledge_summary="Project health indicators (scope/timeline/budget/quality/team), RAG status reports, risk register management, dependency tracking, communication cadence, and retrospective templates.",
    knowledge="""
## Project Status Tracking & Reporting Framework

### Project Health Indicators

Monitor these five dimensions continuously:

**1. Scope Health**
- Feature-complete percentage vs plan
- Change request count and impact
- Requirements stability (how often do requirements change?)
- RAG: GREEN if >90% stable, YELLOW if 70-90%, RED if <70%

**2. Timeline Health**
- Milestone completion vs planned dates
- Sprint velocity trend
- Critical path tasks on schedule?
- RAG: GREEN if on time, YELLOW if <1 week delay, RED if >1 week delay

**3. Budget Health**
- Percentage consumed vs percentage complete
- Burn rate vs planned spend
- Remaining budget vs estimated cost to complete
- RAG: GREEN if within 10%, YELLOW if 10-25% over, RED if >25% over

**4. Quality Health**
- Bug count by severity (critical/high/medium/low)
- Test coverage percentage
- Performance metrics vs targets
- RAG: GREEN if <3 high/critical bugs, YELLOW if 3-5, RED if >5

**5. Team Health**
- Utilization rate (70-80% is healthy; >90% means burnout risk)
- Morale indicators (retro feedback, 1:1 sentiment)
- Key person dependencies (bus factor)
- RAG: GREEN if stable, YELLOW if 1 concern, RED if multiple concerns

### Status Report Template

**Project: [Name]**
**Report Date: [Date]**
**Report Author: [Name]**
**Overall Status: [GREEN / YELLOW / RED]**

**Executive Summary (3 sentences max):**
"Phase 2 of the permissions project is on track for the March 15 launch. Beta testing showed 0 critical issues across 200 admin accounts. One risk: the data migration script needs optimization before GA (mitigation in progress)."

**Milestone Tracker:**

| Milestone | Planned Date | Actual Date | Status | Notes |
|-----------|-------------|-------------|--------|-------|
| Design complete | Feb 1 | Feb 1 | GREEN | On time |
| Beta launch | Feb 15 | Feb 14 | GREEN | 1 day early |
| Beta feedback review | Mar 1 | Mar 1 | GREEN | On time |
| GA launch | Mar 15 | -- | YELLOW | Migration script at risk |
| Post-launch review | Mar 22 | -- | GREEN | Scheduled |

**Key Metrics:**

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Beta adoption | 78% | 70% | GREEN |
| Avg setup time | 6 min | 5 min | YELLOW |
| Critical bugs | 0 | 0 | GREEN |
| Support tickets (beta) | 8 | <15 | GREEN |

**Risk Register Update:**

| Risk | Probability | Impact | Mitigation | Owner | Status |
|------|------------|--------|------------|-------|--------|
| Migration script too slow for large accounts | Medium | High | Batch processing + parallel execution | Eng Lead | In Progress |
| Designer PTO during final QA | Low | Medium | Design system handles most cases; backup designer identified | Design Lead | Mitigated |

**Decisions Needed:**
1. Approve 1-week beta extension to gather more data (recommend: yes)
2. Allocate QA contractor for migration testing ($2,000)

**Next Period Plan:**
- Complete migration script optimization (by Mar 8)
- Run load test with 10,000 user accounts (by Mar 10)
- Final QA pass (Mar 11-13)
- GA launch (Mar 15)

### Risk Management

**Risk vs Issue:**
- **Risk**: Something that MIGHT happen (future, uncertain)
- **Issue**: Something that HAS happened (present, certain)
- Risks need mitigation plans. Issues need resolution plans.

**Risk Register:**

| ID | Risk Description | Category | Probability | Impact | Risk Score | Mitigation Strategy | Owner | Status | Last Updated |
|----|-----------------|----------|-------------|--------|------------|---------------------|-------|--------|-------------|
| R1 | Key engineer leaves mid-project | People | Low | High | Medium | Cross-train backup, document architecture | Eng Manager | Active | Mar 1 |
| R2 | API rate limits hit during migration | Technical | Medium | Medium | Medium | Implement backoff + batching | Eng Lead | In Progress | Mar 3 |
| R3 | Vendor delays API documentation | External | High | Low | Medium | Use existing docs + direct support contact | PM | Active | Feb 28 |

**Risk Score Matrix:**

| | Low Impact | Medium Impact | High Impact |
|-|-----------|---------------|-------------|
| **High Probability** | Medium | High | Critical |
| **Medium Probability** | Low | Medium | High |
| **Low Probability** | Low | Low | Medium |

**Escalation Criteria:**
- Any risk that becomes a CRITICAL score
- Any risk whose probability increased in the last period
- Any risk without an active mitigation plan
- Any issue unresolved for >3 business days

### Dependency Tracking

**Internal Dependencies:**

| Dependency | Providing Team | Needed By | Status | Impact if Delayed |
|-----------|---------------|-----------|--------|-------------------|
| Auth API v3 | Platform team | Mar 5 | On Track | Blocks beta launch by same delay |
| Design system update | Design team | Mar 1 | Complete | -- |
| QA test plan | QA team | Mar 8 | At Risk | Delays GA launch |

**External Dependencies:**

| Dependency | Vendor/Partner | Needed By | Status | Fallback Plan |
|-----------|---------------|-----------|--------|---------------|
| SSO provider API docs | Okta | Feb 28 | Delayed | Use existing v2 docs |
| Audit compliance cert | SOC2 auditor | Mar 30 | On Track | -- |

**Blocked Items:**

| Item | Blocked By | Impact | Unblock Plan | Owner | ETA |
|------|-----------|--------|-------------|-------|-----|
| Migration testing | QA test plan incomplete | Delays GA by 2 days | PM escalating to QA lead | PM | Mar 6 |

### Communication Cadence

| Meeting | Frequency | Audience | Content |
|---------|-----------|----------|---------|
| Daily standup | Daily (15 min) | Execution team | Blockers + today's plan |
| Weekly status report | Weekly (async) | Stakeholders | Written report (template above) |
| Bi-weekly stakeholder review | Bi-weekly (30 min) | Sponsors + stakeholders | Demo + discussion |
| Monthly steering committee | Monthly (60 min) | Exec sponsors | Strategic review + decisions |

### Project Retrospective Template

**Project: [Name]**
**Duration: [Start] to [End]**
**Facilitator: [Name]**
**Participants: [Names]**

**1. Timeline Summary:**
- Planned: [start] to [end] ([X] weeks)
- Actual: [start] to [end] ([Y] weeks)
- Variance: [+/- Z weeks] -- Why?

**2. What Worked Well:**
- [Item]: [Why it worked, how to repeat]
- [Item]: [Why it worked, how to repeat]

**3. What Didn't Work:**
- [Item]: [What happened, root cause]
- [Item]: [What happened, root cause]

**4. Root Cause Analysis (for major issues):**
Use "5 Whys" technique:
1. Why did the launch delay? -- Migration script was too slow.
2. Why was it too slow? -- It processed records sequentially.
3. Why sequentially? -- The original design didn't anticipate 10K+ accounts.
4. Why didn't we anticipate? -- Load testing wasn't in the original plan.
5. Why wasn't it planned? -- We skipped the technical design review for migration.
Root cause: Missing technical design review for migration component.

**5. Action Items for Future Projects:**

| Action | Owner | Deadline | Category |
|--------|-------|----------|----------|
| Add technical design review to project kickoff checklist | Eng Manager | Next project | Process |
| Include load testing in all QA plans | QA Lead | Ongoing | Quality |
| Create migration playbook template | PM | Apr 15 | Documentation |

**6. Quantitative Review:**

| Metric | Planned | Actual | Notes |
|--------|---------|--------|-------|
| Duration | 8 weeks | 9 weeks | +1 week for migration |
| Budget | $50K | $52K | QA contractor |
| Scope delivered | 100% | 95% | Deferred 1 nice-to-have |
| Bugs at launch | 0 critical | 0 critical | Success |
| Team satisfaction | -- | 4.2/5 | From retro survey |
""",
)


# =============================================================================
# Content Creation Skills (category="content")
# =============================================================================

content_strategy = Skill(
    name="content_strategy",
    description="Content strategy framework with audit methodology, pillar planning, editorial calendar design, funnel mapping, and governance.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT, AgentID.STRAT],
    knowledge_summary="Content audit methodology, pillar framework with sub-topics and keyword clusters, editorial calendar design, content funnel mapping (awareness to retention), repurposing strategy, and governance.",
    knowledge="""
## Content Strategy Framework

### Content Audit Methodology

**Step 1: Inventory All Existing Content**
Create a spreadsheet with every content asset:

| URL/Location | Title | Type | Date Published | Author | Topic/Pillar | Word Count | Status |
|-------------|-------|------|----------------|--------|-------------|-----------|--------|

**Step 2: Assess Quality, Relevance, and Performance**
For each piece, score on:
- **Quality** (1-5): Writing quality, accuracy, visual design
- **Relevance** (1-5): Still accurate and aligned with current strategy?
- **Performance** (1-5): Traffic, engagement, conversions, rankings

| Content | Quality | Relevance | Performance | Action |
|---------|---------|-----------|-------------|--------|
| "Getting Started Guide" | 4 | 5 | 5 | Keep, minor update |
| "2022 Trends Report" | 4 | 1 | 2 | Archive |
| "Pricing Comparison" | 3 | 5 | 3 | Update + optimize |
| [Gap: No migration guide] | -- | -- | -- | Create new |

**Step 3: Identify Gaps and Redundancies**
- What topics are missing from your content library?
- Are there multiple pieces covering the same topic? Consolidate.
- What content do competitors have that you don't?

**Step 4: Create Update/Archive/Create Plan**
- **Update**: High-relevance content that needs refreshing (rewrite, add data, improve SEO)
- **Archive**: Outdated or low-performing content (redirect URLs, don't just delete)
- **Create**: New content for identified gaps

### Content Pillar Framework

**What are content pillars?**
3-5 core topics that align to your business goals and audience needs. All content should trace back to a pillar.

**Example Pillars for a Project Management SaaS:**
1. **Remote Team Productivity** -- Align to product value prop
2. **Project Management Best Practices** -- Establish expertise
3. **Agile & Scrum Methodology** -- Serve target audience
4. **Team Communication** -- Related pain point
5. **Leadership & Management** -- Broaden audience

**Each pillar has:**
- 5-10 sub-topics (long-tail content opportunities)
- Keyword clusters mapped to each sub-topic
- A pillar page (comprehensive 3000+ word guide) with links to sub-topic posts

Example for "Remote Team Productivity":
- Sub-topic 1: "Async communication best practices" (keyword: async communication)
- Sub-topic 2: "Remote meeting fatigue solutions" (keyword: meeting fatigue)
- Sub-topic 3: "Time zone management for distributed teams" (keyword: time zone management)
- Sub-topic 4: "Remote team building activities" (keyword: virtual team building)
- Sub-topic 5: "Home office setup for productivity" (keyword: home office productivity)

### Editorial Calendar Design

**Monthly Themes:**
Each month has a theme aligned to a content pillar and business objective.
- January: "New Year Planning" (Pillar: Project Management)
- February: "Team Collaboration" (Pillar: Communication)
- March: "Remote Work" (Pillar: Remote Productivity)

**Weekly Content Types:**

| Day | Content Type | Channel | Purpose |
|-----|-------------|---------|---------|
| Monday | Blog post | Website + email | SEO + thought leadership |
| Tuesday | Social carousel | LinkedIn + Instagram | Engagement |
| Wednesday | Newsletter | Email | Nurture + retain |
| Thursday | Video/Loom | YouTube + social | Education + reach |
| Friday | Community post | Slack/Discord/social | Engagement + UGC |

**Production Timeline:**

| Week | Activity |
|------|----------|
| Week 1 | Topic research, outline, keyword targeting |
| Week 2 | First draft + visuals |
| Week 3 | Review, edit, approval |
| Week 4 | Publish, distribute, promote |

### Content Funnel Mapping

**Awareness (Top of Funnel):**
- Goal: Attract new audience, build brand awareness
- Content types: Educational blog posts, infographics, short videos, social posts, podcasts
- Metrics: Traffic, impressions, social shares, new visitors
- CTA: Subscribe, follow, download free resource

**Consideration (Middle of Funnel):**
- Goal: Educate prospects about solutions, build trust
- Content types: Case studies, comparison guides, webinars, whitepapers, email sequences
- Metrics: Time on page, email signups, webinar registrations, return visits
- CTA: Start free trial, book a demo, download guide

**Decision (Bottom of Funnel):**
- Goal: Convert prospects to customers
- Content types: Product demos, free trials, ROI calculators, customer testimonials, pricing pages
- Metrics: Trial signups, demo bookings, conversion rate
- CTA: Start free trial, buy now, talk to sales

**Retention (Post-Purchase):**
- Goal: Reduce churn, increase expansion
- Content types: Tutorials, product updates, newsletters, community content, advanced guides
- Metrics: Feature adoption, NPS, expansion revenue, churn rate
- CTA: Upgrade, refer a friend, join community

### Content Repurposing Strategy

**One Pillar Piece Becomes 10+ Assets:**

Start with one comprehensive pillar piece (e.g., "Complete Guide to Remote Team Management"):
1. **Blog series**: Break into 5 focused posts (one per chapter)
2. **Social posts**: Extract 15-20 key insights as standalone posts
3. **Email newsletter**: 4-part email series covering highlights
4. **Video**: Record a 10-min overview for YouTube
5. **Podcast**: Discuss key points in a 20-min episode
6. **Infographic**: Visualize the framework or key data
7. **Slide deck**: Convert to a presentation for webinars
8. **Carousel**: Create 3-4 LinkedIn/Instagram carousels
9. **Thread**: Write a Twitter/X thread with key takeaways
10. **Quote graphics**: Pull 5 shareable quotes with branded templates

### Content Performance Metrics

| Metric | What It Measures | Tool |
|--------|-----------------|------|
| Organic traffic | SEO effectiveness | Google Analytics, Search Console |
| Time on page | Content engagement | Google Analytics |
| Bounce rate | Content relevance | Google Analytics |
| Social shares | Content virality | Native analytics |
| Email open rate | Subject line + audience quality | Email platform |
| Email click rate | Content relevance + CTA | Email platform |
| Conversion rate | Content effectiveness | Analytics + CRM |
| SEO ranking | Search visibility | Ahrefs, SEMrush |
| Backlinks | Authority building | Ahrefs, Moz |

### Content Governance

**Brand Voice Guide:**
- Define tone attributes (e.g., professional but approachable, expert but not condescending)
- Provide examples of do/don't for each attribute
- Include word lists (preferred terms vs avoided terms)

**Approval Workflow:**
1. Writer creates draft
2. Peer review (quality + accuracy)
3. SEO review (keywords, meta, structure)
4. Brand review (voice, messaging, visuals)
5. Legal review (if claims, testimonials, or competitor mentions)
6. Final approval + publish

**Legal Review Triggers:**
- Customer testimonials or case studies (need written permission)
- Competitor comparisons (must be factual and verifiable)
- Data claims (must have source)
- Regulatory topics (compliance, security, privacy)

**Archive Policy:**
- Content older than 18 months: Review for relevance
- Content with <50 monthly visits after 6 months: Update or archive
- Archived content: 301 redirect to most relevant current page
""",
)

copywriting_frameworks = Skill(
    name="copywriting_frameworks",
    description="Professional copywriting frameworks including headline formulas, body copy structures, CTA optimization, landing page templates, and email copy.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT, AgentID.SALES],
    knowledge_summary="Headline formulas (How to, Number, Why), body copy frameworks (PAS, AIDA, BAB, 4Ps), CTA optimization, landing page structure, email copy best practices, and tone calibration by audience.",
    knowledge="""
## Professional Copywriting Framework

### Headline Formulas

**Formula 1: How To + Desired Outcome + Without Pain Point**
- "How to double your team's output without working overtime"
- "How to write proposals that win in half the time"

**Formula 2: Number + Ways/Tips/Secrets + Achieve Goal + Timeframe**
- "7 ways to reduce customer churn in 30 days"
- "12 email templates that book 3x more meetings"

**Formula 3: The Adjective Guide to Topic**
- "The complete guide to content marketing in 2024"
- "The no-BS guide to OKRs that actually work"

**Formula 4: Why Common Belief Is Wrong + What to Do Instead**
- "Why your marketing funnel is broken (and the 3-step fix)"
- "Why most product roadmaps fail and what top PMs do differently"

**Formula 5: Question That Triggers Curiosity**
- "What if your onboarding was actually the reason customers churn?"
- "Are you making these 5 pricing mistakes?"

**Formula 6: Specific Result + Proof**
- "How we reduced support tickets by 60% in 6 weeks"
- "The strategy that grew our MRR from $10K to $100K"

**Headline Testing Checklist:**
- [ ] Does it promise a specific benefit?
- [ ] Is it under 65 characters (for SEO)?
- [ ] Would YOU click on this?
- [ ] Does it create curiosity or urgency?
- [ ] Is the language clear and jargon-free?

### Body Copy Frameworks

**PAS: Problem-Agitate-Solve**
Best for: Sales pages, email, social posts, ads

1. **Problem**: State the pain point clearly. "You spend 3 hours every week on manual reporting."
2. **Agitate**: Make them feel the pain. "That's 156 hours a year -- almost a month of work -- just copying data between spreadsheets. Meanwhile, your competitors are using that time to actually analyze and act on their data."
3. **Solve**: Present your solution. "Our automated reporting tool generates every report you need in 5 minutes, pulling data from all your sources into one dashboard."

**AIDA: Attention-Interest-Desire-Action**
Best for: Landing pages, ads, long-form sales copy

1. **Attention**: Bold statement or surprising fact. "Companies waste $1.2M annually on meetings that should have been emails."
2. **Interest**: Build on it with relevant details. "The average employee attends 62 meetings per month, and executives rate 67% of them as unproductive."
3. **Desire**: Show the transformation. "Imagine reclaiming 10 hours per week for your team. Our async collaboration platform replaces 80% of status meetings with 2-minute written updates."
4. **Action**: Clear CTA. "Start your free 14-day trial. No credit card required."

**BAB: Before-After-Bridge**
Best for: Case studies, testimonials, email sequences

1. **Before**: Describe the current painful state. "Before PermissionHub, our admin team spent every Monday morning manually updating user access across 12 tools."
2. **After**: Paint the desired future. "Now, new team members get the right access to every tool in under 2 minutes, and offboarding happens instantly."
3. **Bridge**: Your product is the bridge. "PermissionHub automatically syncs permissions across all your tools based on role templates."

**4Ps: Promise-Picture-Proof-Push**
Best for: Presentations, proposals, pitches

1. **Promise**: Lead with the outcome. "Cut your onboarding time by 80%."
2. **Picture**: Help them visualize. "Imagine a new hire on their first day, fully set up in every tool, with a personalized learning path, before their first coffee."
3. **Proof**: Back it up. "That's exactly what happened for Acme Corp, who reduced onboarding from 5 days to 4 hours."
4. **Push**: Drive to action. "Book a 15-minute demo to see how it works for your team."

**Star-Story-Solution**
Best for: Blog intros, case studies, social storytelling

1. **Star**: Introduce the character (your customer). "Meet Sarah, a VP of Engineering managing 4 remote teams across 3 time zones."
2. **Story**: Tell their challenge story. "Every sprint planning required 3 separate meetings to accommodate time zones, costing the team 6 hours weekly."
3. **Solution**: How they solved it. "Using async sprint planning with written proposals and recorded walkthroughs, Sarah's team now plans sprints in 45 minutes total."

### CTA Optimization

**Formula: Action Verb + Value + Urgency (optional)**

Good CTAs:
- "Get your free report" (action + value)
- "Start saving 10 hours/week" (action + specific value)
- "Book your demo -- slots filling up" (action + urgency)
- "See how it works in 2 minutes" (action + low commitment)

Bad CTAs:
- "Submit" (no value)
- "Click here" (no value, no context)
- "Learn more" (vague, overused)

**CTA Placement Rules:**
- Above the fold (first CTA within scrolling view)
- After each major benefit section
- Use contrasting color (stands out from page design)
- One primary CTA per section (don't compete with yourself)
- Button text > link text (3-5x higher click rate)

### Landing Page Structure

**1. Hero Section (above the fold)**
- Headline: Clear value proposition (see formulas above)
- Subheadline: 1 sentence supporting the headline
- Primary CTA: Prominent button
- Hero image or video: Show the product or outcome

**2. Social Proof Bar**
- Logo bar: "Trusted by [Company] [Company] [Company]"
- Or: "Join 10,000+ teams" / "4.8 stars on G2"

**3. Benefits Section (3-5 benefits)**
- Each benefit: Icon + headline + 2-sentence description
- Focus on outcomes, not features
- "Save 10 hours/week" not "Automated reporting module"

**4. Features Section (detailed)**
- Screenshots or demo GIFs
- Feature name + description + use case
- This section is for prospects who need details

**5. Objection Handling / FAQ**
- Address top 5-7 concerns: pricing, security, migration, support
- Use accordion format for scanability

**6. Final CTA Section**
- Restate the core value proposition
- Repeat primary CTA
- Add urgency or guarantee ("30-day money-back guarantee")

### Email Copy Best Practices

**Subject Line:**
- 3-7 words for highest open rates
- Create curiosity: "The mistake killing your pipeline"
- Or state benefit: "Save 5 hours this week"
- Personalize when possible: "{first_name}, quick question"
- A/B test every subject line

**Preview Text:**
- Extends the subject line (don't repeat it)
- Subject: "The mistake killing your pipeline"
- Preview: "...and a 2-minute fix you can implement today"

**Opening (first 2 lines):**
- Hook immediately. No "I hope this finds you well."
- Start with a question, surprising stat, or bold statement
- "Did you know 68% of free trials fail at step 3?"

**Body:**
- One idea per email (not a newsletter)
- Short paragraphs (1-2 sentences)
- Use bullet points for scanability
- Write at a conversational level

**CTA:**
- One clear action per email
- Make it easy: "Hit reply with 'yes'" or "Click here to book"
- Don't give multiple choices (paradox of choice)

### Tone Calibration by Audience

**B2B Enterprise:** Authoritative, professional, data-driven
- "Our platform reduces compliance review time by 60%, enabling your team to process audits 3x faster while maintaining regulatory standards."

**B2B Startup:** Conversational, innovative, direct
- "Stop wasting time on manual compliance checks. We automate the boring stuff so you can focus on building."

**B2C Consumer:** Emotional, relatable, aspirational
- "Imagine never worrying about permissions again. Just invite your team and get to work."

**Technical Audience:** Precise, educational, jargon-appropriate
- "Built on a zero-trust architecture with RBAC, our permission engine evaluates policies in <50ms at p99, supporting up to 10K concurrent users."
""",
)

design_system_guidelines = Skill(
    name="design_system_guidelines",
    description="Design system and brand consistency guidelines covering typography, color, spacing, components, responsive design, and accessibility.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge_summary="Visual hierarchy principles, typography system (heading scale, body text), color system with accessibility, 8px spacing system, component patterns, responsive breakpoints, accessibility checklist, and dark mode.",
    knowledge="""
## Design System & Brand Consistency Guidelines

### Visual Hierarchy Principles

Elements that establish importance (in order of impact):
1. **Size**: Larger elements draw attention first
2. **Color/Contrast**: High contrast elements stand out
3. **Weight**: Bold text reads before regular text
4. **Spacing**: Isolated elements with whitespace feel important
5. **Position**: Top-left reads first (in LTR languages), above the fold matters most

**Rule of thirds:** No more than 3 levels of visual hierarchy on any single screen. Primary action, secondary info, tertiary details.

### Typography System

**Heading Scale:**

| Level | Size | Weight | Line Height | Use Case |
|-------|------|--------|-------------|----------|
| H1 | 36-48px | Bold (700) | 1.2 | Page title (one per page) |
| H2 | 28-36px | Semi-bold (600) | 1.25 | Section heading |
| H3 | 22-28px | Semi-bold (600) | 1.3 | Sub-section heading |
| H4 | 18-22px | Medium (500) | 1.35 | Card title, label |
| H5 | 16-18px | Medium (500) | 1.4 | Small heading |
| H6 | 14-16px | Medium (500) | 1.4 | Overline, caption heading |

**Body Text:**
- Default size: 16-18px (never smaller for body text)
- Line height: 1.5-1.7 (tighter for headings, looser for body)
- Max line length: 65-75 characters (for readability)
- Paragraph spacing: 1em (equal to font size)

**Font Pairing Guidelines:**
- Use max 2 font families (one for headings, one for body)
- Sans-serif for UI and digital content
- Serif for long-form reading and editorial content
- Monospace for code, technical data, and tables

**Typography Don'ts:**
- Never use more than 3 font weights on one page
- Never center-align body text (left-align for readability)
- Never use all caps for more than 3 words (hard to read)
- Never use light/thin weights below 16px (accessibility)

### Color System

**Primary Colors:**
- Primary: Main brand color (used for primary actions, key UI elements)
- Primary-light: Hover states, backgrounds
- Primary-dark: Active states, text on light backgrounds

**Secondary Colors:**
- Secondary: Supporting brand color (secondary actions, accents)
- Variants: Light and dark versions

**Accent:**
- Used sparingly for highlights, badges, notifications

**Semantic Colors:**

| Name | Hex (example) | Use Case |
|------|-------------|----------|
| Success | #22C55E | Confirmations, completed states |
| Warning | #F59E0B | Caution, pending, at-risk |
| Error | #EF4444 | Errors, destructive actions, failures |
| Info | #3B82F6 | Informational messages, tips |

**Neutral Grays (9-step scale):**
- Gray-50: Backgrounds (#F9FAFB)
- Gray-100: Card backgrounds (#F3F4F6)
- Gray-200: Borders, dividers (#E5E7EB)
- Gray-300: Disabled states (#D1D5DB)
- Gray-400: Placeholder text (#9CA3AF)
- Gray-500: Secondary text (#6B7280)
- Gray-600: Body text (#4B5563)
- Gray-700: Headings (#374151)
- Gray-800: Primary text (#1F2937)
- Gray-900: High-emphasis text (#111827)

**Accessibility Contrast Requirements (WCAG AA):**
- Normal text (<18px): 4.5:1 contrast ratio minimum
- Large text (>18px bold or >24px): 3:1 contrast ratio minimum
- UI components (icons, borders): 3:1 contrast ratio minimum
- Use tools: WebAIM Contrast Checker, Stark plugin

### Spacing System

**Base Unit: 8px**
Use multiples of 8 for all spacing:

| Token | Value | Use Case |
|-------|-------|----------|
| space-1 | 4px | Tight spacing (icon + label) |
| space-2 | 8px | Compact elements |
| space-3 | 12px | Default inline spacing |
| space-4 | 16px | Default padding |
| space-5 | 24px | Section padding |
| space-6 | 32px | Between sections |
| space-8 | 48px | Major section gaps |
| space-10 | 64px | Page sections |
| space-12 | 96px | Hero sections |

**Spacing Rules:**
- Related elements: closer together (8-16px)
- Unrelated elements: further apart (24-48px)
- Consistent padding within component types
- Whitespace is a feature, not wasted space

### Component Patterns

**Buttons:**

| Type | Use Case | Visual |
|------|----------|--------|
| Primary | Main action (1 per section max) | Filled, brand color, white text |
| Secondary | Alternative action | Outlined, brand color border |
| Tertiary | Low-emphasis action | Text only, brand color |
| Ghost | Contextual action (in tables, cards) | Text only, gray |
| Destructive | Delete, remove, cancel | Red, used sparingly |

Button sizing: Height 32px (small), 40px (default), 48px (large). Min width 80px.

**Forms:**
- Labels: Above input (not placeholder text as labels)
- Inputs: 40-48px height, clear border, focus state with brand color
- Validation: Inline error messages below field, red border, error icon
- Help text: Below input, gray, provides context
- Required indicator: Asterisk (*) or "(required)" label

**Cards:**
- Container: Rounded corners (8-12px), subtle shadow or border
- Content: Image (optional) + Title + Description + Action
- Hover: Subtle shadow increase or border color change
- Click target: Entire card or specific CTA (be consistent)

**Navigation:**
- Breadcrumbs: For deep hierarchies (>2 levels)
- Tabs: For switching views within a page (3-7 tabs max)
- Sidebar: For persistent navigation (collapsible on mobile)
- Mega menu: For large sites with many sections (use sparingly)

### Responsive Breakpoints

| Breakpoint | Range | Target | Layout |
|-----------|-------|--------|--------|
| Mobile (sm) | 320-767px | Phones | Single column, stacked elements |
| Tablet (md) | 768-1023px | Tablets, small laptops | 2-column, collapsible sidebar |
| Desktop (lg) | 1024-1439px | Laptops | Full layout, sidebar visible |
| Large (xl) | 1440px+ | Large monitors | Max-width container, extra whitespace |

**Mobile-First Rules:**
- Design for mobile first, then enhance for larger screens
- Touch targets: Minimum 44x44px (Apple) or 48x48px (Google)
- No hover-dependent interactions on mobile
- Stack horizontal layouts vertically on mobile
- Hide secondary navigation behind hamburger menu

### Accessibility Checklist

- [ ] **Color contrast**: All text meets WCAG AA ratios
- [ ] **Keyboard navigation**: All interactive elements reachable via Tab key
- [ ] **Focus indicators**: Visible focus ring on all interactive elements (never `outline: none` without replacement)
- [ ] **Screen reader labels**: All images have alt text; all buttons/links have accessible names
- [ ] **Semantic HTML**: Use proper heading hierarchy (H1 > H2 > H3), landmark regions, lists
- [ ] **Form labels**: Every input has an associated label (not just placeholder)
- [ ] **Error messages**: Descriptive, not just color-based (red alone is not enough)
- [ ] **Motion**: Respect `prefers-reduced-motion` for animations
- [ ] **Zoom**: Page works at 200% zoom without horizontal scroll
- [ ] **Touch targets**: Minimum 44x44px on mobile

### Dark Mode Considerations

- Don't just invert colors -- reduce brightness and contrast
- Use dark grays (#1A1A2E, #16213E) instead of pure black (#000000)
- Reduce white text brightness to ~87% opacity (not pure white)
- Shadows don't work in dark mode -- use borders or lighter backgrounds instead
- Test all semantic colors in dark mode (green on dark background needs adjustment)
- Provide a toggle, don't force based on system preference alone
- Images and illustrations may need dark-mode variants or reduced opacity
""",
)

video_content_strategy = Skill(
    name="video_content_strategy",
    description="Video content planning and production framework with funnel-aligned video types, platform optimization, production workflow, and video SEO.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge_summary="Video types by funnel stage, platform optimization (YouTube, TikTok, LinkedIn), production framework (pre/production/post), UGC strategy, video SEO, and performance metrics.",
    knowledge="""
## Video Content Strategy Framework

### Video Types by Funnel Stage

**Awareness (Top of Funnel):**

| Video Type | Duration | Purpose | Example |
|-----------|----------|---------|---------|
| Explainer | 60-90s | Introduce a concept or problem | "What is async collaboration?" |
| Thought leadership | 3-5 min | Establish authority on a topic | "The future of remote work in 2025" |
| Social clips | 15-60s | Drive reach and engagement | Quick tips, hot takes, trends |
| Brand story | 2-3 min | Build emotional connection | "Why we started [company]" |

Goal: Views, reach, brand awareness. CTA: Follow, subscribe, visit website.

**Consideration (Middle of Funnel):**

| Video Type | Duration | Purpose | Example |
|-----------|----------|---------|---------|
| Product demo | 2-3 min | Show how the product works | "See [product] in action" |
| Customer testimonial | 60-90s | Build trust with social proof | "How Acme Corp saves 10 hrs/week" |
| Comparison | 3-5 min | Help prospects evaluate options | "[Product] vs [Competitor]" |
| Webinar recording | 30-60 min | Deep educational content | "Masterclass: Building OKRs" |
| How-to tutorial | 3-8 min | Teach using the product | "How to set up permissions in 5 min" |

Goal: Engagement, trial signups, demo requests. CTA: Start free trial, book demo, download guide.

**Decision (Bottom of Funnel):**

| Video Type | Duration | Purpose | Example |
|-----------|----------|---------|---------|
| Personalized demo | 5-15 min | Address specific prospect needs | Custom Loom for sales prospects |
| ROI walkthrough | 3-5 min | Show financial justification | "Calculate your ROI with [product]" |
| Onboarding preview | 2-3 min | Reduce trial-to-paid friction | "Your first 5 minutes with [product]" |
| Case study deep dive | 5-8 min | Detailed success story | "How [customer] achieved [result]" |

Goal: Conversion, purchase, contract signing. CTA: Buy now, talk to sales, start implementation.

### Platform Optimization

**YouTube:**
- Ideal length: 8-12 minutes (maximizes ad revenue and algorithm favor)
- SEO-focused: Research keywords with TubeBuddy or VidIQ
- Thumbnail: Custom, high-contrast, face + text, 1280x720px
- First 30 seconds: Hook + promise what viewer will learn (retention)
- End screens: Subscribe button + related video (last 20 seconds)
- Cards: Link to related content at relevant moments
- Description: First 2 lines visible above fold, include links and timestamps
- Upload schedule: Consistent (same day/time weekly builds audience)

**TikTok / Instagram Reels:**
- Ideal length: 15-60 seconds (under 30s for highest completion rate)
- Hook in first 3 seconds: "Stop scrolling if you..." or visual pattern interrupt
- Vertical format: 9:16 aspect ratio (1080x1920px)
- Trending audio: Use popular sounds for algorithmic boost
- Text overlays: Essential (80% watch without sound)
- Captions: Burned in, not auto-generated (for brand consistency)
- Hashtags: 3-5 relevant, mix of niche and broad
- Post frequency: 1-3x daily for growth, 3-5x weekly for maintenance

**LinkedIn:**
- Ideal length: 30-90 seconds (professional, value-dense)
- Professional tone: Insight-driven, no clickbait
- Captions essential: Most watch on mute during work
- Square (1:1) or vertical (4:5) format performs best
- Native upload (not YouTube links) gets 5x more reach
- Post timing: Tuesday-Thursday, 8-10am target audience timezone
- Engage in comments within first hour (boosts distribution)

**Stories (Instagram, Facebook, LinkedIn):**
- 15-second segments (platform auto-splits longer content)
- Interactive elements: Polls, questions, quizzes, sliders
- Ephemeral feel: Less polished, more authentic
- Use for: Behind-the-scenes, quick updates, time-sensitive announcements
- Frequency: 3-7 story frames per session

### Production Framework

**Pre-Production (Planning):**

*Script/Outline:*
- Hook (first 3-5 seconds): What grabs attention?
- Promise: What will the viewer learn/gain?
- Body: 3-5 key points, structured logically
- CTA: What should they do next?
- Keep scripts conversational. Read aloud before shooting.

*Storyboard:*
- Sketch or describe each shot/scene
- Note: Camera angle, on-screen graphics, b-roll needed
- Identify transitions between sections

*Shot List:*
- Every shot needed, organized by location
- Include: Shot type (wide/medium/close), duration, notes
- Saves time during production (no improvising)

**Production (Shooting):**

*Lighting Checklist:*
- [ ] Key light at 45-degree angle (main light source)
- [ ] Fill light opposite key light (reduces shadows)
- [ ] No harsh shadows on face
- [ ] Consistent color temperature (don't mix warm and cool lights)
- [ ] Background not brighter than subject

*Audio Checklist:*
- [ ] External microphone (never use camera mic)
- [ ] Lavalier mic for interviews/talking head
- [ ] Room is quiet (no HVAC noise, no echoes)
- [ ] Test audio levels before full recording
- [ ] Record 10 seconds of room tone (for editing)

*Framing Checklist:*
- [ ] Rule of thirds: Subject at intersection points
- [ ] Eyes at upper third line
- [ ] Clean background (no clutter, no distracting elements)
- [ ] Consistent eye line (camera at eye level)
- [ ] Adequate headroom (not too tight, not too loose)

**Post-Production (Editing):**

*Editing Workflow:*
1. Import and organize footage
2. Rough cut: Assemble best takes in order
3. Fine cut: Trim pauses, add transitions, tighten pacing
4. Color grade: Consistent look across all shots
5. Sound design: Music (licensed), sound effects, audio levels
6. Graphics: Lower thirds, text overlays, animations
7. Captions: Accurate, timed, branded style
8. Export: Platform-specific formats and resolutions

*Pacing Guidelines:*
- Cut every 3-5 seconds for social content (keeps attention)
- Cut every 5-10 seconds for YouTube educational content
- Match cuts to the beat of background music
- Remove ALL dead air and filler words ("um," "uh," "so")

### UGC (User-Generated Content) Strategy

**Creator Brief Template:**

| Field | Content |
|-------|---------|
| Campaign name | [Name] |
| Product/feature | [What to showcase] |
| Key message | [One sentence the video must convey] |
| Do's | [Specific things to include: product demo, personal story, etc.] |
| Don'ts | [What to avoid: competitor mentions, off-brand language] |
| Format | [Vertical, 30-60s, hook in 3s] |
| Deliverables | [Raw footage + 2 edited versions] |
| Timeline | [Draft by X, revisions by Y, final by Z] |
| Compensation | [Payment, product, affiliate, etc.] |

**Content Rights Management:**
- Always get written usage rights (in perpetuity for paid content)
- Specify: platforms, duration, paid amplification rights
- Credit the creator (builds goodwill and authenticity)

**Performance Tracking:**
- Track each creator's content performance separately
- Metrics: Views, engagement rate, conversions, CPA
- Double down on top-performing creators

### Video SEO (YouTube Focus)

**Title:**
- Include primary keyword near the beginning
- Under 60 characters
- Create curiosity or promise value

**Description:**
- First 2 lines: Hook + CTA (visible without clicking "more")
- Timestamps for each section (YouTube creates chapters)
- Include relevant keywords naturally (not stuffed)
- Links: Website, social, related videos
- 200-300 words total

**Tags:**
- Primary keyword as first tag
- 5-10 related keywords
- Include common misspellings
- Use competitor video tags for ideas (TubeBuddy)

**Thumbnail:**
- Custom (never auto-generated)
- High contrast, readable at small size
- Face with expression + 3-4 words of text
- Consistent brand style across all thumbnails
- Test: Can you read it on a phone screen?

**End Screens & Cards:**
- End screen: Last 20 seconds, subscribe button + next video
- Cards: Link to related content at relevant moments
- Use analytics to see where viewers drop off -- add cards before those points

### Video Metrics & KPIs

| Metric | What It Measures | Good Benchmark |
|--------|-----------------|----------------|
| View count | Reach | Depends on audience size |
| Watch time | Total engagement | Higher is better (YouTube ranks by this) |
| Avg view duration | Content quality | >50% of video length |
| Engagement rate | Likes + comments + shares / views | >5% |
| Click-through rate | Thumbnail + title effectiveness | >5% (YouTube), >1% (ads) |
| Conversion rate | Business impact | >1% to trial/signup |
| Audience retention curve | Where viewers drop off | Flat curve = great; steep early drop = weak hook |
| Subscriber growth | Channel building | Steady upward trend |
""",
)

content_distribution = Skill(
    name="content_distribution",
    description="Multi-channel content distribution strategy with channel selection, timing optimization, syndication, amplification, and measurement.",
    category="content",
    agent_ids=[AgentID.CONT, AgentID.MKT],
    knowledge_summary="Distribution channels (owned/earned/paid), channel selection matrix, posting timing by platform, content syndication with canonical tags, email distribution, social amplification playbook, and measurement framework.",
    knowledge="""
## Multi-Channel Content Distribution Framework

### Distribution Channels

**Owned Channels (You Control):**

| Channel | Content Types | Strengths | Limitations |
|---------|-------------|-----------|------------|
| Website/Blog | Articles, guides, landing pages | SEO, full control | Slow to build traffic |
| Email newsletter | Curated content, updates | Direct, high engagement | List size limits reach |
| Social media profiles | Posts, stories, reels | Engagement, community | Algorithm-dependent |
| Podcast | Interviews, deep dives | Loyalty, authority | Slow growth |
| YouTube channel | Tutorials, demos, vlogs | Search + social reach | High production effort |

**Earned Channels (Others Share Your Content):**

| Channel | How to Earn | Strengths | Limitations |
|---------|------------|-----------|------------|
| PR / Press mentions | Newsworthy stories, expert quotes | Credibility, reach | Unpredictable, low control |
| Guest posts | Pitch publications, provide value | Backlinks, new audience | Time-intensive |
| Influencer shares | Build relationships, create value | Trust transfer | Depends on relationship |
| Social shares/retweets | Create share-worthy content | Organic reach | Unpredictable |
| Review sites (G2, Capterra) | Encourage reviews | Trust, SEO | Can't control content |
| Word of mouth | Deliver exceptional product | Highest trust | Unscalable directly |

**Paid Channels (You Pay for Distribution):**

| Channel | Best For | Cost Model | Targeting |
|---------|---------|-----------|----------|
| Social ads (LinkedIn, Meta) | B2B lead gen, awareness | CPC/CPM | Job title, company, interests |
| Content syndication | Reaching new audiences | CPL | Industry, company size |
| Sponsored content | Brand awareness + authority | Flat fee | Publication audience |
| Google Ads (search) | High-intent keywords | CPC | Search keywords |
| Display/retargeting | Re-engaging visitors | CPM | Website visitors |
| Influencer partnerships | Authentic promotion | Per post/campaign | Creator audience |

### Channel Selection Matrix

For each piece of content, evaluate channels:

| Factor | Weight | LinkedIn | Twitter/X | Email | Blog | YouTube |
|--------|--------|----------|-----------|-------|------|---------|
| Audience presence | 30% | 5 | 3 | 4 | 3 | 4 |
| Content format fit | 25% | 4 | 3 | 5 | 5 | 2 |
| Cost (lower=better) | 15% | 4 | 5 | 4 | 5 | 2 |
| Measurability | 15% | 4 | 3 | 5 | 5 | 4 |
| Scale potential | 15% | 3 | 4 | 3 | 4 | 5 |
| **Weighted Score** | | **4.15** | **3.35** | **4.25** | **4.20** | **3.35** |

Prioritize top 3 channels per content piece. Don't spread thin across all channels.

### Distribution Timing

**Best Posting Times by Platform (General Guidelines):**

| Platform | Best Days | Best Times | Notes |
|----------|-----------|-----------|-------|
| LinkedIn | Tue-Thu | 8-10am, 12pm | Business hours, target audience TZ |
| Twitter/X | Mon-Fri | 12-3pm | Lunch breaks, afternoon browsing |
| Instagram | Mon-Fri | 11am-1pm, 7-9pm | Lunch + evening leisure |
| Facebook | Wed-Fri | 1-4pm | Afternoon engagement peak |
| YouTube | Thu-Sat | 12-4pm | Weekends for longer content |
| Email | Tue-Thu | 10am, 2pm | Avoid Monday inbox overload |
| Blog publish | Tue-Wed | 8-10am | Index before weekend traffic |

**CRITICAL: These are starting points. Always test for YOUR audience.**

**How to find your optimal times:**
1. Post at different times for 4 weeks
2. Track engagement rates (not just views)
3. Identify patterns
4. Optimize and re-test quarterly

### Content Syndication Strategy

**What is syndication?**
Republishing your content on third-party platforms to reach new audiences.

**Key Platforms:**
- Medium: Large built-in audience, good for thought leadership
- LinkedIn Articles: Professional audience, high engagement for B2B
- Industry publications: Niche authority, targeted reach
- Dev.to: Technical audience (for dev tools/SaaS)
- Substack: Newsletter-first, growing platform

**Syndication Rules:**
1. **Always publish on your site first** (at least 24-48 hours before syndication)
2. **Use canonical tags**: Point to the original URL to avoid SEO penalties
3. **Delay syndication 1-2 weeks**: Let Google index your original first
4. **Customize the intro**: Don't just copy-paste; adapt for the platform's audience
5. **Include a CTA** back to your site: "Originally published at [your site]"
6. **Track referral traffic**: Measure which syndication channels drive visitors

### Email Distribution

**Segmentation Strategy:**

| Segment | Criteria | Content Type | Frequency |
|---------|---------|-------------|-----------|
| New subscribers | Joined <30 days | Welcome series, best-of content | Daily for 7 days, then weekly |
| Active readers | Open rate >40% | Premium content, early access | Weekly |
| Disengaged | No opens in 60 days | Re-engagement campaign | Once, then prune |
| Customers | Paying users | Product updates, tutorials | Bi-weekly |
| Prospects | Free users, trial | Case studies, conversion content | Weekly |

**A/B Testing for Email:**
- Test one variable at a time
- Subject line: Test on 20% of list, send winner to 80%
- Send time: Test 2 time slots over 4 weeks
- CTA: Test button text, color, placement
- Minimum sample: 1,000 per variant for statistical significance

**Personalization Tactics:**
- First name in subject line (7% higher open rate average)
- Content based on past behavior (clicked on topic X = send more of topic X)
- Location-based timing (send at 10am in recipient's timezone)
- Role-based content (different content for PMMs vs engineers)

### Social Amplification Playbook

**Employee Advocacy Program:**
- Share a weekly "suggested posts" document with pre-written content
- Employees personalize and share from their accounts
- Track participation and celebrate top advocates
- Employees' posts get 8x more engagement than brand posts on average

**Pre-Post Engagement (15 min before posting):**
1. Engage with 5-10 posts in your feed (comments, likes)
2. This signals to the algorithm that you're active
3. Your subsequent post gets higher initial distribution

**Post-Publication Engagement (first 60 min):**
1. Reply to every comment within the first hour
2. Ask follow-up questions to extend conversations
3. Tag relevant people who would find value in the content
4. Share in relevant Slack communities, Discord servers, or groups

**Hashtag Strategy:**
- LinkedIn: 3-5 hashtags, mix of broad (#marketing) and niche (#B2BSaaS)
- Instagram: 15-25 hashtags, mix of sizes (broad + niche + branded)
- Twitter/X: 1-2 hashtags max (more reduces engagement)
- Create a branded hashtag for campaigns

**Cross-Promotion:**
- Share blog post snippet on LinkedIn with link
- Create a Twitter thread summarizing key points
- Record a 60-second TikTok/Reel with the main takeaway
- Send as newsletter with additional commentary

### Paid Amplification Strategy

**Which content to boost:**
1. Look at organic performance (top 10-20% of posts)
2. Boost content that already resonates (proven messaging)
3. Don't boost content that failed organically (fix the content first)

**Retargeting Website Visitors:**
- Show new content to people who visited your blog
- Show product content to people who visited pricing page
- Exclude current customers (unless upsell content)
- Window: 7-30 days (shorter = warmer audience)

**Lookalike Audiences:**
- Upload customer email list to ad platform
- Create 1% lookalike (most similar to your customers)
- Use for top-of-funnel content distribution
- Higher quality leads than interest-based targeting

**Budget Allocation:**
- 60% on proven content amplification
- 25% on testing new content/audiences
- 15% on retargeting

### Measurement Framework

**Metrics by Channel:**

| Channel | Reach Metric | Engagement Metric | Conversion Metric |
|---------|-------------|-------------------|-------------------|
| Blog | Pageviews, unique visitors | Time on page, scroll depth | CTA clicks, signups |
| Email | Delivered, open rate | Click rate, reply rate | Conversion rate |
| LinkedIn | Impressions | Reactions, comments, shares | Profile visits, link clicks |
| Twitter/X | Impressions | Likes, retweets, replies | Link clicks |
| YouTube | Views, impressions | Watch time, likes, comments | Subscriber gain, link clicks |
| Paid ads | Impressions, reach | CTR | Conversions, CPA |

**Content ROI Calculation:**
ROI = (Revenue attributed to content - Content cost) / Content cost x 100

**Content cost includes:**
- Writer/creator time or freelance cost
- Design and production costs
- Distribution costs (paid promotion)
- Tools and platform costs

**Attribution Models:**
- First touch: Credit the first content a customer engaged with
- Last touch: Credit the last content before conversion
- Linear: Equal credit across all touchpoints
- Time-decay: More credit to recent touchpoints
- Recommendation: Use multi-touch (linear or time-decay) for accurate picture

**Monthly Content Report Template:**

| Metric | This Month | Last Month | Change | Target |
|--------|-----------|-----------|--------|--------|
| Total content published | 12 | 10 | +20% | 12 |
| Organic traffic | 15,200 | 14,100 | +7.8% | 16,000 |
| Email subscribers gained | 340 | 290 | +17.2% | 350 |
| Social engagement rate | 4.2% | 3.8% | +10.5% | 5.0% |
| Content-attributed signups | 45 | 38 | +18.4% | 50 |
| Top performing content | "[Title]" | "[Title]" | -- | -- |
""",
)


# =============================================================================
# Register All PM, Productivity, and Content Skills
# =============================================================================


def register_pm_productivity_content_skills() -> None:
    """Register all PM, Productivity, and Content Creation skills in the global registry."""
    all_skills = [
        # Product Management (planning)
        product_spec_writing,
        user_research_synthesis,
        stakeholder_update,
        sprint_planning,
        product_roadmap_management,
        product_metrics_review,
        product_competitive_brief,
        # Productivity (operations, all agents)
        task_prioritization,
        meeting_management,
        goal_setting_framework,
        project_status_tracking,
        # Content Creation (content)
        content_strategy,
        copywriting_frameworks,
        design_system_guidelines,
        video_content_strategy,
        content_distribution,
    ]

    for skill in all_skills:
        skills_registry.register(skill)


# Auto-register skills when module is imported
register_pm_productivity_content_skills()
