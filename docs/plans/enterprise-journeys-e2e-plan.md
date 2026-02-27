
# Enterprise Persona User Journeys – End-to-End Implementation Plan

## Executive summary

This plan ensures all **40 Enterprise persona user journeys** are end-to-end implemented so that:
1. **Users** can discover Enterprise journeys, start them as initiatives, set desired outcomes, and run workflows.
2. **Agents** can execute journey workflows automatically (automode) once they have the required information (initiative outcomes) from the user.

**Current state:** Enterprise journeys exist in `user_journeys` (migration `0017_seed_user_journeys.sql`, lines 127–166) but are **not enriched** with workflow linkage or outcomes prompts. Solopreneur, startup, and SME journeys have been enriched (`0041_enrich_solopreneur_journeys.sql`, `0042_enrich_startup_journeys.sql`, `0043_enrich_sme_journeys.sql`). The backend already supports journey → initiative → workflow execution via `start_journey_workflow`, and the strategic agent can persist `desired_outcomes`/`timeline` via `update_initiative`; InitiativeService merges metadata. The main gap is **Enterprise journey enrichment** (descriptions, stages, KPIs, `primary_workflow_template_name`, `outcomes_prompt`, `category`). Optional UX improvements (outcomes on initiative page, run-workflow button) align with the startup/SME plans.

---

## 1. Current state

### 1.1 Enterprise journeys (40 total)

Defined in `supabase/migrations/0017_seed_user_journeys.sql` (lines 127–166). Each has:

- `persona`: `'enterprise'`
- `title`: e.g. "Global Compliance Audit", "Merger & Acquisition Integration", "Digital Transformation Roadmap", "AI Governance Framework", … (full list in §4)
- `description`: Generic "Standard journey for … in enterprise context."
- `stages`: Generic `[{"name":"Start","status":"pending"},{"name":"In Progress","status":"pending"},{"name":"Complete","status":"pending"}]`
- **Missing** (columns added in `0040_user_journeys_workflow_and_outcomes.sql`, never populated for Enterprise):
  - `primary_workflow_template_name`
  - `suggested_workflows` (JSONB)
  - `outcomes_prompt`
  - `category`
  - `kpis` (optional)

### 1.2 Flow today

| Step | Implemented | Notes |
|------|-------------|--------|
| User sees journeys (Dashboard → User Journeys, filter Enterprise) | ✅ | `frontend/src/app/dashboard/journeys/page.tsx` – Enterprise in `PERSONA_CONFIG` |
| User clicks "Start as Initiative" | ✅ | `POST /initiatives/from-journey` in `app/routers/initiatives.py` |
| Initiative created with `metadata.journey_id`, `journey_title`, `journey_stages`, `kpis` | ✅ | Same router; journey fetched from `user_journeys` |
| Initiative detail page shows "Desired outcomes" and "Discuss with Agent" | ✅ | `frontend/src/app/dashboard/initiatives/[id]/page.tsx` |
| Workspace opens with initiative context and fromJourney prompt | ✅ | `PersonaDashboardLayout.tsx` |
| Agent has `start_journey_workflow(initiative_id)` | ✅ | `app/agents/strategic/tools.py` – uses `primary_workflow_template_name` or fallback "Initiative Framework" |
| Agent can persist desired_outcomes/timeline to initiative metadata | ✅ | `update_initiative` supports `desired_outcomes`, `timeline`, `metadata`; `InitiativeService` merges metadata |
| Enterprise journeys have `primary_workflow_template_name` / `outcomes_prompt` | ❌ | Not set → agent always uses "Initiative Framework" and no guided outcomes prompt |

### 1.3 Workflow templates (reference)

Existing template names in `workflow_templates` that can be used for Enterprise journeys include: Initiative Framework, Strategic Planning Cycle, Merger & Acquisition (M&A), GDPR Compliance Audit, Data Governance Audit, Crisis Management Response, Incident Investigation, Policy Update, Contract Review, Roadmap Planning, Content Creation Workflow, Performance Review, Employee Onboarding, Payroll Processing, Vendor Onboarding, Partnership Development, Fundraising Round, Quality Assurance Audit, Tax Filing Prep, Knowledge Base Update, Ad Campaign Management, Social Media Campaign Workflow, Feature Development, and others. All names used in the mapping below must exist in `workflow_templates`.

---

## 2. Goals

1. **Enrich all 40 Enterprise journeys** with:
   - Meaningful `description`, 5-phase `stages` (Ideation, Validation, Prototype, Build, Scale), `kpis`
   - `primary_workflow_template_name` (and optionally `suggested_workflows`)
   - `outcomes_prompt` (so agent/UI can ask the user for outcomes)
   - `category` for filtering (strategy, compliance, operations, finance, hr, marketing, product, legal, support)

2. **Rely on existing backend behaviour** for:
   - Create-from-journey, initiative detail page, workspace prompt
   - Agent `update_initiative` (desired_outcomes, timeline, metadata merge) and `start_journey_workflow`
   - No backend code changes required; only data enrichment.

3. **(Optional)** Improve UX: show `outcomes_prompt` on journey card or initiative creation; initiative detail "Set outcomes" / "Run journey workflow" button; workspace initial message with journey outcomes prompt.

---

## 3. Implementation plan

### Phase 1: Backend – Verify agent can persist outcomes (no change if already done)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 1.1 | Verify `update_initiative` supports metadata/desired_outcomes/timeline | Backend | In `app/agents/strategic/tools.py`, `update_initiative` already accepts `desired_outcomes`, `timeline`, `metadata` and merges into initiative metadata. Confirm `app/services/initiative_service.py` merges metadata (existing_meta + update) so `journey_id` is preserved. |
| 1.2 | Verify strategic agent instructions | Backend | In `app/agents/strategic/agent.py` (or shared instructions), ensure instructions state: for initiative from user journey, (1) if desired_outcomes/timeline not set, ask using the journey's outcomes_prompt; (2) once set, persist via update_initiative; (3) then call start_journey_workflow. |

**Deliverable:** Confirmation that automode path is already supported for any persona (including Enterprise once journeys are enriched).

---

### Phase 2: Data – Enrich Enterprise journeys (40 rows)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 2.1 | Add migration `0044_enrich_enterprise_journeys.sql` | Backend/DB | For each of the 40 Enterprise journey titles, add one `UPDATE user_journeys SET ... WHERE persona = 'enterprise' AND title = '...'` with: `description` (short, actionable, enterprise-appropriate), `stages` = 5-phase JSON (Ideation, Validation, Prototype, Build, Scale), `kpis` = JSON array of 3–5 KPIs, `primary_workflow_template_name` = one of existing workflow_templates.name, `suggested_workflows` = JSON array of 0–3 template names, `outcomes_prompt` = one or two sentences (e.g. "What does success look like for this initiative? Timeline and key milestones?"), `category` = one of strategy, compliance, operations, finance, hr, marketing, product, legal, support. |
| 2.2 | Map each Enterprise journey to workflow template | Backend/DB | Use existing names from `workflow_templates` (see §4 table). Prefer one primary template per journey; suggest 0–2 alternatives in `suggested_workflows` where useful. |
| 2.3 | Validate migration | QA | Run migration, then `SELECT id, title, primary_workflow_template_name, category, outcomes_prompt FROM user_journeys WHERE persona = 'enterprise';` and spot-check that all 40 have non-null primary_workflow_template_name and outcomes_prompt. |

**Deliverable:** All 40 Enterprise journeys have descriptions, stages, KPIs, workflow linkage, outcomes prompt, and category.

---

### Phase 3: Frontend / UX (optional but recommended)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 3.1 | Show outcomes_prompt on journey card or initiative creation | Frontend | When displaying an Enterprise journey (journey card or "Start as Initiative" flow), optionally show the journey's `outcomes_prompt` so the user knows what the agent will ask. |
| 3.2 | Initiative detail: "Set outcomes" / "Run workflow" | Frontend | On initiative detail page, for initiatives with `metadata.journey_id`: (a) If no `desired_outcomes`, show a short form or CTA "Set desired outcomes"; (b) add a "Run journey workflow" button that starts the journey's primary workflow for this initiative (e.g. POST /initiatives/:id/start-journey-workflow). |
| 3.3 | Workspace: pass journey outcomes_prompt to initial message | Frontend | When opening workspace with fromJourney and initiativeId, optionally append the journey's `outcomes_prompt` to the initial chat prompt (fetch journey by metadata.journey_id or pass from initiative detail). |

**Deliverable:** Clearer UX for setting outcomes and starting the journey workflow; agent remains the primary path for automode.

---

### Phase 4: Agent automode behaviour (verification and tuning)

| # | Task | Owner | Details |
|---|------|--------|---------|
| 4.1 | Verify start_journey_workflow with Enterprise journeys | Backend | After Phase 2, create an initiative from an Enterprise journey (e.g. Digital Transformation Roadmap), set desired_outcomes in metadata (via agent or DB), call `start_journey_workflow(initiative_id)`. Confirm the correct template (from journey's primary_workflow_template_name) is started and context (desired_outcomes, timeline, topic) is passed. |
| 4.2 | Strategic agent instructions | Backend | Ensure instructions in `app/agents/strategic/agent.py` (or shared_instructions) state: for initiative from user journey, (1) if desired_outcomes/timeline not set, ask using the journey's outcomes_prompt (or generic prompt); (2) once set, persist via update_initiative; (3) then call start_journey_workflow and use get_workflow_status/approve_workflow_step for automode. |
| 4.3 | E2E test (manual or automated) | QA | User persona Enterprise → Journeys → Start "Digital Transformation Roadmap" as initiative → Open "Discuss with Agent" → Provide outcomes and timeline → Agent saves and starts workflow → Workflow appears in progress. |

**Deliverable:** Documented and verified automode flow for Enterprise journey–sourced initiatives.

---

## 4. Enterprise journey → workflow mapping (suggested)

Use this as the basis for Phase 2 migration. All template names must exist in `workflow_templates`.

| # | Journey title | Category | Primary workflow template | Suggested workflows |
|---|----------------|----------|---------------------------|---------------------|
| 1 | Global Compliance Audit | compliance | GDPR Compliance Audit | Strategic Planning Cycle, Policy Update |
| 2 | Merger & Acquisition Integration | strategy | Merger & Acquisition (M&A) | Strategic Planning Cycle, Contract Review |
| 3 | Enterprise-wide ERP Rollout | operations | Roadmap Planning | Strategic Planning Cycle, Vendor Onboarding |
| 4 | Digital Transformation Roadmap | strategy | Strategic Planning Cycle | Roadmap Planning, Initiative Framework |
| 5 | Cloud Migration Strategy | strategy | Strategic Planning Cycle | Roadmap Planning, Data Pipeline Setup |
| 6 | Data Lake Architecture | operations | Data Pipeline Setup | Data Governance Audit, Strategic Planning Cycle |
| 7 | AI Governance Framework | compliance | Data Governance Audit | Policy Update, Initiative Framework |
| 8 | Global Payroll Consolidation | hr | Payroll Processing | Strategic Planning Cycle, Vendor Onboarding |
| 9 | Shared Services Center | operations | Strategic Planning Cycle | Vendor Onboarding, Roadmap Planning |
| 10 | Center of Excellence Setup | strategy | Strategic Planning Cycle | Roadmap Planning, Initiative Framework |
| 11 | Innovation Lab Launch | product | Initiative Framework | Strategic Planning Cycle, Partnership Development |
| 12 | Corporate Venture Capital | strategy | Partnership Development | Fundraising Round, Strategic Planning Cycle |
| 13 | Board Governance Review | strategy | Strategic Planning Cycle | Contract Review, Policy Update |
| 14 | Investor Relations Quarterly | strategy | Content Creation Workflow | Strategic Planning Cycle, Quarterly Business Review (QBR) |
| 15 | ESG Strategy | strategy | Strategic Planning Cycle | Content Creation Workflow, Policy Update |
| 16 | Diversity Annual Report | hr | Content Creation Workflow | Strategic Planning Cycle, Policy Update |
| 17 | Global Mobility Program | hr | Policy Update | Employee Onboarding, Contract Review |
| 18 | Executive Compensation Review | hr | Performance Review | Policy Update, Contract Review |
| 19 | Union Negotiation Strategy | hr | Contract Review | Policy Update, Strategic Planning Cycle |
| 20 | Crisis Communication Playbook | support | Crisis Management Response | Content Creation Workflow, Policy Update |
| 21 | Cyber Incident Response | compliance | Incident Investigation | Crisis Management Response, Policy Update |
| 22 | Business Continuity Test | operations | Crisis Management Response | Strategic Planning Cycle, Initiative Framework |
| 23 | Supply Chain Resilience | operations | Strategic Planning Cycle | Vendor Onboarding, Roadmap Planning |
| 24 | Global Tax Strategy | finance | Strategic Planning Cycle | Tax Filing Prep, Financial Reporting |
| 25 | Transfer Pricing Study | finance | Strategic Planning Cycle | Contract Review, Financial Reporting |
| 26 | Brand Architecture Review | marketing | Content Creation Workflow | Strategic Planning Cycle, Ad Campaign Management |
| 27 | Global Marketing Campaign | marketing | Ad Campaign Management | Social Media Campaign Workflow, Content Creation Workflow |
| 28 | Product Portfolio Rationalization | product | Roadmap Planning | Strategic Planning Cycle, Competitor Analysis Workflow |
| 29 | Legacy System Sunsetting | operations | Roadmap Planning | Strategic Planning Cycle, Feature Development |
| 30 | Mainframe Modernization | operations | Roadmap Planning | Feature Development, Data Pipeline Setup |
| 31 | Zero Trust Security Model | compliance | Policy Update | Data Governance Audit, Initiative Framework |
| 32 | GDPR/CCPA Compliance | compliance | GDPR Compliance Audit | Policy Update, Data Governance Audit |
| 33 | Whistleblower Hotline | compliance | Policy Update | Contract Review, Initiative Framework |
| 34 | Internal Audit Cycle | compliance | Quality Assurance Audit | Data Governance Audit, Strategic Planning Cycle |
| 35 | Strategic Vendor Review | operations | Vendor Onboarding | Partnership Development, Strategic Planning Cycle |
| 36 | Real Estate Portfolio | operations | Strategic Planning Cycle | Contract Review, Roadmap Planning |
| 37 | Corporate University | hr | Content Creation Workflow | Employee Onboarding, Knowledge Base Update |
| 38 | Leadership Development Program | hr | Performance Review | Employee Onboarding, Strategic Planning Cycle |
| 39 | Change Management Framework | operations | Strategic Planning Cycle | Initiative Framework, Roadmap Planning |
| 40 | Global Knowledge Management | operations | Knowledge Base Update | Strategic Planning Cycle, Content Creation Workflow |

Use the same 5-phase stages and a short, actionable description and 3–5 KPIs per journey (see solopreneur/startup/SME enrichment for format). `outcomes_prompt` can be: "What does success look like for this initiative? Any timeline or key milestones?"

---

## 5. Success criteria

- All 40 Enterprise journeys have `primary_workflow_template_name`, `outcomes_prompt`, `category`, and enriched `description`/`stages`/`kpis`.
- From workspace, when user has an initiative from an Enterprise journey and provides outcomes (and optionally timeline), the agent can save them via `update_initiative` and run `start_journey_workflow`; the correct workflow template runs with that context.
- (Optional) Initiative detail page supports setting outcomes and/or starting the journey workflow with one click.

---

## 6. Files to touch (summary)

| Area | Files |
|------|--------|
| Backend – verify only | `app/agents/strategic/tools.py`, `app/services/initiative_service.py`, `app/agents/strategic/agent.py` (or `app/agents/shared_instructions.py`) – no code change if already correct |
| Data | New migration `supabase/migrations/0044_enrich_enterprise_journeys.sql` |
| Frontend (optional) | `frontend/src/app/dashboard/journeys/page.tsx`, `frontend/src/app/dashboard/initiatives/[id]/page.tsx`, `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` |
| API (optional) | New route e.g. `POST /initiatives/{id}/start-journey-workflow` in `app/routers/initiatives.py` if Phase 3 "Run workflow" button is implemented |

---

## 7. Order of execution

1. **Phase 1** (verify backend) – confirm automode path is already supported.
2. **Phase 2** (migration: enrich Enterprise journeys) – makes Enterprise journeys first-class like solopreneur/startup/SME.
3. **Phase 4** (verify automode) – confirm end-to-end with one Enterprise journey.
4. **Phase 3** (frontend/UX) – as time allows.

This plan keeps existing flows intact and adds the minimal changes (data enrichment only) required for Enterprise journeys to be end-to-end and agent-executable in automode.

---

## 8. Implementation status (completed)

- **Phase 1:** Verified. Backend already supports `update_initiative` (desired_outcomes, timeline, metadata merge) and strategic agent instructions for journey → outcomes → start_journey_workflow.
- **Phase 2:** Done. Migration `0044_enrich_enterprise_journeys.sql` created; all 40 Enterprise journeys enriched (description, stages, kpis, primary_workflow_template_name, suggested_workflows, outcomes_prompt, category). Data applied to DB via execute_sql; for fresh deploys run `supabase db push` or apply the migration file.
- **Phase 4:** Verified. All 40 rows have non-null primary_workflow_template_name, outcomes_prompt, and category. Agent can run `start_journey_workflow(initiative_id)` and the correct template will be used.
- **Phase 3:** Implemented. (1) Journey card shows `outcomes_prompt` (“The agent will ask: …”). (2) Initiative detail shows “Set desired outcomes” when none set and “Run journey workflow” button; backend `POST /initiatives/:id/start-journey-workflow` exists. (3) Workspace: when opening from initiative with fromJourney, the initiative detail page passes `outcomesPrompt` in the URL; PersonaDashboardLayout appends it to the initial chat prompt so the agent can use the journey’s outcomes_prompt when asking for outcomes.
