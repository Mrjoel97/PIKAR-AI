// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for conditionExpressionTranslator — Phase 111 Plan 04.
 *
 * Bidirectional translator between the Guided-form {field, operator, value}
 * triple and JSONLogic JSON. Round-trip detection: translateJsonLogicToGuided
 * returns null when an expression cannot be expressed as a simple triple
 * (nested logic, computed operands, unknown ops).
 *
 * The load-bearing test is `roadmap_criterion_4_revenue_50000` —
 * Spec B Phase 3 ROADMAP criterion 4 requires the Guided form to produce
 * `{">": [{"var": "revenue"}, 50000]}` from `field=revenue, op=>, val=50000`.
 */

import { describe, it, expect } from 'vitest';

import {
    translateGuidedToJsonLogic,
    translateJsonLogicToGuided,
    OPERATORS,
    type Operator,
    type GuidedExpression,
} from '@/components/workflows/editor/conditionExpressionTranslator';

// ---------------------------------------------------------------------------
// Guided → JSONLogic
// ---------------------------------------------------------------------------

describe('translateGuidedToJsonLogic — basic binary ops', () => {
    it('roadmap_criterion_4_revenue_50000: translates revenue > 50000', () => {
        const result = translateGuidedToJsonLogic({
            field: 'revenue',
            operator: '>',
            value: 50000,
        });
        expect(result).toEqual({ '>': [{ var: 'revenue' }, 50000] });
    });

    it('translates_eq_string: category == premium', () => {
        const result = translateGuidedToJsonLogic({
            field: 'category',
            operator: '==',
            value: 'premium',
        });
        expect(result).toEqual({ '==': [{ var: 'category' }, 'premium'] });
    });

    it('translates_neq_number: count != 0', () => {
        const result = translateGuidedToJsonLogic({
            field: 'count',
            operator: '!=',
            value: 0,
        });
        expect(result).toEqual({ '!=': [{ var: 'count' }, 0] });
    });

    it('translates_lt: score < 50', () => {
        const result = translateGuidedToJsonLogic({
            field: 'score',
            operator: '<',
            value: 50,
        });
        expect(result).toEqual({ '<': [{ var: 'score' }, 50] });
    });

    it('translates_gte: score >= 80', () => {
        const result = translateGuidedToJsonLogic({
            field: 'score',
            operator: '>=',
            value: 80,
        });
        expect(result).toEqual({ '>=': [{ var: 'score' }, 80] });
    });

    it('translates_lte: score <= 100', () => {
        const result = translateGuidedToJsonLogic({
            field: 'score',
            operator: '<=',
            value: 100,
        });
        expect(result).toEqual({ '<=': [{ var: 'score' }, 100] });
    });

    it('translates_boolean_value: is_active == true', () => {
        const result = translateGuidedToJsonLogic({
            field: 'is_active',
            operator: '==',
            value: true,
        });
        expect(result).toEqual({ '==': [{ var: 'is_active' }, true] });
    });
});

describe('translateGuidedToJsonLogic — contains / in / not in', () => {
    it('translates_contains_string: tags contains "urgent"', () => {
        const result = translateGuidedToJsonLogic({
            field: 'tags',
            operator: 'contains',
            value: 'urgent',
        });
        // JSONLogic "in" with [substring, var-ref] = string-contains semantics
        expect(result).toEqual({ in: ['urgent', { var: 'tags' }] });
    });

    it('translates_in_array_string: tier in [premium, enterprise]', () => {
        const result = translateGuidedToJsonLogic({
            field: 'tier',
            operator: 'in',
            value: 'premium,enterprise',
        });
        expect(result).toEqual({
            in: [{ var: 'tier' }, ['premium', 'enterprise']],
        });
    });

    it('translates_in_array_numeric: score in [10,20,30] (CSV → numbers)', () => {
        const result = translateGuidedToJsonLogic({
            field: 'score',
            operator: 'in',
            value: '10,20,30',
        });
        expect(result).toEqual({
            in: [{ var: 'score' }, [10, 20, 30]],
        });
    });

    it('translates_not_in_array: status not in [cancelled,refunded]', () => {
        const result = translateGuidedToJsonLogic({
            field: 'status',
            operator: 'not in',
            value: 'cancelled,refunded',
        });
        expect(result).toEqual({
            '!': [
                {
                    in: [{ var: 'status' }, ['cancelled', 'refunded']],
                },
            ],
        });
    });

    it('translates_in_array_with_whitespace: score in " 10 , 20 , 30 "', () => {
        const result = translateGuidedToJsonLogic({
            field: 'score',
            operator: 'in',
            value: ' 10 , 20 , 30 ',
        });
        expect(result).toEqual({
            in: [{ var: 'score' }, [10, 20, 30]],
        });
    });
});

// ---------------------------------------------------------------------------
// JSONLogic → Guided
// ---------------------------------------------------------------------------

describe('translateJsonLogicToGuided — basic binary ops', () => {
    it('parses_basic_gt: {">": [{"var": "revenue"}, 50000]}', () => {
        const result = translateJsonLogicToGuided({
            '>': [{ var: 'revenue' }, 50000],
        });
        expect(result).toEqual({
            field: 'revenue',
            operator: '>',
            value: 50000,
        });
    });

    it('parses_eq_string: {"==": [{"var": "category"}, "premium"]}', () => {
        const result = translateJsonLogicToGuided({
            '==': [{ var: 'category' }, 'premium'],
        });
        expect(result).toEqual({
            field: 'category',
            operator: '==',
            value: 'premium',
        });
    });

    it('parses_neq_number: {"!=": [{"var": "count"}, 0]}', () => {
        const result = translateJsonLogicToGuided({
            '!=': [{ var: 'count' }, 0],
        });
        expect(result).toEqual({
            field: 'count',
            operator: '!=',
            value: 0,
        });
    });

    it('parses_boolean_value: {"==": [{"var": "is_active"}, true]}', () => {
        const result = translateJsonLogicToGuided({
            '==': [{ var: 'is_active' }, true],
        });
        expect(result).toEqual({
            field: 'is_active',
            operator: '==',
            value: true,
        });
    });
});

describe('translateJsonLogicToGuided — in / contains / not in', () => {
    it('parses_in_array_back: array membership → in', () => {
        const result = translateJsonLogicToGuided({
            in: [{ var: 'tier' }, ['premium', 'enterprise']],
        });
        expect(result).toEqual({
            field: 'tier',
            operator: 'in',
            value: 'premium,enterprise',
        });
    });

    it('parses_in_array_numeric_back: [10,20] → "10,20"', () => {
        const result = translateJsonLogicToGuided({
            in: [{ var: 'score' }, [10, 20, 30]],
        });
        expect(result).toEqual({
            field: 'score',
            operator: 'in',
            value: '10,20,30',
        });
    });

    it('parses_contains_back: {"in": ["urgent", {"var": "tags"}]} → contains', () => {
        const result = translateJsonLogicToGuided({
            in: ['urgent', { var: 'tags' }],
        });
        expect(result).toEqual({
            field: 'tags',
            operator: 'contains',
            value: 'urgent',
        });
    });

    it('parses_not_in_back: {"!": [{"in": [{"var": "status"}, ["a","b"]]}]} → not in', () => {
        const result = translateJsonLogicToGuided({
            '!': [
                {
                    in: [{ var: 'status' }, ['a', 'b']],
                },
            ],
        });
        expect(result).toEqual({
            field: 'status',
            operator: 'not in',
            value: 'a,b',
        });
    });
});

// ---------------------------------------------------------------------------
// Round-trip failure cases
// ---------------------------------------------------------------------------

describe('translateJsonLogicToGuided — round-trip failures (returns null)', () => {
    it('fails_round_trip_for_and: {"and": [...]} → null', () => {
        const result = translateJsonLogicToGuided({
            and: [
                { '>': [{ var: 'a' }, 1] },
                { '<': [{ var: 'b' }, 10] },
            ],
        });
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_or: {"or": [...]} → null', () => {
        const result = translateJsonLogicToGuided({
            or: [
                { '>': [{ var: 'a' }, 1] },
                { '<': [{ var: 'b' }, 10] },
            ],
        });
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_nested_computed: operand is computed → null', () => {
        const result = translateJsonLogicToGuided({
            '>': [{ '+': [{ var: 'a' }, 1] }, 5],
        });
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_unknown_op: {"unknown_op": [...]} → null', () => {
        const result = translateJsonLogicToGuided({
            unknown_op: [{ var: 'x' }, 5],
        });
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_empty: {} → null', () => {
        const result = translateJsonLogicToGuided({});
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_null: null → null', () => {
        const result = translateJsonLogicToGuided(null);
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_undefined: undefined → null', () => {
        const result = translateJsonLogicToGuided(undefined);
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_array_at_top: [1, 2, 3] → null', () => {
        const result = translateJsonLogicToGuided([1, 2, 3]);
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_double_nested_not_in: {"!": [{"!": [...]}]} → null', () => {
        const result = translateJsonLogicToGuided({
            '!': [
                {
                    '!': [
                        {
                            in: [{ var: 'x' }, ['a']],
                        },
                    ],
                },
            ],
        });
        expect(result).toBeNull();
    });

    it('fails_round_trip_for_wrong_arity_gt: {">": [a]} (one operand) → null', () => {
        const result = translateJsonLogicToGuided({
            '>': [{ var: 'x' }],
        });
        expect(result).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// Idempotency / round-trip
// ---------------------------------------------------------------------------

describe('translator — round-trip idempotency', () => {
    const guidedShapes: GuidedExpression[] = [
        { field: 'revenue', operator: '>', value: 50000 },
        { field: 'category', operator: '==', value: 'premium' },
        { field: 'count', operator: '!=', value: 0 },
        { field: 'score', operator: '<', value: 50 },
        { field: 'score', operator: '<=', value: 100 },
        { field: 'score', operator: '>=', value: 80 },
        { field: 'tags', operator: 'contains', value: 'urgent' },
        { field: 'tier', operator: 'in', value: 'premium,enterprise' },
        { field: 'status', operator: 'not in', value: 'cancelled,refunded' },
    ];

    guidedShapes.forEach((shape) => {
        it(`roundtrip ${shape.field} ${shape.operator} ${String(shape.value)}`, () => {
            const json = translateGuidedToJsonLogic(shape);
            const back = translateJsonLogicToGuided(json);
            expect(back).toEqual(shape);
        });
    });

    it('OPERATORS constant exposes 9 entries in expected order', () => {
        expect(OPERATORS).toEqual([
            '==',
            '!=',
            '<',
            '<=',
            '>',
            '>=',
            'contains',
            'in',
            'not in',
        ]);
        expect(OPERATORS.length).toBe(9);
    });

    it('every OPERATORS entry round-trips through both translators', () => {
        for (const op of OPERATORS) {
            const value: string | number =
                op === 'in' || op === 'not in' ? 'a,b' : op === 'contains' ? 'foo' : 1;
            const shape: GuidedExpression = {
                field: 'f',
                operator: op as Operator,
                value,
            };
            const json = translateGuidedToJsonLogic(shape);
            const back = translateJsonLogicToGuided(json);
            expect(back).toEqual(shape);
        }
    });
});
