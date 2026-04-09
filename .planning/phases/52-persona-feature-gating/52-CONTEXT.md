# Phase 52: Persona & Feature Gating - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Make each persona tier see appropriate features with upgrade prompts, adapt the ExecutiveAgent and all sub-agents to user persona, populate enterprise/SME-specific metrics with real data, and wire shell header KPIs to computed values:

1. **Upgrade prompts** — When a user on a restricted tier accesses a gated feature, show a modal upgrade prompt (not an error) with a direct Stripe checkout CTA (GATE-01).
2. **Persona-aware agents** — ExecutiveAgent and all 10 sub-agents receive persona-specific behavioral instructions that adjust tone, depth, and suggested actions — but never restrict tool/agent access (GATE-02, UX-05).
3. **Enterprise portfolio health** — Enterprise dashboard shows real portfolio metrics aggregated from initiatives + workflows tables, not placeholders (GATE-03).
4. **SME department coordination** — SME users can route tasks to department-specific agents via natural language, with cross-department view by default and optional department filter (GATE-04).
5. **Shell header KPIs** — Different KPIs per persona tier, computed from real data via a `kpi_snapshots` table, displayed in the shell header on page load (UX-04).

**Out of scope for Phase 52** (deferred):
- Changing which agents are available per tier (all agents available to all personas — rate limits differentiate)
- Changing the AI model per tier (same model for all tiers)
- Department-scoped sub-workspaces (Phase 53 teams territory)
- Real-time KPI push updates (page-load + manual refresh is sufficient)
- Upgrade flow for enterprise tier (enterprise uses "contact us" — not self-serve checkout)

</domain>

<decisions>
## Implementation Decisions

### Upgrade Prompt UX (GATE-01)

- **Trigger:** Frontend catches HTTP 403 responses that include a `feature` key in the JSON body (`{detail, feature, current_tier, required_tier, upgrade_url}`). If `feature` key is present → upgrade prompt. If absent → standard auth error. Backend already returns this shape via `app/middleware/feature_gate.py`.
- **UI pattern:** **Modal dialog** centered over the current page. Non-blocking — user can dismiss and continue using ungated features. Modal contains: feature name, one-line description of what it does, which tier unlocks it, and a primary CTA button.
- **CTA button:** **"Upgrade to {required_tier} — ${price}/mo"** that creates a Stripe checkout session for the required tier's monthly price (reuses Phase 50 checkout flow). One click from gate to payment. For enterprise tier gates specifically, show "Contact us" instead of checkout.
- **Navigation visibility:** **All features visible** in the sidebar with a **lock icon** on gated ones. Clicking a locked item opens the upgrade modal. Users can discover what's available at higher tiers — drives upgrade interest. Lock icon uses `lucide-react` `Lock` icon (small, subtle, next to the nav label).
- **Frontend implementation:** Create a reusable `<UpgradeGateModal>` component that any page/route can trigger. Intercept 403 responses in the shared `fetchWithAuth` helper to auto-show the modal. If a page component directly calls Supabase (not backend API), it won't hit the gate — only backend API calls go through the feature gate middleware.

### ExecutiveAgent Persona Behavior (GATE-02 + UX-05)

- **Adaptation method:** **Inject persona-specific behavioral instructions** into the system prompt. No tool restriction, no model change, no agent access restriction. Instructions already exist in `app/personas/behavioral_instructions.py` — wire them into agent construction.
- **Scope:** **All agents get persona context** — ExecutiveAgent AND all 10 specialized sub-agents receive the persona instructions. This means each agent's factory function (e.g., `create_financial_agent()`) must accept a `persona` parameter and prepend the behavioral instructions to its system prompt.
- **Tier mention policy:** **Silent by default, mention only for upgrade context.** Agents never say "As a solopreneur..." but DO say "That feature is available on the Startup plan — would you like to upgrade?" when the user asks about a gated capability.
- **Persona source of truth:** **Subscription tier from the `subscriptions` table** (Phase 50). If the user has an active subscription with `tier=startup`, they get Startup behavior regardless of what their profile.persona says. Profile persona (set during onboarding) is the fallback when no active subscription exists. `resolve_effective_persona()` in `app/personas/runtime.py` must be updated to check subscriptions first.
- **Instruction maintenance:** `behavioral_instructions.py` already has per-persona instruction blocks. Plan must verify coverage for all 4 tiers (solopreneur, startup, sme, enterprise) and ensure each agent's factory function uses them. If some agents lack persona-specific nuance, use the generic tier-level instructions (e.g., "enterprise: provide executive-level depth").

### Shell Header KPIs (UX-04)

- **Layout:** **Different 4 KPIs per persona tier** in the shell header. Each tier has its own set of 4 KPI cards reflecting what matters most to that user type.
- **KPI sets by tier:**
  - **Solopreneur:** Revenue, Active Tasks, Content Created, Connected Integrations
  - **Startup:** Revenue, Pipeline Value, Team Size, Growth Rate (MoM)
  - **SME:** Revenue, Active Departments, Compliance Score, Open Tasks
  - **Enterprise:** Portfolio Health %, Risk Score, Total Revenue, Department Count
- **Data source:** **`kpi_snapshots` table** in Supabase. A background job (Cloud Scheduler, hourly or on-demand) computes KPI values per user and writes them to the table. Frontend reads the latest snapshot on page load.
- **Frontend fetch pattern:** **Page load + manual refresh button.** Shell header fetches KPIs from a new `GET /api/kpis` endpoint when the shell mounts. Refresh button triggers a re-fetch. No polling, no realtime subscription. Matches the billing dashboard pattern.
- **Empty state:** **Show $0 / 0 with a subtle hint.** When a KPI has no data (new user, no revenue), display the zero value with a small subtitle: "No revenue yet — complete your first sale to see this update." Honest, not broken-looking.
- **Backend endpoint:** New `GET /api/kpis?persona={tier}` endpoint returns the 4 KPI values for the user's tier. Reads from `kpi_snapshots` where `user_id = current_user`. If no snapshot exists, computes on-the-fly from source tables (fallback for first-time users before the background job runs).

### Enterprise Portfolio Health (GATE-03)

- **Data source:** **Aggregate from existing `initiatives` and `workflows` tables.** No new external data sources. Portfolio health = count of active/stalled/completed initiatives + workflow success rate + revenue trend (from Stripe subscription data via Phase 50).
- **Existing endpoint:** `/portfolio-health` already exists in `app/routers/governance.py`. Plan must verify if it returns real data or placeholders, and update the query logic to compute from real initiative/workflow state.
- **Metrics to surface:** Portfolio health percentage (active initiatives / total), risk score (stalled + failed initiatives / total), initiative breakdown by status, workflow success rate.

### SME Department Coordination (GATE-04)

- **Routing method:** **ExecutiveAgent routes by keyword/intent matching** to department-specific agents. When an SME user says "handle the hiring for engineering," ExecutiveAgent detects 'hiring' + 'engineering' and routes to HR agent with department='engineering' context. No new infrastructure — enhanced routing instructions in the executive prompt.
- **Default view:** **Cross-department view by default.** SME users see data from all departments. A department filter is available in the UI to narrow down results (dropdown in dashboard header or sidebar filter).
- **Department list:** Static list matching existing agent domains: Engineering, Marketing, Sales, Finance, HR, Operations, Compliance, Support. Not user-configurable in Phase 52 — hardcoded to match the 10 agent domains.

### Claude's Discretion

The planner may decide the following without re-asking:
- Exact modal animation/transition for UpgradeGateModal
- Lock icon size and color (should be subtle, match nav text color)
- KPI card layout in shell header (horizontal row vs 2x2 grid — depends on available header space)
- Background job frequency for kpi_snapshots computation (hourly or every 30 min)
- Department filter UI placement (sidebar filter vs dropdown in dashboard header)
- How to handle the "first run" case before kpi_snapshots background job has run (compute on-the-fly is the fallback)
- Exact behavioral instruction wording per agent per persona (follow existing patterns in behavioral_instructions.py)
- Whether to use a React context or prop drilling for persona state in the frontend

</decisions>

<specifics>
## Specific Ideas

- Lock icons on nav items should be subtle — small, same color as nav text, not attention-grabbing. The upgrade modal is where the "sell" happens, not the icon.
- Upgrade modal should feel like an opportunity, not a punishment. Tone: "Unlock [feature] with [tier]" not "You can't access this."
- KPIs should look like the existing dashboard KPI rows (billing, analytics pages already have this pattern) — same card component, same spacing.
- Enterprise portfolio health should feel executive-level — percentages, scores, not raw counts. "85% portfolio health" not "17 active initiatives."
- Silent persona adaptation is key — users should feel the AI "gets them" without being told which bucket they're in.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`app/middleware/feature_gate.py`** — `require_feature()` dependency already returns 403 with `{feature, current_tier, required_tier}` JSON. Backend side of GATE-01 is DONE. Phase 52 only needs the frontend to handle this response.
- **`app/config/feature_gating.py`** — `FEATURE_ACCESS` dict defines which features are gated and at what tier. `is_feature_allowed()` and `get_required_tier()` helpers.
- **`app/personas/behavioral_instructions.py`** — Per-persona instruction blocks. Needs verification that all 4 tiers have coverage and that agent factory functions use them.
- **`app/personas/runtime.py`** — `resolve_effective_persona()` resolves persona from request. Must be updated to check subscription tier first (Phase 50 `subscriptions` table), profile.persona as fallback.
- **`app/personas/policy_registry.py`** — Policy rules per persona. May need expansion for Phase 52.
- **`app/personas/prompt_fragments.py`** — Prompt additions per persona.
- **`app/routers/governance.py`** — `/portfolio-health` endpoint. Needs real query implementation.
- **`app/middleware/rate_limiter.py`** — Rate limiting by persona (solopreneur: 10/min through enterprise: 120/min). Already working.
- **Dashboard KPI patterns** — Multiple pages (`billing/page.tsx`, `analytics/page.tsx`, `content/page.tsx`) already render KPI card rows. Reuse same component and spacing.
- **`SubscriptionContext`** (Phase 50) — React context that provides the user's subscription tier. Can be used to drive persona-specific UI behavior frontend-side.

### Established Patterns

- **`AdminService` base class** — Service pattern for authenticated services. KPI computation service should follow this pattern if it needs service-role access.
- **`require_feature()` middleware** — Dependency injection pattern for feature gates. Already applied to compliance, team features, etc.
- **Agent factory functions** — `create_financial_agent()`, `create_content_agent()`, etc. in `app/agents/<domain>/agent.py`. These are the injection points for persona instructions.
- **`fetchWithAuth`** — Frontend auth-wrapped fetch helper. The 403 interception for upgrade prompts should live here.

### Integration Points

- **Shell header** — `frontend/src/components/layout/PremiumShell.tsx` (or similar shell component) is where KPI cards would render. SubscriptionBadge is already there (Phase 50).
- **Sidebar navigation** — `frontend/src/components/admin/adminNav.ts` and the persona-based nav components. Lock icons need to be added here.
- **Agent construction** — `app/agent.py` (ExecutiveAgent) and `app/agents/specialized_agents.py` for the 10 sub-agents. Persona instructions need to be injected during agent creation.
- **Supabase subscriptions table** — Source of truth for persona tier resolution. Phase 50's webhook handler maintains this.
- **Cloud Scheduler** — Existing pattern for periodic jobs (`/admin/monitoring/run-check`, `/admin/observability/run-rollup`). KPI snapshot job follows the same pattern.

</code_context>

<deferred>
## Deferred Ideas

- **Tool restriction per tier** — Not in Phase 52. All tools available to all personas. Rate limits are the differentiator.
- **Model tier differentiation** — Same model for all tiers. Could be a cost optimization lever later but creates visible quality gaps.
- **Department-scoped sub-workspaces** — Full department isolation is Phase 53 (Multi-User & Teams) territory.
- **Real-time KPI push updates** — Page-load + refresh button is sufficient for beta. Realtime push via Supabase can be added later if demand warrants.
- **Enterprise "contact us" upgrade flow** — Enterprise tier gates show "Contact us" not self-serve checkout. The actual contact flow (Calendly link, form, etc.) is deferred — just show the CTA for now.
- **User-configurable department list** — Departments are hardcoded to match agent domains in Phase 52. Custom departments are a Phase 53+ feature.

</deferred>

---

*Phase: 52-persona-feature-gating*
*Context gathered: 2026-04-09*
