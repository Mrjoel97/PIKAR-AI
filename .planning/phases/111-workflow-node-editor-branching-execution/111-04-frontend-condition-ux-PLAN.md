---
phase: 111-workflow-node-editor-branching-execution
plan: 04
type: execute
wave: 3
depends_on:
  - "111-02"
files_modified:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/components/workflows/editor/useGraphSchema.ts
  - frontend/src/components/workflows/editor/useGraphValidation.ts
  - frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx
  - frontend/src/components/workflows/editor/conditionExpressionTranslator.ts
  - frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx
  - frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx
  - frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts
  - frontend/src/__tests__/workflows/useGraphValidation.test.ts
autonomous: true
gap_closure: false
requirements:
  - NODEEDITOR-EDIT-03
  - NODEEDITOR-VALIDATE-02

must_haves:
  truths:
    - "Selecting a condition node in the editor surfaces the dual-tab ConditionPropertiesEditor (Guided default + Advanced JSON) — NOT the Phase 110 'Coming in Phase 3/4' placeholder"
    - "The Guided tab renders three dropdowns: [Field selector] [Operator] [Value] — populated from upstream nodes' declared output keys (Discretion #4 Option A: static, per-kind output declarations in useGraphSchema)"
    - "The Operator dropdown contains exactly 9 options: == != < <= > >= contains in 'not in'"
    - "Switching from Guided to Advanced auto-translates the current form into a JSONLogic JSON document — the Advanced editor (CodeMirror 6 per Discretion #2) is pre-populated with the translated JSON, formatted with 2-space indent"
    - "Switching from Advanced to Guided attempts to parse the JSONLogic back into the three-dropdown shape; if parsing fails (nested ops, unsupported constructs), the Guided tab becomes read-only and shows the message 'Complex expression — edit in Advanced tab' (round-trip rule from CONTEXT.md decision 1)"
    - "On save, the Guided form ALWAYS persists `config.expression` as a JSONLogic JSON document — NOT the {field, operator, value} triple. Server-side condition routing (Plan 03 graph_executor) reads `config.expression` directly"
    - "useGraphSchema.ts tightens the condition Zod schema from PermissiveConfigSchema to a strict shape: `z.object({ expression: z.unknown() }).strict()` — saved JSONLogic is structurally unknown but the key MUST be present"
    - "useGraphValidation.ts implements rule 4 client-side mirroring Plan 02's server-side _validate_rule_4_condition_outgoing_degree — same algorithm, same set-equality check on source_handle values, same error.rule = 4 + node_id keying"
    - "The shared fixture `tests/fixtures/graph_validation_cases.json` (13 cases after Plan 02) is parametrized in `useGraphValidation.test.ts` and all 13 cases pass on the client (B-4 contract — Plans 02 + 04 must stay aligned)"
    - "ROADMAP criterion 4 UAT pass: the Guided form translation `[revenue] [>] [50000]` produces JSONLogic `{\">\": [{\"var\": \"revenue\"}, 50000]}` (verified by a dedicated unit test in conditionExpressionTranslator.test.ts)"
    - "CodeMirror 6 is added as a frontend dependency (codemirror + @codemirror/lang-json + @codemirror/state + @codemirror/view) — Discretion #2 decision documented"
    - "Saving a condition graph that violates rule 4 (e.g. one outgoing edge) is BLOCKED client-side via the existing Save-button disabled-when-validation-errors gate (Plan 110-04) — Plan 04 just adds new errors to the existing pipeline"
    - "The Field selector lists the union of: (a) static output keys declared per upstream agent-action node kind in useGraphSchema, and (b) a free-text 'custom' input that lets the user type any key — fallback for cases where the upstream produces a non-declared outcome"
  artifacts:
    - path: "frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx"
      provides: "Dual-tab Guided/Advanced editor for condition node config"
      min_lines: 250
    - path: "frontend/src/components/workflows/editor/conditionExpressionTranslator.ts"
      provides: "Pure-function translator: {field, operator, value} ↔ JSONLogic; round-trip detection"
      min_lines: 100
    - path: "frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx"
      provides: "Routes 'condition' kind to ConditionPropertiesEditor (replaces Phase 110 placeholder)"
      contains: "ConditionPropertiesEditor"
    - path: "frontend/src/components/workflows/editor/useGraphSchema.ts"
      provides: "Tightened condition schema + per-kind static output declarations (Discretion #4 Option A)"
      contains: "expression"
    - path: "frontend/src/components/workflows/editor/useGraphValidation.ts"
      provides: "Client-side rule 4 implementation (mirrors graph_validation.py)"
      contains: "rule: 4"
    - path: "frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts"
      provides: "Round-trip + ROADMAP criterion 4 examples"
      min_lines: 150
    - path: "frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx"
      provides: "Tab switching + form behavior + Save translation"
      min_lines: 200
    - path: "frontend/src/__tests__/workflows/useGraphValidation.test.ts"
      provides: "Extended fixture parametrize (13 cases) + rule 4 specific tests"
      contains: "condition_valid_two_handles"
  key_links:
    - from: "frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx"
      to: "ConditionPropertiesEditor"
      via: "switch on selectedNode.kind === 'condition' → render <ConditionPropertiesEditor>"
      pattern: "ConditionPropertiesEditor"
    - from: "frontend/src/components/workflows/editor/useGraphValidation.ts"
      to: "tests/fixtures/graph_validation_cases.json (Plan 02 extended)"
      via: "vitest parametrize loop over the same fixture pytest uses"
      pattern: "graph_validation_cases.json"
    - from: "frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx"
      to: "conditionExpressionTranslator.ts"
      via: "translateGuidedToJsonLogic({field, operator, value}) + translateJsonLogicToGuided(jsonDoc)"
      pattern: "translateGuidedToJsonLogic|translateJsonLogicToGuided"
---

<objective>
Replace the Phase 110 'Coming in Phase 3/4' placeholder in `NodePropertiesDrawer` (for `condition` kind) with the dual-tab Guided/Advanced expression editor locked by CONTEXT.md decision 1. Add CodeMirror 6 (Discretion #2) as the Advanced-tab editor. Ship the bidirectional translator between Guided form `{field, operator, value}` and JSONLogic JSON, the round-trip rule (Guided becomes read-only when an Advanced edit can't be re-parsed), and the client-side rule 4 implementation mirroring Plan 02's server-side validator via the shared fixture.

Purpose: Close ROADMAP criteria 3 (dual-tab UX), 4 (UAT — non-technical user builds "if revenue > 50000 then escalate" in <60s), and 5 client-side (rule 4 with red badges). The B-4 shared-fixture contract from Phase 110 Plan 03/04 stays load-bearing: Plan 02's 5 new rule-4 cases automatically light up in vitest after this plan.

Output: 1 new component (~250 lines), 1 new translator (~100 lines), 2 modified hooks, 1 modified drawer host, 3 new test files. New CodeMirror 6 dep (~300KB gzipped). No backend changes — server-side rule 4 is already enforced by Plan 02.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-CONTEXT.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-02-validation-rule-4-PLAN.md
@.planning/phases/110-workflow-node-editor-editable/110-04-SUMMARY.md
@frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx
@frontend/src/components/workflows/editor/useGraphSchema.ts
@frontend/src/components/workflows/editor/useGraphValidation.ts
@tests/fixtures/graph_validation_cases.json
@CLAUDE.md

<interfaces>
<!-- Phase 110 Plan 04 (already on disk) — extend these. -->

```typescript
// frontend/src/components/workflows/editor/useGraphSchema.ts
export const TriggerConfigSchema = z.object({ trigger_type: ... }).passthrough();
export const AgentActionConfigSchema = z.object({ tool_name: z.string(), ... }).passthrough();
export const OutputConfigSchema = z.object({ output_format: ... }).passthrough();
const PermissiveConfigSchema = z.object({}).passthrough();  // condition uses this — tighten in Plan 04

export const CONFIG_SCHEMAS: Record<NodeKind, z.ZodTypeAny> = {
    trigger: TriggerConfigSchema,
    'agent-action': AgentActionConfigSchema,
    output: OutputConfigSchema,
    condition: PermissiveConfigSchema,  // ← change to ConditionConfigSchema
    parallel: PermissiveConfigSchema,
    merge: PermissiveConfigSchema,
    'human-approval': PermissiveConfigSchema,
};

export type ValidateNodeConfigResult = ReturnType<z.ZodTypeAny['safeParse']>;
export function validateNodeConfig(kind: NodeKind, config: unknown): ValidateNodeConfigResult;
```

```typescript
// frontend/src/components/workflows/editor/useGraphValidation.ts
// Phase 110 Plan 04 — implements rules 1, 2, 3, 6, 7. Plan 111-04 ADDS rule 4.

export interface ValidationError {
    node_id: string | null;
    rule: number;       // currently 1, 2, 3, 6, 7 — Plan 04 adds 4
    message: string;
}

export function validateGraph(
    nodes: Array<{id: string; kind: NodeKind; config: unknown; ...}>,
    edges: Array<{source: string; target: string; source_handle?: string | null}>,
): ValidationError[];

export function bucketErrorsByNode(errors: ValidationError[]): Record<string, ValidationError[]>;
```

```typescript
// frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx (Phase 110 Plan 04)
// Currently: condition kind → "Coming in Phase 3/4" amber panel + readonly label.
// Plan 111-04: condition kind → <ConditionPropertiesEditor node={...} onChange={...} />
```

<!-- Spec B / CONTEXT.md decision 1 — Guided form contract -->

The Guided form produces:
```typescript
interface GuidedExpression {
    field: string;     // e.g. "revenue", "previous_outcomes.a1.lead_score"
    operator: '==' | '!=' | '<' | '<=' | '>' | '>=' | 'contains' | 'in' | 'not in';
    value: string | number | boolean;   // typed input
}
```

Translator output (saved as `config.expression`):
```typescript
// {field: "revenue", operator: ">", value: 50000} →
{ ">": [{"var": "revenue"}, 50000] }

// {field: "category", operator: "==", value: "premium"} →
{ "==": [{"var": "category"}, "premium"] }

// {field: "tags", operator: "contains", value: "urgent"} →
// "contains" = string-contains or array-membership depending on context.
// JSONLogic has no native "contains" — emit "in" with order [substring, full]:
{ "in": ["urgent", {"var": "tags"}] }

// {field: "tier", operator: "in", value: "premium,enterprise"} →
// Array membership: emit "in" with [val, array]; split CSV values:
{ "in": [{"var": "tier"}, ["premium", "enterprise"]] }
// (decision: parse value as CSV if operator === "in" or "not in" and value is string)

// {field: "lead_score", operator: "not in", value: "0,10,20"} →
{ "!": [{ "in": [{"var": "lead_score"}, [0, 10, 20]] }] }
```

<!-- CodeMirror 6 — Discretion #2 winner -->

Packages to add:
- codemirror (^6.x)
- @codemirror/lang-json (^6.x)
- @codemirror/state (^6.x)
- @codemirror/view (^6.x)

(Or use react-codemirror2 / @uiw/react-codemirror as a thin wrapper — Plan 04 executor picks whichever has a stable React component API. Recommendation: @uiw/react-codemirror (simpler React integration) — confirm during Task 04-01.)
</interfaces>

<context_notes>
**Discretion decisions documented (from CONTEXT.md):**

1. **Test-run button (#1): DEFERRED.** Phase 111 does NOT include the Test button — keep scope tight (5 plans, ~4.5 weeks per Spec B estimate). A future phase or Phase 3.5 owns it.
2. **JSON editor library (#2): CodeMirror 6** (~300KB gzipped, JSON syntax highlighting, good a11y) per Spec B recommendation.
3. **Operator semantics (#3):** Keep both `contains` and `in` separate. Translator emits `{"in": [substring, fullstring]}` for `contains` (JSONLogic uses `in` for substring) and `{"in": [val, array]}` for `in` (array membership). The translator decides based on the value type at translate time.
4. **Field selector data source (#4): Option A (static).** Each node kind declares static output keys in useGraphSchema; the Field selector walks the upstream subgraph from the current condition node and collects them. PLUS a "custom" free-text input as fallback.
5. **Dispatch trigger (#5): Option A (kind-based).** Already implemented by Plan 01 + 03.
6. **WorkflowGraphRunWidget placement (#6): `frontend/src/components/widgets/`.** Plan 05 owner.
7. **Active-node visual (#7):** Plan 05 owner.
8. **SSE event shape (#8):** Plan 05 owner. Plan 04 doesn't touch SSE.

**B-4 shared fixture contract (load-bearing):**
- Phase 110 Plan 03 + Plan 04 established the contract: both pytest AND vitest parametrize over `tests/fixtures/graph_validation_cases.json`.
- Plan 02 of THIS phase adds 5 rule-4 cases to that file.
- Plan 04 of THIS phase implements rule 4 client-side AND parametrizes vitest over the now-13-case fixture.
- Any divergence between server (Plan 02) and client (Plan 04) is caught by either test runner — the same `expected_errors` must produce identical `validateGraph` output on both sides (modulo the `message_contains` substring tolerance).

**ConditionPropertiesEditor component contract:**

```typescript
interface ConditionPropertiesEditorProps {
    node: { id: string; kind: 'condition'; label: string; config: { expression?: unknown } };
    upstreamFields: string[];  // computed by parent from upstream subgraph + useGraphSchema output declarations
    onChange: (next: { label?: string; config?: { expression: unknown } }) => void;
    onValidationChange?: (issues: string[]) => void;  // inline form errors
}
```

State machine (per CONTEXT.md decision 1):
- `mode: 'guided' | 'advanced'` (default: 'guided' on mount; persist across re-mounts via local state only)
- `guided: { field, operator, value } | null` (null when expression is uninterpretable in Guided form)
- `advancedJson: string` (the textual JSON in CodeMirror)
- `roundTripFailed: boolean` — set to true when an Advanced JSON edit cannot be re-parsed back into Guided shape; while true, Guided tab shows "Complex expression — edit in Advanced tab" and is read-only.

Behavior:
- Initial mount: read `node.config.expression`; attempt `translateJsonLogicToGuided(expression)`; if success, set `mode='guided'` with the parsed values; if failure, set `mode='advanced'` with `advancedJson = JSON.stringify(expression, null, 2)` and `roundTripFailed = true`.
- User edits Guided form: call `translateGuidedToJsonLogic(guided)` on every change, push the result to `onChange({config: {expression: jsonDoc}})`.
- User clicks Advanced tab: call `translateGuidedToJsonLogic(guided)` to pre-populate the CodeMirror editor; set `mode='advanced'`.
- User edits Advanced JSON: parse the text on every change (debounced); if parse succeeds, push `onChange({config: {expression: parsed}})`. On Guided-tab-click, attempt `translateJsonLogicToGuided`; if it returns a guided triple, set `roundTripFailed=false` and switch to Guided; if it returns null, set `roundTripFailed=true` and stay in Advanced.

**Translator round-trip detection:**

`translateJsonLogicToGuided(expression: unknown): { field, operator, value } | null`

Returns `null` (round-trip failed) when:
- Expression is not a plain object
- Expression has more than one top-level key (nested logic: `{"and": [...]}`, `{"or": [...]}`)
- The operator key is not in the 9-operator dropdown set (== != < <= > >= in '!')
- The operands array doesn't have exactly 2 elements
- The first operand isn't `{"var": "..."}` shape
- The second operand is a complex JSONLogic dict (not a primitive)
- Special handling for "not in" / `{"!": [{"in": [...]}]}` — single nested level OK, deeper nesting → null
- Special handling for "contains" → can re-derive from `{"in": [substring, fullstring]}` shape by inspecting operand types (if first is string and second is `{"var": "..."}`, infer "contains")

Returns the triple otherwise.

**Upstream-fields computation:**

In Plan 04, the upstream subgraph from a condition node is computed in `NodePropertiesDrawer.tsx` (or a helper hook). Algorithm:
1. BFS backward from `selectedNode.id` through `graph_edges` (target → source traversal).
2. Collect agent-action nodes upstream.
3. For each upstream agent-action, look up its declared output keys in `useGraphSchema` (NEW: add `AGENT_ACTION_OUTPUT_KEYS` map keyed by tool_name, with sensible defaults like `['outcome_text', 'output_data', 'duration_ms']` for unknown tools).
4. Emit field names like `previous_outcomes.{node_id}.{output_key}` (matches the JSONLogic var path that Plan 03's graph_executor resolves at runtime).
5. ALSO emit `user_context.{custom_key}` placeholder + a free-text "custom" input as fallback.

For Phase 111 simplicity, the static output keys can be a minimal set: `outcome_text`, `output_data`, `_execution_meta` (from `app/workflows/step_executor.py`'s actual write shape). Plan 04 can hardcode this — Phase 4 or later can elaborate.

**No backend changes in this plan.** Plan 02 already enforces rule 4 server-side; Plan 04 implements the client-side mirror via the shared fixture. The server's rule 4 enforcement on the PUT save path (Plan 110-03 wiring + Plan 02 extension) is the final safety net — Plan 04 just provides faster UX feedback.

**Discretion #1 dispatch trigger doc:** Document in the plan SUMMARY: "Phase 111 Plan 04 ships the dual-tab UX per CONTEXT.md decision 1. Test-run button NOT included — deferred to a future phase per planner Discretion #1 to keep Phase 111 scope tight."

**Branch hygiene:** `git branch --show-current` before every commit — `plan-109-spec-b-phase-1`. Phase 110 Plan 04 had 2 pollution incidents — be vigilant.

**CLAUDE.md conventions:** Next.js 16 App Router, React 19, Tailwind CSS 4. Tests in `frontend/src/__tests__/`. `npx tsc --noEmit` clean before each commit. Vitest runner: `npx vitest run` (NOT `npm test`).
</context_notes>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 04-01: Add CodeMirror 6 dependency + smoke-import test</name>
  <files>frontend/package.json, frontend/package-lock.json</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`.
  </precondition>
  <action>
    From `frontend/` directory, install CodeMirror 6 packages:

    ```bash
    cd frontend && npm install @uiw/react-codemirror @codemirror/lang-json --save
    ```

    `@uiw/react-codemirror` is a thin React wrapper that bundles `codemirror`, `@codemirror/state`, `@codemirror/view` as transitive deps — single install brings the full CM6 stack.

    Verify the dep landed: `grep -E '"(@uiw/react-codemirror|@codemirror/lang-json)"' frontend/package.json` returns 2 lines.

    Smoke-test the import works in TS: from the project root, run `cd frontend && npx tsc --noEmit` — must be clean. (No actual usage yet; just confirms transitive types resolve.)

    DO NOT add other deps. DO NOT bump zod, react, react-flow, or other unrelated deps. If `npm install` proposes incidental bumps, abort and use `--no-save` to test version compat first, then add the lockfile entry surgically.

    Commit message: `feat(111-04): add CodeMirror 6 frontend dep (Discretion #2 — Advanced JSON tab)`.
  </action>
  <verify>
    <automated>grep -E '"(@uiw/react-codemirror|@codemirror/lang-json)"' frontend/package.json</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
  </verify>
  <done>
    - `frontend/package.json` has both packages.
    - `frontend/package-lock.json` updated with transitive CM6 deps.
    - `npx tsc --noEmit` clean.
    - One commit on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-02: conditionExpressionTranslator — pure-function bidirectional translator</name>
  <files>frontend/src/components/workflows/editor/conditionExpressionTranslator.ts, frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 04-01 committed.
  </precondition>
  <behavior>
    **RED phase — write tests first:**

    `frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts`, ≥18 tests:

    Translation: Guided → JSONLogic
    1. `translates_gt_50000` — `{field: 'revenue', operator: '>', value: 50000}` → `{">": [{"var": "revenue"}, 50000]}`. **ROADMAP criterion 4 EXACT requirement.**
    2. `translates_eq_string` — `{field: 'category', operator: '==', value: 'premium'}` → `{"==": [{"var": "category"}, "premium"]}`.
    3. `translates_neq_number` — `{field: 'count', operator: '!=', value: 0}` → `{"!=": [{"var": "count"}, 0]}`.
    4. `translates_lt_gte_lte` — three separate tests for `<`, `>=`, `<=`.
    5. `translates_contains_string` — `{field: 'tags', operator: 'contains', value: 'urgent'}` → `{"in": ["urgent", {"var": "tags"}]}` (substring semantics, value-then-var order).
    6. `translates_in_array` — `{field: 'tier', operator: 'in', value: 'premium,enterprise'}` → `{"in": [{"var": "tier"}, ["premium", "enterprise"]]}` (CSV-split, var-then-array order).
    7. `translates_in_array_numeric` — `{field: 'score', operator: 'in', value: '10,20,30'}` → `{"in": [{"var": "score"}, [10, 20, 30]]}` (numeric coercion when ALL CSV entries parse as numbers; else strings).
    8. `translates_not_in_array` — `{field: 'status', operator: 'not in', value: 'cancelled,refunded'}` → `{"!": [{"in": [{"var": "status"}, ["cancelled", "refunded"]]}]}`.
    9. `translates_boolean_value` — `{field: 'is_active', operator: '==', value: true}` → `{"==": [{"var": "is_active"}, true]}`.

    Translation: JSONLogic → Guided
    10. `parses_basic_gt` — `{">": [{"var": "revenue"}, 50000]}` → `{field: 'revenue', operator: '>', value: 50000}`.
    11. `parses_eq_string` — `{"==": [{"var": "category"}, "premium"]}` → `{field: 'category', operator: '==', value: 'premium'}`.
    12. `parses_in_array_back` — `{"in": [{"var": "tier"}, ["premium", "enterprise"]]}` → `{field: 'tier', operator: 'in', value: 'premium,enterprise'}` (CSV-join).
    13. `parses_contains_back` — `{"in": ["urgent", {"var": "tags"}]}` → `{field: 'tags', operator: 'contains', value: 'urgent'}` (detected by operand-order convention).
    14. `parses_not_in_back` — `{"!": [{"in": [{"var": "status"}, ["a", "b"]]}]}` → `{field: 'status', operator: 'not in', value: 'a,b'}`.

    Round-trip failure cases (returns `null`)
    15. `fails_round_trip_for_and` — `{"and": [{">": [...]}, {"<": [...]}]}` → `null`.
    16. `fails_round_trip_for_nested` — `{">": [{"+": [{"var": "a"}, 1]}, 5]}` → `null` (operand is computed, not a var).
    17. `fails_round_trip_for_unknown_op` — `{"unknown_op": [{"var": "x"}, 5]}` → `null`.
    18. `fails_round_trip_for_empty` — `{}` → `null` and `null` (parameter) → `null`.

    Idempotency
    19. `roundtrip_idempotent_for_all_guided_shapes` — for each of the 9 operators, generate a guided triple, translate to JSONLogic, parse back, assert the result equals the original triple (modulo CSV-join order). Loop test using `it.each` or similar.

    Commit RED: `test(111-04): add failing translator tests (ROADMAP criterion 4 + round-trip rule)`.

    **GREEN phase — implement:**

    `frontend/src/components/workflows/editor/conditionExpressionTranslator.ts`:

    ```typescript
    // Copyright (c) 2024-2026 Pikar AI. All rights reserved.
    // Proprietary and confidential. See LICENSE file for details.

    export type Operator =
      | '==' | '!=' | '<' | '<=' | '>' | '>=' | 'contains' | 'in' | 'not in';

    export const OPERATORS: readonly Operator[] = [
      '==', '!=', '<', '<=', '>', '>=', 'contains', 'in', 'not in',
    ];

    export interface GuidedExpression {
      field: string;
      operator: Operator;
      value: string | number | boolean;
    }

    type JsonLogic = Record<string, unknown>;

    function coerceCsvValues(csv: string): (string | number)[] {
      const parts = csv.split(',').map(s => s.trim()).filter(Boolean);
      // If all parts parse as numbers, return numbers; else strings.
      const numbers = parts.map(p => Number(p));
      if (numbers.every(n => !Number.isNaN(n) && /^[-+]?\d+(\.\d+)?$/.test(parts[numbers.indexOf(n)] ?? ''))) {
        return numbers;
      }
      return parts;
    }

    export function translateGuidedToJsonLogic(g: GuidedExpression): JsonLogic {
      const varRef = { var: g.field };
      switch (g.operator) {
        case '==':
        case '!=':
        case '<':
        case '<=':
        case '>':
        case '>=':
          return { [g.operator]: [varRef, g.value] };
        case 'contains':
          // JSONLogic uses "in" for both string-in-string and array-membership.
          // For "contains" semantics (substring in string), emit:
          //   {"in": [<substring>, <var>]}   — substring first.
          return { in: [g.value, varRef] };
        case 'in':
          // Array membership: {"in": [<var>, <array>]}
          return {
            in: [
              varRef,
              typeof g.value === 'string' ? coerceCsvValues(g.value) : [g.value],
            ],
          };
        case 'not in':
          return {
            '!': [
              {
                in: [
                  varRef,
                  typeof g.value === 'string' ? coerceCsvValues(g.value) : [g.value],
                ],
              },
            ],
          };
        default: {
          const _: never = g.operator;
          throw new Error(`Unsupported operator: ${_}`);
        }
      }
    }

    export function translateJsonLogicToGuided(
      expr: unknown,
    ): GuidedExpression | null {
      if (!expr || typeof expr !== 'object' || Array.isArray(expr)) return null;
      const keys = Object.keys(expr as object);
      if (keys.length !== 1) return null;
      const [op] = keys;
      const operands = (expr as Record<string, unknown>)[op];
      if (!Array.isArray(operands)) return null;

      // Direct binary comparisons
      if ((['==', '!=', '<', '<=', '>', '>='] as const).includes(op as never)) {
        if (operands.length !== 2) return null;
        const [a, b] = operands;
        if (!isVarRef(a)) return null;
        if (typeof b === 'object' && b !== null) return null;  // computed operand
        return {
          field: (a as { var: string }).var,
          operator: op as Operator,
          value: b as string | number | boolean,
        };
      }

      // "in" — two semantics depending on operand order
      if (op === 'in') {
        if (operands.length !== 2) return null;
        const [a, b] = operands;
        if (isVarRef(a) && Array.isArray(b)) {
          // {"in": [{"var": ...}, [arr]]} — array membership
          return {
            field: (a as { var: string }).var,
            operator: 'in',
            value: b.join(','),
          };
        }
        if ((typeof a === 'string' || typeof a === 'number') && isVarRef(b)) {
          // {"in": [<substr>, {"var": ...}]} — contains
          return {
            field: (b as { var: string }).var,
            operator: 'contains',
            value: a as string | number,
          };
        }
        return null;
      }

      // "not in" — {"!": [{"in": [...]}]}
      if (op === '!') {
        if (operands.length !== 1) return null;
        const inner = operands[0];
        if (!inner || typeof inner !== 'object' || Array.isArray(inner)) return null;
        const innerKeys = Object.keys(inner as object);
        if (innerKeys.length !== 1 || innerKeys[0] !== 'in') return null;
        const innerOperands = (inner as { in: unknown }).in;
        if (!Array.isArray(innerOperands) || innerOperands.length !== 2) return null;
        const [a, b] = innerOperands;
        if (!isVarRef(a) || !Array.isArray(b)) return null;
        return {
          field: (a as { var: string }).var,
          operator: 'not in',
          value: b.join(','),
        };
      }

      return null;
    }

    function isVarRef(x: unknown): x is { var: string } {
      return (
        typeof x === 'object' &&
        x !== null &&
        !Array.isArray(x) &&
        Object.keys(x).length === 1 &&
        'var' in x &&
        typeof (x as { var: unknown }).var === 'string'
      );
    }
    ```

    Commit GREEN: `feat(111-04): condition expression translator (Guided ↔ JSONLogic)`.

    Run all 19 tests — must be GREEN.
  </behavior>
  <action>
    Follow the behavior block. Implementation is ~150 lines. Use vitest, TypeScript strict mode. Verify `npx tsc --noEmit` clean before commit.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/conditionExpressionTranslator.test.ts --reporter=verbose</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
  </verify>
  <done>
    - 19 vitest tests GREEN.
    - tsc clean.
    - Two commits on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-03: useGraphSchema tightening + useGraphValidation rule 4 (B-4 client parity)</name>
  <files>frontend/src/components/workflows/editor/useGraphSchema.ts, frontend/src/components/workflows/editor/useGraphValidation.ts, frontend/src/__tests__/workflows/useGraphValidation.test.ts</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 04-01 + 04-02 committed.
    Verify Plan 02 (Wave 1) shipped: `python -c "import json; cases = json.load(open('tests/fixtures/graph_validation_cases.json')); assert len(cases) == 13"`.
  </precondition>
  <behavior>
    **RED phase — extend `frontend/src/__tests__/workflows/useGraphValidation.test.ts`:**

    Phase 110 Plan 04 already parametrizes vitest over the 8-case fixture. Plan 02 of THIS phase extended it to 13 cases. Re-running the existing parametrized test should auto-pick-up the 5 new cases — but since the client doesn't yet implement rule 4, the 5 new cases will RED.

    Also ADD 4 explicit rule-4 tests (mirror Plan 02's server-side):
    1. `test_rule_4_no_outgoing_emits_error` — condition with 0 outgoing → 1 rule-4 error.
    2. `test_rule_4_three_outgoing_emits_error` — 3 outgoing → 1 rule-4 error.
    3. `test_rule_4_correct_handles_no_error` — 2 outgoing with handles ('true', 'false') → empty errors (for that node).
    4. `test_rule_4_handle_set_with_null_emits_error` — 2 outgoing where one has source_handle = null → rule-4 error.

    Commit RED: `test(111-04): expand validation tests for rule 4 + fixture parity (13 cases)`.

    **GREEN phase — implement two surgical edits:**

    **Edit 1: `frontend/src/components/workflows/editor/useGraphSchema.ts`**

    Replace the line `condition: PermissiveConfigSchema` in `CONFIG_SCHEMAS` with:
    ```typescript
    export const ConditionConfigSchema = z.object({
      expression: z.unknown(),
    }).passthrough();   // expression is structurally unknown (JSONLogic); other keys allowed for forward compat

    export const CONFIG_SCHEMAS: Record<NodeKind, z.ZodTypeAny> = {
      ...
      condition: ConditionConfigSchema,
      ...
    };
    ```

    Also ADD a per-kind static output declaration map (Discretion #4 Option A):
    ```typescript
    /**
     * Static output keys each node kind declares. Plan 111-04 uses this to
     * populate the Guided Field selector in ConditionPropertiesEditor.
     *
     * Spec B Phase 4+ may expand this; for Phase 111 a minimal set keeps
     * the UX deterministic and doesn't depend on run history (Option A).
     */
    export const NODE_OUTPUT_KEYS: Record<NodeKind, string[]> = {
      trigger: ['outcome_text', 'user_context'],
      'agent-action': ['outcome_text', 'output_data', '_execution_meta'],
      output: [],  // outputs don't feed downstream
      condition: [],   // condition routing happens BEFORE evaluation, no outputs to consume
      parallel: ['outcome_text'],
      merge: ['outcome_text'],
      'human-approval': ['outcome_text', 'approved_by'],
    };
    ```

    **Edit 2: `frontend/src/components/workflows/editor/useGraphValidation.ts`**

    Add a `validateRule4` helper mirroring `_validate_rule_4_condition_outgoing_degree`:
    ```typescript
    function validateRule4(
      nodes: NodeForValidation[],
      edges: EdgeForValidation[],
    ): ValidationError[] {
      const errors: ValidationError[] = [];
      // Group edges by source
      const outgoingBySource = new Map<string, EdgeForValidation[]>();
      for (const e of edges) {
        if (!e.source) continue;
        const arr = outgoingBySource.get(e.source) ?? [];
        arr.push(e);
        outgoingBySource.set(e.source, arr);
      }
      // Iterate nodes in declaration order for determinism (matches server)
      for (const node of nodes) {
        if (node.kind !== 'condition') continue;
        const outEdges = outgoingBySource.get(node.id) ?? [];
        const handles = new Set(outEdges.map(e => e.source_handle ?? null));
        const isValid =
          outEdges.length === 2 &&
          handles.has('true') &&
          handles.has('false') &&
          handles.size === 2;
        if (!isValid) {
          const handlesList = [...handles].map(h => JSON.stringify(h)).sort().join(', ');
          errors.push({
            node_id: node.id,
            rule: 4,
            message: `Condition node must have exactly 2 outgoing edges with source_handle set to 'true' and 'false' (got ${outEdges.length} edges with handles [${handlesList}])`,
          });
        }
      }
      return errors;
    }
    ```

    Call it from `validateGraph()` AFTER the existing rule 7 loop:
    ```typescript
    errors.push(...validateRule4(nodes, edges));
    ```

    Commit GREEN: `feat(111-04): client-side rule 4 + tightened condition Zod schema`.

    Verify the 13-case parametrized loop is now all-green + the 4 explicit tests pass.
  </behavior>
  <action>
    Follow the behavior block. After GREEN, run the FULL workflows test suite to catch unintended regressions: `cd frontend && npx vitest run src/__tests__/workflows/ --reporter=verbose`. All 90 pre-existing Phase 110 tests should still pass + Plan 04's new ones.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/useGraphValidation.test.ts --reporter=verbose</automated>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
  </verify>
  <done>
    - `useGraphValidation.ts` has `validateRule4` helper + call inside `validateGraph`.
    - `useGraphSchema.ts` has `ConditionConfigSchema` AND `NODE_OUTPUT_KEYS` map.
    - 13 fixture-parametrized cases + 4 explicit rule-4 tests GREEN.
    - All Phase 110 vitest workflow tests still GREEN (no regression).
    - tsc clean.
    - Two commits on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-04: ConditionPropertiesEditor + drawer wiring</name>
  <files>frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx, frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx, frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 04-01/02/03 committed.
  </precondition>
  <behavior>
    **RED phase — `frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx`, ≥12 tests:**

    1. `renders_guided_tab_by_default_for_empty_expression` — mount with `node.config = {}` → Guided tab visible + active, Advanced tab visible.
    2. `renders_three_dropdowns` — Guided tab shows Field selector + Operator dropdown + Value input.
    3. `operator_dropdown_has_nine_options` — Operator dropdown contains exactly: == != < <= > >= contains in 'not in'.
    4. `field_selector_lists_upstream_fields` — pass `upstreamFields = ['previous_outcomes.a1.outcome_text', 'user_context.revenue']` → both appear as options + a "custom" free-text input.
    5. `custom_field_input_propagates_value` — type "revenue" in custom field → onChange fires with `{config: {expression: {">": [{"var": "revenue"}, ...]}}}` (or current operator/value).
    6. `roadmap_criterion_4_revenue_50000` — fill field='revenue', operator='>', value='50000' (string typed, coerced to number on save) → onChange last call's `config.expression` equals `{">": [{"var": "revenue"}, 50000]}` EXACTLY. **This is the load-bearing UAT test.**
    7. `clicking_advanced_tab_pre_populates_with_translated_json` — fill Guided form → click Advanced tab → CodeMirror editor (or a testable wrapper) contains the JSON string `{">": [{"var": "revenue"}, 50000]}` with 2-space indent.
    8. `editing_advanced_json_propagates_to_onchange` — simulate user typing valid JSON in Advanced → onChange fires with the parsed JSON.
    9. `switching_back_to_guided_round_trips_when_simple` — Guided → Advanced → no edit → Guided → form pre-populated with same values.
    10. `switching_back_to_guided_shows_readonly_when_complex` — Advanced → user types `{"and": [{...}, {...}]}` (nested) → Guided tab → Guided form is read-only + shows "Complex expression — edit in Advanced tab" message.
    11. `mounts_in_advanced_when_initial_expression_is_complex` — `node.config.expression = {"and": [...]}` → mount → mode=advanced, roundTripFailed=true, message visible.
    12. `invalid_json_in_advanced_does_not_corrupt_state` — type "{" in Advanced (parse fail) → onChange NOT called (debounce + parse-fail safe); inline error shown.

    Use React Testing Library + vitest. For CodeMirror: mock `@uiw/react-codemirror` if its rendering breaks in jsdom (Phase 110 Plan 04 mocked `@xyflow/react` similarly — see `frontend/src/__tests__/workflows/NodeCanvas.test.tsx` for the pattern). A minimal mock:
    ```typescript
    vi.mock('@uiw/react-codemirror', () => ({
      default: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
        <textarea data-testid="cm-editor" value={value} onChange={e => onChange(e.target.value)} />
      ),
    }));
    ```

    Commit RED: `test(111-04): add failing tests for ConditionPropertiesEditor (dual-tab + round-trip)`.

    **GREEN phase — implement `frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx` (~250 lines):**

    Structure:
    ```typescript
    'use client';
    import { useState, useEffect, useMemo } from 'react';
    import CodeMirror from '@uiw/react-codemirror';
    import { json as jsonLang } from '@codemirror/lang-json';
    import {
      OPERATORS,
      translateGuidedToJsonLogic,
      translateJsonLogicToGuided,
      type GuidedExpression,
      type Operator,
    } from './conditionExpressionTranslator';

    export interface ConditionPropertiesEditorProps {
      node: {
        id: string;
        kind: 'condition';
        label: string;
        config: { expression?: unknown };
      };
      upstreamFields: string[];
      onChange: (next: { label?: string; config?: { expression: unknown } }) => void;
    }

    export function ConditionPropertiesEditor({
      node,
      upstreamFields,
      onChange,
    }: ConditionPropertiesEditorProps) {
      // Determine initial mode from existing expression
      const initial = useMemo(
        () => translateJsonLogicToGuided(node.config.expression),
        [node.config.expression],
      );
      const [mode, setMode] = useState<'guided' | 'advanced'>(
        initial ? 'guided' : (node.config.expression ? 'advanced' : 'guided'),
      );
      const [guided, setGuided] = useState<GuidedExpression>(
        initial ?? { field: '', operator: '==' as Operator, value: '' },
      );
      const [advancedJson, setAdvancedJson] = useState<string>(
        node.config.expression
          ? JSON.stringify(node.config.expression, null, 2)
          : JSON.stringify(initial ? translateGuidedToJsonLogic(initial) : {}, null, 2),
      );
      const [roundTripFailed, setRoundTripFailed] = useState<boolean>(
        !!node.config.expression && !initial,
      );
      const [jsonParseError, setJsonParseError] = useState<string | null>(null);
      const [customFieldMode, setCustomFieldMode] = useState<boolean>(false);

      // Guided form updates push translated JSON via onChange
      useEffect(() => {
        if (mode !== 'guided' || roundTripFailed) return;
        // Coerce value type based on input
        const coercedValue = coerceValue(guided.value);
        const jsonLogic = translateGuidedToJsonLogic({ ...guided, value: coercedValue });
        onChange({ config: { expression: jsonLogic } });
      }, [guided, mode, roundTripFailed]);

      // Tab switch: Guided → Advanced
      const switchToAdvanced = () => {
        if (mode === 'advanced') return;
        const json = translateGuidedToJsonLogic(guided);
        setAdvancedJson(JSON.stringify(json, null, 2));
        setMode('advanced');
      };

      // Tab switch: Advanced → Guided
      const switchToGuided = () => {
        if (mode === 'guided') return;
        try {
          const parsed = JSON.parse(advancedJson);
          const parsedGuided = translateJsonLogicToGuided(parsed);
          if (parsedGuided) {
            setGuided(parsedGuided);
            setRoundTripFailed(false);
          } else {
            setRoundTripFailed(true);
          }
        } catch {
          setRoundTripFailed(true);
        }
        setMode('guided');
      };

      // Advanced editor change handler
      const handleAdvancedChange = (text: string) => {
        setAdvancedJson(text);
        try {
          const parsed = JSON.parse(text);
          setJsonParseError(null);
          onChange({ config: { expression: parsed } });
        } catch (err) {
          setJsonParseError(String(err));
          // Don't propagate invalid JSON
        }
      };

      // ... render tabs + Guided form (3 dropdowns) + Advanced editor + readonly notice ...
    }

    function coerceValue(raw: string | number | boolean): string | number | boolean {
      if (typeof raw !== 'string') return raw;
      // Try number first
      if (/^[-+]?\d+(\.\d+)?$/.test(raw)) return Number(raw);
      // Try boolean
      if (raw === 'true') return true;
      if (raw === 'false') return false;
      return raw;
    }
    ```

    Then wire into `NodePropertiesDrawer.tsx`:

    Find the existing `condition` branch (currently shows "Coming in Phase 3/4" placeholder). Replace with:

    ```tsx
    {selectedNode.kind === 'condition' && (
      <ConditionPropertiesEditor
        node={selectedNode}
        upstreamFields={computedUpstreamFields}
        onChange={handleConditionChange}
      />
    )}
    ```

    The `computedUpstreamFields` should be passed in as a prop OR computed locally via the BFS walk described in `<context_notes>`. For Plan 04's scope, computing it in NodePropertiesDrawer is cleanest — add a small helper `computeUpstreamFields(nodes, edges, selectedNodeId)` that walks backward, collects agent-action nodes, and emits `previous_outcomes.{id}.{key}` for each declared output key in NODE_OUTPUT_KEYS, plus a final 'user_context.{custom_key}' placeholder list.

    Commit GREEN: `feat(111-04): ConditionPropertiesEditor + drawer wiring (CONTEXT decision 1)`.

    Verify all 12 ConditionPropertiesEditor tests GREEN + all 90+ pre-existing Phase 110 vitest tests GREEN.
  </behavior>
  <action>
    Follow the behavior block. Component is the heaviest file in Plan 04 (~250 lines). Use Tailwind for styling consistent with Plan 110-04's NodePropertiesDrawer (find a similar drawer component as a style template).

    Drawer wiring is a 5-10 line change to NodePropertiesDrawer.tsx — preserve all other kinds' behavior.

    The `computeUpstreamFields` helper can be inline in NodePropertiesDrawer or extracted to a sibling util (~30 lines).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ConditionPropertiesEditor.test.tsx --reporter=verbose</automated>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
    <automated>grep -c "ConditionPropertiesEditor" frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx</automated>
  </verify>
  <done>
    - `ConditionPropertiesEditor.tsx` exists (≥250 lines, ~12 tests pass).
    - `NodePropertiesDrawer.tsx` routes `condition` kind to the new editor (Phase 110 placeholder removed).
    - All Phase 110 vitest workflow tests still GREEN.
    - tsc clean.
    - Two commits on `plan-109-spec-b-phase-1`.
  </done>
</task>

</tasks>

<verification>
**Plan-level checks before SUMMARY:**

1. `git branch --show-current` returns `plan-109-spec-b-phase-1`.
2. `cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic` — all workflow tests GREEN (90 from Phase 110 + ~35 new from Plan 04 = ~125 tests).
3. `cd frontend && npx tsc --noEmit` — clean.
4. CodeMirror 6 deps present: `grep -c "@codemirror\|@uiw/react-codemirror" frontend/package.json` ≥ 2.
5. Server-side rule 4 unchanged: `grep -c "rule=4" app/workflows/graph_validation.py` should still be ≥ 1 from Plan 02.
6. Shared fixture parity: pytest parametrized loop still passes the 13 cases server-side; vitest passes them client-side.
7. No backend Python files modified in this plan: `git diff plan-109-spec-b-phase-1 -- app/ supabase/` should be empty for THIS plan's commits.
8. ConditionPropertiesEditor imports translator: `grep -c "translateGuidedToJsonLogic\|translateJsonLogicToGuided" frontend/src/components/workflows/editor/ConditionPropertiesEditor.tsx` ≥ 2.
9. ROADMAP criterion 4 explicit test exists: `grep -n "revenue.*50000" frontend/src/__tests__/workflows/conditionExpressionTranslator.test.ts` returns a match for `{">": [{"var": "revenue"}, 50000]}`.
10. Drawer placeholder replaced: `grep -c "Coming in Phase 3" frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx` should be at most 1 (for parallel/merge/human-approval kinds still placeholder — Phase 4). The condition placeholder text MUST be gone.
</verification>

<success_criteria>
- ROADMAP criterion 3 SHIPPED: dual-tab Guided/Advanced UX rendered in NodePropertiesDrawer for condition kind, with round-trip rule enforced.
- ROADMAP criterion 4 SHIPPED: dedicated unit test `roadmap_criterion_4_revenue_50000` asserts Guided form produces `{">": [{"var": "revenue"}, 50000]}` on save (UAT-grade evidence).
- ROADMAP criterion 5 SHIPPED on the client side: `useGraphValidation.ts` implements rule 4 mirroring server; shared fixture parametrize loop catches divergence; per-node red badges (existing Phase 110 pipeline) automatically light up.
- CodeMirror 6 + JSON language adapter shipped as deps; Advanced tab uses them for syntax-highlighted JSONLogic editing.
- B-4 fixture parity preserved: 13 cases pass on BOTH server (Plan 02) and client (Plan 04).
- Test-button NOT in Phase 111 scope — documented in plan SUMMARY (planner Discretion #1).
- ~7-9 commits on `plan-109-spec-b-phase-1` (TDD splits across 4 tasks).
</success_criteria>

<output>
After completion, create `.planning/phases/111-workflow-node-editor-branching-execution/111-04-SUMMARY.md` mirroring Phase 110 Plan 04's SUMMARY structure (frontend-heavy plan SUMMARY format).
</output>
