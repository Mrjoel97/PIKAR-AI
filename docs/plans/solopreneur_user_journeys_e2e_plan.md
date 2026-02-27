# Solopreneur User Journeys – End-to-End Implementation Plan

## Executive Summary

This plan ensures all **40 solopreneur user journeys** are fully usable by users and executable by the agent in **auto mode** once the user has provided required information (e.g. desired outcomes). It covers schema changes, journey enrichment, workflow mapping, outcomes collection, and agent behaviour.

---

## 1. Current State

### 1.1 Solopreneur User Journeys (40 total, from `0017_seed_user_journeys.sql`)

| # | Journey Title | Current Description | Current Stages |
|---|---------------|---------------------|----------------|
| 1 | First Client Acquisition | Generic | Start → In Progress → Complete |
| 2 | Automated Invoicing Setup | Generic | Same |
| 3 | Personal Brand Building | Generic | Same |
| 4 | Portfolio Website Launch | Generic | Same |
| 5 | Social Media Content Strategy | Generic | Same |
| 6 | Client Onboarding Automation | Generic | Same |
| 7 | Expense Tracking Setup | Generic | Same |
| 8 | Quarterly Tax Prep | Generic | Same |
| 9 | Service Pricing Strategy | Generic | Same |
| 10 | Virtual Assistant Hiring | Generic | Same |
| 11 | Cold Email Outreach | Generic | Same |
| 12 | LinkedIn Networking | Generic | Same |
| 13 | Google Business Profile Optimization | Generic | Same |
| 14 | Project Management Setup | Generic | Same |
| 15 | Proposal Template Creation | Generic | Same |
| 16 | Contract Template Creation | Generic | Same |
| 17 | Customer Feedback Loop | Generic | Same |
| 18 | Email List Building | Generic | Same |
| 19 | Webinar Funnel Setup | Generic | Same |
| 20 | Online Course Launch | Generic | Same |
| 21 | Affiliate Program Setup | Generic | Same |
| 22 | Podcast Launch | Generic | Same |
| 23 | Blog Content Calendar | Generic | Same |
| 24 | SEO Basic Setup | Generic | Same |
| 25 | Time Blocking Schedule | Generic | Same |
| 26 | Remote Office Setup | Generic | Same |
| 27 | Health Insurance Research | Generic | Same |
| 28 | Liability Insurance Setup | Generic | Same |
| 29 | Bank Account Separation | Generic | Same |
| 30 | Emergency Fund Planning | Generic | Same |
| 31 | Retirement Saving Setup | Generic | Same |
| 32 | Networking Event Calendar | Generic (typo: Caldendar) | Same |
| 33 | Client Gift Strategy | Generic | Same |
| 34 | Review Management | Generic | Same |
| 35 | Upsell Strategy | Generic | Same |
| 36 | Legacy Client Migration | Generic | Same |
| 37 | Productivity Tool Stack | Generic | Same |
| 38 | Data Backup Strategy | Generic | Same |
| 39 | Password Management | Generic | Same |
| 40 | Brand Voice Guide | Generic | Same |

- **Schema:** `user_journeys` has `persona`, `title`, `description`, `stages` (JSONB), `kpis` (JSONB). No link to workflows.
- **Stages:** All use the same placeholder: `[{"name": "Start", "status": "pending"}, {"name": "In Progress", "status": "pending"}, {"name": "Complete", "status": "pending"}]`.
- **KPIs:** Not set in seed (column exists, default `[]`).
- **Flow today:** User clicks “Start as Initiative” → initiative is created with `metadata.source = 'user_journey'` and `metadata.journey_id`. No workflow is started; no outcomes are collected.

### 1.2 What Exists Elsewhere

- **Initiative templates (solopreneur):** 5 rich templates (Podcast Launch, Online Course Launch, Personal Brand Building, Freelance Service Launch, Blog Content Strategy) with phases, steps, `suggested_workflows`, and KPIs.
- **Workflow templates:** 60+ in DB (0009 + 0038), e.g. Content Creation Workflow, Lead Generation Workflow, Email Nurture Sequence, Social Media Calendar, Initiative Framework, etc. Agents can call `start_workflow(user_id, template_name, context)`.
- **Agent workflow tools:** `list_workflow_templates`, `start_workflow`, `approve_workflow_step`, `get_workflow_status`. No journey-specific tool.

---

## 2. Goals

1. **Users can use every solopreneur journey end-to-end:** Each journey has a clear description, meaningful stages (or phase alignment), optional KPIs, and a path to execution (create initiative → optional outcomes → run workflow).
2. **Agents can execute journeys in auto mode:** After the user has provided required information (e.g. desired outcomes, timeline), the agent can start the journey’s linked workflow and run it in auto mode, only pausing at approval gates (or auto-approving when configured).

---

## 3. Architecture (Target)

```
User selects journey → [Optional: Outcomes form / first message] → Create initiative (with outcomes in metadata)
       → Agent receives initiative + outcomes
       → Agent calls start_workflow(template from journey, context = { initiative_id, desired_outcomes })
       → Workflow engine runs steps (tools); at approval gates → agent approves or asks user
       → Initiative phase/progress updated as workflow advances (optional sync)
```

- **user_journeys** row: has `primary_workflow_template_name` (or `suggested_workflows[]`) and optional `required_outcomes_schema` (e.g. “desired_outcomes”, “timeline”).
- **Initiative** (from journey): `metadata.journey_id`, `metadata.desired_outcomes`, optionally `metadata.primary_workflow_template`.
- **Agent:** Uses `start_workflow` with template from journey/initiative and context; in auto mode, calls `approve_workflow_step` when status is `waiting_approval` (or follows user preference).

---

## 4. Implementation Plan

### Phase A: Schema and Data Model

| Task | Description | Deliverable |
|------|-------------|-------------|
| A1 | Add to `user_journeys`: `primary_workflow_template_name` (TEXT), `suggested_workflows` (JSONB array of names), optional `outcomes_prompt` (TEXT) describing what to ask the user. | Migration `0040_user_journeys_workflow_and_outcomes.sql` |
| A2 | Keep `stages` and `kpis`; use them for display and for agent context. Optionally add `category` (e.g. marketing, operations) for filtering. | Same migration if needed |

### Phase B: Enrich Solopreneur Journeys (40)

| Task | Description | Deliverable |
|------|-------------|-------------|
| B1 | For each of the 40 solopreneur journeys: (1) Write a short, specific description. (2) Replace generic stages with either 5-phase-aligned stages (ideation → validation → prototype → build → scale) or 3–5 custom stages with real step names. (3) Add 2–4 KPIs per journey where relevant. (4) Set `primary_workflow_template_name` to the best-matching workflow from existing 60+ (see mapping table below). (5) Set `suggested_workflows` (array) and `outcomes_prompt` (e.g. “What does success look like? Timeline?”). | Migration `0041_enrich_solopreneur_journeys.sql` (or split into 2–3 migrations if large) |
| B2 | Fix typo: “Networking Event Caldendar” → “Networking Event Calendar”. | Same migration |

**Suggested journey → workflow mapping (solopreneur)**

- First Client Acquisition → **Lead Generation Workflow** or **Outbound Prospecting**
- Automated Invoicing Setup → **Vendor Onboarding** or new “Invoicing Setup” workflow
- Personal Brand Building → **Content Creation Workflow** / **Social Media Campaign** (or Initiative Framework with Personal Brand template)
- Portfolio Website Launch → **Content Creation Workflow** + **Product Launch Campaign**
- Social Media Content Strategy → **Social Media Campaign** / **Content Creation Workflow**
- Client Onboarding Automation → **Vendor Onboarding**-style or custom “Client Onboarding”
- Expense Tracking Setup → custom or **Pipeline Review**-style (tracking)
- Quarterly Tax Prep → custom “Tax Prep” or use tasks/reports
- Service Pricing Strategy → **Strategic Planning Cycle** or **Competitor Analysis**
- Virtual Assistant Hiring → **Sales Training**-style or HR workflow
- Cold Email Outreach → **Outbound Prospecting** / **Email Nurture Sequence**
- LinkedIn Networking → **Social Media Calendar** / **Influencer Outreach**
- Google Business Profile Optimization → **SEO Optimization Audit**
- Project Management Setup → **Agile Workflow Setup** (if exists) or **Strategic Planning Cycle**
- Proposal Template Creation → **Content Creation Workflow**
- Contract Template Creation → **Content Creation Workflow** / **Deal Closing**
- Customer Feedback Loop → **Win/Loss Analysis**-style or **NPS Survey**
- Email List Building → **Email Nurture Sequence** / **Lead Generation Workflow**
- Webinar Funnel Setup → **Webinar Hosting** (0009)
- Online Course Launch → **Initiative Framework** or **Content Creation Workflow** + **Product Launch Campaign**
- Affiliate Program Setup → **Vendor Onboarding**-style or custom
- Podcast Launch → **Initiative Framework** or **Content Creation Workflow**
- Blog Content Calendar → **Content Creation Workflow** / **Social Media Calendar**
- SEO Basic Setup → **SEO Optimization Audit**
- Time Blocking Schedule → custom (tasks/calendar)
- Remote Office Setup → **Office Move/Expansion** or custom
- Health / Liability Insurance → **Vendor Onboarding** or custom
- Bank Account Separation / Emergency Fund / Retirement → custom or **Strategic Planning Cycle**
- Networking Event Calendar → **Social Media Calendar** / **Content Creation**
- Client Gift / Review Management / Upsell / Legacy Client Migration → **Account Renewal**, **Customer Success**, or custom
- Productivity Tool Stack / Data Backup / Password Management → **IT Asset Provisioning**-style or custom
- Brand Voice Guide → **Content Creation Workflow**

Where no good match exists, use **Initiative Framework** as default so the 5-phase framework drives the journey.

### Phase C: Outcomes Collection (User-Facing)

| Task | Description | Deliverable |
|------|-------------|-------------|
| C1 | **Option A (simple):** On “Start as Initiative” from a journey, redirect to initiative detail with a query flag (e.g. `?promptOutcomes=1`). Initiative detail page shows a short “What does success look like?” text area and “Timeline” (optional). On submit, patch initiative `metadata.desired_outcomes` and `metadata.timeline`, then optionally show “Start execution” or “Discuss with Agent”. | Frontend: `initiatives/[id]/page.tsx` + journey start flow |
| C2 | **Option B (agent-led):** No form. When user clicks “Start as Initiative”, create initiative and redirect to workspace with initial prompt: “I started the [Journey Title] journey. My initiative ID is X. Please ask me what outcomes I want and then run the journey workflow.” Agent then asks for outcomes, writes them to initiative metadata (via `update_initiative`), then calls `start_journey_workflow` or `start_workflow`. | Same as C1 but outcomes collected in chat |
| C3 | Persist outcomes in initiative: `metadata.desired_outcomes` (string or structured), `metadata.timeline`, `metadata.primary_workflow_template` (from journey). | Backend/frontend already support metadata |

### Phase D: Agent Side – Journey-Aware Execution

| Task | Description | Deliverable |
|------|-------------|-------------|
| D1 | Add agent tool **`start_journey_workflow`** (or extend `start_workflow` usage): inputs `initiative_id`, optional `desired_outcomes` override. Implementation: (1) Load initiative; (2) from `metadata.journey_id` load `user_journeys` row; (3) read `primary_workflow_template_name`; (4) call existing `start_workflow(user_id, primary_workflow_template_name, context)` with `context = { initiative_id, desired_outcomes: initiative.metadata.desired_outcomes, ... }`. | New tool in `app/agents/strategic/tools.py` or `app/agents/tools/workflows.py`; register in registry |
| D2 | Agent instructions (Executive + Strategic): When user has created an initiative from a user journey and has provided desired outcomes (or they are already in metadata), the agent should offer to “run the journey in auto mode”. In auto mode: call `start_journey_workflow(initiative_id)`; then poll `get_workflow_status(execution_id)`; when status is `waiting_approval`, call `approve_workflow_step(execution_id, feedback)` to proceed (or ask user once). Document in system prompt. | `app/agent.py`, `app/agents/strategic/agent.py`, `app/services/user_agent_factory.py` |
| D3 | Ensure workflow execution context includes `initiative_id` and `desired_outcomes` so step tools (or backend) can use them. | `app/workflows/engine.py` / `start_workflow` context |

### Phase E: Frontend – Journey to Initiative to Execution

| Task | Description | Deliverable |
|------|-------------|-------------|
| E1 | Journeys page: For solopreneur (and later others), show enriched description, stages, and KPIs from DB. “Start as Initiative” already creates initiative; optionally open workspace with pre-filled prompt that includes journey title and initiative id and asks agent to collect outcomes and run. | `frontend/src/app/dashboard/journeys/page.tsx` |
| E2 | Initiative detail (from journey): Show “Desired outcomes” and “Timeline” from metadata if present; allow edit. Button “Run journey workflow” or “Discuss with Agent” that goes to workspace with context so agent can start the workflow. | `frontend/src/app/dashboard/initiatives/[id]/page.tsx` |
| E3 | Optional: Outcomes modal on “Start as Initiative” (before creating initiative) with 2–3 fields (e.g. “What does success look like?”, “Target date?”). On submit, create initiative with metadata and redirect to initiative detail or workspace. | Modal on journeys page or intermediate page |

### Phase F: Workflow Execution and Approval Gates

| Task | Description | Deliverable |
|------|-------------|-------------|
| F1 | Ensure workflow step execution (edge function or backend) receives and passes `initiative_id` / `desired_outcomes` in context so tools can use them. | Supabase `execute-workflow` + backend `execute-step` |
| F2 | In auto mode, agent must be able to call `approve_workflow_step` when status is `waiting_approval`. No frontend change required if agent has the tool and instructions. | Already have tool; add instruction to auto-approve or ask once per gate |

### Phase G: Verification and Documentation

| Task | Description | Deliverable |
|------|-------------|-------------|
| G1 | Manual test: Pick 3–5 solopreneur journeys (e.g. First Client Acquisition, Podcast Launch, Cold Email Outreach). Start as initiative → provide outcomes → agent starts workflow → workflow runs to first approval gate; approve → continue. | Test script or checklist |
| G2 | Document for users: “How to use User Journeys” (start initiative, set outcomes, discuss with agent, auto-run). | Short doc in `docs/` or in-app help |

---

## 5. Suggested Implementation Order

1. **Phase A** – Migration for `user_journeys` columns.
2. **Phase B** – Enrich all 40 solopreneur journeys (descriptions, stages, KPIs, workflow mapping).
3. **Phase D1** – Implement `start_journey_workflow` (or equivalent) and wire to initiative + journey.
4. **Phase D2** – Agent instructions for “run journey in auto mode” and approval behaviour.
5. **Phase C** – Outcomes collection (Option B first: agent-led in chat; then Option A if you want a form).
6. **Phase E** – Frontend tweaks (journey card display, initiative metadata display, “Discuss with Agent” / “Run workflow”).
7. **Phase F** – Context passing in workflow execution.
8. **Phase G** – Tests and docs.

---

## 6. Out of Scope (Later)

- Other personas (startup, SME, enterprise): same pattern can be applied in a follow-up.
- New workflow templates for journeys that don’t map well (e.g. “Quarterly Tax Prep”) can be added incrementally.
- Full bi-directional sync between workflow step completion and initiative phase progress (optional enhancement).

---

## 7. File Checklist

| Area | Files to touch |
|------|----------------|
| Schema | `supabase/migrations/0040_*.sql`, `0041_*.sql` |
| Journey → workflow | Migration 0041 (data) |
| Agent tools | `app/agents/strategic/tools.py` or `app/agents/tools/workflows.py`, `app/agents/tools/registry.py` |
| Agent instructions | `app/agent.py`, `app/agents/strategic/agent.py`, `app/services/user_agent_factory.py` |
| Workflow context | `app/workflows/engine.py`, `app/routers/workflows.py` (if needed) |
| Frontend – journeys | `frontend/src/app/dashboard/journeys/page.tsx` |
| Frontend – initiative | `frontend/src/app/dashboard/initiatives/[id]/page.tsx` |
| Optional outcomes modal | New component or inline in journeys page |

This plan makes every solopreneur journey end-to-end implementable and allows the agent to execute them in auto mode once the user has provided the required initiative outcomes.
