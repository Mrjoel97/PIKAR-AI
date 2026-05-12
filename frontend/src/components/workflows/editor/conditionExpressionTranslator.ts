// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Bidirectional translator between the Guided form
 * {field, operator, value} triple and JSONLogic JSON — Phase 111 Plan 04.
 *
 * The Guided tab in `ConditionPropertiesEditor` produces simple ternary
 * expressions. The Advanced (JSON) tab accepts arbitrary JSONLogic. This
 * module is the single source of truth for converting between the two.
 *
 * Round-trip rule (CONTEXT.md decision 1): when the user switches from the
 * Advanced tab back to Guided, we attempt `translateJsonLogicToGuided` on
 * the typed JSON. If it returns `null` (nested logic, computed operands,
 * unknown ops), the Guided tab stays read-only and shows the message
 * "Complex expression — edit in Advanced tab".
 *
 * Operator semantics (CONTEXT.md Discretion #3):
 *   - "contains" → JSONLogic `{"in": [<substring>, <var>]}` (substring-in-string)
 *   - "in"       → JSONLogic `{"in": [<var>, [<array>]]}`  (array membership)
 *   - "not in"   → JSONLogic `{"!": [{"in": [<var>, [<array>]]}]}`
 *
 * The two `in`-shaped forms are distinguished by operand order on parse.
 */

export type Operator =
    | '=='
    | '!='
    | '<'
    | '<='
    | '>'
    | '>='
    | 'contains'
    | 'in'
    | 'not in';

/**
 * The 9 operators surfaced in the Guided-tab Operator dropdown. Order
 * matches the dropdown rendering — { Equals, Not equals, Less, …, Not in }.
 */
export const OPERATORS: readonly Operator[] = [
    '==',
    '!=',
    '<',
    '<=',
    '>',
    '>=',
    'contains',
    'in',
    'not in',
] as const;

const COMPARISON_OPS: readonly Operator[] = [
    '==',
    '!=',
    '<',
    '<=',
    '>',
    '>=',
] as const;

const COMPARISON_OP_SET: ReadonlySet<string> = new Set(COMPARISON_OPS);

/** Guided form shape — the {field, operator, value} triple. */
export interface GuidedExpression {
    field: string;
    operator: Operator;
    value: string | number | boolean;
}

type JsonLogic = Record<string, unknown>;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

const NUMBER_LITERAL_RE = /^[-+]?\d+(\.\d+)?$/;

/**
 * Parse a CSV string into `(string | number)[]`. If every comma-separated
 * token matches the number-literal regex, returns a number[] — otherwise
 * returns a string[]. Whitespace around tokens is trimmed; empty tokens are
 * dropped.
 *
 * @example
 *   coerceCsvValues("10, 20, 30") → [10, 20, 30]
 *   coerceCsvValues("a,b,c")      → ["a", "b", "c"]
 *   coerceCsvValues("10, foo")    → ["10", "foo"]
 */
function coerceCsvValues(csv: string): (string | number)[] {
    const parts = csv
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    if (parts.length === 0) return [];
    if (parts.every((p) => NUMBER_LITERAL_RE.test(p))) {
        return parts.map((p) => Number(p));
    }
    return parts;
}

/** Type guard: `{var: "..."}` shape with a single string key. */
function isVarRef(x: unknown): x is { var: string } {
    if (typeof x !== 'object' || x === null || Array.isArray(x)) return false;
    const keys = Object.keys(x);
    if (keys.length !== 1 || keys[0] !== 'var') return false;
    const v = (x as { var: unknown }).var;
    return typeof v === 'string';
}

/** Primitive-value guard. */
function isPrimitive(x: unknown): x is string | number | boolean {
    return (
        typeof x === 'string' ||
        typeof x === 'number' ||
        typeof x === 'boolean'
    );
}

/** Plain (non-array, non-null) object guard. */
function isPlainObject(x: unknown): x is Record<string, unknown> {
    return typeof x === 'object' && x !== null && !Array.isArray(x);
}

// ---------------------------------------------------------------------------
// Guided → JSONLogic
// ---------------------------------------------------------------------------

/**
 * Translate a {field, operator, value} triple into a JSONLogic JSON doc.
 *
 * For `in` / `not in`: if `value` is a string, it is treated as CSV and
 * split into an array (with numeric coercion when every entry parses as a
 * number). If `value` is a primitive (number/boolean), it is wrapped into
 * a single-element array.
 *
 * For `contains`: emits `{"in": [<value>, {"var": <field>}]}` — note the
 * operand order is REVERSED relative to the array-membership `in`. This is
 * how we distinguish the two on parse (operand-order convention).
 */
export function translateGuidedToJsonLogic(
    g: GuidedExpression,
): JsonLogic {
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
            // JSONLogic uses `in` for both string-contains and array-membership.
            // For "contains" semantics (substring in string), substring is FIRST.
            return { in: [g.value, varRef] };
        case 'in': {
            // Array membership: {"in": [<var>, <array>]}
            const arr =
                typeof g.value === 'string'
                    ? coerceCsvValues(g.value)
                    : [g.value];
            return { in: [varRef, arr] };
        }
        case 'not in': {
            const arr =
                typeof g.value === 'string'
                    ? coerceCsvValues(g.value)
                    : [g.value];
            return {
                '!': [
                    {
                        in: [varRef, arr],
                    },
                ],
            };
        }
        default: {
            // Exhaustiveness check
            const _unreachable: never = g.operator;
            throw new Error(
                `Unsupported operator: ${String(_unreachable)}`,
            );
        }
    }
}

// ---------------------------------------------------------------------------
// JSONLogic → Guided
// ---------------------------------------------------------------------------

/**
 * Attempt to parse a JSONLogic JSON doc back into the Guided
 * {field, operator, value} triple. Returns `null` when the document is
 * NOT decomposable into the simple ternary shape — the caller must then
 * keep the user in the Advanced tab (round-trip rule).
 *
 * Returns null when:
 *   - `expr` is not a plain object (null, undefined, arrays, primitives)
 *   - `expr` has != 1 top-level key
 *   - The operator key isn't in the 9-operator set (== != < <= > >= in '!')
 *   - The operands array doesn't have the expected arity (2 for binary,
 *     1 for "!")
 *   - The "var" operand isn't a simple `{var: "..."}` ref
 *   - The non-var operand is itself a JSONLogic dict (computed value)
 *   - For "not in": the inner expression isn't a single-level "in" form
 */
export function translateJsonLogicToGuided(
    expr: unknown,
): GuidedExpression | null {
    if (!isPlainObject(expr)) return null;
    const keys = Object.keys(expr);
    if (keys.length !== 1) return null;
    const [op] = keys;
    const operands = expr[op];

    if (!Array.isArray(operands)) return null;

    // ----- direct binary comparisons -----
    if (COMPARISON_OP_SET.has(op)) {
        if (operands.length !== 2) return null;
        const [a, b] = operands;
        if (!isVarRef(a)) return null;
        // The other operand must be a literal primitive — computed JSONLogic
        // sub-expressions break the round-trip rule.
        if (!isPrimitive(b)) return null;
        return {
            field: a.var,
            operator: op as Operator,
            value: b,
        };
    }

    // ----- "in" — two semantics by operand order -----
    if (op === 'in') {
        if (operands.length !== 2) return null;
        const [a, b] = operands;
        // Array membership: {"in": [{"var": ...}, [arr]]}
        if (isVarRef(a) && Array.isArray(b)) {
            // Each array entry must be a primitive (no nested expressions).
            if (!b.every(isPrimitive)) return null;
            return {
                field: a.var,
                operator: 'in',
                value: b.join(','),
            };
        }
        // Contains: {"in": [<primitive>, {"var": ...}]}
        if (isPrimitive(a) && isVarRef(b)) {
            return {
                field: b.var,
                operator: 'contains',
                value: a,
            };
        }
        return null;
    }

    // ----- "not in" — {"!": [{"in": [...]}]} -----
    if (op === '!') {
        if (operands.length !== 1) return null;
        const inner = operands[0];
        if (!isPlainObject(inner)) return null;
        const innerKeys = Object.keys(inner);
        if (innerKeys.length !== 1 || innerKeys[0] !== 'in') return null;
        const innerOperands = inner.in;
        if (!Array.isArray(innerOperands) || innerOperands.length !== 2) {
            return null;
        }
        const [a, b] = innerOperands;
        if (!isVarRef(a) || !Array.isArray(b)) return null;
        if (!b.every(isPrimitive)) return null;
        return {
            field: a.var,
            operator: 'not in',
            value: b.join(','),
        };
    }

    return null;
}
