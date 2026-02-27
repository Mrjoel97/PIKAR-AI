# Startup Persona User Journeys – End-to-End Implementation Plan

## Executive summary

This plan ensures all **40 startup persona user journeys** are end-to-end implemented so that:
1. **Users** can discover, start as initiatives, set desired outcomes, and run workflows.
2. **Agents** can execute journey workflows automatically (automode) once they have the required information (initiative outcomes) from the user.

Current state: Startup journeys exist in `user_journeys` (migration `0017_seed_user_journeys.sql`) but are **not enriched** with workflow linkage or outcomes prompts. Only solopreneur journeys were enriched in `0041_enrich_solopreneur_journeys.sql`. The backend supports journey → initiative → workflow execution via `start_journey_workflow` and the initiative detail page surfaces “Discuss with Agent” and desired outcomes; the main gaps are **startup journey enrichment**, **agent ability to persist outcomes**, and **optional UX improvements**.

---

## 1. Current state

### 1.1 Startup journeys (40 total)

Defined in `supabase/migrations/0017_seed_user_journeys.sql` (lines 41–80). Each has:

- `persona`: `'startup'`
- `title`: e.g. "Seed Fundraising", "MVP Launch", "First 10 Hires", "Co-founder Agreement", …
- `description`: Generic “Standard journey for … in startup context.”
- `stages`: Generic `[{"name":"Start","status":"pending"},{"name":"In Progress","status":"pending"},{"name":"Complete","status":"pending"}]`
- **Missing** (columns added in `0040_user_journeys_workflow_and_outcomes.sql`, never populated for startup):
  - `primary_workflow_template_name`
  - `suggested_workflows` (JSONB)
  - `outcomes_prompt`
  - `category`
  - `kpis` (optional; solopreneur has these)

### 1.2 Flow today

| Step | Implemented | Notes |
|------|-------------|--------|
| User sees journeys (Dashboard → User Journeys, filter Startup) | ✅ | `frontend/src/app/dashboard/journeys/page.tsx` |
| User clicks “Start as Initiative” | ✅ | Calls `POST /initiatives/from-journey` or direct Supabase insert |
| Initiative created with `metadata.journey_id`, `journey_title`, `journey_stages`, `kpis` | ✅ | `app/routers/initiatives.py` |
| Initiative detail page shows “Desired outcomes” and “Discuss with Agent” | ✅ | `frontend/src/app/dashboard/initiatives/[id]/page.tsx` |
| Workspace opens with initiative context and fromJourney prompt | ✅ | `PersonaDashboardLayout.tsx`: asks for outcomes, then run journey workflow |
| Agent has `start_journey_workflow(initiative_id)` | ✅ | `app/agents/strategic/tools.py`: loads journey, uses `primary_workflow_template_name` or fallback “Initiative Framework” |
| Agent can **persist** desired_outcomes/timeline to initiative metadata | ❌ | `update_initiative` in strategic tools does not accept `metadata` (or `desired_outcomes`/`timeline`) |
| Startup journeys have `primary_workflow_template_name` / `outcomes_prompt` | ❌ | Not set → agent always uses “Initiative Framework” and no guided outcomes prompt |

### 1.3 Workflow templates (reference)

Existing template names (from DB) that can be used for startup journeys include:  
Initiative Framework, Lead Generation Workflow, Product Launch Workflow, Fundraising Round, Competitor Analysis Workflow, Content Creation Workflow, Social Media Campaign Workflow, Recruitment Pipeline, Strategic Planning Cycle, Budget Planning, Financial Reporting, Pipeline Review, Deal Closing, Customer Onboarding, Email Nurture Sequence, Product Launch Campaign, SEO Optimization Audit, etc.

---

## 2. Goals

1. **Enrich all 40 startup journeys** with:
   - Meaningful `description`, 5-phase `stages`, `kpis`
   - `primary_workflow_template_name` (and optionally `suggested_workflows`)
   - `outcomes_prompt` (so agent/UI can ask the user for outcomes)
   - `category` for filtering (e.g. strategy, sales, marketing, operations, finance, legal, hr)

2. **Allow agents to persist outcomes** so that:
   - When the user provides desired outcomes (and optionally timeline), the agent can save them to `initiative.metadata` (`desired_outcomes`, `timeline`).
   - Automode can then run `start_journey_workflow` with that context and optionally advance steps.

3. **Keep existing behaviour** for create-from-journey, initiative detail page, and workspace prompt; fix only what’s missing.

4. **(Optional)** Improve UX: e.g. inline “Set outcomes” on initiative page, or “Run journey workflow” button that starts the primary workflow for that initiative.

---

## 3. Implementation plan

### Phase 1: Backend – Agent can persist outcomes (required for automode)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 1.1 | Extend `update_initiative` in strategic agent to support metadata | Backend | In `app/agents/strategic/tools.py`, add optional `metadata: dict = None` (and/or explicit `desired_outcomes: str = None`, `timeline: str = None`). If provided, merge into existing initiative metadata and call `InitiativeService.update_initiative(..., metadata=merged)`. Ensure merge semantics (read current initiative.metadata, merge keys, write back) so other metadata (e.g. journey_id) is not lost. |
| 1.2 | InitiativeService metadata merge | Backend | In `app/services/initiative_service.py`, ensure `update_initiative` when given `metadata` merges with existing `metadata` (e.g. fetch current initiative, merge dicts, then update) rather than replacing entire metadata. |
| 1.3 | Document agent behaviour | Docs/Agent | In strategic agent instructions, state explicitly: “When the user provides desired outcomes or timeline for a journey-sourced initiative, use update_initiative with metadata containing desired_outcomes and/or timeline, then call start_journey_workflow.” |

**Deliverable:** Agent can save desired outcomes and timeline to the initiative and then start the journey workflow in automode.

---

### Phase 2: Data – Enrich startup journeys (40 rows)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 2.1 | Add migration `0042_enrich_startup_journeys.sql` | Backend/DB | For each of the 40 startup journey titles, add one `UPDATE user_journeys SET ... WHERE persona = 'startup' AND title = '...'` with: `description` (short, actionable), `stages` = 5-phase JSON (Ideation, Validation, Prototype, Build, Scale), `kpis` = JSON array of 3–5 KPIs, `primary_workflow_template_name` = one of existing workflow_templates.name, `suggested_workflows` = JSON array of 0–3 template names, `outcomes_prompt` = one or two sentences (e.g. “What does success look like? Timeline?”), `category` = one of strategy, sales, marketing, operations, finance, legal, hr, content, product, support. |
| 2.2 | Map each startup journey to workflow template | Backend/DB | Use existing names from `workflow_templates` (see list above). Examples: Seed Fundraising → Fundraising Round; MVP Launch → Product Launch Workflow or Initiative Framework; First 10 Hires → Recruitment Pipeline; Co-founder Agreement → Contract Review or Strategic Planning Cycle; Product Market Fit Validation → Initiative Framework or Competitor Analysis Workflow; etc. Prefer one primary template per journey; suggest 0–2 alternatives in `suggested_workflows` where useful. |
| 2.3 | Validate migration | QA | Run migration, then `SELECT id, title, primary_workflow_template_name, category, outcomes_prompt FROM user_journeys WHERE persona = 'startup';` and spot-check that all 40 have non-null primary_workflow_template_name and outcomes_prompt. |

**Deliverable:** All 40 startup journeys have descriptions, stages, KPIs, workflow linkage, outcomes prompt, and category.

---

### Phase 3: Frontend / UX (optional but recommended)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 3.1 | Show outcomes_prompt on journey card or initiative creation | Frontend | When displaying a journey (e.g. journey card or “Start as Initiative” flow), optionally show the journey’s `outcomes_prompt` so the user knows what the agent will ask. |
| 3.2 | Initiative detail: “Set outcomes” / “Run workflow” | Frontend | On initiative detail page, for initiatives with `metadata.journey_id`: (a) If no `desired_outcomes`, show a short form or CTA “Set desired outcomes” that can open workspace with pre-filled context, or (b) add a “Run journey workflow” button that calls an API to start the journey’s primary workflow for this initiative (backend can implement via existing `start_journey_workflow` exposed as e.g. POST /initiatives/:id/start-journey-workflow). |
| 3.3 | Workspace: pass journey outcomes_prompt to initial message | Frontend | When opening workspace with `fromJourney=1` and initiativeId, optionally append the journey’s `outcomes_prompt` to the initial chat prompt (requires fetching journey by metadata.journey_id or passing it from initiative detail). |

**Deliverable:** Clearer UX for setting outcomes and starting the journey workflow from the initiative page; agent still remains the primary path for automode.

---

### Phase 4: Agent automode behaviour (verification and tuning)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 4.1 | Verify start_journey_workflow with startup journeys | Backend | After Phase 2, create an initiative from a startup journey, set desired_outcomes in metadata (via agent or DB), call `start_journey_workflow(initiative_id)`. Confirm the correct template (from journey’s primary_workflow_template_name) is started and context (desired_outcomes, timeline, topic) is passed. |
| 4.2 | Strategic agent instructions | Backend | Ensure instructions in `app/agents/strategic/agent.py` (or shared_instructions) state: for initiative from user journey, (1) if desired_outcomes/timeline not set, ask using the journey’s outcomes_prompt (or generic prompt); (2) once set, persist via update_initiative; (3) then call start_journey_workflow and use get_workflow_status/approve_workflow_step for automode. |
| 4.3 | E2E test (manual or automated) | QA | User persona Startup → Journeys → Start “Seed Fundraising” as initiative → Open “Discuss with Agent” → Provide outcomes and timeline → Agent saves and starts workflow → Workflow appears in progress. |

**Deliverable:** Documented and verified automode flow for startup journey–sourced initiatives.

---

## 4. Startup journey → workflow mapping (suggested)

Use this as the basis for Phase 2 migration. All template names must exist in `workflow_templates`.

| # | Journey title | Category | Primary workflow template | Suggested workflows |
|---|----------------|----------|---------------------------|---------------------|
| 1 | Seed Fundraising | strategy | Fundraising Round | Strategic Planning Cycle |
| 2 | MVP Launch | product | Product Launch Workflow | Initiative Framework |
| 3 | First 10 Hires | hr | Recruitment Pipeline | Employee Onboarding |
| 4 | Co-founder Agreement | legal | Contract Review | Strategic Planning Cycle |
| 5 | Entity Incorporation | legal | Contract Review | Strategic Planning Cycle |
| 6 | Cap Table Setup | finance | Strategic Planning Cycle | Budget Planning, Financial Reporting |
| 7 | Product Market Fit Validation | strategy | Initiative Framework | Competitor Analysis Workflow |
| 8 | Beta User Recruitment | sales | Lead Generation Workflow | Outbound Prospecting |
| 9 | Waitlist Growth Strategy | marketing | Email Nurture Sequence | Lead Generation Workflow, Social Media Campaign Workflow |
| 10 | Investor Update Template | strategy | Strategic Planning Cycle | Content Creation Workflow |
| 11 | Board Meeting Deck | strategy | Strategic Planning Cycle | Content Creation Workflow |
| 12 | Pitch Deck Iteration | strategy | Content Creation Workflow | Strategic Planning Cycle |
| 13 | Employee Stock Option Plan | hr | Contract Review | Strategic Planning Cycle |
| 14 | Remote Team Culture | hr | Employee Onboarding | Strategic Planning Cycle |
| 15 | Agile Workflow Setup | operations | Strategic Planning Cycle | Roadmap Planning |
| 16 | CI/CD Pipeline Setup | operations | Feature Development | Roadmap Planning |
| 17 | Security Compliance (SOC2 Prep) | operations | GDPR Compliance Audit | Policy Update |
| 18 | Data Privacy Policy | legal | Policy Update | Contract Review |
| 19 | Terms of Service Draft | legal | Contract Review | Content Creation Workflow |
| 20 | Trademark Registration | legal | IP Filing | Contract Review |
| 21 | Competitor Analysis | strategy | Competitor Analysis Workflow | Initiative Framework |
| 22 | Unit Economics Analysis | finance | Financial Reporting | Budget Planning, Strategic Planning Cycle |
| 23 | Burn Rate Monitoring | finance | Financial Reporting | Budget Planning, Pipeline Review |
| 24 | Runway Extension Strategy | finance | Fundraising Round | Budget Planning, Strategic Planning Cycle |
| 25 | Growth Hacking Experiments | marketing | A/B Testing Workflow | Social Media Campaign Workflow |
| 26 | Viral Loop Design | marketing | Product Launch Workflow | Social Media Campaign Workflow |
| 27 | Referral Program V1 | marketing | Partnership Development | Email Nurture Sequence |
| 28 | Product Hunt Launch | marketing | Product Launch Campaign | Social Media Campaign Workflow |
| 29 | TechCrunch Outreach | marketing | Influencer Outreach | Content Creation Workflow |
| 30 | AngelList Profile | strategy | Fundraising Round | Content Creation Workflow |
| 31 | YCombinator Application | strategy | Fundraising Round | Strategic Planning Cycle, Content Creation Workflow |
| 32 | Accelerator Prep | strategy | Fundraising Round | Strategic Planning Cycle |
| 33 | Series A Prep | strategy | Fundraising Round | Strategic Planning Cycle, Merger & Acquisition (M&A) |
| 34 | Strategic Pivot Analysis | strategy | Strategic Planning Cycle | Competitor Analysis Workflow, Initiative Framework |
| 35 | Customer Discovery Interviews | sales | Lead Generation Workflow | Win/Loss Analysis |
| 36 | Churn Analysis | sales | Churn Prevention | Win/Loss Analysis, Pipeline Review |
| 37 | Server Cost Optimization | operations | Budget Planning | Financial Reporting |
| 38 | Analytics Stack Setup | operations | Analytics Implementation | Data Pipeline Setup |
| 39 | Internal Dashboard Build | operations | Dashboard Creation | Analytics Implementation |
| 40 | Knowledge Base Create | operations | Knowledge Base Update | Content Creation Workflow |

Use the same 5-phase stages and a short, actionable description and 3–5 KPIs per journey (see solopreneur enrichment in `0041` for format). `outcomes_prompt` can be: “What does success look like for this initiative? Any timeline or key milestones?”

---

## 5. Success criteria

- All 40 startup journeys have `primary_workflow_template_name`, `outcomes_prompt`, `category`, and enriched `description`/`stages`/`kpis`.
- Agent can update an initiative’s metadata with `desired_outcomes` and `timeline`.
- From workspace, when user has an initiative from a startup journey and provides outcomes (and optionally timeline), the agent can save them and run `start_journey_workflow`; the correct workflow template runs with that context.
- (Optional) Initiative detail page supports setting outcomes and/or starting the journey workflow with one click.

---

## 6. Files to touch (summary)

| Area | Files |
|------|--------|
| Backend – agent outcomes | `app/agents/strategic/tools.py` (update_initiative: add metadata/desired_outcomes/timeline; merge and call service), `app/services/initiative_service.py` (metadata merge in update_initiative) |
| Agent instructions | `app/agents/strategic/agent.py` or `app/agents/shared_instructions.py` |
| Data | New migration `supabase/migrations/0042_enrich_startup_journeys.sql` |
| Frontend (optional) | `frontend/src/app/dashboard/journeys/page.tsx`, `frontend/src/app/dashboard/initiatives/[id]/page.tsx`, `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` |
| API (optional) | New route e.g. `POST /initiatives/{id}/start-journey-workflow` in `app/routers/initiatives.py` that calls initiative service + workflow engine (or reuses logic from strategic tools). |

---

## 7. Order of execution

1. **Phase 1** (backend: persist outcomes) – unblocks automode.
2. **Phase 2** (migration: enrich startup journeys) – makes startup journeys first-class like solopreneur.
3. **Phase 4** (verify automode) – confirm end-to-end with one journey.
4. **Phase 3** (frontend/UX) – as time allows.

This plan keeps existing flows intact and adds the minimal changes required for startup journeys to be end-to-end and agent-executable in automode.
