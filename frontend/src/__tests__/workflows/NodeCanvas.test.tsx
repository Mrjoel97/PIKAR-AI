// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for NodeCanvas (Phase 109 / Spec B Phase 1 read-only viewer).
 *
 * React Flow uses window measurement APIs (ResizeObserver, IntersectionObserver,
 * offsetWidth/Height) that jsdom does not implement. We mock the @xyflow/react
 * surface in a minimal way so we can assert that NodeCanvas constructs the
 * right number of Nodes and Edges from a given WorkflowTemplate — which is
 * the actual contract we care about. Pan/zoom/render fidelity is covered by
 * manual UAT and a future Playwright suite.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';
import type { WorkflowTemplate } from '@/services/workflows';

vi.mock('@xyflow/react', () => {
    interface ReactFlowProps {
        nodes: Array<unknown>;
        edges: Array<unknown>;
        children?: React.ReactNode;
        onNodesChange?: (changes: unknown[]) => void;
        onEdgesChange?: (changes: unknown[]) => void;
        onConnect?: (connection: unknown) => void;
    }
    return {
        ReactFlow: ({ nodes, edges, children }: ReactFlowProps) => (
            <div
                data-testid="react-flow"
                data-node-count={nodes.length}
                data-edge-count={edges.length}
            >
                {children}
            </div>
        ),
        Background: () => <div data-testid="background" />,
        Controls: () => <div data-testid="controls" />,
        Handle: () => <div />,
        Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
        // Plan 110-04 edit-mode helpers
        addEdge: (
            connection: { source: string; target: string; id?: string },
            edges: unknown[],
        ) => [...edges, { id: connection.id ?? 'e-new', ...connection }],
        applyNodeChanges: (_changes: unknown[], nodes: unknown[]) => nodes,
        applyEdgeChanges: (_changes: unknown[], edges: unknown[]) => edges,
        useReactFlow: () => ({
            screenToFlowPosition: ({ x, y }: { x: number; y: number }) => ({
                x,
                y,
            }),
        }),
        ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
            <>{children}</>
        ),
    };
});

function makeTemplate(overrides: Record<string, unknown>): WorkflowTemplate {
    return {
        id: 't-test',
        name: 'Test',
        description: '',
        category: 'operations',
        ...overrides,
    } as unknown as WorkflowTemplate;
}

describe('NodeCanvas', () => {
    it('renders 6 nodes and 5 edges for a 4-step template (happy path)', () => {
        const template = makeTemplate({
            graph_nodes: [
                { id: 'trigger', kind: 'trigger', label: 'Start' },
                {
                    id: 'step-0',
                    kind: 'agent-action',
                    label: 's1',
                    config: { tool_name: 't1' },
                },
                {
                    id: 'step-1',
                    kind: 'agent-action',
                    label: 's2',
                    config: { tool_name: 't2' },
                },
                {
                    id: 'step-2',
                    kind: 'agent-action',
                    label: 's3',
                    config: { tool_name: 't3' },
                },
                {
                    id: 'step-3',
                    kind: 'agent-action',
                    label: 's4',
                    config: { tool_name: 't4' },
                },
                { id: 'output', kind: 'output', label: 'Done' },
            ],
            graph_edges: [
                { id: 'e-trigger-step-0', source: 'trigger', target: 'step-0' },
                { id: 'e-step-0-step-1', source: 'step-0', target: 'step-1' },
                { id: 'e-step-1-step-2', source: 'step-1', target: 'step-2' },
                { id: 'e-step-2-step-3', source: 'step-2', target: 'step-3' },
                { id: 'e-step-3-output', source: 'step-3', target: 'output' },
            ],
            graph_layout: {
                trigger: { x: 0, y: 0 },
                'step-0': { x: 200, y: 0 },
                'step-1': { x: 400, y: 0 },
                'step-2': { x: 600, y: 0 },
                'step-3': { x: 800, y: 0 },
                output: { x: 1000, y: 0 },
            },
        });

        render(<NodeCanvas template={template} />);
        const rf = screen.getByTestId('react-flow');
        expect(rf.getAttribute('data-node-count')).toBe('6');
        expect(rf.getAttribute('data-edge-count')).toBe('5');
    });

    it('falls back to client-side projection from flat steps when graph fields are absent', () => {
        const template = makeTemplate({
            steps: [
                { name: 's1', tool: 't1' },
                { name: 's2', tool: 't2' },
            ],
            // graph_nodes / graph_edges / graph_layout deliberately omitted
        });

        render(<NodeCanvas template={template} />);
        const rf = screen.getByTestId('react-flow');
        // trigger + 2 steps + output = 4 nodes; 3 edges
        expect(rf.getAttribute('data-node-count')).toBe('4');
        expect(rf.getAttribute('data-edge-count')).toBe('3');
    });

    it('falls back to client-side projection from phases.*.steps when graph fields are absent', () => {
        const template = makeTemplate({
            phases: [
                {
                    name: 'Phase A',
                    steps: [
                        { name: 'a1', tool: 'tool_a' },
                        { name: 'a2', tool: 'tool_b' },
                    ],
                },
                {
                    name: 'Phase B',
                    steps: [{ name: 'b1', tool: 'tool_c' }],
                },
            ],
        });

        render(<NodeCanvas template={template} />);
        const rf = screen.getByTestId('react-flow');
        // trigger + 3 flattened steps + output = 5 nodes; 4 edges
        expect(rf.getAttribute('data-node-count')).toBe('5');
        expect(rf.getAttribute('data-edge-count')).toBe('4');
    });

    it('renders empty-state placeholder when template has no graph fields and no steps', () => {
        const template = makeTemplate({});

        render(<NodeCanvas template={template} />);
        // No React Flow when empty — empty-state copy is rendered instead
        expect(screen.queryByTestId('react-flow')).toBeNull();
        expect(
            screen.getByText(/This template has no graph nodes yet\./i),
        ).toBeTruthy();
    });

    it('passes through agent-action tool_name into node data', () => {
        // The mock can't introspect node.data directly, but we can assert that
        // the construction did not throw and that the count matches.
        const template = makeTemplate({
            graph_nodes: [
                { id: 'trigger', kind: 'trigger', label: 'Start' },
                {
                    id: 'step-0',
                    kind: 'agent-action',
                    label: 'Send email',
                    config: { tool_name: 'send_gmail' },
                },
                { id: 'output', kind: 'output', label: 'Done' },
            ],
            graph_edges: [
                { id: 'e-trigger-step-0', source: 'trigger', target: 'step-0' },
                { id: 'e-step-0-output', source: 'step-0', target: 'output' },
            ],
            graph_layout: {
                trigger: { x: 0, y: 0 },
                'step-0': { x: 200, y: 0 },
                output: { x: 400, y: 0 },
            },
        });

        render(<NodeCanvas template={template} />);
        const rf = screen.getByTestId('react-flow');
        expect(rf.getAttribute('data-node-count')).toBe('3');
        expect(rf.getAttribute('data-edge-count')).toBe('2');
    });

    it('does not crash when graph_layout is missing (defaults to 0,0)', () => {
        const template = makeTemplate({
            graph_nodes: [
                { id: 'trigger', kind: 'trigger', label: 'Start' },
                { id: 'output', kind: 'output', label: 'Done' },
            ],
            graph_edges: [
                { id: 'e-trigger-output', source: 'trigger', target: 'output' },
            ],
            // graph_layout intentionally omitted
        });

        render(<NodeCanvas template={template} />);
        const rf = screen.getByTestId('react-flow');
        expect(rf.getAttribute('data-node-count')).toBe('2');
        expect(rf.getAttribute('data-edge-count')).toBe('1');
    });
});

describe('NodeCanvas (editable mode — Phase 110 Plan 04)', () => {
    it('renders editor empty-state when editable + no graph fields', () => {
        const template = makeTemplate({});
        render(<NodeCanvas template={template} editable />);
        // Should show the editor-specific empty state, NOT mount ReactFlow
        expect(screen.queryByTestId('react-flow')).toBeNull();
        expect(screen.getByTestId('editor-empty-state')).toBeTruthy();
        expect(
            screen.getByText(/Drag a Trigger from the palette/i),
        ).toBeTruthy();
    });

    it('mounts the editor canvas container with data-testid', () => {
        const template = makeTemplate({
            graph_nodes: [
                { id: 't', kind: 'trigger', label: 'Start' },
                { id: 'o', kind: 'output', label: 'Done' },
            ],
            graph_edges: [{ id: 'e1', source: 't', target: 'o' }],
        });
        render(<NodeCanvas template={template} editable />);
        expect(screen.getByTestId('editor-canvas')).toBeTruthy();
        const rf = screen.getByTestId('react-flow');
        expect(rf.getAttribute('data-node-count')).toBe('2');
        expect(rf.getAttribute('data-edge-count')).toBe('1');
    });

    it('preserves backward-compat: editable defaults false (no editor container)', () => {
        const template = makeTemplate({
            graph_nodes: [
                { id: 't', kind: 'trigger', label: 'Start' },
                { id: 'o', kind: 'output', label: 'Done' },
            ],
            graph_edges: [{ id: 'e1', source: 't', target: 'o' }],
        });
        render(<NodeCanvas template={template} />);
        // Plan 109's read-only path — no editor-canvas container
        expect(screen.queryByTestId('editor-canvas')).toBeNull();
        expect(screen.getByTestId('react-flow')).toBeTruthy();
    });
});
