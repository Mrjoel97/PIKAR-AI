# GTM Production Operating Plan

Date: 2026-03-12
Status: Proposed
Companion to: `.planning/ROADMAP.md`

## 1. Executive Summary

Pikar AI is already a real product with a meaningful core loop:

1. A user completes onboarding and receives a persona-aware workspace.
2. The user works through chat, initiatives, workflows, and widgets instead of a plain chatbot.
3. Outputs are stored in the workspace, vault, reports, and related operating surfaces.

The current product is strongest as an AI operating system for founder-led execution. It is already capable of serving real users in the solopreneur and startup segments. It is only partially ready for SME use and is not yet enterprise-ready.

The main gap is not lack of features. The main gap is trust:

- schema drift
- inconsistent auth and configuration flows
- degraded or simulated execution paths
- incomplete deployment automation
- weak test and release gates
- messaging that is broader than the product proof

The right operating strategy is:

- Sell now to solopreneurs and startups.
- Pilot SMEs selectively with hands-on onboarding.
- Defer broad enterprise selling until governance, deployment, and security hardening are complete.

## 2. Product Reality by Area

### What is already strong

- Workspace and chat act like an operator console rather than a generic assistant.
- Initiatives and journeys provide a useful planning-to-execution bridge.
- Workflow templates, runs, approvals, and monitoring create real operational leverage.
- Vault, widgets, and content bundles make outputs reusable instead of disposable.
- Persona policies are meaningful in backend orchestration even if frontend differentiation is still light.
- Tooling depth is real across Supabase, Google, Stripe, SendGrid, HubSpot, media generation, and social flows.

### What is partially implemented or fragile

- Public lead capture and marketing-page conversion paths are inconsistent with the stronger backend CRM/form stack.
- Workflow generation, execution, and some department flows still include degraded or fallback behavior.
- Scheduled reports, analytics, and some organizational views are not fully hardened.
- Frontend and backend contract patterns are mixed: some paths use the API cleanly, others fall back to direct Supabase access or browser-local persistence.
- Deployment maturity is backend-heavy; frontend and Supabase rollout automation are not equally mature.

### Dead, stale, or drift-heavy areas

- The deprecated Supabase compatibility layer still carries live usage.
- Docs are stale in several places, including frontend setup and some testing guidance.
- Some schema definitions live outside the canonical Supabase migration chain.
- A few UI and storage paths still reference legacy naming or older bucket/table assumptions.

## 3. Persona Fit and Monetizable Value

### Solopreneur

Current value:

- turn a brain dump into an initiative
- get a recommended plan from chat
- run lightweight workflows
- generate assets, landing pages, or content support
- keep everything in one workspace

Current fit: High

Why they will buy:

- faster execution with less overhead
- one interface for planning, doing, and tracking
- strong perceived leverage even before team collaboration is mature

What must improve next:

- simpler setup
- better first-run guidance
- fewer integration decisions
- clearer "do this for me" defaults

### Startup

Current value:

- move from idea to campaign or initiative quickly
- use workflows for repeatable execution
- coordinate launches, approvals, and artifacts
- keep strategic and operational work in one system

Current fit: High

Why they will buy:

- founder leverage
- marketing and operations acceleration
- ability to standardize execution before hiring large teams

What must improve next:

- team collaboration
- cleaner CRM and reporting loops
- better reliability for workflow and initiative state

### SME

Current value:

- structured initiatives
- early approvals and reporting surfaces
- persona-aware operating posture
- reusable workflow templates for departments

Current fit: Medium

Why they may buy:

- desire for lightweight operating discipline without enterprise software overhead

What blocks broader adoption:

- limited confidence in scheduled reporting and ops-grade reliability
- inconsistent backend contracts
- limited role-based and team-grade persistence guarantees

### Enterprise

Current value:

- narrative and policy foundations exist
- approvals, workflows, and reporting direction are visible
- multi-domain orchestration concept is compelling

Current fit: Low

Why they will not broadly buy yet:

- governance not hardened enough
- deployment and auth assumptions are still too fragile
- auditability, SSO, RBAC, admin control, and compliance posture are not ready

## 4. Recommended Market Sequence

### Wave 1: Sell aggressively

- Solopreneurs
- Founder-led startups

Positioning:

"Your AI chief of staff for turning strategy into execution."

Primary promise:

- capture ideas
- convert them into initiatives
- run repeatable workflows
- keep execution and outputs in one operating workspace

### Wave 2: Sell selectively

- SMEs with operational pain and a clear internal champion

Positioning:

"A lightweight operating system for repeatable growth and team execution."

Condition for scale:

- reporting, approvals, and collaboration flows must be trustworthy

### Wave 3: Defer until hardened

- Enterprise accounts

Positioning later:

"Governed AI operations infrastructure for multi-team execution."

Entry requirement:

- governance, security, deployment, and procurement readiness

## 5. Phased Operating Plan

| Phase | Goal | Primary Owner | Why It Matters | Persona Impact | Exit Gate |
|---|---|---|---|---|---|
| 1. Product Truth Foundation | Eliminate trust-breaking behavior across schema, auth, and workflow execution | Platform + Backend | No GTM motion survives if outputs can be wrong or environments drift | Helps every persona; critical for startup and SME retention | Canonical schema, no simulated completions in production, auth/CORS aligned, release gates defined |
| 2. Activation and First Value | Reduce time-to-value from signup to first meaningful win | Product + Frontend + Growth | Solopreneurs and founders need fast payoff, not setup fatigue | Strongest for solopreneur and startup | New user reaches first initiative/workflow outcome in one session |
| 3. Founder Operating System | Package the strongest loop as the core commercial product | Product Marketing + Product + Engineering | The product already wins here; this is the clearest revenue path | Solopreneur and startup | Clear plan, pricing, messaging, onboarding path, and proof points |
| 4. Team Execution Expansion | Add collaboration, reporting, and role-aware operating flows | Product + Backend + Frontend | Moves product from founder tool to team system | Startup and SME | Shared workspaces, stable reporting, team-safe persistence, approval reliability |
| 5. SME Readiness | Build packaged departmental value and repeatability | Product Ops + CS + Engineering | SMEs need solutions, not a toolbox | SME | Department templates, scheduled reporting, role-aware workflow packs, customer success playbook |
| 6. Enterprise Hardening | Add governance and deployment maturity required for large accounts | Security + Platform + Product | Enterprise deals are blocked by trust and admin controls, not UI breadth | Enterprise | SSO/RBAC roadmap, auditability, secure secret handling, documented deployment model |

## 6. Workstream Breakdown

### Phase 1: Product Truth Foundation

Core work:

- make Supabase migrations the single source of truth
- remove or gate all degraded execution paths in production
- align frontend headers, backend auth, and CORS behavior
- remove service-role fallbacks and risky user-id assumptions
- harden secrets, encryption, and OAuth state handling
- add frontend build, backend tests, migration checks, and Edge Function deployment to one release path

Why it matters:

This phase converts the app from "feature-rich but risky" into "credible enough to scale."

### Phase 2: Activation and First Value

Core work:

- compress onboarding into a guided "first win" path
- provide persona-specific starter packs
- preconfigure demo-safe templates and sample data
- create a single success path: chat -> initiative -> workflow -> output
- reduce configuration friction for key integrations

Why it matters:

This phase improves conversion and trial success more than adding another feature area.

### Phase 3: Founder Operating System

Core work:

- define the default founder dashboard and workspace flow
- package workflows for launch, research, growth, content, and follow-up
- build a cleaner landing-page-to-lead-to-initiative story
- align messaging to proven capabilities instead of aspirational breadth
- establish pricing and proof metrics around time saved and outputs shipped

Why it matters:

This is the fastest path from product depth to revenue.

### Phase 4: Team Execution Expansion

Core work:

- improve shared state and persistence across sessions and devices
- stabilize approvals, reports, and status surfaces
- add better role-aware views for founders, operators, and contributors
- tighten initiative and workflow collaboration patterns

Why it matters:

This turns Pikar AI from a single-operator tool into a team operating system.

### Phase 5: SME Readiness

Core work:

- release departmental packs for marketing, operations, finance, and support
- add scheduled reporting and stakeholder-ready summaries
- strengthen SOP and recurring workflow management
- support success-led onboarding and account expansion motions

Why it matters:

SMEs buy repeatable outcomes, not platform flexibility.

### Phase 6: Enterprise Hardening

Core work:

- add SSO, RBAC, audit logs, and admin controls
- document deployment, secret management, and compliance posture
- support enterprise integration expectations with clear contract ownership
- introduce procurement-ready reliability and security materials

Why it matters:

This phase unlocks enterprise trust, which is the true prerequisite for enterprise revenue.

## 7. Persona-Specific Enhancement Backlog

### Solopreneur enhancements

- weekly operating plan autopilot
- launch-in-a-box starter workflows
- simple revenue and content scoreboard
- better calendar, email, and payment visibility
- stronger "suggest next best action" behavior

### Startup enhancements

- experiment and campaign operating board
- investor and board update generation
- CRM attribution and lead follow-up automation
- collaboration across founders and early operators
- launch retrospective and growth learning loops

### SME enhancements

- departmental scorecards
- recurring operational review packs
- approval chains by function
- SOP template bundles
- manager-visible team execution views

### Enterprise enhancements

- SSO and SCIM
- RBAC and environment separation
- audit trails and policy enforcement
- admin reporting and controls
- deployment and data governance options

## 8. KPI Framework

### Product trust KPIs

- percent of core journeys that pass end-to-end in CI
- number of schema mismatches between code and production
- workflow success rate without degraded fallback
- auth or CORS failure rate

### Activation KPIs

- time from signup to first completed initiative
- time from signup to first completed workflow
- percentage of users who complete onboarding and reach workspace
- percentage of new users who receive a usable output on day one

### Retention KPIs

- weekly active workspaces
- workflows run per active account
- initiatives updated per active account
- artifact reuse rate from vault and workspace

### GTM KPIs

- demo-to-trial conversion
- trial-to-paid conversion by persona
- activation rate by persona
- expansion from founder-only to multi-user accounts

## 9. Release Gates

Do not widen the market until these are true:

- backend tests collect and pass for core journeys
- frontend tests pass for auth, onboarding, workspace, initiatives, workflows, and configuration
- frontend build is in CI
- Supabase migrations and Edge Functions deploy through the same controlled path
- production messaging matches verified capability

## 10. Decision Summary

The product should be commercialized in this sequence:

1. Solopreneur
2. Startup
3. SME
4. Enterprise

The next best move is not to add more breadth. It is to tighten truth, activation, and founder-grade packaging around the product loop that already works.
