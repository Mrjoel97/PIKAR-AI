# Requirements: Phase 1 (Harden & Nurture)

## 1. Workflow Hardening (Consolidate & Harden)
- **Deterministic Argument Mapping:** Standardize how workflow steps map inputs to tool arguments. Eliminate broad `**sys_context` calls in `app/workflows/worker.py` in favor of explicit Pydantic-based input schemas for each tool.
- **Unified Worker Logic:** Consolidate the execution paths in `app/workflows/engine.py` and `app/workflows/worker.py` to ensure consistent runtime behavior across backend and Supabase edge functions.
- **Improved Fault Tolerance:** Add explicit validation and retry mechanisms for tool calls, especially those involving external media generation (Vertex AI, Remotion).

## 2. Idea Nurturing Flow (Strategic Improvement)
- **Enhanced Strategic Agent:** The `StrategicPlanningAgent` must handle the transition from a single "Idea Prompt" to a multi-phase "Business Roadmap".
- **Product Brief Generation:** Automate the creation of a "Product Brief" (Markdown or PDF) that synthesizes the vision, user segments, and core features discussed in chat.
- **Seamless Delegation:** The `ExecutiveAgent` should automatically identify when a conversation has matured into a "Business Plan" and suggest the appropriate "New Venture" workflow.

## 3. Technical Debt Mitigation
- **Migration Reconciliation:** Reconcile numerical migration collisions in `supabase/migrations/` and standardize on a consistent timestamped prefix strategy.
- **Caching Layer hardening:** Implement Redis circuit breakers for all database-backed cache lookups (Personas, Sessions, Config).

## 4. Quality & Testing
- **Integrated E2E Testing:** Create a suite of automated integration tests that simulate the "Idea to Roadmap" flow using the mock session service.
- **Performance Benchmarking:** Establish baseline latency for the `ExecutiveAgent` orchestration overhead.
