# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Professional Operations & Data Skills Library.

This module defines professional-grade skills for the Operations and Data agents,
covering process documentation, compliance, change management, capacity planning,
vendor management, reporting, runbooks, risk assessment, process optimization,
SQL, data exploration, statistics, visualization, validation, dashboards, and
analysis workflows.

Total: 16 skills (9 operations, 7 data).
"""

from app.skills.registry import AgentID, Skill, skills_registry

# =============================================================================
# Operations Skills
# =============================================================================

process_documentation = Skill(
    name="process_documentation",
    description="Business process documentation including swimlane diagrams, RACI matrices, SOP templates, and change management for process updates.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.HR],
    knowledge_summary="Process mapping (swimlane, flowchart, value stream, SIPOC), RACI matrix methodology, SOP template with decision points and exception handling, documentation standards and naming conventions.",
    knowledge="""
## Business Process Documentation Framework

### Process Map Types

#### 1. Swimlane / Cross-Functional Diagram
- **When to use:** Processes that span multiple departments or roles.
- **Structure:** Horizontal or vertical lanes, one per actor (role, team, system).
- **Elements:** Start/end ovals, activity rectangles, decision diamonds, arrows for flow.
- **Best practice:** Keep lanes to 5 or fewer. Highlight hand-offs between lanes with bold arrows.

#### 2. Flowchart
- **When to use:** Single-owner linear or branching processes.
- **Symbols:** Oval (start/end), rectangle (step), diamond (decision), parallelogram (input/output), circle (connector).
- **Best practice:** Flow top-to-bottom or left-to-right. Number each step. One decision per diamond.

#### 3. Value Stream Map (VSM)
- **When to use:** Lean process improvement — visualize material and information flow.
- **Key metrics per step:** Cycle time (CT), lead time (LT), percent complete and accurate (%C&A), changeover time.
- **Structure:** Current state map -> identify waste -> future state map -> implementation plan.
- **Data boxes:** Process time, wait time, inventory, FTE count, uptime %.

#### 4. SIPOC Diagram
- **When to use:** High-level scoping before detailed mapping.
- **Columns:** Suppliers | Inputs | Process (5-7 high-level steps) | Outputs | Customers.
- **Best practice:** Complete in a 30-minute workshop with process owner and 2-3 participants.

---

### RACI Matrix Methodology

**Roles:**
| Role | Definition | Rules |
|------|-----------|-------|
| **R** — Responsible | Does the work | Can be multiple per task |
| **A** — Accountable | Final decision-maker, signs off | Exactly ONE per task (never zero, never two) |
| **C** — Consulted | Provides input before work (two-way) | Minimize — each C adds cycle time |
| **I** — Informed | Notified after completion (one-way) | Minimize — only those who truly need to know |

**Construction Steps:**
1. List all process tasks/deliverables as rows.
2. List all roles/teams as columns.
3. Assign R first — who does the work?
4. Assign A — who is the single decision-maker? (Must differ from R where possible for segregation of duties.)
5. Assign C sparingly — every C is a potential bottleneck.
6. Assign I — default to I over C when in doubt.

**Validation Checks:**
- Every row has exactly one A.
- No row is missing an R.
- No person is both A and R on more than 60% of tasks (overload risk).
- Columns with many C entries indicate a potential approval bottleneck.

---

### SOP Template

```
STANDARD OPERATING PROCEDURE
=============================
Title:          [Process Name]
Document ID:    SOP-[DEPT]-[###]
Version:        [X.Y]
Effective Date: [YYYY-MM-DD]
Owner:          [Role / Name]
Approved By:    [Name, Date]
Next Review:    [YYYY-MM-DD]

1. PURPOSE
   [One paragraph: why this SOP exists and what outcome it ensures.]

2. SCOPE
   - Applies to: [roles, departments]
   - Triggered by: [event, schedule, request]
   - Out of scope: [what this does NOT cover]

3. DEFINITIONS
   | Term | Definition |
   |------|-----------|
   | ...  | ...       |

4. RESPONSIBILITIES
   | Role | Responsibility |
   |------|---------------|
   | ...  | ...           |

5. PREREQUISITES
   - System access: [list]
   - Training: [list]
   - Tools: [list]

6. PROCEDURE
   Step 1: [Actor] [verb] [object].
     - Expected result: [what should happen]
     - If [condition]: Go to Step X / See Exception Handling.
   Step 2: ...
   [DECISION POINT] If [condition A] -> Step 3a. If [condition B] -> Step 3b.
   Step 3a: ...
   Step 3b: ...

7. EXCEPTION HANDLING
   | Exception | Response | Escalation |
   |-----------|----------|-----------|
   | ...       | ...      | ...       |

8. VERIFICATION
   - [ ] [Check 1]
   - [ ] [Check 2]

9. RELATED DOCUMENTS
   - [Link to related SOP]
   - [Link to policy]

10. REVISION HISTORY
   | Version | Date | Author | Changes |
   |---------|------|--------|---------|
   | 1.0     | ...  | ...    | Initial |
```

---

### Documentation Standards
- **Voice:** Active voice ("Click Submit", not "Submit should be clicked").
- **Granularity:** One action per step. If a step has "and", split it.
- **Screenshots:** Include for any UI interaction. Annotate with numbered callouts.
- **Version control:** Use semantic versioning (major.minor). Major = process change, minor = clarification.
- **Review cadence:** Minimum annual review. Trigger review on any process change, incident, or audit finding.

### Process Naming Conventions
- Format: `[Department]-[Function]-[Subprocess]`
- Examples: `FIN-AP-InvoiceApproval`, `OPS-DEPLOY-ProductionRelease`, `HR-RECRUIT-PhoneScreen`
- Use PascalCase for subprocess names, uppercase abbreviations for department.

### Review and Approval Workflow
1. Author drafts/updates document.
2. Peer review by someone who executes the process.
3. SME review for technical accuracy.
4. Process owner approval (the "A" in RACI).
5. Publish to document management system with notification to affected teams.
6. Archive previous version (never delete).

### Change Management for Process Updates
- **Minor update (clarification, typo):** Author + peer review. Increment minor version.
- **Major update (new steps, changed flow):** Full review cycle. Increment major version. Communication to all stakeholders. Training if needed.
- **Emergency update:** Expedited approval by process owner. Full review within 5 business days.
- **Impact assessment:** Before any change, document: who is affected, what training is needed, what systems change, what the rollback plan is.
""",
)

compliance_tracking = Skill(
    name="compliance_tracking",
    description="Compliance requirement tracking, audit readiness checklists, compliance calendars, and gap analysis methodology.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.LEGAL],
    knowledge_summary="Compliance register template, audit readiness checklist, compliance calendar management, gap analysis methodology, evidence collection best practices, and dashboard metrics for control testing coverage.",
    knowledge="""
## Compliance Requirement Tracking & Audit Readiness

### Compliance Register Template

| # | Requirement | Source Regulation | Owner | Control Description | Evidence Type | Testing Frequency | Last Tested | Next Due | Status |
|---|------------|-------------------|-------|-------------------|---------------|-------------------|-------------|----------|--------|
| 1 | Data encryption at rest | SOC 2 CC6.1 | IT Security | AES-256 on all databases | Config screenshot + audit log | Quarterly | 2024-01-15 | 2024-04-15 | Compliant |
| 2 | Access reviews | SOX 404 | IT Ops | Quarterly access recertification | Signed review sheets | Quarterly | 2024-02-01 | 2024-05-01 | In Progress |

**Fields explained:**
- **Requirement:** Plain-language description of what must be done.
- **Source Regulation:** Specific clause/section (e.g., GDPR Art. 32, SOC 2 CC6.1).
- **Owner:** Single accountable person (not a team).
- **Control Description:** How the requirement is met (the "control").
- **Evidence Type:** What artifact proves compliance (screenshot, log, signed document, system report).
- **Testing Frequency:** How often the control is validated (continuous, monthly, quarterly, annually).
- **Status:** Compliant | In Progress | Non-Compliant | Not Tested | Exception Granted.

---

### Audit Readiness Checklist

**30 Days Before Audit:**
- [ ] Confirm audit scope, dates, and auditor team.
- [ ] Assign internal liaison for each audit area.
- [ ] Review prior audit findings — confirm all remediation complete.
- [ ] Pull all evidence artifacts; organize by control area.
- [ ] Conduct internal spot-check: randomly test 10% of controls.
- [ ] Brief all control owners on expectations and timeline.

**7 Days Before Audit:**
- [ ] Evidence repository finalized and indexed.
- [ ] Exceptions documented with justification and compensating controls.
- [ ] Walk-through rehearsal with key control owners.
- [ ] Conference room / virtual meeting logistics confirmed.
- [ ] Escalation contacts identified for urgent requests.

**During Audit:**
- [ ] Designate single point of contact for auditor requests.
- [ ] Log all requests with timestamp and response deadline.
- [ ] Track open items daily; resolve within 24 hours.
- [ ] Escalate blockers immediately — do not let items age.

**Post-Audit:**
- [ ] Receive draft findings; review for factual accuracy.
- [ ] Create remediation plan for each finding (owner, deadline, action).
- [ ] Track remediation to closure.
- [ ] Update compliance register with any new or changed controls.
- [ ] Conduct lessons-learned session.

---

### Compliance Calendar

| Month | Activity | Type | Owner | Deadline |
|-------|---------|------|-------|----------|
| Jan | SOC 2 evidence collection begins | Audit Prep | IT Security | Jan 15 |
| Feb | Q1 access recertification | Control Testing | IT Ops | Feb 28 |
| Mar | Annual policy review | Policy | Compliance | Mar 31 |
| Apr | SOC 2 audit period starts | External Audit | Compliance | Apr 1 |
| May | Q2 vendor risk assessments due | Vendor Mgmt | Procurement | May 15 |
| Jun | Security awareness training refresh | Training | HR + IT | Jun 30 |
| Jul | Mid-year compliance self-assessment | Internal Review | All Owners | Jul 31 |
| Aug | Business continuity test | Control Testing | Operations | Aug 31 |
| Sep | Annual penetration test | Security Testing | IT Security | Sep 30 |
| Oct | Q3 access recertification | Control Testing | IT Ops | Oct 31 |
| Nov | Regulatory change impact assessment | Compliance | Legal | Nov 15 |
| Dec | Annual compliance report to board | Reporting | Compliance | Dec 15 |

**Calendar Management:**
- Review monthly at compliance committee meeting.
- Auto-reminders 30 and 7 days before each deadline.
- Track completion percentage per quarter.
- Escalate overdue items after 5 business days.

---

### Gap Analysis Methodology

**Step 1: Identify Requirements**
- Extract all applicable requirements from regulations, contracts, frameworks.
- Source: regulatory text, contract appendices, framework control lists.
- Create master requirements list with unique IDs.

**Step 2: Map to Current Controls**
- For each requirement, identify existing controls (policies, procedures, technical controls).
- Rate mapping: Full | Partial | None.

**Step 3: Identify Gaps**
- Full mapping = no gap.
- Partial mapping = gap exists (document what is missing).
- No mapping = critical gap.

**Step 4: Prioritize by Risk**
| Risk Level | Criteria | Response Time |
|-----------|---------|---------------|
| Critical | Regulatory penalty exposure, data breach risk | 30 days |
| High | Audit finding likely, significant control weakness | 60 days |
| Medium | Best practice gap, minor control weakness | 90 days |
| Low | Enhancement opportunity, no immediate risk | Next review cycle |

**Step 5: Create Remediation Plan**
- For each gap: owner, action items, resource needs, timeline, success criteria.
- Track in project management tool with weekly status updates.
- Verify closure with evidence before marking complete.

---

### Evidence Collection Best Practices
- **Timestamped:** Every artifact must show when it was generated.
- **Unaltered:** Use system-generated reports, not manually edited screenshots.
- **Organized:** Folder structure mirrors control framework numbering.
- **Retained:** Minimum 7 years or per regulatory requirement.
- **Accessible:** Stored in shared, access-controlled repository (not personal drives).
- **Described:** Each evidence file has a cover sheet: control ID, description, date range, preparer.

### Compliance Dashboard Metrics
| Metric | Target | Formula |
|--------|--------|---------|
| % Controls Tested | 100% by period end | Tested / Total controls |
| % On Schedule | > 95% | On-time tests / Total tests due |
| Open Findings | 0 critical, < 5 total | Count of unresolved findings |
| Overdue Items | 0 | Count of items past deadline |
| Evidence Freshness | < 90 days | Days since last evidence update |
| Exception Count | < 3% of controls | Controls with exceptions / Total |
""",
)

change_management_request = Skill(
    name="change_management_request",
    description="Change management with impact analysis, risk scoring, change types, communication plans, and rollback procedures.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.EXEC],
    knowledge_summary="Change request template with impact assessment and rollback plan, change types (standard/normal/emergency), risk scoring matrix, communication plan template, and post-implementation review checklist.",
    knowledge="""
## Change Management Framework

### Change Request Template

```
CHANGE REQUEST
==============
CR Number:      CR-[YYYY]-[###]
Title:          [Brief descriptive title]
Requestor:      [Name, Role]
Date Submitted: [YYYY-MM-DD]
Priority:       [Low / Medium / High / Emergency]
Change Type:    [Standard / Normal / Emergency]

1. DESCRIPTION
   [What is being changed? Be specific about systems, configurations, code, or processes.]

2. JUSTIFICATION
   [Why is this change needed? Business driver, incident reference, improvement goal.]

3. IMPACT ASSESSMENT
   See Impact Categories table below.

4. RISK ANALYSIS
   Likelihood: [1-5]
   Impact: [1-5]
   Risk Score: [Likelihood x Impact]
   Mitigations: [List specific risk mitigations]

5. ROLLBACK PLAN
   [Exact steps to reverse the change if it fails.]
   Rollback Time Estimate: [minutes/hours]
   Rollback Decision Criteria: [What triggers rollback?]

6. TESTING REQUIREMENTS
   - [ ] Unit/integration tests pass
   - [ ] Staging environment validated
   - [ ] Smoke test plan documented
   - [ ] Performance impact assessed

7. IMPLEMENTATION PLAN
   Scheduled Window: [Date, Time, Duration]
   Implementer: [Name]
   Steps: [Numbered implementation steps]

8. APPROVAL CHAIN
   | Approver | Role | Status | Date |
   |----------|------|--------|------|
   | ...      | ...  | ...    | ...  |

9. POST-IMPLEMENTATION VERIFICATION
   - [ ] Change deployed successfully
   - [ ] Smoke tests passed
   - [ ] Monitoring shows no anomalies for 30 min
   - [ ] Stakeholders notified of completion
```

---

### Impact Categories

| Category | Assessment Questions | Rating (H/M/L/None) |
|----------|---------------------|---------------------|
| Systems Affected | Which applications, services, databases, infrastructure? | |
| Teams Affected | Which teams need to change behavior or be trained? | |
| Customers Affected | Will customers see downtime, UI changes, or behavior changes? | |
| SLA Impact | Will any SLAs be at risk during or after the change? | |
| Security Impact | Does this change attack surface, access controls, or data handling? | |
| Compliance Impact | Does this affect controls, audit evidence, or regulatory posture? | |
| Data Impact | Is data being migrated, transformed, or could data loss occur? | |
| Integration Impact | Are API contracts, event schemas, or data feeds changing? | |

---

### Risk Scoring Matrix

**Likelihood Scale:**
| Score | Definition |
|-------|-----------|
| 1 | Rare — very unlikely to occur |
| 2 | Unlikely — could happen but not expected |
| 3 | Possible — has happened before in similar changes |
| 4 | Likely — will probably occur without mitigation |
| 5 | Almost Certain — expected to happen |

**Impact Scale:**
| Score | Definition |
|-------|-----------|
| 1 | Negligible — no user-visible impact |
| 2 | Minor — small group affected, quick recovery |
| 3 | Moderate — noticeable service degradation, workaround available |
| 4 | Major — significant outage or data issue, extended recovery |
| 5 | Critical — full outage, data loss, regulatory exposure |

**Risk Score = Likelihood x Impact:**
| Score | Category | Required Action |
|-------|----------|----------------|
| 1-4 | Low | Standard approval |
| 5-9 | Medium | Manager approval + documented rollback |
| 10-15 | High | CAB review + rehearsed rollback + monitoring plan |
| 16-25 | Critical | Executive approval + full dry-run + dedicated rollback team |

---

### Change Types

**Standard Change (Pre-Approved)**
- Low risk, well-understood, performed regularly.
- Examples: password resets, routine patching, adding monitoring alerts.
- Process: Submit record, implement during approved window, close.
- No CAB review required.

**Normal Change (CAB Review)**
- Medium-to-high risk, not routine.
- Examples: infrastructure upgrades, schema changes, new integrations, configuration changes.
- Process: Submit CR -> peer review -> CAB review -> scheduled window -> implement -> verify.
- Lead time: minimum 3 business days for review.

**Emergency Change (Expedited)**
- Critical incident or security vulnerability requiring immediate action.
- Process: Implement with verbal approval from on-call manager -> submit CR within 24 hours -> post-review at next CAB.
- Must still have rollback plan and monitoring.
- Requires post-implementation review within 5 business days.

---

### Communication Plan Template

| Audience | When | Channel | Message |
|----------|------|---------|---------|
| Affected teams | 5 days before | Email + Slack | Change description, impact, timing |
| Customers (if visible) | 3 days before | Status page + email | Maintenance window notice |
| On-call / Support | 1 day before | Slack + runbook link | What to watch for, escalation path |
| All stakeholders | During change | Status page | Real-time progress updates |
| All stakeholders | After completion | Email + Slack | Confirmation of success or rollback |

---

### Post-Implementation Review Checklist
- [ ] Was the change implemented as planned?
- [ ] Were there any unexpected issues? Document them.
- [ ] Was the rollback plan adequate? Would it have worked?
- [ ] Did monitoring detect the change impact accurately?
- [ ] Were stakeholders notified on time?
- [ ] What should be improved for next time?
- [ ] Update runbook / SOP if procedures changed.
- [ ] Close the CR with actual implementation details.

### Rollback Criteria and Procedures
**Trigger rollback when:**
- Smoke tests fail after deployment.
- Error rates exceed 2x baseline within 15 minutes.
- Customer-facing functionality is broken.
- Data integrity issues detected.
- Performance degradation exceeds acceptable thresholds (defined per-service).

**Rollback procedure:**
1. Announce rollback decision in change channel.
2. Execute rollback steps from CR Section 5.
3. Verify system returns to pre-change state.
4. Run smoke tests again.
5. Notify stakeholders of rollback.
6. Schedule post-mortem within 48 hours.
""",
)

capacity_planning = Skill(
    name="capacity_planning",
    description="Resource capacity planning with utilization forecasting, demand modeling, gap analysis, and hiring decision frameworks.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.EXEC, AgentID.HR],
    knowledge_summary="Capacity calculation formulas, utilization targets by role type (billable 75-85%, mgmt 50-60%, support 85-95%), demand forecasting, scenario modeling, contractor vs FTE framework, and burnout indicators.",
    knowledge="""
## Resource Capacity Planning & Utilization Forecasting

### Capacity Calculation

**Available Capacity (hours/month):**
```
Available Hours = Headcount x Working Days x Hours/Day x Utilization Target
                = Headcount x 21 x 8 x Target%

Example: 5 engineers x 21 days x 8 hrs x 0.80 = 672 available hours/month
```

**Deductions from gross capacity:**
- PTO/holidays: ~10% (varies by region)
- Meetings/overhead: 10-20%
- Training/development: 5%
- Unplanned work (interrupts): 5-15%

**Net available = Gross - Deductions**

---

### Utilization Targets by Role Type

| Role Type | Target Utilization | Rationale |
|-----------|-------------------|-----------|
| Billable / IC (engineers, designers) | 75-85% | Allows for learning, mentoring, overhead |
| Management | 50-60% | Meetings, 1:1s, planning, reviews consume rest |
| Support / Operations | 85-95% | Reactive roles; high utilization expected |
| Sales | 60-70% | Prospecting, admin, CRM updates consume rest |
| Executives | 30-40% | Strategy, stakeholder management, decision-making |

**Warning:** Sustained utilization >90% for any role leads to burnout, quality degradation, and turnover.

---

### Demand Forecasting

**Pipeline-Weighted Demand:**
```
Weighted Demand = SUM(Project Hours x Probability of Start)

Example:
  Project A: 200 hrs x 90% probability = 180 weighted hrs
  Project B: 400 hrs x 50% probability = 200 weighted hrs
  Project C: 100 hrs x 20% probability =  20 weighted hrs
  Total Weighted Demand = 400 hrs
```

**Historical Pattern Analysis:**
- Pull 12 months of actual hours by team/skill.
- Identify seasonality (Q4 spike, summer lull, etc.).
- Calculate growth trend (month-over-month % change).
- Apply trend + seasonality to baseline for forecast.

**Seasonal Adjustment Factors:**
| Quarter | Typical Adjustment | Reason |
|---------|-------------------|--------|
| Q1 | 0.95 | Ramp-up after holidays |
| Q2 | 1.05 | Peak productivity |
| Q3 | 0.90 | Summer PTO |
| Q4 | 1.10 | Year-end push (but minus holidays) |

---

### Gap Analysis: Demand vs Capacity

**By Skill / Team / Time Period:**

| Period | Skill/Team | Demand (hrs) | Capacity (hrs) | Gap | Action |
|--------|-----------|-------------|----------------|-----|--------|
| Apr | Frontend | 500 | 400 | -100 | Contractor or deprioritize |
| Apr | Backend | 300 | 450 | +150 | Cross-train or take on more |
| May | DevOps | 200 | 200 | 0 | Monitor |

**Negative gap = over-allocated.** Options: hire, contract, reprioritize, defer.
**Positive gap = under-utilized.** Options: pull forward work, cross-team lending, skill development.

---

### Scenario Modeling

| Scenario | Headcount | Capacity | Demand Assumption | Gap |
|----------|-----------|----------|-------------------|-----|
| **Best Case** | Current + 2 hires | +320 hrs/mo | Pipeline at 70% close rate | +200 |
| **Likely Case** | Current + 1 hire | +160 hrs/mo | Pipeline at 50% close rate | -50 |
| **Worst Case** | Current (no hires) | Baseline | Pipeline at 30% + 1 attrition | -400 |

**Decision triggers:**
- If likely case shows gap > 15% of capacity -> start hiring process now.
- If worst case shows gap > 30% -> engage contractors as bridge.
- If best case shows surplus > 20% -> delay hiring, invest in skill-building.

---

### Hiring Lead Time Considerations

| Role Level | Avg Time to Hire | Avg Time to Productivity |
|-----------|-----------------|-------------------------|
| Junior IC | 30-45 days | 30-60 days |
| Mid-level IC | 45-60 days | 30-45 days |
| Senior IC | 60-90 days | 14-30 days |
| Manager | 60-90 days | 30-60 days |
| Executive | 90-120 days | 60-90 days |

**Total lead time = Time to hire + Time to productivity.** Factor this into demand planning horizon.

---

### Contractor vs FTE Decision Framework

| Factor | Favor Contractor | Favor FTE |
|--------|-----------------|-----------|
| Duration | < 6 months | > 6 months |
| Knowledge retention | Not critical | Critical (IP, institutional knowledge) |
| Cost | Short-term projects | Long-term cheaper (benefits amortized) |
| Ramp-up | Specialist, minimal ramp | Complex domain, significant ramp |
| Availability | Need someone NOW | Can wait for right hire |
| Scale flexibility | Seasonal / project-based demand | Steady baseline demand |

**Rule of thumb:** If you need the role for >12 months AND it touches core IP, hire FTE. Otherwise, contract first and convert if the need persists.

---

### Workload Balancing Techniques
1. **Skills matrix:** Map team members to capabilities. Identify single points of failure.
2. **Cross-training:** Ensure at least 2 people can perform any critical function.
3. **Work-in-progress limits:** Cap concurrent assignments per person (max 2-3 projects).
4. **Buffer capacity:** Reserve 10-15% of team capacity for unplanned work.
5. **Rotation:** Rotate on-call, support duty, and maintenance to spread load.

### Burnout Indicators
- Sustained utilization >90% for 3+ consecutive weeks.
- Increasing overtime trend.
- Rising error/defect rates from a team or individual.
- Declining velocity or throughput despite same hours.
- Increased PTO usage, especially unplanned.
- Team survey scores declining on workload questions.

**Response:** Immediately rebalance work, bring in temporary help, defer non-critical projects.

### Capacity Dashboard Template
| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Team Utilization | 82% | 75-85% | Green |
| Demand Coverage | 94% | >95% | Amber |
| Open Headcount | 2 | 0 | Red |
| Contractor Count | 3 | As needed | Green |
| Avg Hours/Person/Week | 42 | <45 | Green |
| Cross-training Coverage | 70% | >80% | Amber |
""",
)

vendor_review_framework = Skill(
    name="vendor_review_framework",
    description="Vendor evaluation scorecard, RFI/RFP process, risk tiering, performance reviews, and make-vs-buy framework.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.LEGAL, AgentID.FIN],
    knowledge_summary="Vendor scorecard (quality, cost, delivery, relationship, risk), RFI/RFP/RFQ evaluation process, vendor risk tiers (critical/strategic/tactical/commodity), ongoing performance reviews, and make-vs-buy decision framework.",
    knowledge="""
## Vendor Evaluation & Management Framework

### Vendor Scorecard

| Category | Weight | Metric | Measurement | Score (1-5) |
|----------|--------|--------|-------------|-------------|
| **Quality** | 25% | SLA adherence | % of SLAs met | |
| | | Defect rate | Defects per delivery | |
| | | First-time-right | % deliveries without rework | |
| **Cost** | 20% | Total cost of ownership | Annual all-in cost | |
| | | Price competitiveness | vs. market benchmark | |
| | | Cost trend | YoY price change % | |
| **Delivery** | 20% | On-time delivery | % deliveries on time | |
| | | Lead times | Avg days from order to delivery | |
| | | Responsiveness | Avg response time to requests | |
| **Relationship** | 15% | Communication quality | Proactive updates, clarity | |
| | | Innovation | New ideas, process improvements | |
| | | Flexibility | Willingness to accommodate changes | |
| **Risk** | 20% | Financial stability | Credit rating, revenue trend | |
| | | Concentration risk | % of our spend with this vendor | |
| | | Compliance | Certifications, audit results | |
| | | Business continuity | DR plan, geographic diversity | |

**Scoring: 1=Poor, 2=Below Expectations, 3=Meets Expectations, 4=Exceeds, 5=Exceptional.**
**Weighted Score = SUM(Category Weight x Category Avg Score).**

---

### Evaluation Process

**Stage 1: RFI (Request for Information)**
- Purpose: Market scan, shortlisting.
- Send to: 8-12 potential vendors.
- Evaluate: Capabilities, experience, certifications, rough pricing.
- Output: Shortlist of 3-5 vendors for RFP.

**Stage 2: RFP (Request for Proposal)**
- Purpose: Detailed evaluation.
- Include: Detailed requirements, evaluation criteria with weights, timeline, terms.
- Evaluate: Solution fit, implementation plan, pricing, references, team.
- Score: Each evaluator scores independently, then calibrate.

**Stage 3: RFQ (Request for Quote) — if applicable**
- Purpose: Final pricing comparison for commodity/standard items.
- Used when: Requirements are well-defined and differentiator is price.

**Evaluation Criteria Weighting Example:**
| Criterion | Weight |
|----------|--------|
| Solution fit / functionality | 30% |
| Price / total cost of ownership | 25% |
| Implementation approach | 15% |
| Vendor stability / references | 15% |
| Support / SLA commitments | 10% |
| Innovation / roadmap | 5% |

---

### Vendor Risk Tiers

| Tier | Definition | Examples | Review Cadence | Contract Length |
|------|-----------|---------|----------------|----------------|
| **Critical** | Business cannot operate without them | Cloud provider, core SaaS, payment processor | Monthly scorecard, Quarterly QBR | Multi-year with exit planning |
| **Strategic** | Significant impact, alternatives exist but switching is costly | CRM, ERP, major staffing partner | Quarterly scorecard, Semi-annual QBR | 1-3 years |
| **Tactical** | Supports operations, readily replaceable | Office supplies, standard tools | Semi-annual scorecard | 1 year or PO-based |
| **Commodity** | Interchangeable, price-driven | Generic SaaS, standard services | Annual review | As needed |

---

### Contract Negotiation Checklist
- [ ] Pricing: Unit price, volume discounts, price escalation caps, payment terms.
- [ ] SLAs: Uptime, response times, resolution times, penalties for misses.
- [ ] Data: Ownership, portability, deletion on termination, processing location.
- [ ] Security: Certifications required, audit rights, breach notification timeline.
- [ ] Liability: Caps, indemnification, insurance requirements.
- [ ] Termination: Notice period, termination for convenience, data return.
- [ ] Change management: How changes to scope/pricing are handled.
- [ ] Escalation: Named contacts, escalation paths, executive sponsors.

### Ongoing Performance Review

| Frequency | Activity | Participants |
|-----------|---------|-------------|
| Monthly | Scorecard review, issue tracking | Account manager + internal owner |
| Quarterly | Business review (QBR): performance trends, roadmap, strategic alignment | Leadership from both sides |
| Annually | Strategic review: contract renewal decision, market comparison, relationship health | Executive sponsors |

### Vendor Consolidation Analysis
- List all vendors by category.
- Identify overlap (multiple vendors serving same need).
- Calculate: potential savings from consolidation, risk of concentration.
- Decision: consolidate if savings >15% AND concentration risk acceptable (no single vendor >40% of critical category).

### Exit Planning Checklist
- [ ] Data export: format, completeness, timeline.
- [ ] Transition plan: parallel running period, knowledge transfer.
- [ ] Contract obligations: notice period met, termination fees calculated.
- [ ] Alternative vendor: selected, contracted, onboarded.
- [ ] Communication: internal teams notified, training on new vendor.
- [ ] Verification: all data migrated, old vendor access revoked.

### Make-vs-Buy Framework
| Factor | Build In-House | Buy / Outsource |
|--------|---------------|----------------|
| Core competency? | Yes — strategic advantage | No — commodity capability |
| Expertise available? | Yes — team has skills | No — would need to hire |
| Time to deliver | Can meet timeline | Faster with vendor |
| Cost (3-year TCO) | Lower when amortized | Lower for non-core |
| Control required | High — regulatory, IP | Low — standard process |
| Maintenance burden | Willing to own long-term | Prefer vendor manages |

**Decision rule:** Build if it is a core differentiator AND you have (or can build) the expertise. Buy everything else.
""",
)

status_report_generation = Skill(
    name="status_report_generation",
    description="Status report creation with executive summaries, RAG methodology, KPI reporting, risk registers, and stakeholder-specific views.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.EXEC],
    knowledge_summary="Executive summary format (3-sentence structure), RAG status methodology with clear criteria, KPI reporting with trend indicators, risk register updates, and stakeholder-specific report views (executive, team, board).",
    knowledge="""
## Status Report Creation Framework

### Executive Summary Format

**The 3-Sentence Structure:**
1. **What is on track:** "[X] of [Y] initiatives are on track. Key wins this period: [brief highlight]."
2. **What is at risk:** "[N] items are at risk due to [root cause]. Mitigation in progress: [brief action]."
3. **What needs decisions:** "[Specific decision needed] by [date] to unblock [what]."

**Example:**
"7 of 9 Q2 initiatives are on track, with the new customer portal launching ahead of schedule. Two items are at risk: the data migration is 1 week behind due to unexpected schema complexity, and vendor onboarding is stalled pending legal review. We need executive approval on the revised migration timeline by Friday to maintain the Q2 launch target."

---

### RAG Status Methodology

| Status | Color | Criteria | Action Required |
|--------|-------|----------|----------------|
| **Green** | On Track | On schedule, on budget, no blockers, risks mitigated | Continue as planned |
| **Amber** | At Risk | Trending negative on schedule OR budget, risks emerging, mitigation underway | Monitor closely, escalate if no improvement in 1 week |
| **Red** | Blocked / Behind | Behind schedule AND/OR over budget, active blockers, mitigation failing | Immediate escalation, recovery plan required |

**RAG Assignment Rules:**
- Schedule: Green = on time, Amber = <1 week delay, Red = >1 week delay.
- Budget: Green = within 5%, Amber = 5-15% over, Red = >15% over.
- Scope: Green = no changes, Amber = minor scope adjustment, Red = significant scope change.
- Overall RAG = worst of (schedule, budget, scope) unless mitigated.

**Trend Indicators:**
- Arrow up: improving from last period.
- Arrow flat: unchanged.
- Arrow down: deteriorating from last period.
- RAG + trend gives full picture (e.g., Amber-improving is less concerning than Amber-declining).

---

### KPI Reporting Template

| KPI | Target | Actual | Variance | Trend | RAG |
|-----|--------|--------|----------|-------|-----|
| Revenue | $1.2M | $1.15M | -4.2% | Flat | Amber |
| Customer NPS | 45 | 48 | +6.7% | Up | Green |
| Sprint Velocity | 42 pts | 38 pts | -9.5% | Down | Amber |
| Uptime | 99.9% | 99.95% | +0.05% | Up | Green |

**Rules for KPI tables:**
- Always show target AND actual (never just actual).
- Calculate variance as percentage.
- Include trend arrow (vs last period).
- RAG based on variance thresholds defined per KPI.
- Footnote any changes in methodology or data source.

---

### Risk Register Update

| ID | Risk | Likelihood | Impact | Score | Owner | Mitigation | Status | Change |
|----|------|-----------|--------|-------|-------|-----------|--------|--------|
| R-001 | Key developer attrition | 3 | 4 | 12 | Eng Lead | Cross-training, retention bonus | Active | New |
| R-002 | Vendor API deprecation | 2 | 3 | 6 | Tech Lead | Migration plan drafted | Mitigating | Decreased |
| R-003 | Budget overrun on infra | 4 | 3 | 12 | Ops Lead | Reserved funds allocated | Active | Unchanged |

**Update protocol:** Review every reporting period. For each risk:
- New risks: added since last report.
- Changed risks: score or status changed.
- Closed risks: moved to archive with closure reason.
- Escalated risks: score increased above threshold.

---

### Action Item Tracking

| ID | Action | Owner | Due Date | Status | Blockers |
|----|--------|-------|----------|--------|----------|
| A-001 | Finalize vendor contract | Legal | Mar 28 | In Progress | Awaiting vendor redline |
| A-002 | Deploy staging environment | DevOps | Mar 25 | Complete | None |
| A-003 | Hire 2 frontend engineers | HR | Apr 15 | At Risk | Candidate pipeline thin |

**Rules:** Every action has a single owner (person, not team), a specific due date, and a clear definition of done.

### Milestone Tracking

| Milestone | Planned Date | Actual Date | % Complete | RAG |
|-----------|-------------|-------------|-----------|-----|
| Requirements signed off | Feb 15 | Feb 15 | 100% | Green |
| Design complete | Mar 1 | Mar 5 | 100% | Amber |
| Development complete | Apr 15 | — | 65% | Green |
| UAT complete | May 1 | — | 0% | Green |
| Go-live | May 15 | — | 0% | Green |

### Budget Tracking

| Category | Planned | Actual | Forecast | Variance |
|----------|---------|--------|----------|----------|
| Personnel | $200K | $195K | $200K | -$5K (2.5% under) |
| Infrastructure | $50K | $58K | $62K | +$12K (24% over) |
| Vendor/Tools | $30K | $28K | $30K | $0 (on budget) |
| **Total** | **$280K** | **$281K** | **$292K** | **+$12K (4.3% over)** |

### Stakeholder-Specific Views

**Executive View (1-page):**
- 3-sentence summary.
- Overall RAG status.
- Top 5 KPIs with trends.
- Top 3 risks.
- Decisions needed.

**Team View (detailed):**
- All KPIs with analysis.
- Full risk register.
- All action items.
- Detailed milestone tracking.
- Resource utilization.

**Board View (strategic):**
- Initiative portfolio RAG summary.
- Financial performance vs plan.
- Strategic risks and opportunities.
- Key decisions made and upcoming.
- Quarterly trend analysis.
""",
)

operational_runbook = Skill(
    name="operational_runbook",
    description="Operational runbook creation with step format standards, common runbook types, automation opportunities, and on-call reference cards.",
    category="operations",
    agent_ids=[AgentID.OPS],
    knowledge_summary="Runbook structure (purpose, prerequisites, procedure, verification, troubleshooting, rollback, escalation), step format with expected results, common runbook types (deployment, incident, backup, scaling), automation identification, and testing requirements.",
    knowledge="""
## Operational Runbook Creation Guide

### Runbook Document Structure

```
OPERATIONAL RUNBOOK
===================
Title:          [System/Process] — [Action Type]
Runbook ID:     RB-[SYSTEM]-[###]
Version:        [X.Y]
Last Updated:   [YYYY-MM-DD]
Author:         [Name]
Approved By:    [Name]
Classification: [Standard / Emergency / Maintenance]

1. PURPOSE
   [One sentence: what this runbook accomplishes.]

2. SCOPE
   - System(s): [list]
   - Environment(s): [production, staging, etc.]
   - When to use: [trigger condition]
   - When NOT to use: [exclusions]

3. PREREQUISITES
   - Access required: [SSH keys, VPN, console access, etc.]
   - Tools needed: [CLI tools, scripts, dashboards]
   - Permissions: [IAM roles, sudo access]
   - Dependencies: [other systems that must be running]

4. PROCEDURE
   [See Step Format below]

5. VERIFICATION / VALIDATION
   [How to confirm the procedure succeeded]

6. TROUBLESHOOTING
   [Common issues and resolutions]

7. ROLLBACK
   [Steps to undo the procedure]

8. ESCALATION CONTACTS
   | Role | Name | Contact | Availability |
   |------|------|---------|-------------|
   | Primary On-Call | ... | ... | 24/7 |
   | Secondary | ... | ... | Business hours |
   | Manager | ... | ... | Escalation only |

9. REVISION HISTORY
   | Version | Date | Author | Changes |
   |---------|------|--------|---------|
```

---

### Step Format Standard

Each step follows this pattern:

```
Step [N]: [ACTION TITLE]

Action:
  [Exact command or action to perform]

  $ kubectl rollout restart deployment/api-server -n production

Expected Result:
  [What you should see if it worked]

  deployment.apps/api-server restarted
  Pods cycling: 3/3 ready within 60 seconds

If Unexpected:
  - If pods not ready after 120s: See Troubleshooting T-003
  - If error "ImagePullBackOff": Check container registry auth (Step N+1)
  - If rollout stuck: Execute Rollback Step R-001

Estimated Duration: [2 minutes]
Can Be Automated: [Yes / No / Partially]
```

**Writing Rules:**
- One action per step. Never combine "do X and then Y" in one step.
- Copy-pasteable commands (no pseudocode in production runbooks).
- Include exact expected output, not "it should work."
- Always include the "If Unexpected" section — this is where runbooks earn their value.
- Timestamp-sensitive steps: note time windows and dependencies.

---

### Common Runbook Types

**1. Deployment Runbook**
- Pre-deployment checks (health, backups, feature flags).
- Deployment steps (blue-green, canary, rolling).
- Post-deployment verification (smoke tests, monitoring).
- Rollback procedure with time estimates.

**2. Incident Response Runbook**
- Detection: How the incident is identified (alert, customer report).
- Triage: Severity classification, initial assessment.
- Mitigation: Immediate actions to reduce impact.
- Resolution: Root cause fix.
- Post-incident: Timeline documentation, RCA trigger.

**3. Backup / Restore Runbook**
- Backup: Schedule, retention, verification steps.
- Restore: Point-in-time recovery, full restore, partial restore.
- Validation: Data integrity checks post-restore.
- Tested quarterly with documented results.

**4. Scaling Runbook**
- Horizontal scaling: Add instances (manual and auto-scaling triggers).
- Vertical scaling: Resize instances (requires downtime?).
- Database scaling: Read replicas, connection pool adjustment.
- Capacity thresholds that trigger each scaling action.

**5. Maintenance Runbook**
- Patching: OS, application, dependency updates.
- Certificate rotation: Steps, validation, rollback.
- Log rotation and cleanup: Disk space management.
- Database maintenance: Vacuum, reindex, statistics update.

**6. Monitoring Alert Response**
- Alert name and description.
- What it means (not just what metric crossed threshold).
- Immediate actions (check X, restart Y, page Z).
- When to escalate vs. when to acknowledge and monitor.

---

### Automation Opportunities

**Criteria for automation candidates:**
| Criterion | Automate If |
|----------|------------|
| Frequency | Performed weekly or more often |
| Complexity | Steps are deterministic (no judgment calls) |
| Risk of human error | High (copy-paste errors, missed steps) |
| Duration | Takes >15 minutes manually |
| Off-hours | Needs to run outside business hours |

**Automation progression:**
1. **Document** the manual procedure (this runbook).
2. **Script** individual steps.
3. **Chain** scripts into orchestrated workflow.
4. **Monitor** automated execution with human approval gates.
5. **Full auto** with alerting on failure.

**Keep manual:** Steps requiring judgment, customer communication, security-sensitive decisions.

---

### Testing Requirements
- **Frequency:** Quarterly dry-run in staging. After any change to the procedure.
- **Participants:** At least one person who was NOT the author.
- **Documentation:** Record test date, tester, environment, outcome, issues found.
- **Failure simulation:** Intentionally trigger the "If Unexpected" paths to validate troubleshooting steps.

### Access Control
- **Who can execute:** Defined roles (e.g., SRE, on-call engineer, DBA).
- **Who approves execution:** For production changes, require approval from on-call lead.
- **Audit trail:** Log who executed, when, which version, outcome.

### On-Call Reference Card Format

```
ON-CALL QUICK REFERENCE
========================
Service: [Service Name]
Dashboard: [URL]
Logs: [URL or command]
Runbooks: [Link to runbook index]

Common Alerts:
  [Alert Name] → [Runbook ID] → [1-line action]
  [Alert Name] → [Runbook ID] → [1-line action]

Escalation:
  L1 (you): [scope]
  L2 (senior): [when to escalate]
  L3 (management): [when to escalate]

Key Commands:
  $ [health check command]
  $ [restart command]
  $ [log tail command]
```
""",
)

operational_risk_assessment = Skill(
    name="operational_risk_assessment",
    description="Operational risk identification and mitigation with probability-impact matrix, risk appetite framework, control effectiveness rating, and key risk indicators.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.LEGAL, AgentID.EXEC],
    knowledge_summary="Risk categories (process, technology, people, vendor, regulatory, disaster, cyber, reputation), probability-impact matrix (5x5), risk appetite framework, control effectiveness rating, residual risk calculation, treatment strategies, and key risk indicators.",
    knowledge="""
## Operational Risk Assessment Framework

### Risk Categories

| Category | Description | Examples |
|----------|-----------|---------|
| **Process Failure** | Breakdown in business processes | Manual errors, missed steps, process gaps, inadequate controls |
| **Technology Failure** | IT system outages or malfunctions | Server crashes, data corruption, integration failures, software bugs |
| **People / Key-Person** | Dependency on specific individuals | Single point of failure, skill gaps, unexpected departures, tribal knowledge |
| **Vendor / Supply Chain** | Third-party failures | Vendor outage, supply disruption, contract dispute, vendor bankruptcy |
| **Regulatory Change** | New or changed regulations | New compliance requirements, enforcement actions, reporting changes |
| **Natural Disaster** | Physical disruptions | Flood, fire, earthquake, pandemic, power outage |
| **Cyber Security** | Digital threats | Ransomware, phishing, data breach, DDoS, insider threat |
| **Reputation** | Brand and trust damage | PR crisis, customer data exposure, product failure, social media incident |

---

### Risk Identification Techniques

**1. Process Walkthroughs**
- Walk through each step of a process with the team.
- At each step ask: "What could go wrong? What if this step fails?"
- Document: risk, cause, effect, current controls.

**2. Failure Mode and Effect Analysis (FMEA)**
- For each process step: identify failure modes.
- Rate: Severity (1-10) x Occurrence (1-10) x Detection (1-10) = Risk Priority Number (RPN).
- Prioritize: Address highest RPN first.
- Re-rate after implementing controls.

**3. Incident History Review**
- Review last 12 months of incidents, near-misses, audit findings.
- Categorize by risk type.
- Identify patterns and recurring themes.
- Update risk register with evidenced risks.

**4. What-If Scenarios**
- "What if our primary cloud region goes down?"
- "What if our top engineer leaves tomorrow?"
- "What if a key vendor doubles their pricing?"
- "What if we receive a data subject access request for 10,000 records?"
- Document each scenario: likelihood, impact, current preparedness, gap.

---

### Probability-Impact Matrix (5x5)

**Probability Scale:**
| Level | Label | Definition | Frequency Indicator |
|-------|-------|-----------|-------------------|
| 1 | Rare | Exceptional circumstances | <1% chance in 12 months |
| 2 | Unlikely | Could occur but not expected | 1-10% chance |
| 3 | Possible | Might occur at some time | 10-50% chance |
| 4 | Likely | Will probably occur | 50-90% chance |
| 5 | Almost Certain | Expected to occur | >90% chance |

**Impact Scale:**
| Level | Label | Financial | Operational | Reputational |
|-------|-------|-----------|-------------|-------------|
| 1 | Insignificant | <$10K | No disruption | No media attention |
| 2 | Minor | $10K-$50K | <4 hrs disruption | Local media |
| 3 | Moderate | $50K-$250K | 4-24 hrs disruption | Industry media |
| 4 | Major | $250K-$1M | 1-7 days disruption | National media |
| 5 | Catastrophic | >$1M | >7 days disruption | Sustained negative coverage |

**Risk Matrix:**
```
Impact ->    1    2    3    4    5
Prob 5:      5   10   15   20   25  (Almost Certain)
Prob 4:      4    8   12   16   20  (Likely)
Prob 3:      3    6    9   12   15  (Possible)
Prob 2:      2    4    6    8   10  (Unlikely)
Prob 1:      1    2    3    4    5  (Rare)
```

**Risk Zones:**
- 1-4: **Low** (accept and monitor)
- 5-9: **Medium** (active management required)
- 10-15: **High** (senior management attention, priority mitigation)
- 16-25: **Critical** (immediate executive action required)

---

### Risk Appetite Statement Framework

**Components:**
1. **Risk appetite:** The amount and type of risk the organization is willing to pursue or retain.
2. **Risk tolerance:** The acceptable deviation from the risk appetite.
3. **Risk capacity:** The maximum risk the organization can absorb.

**Template by category:**
| Category | Appetite | Tolerance | Boundary |
|----------|---------|-----------|----------|
| Financial | Moderate | Up to 5% revenue variance | No single loss >$500K |
| Compliance | Very Low | Zero tolerance for material violations | All regulatory requirements met |
| Technology | Moderate | 99.9% uptime target | No data loss events |
| Reputation | Low | No sustained negative coverage | Immediate crisis response required |

---

### Control Effectiveness Rating

| Rating | Definition | Criteria |
|--------|-----------|---------|
| **Effective** | Control operates as designed | Tested, evidence available, no exceptions in last 12 months |
| **Partially Effective** | Control has gaps | Some evidence, occasional exceptions, needs improvement |
| **Ineffective** | Control does not achieve objective | Failed testing, frequent exceptions, not operating as designed |

**Testing methods:**
- Inquiry: Ask control owner (weakest evidence).
- Observation: Watch the control operate.
- Inspection: Review evidence artifacts.
- Re-performance: Execute the control yourself (strongest evidence).

### Residual Risk Calculation

```
Inherent Risk = Probability x Impact (before controls)
Control Effectiveness Factor:
  Effective = 0.3 (reduces risk by 70%)
  Partially Effective = 0.6 (reduces risk by 40%)
  Ineffective = 1.0 (no reduction)

Residual Risk = Inherent Risk x Control Effectiveness Factor
```

**Example:**
- Inherent risk: Probability 4 x Impact 3 = 12 (High)
- Control: Automated backup with daily verification (Effective, factor 0.3)
- Residual risk: 12 x 0.3 = 3.6 -> round to 4 (Low)

---

### Risk Treatment Strategies

| Strategy | When to Use | Example |
|----------|-----------|---------|
| **Avoid** | Risk is unacceptable and can be eliminated | Stop offering a service that creates regulatory exposure |
| **Reduce** | Risk can be lowered to acceptable level | Add automated testing, implement redundancy, add monitoring |
| **Transfer** | Risk is better managed by a third party | Insurance, outsourcing, contractual liability shift |
| **Accept** | Risk is within appetite and cost to treat exceeds benefit | Accept minor operational inefficiency, monitor with KRI |

---

### Key Risk Indicators (KRIs)

**Leading indicators (predict risk events before they occur):**
| KRI | Risk It Predicts | Threshold |
|-----|-----------------|-----------|
| Employee turnover rate | Key-person risk | >15% annual |
| Failed login attempts | Cyber security breach | >3x baseline |
| SLA near-misses | Service failure | >3 per month |
| Vendor financial news sentiment | Vendor failure | Negative trend |
| Change failure rate | Process failure | >15% of changes |
| Unpatched critical vulnerabilities | Cyber attack | Any >30 days old |
| Customer complaint trend | Reputation risk | >10% MoM increase |

**Monitoring cadence:**
- Critical KRIs: Real-time or daily.
- High KRIs: Weekly.
- Medium KRIs: Monthly.
- Low KRIs: Quarterly.

### Business Impact Analysis Template

| Process | RTO | RPO | Impact if Unavailable | Dependencies | Recovery Strategy |
|---------|-----|-----|----------------------|-------------|-------------------|
| Order Processing | 4 hrs | 1 hr | Revenue loss, customer dissatisfaction | ERP, Payment Gateway | Failover to backup, manual processing |
| Customer Support | 2 hrs | 0 (real-time) | SLA breach, churn risk | CRM, Phone System | Cloud-based backup, overflow to partner |
| Payroll | 24 hrs | 4 hrs | Employee dissatisfaction, legal risk | HRIS, Banking | Manual payment as backup |

**RTO** = Recovery Time Objective (how fast must it be restored).
**RPO** = Recovery Point Objective (how much data loss is acceptable).
""",
)

process_optimization = Skill(
    name="process_optimization",
    description="Business process improvement with Lean, Six Sigma DMAIC, value stream mapping, bottleneck resolution, automation assessment, and continuous improvement culture.",
    category="operations",
    agent_ids=[AgentID.OPS, AgentID.DATA],
    knowledge_summary="Process mining methodology, Lean 8 wastes identification, improvement frameworks (Lean, Six Sigma DMAIC, TOC, BPR), value stream mapping, automation opportunity assessment, and A3 problem-solving template.",
    knowledge="""
## Business Process Improvement Framework

### Process Mining Methodology

**Step 1: Data Collection**
- Extract event logs from systems (ERP, CRM, ticketing, workflow tools).
- Required fields: Case ID, Activity Name, Timestamp, Resource (optional), other attributes.
- Minimum: 1,000 cases for statistical significance.

**Step 2: Process Discovery**
- Automatically generate process map from event logs.
- Identify: most common paths (happy path), variants, loops, rework.
- Metrics per activity: frequency, average duration, resource utilization.

**Step 3: Conformance Checking**
- Compare discovered process to documented/intended process.
- Identify deviations: skipped steps, out-of-order activities, unauthorized paths.
- Quantify: % of cases conforming, % with each type of deviation.

**Step 4: Enhancement**
- Overlay performance data on process map (bottleneck heatmap).
- Identify: slowest activities, longest wait times, highest rework rates.
- Prioritize improvements by impact.

---

### Waste Identification — Lean 8 Wastes (DOWNTIME)

| Waste | Definition | Business Process Examples | Detection Method |
|-------|-----------|-------------------------|-----------------|
| **D**efects | Errors requiring rework | Data entry errors, incorrect invoices, wrong shipments | Error/rework rate tracking |
| **O**verproduction | Producing more than needed | Generating reports nobody reads, over-engineering features | Usage analytics, stakeholder survey |
| **W**aiting | Idle time between steps | Approval queue delays, waiting for information, batch processing delays | Queue time measurement |
| **N**on-utilized talent | Not using people's full capabilities | Senior engineers doing data entry, manual work that could be automated | Skills matrix vs task analysis |
| **T**ransportation | Unnecessary movement of information | Emailing documents between systems, manual data transfer, paper routing | Process map analysis |
| **I**nventory | Excess work in progress | Backlog buildup, unprocessed requests, pending approvals | WIP tracking, queue depth |
| **M**otion | Unnecessary actions by people | Switching between systems, searching for information, redundant data entry | Time-motion study, screen recording analysis |
| **E**xtra-processing | Doing more than customer requires | Over-documentation, excessive approvals, gold-plating deliverables | Value analysis — does customer pay for this? |

---

### Improvement Frameworks

**1. Lean**
- Focus: Eliminate waste, maximize value flow.
- Key tools: Value stream mapping, 5S, Kanban, Poka-Yoke (error-proofing).
- Approach: Continuous small improvements (Kaizen).
- Best for: Process simplification, flow optimization.

**2. Six Sigma DMAIC**
- **D**efine: Problem statement, project charter, voice of customer.
- **M**easure: Current process performance, baseline metrics, measurement system analysis.
- **A**nalyze: Root cause analysis (fishbone, 5 Whys, Pareto), statistical analysis, hypothesis testing.
- **I**mprove: Solution design, pilot testing, implementation plan.
- **C**ontrol: Control charts, monitoring plan, process documentation, training.
- Best for: Reducing variation and defects in established processes.

**3. Theory of Constraints (TOC)**
- Identify the constraint (bottleneck).
- Exploit: Maximize throughput at the constraint.
- Subordinate: Align everything else to support the constraint.
- Elevate: Invest to increase constraint capacity.
- Repeat: Find the next constraint.
- Best for: Throughput improvement, capacity optimization.

**4. Business Process Reengineering (BPR)**
- Fundamental rethinking and radical redesign.
- Question: "If we were starting from scratch, how would we design this?"
- Best for: Broken processes that need complete overhaul, not incremental improvement.
- Risk: High disruption, requires strong change management.

---

### Value Stream Mapping

**Current State Map:**
1. Identify the process to map (start and end points).
2. Walk the process physically (Gemba walk).
3. Document each step: process time, wait time, inventory/queue, FTE, %C&A.
4. Calculate: Total lead time, total process time, process efficiency (process time / lead time).
5. Identify waste and improvement opportunities.

**Future State Map:**
1. Define target: What does the ideal flow look like?
2. Apply Lean principles: continuous flow, pull systems, level loading.
3. Eliminate or reduce: wait times, batching, unnecessary approvals, rework loops.
4. Calculate: Expected lead time, expected efficiency.
5. Identify: What must change to achieve future state.

**Implementation Plan:**
- Gap analysis: current vs future state.
- Prioritized action items with owners and deadlines.
- Quick wins (implement in <2 weeks) vs structural changes (2-6 months).

---

### Cycle Time Analysis

```
Lead Time = Queue Time + Process Time + Wait Time + Move Time

Process Efficiency = Process Time / Lead Time x 100%

Typical findings:
- Manufacturing: 5-25% process efficiency
- Office/Admin: 1-10% process efficiency (most time is waiting)
- Software development: 5-15% process efficiency
```

**Improvement levers:**
1. Reduce queue time: Reduce batch sizes, implement pull systems.
2. Reduce process time: Automation, skill improvement, better tools.
3. Reduce wait time: Eliminate approvals, co-locate teams, real-time notifications.
4. Reduce move time: System integration, eliminate handoffs.

### Bottleneck Identification and Resolution
- **Identify:** Step with longest queue or lowest throughput.
- **Quantify:** How much does it limit overall throughput?
- **Quick fixes:** Overtime, temporary resources, simplified process.
- **Structural fixes:** Automation, parallelization, capacity addition, process redesign.
- **Validate:** Re-measure after fix; confirm new bottleneck is acceptable.

---

### Automation Opportunity Assessment

| Criterion | Score 1-5 | Weight |
|----------|----------|--------|
| Rule-based (no judgment) | | 25% |
| High volume (>50x/week) | | 25% |
| Error-prone manual steps | | 20% |
| Stable process (low change rate) | | 15% |
| Digital inputs/outputs | | 15% |

**Weighted Score > 3.5:** Strong automation candidate.
**Weighted Score 2.5-3.5:** Partial automation (assist, not replace).
**Weighted Score < 2.5:** Keep manual (for now).

**Automation approaches by score:**
- 4.0+: Full automation (RPA, scripts, workflow engine).
- 3.0-3.9: Assisted automation (pre-fill, validation, routing).
- 2.0-2.9: Templates and checklists (reduce cognitive load).

### Improvement Prioritization Matrix

| | Low Effort | High Effort |
|--|-----------|------------|
| **High Impact** | **Quick Wins** — Do immediately | **Major Projects** — Plan and resource |
| **Low Impact** | **Fill-ins** — Do when capacity allows | **Avoid** — Not worth the investment |

### A3 Problem-Solving Template

```
A3 PROBLEM SOLVING REPORT
==========================
Title: [Problem Name]               Owner: [Name]
Date: [YYYY-MM-DD]                  Status: [Active/Closed]

1. BACKGROUND
   [Context: why this matters, what triggered the investigation]

2. CURRENT CONDITION
   [Data showing the problem: metrics, charts, process map excerpt]

3. GOAL / TARGET
   [Specific, measurable target: "Reduce invoice processing time from 5 days to 2 days"]

4. ROOT CAUSE ANALYSIS
   [5 Whys, fishbone diagram, or Pareto analysis]

5. COUNTERMEASURES
   | # | Action | Owner | Due | Status |
   |---|--------|-------|-----|--------|

6. CONFIRMATION OF EFFECT
   [How will we measure success? Before/after comparison plan]

7. FOLLOW-UP ACTIONS
   [Standardize, share learnings, update documentation]
```

### Continuous Improvement Culture
- **Kaizen events:** 3-5 day focused improvement workshops. Team maps process, identifies waste, implements improvements, measures results.
- **Suggestion systems:** Structured way for any employee to propose improvements. Track: submitted, reviewed, implemented, impact measured.
- **Gemba walks:** Leaders visit where work happens. Observe, ask questions, do not direct. Frequency: weekly for managers, monthly for executives.
- **Visual management:** Make process performance visible (dashboards, Kanban boards, Andon signals).
- **Standard work:** Document the current best-known method. Improve from the standard, then update it.
""",
)


# =============================================================================
# Data Skills
# =============================================================================

sql_query_writing = Skill(
    name="sql_query_writing",
    description="Optimized SQL across dialects with join optimization, window functions, analytical query patterns, and anti-patterns to avoid.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.FIN],
    knowledge_summary="SQL best practices (CTEs, aliases, avoid SELECT *), join optimization, window functions for analytics, common analytical queries (cohort, funnel, RFM), dialect differences (BigQuery, Snowflake, PostgreSQL), and performance optimization with EXPLAIN ANALYZE.",
    knowledge="""
## SQL Query Writing — Optimized Across Dialects

### Query Structure Best Practices

**Readability:**
- SELECT specific columns (never SELECT * in production).
- Use meaningful aliases: `o` for orders, `c` for customers (or full names for complex queries).
- Use CTEs (WITH clauses) for readability — one logical step per CTE.
- Indent consistently: keywords left-aligned, columns indented.

**Template:**
```sql
WITH filtered_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.total_amount
    FROM orders AS o
    WHERE o.order_date >= '2024-01-01'
      AND o.status = 'completed'
),
customer_totals AS (
    SELECT
        customer_id,
        COUNT(*) AS order_count,
        SUM(total_amount) AS lifetime_value
    FROM filtered_orders
    GROUP BY customer_id
)
SELECT
    ct.customer_id,
    c.name,
    ct.order_count,
    ct.lifetime_value
FROM customer_totals AS ct
JOIN customers AS c ON c.id = ct.customer_id
ORDER BY ct.lifetime_value DESC
LIMIT 100;
```

---

### Join Optimization

| Join Type | When to Use | Performance Note |
|-----------|-----------|-----------------|
| INNER JOIN | Only matching rows needed | Fastest; optimizer can reorder |
| LEFT JOIN | Need all rows from left table | More expensive than INNER; filter in ON, not WHERE |
| RIGHT JOIN | Avoid — rewrite as LEFT JOIN | Easier to read as LEFT |
| FULL OUTER | Need all rows from both tables | Most expensive; often indicates design issue |
| CROSS JOIN | Cartesian product needed (rare) | Dangerous on large tables |

**Optimization tips:**
- Join on indexed columns.
- Filter early (in CTEs or subqueries) to reduce join input size.
- Join order: smallest table first (though most optimizers handle this).
- Avoid joining on expressions (e.g., `LOWER(a.name) = LOWER(b.name)`) — not sargable.

---

### Window Functions for Analytics

**Running totals:**
```sql
SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS running_total
```

**Rankings:**
```sql
ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank_in_dept
RANK()       -- ties get same rank, next rank skipped
DENSE_RANK() -- ties get same rank, next rank NOT skipped
```

**Moving averages:**
```sql
AVG(daily_revenue) OVER (
    ORDER BY date_day
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS seven_day_moving_avg
```

**Lag / Lead (period-over-period):**
```sql
LAG(revenue, 1) OVER (ORDER BY month) AS prev_month_revenue,
revenue - LAG(revenue, 1) OVER (ORDER BY month) AS mom_change
```

**Percent of total:**
```sql
amount / SUM(amount) OVER (PARTITION BY category) * 100 AS pct_of_category
```

---

### Common Analytical Query Patterns

**1. Period-over-Period Comparison:**
```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', order_date) AS month,
           SUM(amount) AS revenue
    FROM orders GROUP BY 1
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev_month,
       ROUND((revenue - LAG(revenue) OVER (ORDER BY month))
             / LAG(revenue) OVER (ORDER BY month) * 100, 1) AS pct_change
FROM monthly;
```

**2. Cohort Retention:**
```sql
WITH first_purchase AS (
    SELECT customer_id, DATE_TRUNC('month', MIN(order_date)) AS cohort_month
    FROM orders GROUP BY 1
),
activity AS (
    SELECT o.customer_id, fp.cohort_month,
           DATE_TRUNC('month', o.order_date) AS activity_month,
           DATE_DIFF('month', fp.cohort_month, DATE_TRUNC('month', o.order_date)) AS months_since
    FROM orders o JOIN first_purchase fp ON o.customer_id = fp.customer_id
)
SELECT cohort_month, months_since, COUNT(DISTINCT customer_id) AS active_customers
FROM activity GROUP BY 1, 2 ORDER BY 1, 2;
```

**3. Funnel Analysis:**
```sql
SELECT
    COUNT(DISTINCT CASE WHEN event = 'page_view' THEN user_id END) AS step1_views,
    COUNT(DISTINCT CASE WHEN event = 'add_to_cart' THEN user_id END) AS step2_cart,
    COUNT(DISTINCT CASE WHEN event = 'checkout' THEN user_id END) AS step3_checkout,
    COUNT(DISTINCT CASE WHEN event = 'purchase' THEN user_id END) AS step4_purchase
FROM events WHERE event_date BETWEEN '2024-01-01' AND '2024-01-31';
```

**4. RFM Segmentation:**
```sql
WITH rfm AS (
    SELECT customer_id,
           DATE_DIFF('day', MAX(order_date), CURRENT_DATE) AS recency_days,
           COUNT(*) AS frequency,
           SUM(amount) AS monetary
    FROM orders GROUP BY 1
),
scored AS (
    SELECT *, NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
           NTILE(5) OVER (ORDER BY frequency) AS f_score,
           NTILE(5) OVER (ORDER BY monetary) AS m_score
    FROM rfm
)
SELECT *, r_score + f_score + m_score AS rfm_total FROM scored;
```

---

### Dialect Differences

| Feature | PostgreSQL | BigQuery | Snowflake |
|---------|-----------|----------|-----------|
| Date truncate | `DATE_TRUNC('month', d)` | `DATE_TRUNC(d, MONTH)` | `DATE_TRUNC('MONTH', d)` |
| Date diff | `date2 - date1` or `AGE()` | `DATE_DIFF(d2, d1, DAY)` | `DATEDIFF('day', d1, d2)` |
| Array agg | `ARRAY_AGG(x)` | `ARRAY_AGG(x)` | `ARRAY_AGG(x)` |
| String agg | `STRING_AGG(x, ',')` | `STRING_AGG(x, ',')` | `LISTAGG(x, ',')` |
| Nested data | JSONB operators | STRUCT, ARRAY, UNNEST | VARIANT, FLATTEN |
| Lateral join | `LATERAL` | `UNNEST()` in FROM | `LATERAL FLATTEN()` |
| Time travel | N/A | `FOR SYSTEM_TIME AS OF` | `AT(TIMESTAMP => ...)` |
| Approx count | `N/A` (extension) | `APPROX_COUNT_DISTINCT()` | `APPROX_COUNT_DISTINCT()` |

---

### Performance Optimization

**EXPLAIN ANALYZE:** Always run on complex queries before production.
- Look for: sequential scans on large tables, nested loop joins on large sets, high row estimates vs actuals.
- Fix: Add indexes, rewrite joins, add WHERE filters, use materialized views.

**Key optimizations:**
- **Partition pruning:** Ensure WHERE clause includes partition key.
- **Materialized views:** Pre-compute expensive aggregations, refresh on schedule.
- **Query caching:** Identical queries return cached results (BigQuery, Snowflake).
- **Approximate functions:** Use `APPROX_COUNT_DISTINCT` when exact count unnecessary.

### Anti-Patterns to Avoid
| Anti-Pattern | Why It Is Bad | Fix |
|-------------|-------------|-----|
| `SELECT *` | Reads unnecessary columns, breaks if schema changes | List specific columns |
| Correlated subqueries | Executes per-row, O(n^2) | Rewrite as JOIN or CTE |
| `WHERE LOWER(col) = 'x'` | Non-sargable, cannot use index | Use case-insensitive collation or functional index |
| Implicit type casting | Prevents index usage, unexpected results | Explicit CAST |
| `NOT IN` with NULLs | Returns no rows if subquery has NULL | Use `NOT EXISTS` instead |
| `ORDER BY` without `LIMIT` | Sorts entire result set | Always pair with LIMIT or use in window function |
| Functions in WHERE on indexed columns | Prevents index scan | Move function to the constant side |
""",
)

data_exploration = Skill(
    name="data_exploration",
    description="Dataset profiling and exploration with quality assessment, pattern detection, statistical summaries, and data dictionary creation.",
    category="data",
    agent_ids=[AgentID.DATA],
    knowledge_summary="Initial profiling checklist (row/column counts, null rates, distributions), data quality dimensions (completeness, accuracy, consistency, timeliness, uniqueness), pattern detection (correlation, outliers via IQR/Z-score), and data dictionary template.",
    knowledge="""
## Dataset Profiling & Exploration Guide

### Initial Profiling Checklist

Run these checks on any new dataset before analysis:

**1. Shape and Structure:**
- Row count and column count.
- Data types per column (numeric, categorical, datetime, text, boolean).
- Memory footprint / estimated storage size.

**2. Completeness:**
| Column | Total Rows | Non-Null | Null Count | Null % |
|--------|-----------|----------|-----------|--------|
| ... | ... | ... | ... | ... |

- Flag columns with >5% nulls for investigation.
- Flag columns with 100% nulls (possibly deprecated or error).

**3. Numeric Column Summary:**
| Column | Min | Max | Mean | Median | Std Dev | Skewness | Kurtosis | Zeros % |
|--------|-----|-----|------|--------|---------|----------|----------|---------|

- Check for: impossible values (negative ages, future dates), suspicious ranges.
- Compare mean vs median — large difference indicates skew.

**4. Categorical Column Summary:**
| Column | Unique Values | Top Value | Top Frequency | Bottom Value | Bottom Frequency |
|--------|--------------|-----------|--------------|-------------|-----------------|

- Flag: single-value columns (no variance), near-unique columns (possible IDs).
- Check for: inconsistent casing, trailing spaces, encoding issues.

**5. Datetime Columns:**
- Min and max dates (expected range?).
- Gaps in time series (missing dates/hours?).
- Timezone consistency.

---

### Data Quality Assessment

| Dimension | Definition | How to Check | Threshold |
|----------|-----------|-------------|-----------|
| **Completeness** | Are all expected records and fields present? | Null rates, row count vs source count | >95% complete |
| **Accuracy** | Do values reflect reality? | Cross-validate against source, spot-check sample | 100% for key fields |
| **Consistency** | Are values consistent across sources? | Compare same entity across tables/systems | Zero conflicts |
| **Timeliness** | Is data current enough for the use case? | Check max timestamp vs expected freshness | Depends on use case |
| **Uniqueness** | Are there no unintended duplicates? | GROUP BY key columns, check for duplicate counts | Zero duplicates on PK |

**Data Quality Score:**
```
DQ Score = (Completeness x 0.25) + (Accuracy x 0.30) + (Consistency x 0.20) +
           (Timeliness x 0.15) + (Uniqueness x 0.10)
```

---

### Pattern Detection

**Correlation Matrix:**
- Calculate pairwise Pearson correlation for all numeric columns.
- Flag: |r| > 0.8 (high correlation — possible redundancy or multicollinearity).
- Flag: r ~ 0 for columns expected to correlate (data quality issue?).
- Visualize as heatmap with diverging color scale.

**Distribution Shapes:**
| Shape | Skewness | What It Means | Common In |
|-------|----------|--------------|-----------|
| Normal | ~0 | Symmetric, bell-shaped | Heights, test scores |
| Right-skewed | >0.5 | Long right tail | Income, prices, time durations |
| Left-skewed | <-0.5 | Long left tail | Age at retirement, saturation metrics |
| Bimodal | Two peaks | Two distinct populations | Mixed segments, AM/PM patterns |
| Uniform | ~0, flat | Equal probability | Random IDs, uniform sampling |

**Outlier Identification:**

*IQR Method:*
```
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1
Lower bound = Q1 - 1.5 * IQR
Upper bound = Q3 + 1.5 * IQR
Outliers = values outside [lower bound, upper bound]
```

*Z-Score Method:*
```
Z = (value - mean) / std_dev
Outlier if |Z| > 3 (or >2.5 for stricter threshold)
```

*Decision:* IQR is robust to skewed distributions. Z-score assumes normality. Use IQR by default.

---

### Exploratory Visualization Sequence

**Recommended order:**
1. **Histograms:** One per numeric column — understand distributions.
2. **Bar charts:** One per categorical column — understand value frequencies.
3. **Box plots:** Numeric columns grouped by key categoricals — compare distributions.
4. **Scatter plots:** Pairwise for numeric columns with high correlation — visualize relationships.
5. **Heatmaps:** Correlation matrix, missing data patterns.
6. **Time series:** If temporal data, plot key metrics over time.

---

### Statistical Summary Generation

```python
# Python / Pandas quick profiling
df.describe()                          # Numeric summary
df.describe(include='object')          # Categorical summary
df.isnull().sum() / len(df) * 100     # Null percentages
df.nunique()                           # Unique value counts
df.dtypes                              # Data types
df.duplicated().sum()                  # Duplicate row count
df.corr()                              # Correlation matrix
```

### Data Dictionary Template

| Column Name | Data Type | Description | Source | Valid Values / Range | Business Rules | Example |
|------------|----------|-------------|--------|---------------------|---------------|---------|
| customer_id | UUID | Unique customer identifier | CRM system | UUID format | Primary key, never null | a1b2c3d4-... |
| order_date | TIMESTAMP | When order was placed | Order system | 2020-01-01 to present | UTC timezone | 2024-03-15T14:30:00Z |
| amount | DECIMAL(10,2) | Order total in USD | Payment system | 0.01 - 999999.99 | Always positive, includes tax | 149.99 |
| status | VARCHAR(20) | Order status | Order system | pending, completed, cancelled, refunded | Transitions: pending->completed->refunded | completed |

### Sampling Strategies for Large Datasets
- **Random sampling:** Simple random sample of N rows. Good for general profiling.
- **Stratified sampling:** Sample proportionally from each segment. Use when data has distinct populations.
- **Systematic sampling:** Every Nth row. Quick but watch for periodic patterns.
- **Time-based sampling:** Recent N days. Good when recent data represents current state.
- **Reservoir sampling:** Streaming data. Maintains uniform random sample of fixed size.

### Common Data Issues
| Issue | Detection | Resolution |
|-------|----------|-----------|
| Encoding errors | Non-printable characters, mojibake | Re-import with correct encoding (UTF-8) |
| Mixed types | Column has both numbers and strings | Investigate source, cast or split |
| Phantom duplicates | Trailing spaces, invisible characters | TRIM, REPLACE special chars, then dedup |
| Timezone confusion | Same event at different times across sources | Standardize to UTC, document source TZ |
| Delimiter in values | CSV parsing errors, extra columns | Use proper quoting, switch to JSON/Parquet |
""",
)

statistical_analysis_methods = Skill(
    name="statistical_analysis_methods",
    description="Statistical analysis methodology covering descriptive stats, hypothesis testing, regression, time series, and common pitfalls.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.FIN],
    knowledge_summary="Descriptive statistics, hypothesis testing framework (null/alt hypothesis, p-value, effect size), common tests (t-test, ANOVA, chi-square, correlation), regression analysis with assumptions checking, time series methods (ARIMA, seasonality), and pitfalls (p-hacking, Simpson's paradox).",
    knowledge="""
## Statistical Analysis Methodology

### Descriptive Statistics

**Central Tendency:**
| Measure | When to Use | Sensitive to Outliers? |
|---------|-----------|----------------------|
| Mean | Symmetric distributions | Yes |
| Median | Skewed distributions, ordinal data | No |
| Mode | Categorical data, multimodal distributions | No |

**Dispersion:**
| Measure | Formula | Use |
|---------|---------|-----|
| Range | Max - Min | Quick sense of spread (unreliable) |
| IQR | Q3 - Q1 | Robust spread measure |
| Variance | Mean of squared deviations | Mathematical convenience |
| Standard Deviation | Square root of variance | Same units as data |
| Coefficient of Variation | (StdDev / Mean) x 100% | Compare spread across different scales |

**Shape:**
- **Skewness:** 0 = symmetric, >0 = right-skewed, <0 = left-skewed.
- **Kurtosis:** 3 = normal (mesokurtic), >3 = heavy tails (leptokurtic), <3 = light tails (platykurtic).
- Use excess kurtosis (kurtosis - 3) so normal distribution = 0.

---

### Hypothesis Testing Framework

**Step 1: State Hypotheses**
- H0 (Null): No effect / no difference (status quo).
- H1 (Alternative): There IS an effect / difference.
- Example: H0: mean_A = mean_B; H1: mean_A != mean_B.

**Step 2: Choose Significance Level**
- Alpha (a) = probability of rejecting H0 when it is true (Type I error).
- Standard: a = 0.05 (5%). Stricter: a = 0.01. Exploratory: a = 0.10.

**Step 3: Select Test** (see table below).

**Step 4: Calculate Test Statistic and p-value**
- p-value = probability of observing data this extreme if H0 is true.

**Step 5: Decision**
- p < a: Reject H0 (statistically significant).
- p >= a: Fail to reject H0 (not significant — does NOT prove H0 true).

**Step 6: Report Effect Size**
- Statistical significance != practical significance.
- Always report: effect size (Cohen's d, r^2, odds ratio) + confidence interval.

**Step 7: Power Analysis**
- Power = probability of detecting a real effect (1 - Type II error).
- Target: power >= 0.80.
- Determine sample size BEFORE collecting data.
- Underpowered studies produce unreliable results.

---

### Common Tests — When to Use

| Test | Use Case | Data Requirements | Example |
|------|---------|-------------------|---------|
| **One-sample t-test** | Compare sample mean to known value | Numeric, ~normal, n>30 | "Is our avg order value different from $50?" |
| **Independent t-test** | Compare means of 2 groups | Numeric, ~normal, equal variance | "Do control and treatment groups differ?" |
| **Paired t-test** | Compare before/after in same group | Numeric, paired observations | "Did the training improve scores?" |
| **One-way ANOVA** | Compare means of 3+ groups | Numeric, ~normal, equal variance | "Do regions differ in revenue?" |
| **Chi-square test** | Test independence of categories | Categorical, expected freq >= 5 | "Is churn related to plan type?" |
| **Mann-Whitney U** | Non-parametric 2-group comparison | Ordinal or non-normal numeric | "Do satisfaction ratings differ?" |
| **Kruskal-Wallis** | Non-parametric 3+ group comparison | Ordinal or non-normal numeric | "Do departments differ in tenure?" |
| **Pearson correlation** | Linear relationship strength | Numeric, ~normal, linear | "Is spend correlated with revenue?" |
| **Spearman correlation** | Monotonic relationship strength | Ordinal or non-normal | "Is rank correlated with satisfaction?" |

---

### Regression Analysis

**Linear Regression:**
- Predicts numeric outcome from one or more predictors.
- Equation: Y = b0 + b1*X1 + b2*X2 + ... + error.
- Interpret coefficients: "A 1-unit increase in X is associated with a b-unit change in Y."

**Logistic Regression:**
- Predicts binary outcome (yes/no, churn/not churn).
- Output: probability (0-1), classified via threshold (default 0.5).
- Interpret: odds ratios (OR>1 = increases odds, OR<1 = decreases odds).

**Assumptions to Check (Linear Regression):**

| Assumption | How to Check | What If Violated |
|-----------|-------------|-----------------|
| Linearity | Scatter plot of Y vs X, residual plot | Transform variables (log, polynomial) |
| Normality of residuals | Q-Q plot, Shapiro-Wilk test | Large samples are robust; transform Y |
| Homoscedasticity | Residual vs fitted plot (even spread?) | Use robust standard errors, transform Y |
| Independence | Durbin-Watson test (time series) | Add lagged terms, use time series models |
| No multicollinearity | VIF (Variance Inflation Factor) < 5 | Remove or combine correlated predictors |

---

### Time Series Methods

**Decomposition:**
- Trend: Long-term direction (increasing, decreasing, flat).
- Seasonality: Regular repeating pattern (daily, weekly, monthly, yearly).
- Residual: What remains after removing trend and seasonality.
- Methods: Additive (Y = T + S + R) vs Multiplicative (Y = T x S x R).

**Stationarity Testing:**
- ADF (Augmented Dickey-Fuller) test: H0 = non-stationary. If p < 0.05, data is stationary.
- If non-stationary: difference the series (d=1 usually sufficient).

**ARIMA Components:**
- AR (AutoRegressive, p): Value depends on its own lags.
- I (Integrated, d): Number of differences to achieve stationarity.
- MA (Moving Average, q): Value depends on past forecast errors.
- Seasonal ARIMA: SARIMA(p,d,q)(P,D,Q,s) for seasonal data.

**Seasonality Detection:**
- Visual: Plot data and look for repeating patterns.
- ACF plot: Spikes at seasonal lags.
- Fourier analysis: Decompose into frequency components.

---

### Confidence Intervals

**Interpretation:** "We are 95% confident the true population parameter falls within [lower, upper]."
- NOT: "There is a 95% probability the parameter is in this range."
- Width depends on: sample size (larger = narrower), variability (more = wider), confidence level (higher = wider).

**Sample Size Requirements:**
```
n = (Z^2 * sigma^2) / E^2

Where:
  Z = 1.96 for 95% confidence
  sigma = estimated population std dev
  E = desired margin of error
```

### Common Pitfalls

| Pitfall | Description | How to Avoid |
|---------|-----------|-------------|
| **P-hacking** | Running many tests until p < 0.05 | Pre-register hypotheses, apply Bonferroni correction |
| **Multiple comparisons** | Testing many pairs inflates false positive rate | Use Bonferroni, Holm, or FDR correction |
| **Correlation != Causation** | Two variables correlate but one does not cause the other | Use experiments (A/B test), control for confounders |
| **Survivorship bias** | Analyzing only surviving entities | Include failed/churned/dropped entities |
| **Simpson's Paradox** | Trend reverses when data is disaggregated | Always check subgroup analysis |
| **Base rate neglect** | Ignoring prior probability | Use Bayesian reasoning, report absolute numbers |
| **Cherry-picking** | Selecting only favorable time periods or segments | Pre-define analysis window, report all segments |
""",
)

data_visualization_best_practices = Skill(
    name="data_visualization_best_practices",
    description="Effective data visualization with chart selection guide, design principles, annotation best practices, and dashboard layout guidance.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.MKT, AgentID.FIN],
    knowledge_summary="Chart selection guide (comparison, composition, distribution, relationship, trend), design principles (data-ink ratio, accessibility), annotation best practices, dashboard layout (inverted pyramid, 5-second rule), and common visualization mistakes to avoid.",
    knowledge="""
## Data Visualization Best Practices

### Chart Selection Guide

| Purpose | Chart Type | When to Use | Example |
|---------|-----------|-----------|---------|
| **Comparison** | Bar chart (vertical) | Compare values across categories | Revenue by product line |
| | Bar chart (horizontal) | Long category labels | Revenue by country name |
| | Grouped bar | Compare sub-categories | Revenue by product by quarter |
| | Lollipop chart | Clean alternative to bar | Rankings |
| **Composition** | Stacked bar | Part-to-whole over categories | Revenue mix by region |
| | 100% stacked bar | Proportion comparison | Channel mix % by quarter |
| | Pie chart | Part-to-whole, <=5 slices | Market share (3-4 competitors) |
| | Treemap | Hierarchical composition | Budget allocation by dept+team |
| **Distribution** | Histogram | Shape of numeric distribution | Customer age distribution |
| | Box plot | Compare distributions across groups | Salary by department |
| | Violin plot | Distribution shape + density | Response time by service tier |
| | Strip/jitter plot | Small datasets, show individual points | Test scores by class |
| **Relationship** | Scatter plot | Two numeric variables | Price vs demand |
| | Bubble chart | Three variables (x, y, size) | Revenue vs growth vs market size |
| | Connected scatter | Change over time for 2 variables | Inflation vs unemployment by year |
| **Trend** | Line chart | Change over time | Monthly revenue, daily users |
| | Area chart | Volume over time (stacked = composition) | Stacked revenue by channel |
| | Sparkline | Compact trend in a table/dashboard | Inline KPI trend |
| **Geographic** | Choropleth | Values by region | Sales by state |
| | Bubble map | Point data with magnitude | Store locations sized by revenue |

---

### Design Principles

**Data-Ink Ratio (Tufte):**
- Maximize the share of ink used to display data.
- Remove: gridlines (or lighten), borders, background colors, 3D effects, decorative elements.
- Keep: axis labels, data labels (when needed), title, legend (if >1 series).

**Avoid Chartjunk:**
- No 3D charts (distorts perception).
- No excessive gridlines.
- No decorative images or icons within chart area.
- No gradient fills on data elements.

**Color Encoding:**
- Use consistent color for same category across all charts.
- Sequential palette: light-to-dark for ordered data (revenue levels).
- Diverging palette: two-hue for data with meaningful midpoint (profit/loss).
- Categorical palette: distinct hues for unordered groups (max 8-10 colors).

**Accessible Color Palettes:**
- Avoid red/green only — 8% of men are red-green colorblind.
- Use: blue/orange, blue/red, or add pattern/shape differentiation.
- Test with colorblind simulator.
- Ensure sufficient contrast (WCAG AA: 4.5:1 for text, 3:1 for graphics).

**Axis Scaling:**
- Bar charts: ALWAYS start y-axis at 0 (truncated bars mislead).
- Line charts: Starting above 0 is acceptable when showing trend detail.
- Use consistent scales when comparing charts side by side.
- Log scale: Use when data spans multiple orders of magnitude.

---

### Annotation Best Practices

**Titles that state the insight:**
- Bad: "Monthly Revenue"
- Good: "Revenue grew 23% in Q3, driven by enterprise segment"
- The title is the first thing people read — make it the takeaway.

**Callouts for key data points:**
- Annotate outliers, inflection points, targets, and events.
- Format: Short text label with line pointing to data point.
- Example: "Product launch (Mar 15)" on the timeline.

**Context lines:**
- Add horizontal reference lines for: targets, benchmarks, averages, prior period.
- Label them clearly. Use dashed style to distinguish from data.

**Legend placement:**
- Prefer direct labels on data series (eliminates legend lookup).
- If legend required, place it close to data (not in a distant corner).

---

### Dashboard Layout Principles

**Inverted Pyramid:**
```
[KPI Cards — 5-7 key metrics with RAG status]    <- Top: most important
[Trend Charts — time series of key metrics]       <- Middle: context
[Detail Tables — supporting data, drill-down]     <- Bottom: detail
```

**F-Pattern Reading:**
- Users scan left-to-right, then down. Most important metric = top-left.
- Group related metrics together.
- Use consistent card sizing for visual harmony.

**5-Second Rule:**
- The key message should be visible within 5 seconds of looking at the dashboard.
- If someone cannot tell "what's going well and what's not" in 5 seconds, redesign.

**Filter Placement:**
- Global filters (date range, segment): top of dashboard or left sidebar.
- Chart-specific filters: within the chart card.
- Default to the most common view (e.g., last 30 days, all segments).

---

### Visualization Libraries (Python)

| Library | Best For | Interactivity | Learning Curve |
|---------|---------|---------------|---------------|
| matplotlib | Publication-quality static charts | None | Medium |
| seaborn | Statistical visualization | None | Low |
| plotly | Interactive web charts | Full | Medium |
| altair | Declarative grammar of graphics | Moderate | Low-Medium |
| bokeh | Interactive dashboards | Full | Medium-High |

### Common Visualization Mistakes

| Mistake | Why It Is Bad | Fix |
|---------|-------------|-----|
| Dual y-axis | Readers misjudge relationship between series | Use two charts or normalize to common scale |
| 3D charts | Distorts values, occludes data | Use 2D — always |
| Rainbow color scales | Not perceptually uniform, colorblind-unfriendly | Use sequential or diverging palette |
| Pie chart with >5 slices | Hard to compare small slices | Use bar chart |
| Truncated bar chart y-axis | Makes small differences look huge | Start y-axis at 0 |
| Too many series on one chart | Cluttered, unreadable | Highlight 2-3 key series, gray out rest |
| No units on axes | Reader cannot interpret values | Always label axes with units |
| Inconsistent time intervals | Misleading trends | Ensure uniform x-axis spacing |
""",
)

data_validation_qa = Skill(
    name="data_validation_qa",
    description="Data analysis QA methodology with pre-analysis validation, accuracy checks, bias detection, reproducibility requirements, and peer review templates.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.FIN],
    knowledge_summary="Pre-analysis validation (source verification, freshness, completeness), methodology review checklist, accuracy checks (reconcile to source, cross-validate, sanity check), bias detection, reproducibility requirements, and common QA catches.",
    knowledge="""
## Data Analysis QA Methodology

### Pre-Analysis Validation

**Before starting ANY analysis, validate the data:**

| Check | Question | How to Verify | Red Flag |
|-------|---------|--------------|----------|
| Source verification | Where did this data come from? | Confirm source system, extraction method, who provided it | "I think it's from..." (no clear provenance) |
| Freshness | Is the data current enough? | Check max timestamp, compare to expected | Data is >24 hrs old for real-time analysis |
| Completeness | Is all expected data present? | Row count vs source count, date range check, entity count | Missing recent dates, lower count than expected |
| Known issues | Are there known data quality problems? | Check data team's issue tracker, ask data owner | Undocumented issues discovered mid-analysis |
| Schema stability | Has the source schema changed recently? | Compare column list to documentation, check for new NULLs | New NULL columns, changed data types |

**Document findings:** Before analysis begins, write 3-5 bullet points on data provenance and any caveats.

---

### Methodology Review Checklist

Before finalizing any analysis, verify:

- [ ] **Appropriate test/method selected:** Does the statistical test match the data type and question?
- [ ] **Assumptions validated:** Normality, independence, homoscedasticity — tested, not assumed.
- [ ] **Sample size sufficient:** Power analysis conducted; results are not from tiny samples.
- [ ] **Time period appropriate:** Not cherry-picked; covers complete cycles (full months, full quarters).
- [ ] **Segmentation logic correct:** Groups are mutually exclusive and collectively exhaustive.
- [ ] **Outlier treatment documented:** Decision to include/exclude outliers is explicit and justified.
- [ ] **Null handling documented:** How NULLs were treated (excluded, imputed, default value) is explicit.
- [ ] **Metric definitions match business understanding:** "Active user" means the same thing to analyst and stakeholder.
- [ ] **Comparison baseline appropriate:** Comparing to right period (YoY vs MoM), right benchmark.
- [ ] **Causation claims justified:** If claiming X causes Y, is there experimental evidence or just correlation?

---

### Accuracy Checks

**1. Reconcile to Source Totals:**
```
Source system total revenue (Jan): $1,234,567
Analysis dataset total revenue (Jan): $1,234,567
Match: YES / NO (if NO, investigate difference)
```

**2. Cross-Validate with Independent Source:**
- Compare key metrics against another system (e.g., CRM revenue vs accounting revenue).
- Acceptable variance: <1% for financial data, <5% for behavioral data.
- If variance exceeds threshold, document why before proceeding.

**3. Sanity Check Against Benchmarks:**
| Metric | Your Finding | Industry Benchmark | Reasonable? |
|--------|-------------|-------------------|-------------|
| Conversion rate | 15% | 2-5% typical | Suspicious — investigate |
| Avg order value | $47 | $40-60 typical | Reasonable |
| Churn rate | 0.1% monthly | 3-7% typical | Suspicious — too good |

**4. Unit Testing for Calculations:**
```python
# Test your calculation on a known small dataset
test_data = pd.DataFrame({'amount': [100, 200, 300]})
assert calculate_growth(test_data) == expected_result
```

---

### Bias Detection

| Bias Type | Description | Detection Method | Mitigation |
|----------|-----------|-----------------|-----------|
| **Selection bias** | Sample not representative of population | Compare sample demographics to known population | Stratified sampling, weighting |
| **Survivorship bias** | Only analyzing survivors | Check: are churned/failed/dropped entities included? | Include all entities, note when exclusion is intentional |
| **Confirmation bias** | Looking for data that supports hypothesis | Pre-register hypothesis, review by someone without the hypothesis | Blind analysis, devil's advocate review |
| **Measurement bias** | Systematic error in data collection | Compare collection methods, look for instrument effects | Calibrate instruments, validate survey questions |
| **Time period bias** | Choosing favorable time window | Check: does conclusion hold for other time periods? | Test on multiple time periods, report sensitivity |
| **Aggregation bias** | Aggregate hides subgroup patterns | Check: do subgroups show same pattern? (Simpson's Paradox) | Always check key segments separately |
| **Anchoring bias** | Over-relying on first data point seen | Start with distribution, not single numbers | Present ranges and distributions first |

---

### Reproducibility Requirements

**Every analysis must be reproducible by another analyst:**

1. **Document all transformations:** No ad-hoc Excel manipulations. Every filter, join, calculation in code or documented steps.
2. **Version control for queries/code:** All SQL, Python, R scripts in version control with commit messages.
3. **Parameterize date ranges:** Never hardcode dates. Use variables/parameters that can be updated.
4. **Seed random processes:** If using sampling or ML: set random seed and document it.
5. **Document environment:** Python version, package versions, database connection, data extraction timestamp.
6. **Include raw data snapshot or extraction query:** Another analyst should be able to get the same starting dataset.

**Reproducibility test:** Hand your analysis to a colleague. Can they get the same results within 1 hour without asking you questions?

---

### Peer Review Template

```
ANALYSIS PEER REVIEW
=====================
Analysis Title: [Title]
Analyst: [Name]
Reviewer: [Name]
Review Date: [YYYY-MM-DD]

DATA SOURCING                               [PASS / FAIL / N/A]
- Source documented and verified?            [ ]
- Data freshness appropriate?               [ ]
- Known issues documented?                  [ ]

METHODOLOGY                                 [PASS / FAIL / N/A]
- Appropriate method for question?          [ ]
- Assumptions checked?                      [ ]
- Sample size adequate?                     [ ]

CALCULATIONS                                [PASS / FAIL / N/A]
- Spot-checked 3 calculations?             [ ]
- Totals reconcile to source?             [ ]
- Edge cases handled?                      [ ]

CONCLUSIONS                                 [PASS / FAIL / N/A]
- Supported by data shown?                 [ ]
- Alternative explanations considered?     [ ]
- Limitations stated?                      [ ]

PRESENTATION                                [PASS / FAIL / N/A]
- Charts clear and correctly scaled?       [ ]
- Numbers properly formatted?              [ ]
- Takeaway obvious to audience?            [ ]

OVERALL: [APPROVED / REVISIONS NEEDED]
Comments: [Free text]
```

---

### Common QA Catches

| Issue | How to Catch | Example |
|-------|-------------|---------|
| **Off-by-one in date ranges** | Check: `BETWEEN '2024-01-01' AND '2024-01-31'` includes both endpoints | Missing Jan 31 data because query used `< '2024-01-31'` instead of `<= '2024-01-31'` |
| **Timezone mismatches** | Compare timestamps across sources for same event | Event at 11pm EST counted in wrong day when converted to UTC |
| **Null handling inconsistency** | Check: do aggregate functions exclude NULLs? | AVG ignores NULLs but COUNT(*) includes them — denominator mismatch |
| **Aggregation level mismatch** | Check: are you comparing apples to apples? | Comparing daily metric to monthly metric without proper aggregation |
| **Duplicate counting** | Check: COUNT vs COUNT DISTINCT | Counting 1000 orders but only 800 unique orders due to line items |
| **Currency/unit mismatch** | Check: are all values in same currency/unit? | Mixing USD and EUR without conversion |
| **Historical data changes** | Check: has source data been restated/backfilled? | Revenue numbers changed because finance did a restatement |
| **Filter leakage** | Check: do filters apply to all parts of the query? | WHERE clause in main query but not in subquery |
""",
)

dashboard_building = Skill(
    name="dashboard_building",
    description="Interactive dashboard design with layout principles, KPI card design, interactivity patterns, performance optimization, and stakeholder-specific views.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.EXEC, AgentID.MKT],
    knowledge_summary="Dashboard types (executive, operational, analytical, strategic), layout principles (F-pattern, most important top-left), KPI card design, interactivity patterns (drill-down, cross-filter), performance optimization, and refresh cadence by metric type.",
    knowledge="""
## Dashboard Design & Construction Guide

### Dashboard Types

| Type | Purpose | Audience | Metrics | Refresh |
|------|---------|---------|---------|---------|
| **Executive** | KPI-focused decision support | C-suite, VPs | 5-7 top-line metrics | Daily |
| **Operational** | Real-time monitoring and alerting | Ops teams, support | System health, queues, SLAs | Real-time to hourly |
| **Analytical** | Exploratory data investigation | Analysts, PMs | Many metrics, heavy filtering | On-demand |
| **Strategic** | Long-term trend and goal tracking | Board, leadership | Strategic KPIs, OKRs | Weekly to monthly |

---

### Layout Principles

**F-Pattern Reading:**
```
+--[KPI 1]--+--[KPI 2]--+--[KPI 3]--+--[KPI 4]--+
|                                                   |  <- Most important row
+--[Trend Chart 1]-------+--[Trend Chart 2]--------+
|                         |                          |  <- Context row
+--[Detail Table]------------------------------------+
|                                                    |  <- Detail row
+----------------------------------------------------+
```

- Most important metric: top-left position.
- Related metrics grouped together (e.g., all revenue metrics in one section).
- Use consistent card sizing for visual rhythm.
- White space between sections aids scanning.

**Grid System:**
- Use 12-column grid for responsive layouts.
- KPI cards: 3 columns each (4 per row) or 2 columns (6 per row).
- Charts: 6 columns (2 per row) or 12 columns (full width for key charts).
- Tables: always full width (12 columns).

---

### KPI Card Design

```
+---------------------------------------+
| Revenue                    [trend icon]|
|                                        |
|     $1.24M                             |
|     vs $1.10M last month  (+12.7%)     |
|                                        |
| [sparkline ~~~~~~~~~/]     [RAG dot]   |
+---------------------------------------+
```

**Required elements:**
1. **Metric name:** Clear, concise label.
2. **Current value:** Large, prominent number with proper formatting ($, %, commas).
3. **Comparison:** vs target, vs prior period, vs benchmark.
4. **Trend indicator:** Up/down/flat arrow or sparkline.
5. **RAG status:** Color dot or border indicating health.

**Formatting rules:**
- Numbers: Use K, M, B suffixes for large numbers ($1.2M not $1,234,567).
- Percentages: One decimal place (12.3% not 12.345%).
- Currency: Include symbol, proper locale formatting.
- Dates: Consistent format throughout dashboard.

---

### Interactivity Patterns

**1. Drill-Down:**
- Click KPI card -> see breakdown chart.
- Click chart bar -> see detail table.
- Example: Revenue card -> Revenue by product chart -> Product transaction table.
- Breadcrumb navigation to track drill-down path.

**2. Cross-Filtering:**
- Clicking a segment in one chart filters all other charts.
- Example: Click "Enterprise" in segment chart -> all metrics filter to enterprise.
- Visual indicator of active filter (highlighted selection, filter badge).
- Clear all filters button always visible.

**3. Time Range Selection:**
- Preset buttons: Today, 7D, 30D, 90D, YTD, Custom.
- Date picker for custom ranges.
- Comparison toggle: vs prior period, vs same period last year.
- Default: last 30 days (most common use case).

**4. Export:**
- Export chart as image (PNG/SVG).
- Export underlying data as CSV.
- Export full dashboard as PDF.
- Schedule automated email delivery.

---

### Performance Optimization

| Technique | When to Apply | Impact |
|----------|-------------|--------|
| Pre-aggregate data | Always for dashboards with >1M rows | 10-100x faster queries |
| Materialized views | Metrics that do not need real-time accuracy | Eliminates repeated computation |
| Cache static metrics | Metrics that refresh daily or less | Reduces database load |
| Progressive loading | Dashboard with >10 components | Perceived performance improvement |
| Lazy loading | Below-the-fold charts and tables | Faster initial render |
| Query pagination | Tables with >100 rows | Prevents browser memory issues |
| Incremental refresh | Only update data since last refresh | 5-50x faster than full refresh |

**Query optimization for dashboards:**
- One query per card (not one mega-query).
- Use date partitioning and partition pruning.
- Index all filter/group-by columns.
- Avoid DISTINCT and complex JOINs in real-time queries.

---

### HTML/CSS Dashboard Framework

**Responsive grid:**
```css
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 16px;
    padding: 24px;
}
.kpi-card { grid-column: span 3; }      /* 4 per row */
.chart-half { grid-column: span 6; }     /* 2 per row */
.chart-full { grid-column: span 12; }    /* 1 per row */
.table-full { grid-column: span 12; }    /* Full width */

@media (max-width: 768px) {
    .kpi-card { grid-column: span 6; }   /* 2 per row on tablet */
    .chart-half { grid-column: span 12; } /* Full width on tablet */
}
```

**Chart libraries for web dashboards:**
- chart.js: Lightweight, good defaults, responsive.
- plotly.js: Feature-rich, interactive, good for analytical dashboards.
- D3.js: Maximum flexibility, steep learning curve, for custom visualizations.
- Apache ECharts: Rich chart types, good performance with large datasets.

**Auto-refresh pattern:**
```javascript
// Refresh KPIs every 60 seconds, charts every 5 minutes
setInterval(refreshKPIs, 60000);
setInterval(refreshCharts, 300000);
```

---

### Stakeholder-Specific Views

**Executive Dashboard:**
- 5-7 KPI cards with RAG and trend.
- One summary trend chart (revenue or key metric).
- Top 3 risks or action items.
- No filters (curated view, no exploration needed).
- Fits on one screen without scrolling.

**Operational Dashboard:**
- Real-time metrics with auto-refresh.
- Alert indicators (flashing/colored for threshold breaches).
- Queue depths, response times, error rates.
- Filterable by service/team/region.
- Optimized for large monitors in operations centers.

**Analytical Dashboard:**
- Many filter options (date, segment, product, region, etc.).
- Drill-down from every chart.
- Export capability on every component.
- Detail tables with sorting and searching.
- Designed for exploration, not just monitoring.

### Refresh Cadence by Metric Type

| Metric Type | Refresh | Example |
|------------|---------|---------|
| System health | Real-time (1-5 sec) | Uptime, error rate, latency |
| Operational | Every 5-15 min | Queue depth, active tickets, orders processing |
| Business daily | Once daily (overnight) | Revenue, new customers, churn |
| Business weekly | Monday morning | Pipeline, sprint velocity, NPS |
| Strategic | Monthly | MRR, CAC, LTV, market share |
""",
)

data_analysis_workflow = Skill(
    name="data_analysis_workflow",
    description="End-to-end data analysis methodology from request intake through insight delivery, with scoping, frameworks, and communication structures.",
    category="data",
    agent_ids=[AgentID.DATA, AgentID.FIN, AgentID.STRAT],
    knowledge_summary="Analysis request intake template, scoping (metrics, definitions, data sources, effort), analysis frameworks (descriptive, diagnostic, predictive, prescriptive), insight generation with the so-what test, communication structures (SCR), and deliverable formats by audience.",
    knowledge="""
## End-to-End Data Analysis Workflow

### Step 1: Analysis Request Intake

**Intake Template:**
```
ANALYSIS REQUEST
================
Requestor: [Name, Role]
Date: [YYYY-MM-DD]
Priority: [Low / Medium / High / Urgent]

1. BUSINESS QUESTION
   [What question are you trying to answer?]

2. DECISION TO BE INFORMED
   [What will you do differently based on the answer?]

3. AUDIENCE
   [Who will see the results? What is their data literacy?]

4. DEADLINE
   [When is this needed? Is there a meeting/decision date driving it?]

5. AVAILABLE DATA SOURCES
   [What data do you know exists? Any access you can provide?]

6. PREVIOUS ANALYSIS
   [Has this been analyzed before? Where are those results?]

7. SUCCESS CRITERIA
   [How will you know if this analysis is useful?]
```

**Triage rules:**
- Urgent: CEO/board request, revenue-impacting decision, regulatory deadline -> start within 24 hrs.
- High: VP-level request, strategic decision -> start within 3 days.
- Medium: Manager request, operational improvement -> start within 1 week.
- Low: Curiosity-driven, nice-to-have -> backlog, prioritize monthly.

---

### Step 2: Scoping

**Before any data work, agree on scope:**

| Element | Question | Document |
|---------|---------|----------|
| **Metrics** | What exactly are we measuring? | Metric name, formula, unit |
| **Definitions** | What counts as [X]? | "Active user = logged in within 30 days" |
| **Data sources** | Where does the data come from? | System name, table, extraction method |
| **Time period** | What date range? | Start/end, any exclusions |
| **Segments** | Any breakdowns needed? | By region, product, customer type |
| **Effort estimate** | How long will this take? | Hours/days, with assumptions |

**Effort Estimation Guide:**
| Complexity | Characteristics | Typical Effort |
|-----------|----------------|---------------|
| Quick question | Single query, known data source | 1-4 hours |
| Standard analysis | Multiple queries, some joins, basic viz | 1-3 days |
| Deep dive | New data sources, complex methodology, modeling | 1-2 weeks |
| Research project | Novel question, data collection needed, iteration | 2-4 weeks |

**Scope agreement:** Get written confirmation before starting. Prevents scope creep and rework.

---

### Step 3: Data Collection

**Source Identification:**
1. Primary source: System of record for the metric (e.g., billing system for revenue).
2. Supplementary sources: Context data (CRM for customer attributes, product analytics for usage).
3. External sources: Benchmarks, market data, third-party enrichment.

**Extraction Checklist:**
- [ ] Query documented and version-controlled.
- [ ] Date range parameterized (not hardcoded).
- [ ] Extraction timestamp recorded.
- [ ] Row count logged and sanity-checked against source.
- [ ] Sample records spot-checked for accuracy.

**Transformation Best Practices:**
- Transform in code (SQL/Python), never manually in spreadsheets.
- Document every transformation step.
- Keep raw data separate from transformed data.
- Validate row counts after each transformation step (no silent drops).

---

### Step 4: Analysis Framework

**Choose the right depth based on the question:**

| Level | Question | Methods | Example |
|-------|---------|---------|---------|
| **Descriptive** | What happened? | Aggregation, trending, segmentation | "Revenue was $1.2M in Q3, up 15% YoY" |
| **Diagnostic** | Why did it happen? | Drill-down, correlation, root cause analysis | "Growth driven by Enterprise segment (+30%), SMB declined (-5%)" |
| **Predictive** | What will happen? | Forecasting, regression, ML models | "At current trajectory, Q4 revenue will be $1.35M" |
| **Prescriptive** | What should we do? | Optimization, scenario modeling, simulation | "Investing $50K in Enterprise sales would yield $200K additional revenue" |

**Most analyses should go at least to Diagnostic.** Descriptive alone ("here are the numbers") is not analysis — it is reporting.

---

### Step 5: Insight Generation

**The So-What Test:**
Every finding must answer: "So what should we do about it?"

| Finding | So What? | Recommendation |
|---------|---------|---------------|
| "Revenue is up 15%" | Is this good? vs target? sustainable? | "Exceeds target by 5%. Driven by Enterprise. Recommend increasing Enterprise sales investment." |
| "Churn is 5% monthly" | Is this concerning? what's causing it? | "Above industry average (3%). Top reason: product complexity. Recommend onboarding improvement." |
| "Campaign A has 2x ROI of Campaign B" | Should we shift spend? | "Reallocate 30% of Campaign B budget to Campaign A. Expected impact: +$50K revenue." |

**Findings without recommendations are incomplete.** Always pair data with action.

---

### Step 6: Communication Structure

**Situation-Complication-Resolution (SCR):**
1. **Situation:** Context everyone agrees on. "We launched the enterprise product in Q2."
2. **Complication:** The tension or problem. "Enterprise adoption is 40% below target."
3. **Resolution:** Your recommendation. "Analysis shows onboarding complexity is the primary barrier. Recommend simplified onboarding flow."

**Lead with the Answer:**
- Do NOT build suspense. Start with the conclusion.
- Supporting data follows the answer, not precedes it.
- Audience decides how deep to go — give them the answer first.

**Structure:**
```
1. Answer / Recommendation (1-2 sentences)
2. Key supporting evidence (3-5 bullet points)
3. Methodology summary (1 paragraph)
4. Detailed analysis (appendix, for those who want it)
```

---

### Step 7: Deliverable Formats

**Email Summary (3-5 bullet points):**
- For: Quick answers, status updates, FYI communications.
- Format: Subject line = the answer. Body = 3-5 bullets with key data. Attachment = detailed analysis if needed.

**Presentation Deck (5-10 slides):**
```
Slide 1: Title + executive summary (the answer)
Slide 2: Context / background
Slide 3-4: Key findings with visualizations
Slide 5: Root cause analysis
Slide 6-7: Recommendations with expected impact
Slide 8: Next steps and timeline
Slide 9-10: Appendix (methodology, detailed data)
```

**Full Report (detailed methodology):**
```
1. Executive Summary (1 page)
2. Background and Objectives
3. Methodology
4. Data Sources and Limitations
5. Findings
6. Analysis and Discussion
7. Recommendations
8. Appendix: Detailed Tables, Code, Raw Data Reference
```

---

### Analysis Documentation

**Assumptions Log:**
| # | Assumption | Rationale | Impact if Wrong |
|---|-----------|-----------|----------------|
| 1 | Exclude test accounts (email contains "test") | Standard practice | Minor — <0.5% of data |
| 2 | Use list price, not negotiated price | Negotiated price not in dataset | Could overstate revenue by 10-15% |

**Methodology Decisions:**
- Document every fork in the analysis road: "We chose X over Y because Z."
- Include alternatives considered and why they were rejected.

**Data Limitations:**
- What data is missing or incomplete?
- What biases might exist in the data?
- What confidence level do you have in the results?
- What would change the conclusion?

**Sensitivity Analysis:**
- Test: does the conclusion hold if key assumptions change?
- Example: "If churn rate is 4% instead of 5%, payback period changes from 8 to 7 months."
- Report range of outcomes, not just point estimates.
""",
)


# =============================================================================
# Registration
# =============================================================================


def register_operations_data_skills() -> None:
    """Register all professional operations and data skills."""
    all_skills = [
        # Operations (9 skills)
        process_documentation,
        compliance_tracking,
        change_management_request,
        capacity_planning,
        vendor_review_framework,
        status_report_generation,
        operational_runbook,
        operational_risk_assessment,
        process_optimization,
        # Data (7 skills)
        sql_query_writing,
        data_exploration,
        statistical_analysis_methods,
        data_visualization_best_practices,
        data_validation_qa,
        dashboard_building,
        data_analysis_workflow,
    ]

    for skill in all_skills:
        skills_registry.register(skill)


# Auto-register when module is imported
register_operations_data_skills()
