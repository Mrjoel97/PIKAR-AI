# SME Persona User Journeys – End-to-End Implementation Plan

## Executive summary

This plan ensures all **40 SME persona user journeys** are end-to-end implemented so that:
1. **Users** can discover SME journeys, start them as initiatives, set desired outcomes, and run workflows.
2. **Agents** can execute journey workflows automatically (automode) once they have the required information (initiative outcomes) from the user.

**Current state:** SME journeys exist in `user_journeys` (migration `0017_seed_user_journeys.sql`, lines 86–125) but are **not enriched** with workflow linkage or outcomes prompts. Only solopreneur and startup journeys have been enriched (`0041_enrich_solopreneur_journeys.sql`, `0042_enrich_startup_journeys.sql`). The backend already supports journey → initiative → workflow execution via `start_journey_workflow`, and the strategic agent can persist `desired_outcomes`/`timeline` via `update_initiative`. The main gap is **SME journey enrichment** (descriptions, stages, KPIs, `primary_workflow_template_name`, `outcomes_prompt`, `category`). Optional UX improvements (outcomes on initiative page, run-workflow button) align with the startup plan.

---

## 1. Current state

### 1.1 SME journeys (40 total)

Defined in `supabase/migrations/0017_seed_user_journeys.sql` (lines 86–125). Each has:

- `persona`: `'sme'`
- `title`: e.g. "Performance Review Cycle", "Supply Chain Optimization", "New Market Expansion", "Department Budgeting", … (full list in §4)
- `description`: Generic "Standard journey for … in sme context."
- `stages`: Generic `[{"name":"Start","status":"pending"},{"name":"In Progress","status":"pending"},{"name":"Complete","status":"pending"}]`
- **Missing** (columns added in `0040_user_journeys_workflow_and_outcomes.sql`, never populated for SME):
  - `primary_workflow_template_name`
  - `suggested_workflows` (JSONB)
  - `outcomes_prompt`
  - `category`
  - `kpis` (optional)

### 1.2 Flow today

| Step | Implemented | Notes |
|------|-------------|--------|
| User sees journeys (Dashboard → User Journeys, filter SME) | ✅ | `frontend/src/app/dashboard/journeys/page.tsx` – SME in `PERSONA_CONFIG` |
| User clicks "Start as Initiative" | ✅ | `POST /initiatives/from-journey` in `app/routers/initiatives.py` |
| Initiative created with `metadata.journey_id`, `journey_title`, `journey_stages`, `kpis` | ✅ | Same router; journey fetched from `user_journeys` |
| Initiative detail page shows "Desired outcomes" and "Discuss with Agent" | ✅ | `frontend/src/app/dashboard/initiatives/[id]/page.tsx` |
| Workspace opens with initiative context and fromJourney prompt | ✅ | `PersonaDashboardLayout.tsx` |
| Agent has `start_journey_workflow(initiative_id)` | ✅ | `app/agents/strategic/tools.py` – uses `primary_workflow_template_name` or fallback "Initiative Framework" |
| Agent can persist desired_outcomes/timeline to initiative metadata | ✅ | `update_initiative` supports `desired_outcomes`, `timeline`, `metadata`; `InitiativeService` merges metadata |
| SME journeys have `primary_workflow_template_name` / `outcomes_prompt` | ❌ | Not set → agent always uses "Initiative Framework" and no guided outcomes prompt |

### 1.3 Workflow templates (reference)

Existing template names in `workflow_templates` (from `0009_seed_workflows.sql`, `0038_seed_yaml_workflows.sql`) that can be used for SME journeys include: Initiative Framework, Strategic Planning Cycle, Lead Generation Workflow, Content Creation Workflow, Competitor Analysis Workflow, Product Launch Workflow, Social Media Campaign Workflow, Social Media Calendar, Email Nurture Sequence, Product Launch Campaign, SEO Optimization Audit, Influencer Outreach, Outbound Prospecting, Deal Closing, Account Renewal, Pipeline Review, Win/Loss Analysis, Fundraising Round, Partnership Development, Vendor Onboarding, Recruitment Pipeline, Customer Onboarding, Budget Planning, Financial Reporting, Contract Review, Policy Update, GDPR Compliance Audit, Churn Prevention, Knowledge Base Update, A/B Testing Workflow, etc. All names used in the mapping below must exist in `workflow_templates`.

---

## 2. Goals

1. **Enrich all 40 SME journeys** with:
   - Meaningful `description`, 5-phase `stages` (Ideation, Validation, Prototype, Build, Scale), `kpis`
   - `primary_workflow_template_name` (and optionally `suggested_workflows`)
   - `outcomes_prompt` (so agent/UI can ask the user for outcomes)
   - `category` for filtering (strategy, sales, marketing, operations, finance, legal, hr, support, content)

2. **Rely on existing backend behaviour** for:
   - Create-from-journey, initiative detail page, workspace prompt
   - Agent `update_initiative` (desired_outcomes, timeline, metadata merge) and `start_journey_workflow`
   - No backend changes required if Phase 1 from the startup plan is already done.

3. **(Optional)** Improve UX: show `outcomes_prompt` on journey card or initiative creation; initiative detail "Set outcomes" / "Run journey workflow" button; workspace initial message with journey outcomes prompt.

---

## 3. Implementation plan

### Phase 1: Backend – Verify agent can persist outcomes (no change if already done)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 1.1 | Verify `update_initiative` supports metadata/desired_outcomes/timeline | Backend | In `app/agents/strategic/tools.py`, `update_initiative` already accepts `desired_outcomes`, `timeline`, `metadata` and merges into initiative metadata. Confirm `app/services/initiative_service.py` merges metadata (existing_meta + update) so `journey_id` is preserved. |
| 1.2 | Verify strategic agent instructions | Backend | In `app/agents/strategic/agent.py` (or shared instructions), ensure instructions state: for initiative from user journey, (1) if desired_outcomes/timeline not set, ask using the journey's outcomes_prompt; (2) once set, persist via update_initiative; (3) then call start_journey_workflow. |

**Deliverable:** Confirmation that automode path is already supported for any persona (including SME once journeys are enriched).

---

### Phase 2: Data – Enrich SME journeys (40 rows)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 2.1 | Add migration `0043_enrich_sme_journeys.sql` | Backend/DB | For each of the 40 SME journey titles, add one `UPDATE user_journeys SET ... WHERE persona = 'sme' AND title = '...'` with: `description` (short, actionable), `stages` = 5-phase JSON (Ideation, Validation, Prototype, Build, Scale), `kpis` = JSON array of 3–5 KPIs, `primary_workflow_template_name` = one of existing workflow_templates.name, `suggested_workflows` = JSON array of 0–3 template names, `outcomes_prompt` = one or two sentences (e.g. "What does success look like? Timeline?"), `category` = one of strategy, sales, marketing, operations, finance, legal, hr, support, content. |
| 2.2 | Map each SME journey to workflow template | Backend/DB | Use existing names from `workflow_templates` (see §4 table). Prefer one primary template per journey; suggest 0–2 alternatives in `suggested_workflows` where useful. |
| 2.3 | Validate migration | QA | Run migration, then `SELECT id, title, primary_workflow_template_name, category, outcomes_prompt FROM user_journeys WHERE persona = 'sme';` and spot-check that all 40 have non-null primary_workflow_template_name and outcomes_prompt. |

**Deliverable:** All 40 SME journeys have descriptions, stages, KPIs, workflow linkage, outcomes prompt, and category.

---

### Phase 3: Frontend / UX (optional but recommended)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 3.1 | Show outcomes_prompt on journey card or initiative creation | Frontend | When displaying an SME journey (journey card or "Start as Initiative" flow), optionally show the journey's `outcomes_prompt` so the user knows what the agent will ask. |
| 3.2 | Initiative detail: "Set outcomes" / "Run workflow" | Frontend | On initiative detail page, for initiatives with `metadata.journey_id`: (a) If no `desired_outcomes`, show a short form or CTA "Set desired outcomes"; (b) add a "Run journey workflow" button that starts the journey's primary workflow for this initiative (e.g. POST /initiatives/:id/start-journey-workflow). |
| 3.3 | Workspace: pass journey outcomes_prompt to initial message | Frontend | When opening workspace with fromJourney and initiativeId, optionally append the journey's `outcomes_prompt` to the initial chat prompt (fetch journey by metadata.journey_id or pass from initiative detail). |

**Deliverable:** Clearer UX for setting outcomes and starting the journey workflow; agent remains the primary path for automode.

---

### Phase 4: Agent automode behaviour (verification)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 4.1 | Verify start_journey_workflow with SME journeys | Backend | After Phase 2: create an initiative from an SME journey (e.g. "New Market Expansion"), set desired_outcomes in metadata (via agent or DB), call `start_journey_workflow(initiative_id)`. Confirm the correct template (from journey's primary_workflow_template_name) is started and context (desired_outcomes, timeline, topic) is passed. |
| 4.2 | E2E test (manual or automated) | QA | User persona SME → Journeys → Start "New Market Expansion" (or "CRM Migration") as initiative → Open "Discuss with Agent" → Provide outcomes and timeline → Agent saves and starts workflow → Workflow appears in progress. |

**Deliverable:** Documented and verified automode flow for SME journey–sourced initiatives.

---

## 4. SME journey → workflow mapping (suggested)

Use this as the basis for Phase 2 migration. All template names must exist in `workflow_templates`.

| # | Journey title | Category | Primary workflow template | Suggested workflows |
|---|----------------|----------|---------------------------|---------------------|
| 1 | Performance Review Cycle | hr | Strategic Planning Cycle | Win/Loss Analysis, Content Creation Workflow |
| 2 | Supply Chain Optimization | operations | Strategic Planning Cycle | Vendor Onboarding, Pipeline Review |
| 3 | New Market Expansion | strategy | Competitor Analysis Workflow | Lead Generation Workflow, Strategic Planning Cycle |
| 4 | Department Budgeting | finance | Budget Planning | Financial Reporting, Strategic Planning Cycle |
| 5 | Management Training Program | hr | Strategic Planning Cycle | Content Creation Workflow, Recruitment Pipeline |
| 6 | Diversity & Inclusion Initiative | hr | Strategic Planning Cycle | Content Creation Workflow, Win/Loss Analysis |
| 7 | Employee Wellness Program | hr | Customer Onboarding | Strategic Planning Cycle |
| 8 | Office Hybrid Policy | hr | Policy Update | Strategic Planning Cycle, Content Creation Workflow |
| 9 | IT Asset Lifecycle | operations | Vendor Onboarding | Strategic Planning Cycle |
| 10 | Cybersecurity Audit | operations | GDPR Compliance Audit | Policy Update, Strategic Planning Cycle |
| 11 | Disaster Recovery Plan | operations | Strategic Planning Cycle | Policy Update, Crisis Management Response |
| 12 | CRM Migration | operations | Vendor Onboarding | Strategic Planning Cycle, Customer Onboarding |
| 13 | ERP Implementation | operations | Strategic Planning Cycle | Vendor Onboarding, Budget Planning |
| 14 | Sales Commission Structure | sales | Strategic Planning Cycle | Deal Closing, Pipeline Review |
| 15 | Customer Success Playbook | support | Customer Onboarding | Churn Prevention, Account Renewal |
| 16 | NPS Survey Campaign | support | Win/Loss Analysis | Email Nurture Sequence, Content Creation Workflow |
| 17 | Brand Refresh | marketing | Content Creation Workflow | Social Media Campaign Workflow, SEO Optimization Audit |
| 18 | Website Replatforming | marketing | Product Launch Workflow | Content Creation Workflow, SEO Optimization Audit |
| 19 | Vendor Consolidation | operations | Vendor Onboarding | Strategic Planning Cycle, Pipeline Review |
| 20 | Procurement Policy | operations | Policy Update | Contract Review, Strategic Planning Cycle |
| 21 | Expense Policy Update | operations | Policy Update | Budget Planning, Strategic Planning Cycle |
| 22 | Travel Policy Update | operations | Policy Update | Strategic Planning Cycle |
| 23 | Recruitment Agency ROI | hr | Recruitment Pipeline | Win/Loss Analysis, Pipeline Review |
| 24 | Internship Program | hr | Recruitment Pipeline | Employee Onboarding, Strategic Planning Cycle |
| 25 | Corporate Social Responsibility | strategy | Strategic Planning Cycle | Content Creation Workflow, Partnership Development |
| 26 | Sustainability Report | strategy | Content Creation Workflow | Strategic Planning Cycle, Financial Reporting |
| 27 | Annual Report Design | strategy | Content Creation Workflow | Financial Reporting, Strategic Planning Cycle |
| 28 | Town Hall Meeting Deck | strategy | Content Creation Workflow | Strategic Planning Cycle |
| 29 | Leadership Offsite | strategy | Strategic Planning Cycle | Content Creation Workflow |
| 30 | Succession Planning | hr | Strategic Planning Cycle | Recruitment Pipeline, Win/Loss Analysis |
| 31 | Key Account Management | sales | Account Renewal | Pipeline Review, Deal Closing |
| 32 | Partner Channel Strategy | strategy | Partnership Development | Lead Generation Workflow, Strategic Planning Cycle |
| 33 | Reseller Program | sales | Partnership Development | Deal Closing, Vendor Onboarding |
| 34 | Loyalty Program Revamp | marketing | Email Nurture Sequence | Social Media Campaign Workflow, A/B Testing Workflow |
| 35 | Inventory Turnover Analysis | operations | Pipeline Review | Financial Reporting, Strategic Planning Cycle |
| 36 | Cash Flow Forecasting | finance | Financial Reporting | Budget Planning, Strategic Planning Cycle |
| 37 | Debt Refinancing | finance | Strategic Planning Cycle | Financial Reporting, Contract Review |
| 38 | Insurance Renewal | operations | Vendor Onboarding | Contract Review, Budget Planning |
| 39 | Legal Retainer Review | legal | Contract Review | Strategic Planning Cycle, Pipeline Review |
| 40 | Compliance Training | legal | Policy Update | GDPR Compliance Audit, Content Creation Workflow |

Use the same 5-phase stages format as solopreneur/startup:  
`[{"name":"Ideation","status":"pending"},{"name":"Validation","status":"pending"},{"name":"Prototype","status":"pending"},{"name":"Build","status":"pending"},{"name":"Scale","status":"pending"}]`  

`outcomes_prompt` can be: **"What does success look like for this initiative? Any timeline or key milestones?"** (or journey-specific variants as in startup/solopreneur).

---

## 5. Success criteria

- All 40 SME journeys have `primary_workflow_template_name`, `outcomes_prompt`, `category`, and enriched `description`/`stages`/`kpis`.
- From workspace, when user has an initiative from an SME journey and provides outcomes (and optionally timeline), the agent can save them via `update_initiative` and run `start_journey_workflow`; the correct workflow template runs with that context.
- (Optional) Initiative detail page supports setting outcomes and/or starting the journey workflow with one click.

---

## 6. Files to touch (summary)

| Area | Files |
|------|--------|
| Data | New migration `supabase/migrations/0043_enrich_sme_journeys.sql` |
| Backend (verify only) | `app/agents/strategic/tools.py`, `app/services/initiative_service.py`, `app/agents/strategic/agent.py` or `app/agents/shared_instructions.py` |
| Frontend (optional) | `frontend/src/app/dashboard/journeys/page.tsx`, `frontend/src/app/dashboard/initiatives/[id]/page.tsx`, `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` |
| API (optional) | New route e.g. `POST /initiatives/{id}/start-journey-workflow` in `app/routers/initiatives.py` |

---

## 7. Order of execution

1. **Phase 1** (verify backend) – confirm no code changes needed for SME automode.
2. **Phase 2** (migration: enrich SME journeys) – makes SME journeys first-class like solopreneur and startup.
3. **Phase 4** (verify automode) – confirm end-to-end with one SME journey.
4. **Phase 3** (frontend/UX) – as time allows.

This plan keeps existing flows intact and adds the minimal changes required for SME journeys to be end-to-end and agent-executable in automode.
