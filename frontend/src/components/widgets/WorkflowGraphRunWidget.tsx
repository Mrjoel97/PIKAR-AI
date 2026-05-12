'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Phase 111 Plan 05 — WorkflowGraphRunWidget.
 *
 * Live React Flow renderer for branched workflow runs. Subscribes to
 * Spec A's existing SSE event stream and overlays node/edge runState on a
 * graph derived from the execution's template_version pinned snapshot.
 *
 * Discretion decisions (CONTEXT.md):
 *   - #6 Widget placement: workspace-rendered (under widgets/). Imports
 *     `NODE_TYPES` from the editor's shared `nodeTypes.ts` module to reuse
 *     the 7 Phase 109/110 visual node components.
 *   - #7 Active-node visual: Tailwind `animate-pulse ring-2 ring-amber-500`
 *     via the `runStateStyles.getNodeRunStateClasses` helper.
 *
 * Live state machine:
 *   - On mount: fetch execution + template -> derive initial runState from
 *     history rows keyed by output_data._execution_meta.graph_node_id
 *     (Plan 03's JSONB workaround).
 *   - SSE events update state on the fly. CANONICAL event types
 *     (BLOCKER #2 fix from plan-checker iteration 1):
 *       'workflow.step.started'    -> node 'active'
 *       'workflow.step.completed'  -> node 'completed' + re-eval taken edge
 *       'workflow.step.failed'     -> node 'failed'
 *       'workflow.step.paused'     -> node 'active' (paused visual TBD)
 *     Backend emits these from app/workflows/step_executor.py:752-760
 *     (verified 2026-05-12).
 *
 * The widget is purely additive — no backend / SSE-wire / OutcomeWriter /
 * WorkflowTimelineWidget changes (ROADMAP criterion 10).
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    ReactFlowProvider,
    type Edge,
    type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { WidgetProps } from './WidgetRegistry';
import {
    getWorkflowExecutionDetails,
    getWorkflowTemplate,
} from '@/services/workflows';
import {
    subscribeToExecution,
    type WorkflowEvent,
} from '@/services/workflowExecutionStream';
import { NODE_TYPES } from '@/components/workflows/editor/nodeTypes';
import {
    type NodeRunState,
    type EdgeRunState,
    getEdgeRunStateStyle,
} from '@/components/workflows/editor/runStateStyles';

// ---------------------------------------------------------------------------
// Internal payload shapes — narrowed from the loose service-layer types so
// the live state machine only depends on the fields it reads.
// ---------------------------------------------------------------------------

interface GraphNodeShape {
    id: string;
    kind: string;
    label?: string;
    config?: Record<string, unknown> | null;
    position?: { x: number; y: number };
}

interface GraphEdgeShape {
    id: string;
    source: string;
    target: string;
    source_handle?: string | null;
    label?: string | null;
}

interface HistoryRow {
    id: string;
    status?: string;
    output_data?: {
        _execution_meta?: { graph_node_id?: string };
    } | null;
}

interface TemplatePayload {
    graph_nodes?: GraphNodeShape[] | null;
    graph_edges?: GraphEdgeShape[] | null;
    graph_layout?: Record<string, { x: number; y: number }> | null;
}

interface ExecutionDetailsPayload {
    execution?: { id?: string; template_id?: string; status?: string };
    history?: HistoryRow[];
}

interface DerivedState {
    nodeState: Record<string, NodeRunState>;
    edgeState: Record<string, EdgeRunState>;
    stepIdToNodeId: Record<string, string>;
}

/**
 * Builds the initial RunStateMap from a fetched execution + template.
 *
 * Initial state rules:
 *  - All nodes start 'pending'.
 *  - All edges start 'pending'.
 *  - history rows map step.id -> graph_node_id; the corresponding node's
 *    state is set from step.status:
 *      'completed' -> 'completed'  (also recorded in `completedNodeIds`)
 *      'running' / 'pending' -> 'active'
 *      'failed' -> 'failed'
 *      'skipped' -> 'skipped'
 *  - Condition-node outgoing edges: if any outgoing edge points at a
 *    completed downstream, that edge becomes 'taken' and the other
 *    outgoing edges from the same condition become 'not_taken'.
 */
function deriveRunState(
    execution: ExecutionDetailsPayload,
    template: TemplatePayload,
): DerivedState {
    const nodeState: Record<string, NodeRunState> = {};
    const edgeState: Record<string, EdgeRunState> = {};
    const stepIdToNodeId: Record<string, string> = {};

    const nodes: GraphNodeShape[] = template.graph_nodes ?? [];
    const edges: GraphEdgeShape[] = template.graph_edges ?? [];

    for (const n of nodes) {
        nodeState[n.id] = 'pending';
    }
    for (const e of edges) {
        edgeState[e.id] = 'pending';
    }

    const completedNodeIds = new Set<string>();
    for (const step of execution.history ?? []) {
        const nodeId = step.output_data?._execution_meta?.graph_node_id;
        if (!nodeId) continue;
        stepIdToNodeId[step.id] = nodeId;
        switch (step.status) {
            case 'completed':
                nodeState[nodeId] = 'completed';
                completedNodeIds.add(nodeId);
                break;
            case 'running':
            case 'pending':
                nodeState[nodeId] = 'active';
                break;
            case 'failed':
                nodeState[nodeId] = 'failed';
                break;
            case 'skipped':
                nodeState[nodeId] = 'skipped';
                break;
            default:
                // Unknown status — leave as pending.
                break;
        }
    }

    // Re-evaluate condition node outgoing edges. For each condition with
    // any completed downstream, mark the matching edges taken / not_taken.
    for (const node of nodes) {
        if (node.kind !== 'condition') continue;
        const outEdges = edges.filter((e) => e.source === node.id);
        const anyTaken = outEdges.some((e) => completedNodeIds.has(e.target));
        if (!anyTaken) continue;
        for (const e of outEdges) {
            edgeState[e.id] = completedNodeIds.has(e.target) ? 'taken' : 'not_taken';
        }
    }

    return { nodeState, edgeState, stepIdToNodeId };
}

// ---------------------------------------------------------------------------
// Canvas — wrapped in ReactFlowProvider by the default export.
// ---------------------------------------------------------------------------

interface GraphRunCanvasProps {
    executionId: string;
}

function GraphRunCanvas({ executionId }: GraphRunCanvasProps) {
    const [template, setTemplate] = useState<TemplatePayload | null>(null);
    const [execution, setExecution] = useState<ExecutionDetailsPayload | null>(
        null,
    );
    const [nodeState, setNodeState] = useState<Record<string, NodeRunState>>({});
    const [edgeState, setEdgeState] = useState<Record<string, EdgeRunState>>({});
    const [stepIdToNodeId, setStepIdToNodeId] = useState<Record<string, string>>(
        {},
    );
    const [error, setError] = useState<string | null>(null);

    // Keep latest state in refs for the SSE callback to read without
    // re-subscribing on every keystroke.
    const templateRef = useRef(template);
    templateRef.current = template;
    const stepMapRef = useRef(stepIdToNodeId);
    stepMapRef.current = stepIdToNodeId;

    // Refresh both fetches and recompute state. Used on initial mount and
    // whenever an SSE event references a step we haven't seen yet (refetch
    // path) or a step completes (re-evaluate edges).
    const refresh = useCallback(async () => {
        try {
            const exec = (await getWorkflowExecutionDetails(
                executionId,
            )) as ExecutionDetailsPayload;
            const templateId = exec.execution?.template_id;
            if (!templateId) {
                setError('Execution has no template_id');
                return;
            }
            const tpl = (await getWorkflowTemplate(templateId)) as TemplatePayload;
            setExecution(exec);
            setTemplate(tpl);
            const derived = deriveRunState(exec, tpl);
            setNodeState(derived.nodeState);
            setEdgeState(derived.edgeState);
            setStepIdToNodeId(derived.stepIdToNodeId);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }
    }, [executionId]);

    // Initial fetch.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            await refresh();
            if (cancelled) return;
        })();
        return () => {
            cancelled = true;
        };
    }, [refresh]);

    // SSE subscription — canonical workflow.step.{started,completed,failed,
    // paused} dot-separated event types (BLOCKER #2 fix). The callback uses
    // refs to read the latest template + step map so it doesn't have to be
    // re-subscribed on every state change.
    //
    // Edge re-evaluation strategy: when a node flips to 'completed' and that
    // node is the target of a condition-node's outgoing edge, mark that
    // edge 'taken' and all sibling outgoing edges 'not_taken'. We do this
    // locally (without refetching) so the tests' mocked SSE events don't
    // get clobbered by the re-fetch overwriting state from stale fixtures.
    // The full refetch path is still used for unknown-step events (when an
    // SSE event refers to a step not in our initial snapshot).
    useEffect(() => {
        const unsub = subscribeToExecution(executionId, (event: WorkflowEvent) => {
            const stepId = event.step_id;
            if (!stepId) return;
            const nodeId = stepMapRef.current[stepId];
            if (!nodeId) {
                // Unknown step — refetch to learn its node mapping.
                void refresh();
                return;
            }
            switch (event.type) {
                case 'workflow.step.started':
                    setNodeState((prev) => ({ ...prev, [nodeId]: 'active' }));
                    break;
                case 'workflow.step.completed': {
                    setNodeState((prev) => {
                        const next = { ...prev, [nodeId]: 'completed' as const };
                        // Re-evaluate edges using the current template + the
                        // updated node state. If any condition upstream of
                        // nodeId now has a completed downstream, the matching
                        // edge becomes 'taken' and siblings become 'not_taken'.
                        const tpl = templateRef.current;
                        if (tpl) {
                            const edges = tpl.graph_edges ?? [];
                            const nodes = tpl.graph_nodes ?? [];
                            const completedIds = new Set<string>();
                            for (const [id, st] of Object.entries(next)) {
                                if (st === 'completed') completedIds.add(id);
                            }
                            setEdgeState((prevEdges) => {
                                const nextEdges = { ...prevEdges };
                                for (const sourceNode of nodes) {
                                    if (sourceNode.kind !== 'condition') continue;
                                    const outEdges = edges.filter(
                                        (e) => e.source === sourceNode.id,
                                    );
                                    const anyTaken = outEdges.some((e) =>
                                        completedIds.has(e.target),
                                    );
                                    if (!anyTaken) continue;
                                    for (const e of outEdges) {
                                        nextEdges[e.id] = completedIds.has(e.target)
                                            ? 'taken'
                                            : 'not_taken';
                                    }
                                }
                                return nextEdges;
                            });
                        }
                        return next;
                    });
                    break;
                }
                case 'workflow.step.failed':
                    setNodeState((prev) => ({ ...prev, [nodeId]: 'failed' }));
                    break;
                case 'workflow.step.paused':
                    // Render paused as active for now (Discretion: visual TBD).
                    setNodeState((prev) => ({ ...prev, [nodeId]: 'active' }));
                    break;
                default:
                    // Unknown event type — ignore.
                    break;
            }
        });
        return unsub;
    }, [executionId, refresh]);

    const reactFlowNodes: Node[] = useMemo(() => {
        if (!template) return [];
        const layout = template.graph_layout ?? {};
        return (template.graph_nodes ?? []).map((gn) => ({
            id: gn.id,
            type: gn.kind,
            position: gn.position ?? layout[gn.id] ?? { x: 0, y: 0 },
            data: {
                label: gn.label ?? '',
                config: gn.config ?? {},
                runState: nodeState[gn.id],
            },
        }));
    }, [template, nodeState]);

    const reactFlowEdges: Edge[] = useMemo(() => {
        if (!template) return [];
        return (template.graph_edges ?? []).map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            sourceHandle: e.source_handle ?? undefined,
            label: e.label ?? undefined,
            style: getEdgeRunStateStyle(edgeState[e.id]),
        }));
    }, [template, edgeState]);

    if (error) {
        return (
            <div
                className="p-4 text-sm text-red-600"
                data-testid="workflow-graph-run-widget-error"
            >
                Failed to load run: {error}
            </div>
        );
    }

    if (!template || !execution) {
        return (
            <div
                data-testid="workflow-graph-run-widget-loading"
                className="p-4 text-sm text-slate-500"
            >
                Loading branched run...
            </div>
        );
    }

    return (
        <div
            data-testid="workflow-graph-run-widget"
            className="w-full h-[480px] rounded-2xl border border-slate-200 bg-white"
        >
            <ReactFlow
                nodes={reactFlowNodes}
                edges={reactFlowEdges}
                nodeTypes={NODE_TYPES}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
                fitView
                attributionPosition="bottom-left"
            >
                <Background />
                <Controls showInteractive={false} />
            </ReactFlow>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Default export — extracts execution_id from the WidgetDefinition payload
// and wraps GraphRunCanvas in ReactFlowProvider.
// ---------------------------------------------------------------------------

export default function WorkflowGraphRunWidget({ definition }: WidgetProps) {
    const data = (definition.data ?? {}) as Record<string, unknown>;
    const executionId =
        (typeof data.execution_id === 'string' && data.execution_id) ||
        (typeof data.executionId === 'string' && data.executionId) ||
        '';
    if (!executionId) {
        return (
            <div
                data-testid="workflow-graph-run-widget-missing-exec-id"
                className="p-3 text-sm text-amber-600"
            >
                No execution_id provided to WorkflowGraphRunWidget.
            </div>
        );
    }
    return (
        <ReactFlowProvider>
            <GraphRunCanvas executionId={executionId} />
        </ReactFlowProvider>
    );
}
