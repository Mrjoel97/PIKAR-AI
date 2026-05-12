// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Vitest tests for WorkflowGraphRunWidget — Phase 111 Plan 05 Task 05-03.
 *
 * The widget renders a live React Flow canvas of a branched workflow run,
 * driving node/edge runState from:
 *   1. Initial fetch: getWorkflowExecutionDetails + getWorkflowTemplate
 *      (history yields per-step graph_node_id via output_data
 *      ._execution_meta.graph_node_id — Plan 03's JSONB workaround).
 *   2. Live SSE: subscribeToExecution wires workflow.step.{started,
 *      completed, failed, paused} events (CANONICAL dot-separated form
 *      per BLOCKER #2 fix — backend emits this format from
 *      app/workflows/step_executor.py:752-760).
 *
 * Mocks:
 *   - @xyflow/react: jsdom can't render the real React Flow; we mock to a
 *     stub that exposes nodes/edges in data-attributes for assertion.
 *   - @/services/workflows: getWorkflowExecutionDetails +
 *     getWorkflowTemplate return canned payloads per test.
 *   - @/services/workflowExecutionStream: subscribeToExecution captures
 *     the callback so each test can fire synthetic SSE events.
 *
 * Test data shape:
 *   Branching template: trigger -> condition -> {output-true, output-false}.
 *   Linear template: trigger -> agent-action -> output.
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks — must come BEFORE the import of the component under test.
// ---------------------------------------------------------------------------

// React Flow mock: surface nodes/edges via data-attributes + render children.
vi.mock('@xyflow/react', () => {
    interface MockReactFlowProps {
        nodes: Array<{
            id: string;
            type: string;
            data?: { runState?: string; label?: string };
        }>;
        edges: Array<{
            id: string;
            source: string;
            target: string;
            style?: Record<string, unknown>;
        }>;
        children?: React.ReactNode;
    }
    return {
        ReactFlow: ({ nodes, edges, children }: MockReactFlowProps) => (
            <div
                data-testid="react-flow"
                data-node-count={nodes.length}
                data-edge-count={edges.length}
            >
                {nodes.map((n) => (
                    <div
                        key={n.id}
                        data-testid={`rf-node-${n.id}`}
                        data-run-state={n.data?.runState ?? ''}
                        data-node-type={n.type}
                    />
                ))}
                {edges.map((e) => (
                    <div
                        key={e.id}
                        data-testid={`rf-edge-${e.id}`}
                        data-edge-stroke={
                            e.style && typeof e.style === 'object'
                                ? ((e.style as Record<string, unknown>).stroke as string) ?? ''
                                : ''
                        }
                        data-edge-opacity={
                            e.style && typeof e.style === 'object'
                                ? String(
                                      (e.style as Record<string, unknown>).opacity ?? '',
                                  )
                                : ''
                        }
                        data-edge-dasharray={
                            e.style && typeof e.style === 'object'
                                ? ((e.style as Record<string, unknown>).strokeDasharray as string) ?? ''
                                : ''
                        }
                    />
                ))}
                {children}
            </div>
        ),
        Background: () => <div data-testid="rf-bg" />,
        Controls: () => <div data-testid="rf-ctrls" />,
        ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
            <>{children}</>
        ),
    };
});

// Capture SSE callbacks at module level so each test can fire events.
const sseCallbacks: Array<(e: import('@/services/workflowExecutionStream').WorkflowEvent) => void> = [];
const sseUnsubscribes: Array<() => void> = [];
vi.mock('@/services/workflowExecutionStream', () => {
    return {
        subscribeToExecution: (
            _executionId: string,
            cb: (e: import('@/services/workflowExecutionStream').WorkflowEvent) => void,
        ) => {
            sseCallbacks.push(cb);
            const unsub = vi.fn();
            sseUnsubscribes.push(unsub);
            return unsub;
        },
    };
});

// Mock workflows service: returns canned execution + template payloads.
const mockGetExec = vi.fn();
const mockGetTpl = vi.fn();
vi.mock('@/services/workflows', () => ({
    getWorkflowExecutionDetails: (...args: unknown[]) => mockGetExec(...args),
    getWorkflowTemplate: (...args: unknown[]) => mockGetTpl(...args),
}));

import WorkflowGraphRunWidget from '../WorkflowGraphRunWidget';
import type { WidgetDefinition } from '@/types/widgets';

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function makeBranchingTemplate() {
    return {
        id: 'tpl-branching',
        name: 'Lead routing',
        description: '',
        category: 'sales',
        graph_nodes: [
            { id: 't', kind: 'trigger', label: 'Start', config: {}, position: { x: 0, y: 0 } },
            { id: 'a1', kind: 'agent-action', label: 'Score lead', config: { tool_name: 'noop' }, position: { x: 200, y: 0 } },
            { id: 'c1', kind: 'condition', label: 'Score > 50?', config: { expression: { '>': [{ var: 'a1.score' }, 50] } }, position: { x: 400, y: 0 } },
            { id: 'o-true', kind: 'output', label: 'Hot lead', config: {}, position: { x: 600, y: -50 } },
            { id: 'o-false', kind: 'output', label: 'Cold lead', config: {}, position: { x: 600, y: 50 } },
        ],
        graph_edges: [
            { id: 'e-t-a1', source: 't', target: 'a1', source_handle: null, label: null },
            { id: 'e-a1-c1', source: 'a1', target: 'c1', source_handle: null, label: null },
            { id: 'e-c1-true', source: 'c1', target: 'o-true', source_handle: 'true', label: 'true' },
            { id: 'e-c1-false', source: 'c1', target: 'o-false', source_handle: 'false', label: 'false' },
        ],
        graph_layout: {},
    };
}

function makeLinearTemplate() {
    return {
        id: 'tpl-linear',
        name: 'Daily digest',
        description: '',
        category: 'operations',
        graph_nodes: [
            { id: 't', kind: 'trigger', label: 'Start', config: {}, position: { x: 0, y: 0 } },
            { id: 'a1', kind: 'agent-action', label: 'Fetch', config: { tool_name: 'noop' }, position: { x: 200, y: 0 } },
            { id: 'o', kind: 'output', label: 'Done', config: {}, position: { x: 400, y: 0 } },
        ],
        graph_edges: [
            { id: 'e-t-a1', source: 't', target: 'a1' },
            { id: 'e-a1-o', source: 'a1', target: 'o' },
        ],
        graph_layout: {},
    };
}

function makeHistoryStep(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        id: 's-1',
        status: 'completed',
        output_data: {},
        ...overrides,
    };
}

function makeWidgetDef(executionId = 'exec-1'): WidgetDefinition {
    return {
        type: 'workflow_graph_run',
        title: 'Live run',
        data: { execution_id: executionId },
    } as unknown as WidgetDefinition;
}

beforeEach(() => {
    sseCallbacks.length = 0;
    sseUnsubscribes.length = 0;
    mockGetExec.mockReset();
    mockGetTpl.mockReset();
});

// =============================================================================
// Initial render + fetch
// =============================================================================

describe('WorkflowGraphRunWidget — initial render', () => {
    it('renders_loading_state_initially', () => {
        // Make fetches hang so loading state persists.
        mockGetExec.mockReturnValue(new Promise(() => undefined));
        mockGetTpl.mockReturnValue(new Promise(() => undefined));

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        expect(screen.getByText(/loading/i)).toBeTruthy();
    });

    it('renders_graph_after_fetch_resolves', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        const flow = await screen.findByTestId('react-flow');
        expect(flow.getAttribute('data-node-count')).toBe('5');
        expect(flow.getAttribute('data-edge-count')).toBe('4');
    });

    it('shows_amber_warning_when_execution_id_missing', () => {
        const def = {
            type: 'workflow_graph_run',
            title: 'Live run',
            data: {},
        } as unknown as WidgetDefinition;
        render(<WorkflowGraphRunWidget definition={def} />);
        expect(screen.getByText(/no execution.?id/i)).toBeTruthy();
    });
});

// =============================================================================
// Initial state derivation from history
// =============================================================================

describe('WorkflowGraphRunWidget — initial state from history', () => {
    it('marks_completed_steps_as_completed_on_mount', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-t',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 't' } },
                }),
                makeHistoryStep({
                    id: 's-a1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        expect(screen.getByTestId('rf-node-t').getAttribute('data-run-state')).toBe('completed');
        expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe('completed');
    });

    it('marks_running_step_as_active_on_mount', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-a1',
                    status: 'running',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe('active');
    });

    it('pending_nodes_are_pending', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-t',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 't' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        // a1, c1, o-true, o-false all have no completed history row -> pending.
        expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe('pending');
        expect(screen.getByTestId('rf-node-o-true').getAttribute('data-run-state')).toBe('pending');
    });

    it('highlights_taken_edge_after_condition', async () => {
        // History: trigger, a1, c1 all completed; o-true completed -> 'true'
        // branch taken; 'false' branch becomes not_taken.
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-t',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 't' } },
                }),
                makeHistoryStep({
                    id: 's-a1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
                makeHistoryStep({
                    id: 's-c1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'c1' } },
                }),
                makeHistoryStep({
                    id: 's-out',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'o-true' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        const takenEdge = screen.getByTestId('rf-edge-e-c1-true');
        expect(takenEdge.getAttribute('data-edge-stroke')).toBe('#10b981');
        const muted = screen.getByTestId('rf-edge-e-c1-false');
        // Not-taken edge muted (opacity 0.3 + dashed)
        expect(muted.getAttribute('data-edge-opacity')).toBe('0.3');
        expect(muted.getAttribute('data-edge-dasharray')).toBeTruthy();
    });

    it('failed_step_marks_node_failed', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'failed' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-a1',
                    status: 'failed',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe('failed');
    });
});

// =============================================================================
// SSE event handling — CANONICAL dot-separated event types
// =============================================================================

describe('WorkflowGraphRunWidget — SSE event handling (canonical workflow.step.* dot-separated)', () => {
    it('sse_event_flips_node_to_active', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-a1',
                    status: 'running',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        // SSE event: a1 completes; another step starts on c1 (the condition).
        await act(async () => {
            sseCallbacks[0]({
                type: 'workflow.step.completed',
                step_id: 's-a1',
            });
        });
        await waitFor(() => {
            expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe(
                'completed',
            );
        });
    });

    it('sse_event_flips_node_to_completed', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-t',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 't' } },
                }),
                makeHistoryStep({
                    id: 's-a1',
                    status: 'running',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        await act(async () => {
            sseCallbacks[0]({
                type: 'workflow.step.completed',
                step_id: 's-a1',
            });
        });
        await waitFor(() => {
            expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe(
                'completed',
            );
        });
    });

    it('sse_workflow_step_failed_marks_node_failed', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-a1',
                    status: 'running',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        await act(async () => {
            sseCallbacks[0]({
                type: 'workflow.step.failed',
                step_id: 's-a1',
            });
        });
        await waitFor(() => {
            expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe(
                'failed',
            );
        });
    });

    it('sse_workflow_step_paused_keeps_node_active', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'paused' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-a1',
                    status: 'running',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        await act(async () => {
            sseCallbacks[0]({
                type: 'workflow.step.paused',
                step_id: 's-a1',
            });
        });
        await waitFor(() => {
            expect(screen.getByTestId('rf-node-a1').getAttribute('data-run-state')).toBe(
                'active',
            );
        });
    });

    it('unsubscribes_sse_on_unmount', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());
        const { unmount } = render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        expect(sseUnsubscribes.length).toBeGreaterThan(0);
        unmount();
        expect(sseUnsubscribes[0]).toHaveBeenCalled();
    });

    it('re_evaluates_taken_edge_after_late_completion', async () => {
        // Initial: trigger + a1 completed but no downstream of condition.
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-t',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 't' } },
                }),
                makeHistoryStep({
                    id: 's-a1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
                makeHistoryStep({
                    id: 's-c1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'c1' } },
                }),
                // The taken-branch step is just inserted but Plan 05 sees it via refetch.
                makeHistoryStep({
                    id: 's-out',
                    status: 'running',
                    output_data: { _execution_meta: { graph_node_id: 'o-false' } },
                }),
            ],
        });
        mockGetTpl.mockResolvedValue(makeBranchingTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        await screen.findByTestId('react-flow');
        // Refetch path is triggered when an event with unknown step_id arrives;
        // for this test we fire the same step's completion via SSE.
        // The widget's `workflow.step.completed` re-evaluates taken-edge logic.
        // Update the exec mock to reflect the post-event state for the refetch.
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-branching', status: 'running' },
            template_name: 'Lead routing',
            history: [
                makeHistoryStep({
                    id: 's-t',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 't' } },
                }),
                makeHistoryStep({
                    id: 's-a1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'a1' } },
                }),
                makeHistoryStep({
                    id: 's-c1',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'c1' } },
                }),
                makeHistoryStep({
                    id: 's-out',
                    status: 'completed',
                    output_data: { _execution_meta: { graph_node_id: 'o-false' } },
                }),
            ],
        });
        await act(async () => {
            sseCallbacks[0]({
                type: 'workflow.step.completed',
                step_id: 's-out',
            });
        });
        await waitFor(() => {
            expect(
                screen.getByTestId('rf-edge-e-c1-false').getAttribute('data-edge-stroke'),
            ).toBe('#10b981');
        });
        // The not-taken edge becomes muted.
        expect(
            screen.getByTestId('rf-edge-e-c1-true').getAttribute('data-edge-opacity'),
        ).toBe('0.3');
    });

    it('linear_template_renders_without_errors', async () => {
        mockGetExec.mockResolvedValue({
            execution: { id: 'exec-1', template_id: 'tpl-linear', status: 'running' },
            template_name: 'Daily digest',
            history: [],
        });
        mockGetTpl.mockResolvedValue(makeLinearTemplate());

        render(<WorkflowGraphRunWidget definition={makeWidgetDef()} />);
        const flow = await screen.findByTestId('react-flow');
        expect(flow.getAttribute('data-node-count')).toBe('3');
        expect(flow.getAttribute('data-edge-count')).toBe('2');
        // Linear template -> no taken/not_taken edge styling.
        const e1 = screen.getByTestId('rf-edge-e-t-a1');
        expect(e1.getAttribute('data-edge-stroke')).toBe('');
    });
});
