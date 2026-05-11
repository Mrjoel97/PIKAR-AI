// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for useGraphValidation — Phase 110 client-side validator
 * mirroring app/workflows/graph_validation.py (B-4 contract).
 *
 * Both the server's pytest suite (tests/unit/workflows/test_graph_validation.py)
 * and this vitest suite parametrize over the SAME canonical fixture at
 * tests/fixtures/graph_validation_cases.json. Any divergence between
 * client and server behavior fails one of the two suites.
 */

import { describe, it, expect } from 'vitest';

// Shared canonical fixture (4 levels up from frontend/src/__tests__/workflows/).
// Plan 03 created this file; Plan 04 reads it.
import cases from '../../../../tests/fixtures/graph_validation_cases.json';

import {
    validateGraph,
} from '@/components/workflows/editor/useGraphValidation';
import { validateNodeConfig } from '@/components/workflows/editor/useGraphSchema';
import type {
    GraphNode,
    GraphEdge,
    NodeKind,
} from '@/services/workflows';

interface ExpectedError {
    node_id: string | null;
    rule: number;
    message_contains?: string;
}

interface FixtureCase {
    name: string;
    description: string;
    input: {
        graph_nodes: GraphNode[];
        graph_edges: GraphEdge[];
    };
    expected_errors: ExpectedError[];
}

const FIXTURE_CASES = cases as unknown as FixtureCase[];

describe('useGraphValidation — shared fixture parity (B-4)', () => {
    FIXTURE_CASES.forEach((tc) => {
        it(`case: ${tc.name} (${tc.description})`, () => {
            const actual = validateGraph(
                tc.input.graph_nodes,
                tc.input.graph_edges,
            );
            // Count parity first — fixture is the canonical contract.
            expect(actual.length).toBe(tc.expected_errors.length);
            tc.expected_errors.forEach((expected, i) => {
                expect(actual[i].node_id).toBe(expected.node_id);
                expect(actual[i].rule).toBe(expected.rule);
                if (expected.message_contains) {
                    expect(actual[i].message.toLowerCase()).toContain(
                        expected.message_contains.toLowerCase(),
                    );
                }
            });
        });
    });
});

describe('useGraphValidation — additional edge cases (non-fixture)', () => {
    it('returns rule-1 error for completely empty graph', () => {
        const result = validateGraph([], []);
        expect(result.length).toBeGreaterThanOrEqual(1);
        const rule1 = result.find((e) => e.rule === 1);
        expect(rule1).toBeDefined();
        expect(rule1?.node_id).toBeNull();
    });

    it('detects 3-node cycle (a -> b -> c -> a) and flags all three', () => {
        const nodes: GraphNode[] = [
            { id: 't', kind: 'trigger', label: 'T', config: {} },
            {
                id: 'a',
                kind: 'agent-action',
                label: 'A',
                config: { tool_name: 'noop' },
            },
            {
                id: 'b',
                kind: 'agent-action',
                label: 'B',
                config: { tool_name: 'noop' },
            },
            {
                id: 'c',
                kind: 'agent-action',
                label: 'C',
                config: { tool_name: 'noop' },
            },
            { id: 'o', kind: 'output', label: 'O', config: {} },
        ];
        const edges: GraphEdge[] = [
            { id: 'e1', source: 't', target: 'a' },
            { id: 'e2', source: 'a', target: 'b' },
            { id: 'e3', source: 'b', target: 'c' },
            { id: 'e4', source: 'c', target: 'a' },
            { id: 'e5', source: 'c', target: 'o' },
        ];
        const result = validateGraph(nodes, edges);
        const cycleErrors = result.filter((e) => e.rule === 3);
        expect(cycleErrors.length).toBe(3);
        const cycleNodeIds = cycleErrors.map((e) => e.node_id).sort();
        expect(cycleNodeIds).toEqual(['a', 'b', 'c']);
    });

    it('agent-action with extra unknown keys passes rule 7 (passthrough)', () => {
        const nodes: GraphNode[] = [
            { id: 't', kind: 'trigger', label: 'T', config: {} },
            {
                id: 'a',
                kind: 'agent-action',
                label: 'A',
                config: {
                    tool_name: 'noop',
                    extra_random_key: 'allowed',
                    nested: { foo: 1 },
                },
            },
            { id: 'o', kind: 'output', label: 'O', config: {} },
        ];
        const edges: GraphEdge[] = [
            { id: 'e1', source: 't', target: 'a' },
            { id: 'e2', source: 'a', target: 'o' },
        ];
        const result = validateGraph(nodes, edges);
        const rule7 = result.filter((e) => e.rule === 7);
        expect(rule7).toEqual([]);
    });

    it('condition node with empty config passes rule 7 (Phase 110 permissive)', () => {
        const nodes: GraphNode[] = [
            { id: 't', kind: 'trigger', label: 'T', config: {} },
            { id: 'c', kind: 'condition', label: 'C', config: {} },
            { id: 'o', kind: 'output', label: 'O', config: {} },
        ];
        const edges: GraphEdge[] = [
            { id: 'e1', source: 't', target: 'c' },
            { id: 'e2', source: 'c', target: 'o' },
        ];
        const result = validateGraph(nodes, edges);
        const rule7 = result.filter((e) => e.rule === 7);
        expect(rule7).toEqual([]);
    });

    it('parallel/merge/human-approval with empty config all pass rule 7', () => {
        const kinds: NodeKind[] = ['parallel', 'merge', 'human-approval'];
        kinds.forEach((kind) => {
            const result = validateNodeConfig(kind, {});
            expect(result.success).toBe(true);
        });
    });

    it('returns ValidationError shape {node_id, rule, message}', () => {
        const result = validateGraph(
            [
                { id: 't', kind: 'trigger', label: 'T', config: {} },
                {
                    id: 'a',
                    kind: 'agent-action',
                    label: 'A',
                    // Missing tool_name → rule 7
                    config: {},
                },
                { id: 'o', kind: 'output', label: 'O', config: {} },
            ],
            [
                { id: 'e1', source: 't', target: 'a' },
                { id: 'e2', source: 'a', target: 'o' },
            ],
        );
        const rule7 = result.find((e) => e.rule === 7);
        expect(rule7).toBeDefined();
        expect(rule7?.node_id).toBe('a');
        expect(typeof rule7?.message).toBe('string');
        expect(rule7?.message.length).toBeGreaterThan(0);
    });
});

describe('useGraphSchema.validateNodeConfig — per-kind', () => {
    it('trigger accepts empty config', () => {
        expect(validateNodeConfig('trigger', {}).success).toBe(true);
    });

    it('trigger accepts trigger_type=manual|schedule|event', () => {
        for (const t of ['manual', 'schedule', 'event']) {
            expect(
                validateNodeConfig('trigger', { trigger_type: t }).success,
            ).toBe(true);
        }
    });

    it('agent-action rejects missing tool_name', () => {
        const r = validateNodeConfig('agent-action', {});
        expect(r.success).toBe(false);
    });

    it('agent-action accepts tool_name + extras (passthrough)', () => {
        const r = validateNodeConfig('agent-action', {
            tool_name: 'send_email',
            agent_role: 'marketing',
            arguments: { to: 'a@b.com' },
        });
        expect(r.success).toBe(true);
    });

    it('output accepts empty config', () => {
        expect(validateNodeConfig('output', {}).success).toBe(true);
    });
});
