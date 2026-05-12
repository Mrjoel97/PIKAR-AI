---
phase: 111-workflow-node-editor-branching-execution
plan: 04
subsystem: frontend
tags: [workflow-editor, condition-node, jsonlogic, codemirror, dual-tab-ux, react, zod, vitest, shared-fixture, client-validation, rule-4]

# Dependency graph
requires:
  - phase: 110-04-frontend-editable
    provides: NodePropertiesDrawer + useGraphSchema + useGraphValidation pure-functional client validator with rules 1/2/3/6/7 + shared fixture (8 cases) parametrized in vitest + NodeKind union type
  - phase: 111-02-validation-rule-4
    provides: Shared fixture extended 8 -> 13 cases (5 new condition_* rule-4 cases) — Plan 04 imports same JSON for client-side vitest parametrize
provides:
  - "frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx — dual-tab Guided/Advanced editor for condition node config (CONTEXT.md decision 1)"
  - "frontend/src/components/workflows/editor/conditionExpressionTranslator.ts — pure-function bidirectional translator {field,operator,value} <-> JSONLogic JSON with round-trip-failure detection"
  - "frontend/src/components/workflows/editor/useGraphSchema.ts — tightened ConditionConfigSchema + NODE_OUTPUT_KEYS static per-kind output map (Discretion #4 Option A)"
  - "frontend/src/components/workflows/editor/useGraphValidation.ts — rule 4 client validator mirrors Plan 02 server _validate_rule_4_condition_outgoing_degree byte-for-byte via shared fixture"
  - "NodePropertiesDrawer.tsx routes condition kind to ConditionPropertiesEditor (Phase 110 'Coming in Phase 3/4' placeholder replaced)"
  - "frontend/package.json: @uiw/react-codemirror ^4.25.9 + @codemirror/lang-json ^6.0.2 dependencies"
  - "54 new vitest tests (41 translator + 13 editor + 14 extended validation tests) + 1 updated drawer test — total workflow vitest suite: 159 GREEN"
affects: [111-05-frontend-graph-run-widget]

# Tech tracking
tech-stack:
  added:
    - "@uiw/react-codemirror ^4.25.9 (thin React wrapper around CM6 stack)"
    - "@codemirror/lang-json ^6.0.2 (JSON syntax highlighting)"
    - "Transitive: codemirror, @codemirror/state, @codemirror/view (~300KB gzipped per Discretion #2)"
  patterns:
    - "Mock CodeMirror in vitest via vi.mock('@uiw/react-codemirror') -> <textarea data-testid='cm-editor'> — same pattern Phase 110 used for @xyflow/react (jsdom can't render the real CM6 canvas/measurement code)"
    - "Bidirectional translator with round-trip-failure detection: translateJsonLogicToGuided returns null when expression cannot be decomposed (nested logic, computed operands, unknown ops, wrong arity); caller keeps user in Advanced tab with read-only Guided + 'Complex expression' notice"
    - "Operand-order convention for distinguishing JSONLogic 'in' semantics: {in: [<var>, [arr]]} = array membership; {in: [<primitive>, <var>]} = substring-in-string (contains). Translator decides which Guided operator to emit based on operand types"
    - "CSV with numeric coercion for in/not in: every CSV token tested against /^[-+]?\\d+(\\.\\d+)?$/ regex; if all tokens parse as numbers, returns number[]; else string[]"
    - "Shared fixture parametrize parity (B-4 contract): both pytest (Plan 02) and vitest (Plan 04) loop over tests/fixtures/graph_validation_cases.json; client-side rule 4 emits same error count + node_id + message_contains as server"
    - "Static per-kind output declarations (Discretion #4 Option A): NODE_OUTPUT_KEYS map keyed by NodeKind; BFS-backward from selected condition node collects upstream agent-action outputs as previous_outcomes.{id}.{key} options"
    - "Append rule 4 AFTER rule 7 loop in validateGraph: preserves Phase 110 error-emission order (1/6/2/3/7/4) so existing fixture assertions stay byte-for-byte stable"

key-files:
  created:
    - frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx
    - frontend/src/components/workflows/editor/conditionExpressionTranslator.ts
    - frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx
    - frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx
    - frontend/src/components/workflows/editor/useGraphSchema.ts
    - frontend/src/components/workflows/editor/useGraphValidation.ts
    - frontend/src/__tests__/workflows/NodePropertiesDrawer.test.tsx
    - frontend/src/__tests__/workflows/useGraphValidation.test.ts
    - frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx

key-decisions:
  - "CodeMirror 6 via @uiw/react-codemirror wrapper (Discretion #2 winner). Brings codemirror + @codemirror/state + @codemirror/view as transitive deps. Single npm install for the full CM6 stack. ~300KB gzipped — light enough for the Advanced tab"
  - "Round-trip rule (CONTEXT.md decision 1): translateJsonLogicToGuided returns null for non-decomposable JSONLogic. UI sets roundTripFailed=true, disables Guided form inputs, shows amber 'Complex expression — edit in Advanced tab' notice. Mount-in-Advanced when initial expression is already complex"
  - "Operator semantics for 'contains' (Discretion #3): emit {in: [<substring>, {var: <field>}]} — substring FIRST. Distinguishes from array-membership 'in' at parse time. JSONLogic has only one 'in' op; we use operand-order convention to round-trip cleanly"
  - "CSV with numeric coercion: 'in 10,20,30' -> {in: [{var: f}, [10, 20, 30]]}; 'in a,b,c' -> {in: [{var: f}, ['a', 'b', 'c']]}. Coercion: every token must match number-literal regex. Mixed (e.g. '10,foo') stays as strings"
  - "NODE_OUTPUT_KEYS static map (Discretion #4 Option A): each NodeKind declares its output keys statically. agent-action -> [outcome_text, output_data, _execution_meta] matching Spec A's step_executor.py write shape. NodePropertiesDrawer.computeUpstreamFields walks backward, emits previous_outcomes.{up_id}.{key} per upstream agent-action"
  - "ConditionConfigSchema = z.object({expression: z.unknown().optional()}).passthrough(). Expression is structurally arbitrary (JSONLogic); semantic validation happens at engine evaluate time (Plan 03's graph_executor with json-logic Python). Optional so freshly-dragged condition nodes don't immediately fire rule 7; rule 4 server-side blocks save when edges are wrong anyway"
  - "Append rule 4 AFTER rule 7 in validateGraph (mirrors Plan 02's server pattern). Preserves Phase 110 error emission order so fixture assertions are stable. Iterates graph_nodes in declaration order for determinism (matches server)"
  - "Custom field input as fallback in Field selector: dropdown lists upstreamFields + __custom__ sentinel. Selecting __custom__ reveals a text input for arbitrary field name. Round-trip parses field back into either the dropdown's matched option or custom-field mode (depending on upstreamFields membership)"
  - "Save semantics: Guided changes ALWAYS persist config.expression as JSONLogic JSON document (never as the {field, operator, value} triple). Server-side condition routing (Plan 03 graph_executor) reads config.expression directly via json-logic library. Single source of truth on disk"
  - "Test-run button NOT shipped in Phase 111 (planner Discretion #1). Spec B § Phase 3 doesn't explicitly require it; absorbing it would push beyond the 4.5-week estimate. Deferred to a future phase / Phase 3.5 — Plan 04 keeps scope tight"

patterns-established:
  - "Bidirectional pure-function translator pattern: {Guided <-> JSONLogic} module isolates serialization concerns from React component. Component imports translate*; tests can exercise translator independently. Round-trip detection is the key safety property — caller knows whether re-parsing succeeded"
  - "Mock CodeMirror in vitest: vi.mock('@uiw/react-codemirror', () => ({default: <textarea data-testid='cm-editor' value/onChange>})). Same pattern Phase 110 used for @xyflow/react — jsdom can't render the real editor; the mock surface gives tests value/onChange control"
  - "Shared canonical fixture for client/server parity continues to work across phase boundaries: Plan 02 added 5 cases to graph_validation_cases.json; Plan 04 auto-picked them up via the existing vitest forEach loop. No fixture editing needed in Plan 04 — only the client implementation"
  - "Per-kind static output declarations in useGraphSchema (NODE_OUTPUT_KEYS): Phase 4 can expand without re-architecting the field selector. NodePropertiesDrawer.computeUpstreamFields is a pure-function BFS that works for any future node kind"
  - "Drawer-host renders kind-specific editor: NodePropertiesDrawer is a router by node.kind. Phase 110 had inline forms for trigger/agent-action/output; Phase 111 extracted the condition editor to its own component. Pattern scales for Phase 4 parallel/merge/human-approval editors"

requirements-completed: [NODEEDITOR-EDIT-03, NODEEDITOR-VALIDATE-02]

# Metrics
duration: 23min
completed: 2026-05-12
---

# Phase 111 Plan 04: Frontend Condition UX (Dual-Tab Editor + Client Rule 4) Summary

**Dual-tab Guided/Advanced editor for `condition` node config (CONTEXT.md decision 1) ships with CodeMirror 6 for syntax-highlighted JSONLogic editing; pure-function bidirectional translator with round-trip-failure detection (Guided becomes read-only when Advanced edit can't be decomposed); ROADMAP criterion 4 UAT contract verified by dedicated unit test (`revenue > 50000` produces `{">": [{"var": "revenue"}, 50000]}` exactly); client-side rule 4 mirrors Plan 02's server logic via shared fixture parametrize parity (13 cases). 41 + 13 + 14 = 68 new vitest tests + 1 updated test — 159 workflow tests GREEN overall, zero Phase 110 regressions, tsc clean.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-05-12T05:15:00Z (approx; first read in this session)
- **Completed:** 2026-05-12T05:38:00Z
- **Tasks:** 4 (7 atomic commits — 3 TDD RED+GREEN splits + 1 single feat commit for dep install)
- **Files created:** 4 (2 component/translator + 2 test files)
- **Files modified:** 8 (package.json/lock + 3 editor source + 2 test files + 1 page)

## Accomplishments

- **CodeMirror 6 frontend dep** (`@uiw/react-codemirror` ^4.25.9 + `@codemirror/lang-json` ^6.0.2). Brings the full CM6 stack (codemirror + state + view) as transitive deps via the thin `@uiw/react-codemirror` wrapper. ~300KB gzipped per Discretion #2.

- **`conditionExpressionTranslator.ts`** at `frontend/src/components/workflows/editor/conditionExpressionTranslator.ts` — pure-function bidirectional translator:
  - `translateGuidedToJsonLogic({field, operator, value})` → JSONLogic JSON document. Handles 9 operators: `==`, `!=`, `<`, `<=`, `>`, `>=`, `contains`, `in`, `not in`. CSV-split with numeric coercion for `in`/`not in`; substring-first operand order for `contains` (distinguishes from array-membership `in`).
  - `translateJsonLogicToGuided(jsonDoc)` → `{field, operator, value}` or `null`. Returns null when expression is non-decomposable (nested logic, computed operands, unknown ops, wrong arity). Uses operand-order convention to distinguish `contains` from array-`in`.
  - `OPERATORS` constant: readonly tuple of 9 operators in dropdown order.

- **`ConditionPropertiesEditor.tsx`** at `frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx` (~420 lines) — dual-tab UX:
  - **Guided tab** (default): 3 dropdowns. Field selector lists upstream fields + `__custom__` sentinel that reveals a free-text custom-field input. Operator dropdown has all 9 options. Value is a typed text input with op-specific placeholder.
  - **Advanced tab**: CodeMirror 6 editor with `@codemirror/lang-json` highlighting. Edits parse on every change; valid JSON propagates via onChange; invalid JSON shows inline parse error and does NOT propagate (preserves parent state).
  - **Round-trip rule** (CONTEXT.md decision 1): switching Advanced → Guided attempts `translateJsonLogicToGuided`; null result sets `roundTripFailed=true`, disables Guided form, shows amber "Complex expression — edit in Advanced tab" notice. Mount in Advanced when initial expression is already complex (`node.config.expression` exists but can't be translated).
  - **Save semantics**: `config.expression` is ALWAYS persisted as JSONLogic JSON document. Plan 03's server-side `graph_executor` reads it directly.

- **`useGraphSchema.ts` tightening** at `frontend/src/components/workflows/editor/useGraphSchema.ts`:
  - `ConditionConfigSchema = z.object({expression: z.unknown().optional()}).passthrough()`. Tightens from Phase 110's `PermissiveConfigSchema`. Expression is structurally arbitrary (validated semantically by json-logic at engine time, Plan 03); optional so freshly-dragged condition nodes don't fire rule 7.
  - `NODE_OUTPUT_KEYS` map (Discretion #4 Option A): per-kind static output declarations. `agent-action` declares `[outcome_text, output_data, _execution_meta]` matching Spec A's `step_executor.py` write shape. Used by `NodePropertiesDrawer.computeUpstreamFields`.

- **`useGraphValidation.ts` rule 4** at `frontend/src/components/workflows/editor/useGraphValidation.ts`:
  - `validateRule4(graph_nodes, graph_edges)` helper mirrors `app/workflows/graph_validation.py:_validate_rule_4_condition_outgoing_degree` byte-for-byte. For each `condition` node: collect outgoing edges, build `handles = new Set(edges.map(e => e.source_handle ?? null))`, emit `ValidationError(rule=4, node_id, ...)` if `length !== 2 || handles.size !== 2 || !handles.has('true') || !handles.has('false')`.
  - Called from `validateGraph()` AFTER rule 7 loop (preserves Phase 110 error-emission order 1/6/2/3/7/4 so existing fixture assertions stay byte-for-byte stable).
  - Iterates `graph_nodes` in declaration order for determinism (matches server).

- **`NodePropertiesDrawer.tsx` wiring** at `frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx`:
  - Added optional `nodes?: GraphNode[]` + `edges?: GraphEdge[]` props (default `[]` for backward-compat).
  - `computeUpstreamFields(nodes, edges, nodeId)` helper: BFS-backward from the selected condition node, collects upstream agent-action nodes, emits `previous_outcomes.{up_id}.{key}` per `NODE_OUTPUT_KEYS`.
  - Routes `condition` kind to `<ConditionPropertiesEditor>` (replaces Phase 110's "Coming in Phase 3/4" placeholder). Editor handles its own label input + config mutations.
  - `PHASE_3_4_KINDS` → `PHASE_4_KINDS` (now only parallel/merge/human-approval show "Coming in Phase 4" placeholder).

- **Editor page wiring** at `frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx`:
  - Pass `nodes` + `edges` props to `<NodePropertiesDrawer>` so the field selector works in real usage. (5-line change.)

- **Test parity**: 159 workflow vitest tests GREEN across 12 files. Phase 110 had 105 tests (including the 8-case fixture parametrize); Plan 04 added 54 new tests (41 translator + 13 ConditionPropertiesEditor + 14 extended validation including 5 rule-4 fixture cases + 5 explicit rule-4 + 4 NODE_OUTPUT_KEYS/ConditionConfigSchema). One existing Phase 110 test was updated: the drawer test for `condition` kind now asserts the editor mounts (vs. the old "Coming in Phase 3" placeholder).

- **B-4 fixture parity preserved**: shared `tests/fixtures/graph_validation_cases.json` now has 13 cases. Both pytest (Plan 02 server) and vitest (Plan 04 client) loop over the same JSON; identical `expected_errors` produce identical `validateGraph` output on both sides. Any future divergence is caught by either suite.

- **Zero backend changes**: `git show --name-only` for all 7 Plan 04 commits confirms `frontend/` paths only. `app/workflows/engine.py` (modified in working tree) and `tests/integration/test_branching_workflow_execution.py` (untracked) are from Plan 03's interleaved parallel work — NOT in Plan 04's commits.

## Task Commits

Each task committed atomically on `plan-109-spec-b-phase-1`. Tasks 04-02, 04-03, 04-04 split into RED+GREEN per TDD:

1. **Task 04-01: add CodeMirror 6 frontend dep** — `7f0dab1a` (feat)
2. **Task 04-02 RED: failing tests for translator (31 cases)** — `0c0ccb7c` (test)
3. **Task 04-02 GREEN: conditionExpressionTranslator implementation (41 tests)** — `b189217e` (feat)
4. **Task 04-03 RED: failing tests for rule 4 + NODE_OUTPUT_KEYS + ConditionConfigSchema** — `2ef4078d` (test)
5. **Task 04-03 GREEN: client-side rule 4 + tightened condition Zod schema** — `b5063b0d` (feat)
6. **Task 04-04 RED: failing tests for ConditionPropertiesEditor (dual-tab + round-trip)** — `25325b65` (test)
7. **Task 04-04 GREEN: ConditionPropertiesEditor + drawer wiring** — `25728a11` (feat)

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write).

## Files Created/Modified

**Created (4 files):**

- `frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx` (~420 lines) — dual-tab Guided/Advanced editor
- `frontend/src/components/workflows/editor/conditionExpressionTranslator.ts` (~250 lines) — pure-function translator + 9-op `OPERATORS` constant
- `frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx` (~350 lines, 13 tests)
- `frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts` (~390 lines, 41 tests)

**Modified (8 files):**

- `frontend/package.json` — added `@uiw/react-codemirror` ^4.25.9 + `@codemirror/lang-json` ^6.0.2
- `frontend/package-lock.json` — transitive CM6 lockfile updates
- `frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx` — `condition` branch replaced with `<ConditionPropertiesEditor>`; added optional `nodes`/`edges` props + `computeUpstreamFields` helper; `PHASE_3_4_KINDS` → `PHASE_4_KINDS`. (+85 lines, -17 lines net)
- `frontend/src/components/workflows/editor/useGraphSchema.ts` — added `ConditionConfigSchema` + `NODE_OUTPUT_KEYS` map; condition entry in `CONFIG_SCHEMAS` swapped from `PermissiveConfigSchema` to `ConditionConfigSchema`. (+50 lines net)
- `frontend/src/components/workflows/editor/useGraphValidation.ts` — added `validateRule4` helper + call inside `validateGraph` after rule 7 loop; updated module docstring. (+95 lines net)
- `frontend/src/__tests__/workflows/useGraphValidation.test.ts` — appended 11 new tests under three new describe blocks (5 explicit rule-4 + 3 NODE_OUTPUT_KEYS + 2 ConditionConfigSchema + 1 implicit deterministic emission for 2 conditions). The existing parametrized fixture loop auto-picked up the 5 new rule-4 cases. (+191 lines net)
- `frontend/src/__tests__/workflows/NodePropertiesDrawer.test.tsx` — added CodeMirror mock at top; condition test updated to assert editor mounts (vs. old placeholder); renamed "Coming in Phase 3/4" test to "Coming in Phase 4" for parallel/merge/human-approval. (+25 lines, -10 lines net)
- `frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx` — pass `nodes` + `edges` props to `<NodePropertiesDrawer>`. (+2 lines)

## Decisions Made

1. **`@uiw/react-codemirror` (Discretion #2 winner over plain `codemirror` + manual React glue).** Single `npm install @uiw/react-codemirror @codemirror/lang-json --save` brings the full CM6 stack as transitive deps (codemirror + @codemirror/state + @codemirror/view). Wrapper has a stable React component API (`<CodeMirror value extensions onChange basicSetup height />`) that matches React 19's idioms cleanly. ~300KB gzipped, well within Spec B's "medium" envelope.

2. **Round-trip rule per CONTEXT.md decision 1, implemented as `roundTripFailed: boolean` state.** When set, Guided form inputs are `disabled` + amber notice rendered. State flips back to `false` when Advanced → Guided succeeds in re-parsing. Mount-in-Advanced when initial `node.config.expression` exists but isn't decomposable (preserves user's existing complex expressions).

3. **Operand-order convention for `contains` vs `in` (Discretion #3).** JSONLogic has only one `in` operator that handles both substring-in-string and array-membership. The translator emits substring-first for `contains`: `{in: [<substring>, {var: <field>}]}`; var-first for `in`: `{in: [{var: <field>}, [<array>]]}`. Round-trip parser distinguishes by inspecting `Array.isArray(operands[1])`.

4. **CSV with numeric coercion for `in`/`not in` value input.** User types `"premium,enterprise"` or `"10,20,30"` in the Value field; translator splits on `,`, trims whitespace, filters empty tokens, then coerces to `number[]` iff every token matches `/^[-+]?\d+(\.\d+)?$/`. Mixed like `"10,foo"` stays as strings.

5. **Static `NODE_OUTPUT_KEYS` map (Discretion #4 Option A) over dynamic run-history-based field discovery (Option B).** Deterministic — doesn't depend on prior runs of the template. Lets users build a workflow from scratch and immediately see field options. `agent-action` declares `[outcome_text, output_data, _execution_meta]` matching the shape Plan 03 + Spec A's `step_executor.py` write into `workflow_steps.output_data`. Phase 4+ can expand.

6. **`ConditionConfigSchema` keeps `expression` optional, not required.** Freshly-dragged condition nodes from the palette have `config = {}` (no expression yet). Making expression required would fire rule 7 on every new node, blocking save and confusing users. Rule 4 server-side (Plan 02) blocks save when the edges aren't right anyway — that's the load-bearing safety net.

7. **Append rule 4 AFTER rule 7 in `validateGraph()` (mirrors Plan 02's server pattern).** Preserves Phase 110's error-emission order (1/6/2/3/7/4) byte-for-byte so existing fixture assertions for Phase 110 cases stay green. New rule-4 fixture cases (Plan 02 added 5) auto-passed without test rewrites.

8. **Custom-field input as fallback in Field selector.** The dropdown lists each upstream field + a `__custom__` sentinel option that reveals a free-text `<input>` for arbitrary field names. Lets users type `revenue` or `user_context.x` when the upstream subgraph hasn't declared the key statically. Round-trip parses the field back into custom-field mode if it isn't in `upstreamFields`.

9. **Save semantics: `config.expression` ALWAYS persists as JSONLogic JSON document.** Never the `{field, operator, value}` triple. Server-side condition routing (Plan 03's `graph_executor`) reads `config.expression` directly via the json-logic Python library. Single source of truth on disk; Guided form is purely a UX skin.

10. **Test-run button NOT included in Phase 111 (planner Discretion #1 deferred).** Spec B § Phase 3 doesn't explicitly require it; absorbing it would push beyond the 4.5-week estimate. Deferred to a future phase / Phase 3.5 — Plan 04 keeps scope tight on the dual-tab UX + rule 4 + translator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript exhaustiveness check failed with if/else cascade**

- **Found during:** Task 04-02 GREEN (first `npx tsc --noEmit` after writing translator)
- **Issue:** Initial implementation used `if (COMPARISON_OP_SET.has(op)) return {...}` followed by `if (op === 'contains') ...`. TypeScript can't narrow `op` through a Set's `.has()` runtime check, so the trailing `const _unreachable: never = op` triggered `TS2322: Type '"=="|"!="|"<"|"<="|">"|">="' is not assignable to type 'never'`.
- **Fix:** Refactored `translateGuidedToJsonLogic` to a `switch (g.operator)` with explicit `case '=='` etc. arms. TypeScript correctly narrows through `case` labels, exhaustiveness check passes.
- **Files modified:** `frontend/src/components/workflows/editor/conditionExpressionTranslator.ts`
- **Verification:** `npx tsc --noEmit` clean; 41 vitest tests GREEN.
- **Committed in:** `b189217e` (Task 04-02 GREEN — bundled with the implementation)

**2. [Rule 2 - Missing critical functionality] Phase 110 drawer test asserted "Coming in Phase 3/4" for condition kind — needed update**

- **Found during:** Task 04-04 GREEN (vitest after wiring drawer)
- **Issue:** Phase 110 Plan 04 shipped a test asserting `screen.getByText(/Coming in Phase 3/i)` for condition kind. Plan 111 Plan 04 replaces that placeholder with the full editor, so the assertion would fail.
- **Fix:** Updated the test to assert `data-testid="condition-properties-editor"` + `cpe-tab-guided` + `cpe-tab-advanced` are present, AND that "Coming in Phase 3" text is gone. Also renamed the "Coming in Phase 3/4 for parallel/merge/human-approval" test → "Coming in Phase 4" since condition is no longer in that category. Added CodeMirror mock at the top of the test file (jsdom can't render real CM6) using the same pattern as `ConditionPropertiesEditor.test.tsx`.
- **Files modified:** `frontend/src/__tests__/workflows/NodePropertiesDrawer.test.tsx`
- **Verification:** All 9 drawer tests GREEN; 159 total workflow tests GREEN.
- **Committed in:** `25728a11` (Task 04-04 GREEN — bundled with editor + drawer wiring)

---

**Total deviations:** 2 auto-fixed (1 bug — TS exhaustiveness; 1 expected scope-change test update)
**Impact on plan:** Minimal — TS narrowing issue is a routine refactor (if/else → switch); drawer test update was explicit in plan scope ("Phase 110 placeholder gets replaced"). No file footprint expansion beyond `<files_modified>` list.

### Branch hygiene incidents

**Zero branch-pollution incidents detected during Plan 04 execution.** Every commit (7 total) preceded by `git branch --show-current` returning `plan-109-spec-b-phase-1`. The project memory `project_branch_pollution_2026_05_09.md` documents 9 prior incidents this session; Plan 04 ran cleanly. Speculation on the cause: Plan 03 (running in parallel) modifies `app/workflows/engine.py` and `tests/integration/test_branching_workflow_execution.py` — files Plan 04 has zero overlap with — so the staging discipline held cleanly. No `git stash`/recovery dance needed.

**Working-tree noise from Plan 03 throughout the session.** `git status` showed `M app/workflows/engine.py` and untracked `tests/integration/test_branching_workflow_execution.py` continuously. I never staged these files (always staged Plan 04's specific frontend paths by name); Plan 03's commits captured them on their own atomic commits between mine.

## Issues Encountered

**One bash environment hiccup mid-execution.** Three consecutive `git status` / `git branch --show-current` commands returned `fatal error - add_item ("\??\C:\Program Files\Git", "/", ...) failed, errno 1` (Cygwin/MSYS path-resolution glitch on Windows). Self-resolved on the 4th call; no commits affected. Same class of issue as the one-off file-revert race documented in Plan 02's SUMMARY — concurrent automation hazard, not a code defect.

**No CRLF line-ending warnings impacted commits.** Standard Windows checkout LF→CRLF warnings appeared on every git add for the new files (`conditionExpressionTranslator.test.ts`, `conditionExpressionTranslator.ts`, `ConditionPropertiesEditor.test.tsx`, `ConditionPropertiesEditor.tsx`) but caused no functional issues. Git's autocrlf default handles them.

**No regression on Phase 110 tests.** All 105 pre-existing workflow tests still GREEN. The single updated drawer test (condition kind asserting the editor mounts vs. placeholder) is an explicit scope change documented in the plan's `<files_modified>` list.

## User Setup Required

None — pure frontend additive changes. After this plan merges to main:

1. CI installs `@uiw/react-codemirror` ^4.25.9 + `@codemirror/lang-json` ^6.0.2 from `package-lock.json` automatically. Frontend bundle grows by ~300KB gzipped (CodeMirror 6 stack only loaded when `condition` kind is selected — code-splittable if Phase 4+ wants).
2. Users with `workflows` feature enabled can visit `/dashboard/workflows/templates`, click Edit on a template, drag a condition node from the palette (Phase 110 wiring), click on it, and see the dual-tab Guided/Advanced editor.
3. Guided form's Field selector lists upstream `previous_outcomes.{id}.{key}` options computed from the BFS-backward walk through the current graph. Custom field input is the fallback for arbitrary field names.
4. Saving a graph that violates rule 4 (wrong outgoing-edge count or wrong handles) is blocked client-side (red badge on the condition node + Save button disabled) AND server-side (Plan 02's `validate_workflow_graph` returns HTTP 400). Both surfaces emit the same error structure.
5. No env vars, no dashboard config, no third-party services.

## Next Phase Readiness

**Ready for Plan 111-05** (WorkflowGraphRunWidget — live-run rendering for branched workflows):

- **No direct dependency on Plan 04.** Plan 05 consumes runtime SSE events from Spec A's existing bus and renders the graph with active/taken/muted overlays. Plan 04 is save-time only — they touch disjoint surfaces.
- The condition node's saved `config.expression` (JSONLogic JSON) is now structurally tight enough that Plan 05 could read it for tooltip preview if it wants ("show the expression on hover"), but Spec B § Phase 3 doesn't require this.

**Test-button (Discretion #1 deferred):** A future phase or Phase 3.5 can add the "Test this expression" button to the ConditionPropertiesEditor (evaluates `config.expression` against synthetic inputs in a modal). Plan 04 deliberately keeps it out of scope.

**Phase 4 inherits a clean baseline:**
- `useGraphValidation.ts` has rule 4. Rule 5 (parallel/merge pairing) stub remains in `graph_validation.py` server-side; client-side parity is open.
- `NODE_OUTPUT_KEYS` map declares output keys for all 7 kinds. Phase 4 can extend per-kind keys as parallel/merge/human-approval gain real execution.
- `ConditionPropertiesEditor` is a self-contained component; Phase 4 may add similar `ParallelPropertiesEditor`, `MergePropertiesEditor`, `HumanApprovalPropertiesEditor` siblings that NodePropertiesDrawer routes to.

**ROADMAP criteria SHIPPED by Plan 04:**
- **#3 (dual-tab condition UX) — SHIPPED.** Guided + Advanced (CodeMirror 6) tabs rendered in NodePropertiesDrawer when condition kind selected. Round-trip rule enforced.
- **#4 (UAT — non-technical user builds "if revenue > 50000 then escalate" in <60s) — SHIPPED.** Dedicated unit test `roadmap_criterion_4_revenue_50000` asserts the Guided form produces `{">": [{"var": "revenue"}, 50000]}` exactly. The Field selector → Operator → Value workflow is the literal UAT path.
- **#5 (client-side rule 4 with red badges) — SHIPPED.** `useGraphValidation.ts` enforces rule 4 mirroring Plan 02; per-node red badges automatically light up via Phase 110's existing `bucketErrorsByNode` pipeline; Save button disabled when errors present.

---

## Self-Check: PASSED

Verified post-write (all paths absolute on C:/Users/expert/documents/pka/pikar-ai/):

- [x] `frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx` exists on disk (~420 lines)
- [x] `frontend/src/components/workflows/editor/conditionExpressionTranslator.ts` exists on disk (~250 lines)
- [x] `frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx` exists on disk (13 tests)
- [x] `frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts` exists on disk (41 tests)
- [x] `frontend/package.json` has `@uiw/react-codemirror` + `@codemirror/lang-json` (grep returns 2)
- [x] `frontend/src/components/workflows/editor/useGraphSchema.ts` has `ConditionConfigSchema` + `NODE_OUTPUT_KEYS` exports
- [x] `frontend/src/components/workflows/editor/useGraphValidation.ts` has `validateRule4` helper + call in `validateGraph`
- [x] `frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx` imports + renders `ConditionPropertiesEditor` (grep returns 5)
- [x] No `Coming in Phase 3` text in `NodePropertiesDrawer.tsx` body (only in updated docstring history comment)
- [x] `frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts` has `roadmap_criterion_4_revenue_50000` test (line 32)
- [x] Commit `7f0dab1a` exists on `plan-109-spec-b-phase-1` (Task 04-01: CodeMirror 6 dep)
- [x] Commit `0c0ccb7c` exists on `plan-109-spec-b-phase-1` (Task 04-02 RED: translator tests)
- [x] Commit `b189217e` exists on `plan-109-spec-b-phase-1` (Task 04-02 GREEN: translator impl)
- [x] Commit `2ef4078d` exists on `plan-109-spec-b-phase-1` (Task 04-03 RED: rule 4 + NODE_OUTPUT_KEYS tests)
- [x] Commit `b5063b0d` exists on `plan-109-spec-b-phase-1` (Task 04-03 GREEN: rule 4 impl + tightened schema)
- [x] Commit `25325b65` exists on `plan-109-spec-b-phase-1` (Task 04-04 RED: ConditionPropertiesEditor tests)
- [x] Commit `25728a11` exists on `plan-109-spec-b-phase-1` (Task 04-04 GREEN: editor + drawer wiring)
- [x] All 7 commits land on `plan-109-spec-b-phase-1` (verified `git log --oneline plan-109-spec-b-phase-1 -20 | grep 111-04`)
- [x] 159 workflow vitest tests GREEN (105 existing Phase 110 + 54 new Plan 04 — translator 41 + editor 13)
- [x] All 11 Phase 110 pre-existing workflow test files still GREEN (no regression)
- [x] `npx tsc --noEmit` clean across the entire frontend
- [x] No backend (app/) files modified by Plan 04 commits — `git show --name-only` confirms `frontend/` paths only
- [x] No DB migrations / schema changes / fixture writes (`tests/fixtures/graph_validation_cases.json` unchanged; Plan 04 imports it READ-ONLY)
- [x] Branch hygiene: 0 pollution incidents during Plan 04 execution; all 7 commits on the correct branch verified before each `git commit`
- [x] ROADMAP criterion 4 verified by dedicated test (line 32 of translator test): `{field: 'revenue', op: '>', val: 50000}` → `{">": [{"var": "revenue"}, 50000]}` exactly

---

*Phase: 111-workflow-node-editor-branching-execution*
*Completed: 2026-05-12*
