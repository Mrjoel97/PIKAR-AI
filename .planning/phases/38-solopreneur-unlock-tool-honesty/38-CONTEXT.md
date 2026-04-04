# Phase 38: Solopreneur Unlock & Tool Honesty - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove feature restrictions for the solopreneur persona so it is a full-featured single-user tier (not a limited tier), and rename all misleading agent tools to honestly reflect that they provide knowledge/guidance rather than real-world actions. Update behavioral instructions, KPIs, billing page, and org chart display to reflect these changes.

</domain>

<decisions>
## Implementation Decisions

### Gating Philosophy
- Solopreneur gets full access to: workflows, custom-workflows, sales, reports, approvals, compliance, finance-forecasting
- Only **two** features remain restricted for solopreneur: `teams` and `governance`
- `custom-workflows` (previously enterprise-only) is unlocked — solopreneurs get both standard and custom workflow builders
- Backend `feature_gating.py`: change `min_tier` to `"solopreneur"` for workflows, sales, reports, approvals, compliance, finance-forecasting, custom-workflows
- Frontend `featureGating.ts`: mirror all backend changes
- Backend `feature_gate.py` middleware: no logic change needed — `is_feature_allowed()` will naturally pass with updated min_tier values
- Billing page (`/dashboard/billing`): update comparison table to show solopreneur with checkmarks for all non-team/non-governance features. Upgrade pitch shifts to "team collaboration + enterprise governance"
- Solopreneur onboarding checklist items: Claude's discretion — pick the best 5 items that showcase the full capability set for a one-person business

### Tool Rename Strategy
- **Approach:** Rename only — no removal, no deprecation notices, no behavior changes
- **7 tools to rename:**
  - `manage_hubspot` → `hubspot_setup_guide`
  - `run_security_audit` → `security_checklist`
  - `deploy_container` → `container_deployment_guide`
  - `architect_cloud_solution` → `cloud_architecture_guide`
  - `perform_seo_audit` → `seo_fundamentals_guide`
  - `generate_product_roadmap` → `product_roadmap_guide`
  - `design_rag_pipeline` → `rag_architecture_guide`
- All 7 live in `app/agents/enhanced_tools.py` — rename the function definitions and their docstrings
- Keep renamed tools in their existing agent groups (STRATEGIC_TOOLS, SALES_TOOLS, etc.) — don't create a separate KNOWLEDGE_TOOLS group
- Update `tool_registry.py` imports and references
- Update agent instruction strings in `app/agents/sales/agent.py`, `app/agents/operations/agent.py`, `app/agents/strategic/agent.py`, `app/agents/marketing/agent.py` to use honest language ("Get security checklist guidance" instead of "Run security checks")
- **HubSpot guide fate when real tools arrive (Phase 42):** Claude's discretion — decide based on whether connected/unconnected users need different tool sets

### Behavioral Update
- **Tone shift:** Elevate solopreneur from "scrappy saver" to "capable business operator"
- **Planning horizon:** Extend from 7-14 days to 30 days
- **Core objectives:** Shift from "save time, ship fast, protect cash" to "run entire business confidently, automate everything possible, full business visibility"
- **Response style:** More comprehensive output — still action-first but not minimalist
- **KPIs:** Expand from (cash collected, weekly pipeline, content consistency) to include business health metrics (revenue trend, active workflows, compliance score)
- **Approval posture:** Claude's discretion — balance minimal gates for routine work with appropriate escalation for financial transactions and compliance decisions
- **Scope:** Update all 11 solopreneur behavioral instruction entries for a unified "capable operator" experience
- **Files affected:**
  - `app/personas/policy_registry.py` — update solopreneur PersonaPolicy (summary, core_objectives, planning_horizon, response_style, output_contract, default_kpis)
  - `app/personas/behavioral_instructions.py` — update all 11 solopreneur entries
  - `frontend/src/components/personas/personaShellConfig.ts` — update solopreneur KPI labels
  - `frontend/src/services/onboarding.ts` — update solopreneur checklist items if needed

### Org Chart Display
- **Approach:** Single list with [ACTION]/[GUIDE] badges per tool
- **Data source:** Backend `/org-chart` endpoint adds a `kind` field per tool: `"action"` or `"knowledge"`
- **Classification logic:** Tools that call `skills_registry.use_skill()` are `"knowledge"`, all others are `"action"`
- **Badge styling:** Claude's discretion — choose approach that fits existing design system (StatusBadge reuse or simple tags)
- **Files affected:**
  - Backend endpoint that serves org chart data — add `kind` field
  - Frontend org chart inspector component — render badges

### Claude's Discretion
- Solopreneur onboarding checklist item selection
- HubSpot guide tool coexistence strategy when real CRM tools arrive
- Approval posture fine-tuning for solopreneur
- Org chart badge styling approach
- Exact wording of updated behavioral instructions (guided by "capable operator" tone)
- Exact KPI set expansion (guided by "revenue trend, active workflows, compliance score" direction)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/config/feature_gating.py`: `FEATURE_ACCESS` dict with `min_tier` per feature — direct edit target
- `frontend/src/config/featureGating.ts`: Mirror of backend with `FeatureKey` type and `FEATURE_ACCESS` record
- `app/agents/enhanced_tools.py`: All 7 misleading tools defined here as functions calling `skills_registry.use_skill()`
- `app/agents/tools/tool_registry.py`: Central import registry grouping tools by agent domain
- `app/personas/policy_registry.py`: `_PERSONA_POLICIES["solopreneur"]` PersonaPolicy dataclass
- `app/personas/behavioral_instructions.py`: 44-entry dict with `(agent_name, persona_key)` keys
- `frontend/src/components/personas/personaShellConfig.ts`: KPI labels per persona
- `frontend/src/app/dashboard/billing/page.tsx`: Tier comparison table with FEATURE_ROWS

### Established Patterns
- Feature gating uses `TIER_ORDER` index comparison — `min_tier: "solopreneur"` means all tiers get access
- Behavioral instructions are pure strings injected via `build_persona_policy_block()`
- Org chart data served from a FastAPI endpoint, rendered by ReactFlow in frontend
- StatusBadge component exists for semantic colored badges

### Integration Points
- `app/middleware/feature_gate.py`: `require_feature()` dependency — no change needed, reads from `FEATURE_ACCESS`
- `frontend/src/components/dashboard/GatedPage.tsx`: Reads `isFeatureAllowed()` — automatically reflects new gating
- `frontend/src/app/(personas)/solopreneur/page.tsx`: Persona dashboard — quick actions may need update
- `frontend/src/components/personas/personaWidgetDefaults.ts`: Default widget sections may need update

</code_context>

<specifics>
## Specific Ideas

- "Solopreneur is not a limited persona — it's a single-user category that should have full access to real value features"
- "The difference between solopreneur and other personas is team features, not capability restrictions"
- "A solopreneur should be able to run their one-person business or company without limitations"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 38-solopreneur-unlock-tool-honesty*
*Context gathered: 2026-04-04*
