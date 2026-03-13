# Plan: Phase 1 - Milestone 2 (Persona-Aware Orchestration)

**Objective:** Convert persona handling from lightweight prompt decoration into a typed orchestration policy that changes how the Executive Agent and top-level specialists plan, route, and respond for solopreneur, startup, SME, and enterprise users.

## 1. Persona Policy Registry
**Problem:** Persona is currently represented as a short guidance block in `app/services/user_agent_factory.py`, which is too weak to drive real behavior differences across agents.

**Strategy:**
- Introduce a typed persona policy registry as the single source of truth for the four supported personas.
- Store policy fields that actually change behavior, not just tone:
  - core objectives
  - default KPIs
  - budget sensitivity
  - risk posture
  - desired response style
  - approval posture
  - preferred agent bundle
  - anti-patterns
  - routing priorities
- Keep the existing persona enum (`solopreneur`, `startup`, `sme`, `enterprise`) as the top-level key, but add optional derived modifiers for future expansion:
  - role
  - team maturity
  - compliance burden
  - technical sophistication
- Replace hard-coded `_PERSONA_GUIDES` text with a builder that renders a structured prompt block from the registry.

**Implementation shape:**
- Add `app/personas/models.py` for typed policy models.
- Add `app/personas/policy_registry.py` for persona definitions and lookup helpers.
- Update `app/services/user_agent_factory.py` to consume the registry instead of inline string constants.

**Files to modify:**
- `app/services/user_agent_factory.py`
- `app/services/user_onboarding_service.py`
- `app/models/profile.py` only if new derived fields are persisted now

## 2. Prompt Fragment Composition
**Problem:** Top-level agent prompts are mostly function-first. Even though personalization is injected at runtime, persona behavior is not expressed in each specialist's operating rules.

**Strategy:**
- Introduce agent-specific persona prompt fragments for every top-level production agent:
  - Executive
  - Financial
  - Content
  - Strategic
  - Sales
  - Marketing
  - Operations
  - HR
  - Compliance
  - Customer Support
  - Data
  - Data Reporting
- Fragments should specify how that agent should behave differently by persona, for example:
  - Financial: runway/burn for startups, cash discipline for solopreneurs, departmental margin control for SMEs, board-ready reporting for enterprise
  - Operations: low-overhead automations for solopreneurs, fast handoff design for startups, SOP and vendor discipline for SMEs, rollout governance for enterprise
  - Compliance: minimal viable compliance for solopreneurs, readiness posture for startups, audit cadence for SMEs, control mapping and approvals for enterprise
- Keep helper schema agents mostly persona-neutral unless they produce user-facing narratives.

**Implementation shape:**
- Add `app/personas/prompt_fragments.py` with helpers such as:
  - `build_persona_policy_block(...)`
  - `build_agent_persona_fragment(agent_name, persona)`
  - `build_delegation_handoff_fragment(...)`
- Use these helpers from top-level agent definitions or from the shared callback path.
- Preserve existing prompt strengths while inserting a dedicated `PERSONA OPERATING MODE` section.

**Files to modify:**
- `app/prompts/executive_instruction.txt`
- `app/agents/financial/agent.py`
- `app/agents/content/agent.py`
- `app/agents/strategic/agent.py`
- `app/agents/sales/agent.py`
- `app/agents/marketing/agent.py`
- `app/agents/operations/agent.py`
- `app/agents/hr/agent.py`
- `app/agents/compliance/agent.py`
- `app/agents/customer_support/agent.py`
- `app/agents/data/agent.py`
- `app/agents/reporting/agent.py`

## 3. Persona-Aware Routing and Delegation
**Problem:** The Executive Agent currently exposes a broad universal agent system. Persona does not materially change which agents are favored, how much complexity is surfaced, or which approval gates apply.

**Strategy:**
- Add explicit routing policy that biases delegation by persona.
- First implementation should be soft-routing, not hard entitlement gating:
  - Solopreneur: default to Executive + Content + Marketing, minimize multi-agent fan-out unless it clearly improves execution
  - Startup: bias to Strategy + Marketing + Sales + Finance + Data for growth and PMF work
  - SME: bias to Operations + Reporting + Finance + Compliance + HR for cross-functional reliability
  - Enterprise: bias to Strategy + Reporting + Data + Compliance + Operations with stronger approval and stakeholder framing
- Update delegation handoffs so sub-agents receive:
  - active persona
  - current business context
  - explicit task objective
  - expected output style
  - escalation or approval posture
- Resolve prompt contradictions found during analysis:
  - Executive auto-initiative behavior vs Strategic consent-first behavior
  - Executive widget claims vs actual specialist widget support
  - outdated "11 agents" narrative vs live 12-agent production setup

**Implementation shape:**
- Add `app/personas/routing_policy.py` or extend `policy_registry.py` with routing preferences.
- Update the Executive prompt to instruct persona-based routing defaults.
- Update `app/agents/context_extractor.py` so injected personalization includes:
  - persona policy block
  - routing bias block
  - response contract block
- Keep root-level `system_prompt_override` behavior, but ensure specialists always receive the persona policy and delegation contract additively.

**Files to modify:**
- `app/prompts/executive_instruction.txt`
- `app/agents/context_extractor.py`
- `app/services/user_agent_factory.py`
- `app/agents/specialized_agents.py` only if naming cleanup is folded into this milestone
- `AGENTS.md`

## 4. Template and Workflow Alignment
**Problem:** Persona exists in template and workflow data models, but orchestration and UI behavior only partially honor it.

**Strategy:**
- Ensure persona is passed consistently when listing workflow templates, initiative templates, and related recommendation surfaces.
- Align suggested workflow experiences to persona routing defaults.
- If the current library page omits persona filtering, fix that as part of this milestone so the agent recommendations match the visible template catalog.

**Files to modify:**
- `app/workflows/engine.py`
- `app/services/initiative_service.py`
- `frontend/src/services/workflows.ts`
- `frontend/src/app/dashboard/workflows/templates/page.tsx`

## 5. Eval and Test Coverage
**Problem:** Without persona-specific tests, the system can regress back to generic responses while still technically "supporting" persona.

**Strategy:**
- Add unit tests for persona policy lookup and prompt-block construction.
- Add integration tests that verify the same request produces materially different routing and instructions by persona.
- Add evaluation datasets for canonical scenarios that matter to the product:
  - "Help me launch a service" across all four personas
  - "Build a weekly business operating system"
  - "Create a reporting structure"
  - "How should I handle compliance risk?"
- Assert differences in:
  - delegate selection
  - KPI emphasis
  - output format
  - approval behavior
  - complexity level

**Implementation shape:**
- Add `tests/unit/test_persona_policy_registry.py`
- Add `tests/unit/test_persona_prompt_fragments.py`
- Add `tests/integration/test_persona_routing.py`
- Add eval files under `tests/eval_datasets/`

## 6. Suggested Execution Order
1. Build the persona policy models and registry.
2. Replace inline persona guide generation in `user_agent_factory`.
3. Extend `context_extractor` to inject structured persona policy blocks.
4. Update the Executive prompt for persona-aware routing and approval posture.
5. Add top-level specialist prompt fragments in descending business impact order:
   - Strategic
   - Financial
   - Content
   - Marketing
   - Sales
   - Operations
   - Reporting
   - Compliance
   - Data
   - HR
   - Customer Support
6. Align template/workflow persona filtering in backend and frontend.
7. Add unit tests.
8. Add integration tests and eval datasets.
9. Run prompt review and regression pass on key business journeys.

## 7. Acceptance Criteria
- Persona handling is no longer defined by four short text paragraphs.
- Executive routing behavior differs in a testable way by persona.
- All top-level production agents receive persona-specific operating guidance.
- Prompt contradictions identified in the analysis are resolved.
- Workflow and template recommendation surfaces honor persona consistently.
- Eval scenarios show materially different outputs for the same request across personas.

## 8. Verification Plan
- **Registry verification:** Unit-test every persona definition and required policy field.
- **Prompt verification:** Snapshot or structured assertion tests for injected persona blocks and agent-specific fragments.
- **Routing verification:** Integration tests that inspect delegate choice or intermediate prompt state for representative requests.
- **Behavior verification:** Eval runs for the four canonical persona journeys and comparison against expected persona-specific response traits.
- **Regression verification:** Re-run existing chat and workflow tests that touch onboarding, context injection, initiatives, and template listing.

## 9. Risks and Guardrails
- **Risk:** Persona instructions become too verbose and drown out core agent prompts.
  - **Guardrail:** Keep registry policy concise and structured; inject only the fields needed at runtime.
- **Risk:** Persona becomes confused with pricing tier or entitlement gating.
  - **Guardrail:** Implement routing bias first; keep hard feature gating separate unless product explicitly requires it.
- **Risk:** Specialists remain generic because only the Executive prompt changes.
  - **Guardrail:** Treat specialist fragments as milestone-critical, not optional polish.
- **Risk:** Prompt behavior changes are difficult to verify.
  - **Guardrail:** Add persona eval datasets before finalizing the milestone.
