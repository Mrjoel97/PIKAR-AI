# Agent Operating Model — W3 Plan: Executive, Marketing, Data Migration

**Spec**: `docs/superpowers/specs/2026-05-11-agent-operating-model-design.md` (§ 17 Wave 3)
**Predecessor**: `docs/superpowers/plans/2026-05-11-agent-operating-model-w1-w2.md`
**Author**: PIKAR AI (with Claude Opus 4.7)
**Date**: 2026-05-11
**Scope**: Wave 3 of the wave-based migration plan from spec § 17.

---

## 1. Goal

Migrate three additional agents — **executive**, **marketing**, **data** — to `PikarBaseAgent`, wire **skill auto-injection** as a live (not just compiled-in) feature, and gate executive rollout behind **10% shadow traffic** so production parity can be measured before full cutover.

### Success criteria

A W3 PR is mergeable when:

1. `app/agents/executive/`, `app/agents/marketing/`, `app/agents/data/` each have the canonical four-file layout (`agent.py` ≤30 lines, `instructions.md`, `operations.yaml`, `tools.py`).
2. `specialized_agents.py` re-exports the new factories without behavior change (legacy callers still work).
3. `skill_injection.match_and_inject` is wired to a production semantic-matching backend (not just `allowed_skill_ids` lookup) with telemetry on top-K hit rate and latency.
4. A shadow-traffic router sends 10% of incoming executive requests through both old and new agent code paths and persists a structured diff (text, tool calls, artifacts) for review.
5. Contract + integration tests pass for all three agents, mirroring the financial-pilot pattern.
6. No regression in `tests/unit/agents tests/integration/agents` (currently 425 passing post-W1/W2).
7. The shadow-diff dashboard shows **<5% material divergence** across 1,000 executive turns over 72 hours before W3 can be considered "validated for full rollout in W4".

### Out of scope

- Migrating the remaining 7 agents (`content_creation`, `sales`, `operations`, `hr`, `compliance`, `customer_support`, `strategic`) — that's W4.
- Retiring `shared_instructions.py` or `enhanced_tools.py` wrappers — that's W5.
- Admin-panel UI for editing `operations.yaml` — separate downstream project.

---

## 1a. Section A status — post-survey reconciliation (2026-05-11)

After this plan landed on `main` (PR #26), a survey of the existing codebase showed that **most of Section A was already shipped** during W1/W2 — the plan was written from the spec § 17 description rather than against the actual code. The reconciliation:

| Task in plan | Reality | Disposition |
|---|---|---|
| **A1** Define `SkillMatcher` protocol | `skills_registry.semantic_search` is the live matcher interface (`app/skills/registry.py:224`) | Already shipped |
| **A2** `VertexEmbeddingMatcher` | `app/rag/embedding_service.py` + `app/skills/skill_embeddings.py` warm-cache | Already shipped |
| **A3** `KeywordFallbackMatcher` | No keyword fallback existed — dev environments without Vertex got empty injection | **A3-lite shipped** (substring tokens over name + description + summary; scores capped in `[0.65, 0.95]`; fires when `is_warmed()` returns False) |
| **A4** Factory + `SKILL_MATCHER` env var | `startup_warmup_enabled()` auto-detects via `SKILL_EMBEDDING_WARMUP_ENABLED` + `K_SERVICE` | Already shipped |
| **A5** Wire `match_and_inject` to matcher | `skill_injection.py:140` already calls `semantic_search` | Already shipped |
| **A6** OTel span `pikar.skill_injection.match` | Was missing | **Shipped** in this PR — span emitted on every call with attributes `agent_id`, `mode`, `top_k`, `similarity_floor`, `query_len`, `matcher` (semantic\|keyword_fallback), `candidate_count`, `matched_count`, optional `skipped` and `error` |
| **A7** Perf regression test p95 < 80ms | Was missing | **Shipped** — 100-iteration loop with mocked semantic search, asserts p95 < 80ms |
| **A8** Backfill migration | `warmup_skill_embeddings()` runs at startup | Already shipped |

Net delta: 3 changes (A6, A7, A3-lite) instead of 8 tasks. The lesson for Sections B–D: **survey before re-deriving the plan**. Section B (executive migration + shadow router) and Sections C/D (marketing + data migration) should each get a brief code survey before execution to avoid duplicate work.

---

## 2. Pre-requisites

- W1/W2 merged to `main` (this is being landed via PR #25).
- `app/agents/runtime/` package green on `main`.
- Financial agent runs through `PikarBaseAgent` in production without regressions for at least 1 week (operational soak).
- Skill registry stable; `allowed_skill_ids` declared on the 10 specialized agents' legacy configs (for fallback during shadow traffic).

---

## 3. Approach

**Per-agent migration is mechanical** — the financial pilot proved the four-file template. W3 risk concentrates in two cross-cutting concerns:

1. **Skill auto-injection going from "module exists" to "live in production"**. The W1/W2 module is wired into `before_agent` but its `match_and_inject` body still falls back to `allowed_skill_ids` filtering in absence of a semantic backend. W3 makes it actually semantic.
2. **Executive shadow traffic**. The executive agent is the highest-stakes router. Cutover without diff data is unsafe.

W3 therefore front-loads the cross-cutting work (Section A) before any agent migration touches `PikarBaseAgent` in production.

---

## 4. Section breakdown

### Section A — Skill auto-injection production wiring (Tasks A1–A8)

Make `runtime/skill_injection.match_and_inject` a live semantic matcher with telemetry.

- **A1**: Define `SkillMatcher` protocol (`match(query: str, candidates: list[str], top_k: int) -> list[Match]`) in `app/agents/runtime/skill_injection.py`. Each `Match` has `skill_id`, `score`, `reason`.
- **A2**: Implement `VertexEmbeddingMatcher` adapter using existing `gemini-embedding-001` infrastructure (`app/services/embeddings/`). Cache embeddings per skill description in Supabase (`skills_registry.embedding` column — add migration if missing).
- **A3**: Implement `KeywordFallbackMatcher` for environments without Vertex credentials (dev, tests).
- **A4**: Wire a factory `get_skill_matcher() -> SkillMatcher` that picks `VertexEmbeddingMatcher` when `GOOGLE_API_KEY` is set, else `KeywordFallbackMatcher`. Single env var: `SKILL_MATCHER` (`vertex|keyword|disabled`), default `vertex`.
- **A5**: Update `skill_injection.match_and_inject` to call the matcher with top-K=5 (configurable via `operations.yaml::skills.top_k`).
- **A6**: Add OpenTelemetry span `pikar.skill_injection.match` with attributes `agent_id`, `mode`, `query_len`, `top_k`, `hit_rate`, `latency_ms`. Span exported via existing telemetry pipeline.
- **A7**: Performance budget: p95 < 80 ms for matcher call (Vertex embedding is ~30-50 ms; cache hit is ~2-5 ms). Add a regression test with mocked Vertex round-trip ≤60 ms.
- **A8**: Backfill migration: pre-compute embeddings for all rows in `skills_registry` so the first production call doesn't pay a cold cost. Idempotent script in `scripts/backfill_skill_embeddings.py`.

**Exit gate**: All `tests/unit/agents/runtime/test_skill_injection.py` pass with both matchers. Backfill script run on staging. p95 latency under 80 ms on staging traces.

---

### Section B — Executive migration + shadow traffic infrastructure (Tasks B1–B14)

#### Sub-section B.i — Shadow router (Tasks B1–B5)

- **B1**: Create `app/services/shadow_router.py` with a `ShadowRouter` class. Constructor takes `(primary: Agent, candidate: Agent, percent: int)`. `route(request) -> AsyncIterator[Event]` returns the primary stream to the user and fires the candidate stream in the background.
- **B2**: Add `agent_shadow_diffs` table:
  ```sql
  id UUID PK, created_at TIMESTAMPTZ,
  agent_id TEXT, request_id UUID, user_id UUID,
  primary_text TEXT, candidate_text TEXT,
  primary_tool_calls JSONB, candidate_tool_calls JSONB,
  primary_artifacts JSONB, candidate_artifacts JSONB,
  divergence_score FLOAT,  -- 0.0 identical, 1.0 fully diverged
  divergence_kind TEXT  -- 'text'|'tool_calls'|'artifacts'|'multiple'
  ```
- **B3**: Implement `compute_divergence(primary, candidate) -> Divergence` in `app/services/shadow_router.py`. Three checks:
  - text: cosine similarity over Vertex embeddings (threshold ≥0.85 = identical).
  - tool_calls: structural diff on `(tool_id, args)` tuples; ignore ordering for parallel calls.
  - artifacts: structural diff on `(kind, content_id)` pairs.
- **B4**: `app/fast_api_app.py::run_sse` reads `EXECUTIVE_SHADOW_PERCENT` env var (default 0). When > 0, route through `ShadowRouter`.
- **B5**: Background candidate-stream cancellation: if primary completes first, candidate is cancelled (don't keep paying for tokens). If candidate completes first, primary still streams to user.

#### Sub-section B.ii — Executive agent file structure (Tasks B6–B11)

- **B6**: Create `app/agents/executive/instructions.md` — extract from current `app/agents/executive_agent.py` system prompt, preserving every behavioral directive.
- **B7**: Create `app/agents/executive/operations.yaml` — declare `model`, `routing`, `skills.allowed_skill_ids` (all skills), `skills.top_k=5`, `persona_id_default`, `initiative.phases_owned=['vision','planning']`, `tools` manifest.
- **B8**: Create `app/agents/executive/tools.py` declaring `ToolsManifest` with the full executive toolset (already in `app/agents/executive_agent.py::TOOLS`).
- **B9**: Refactor `app/agents/executive/agent.py` to ~30 lines using `PikarBaseAgent` — mirror the financial pilot.
- **B10**: Update `app/agents/specialized_agents.py` to re-export both `create_executive_agent_legacy` (current impl) AND `create_executive_agent` (new). Legacy is the default until B14 flips it.
- **B11**: Backward-compat regression test (`tests/integration/agents/test_executive_legacy_compat.py`) — runs a fixed transcript through both implementations, asserts non-empty response from both, logs divergence to `agent_shadow_diffs` but does not fail on divergence (this is a diff-baseline test).

#### Sub-section B.iii — Shadow rollout (Tasks B12–B14)

- **B12**: Deploy with `EXECUTIVE_SHADOW_PERCENT=10`. Monitor `agent_shadow_diffs` for 72 hours.
- **B13**: Build a minimal admin view (`/dashboard/admin/shadow-diffs`) — table of recent diffs, filterable by `divergence_kind`, with side-by-side text view. ~200 lines of React, reuses existing `DashboardAdminLayout`.
- **B14**: Decision gate: if median `divergence_score` < 0.15 and no critical regressions in tool calls, mark executive as "shadow-validated" and flip the default factory to the new implementation in `specialized_agents.py`. Otherwise iterate on `instructions.md` / `operations.yaml` and re-shadow.

**Exit gate**: Executive PikarBaseAgent serves 100% of traffic; shadow router can be left enabled at low percent for ongoing parity monitoring.

---

### Section C — Marketing migration (Tasks C1–C7)

Marketing has more domain-specific tools (Canva MCP, ad management, campaign orchestration) and a larger `allowed_skill_ids` set. No shadow traffic required — financial-pilot pattern proves the migration is mechanical.

- **C1**: Create `app/agents/marketing/instructions.md` from current `app/agents/marketing/agent.py` system prompt.
- **C2**: Create `app/agents/marketing/operations.yaml`. `phases_owned=['awareness','acquisition','retention']`. `allowed_skill_ids` includes every `marketing:*` skill from the registry. Action thresholds: `require_approval_for_external_send=True` (ad spend, email blasts).
- **C3**: Create `app/agents/marketing/tools.py` — manifest includes Canva MCP tools, ad platform tools, content scheduler, etc.
- **C4**: Refactor `app/agents/marketing/agent.py` to thin `PikarBaseAgent` factory.
- **C5**: Update `specialized_agents.py` re-exports.
- **C6**: Contract test: `tests/integration/agents/test_marketing_contract.py` — operations.yaml parses, manifest resolves, all `allowed_skill_ids` exist in registry, instructions.md non-empty.
- **C7**: Integration test: `tests/integration/agents/test_marketing_initiative.py` — run a "launch campaign" initiative step end-to-end with mocked Canva MCP, assert audit produced and workspace event observable.

**Exit gate**: Marketing migration green; legacy factory removed from `specialized_agents.py` (no shadow traffic gate needed for non-executive agents per spec § 17).

---

### Section D — Data migration (Tasks D1–D7)

Data agent is moderately complex (Hex MCP, BigQuery, dashboard tools). Same template as Marketing.

- **D1**: `app/agents/data/instructions.md`.
- **D2**: `app/agents/data/operations.yaml`. `phases_owned=['discovery','reporting']`. `allowed_skill_ids` includes every `data:*` skill. Action thresholds: financial caps don't apply; external-send doesn't apply.
- **D3**: `app/agents/data/tools.py`.
- **D4**: Refactor `app/agents/data/agent.py`.
- **D5**: Re-exports.
- **D6**: Contract test.
- **D7**: Integration test: end-to-end "build a dashboard" with mocked Hex MCP + BigQuery.

**Exit gate**: Data migration green.

---

### Section E — Validation + rollout (Tasks E1–E5)

- **E1**: Run the full `tests/unit/agents tests/integration/agents` suite — must pass at 425+ tests, accounting for new tests added across Sections A-D.
- **E2**: Lint pass per Makefile (`uv run ruff check`, `uv run ruff format --check`, `uv run ty check`).
- **E3**: Pre-merge smoke deploy to staging Cloud Run. Run the **shadow-diff dashboard** for 72 hours.
- **E4**: Document any divergences and their resolution in `docs/superpowers/plans/2026-05-11-agent-operating-model-w3-rollout-notes.md` (follow-up file).
- **E5**: Open W3 PR against `main`. Body includes: shadow-diff summary, contract/integration test results, link to staging traces.

**Exit gate**: W3 PR approved and merged. Ready to begin W4 (the remaining 7 agents).

---

## 5. Task dependency graph

```
A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8  (skill matcher, ordered)
                                  ↓
B1 → B2 → B3 → B4 → B5            ↓   (shadow router, ordered)
                  ↓               ↓
B6 → B7 → B8 → B9 → B10 → B11     ↓   (executive files, ordered)
                            ↓     ↓
B12 → B13 → B14 ←———————————————— (shadow rollout, needs both)
  ↓
  ↓ (shadow gate clears)
  ↓
C1...C7  (marketing, parallel to D)
D1...D7  (data, parallel to C)
  ↓
E1 → E2 → E3 → E4 → E5
```

Sections A and B.i can run in parallel (independent infrastructure). B.ii depends on A8 (skill matcher available). B.iii depends on B.i + B.ii. Sections C and D can run in parallel after B.iii clears the shadow gate.

Estimated total: ~40 tasks, ~3-4 weeks calendar time given parallelization.

---

## 6. Test strategy

Same three layers as W1/W2 (spec § 18):

- **Unit tests** per new module. New tests in `tests/unit/agents/runtime/test_skill_injection.py` for the matcher protocol + adapters. New tests in `tests/unit/services/test_shadow_router.py` for routing and divergence computation. Per-agent unit tests for `operations.yaml` loaders.
- **Contract tests** per migrated agent (`test_executive_contract.py`, `test_marketing_contract.py`, `test_data_contract.py`). Verify `operations.yaml` parses, `ToolsManifest.resolve()` returns real callables for every tool, `instructions.md` is non-empty, every `allowed_skill_ids` entry exists in `skills_registry`.
- **Integration tests** per migrated agent — initiative step end-to-end with mocked external dependencies. Asserts research gate enforced, audit produced and persisted, workspace SSE event observable, `agent_task_executions` row written.

**TDD discipline**: every task that adds production code starts with a failing test (per `superpowers:test-driven-development`). The plan above intentionally does NOT enumerate test scaffolding per task — that's TDD discipline applied at execution time, not pre-baked in the plan.

---

## 7. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Vertex embedding latency spikes break the `before_agent` budget | M | M | Cache embeddings per skill, p95 budget of 80 ms with regression test (A7). Fall back to keyword matcher on timeout. |
| Executive shadow traffic doubles cost during W3 | H | L | Shadow only 10% of traffic, cancel candidate stream once primary completes, time-cap the 72-hour shadow window. |
| Executive divergence score is high → can't merge | M | H | The `operations.yaml` + `instructions.md` are tunable post-shadow without re-deploying code. Iterate on prompt content, re-run shadow. Worst case: roll back the executive flip in `specialized_agents.py` and ship marketing+data without executive. |
| Skill matcher returns unexpected top-K → agent behavior drift | M | M | Telemetry on `hit_rate` (A6). Shadow-traffic diff catches behavioral drift before production. |
| Parallel automation interferes with branch hygiene (per W1/W2 experience) | H | L | Same playbook: reset-to-origin + cherry-pick, atomic git command chains, `--force-with-lease` only when origin matches expectation. Document in branch-pollution memory if encountered. |
| Marketing/data migration uncovers shared-instruction dependencies | M | M | The W5 work to fold `shared_instructions.py` into `runtime/skill_injection.py` is deferred. If a hard dependency surfaces in W3, lift it into `runtime/skill_injection.py` opportunistically. |

---

## 8. Rollback plan

Each migration is gated by a re-export flip in `specialized_agents.py`. Rolling back any single agent means changing one line back to `create_<agent>_legacy`. The legacy implementations are preserved throughout W3 and W4 (per spec § 17 backward-compatibility commitment).

Database changes are additive (new tables, new columns with defaults) — no destructive migrations. Rolling back code does not require a schema rollback.

Shadow router can be disabled in seconds via `EXECUTIVE_SHADOW_PERCENT=0`.

---

## 9. Open questions (resolve during implementation, not blocking)

- **Q1**: Should `skills_registry.embedding` be a `vector(768)` column or stored in a separate `skill_embeddings` table? Pro-column: simpler joins. Pro-separate: schema cleanliness, allows multi-model embeddings later. **Recommendation**: column for now, separate if multi-model emerges.
- **Q2**: Should shadow router run candidate streams in the same process or fire-and-forget to a worker queue? Same-process is simpler; worker queue is more isolated. **Recommendation**: same-process for W3 (lower complexity), revisit if executive load makes it hot.
- **Q3**: Where does the shadow-diff dashboard live in the admin nav? Existing `Workflows` tab or a new `Operating Model` tab? **Recommendation**: new tab — separates operating-model concerns from workflow concerns and gives W4 a home for additional agent-migration dashboards.

---

## 10. Acceptance checklist

Before opening the W3 PR:

- [ ] All Section A tasks complete; skill matcher p95 ≤ 80 ms verified on staging.
- [ ] All Section B tasks complete; executive shadow-diff median < 0.15.
- [ ] All Section C tasks complete; marketing contract + integration tests green.
- [ ] All Section D tasks complete; data contract + integration tests green.
- [ ] All Section E tasks complete; staging smoke + 72-hour shadow soak documented.
- [ ] `tests/unit/agents tests/integration/agents` ≥ 425 passing.
- [ ] `uv run ruff check`, `uv run ruff format --check`, `uv run ty check` all clean.
- [ ] PR body summarizes shadow-diff outcomes and links to the rollout-notes file.

---

## 11. Hand-off to W4

W4 inherits:

- A proven per-agent migration pattern (now validated against 4 agents: financial, executive, marketing, data).
- The shadow-router infrastructure (reusable for any cross-version comparison, not just executive).
- The skill-matcher infrastructure (production-grade).
- The `operations.yaml` schema with no breaking changes anticipated.

W4 adds the remaining 7 agents in roughly two batches (e.g., content cluster + ops cluster). Each batch can use the shadow router opportunistically if risk warrants, but for non-executive agents the spec recommends direct cutover after contract + integration tests pass.
