# Phase 38: Solopreneur Unlock & Tool Honesty - Research

**Researched:** 2026-04-04
**Domain:** Configuration editing, persona behavioral tuning, tool naming, frontend gating
**Confidence:** HIGH

## Summary

Phase 38 is a configuration-heavy phase with zero new features. Every change involves editing existing dictionaries, string literals, and frontend data structures. The codebase is well-organized with single sources of truth for each concern: `feature_gating.py` / `featureGating.ts` for tier access, `enhanced_tools.py` for tool definitions, `tool_registry.py` for tool-to-agent mapping, `behavioral_instructions.py` and `policy_registry.py` for persona behavior, and clearly identified frontend files for billing, KPIs, onboarding, and org chart display.

The 7 tools to rename all live in `enhanced_tools.py` and call `skills_registry.use_skill()` -- this is the exact classification signal the org chart needs for [ACTION] vs [GUIDE] badges. The feature gating system uses a simple `TIER_ORDER` index comparison, so changing `min_tier` to `"solopreneur"` (index 0) automatically grants access to all tiers. The existing test suite has strong behavioral instruction tests (48 combination coverage) and policy registry tests that will need updating.

**Primary recommendation:** Execute in 3 waves: (1) feature gating + billing page, (2) tool renames with full import chain updates, (3) behavioral/KPI/onboarding/org-chart updates. Each wave is independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Solopreneur gets full access to: workflows, custom-workflows, sales, reports, approvals, compliance, finance-forecasting
- Only **two** features remain restricted for solopreneur: `teams` and `governance`
- Backend `feature_gating.py`: change `min_tier` to `"solopreneur"` for workflows, sales, reports, approvals, compliance, finance-forecasting, custom-workflows
- Frontend `featureGating.ts`: mirror all backend changes
- Backend `feature_gate.py` middleware: no logic change needed
- **7 tools to rename** (rename only -- no removal, no deprecation, no behavior changes):
  - `manage_hubspot` -> `hubspot_setup_guide`
  - `run_security_audit` -> `security_checklist`
  - `deploy_container` -> `container_deployment_guide`
  - `architect_cloud_solution` -> `cloud_architecture_guide`
  - `perform_seo_audit` -> `seo_fundamentals_guide`
  - `generate_product_roadmap` -> `product_roadmap_guide`
  - `design_rag_pipeline` -> `rag_architecture_guide`
- Keep renamed tools in their existing agent groups -- no separate KNOWLEDGE_TOOLS group
- Update agent instruction strings to use honest language
- Tone shift: elevate solopreneur from "scrappy saver" to "capable business operator"
- Planning horizon: extend from 7-14 days to 30 days
- Core objectives shift to "run entire business confidently, automate everything possible, full business visibility"
- Org chart: single list with [ACTION]/[GUIDE] badges per tool
- Classification logic: tools that call `skills_registry.use_skill()` are "knowledge", all others are "action"
- Backend `/org-chart` endpoint adds a `kind` field per tool
- Billing page: update comparison table to show solopreneur with checkmarks for all non-team/non-governance features

### Claude's Discretion
- Solopreneur onboarding checklist item selection (best 5 items showcasing full capability set)
- HubSpot guide tool coexistence strategy when real CRM tools arrive
- Approval posture fine-tuning for solopreneur
- Org chart badge styling approach
- Exact wording of updated behavioral instructions (guided by "capable operator" tone)
- Exact KPI set expansion (guided by "revenue trend, active workflows, compliance score" direction)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SOLO-01 | Solopreneur has full access to workflows, dynamic workflow generator, and workflow templates | Feature gating `min_tier` change in `feature_gating.py` and `featureGating.ts` -- both `workflows` and `custom-workflows` keys |
| SOLO-02 | Solopreneur has full access to approvals, sales pipeline, and reports | Feature gating `min_tier` change for `approvals`, `sales`, `reports` keys |
| SOLO-03 | Solopreneur has full access to compliance suite and financial forecasting | Feature gating `min_tier` change for `compliance`, `finance-forecasting` keys |
| SOLO-04 | Solopreneur behavioral instructions updated to reflect full-featured single-user | `policy_registry.py` PersonaPolicy + all 11 entries in `behavioral_instructions.py` + `personaShellConfig.ts` KPIs |
| SOLO-05 | Only team_management, shared_workspaces, and team_analytics remain restricted | Verified: `teams` (min_tier: startup) and `governance` (min_tier: enterprise) stay unchanged |
| SOLO-06 | Frontend feature gating mirrors backend -- no upgrade prompts for non-team features | `featureGating.ts` FEATURE_ACCESS + billing page `FEATURE_ROWS` + GatedPage auto-reflects |
| TOOL-01 | `manage_hubspot` renamed to `hubspot_setup_guide` | enhanced_tools.py L238, tool_registry.py L114/L128, sales/agent.py L14/L86/L147 |
| TOOL-02 | `run_security_audit` renamed to `security_checklist` | enhanced_tools.py L135, tool_registry.py L160/L179, operations/agent.py L18-21/L61/L164 |
| TOOL-03 | `deploy_container` renamed to `container_deployment_guide` | enhanced_tools.py L159, tool_registry.py L161/L180, operations/agent.py L20/L63/L165 |
| TOOL-04 | `architect_cloud_solution` renamed to `cloud_architecture_guide` | enhanced_tools.py L177, tool_registry.py L160/L181, operations/agent.py L18/L62/L166 |
| TOOL-05 | `perform_seo_audit` renamed to `seo_fundamentals_guide` | enhanced_tools.py L262, tool_registry.py L134/L152, marketing/agent.py L19/L213/L224 |
| TOOL-06 | `generate_product_roadmap` renamed to `product_roadmap_guide` | enhanced_tools.py L283, tool_registry.py L93/L108, strategic/agent.py L14/L130/L267 |
| TOOL-07 | `design_rag_pipeline` renamed to `rag_architecture_guide` | enhanced_tools.py L217, tool_registry.py L260/L271, data/agent.py L21/L210 |
| TOOL-08 | Org chart separates "Tools" (actions) from "Knowledge" (frameworks) | Backend: `app/routers/org.py` OrgNode model + `_get_tool_list()`. Frontend: `AgentInspector.tsx` tool list rendering |
</phase_requirements>

## Architecture Patterns

### Feature Gating Change Pattern

The feature gating system uses tier-index comparison. `TIER_ORDER = ["solopreneur", "startup", "sme", "enterprise"]` where index 0 is lowest. Setting `min_tier: "solopreneur"` (index 0) means ALL tiers pass the `>=` check automatically.

**Backend (`app/config/feature_gating.py`):**
```python
# BEFORE: min_tier: "startup" or "sme" or "enterprise"
# AFTER:  min_tier: "solopreneur"

# 7 entries to change:
"workflows":         { "min_tier": "solopreneur" },   # was "startup"
"sales":             { "min_tier": "solopreneur" },   # was "startup"
"reports":           { "min_tier": "solopreneur" },   # was "startup"
"approvals":         { "min_tier": "solopreneur" },   # was "startup"
"compliance":        { "min_tier": "solopreneur" },   # was "sme"
"finance-forecasting": { "min_tier": "solopreneur" }, # was "sme"
"custom-workflows":  { "min_tier": "solopreneur" },   # was "enterprise"

# 2 entries UNCHANGED:
"governance":        { "min_tier": "enterprise" },    # stays
"teams":             { "min_tier": "startup" },       # stays
```

**Frontend (`frontend/src/config/featureGating.ts`):** Exact mirror -- change `minTier` for same 7 keys. Also update the doc-comment access matrix at top of file.

**Middleware (`app/middleware/feature_gate.py`):** No changes needed -- it calls `is_feature_allowed()` which uses the updated `FEATURE_ACCESS` dict.

**Frontend `GatedPage` / `useFeatureGate`:** No changes needed -- they call `isFeatureAllowed()` from `featureGating.ts`.

### Tool Rename Pattern

Each of the 7 tools requires coordinated changes across exactly 4 locations:

| # | Location | What Changes |
|---|----------|-------------|
| 1 | `app/agents/enhanced_tools.py` | Function name + docstring |
| 2 | `app/agents/tools/tool_registry.py` | Import name + list reference |
| 3 | Agent `agent.py` file | Import name + instruction string reference |
| 4 | Agent `agent.py` file | Tool list reference (if separate from tool_registry) |

**Complete rename chain for each tool:**

**1. `manage_hubspot` -> `hubspot_setup_guide`**
- `enhanced_tools.py` L238: `def manage_hubspot(` -> `def hubspot_setup_guide(`
- `enhanced_tools.py` L239: Update docstring from "Manage HubSpot CRM data" to "Get HubSpot CRM setup guidance and best practices"
- `tool_registry.py` L114: `from app.agents.enhanced_tools import manage_hubspot` -> `import hubspot_setup_guide`
- `tool_registry.py` L128: `manage_hubspot,` -> `hubspot_setup_guide,`
- `sales/agent.py` L14: `from app.agents.enhanced_tools import manage_hubspot` -> `import hubspot_setup_guide`
- `sales/agent.py` L86: instruction string "Manage HubSpot CRM data using 'manage_hubspot'" -> "Get HubSpot CRM setup guidance using 'hubspot_setup_guide'"
- `sales/agent.py` L147: `manage_hubspot,` -> `hubspot_setup_guide,`

**2. `run_security_audit` -> `security_checklist`**
- `enhanced_tools.py` L135: `def run_security_audit(` -> `def security_checklist(`
- `enhanced_tools.py` L136: Update docstring
- `tool_registry.py` L162: import + L179: reference
- `operations/agent.py` L21: import, L61: instruction, L164: tools list

**3. `deploy_container` -> `container_deployment_guide`**
- `enhanced_tools.py` L159: function name + docstring
- `tool_registry.py` L161/L180
- `operations/agent.py` L20/L63/L165

**4. `architect_cloud_solution` -> `cloud_architecture_guide`**
- `enhanced_tools.py` L177: function name + docstring
- `tool_registry.py` L160/L181
- `operations/agent.py` L18/L62/L166

**5. `perform_seo_audit` -> `seo_fundamentals_guide`**
- `enhanced_tools.py` L262: function name + docstring
- `tool_registry.py` L134/L152
- `marketing/agent.py` L19: import, L224: SEO sub-agent instruction, L213: SEO sub-agent tools list

**6. `generate_product_roadmap` -> `product_roadmap_guide`**
- `enhanced_tools.py` L283: function name + docstring
- `tool_registry.py` L93/L108
- `strategic/agent.py` L14: import, L130: instruction, L267: tools list

**7. `design_rag_pipeline` -> `rag_architecture_guide`**
- `enhanced_tools.py` L217: function name + docstring
- `tool_registry.py` L260/L271
- `data/agent.py` L21: import, L210: tools list

### Tool Kind Classification for Org Chart

The CONTEXT.md specifies: "Tools that call `skills_registry.use_skill()` are `knowledge`, all others are `action`."

**Implementation approach in `app/routers/org.py`:**

The current `_get_tool_list()` returns `list[str]`. We need to change it to return tool metadata with `kind` field.

**Classification method:** Inspect each tool's source module. All 7 renamed tools (and the existing `use_skill`, `generate_remotion_video`, `generate_react_component`, `build_portfolio`) call `skills_registry.use_skill()`. The simplest approach: maintain a set of known knowledge tool names in org.py (or detect at introspection time by checking if the function's source contains `skills_registry`).

**Practical approach:** Since the tool names are known at build time, a static set is simpler and more reliable:
```python
_KNOWLEDGE_TOOLS = {
    "hubspot_setup_guide", "security_checklist", "container_deployment_guide",
    "cloud_architecture_guide", "seo_fundamentals_guide", "product_roadmap_guide",
    "rag_architecture_guide", "generate_react_component", "build_portfolio",
    "generate_remotion_video", "use_skill", "list_available_skills",
}
```

**OrgNode model change:**
```python
class OrgNode(BaseModel):
    # ... existing fields ...
    tools: list[dict[str, str]] = []  # Changed from list[str]
    # Each tool: {"name": "tool_name", "kind": "action" | "knowledge"}
```

**CAUTION:** This is a breaking API change for the frontend. The `AgentInspector.tsx` and `OrgChart.tsx` expect `tools: string[]`. Must update both backend response shape and frontend consumption.

**Alternative (non-breaking):** Add a parallel `tool_kinds: dict[str, str]` field alongside the existing `tools: list[str]`. Frontend reads from both. This is safer and simpler.

### Recommended Project Structure (files to edit)

```
app/
  config/
    feature_gating.py            # SOLO-01,02,03,05: min_tier changes
  agents/
    enhanced_tools.py            # TOOL-01..07: rename 7 functions
    tools/
      tool_registry.py           # TOOL-01..07: update imports/references
    sales/agent.py               # TOOL-01: rename import + instruction
    operations/agent.py          # TOOL-02,03,04: rename imports + instructions
    marketing/agent.py           # TOOL-05: rename import + instruction
    strategic/agent.py           # TOOL-06: rename import + instruction
    data/agent.py                # TOOL-07: rename import + instruction
  personas/
    policy_registry.py           # SOLO-04: update solopreneur PersonaPolicy
    behavioral_instructions.py   # SOLO-04: update 11 solopreneur entries
  routers/
    org.py                       # TOOL-08: add kind field to tool list

frontend/src/
  config/
    featureGating.ts             # SOLO-06: mirror backend min_tier changes
  app/dashboard/billing/
    page.tsx                     # SOLO-06: update FEATURE_ROWS checkmarks
  components/
    personas/
      personaShellConfig.ts      # SOLO-04: update solopreneur KPI labels
    org-chart/
      AgentInspector.tsx         # TOOL-08: render [ACTION]/[GUIDE] badges
    dashboard/
      OnboardingChecklist.tsx    # SOLO-04: update solopreneur checklist items
```

### Anti-Patterns to Avoid
- **Partial gating update:** Backend and frontend MUST stay in sync. If backend says solopreneur can access workflows but frontend still shows upgrade prompt, users see broken state.
- **Renaming function but not docstring:** The LLM reads docstrings to understand tool purpose. A function named `security_checklist` with docstring "Run a security audit" defeats the purpose.
- **Breaking org chart API contract:** Changing `tools: list[str]` to `tools: list[dict]` will crash the frontend. Use additive approach (add `tool_kinds` field).
- **Forgetting tool_registry.py cache:** The `_tools_cache` in tool_registry.py caches tool lists. Renames work fine since cache is built lazily at import time -- but tests that import both old and new names may fail.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool kind classification | Runtime source inspection | Static `_KNOWLEDGE_TOOLS` set | Reliable, no import-time overhead, easy to maintain |
| Badge styling | Custom badge component | Existing `StatusBadge` component | Already has color mapping, `variant='dot'` mode, handles unknown statuses |
| Feature gating logic | Custom middleware changes | Existing `is_feature_allowed()` + `isFeatureAllowed()` | Changing min_tier is sufficient; the comparison logic handles it |

## Common Pitfalls

### Pitfall 1: Stale Tool Registry Cache in Tests
**What goes wrong:** Tool registry caches tool lists in `_tools_cache`. If tests import tools under old names and then exercise the new names, the cache may serve stale data.
**Why it happens:** `_tools_cache` is a module-level dict populated on first `get_tools_for_agent()` call.
**How to avoid:** Call `clear_cache()` from `tool_registry` in test setup. Existing tests likely don't hit this since they mock at higher levels.
**Warning signs:** Tests pass individually but fail when run together.

### Pitfall 2: Frontend Type Breakage from Org Chart API Change
**What goes wrong:** Changing the `tools` field from `list[str]` to `list[dict]` in `OrgNode` breaks TypeScript type expectations in `AgentInspector.tsx`.
**Why it happens:** The `OrgNodeData` interface defines `tools: string[]`.
**How to avoid:** Add a NEW field `tool_kinds: Record<string, string>` alongside existing `tools: string[]`. Frontend reads `tool_kinds[toolName]` for badge rendering.
**Warning signs:** TypeScript compilation errors, org chart tools section blank.

### Pitfall 3: Test Assertions on Exact Behavioral Strings
**What goes wrong:** Existing tests assert specific words in behavioral instructions (e.g., "cash" in solopreneur financial, "portfolio" NOT in solopreneur). Rewriting solopreneur instructions may break these.
**Why it happens:** `test_persona_behavioral_instructions.py` has exact word checks.
**How to avoid:** Update test assertions alongside instruction text changes. The tests at `tests/unit/test_persona_behavioral_instructions.py` and `tests/unit/test_persona_policy_registry.py` must be updated.
**Warning signs:** `test_solopreneur_financial_agent_contains_cash_flow()` failing because new instructions mention "revenue" instead of just "cash".

### Pitfall 4: Billing Page FEATURE_ROWS Hardcoded Booleans
**What goes wrong:** The billing page `FEATURE_ROWS` array has hardcoded `solopreneur: false` for features that are now unlocked.
**Why it happens:** The billing page uses its own static data, NOT the `featureGating.ts` config.
**How to avoid:** Update the `FEATURE_ROWS` array in `frontend/src/app/dashboard/billing/page.tsx` lines 69-80 to set `solopreneur: true` for all newly unlocked features.
**Warning signs:** Billing page shows dashes for solopreneur features that should have checkmarks.

### Pitfall 5: Agent Instruction Strings Reference Old Tool Names
**What goes wrong:** Agent instruction strings that reference tools by name (e.g., "Run security checks on systems or code using 'run_security_audit'") become stale after rename.
**Why it happens:** The LLM reads these instruction strings to know which tools to call. If the instruction says `run_security_audit` but the tool is now `security_checklist`, the LLM may fail to find it.
**How to avoid:** Search all instruction strings in the 5 agent files for old tool names. The grep results show exact line numbers for each reference.
**Warning signs:** Agent tries to call a tool that no longer exists.

### Pitfall 6: Solopreneur Quick Actions Still Link to Gated Pages
**What goes wrong:** The solopreneur shell config (`personaShellConfig.ts`) already has a "Sales Pipeline" quick action pointing to `/dashboard/sales`. Currently this is gated for solopreneur. After ungating, the link works -- but if we missed updating the sidebar navigation, the user can access the page via quick action but not find it in the nav.
**How to avoid:** Verify sidebar navigation also respects `isFeatureAllowed()` and will automatically show the new links. The sidebar likely already uses the gating config -- verify this.
**Warning signs:** Users can reach pages via quick actions but not sidebar.

## Code Examples

### Feature Gating Backend Change (verified from source)
```python
# app/config/feature_gating.py - FEATURE_ACCESS dict
# Change min_tier for these 7 entries:
"workflows":          {"label": "Workflow Engine",        "description": "...", "min_tier": "solopreneur"},
"sales":              {"label": "Sales Pipeline & CRM",   "description": "...", "min_tier": "solopreneur"},
"reports":            {"label": "Reports",                "description": "...", "min_tier": "solopreneur"},
"approvals":          {"label": "Approvals",              "description": "...", "min_tier": "solopreneur"},
"compliance":         {"label": "Compliance Suite",       "description": "...", "min_tier": "solopreneur"},
"finance-forecasting":{"label": "Financial Forecasting",  "description": "...", "min_tier": "solopreneur"},
"custom-workflows":   {"label": "Custom Workflows",       "description": "...", "min_tier": "solopreneur"},
```

### Tool Rename Example (verified from source)
```python
# app/agents/enhanced_tools.py
# BEFORE:
def manage_hubspot(action: str, data: dict = None) -> dict:
    """Manage HubSpot CRM data."""

# AFTER:
def hubspot_setup_guide(action: str, data: dict = None) -> dict:
    """Get HubSpot CRM setup guidance and integration best practices."""
```

### Org Chart Tool Kind Addition (verified from source)
```python
# app/routers/org.py - Add alongside existing OrgNode fields
class OrgNode(BaseModel):
    # ... existing fields unchanged ...
    tools: list[str] = []           # Keep as-is (backward compat)
    tool_kinds: dict[str, str] = {} # NEW: {"tool_name": "action" | "knowledge"}

# In _get_tool_list, also return kinds:
_KNOWLEDGE_TOOLS = {
    "hubspot_setup_guide", "security_checklist", "container_deployment_guide",
    "cloud_architecture_guide", "seo_fundamentals_guide", "product_roadmap_guide",
    "rag_architecture_guide", "use_skill", "list_available_skills",
    "generate_react_component", "build_portfolio", "generate_remotion_video",
}

def _get_tool_list_with_kinds(agent) -> tuple[list[str], dict[str, str]]:
    tools = _get_tool_list(agent)  # existing function
    kinds = {t: ("knowledge" if t in _KNOWLEDGE_TOOLS else "action") for t in tools}
    return tools, kinds
```

### Frontend Badge Rendering (verified StatusBadge exists)
```tsx
// AgentInspector.tsx - In the tools list
{agent.tools.map((tool) => {
    const kind = agent.tool_kinds?.[tool];
    return (
        <li key={tool} className="flex items-center gap-2 ...">
            <Wrench className="h-3.5 w-3.5 shrink-0 text-slate-500" />
            <span className="font-mono text-xs">{tool}</span>
            {kind && (
                <span className={`ml-auto rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                    kind === 'action'
                        ? 'bg-blue-50 text-blue-600'
                        : 'bg-amber-50 text-amber-600'
                }`}>
                    {kind === 'action' ? 'ACTION' : 'GUIDE'}
                </span>
            )}
        </li>
    );
})}
```

### Behavioral Instructions Update Pattern (verified from source)
```python
# app/personas/policy_registry.py - solopreneur PersonaPolicy
"solopreneur": PersonaPolicy(
    key="solopreneur",
    label="Solopreneur",
    summary="Full-featured single-user business operator with access to every non-team capability.",
    core_objectives=(
        "Run entire business confidently with full AI support",
        "Automate everything possible to maximize personal leverage",
        "Maintain full business visibility across revenue, operations, and compliance",
    ),
    default_kpis=(
        "revenue trend",
        "active workflows",
        "compliance score",
    ),
    planning_horizon="Bias to the next 30 days with weekly milestones.",
    response_style="Be action-first but comprehensive. Provide complete analysis, not just quick tips.",
    # ... update remaining fields to "capable operator" tone
),
```

## Billing Page FEATURE_ROWS Update

Current state (line 69-80 of `frontend/src/app/dashboard/billing/page.tsx`):
```typescript
const FEATURE_ROWS: FeatureRow[] = [
    { label: 'AI Agents (All 11)',       solopreneur: true,  ... },
    { label: 'Brain Dump & Action Plans', solopreneur: true,  ... },
    { label: 'Invoice Generation',        solopreneur: true,  ... },
    { label: 'Social Publishing',         solopreneur: true,  ... },
    { label: 'Workflow Engine',           solopreneur: false, ... }, // -> true
    { label: 'Sales Pipeline & CRM',     solopreneur: false, ... }, // -> true
    { label: 'Compliance Suite',          solopreneur: false, ... }, // -> true
    { label: 'Financial Forecasting',     solopreneur: false, ... }, // -> true
    { label: 'Custom Workflows',          solopreneur: false, ... }, // -> true
    { label: 'SSO & Governance',          solopreneur: false, ... }, // stays false
];
```

**Also needed:** Add a `Team Workspace` row (currently missing from FEATURE_ROWS) showing `solopreneur: false` to make the team restriction visible. And update the upgrade pitch text to emphasize "team collaboration + enterprise governance" as the upsell.

## Onboarding Checklist Items

Current solopreneur items (from `OnboardingChecklist.tsx` lines 20-26):
1. Map your revenue strategy
2. Do a brain dump
3. Plan your week
4. Run your first workflow
5. Create your first content piece

These should be updated to reflect the full capability set. Recommended new items showcasing unlocked features:
1. **Run your first workflow** - Automate a repetitive business process (showcases SOLO-01)
2. **Set up your sales pipeline** - Track deals and manage your funnel (showcases SOLO-02)
3. **Do a brain dump** - Get all your ideas organized into action plans
4. **Run a compliance check** - Ensure your business meets key requirements (showcases SOLO-03)
5. **Create a financial forecast** - Project your revenue and plan ahead (showcases SOLO-03)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `pyproject.toml` [tool.pytest.ini_options], `frontend/vitest.config.ts` |
| Quick run command | `uv run pytest tests/unit/test_persona_behavioral_instructions.py tests/unit/test_persona_policy_registry.py tests/unit/test_persona_equalization.py -x` |
| Full suite command | `make test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOLO-01 | Solopreneur can access workflows + custom-workflows | unit | `uv run pytest tests/unit/test_solopreneur_unlock.py::test_solopreneur_workflows_access -x` | Wave 0 |
| SOLO-02 | Solopreneur can access approvals, sales, reports | unit | `uv run pytest tests/unit/test_solopreneur_unlock.py::test_solopreneur_sales_reports_access -x` | Wave 0 |
| SOLO-03 | Solopreneur can access compliance + finance-forecasting | unit | `uv run pytest tests/unit/test_solopreneur_unlock.py::test_solopreneur_compliance_finance_access -x` | Wave 0 |
| SOLO-04 | Behavioral instructions updated for capable operator | unit | `uv run pytest tests/unit/test_persona_behavioral_instructions.py -x` | Exists (update) |
| SOLO-05 | Only teams + governance remain restricted | unit | `uv run pytest tests/unit/test_solopreneur_unlock.py::test_solopreneur_restricted_features -x` | Wave 0 |
| SOLO-06 | Frontend mirrors backend gating | manual-only | Visual check: solopreneur sees no upgrade prompts | N/A |
| TOOL-01 | manage_hubspot renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_hubspot_renamed -x` | Wave 0 |
| TOOL-02 | run_security_audit renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_security_renamed -x` | Wave 0 |
| TOOL-03 | deploy_container renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_container_renamed -x` | Wave 0 |
| TOOL-04 | architect_cloud_solution renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_cloud_renamed -x` | Wave 0 |
| TOOL-05 | perform_seo_audit renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_seo_renamed -x` | Wave 0 |
| TOOL-06 | generate_product_roadmap renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_roadmap_renamed -x` | Wave 0 |
| TOOL-07 | design_rag_pipeline renamed | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_rag_renamed -x` | Wave 0 |
| TOOL-08 | Org chart shows action/knowledge badges | unit | `uv run pytest tests/unit/test_tool_honesty.py::test_org_chart_tool_kinds -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_solopreneur_unlock.py tests/unit/test_tool_honesty.py tests/unit/test_persona_behavioral_instructions.py tests/unit/test_persona_policy_registry.py tests/unit/test_persona_equalization.py -x`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_solopreneur_unlock.py` -- covers SOLO-01, SOLO-02, SOLO-03, SOLO-05 (feature gating assertions)
- [ ] `tests/unit/test_tool_honesty.py` -- covers TOOL-01..07 (renamed tools importable, old names gone), TOOL-08 (org chart tool_kinds)
- [ ] Update `tests/unit/test_persona_behavioral_instructions.py` -- update assertions for new solopreneur wording
- [ ] Update `tests/unit/test_persona_policy_registry.py` -- update assertions for new solopreneur policy

## Complete File Edit Manifest

This is the exhaustive list of every file that needs editing, organized by wave:

### Wave 1: Feature Gating + Billing (SOLO-01,02,03,05,06)

| File | Lines | Change |
|------|-------|--------|
| `app/config/feature_gating.py` | 20,26,32,37,42,48,52 | Change `min_tier` to `"solopreneur"` for 7 features |
| `frontend/src/config/featureGating.ts` | 93,99,107,113,119,127,131 | Change `minTier` to `'solopreneur'` for 7 features; update doc-comment matrix |
| `frontend/src/app/dashboard/billing/page.tsx` | 69-80 | Set `solopreneur: true` for 5 more features in FEATURE_ROWS; add Team Workspace row |

### Wave 2: Tool Renames (TOOL-01..07)

| File | What Changes |
|------|-------------|
| `app/agents/enhanced_tools.py` | Rename 7 function definitions + update 7 docstrings |
| `app/agents/tools/tool_registry.py` | Update 7 import statements + 7 list references |
| `app/agents/sales/agent.py` | 1 import, 1 instruction string ref, 1 tools list ref |
| `app/agents/operations/agent.py` | 3 imports, 3 instruction string refs, 3 tools list refs |
| `app/agents/marketing/agent.py` | 1 import, 1 instruction string ref, 1 tools list ref |
| `app/agents/strategic/agent.py` | 1 import, 1 instruction string ref, 1 tools list ref |
| `app/agents/data/agent.py` | 1 import, 1 tools list ref (no instruction string ref -- data agent doesn't mention it by name in instructions) |

### Wave 3: Behavioral + KPIs + Onboarding + Org Chart (SOLO-04, TOOL-08)

| File | What Changes |
|------|-------------|
| `app/personas/policy_registry.py` | Update solopreneur PersonaPolicy (summary, core_objectives, default_kpis, planning_horizon, response_style, output_contract, approval_posture) |
| `app/personas/behavioral_instructions.py` | Rewrite all 11 solopreneur entries (1 per agent in `_BEHAVIORAL_INSTRUCTIONS`) |
| `frontend/src/components/personas/personaShellConfig.ts` | Update solopreneur `tagline`, `description`, `kpiLabels` |
| `frontend/src/components/dashboard/OnboardingChecklist.tsx` | Replace 5 solopreneur checklist items |
| `app/routers/org.py` | Add `tool_kinds` field to OrgNode, update `_get_tool_list` to also return kinds |
| `frontend/src/components/org-chart/AgentInspector.tsx` | Add `tool_kinds` to OrgNodeData interface, render [ACTION]/[GUIDE] badges |

### Tests (all waves)

| File | What Changes |
|------|-------------|
| `tests/unit/test_solopreneur_unlock.py` | NEW: feature gating assertions |
| `tests/unit/test_tool_honesty.py` | NEW: renamed tool importability + org chart kind field |
| `tests/unit/test_persona_behavioral_instructions.py` | UPDATE: adjust word-match assertions for new solopreneur text |
| `tests/unit/test_persona_policy_registry.py` | UPDATE: adjust KPI/objective assertions for new solopreneur policy |

## Open Questions

1. **Sidebar navigation auto-update**
   - What we know: GatedPage and useFeatureGate read from featureGating.ts config
   - What's unclear: Whether sidebar links for workflows, sales, etc. also use isFeatureAllowed or have separate visibility logic
   - Recommendation: Grep for sidebar navigation component during implementation and verify it uses featureGating

2. **Solopreneur personaWidgetDefaults update**
   - What we know: Widget defaults include `kanban_board` and `campaign_hub` for solopreneur. Section titles are "Revenue & Pipeline" and "Content & Marketing"
   - What's unclear: Whether to add workflow-related widgets now that workflows are unlocked
   - Recommendation: This is a nice-to-have; the current defaults are fine since they already show revenue and campaign data. Can update in a future polish pass.

## Sources

### Primary (HIGH confidence)
- `app/config/feature_gating.py` -- read directly, verified TIER_ORDER and FEATURE_ACCESS structure
- `app/agents/enhanced_tools.py` -- read directly, verified all 7 tool definitions call skills_registry.use_skill()
- `app/agents/tools/tool_registry.py` -- read directly, mapped all import chains for 7 tools
- `app/personas/behavioral_instructions.py` -- read directly, confirmed 12 agents x 4 personas = 48 entries, 11 solopreneur entries (DataReportingAgent is 12th agent)
- `app/personas/policy_registry.py` -- read directly, confirmed PersonaPolicy dataclass fields
- `frontend/src/config/featureGating.ts` -- read directly, confirmed mirror structure
- `frontend/src/app/dashboard/billing/page.tsx` -- read directly, confirmed FEATURE_ROWS hardcoded booleans
- `frontend/src/components/org-chart/AgentInspector.tsx` -- read directly, confirmed tools: string[] type
- `app/routers/org.py` -- read directly, confirmed OrgNode model and _get_tool_list helper
- All 5 agent files (sales, operations, marketing, strategic, data) -- read directly
- All test files -- read directly

### Secondary (MEDIUM confidence)
- Sidebar navigation behavior inferred from GatedPage pattern -- needs verification during implementation

## Metadata

**Confidence breakdown:**
- Feature gating changes: HIGH -- exact line numbers identified, simple dict value changes
- Tool renames: HIGH -- complete import chain mapped with grep, every reference found
- Behavioral instructions: HIGH -- structure verified, all 11 entries confirmed
- Org chart badge: HIGH -- backend model and frontend component both read, additive approach identified
- Billing page: HIGH -- FEATURE_ROWS structure confirmed, exact booleans identified
- Sidebar behavior: MEDIUM -- inferred from architecture, not directly verified

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable -- config files don't change rapidly)
