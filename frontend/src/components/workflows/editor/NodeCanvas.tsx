'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow wrapper component for the workflow node editor.
 *
 * Phase 109 shipped this in READ-ONLY mode (nodesDraggable=false,
 * nodesConnectable=false). Phase 110 Plan 04 widens it to accept an
 * `editable` prop (defaults false for backward-compat with the Phase 109
 * viewer callsite). When editable=true:
 *   - React Flow's standard onNodesChange / onEdgesChange / onConnect
 *     wired with applyNodeChanges / applyEdgeChanges / addEdge
 *   - Drag/drop drop handler reads 'application/reactflow' payload from
 *     NodePalette (Task 04-03) and adds a new GraphNode
 *   - onChange callback emits the current {nodes, edges, layout} to the
 *     parent (editor page) so it can track dirty state + run validation
 *   - Selection state lifts up via onSelectNode callback
 *   - validationErrors prop is bucketed by node_id and pushed into each
 *     node's data so custom node components can render red badges
 *
 * All 7 node kinds are registered in NODE_TYPES (3 from Phase 109 + 4
 * shipped in Task 04-01).
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    addEdge,
    applyNodeChanges,
    applyEdgeChanges,
    useReactFlow,
    type Node,
    type Edge,
    type NodeChange,
    type EdgeChange,
    type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import type {
    WorkflowTemplate,
    GraphNode,
    GraphEdge,
    NodePosition,
    NodeKind,
    ValidationError,
} from '@/services/workflows';
import { TriggerNode } from './nodes/TriggerNode';
import { AgentActionNode } from './nodes/AgentActionNode';
import { OutputNode } from './nodes/OutputNode';
import { ConditionNode } from './nodes/ConditionNode';
import { ParallelNode } from './nodes/ParallelNode';
import { MergeNode } from './nodes/MergeNode';
import { HumanApprovalNode } from './nodes/HumanApprovalNode';
import { bucketErrorsByNode } from './useGraphValidation';

// nodeTypes must be defined at module scope (not inline) so React Flow does
// not warn about "It looks like you have created a new nodeTypes object" on
// every render. Phase 110 Plan 04 adds all 4 Phase 3/4 node components.
const NODE_TYPES = {
    trigger: TriggerNode,
    'agent-action': AgentActionNode,
    output: OutputNode,
    condition: ConditionNode,
    parallel: ParallelNode,
    merge: MergeNode,
    'human-approval': HumanApprovalNode,
};

interface LegacyStep {
    name?: unknown;
    tool?: unknown;
    description?: unknown;
}

interface LegacyPhase {
    name?: unknown;
    steps?: unknown;
}

export interface EditorGraphChange {
    nodes: GraphNode[];
    edges: GraphEdge[];
    layout: Record<string, NodePosition>;
}

interface NodeCanvasProps {
    template: WorkflowTemplate;
    /**
     * When true: wire onNodesChange/onEdgesChange/onConnect + drag/drop drop
     * handler + selection. When false / unset: behaves identically to the
     * Phase 109 read-only viewer (backward-compat).
     */
    editable?: boolean;
    /** Called whenever the graph changes (drag, connect, drop). Edit-mode only. */
    onChange?: (change: EditorGraphChange) => void;
    /** id of the currently-selected node (edit mode). */
    selectedNodeId?: string | null;
    onSelectNode?: (id: string | null) => void;
    /** Errors from useGraphValidation; bucketed and passed to each node. */
    validationErrors?: ValidationError[];
}

export function NodeCanvas({
    template,
    editable = false,
    onChange,
    selectedNodeId,
    onSelectNode,
    validationErrors = [],
}: NodeCanvasProps) {
    // Derive the initial graph from the template prop. We use the same
    // useMemo-based projection as Phase 109, but in edit mode we then
    // mirror it into local React Flow state so user edits don't get
    // clobbered on every render.
    const initial = useMemo(() => {
        if (template.graph_nodes && template.graph_edges) {
            const layout = (template.graph_layout ?? {}) as Record<
                string,
                NodePosition
            >;
            const rfNodes: Node[] = template.graph_nodes.map((gn: GraphNode) => ({
                id: gn.id,
                type: gn.kind,
                position: layout[gn.id] ?? { x: 0, y: 0 },
                data: {
                    label: gn.label,
                    config: gn.config ?? {},
                    tool_name:
                        gn.config && typeof gn.config === 'object'
                            ? ((gn.config as Record<string, unknown>)
                                  .tool_name as string | undefined)
                            : undefined,
                },
            }));
            const rfEdges: Edge[] = template.graph_edges.map(
                (ge: GraphEdge) => ({
                    id: ge.id,
                    source: ge.source,
                    target: ge.target,
                    sourceHandle: ge.source_handle ?? undefined,
                    label: ge.label ?? undefined,
                }),
            );
            return {
                nodes: rfNodes,
                edges: rfEdges,
                isEmpty: rfNodes.length === 0,
            };
        }
        // Fallback projection — Phase 109 dead-code path kept for safety.
        const projected = projectTemplateToGraph(template);
        return {
            nodes: projected.nodes,
            edges: projected.edges,
            isEmpty: projected.nodes.length === 0,
        };
    }, [template]);

    // ---------- READ-ONLY MODE (Phase 109 viewer call site) -----------
    if (!editable) {
        if (initial.isEmpty) {
            return (
                <div
                    style={{ width: '100%', height: '70vh' }}
                    className="flex items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50"
                >
                    <div className="text-center">
                        <p className="text-sm font-medium text-slate-700">
                            This template has no graph nodes yet.
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                            Phase 2 of the workflow node editor will let you
                            add nodes here.
                        </p>
                    </div>
                </div>
            );
        }
        return (
            <div
                style={{ width: '100%', height: '70vh' }}
                className="rounded-2xl border border-slate-200 bg-white"
            >
                <ReactFlow
                    nodes={initial.nodes}
                    edges={initial.edges}
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

    // ---------- EDITABLE MODE (Phase 110 editor page) -----------
    return (
        <EditableNodeCanvas
            initial={initial}
            onChange={onChange}
            selectedNodeId={selectedNodeId}
            onSelectNode={onSelectNode}
            validationErrors={validationErrors}
        />
    );
}

// Split into a sibling component so we can call useReactFlow() inside it
// (requires ReactFlowProvider somewhere up the tree — the editor page does
// the wrap).
interface EditableProps {
    initial: { nodes: Node[]; edges: Edge[]; isEmpty: boolean };
    onChange?: (change: EditorGraphChange) => void;
    selectedNodeId?: string | null;
    onSelectNode?: (id: string | null) => void;
    validationErrors: ValidationError[];
}

function EditableNodeCanvas({
    initial,
    onChange,
    selectedNodeId,
    onSelectNode,
    validationErrors,
}: EditableProps) {
    const [nodes, setNodes] = useState<Node[]>(initial.nodes);
    const [edges, setEdges] = useState<Edge[]>(initial.edges);
    const reactFlow = useReactFlow();

    // Re-seed local state when the template prop changes from underneath us
    // (e.g. after Save + reload, or seed-fork redirect to a new template).
    const lastInitialRef = useRef(initial);
    useEffect(() => {
        if (lastInitialRef.current !== initial) {
            setNodes(initial.nodes);
            setEdges(initial.edges);
            lastInitialRef.current = initial;
        }
    }, [initial]);

    // Bucket validation errors and inject into each node's data so custom
    // node components can render red badges from data.validationErrors.
    const errorsByNode = useMemo(
        () => bucketErrorsByNode(validationErrors),
        [validationErrors],
    );

    const nodesWithBadges = useMemo<Node[]>(
        () =>
            nodes.map((n) => ({
                ...n,
                selected: n.id === selectedNodeId,
                data: {
                    ...(n.data ?? {}),
                    validationErrors: errorsByNode.get(n.id) ?? [],
                },
            })),
        [nodes, errorsByNode, selectedNodeId],
    );

    // Emit the current graph shape to the parent. Wrapped in useCallback so
    // it's stable across re-renders.
    const emitChange = useCallback(
        (
            currentNodes: Node[],
            currentEdges: Edge[],
        ) => {
            if (!onChange) return;
            const graphNodes: GraphNode[] = currentNodes.map((n) => ({
                id: n.id,
                kind: (n.type ?? 'agent-action') as NodeKind,
                label:
                    (n.data && typeof n.data === 'object'
                        ? ((n.data as Record<string, unknown>).label as
                              | string
                              | undefined)
                        : undefined) ?? '',
                config:
                    n.data && typeof n.data === 'object'
                        ? ((n.data as Record<string, unknown>).config as
                              | Record<string, unknown>
                              | undefined) ?? {}
                        : {},
            }));
            const graphEdges: GraphEdge[] = currentEdges.map((e) => ({
                id: e.id,
                source: e.source,
                target: e.target,
                source_handle: e.sourceHandle ?? null,
                label: (e.label as string | undefined) ?? null,
            }));
            const layout: Record<string, NodePosition> = {};
            for (const n of currentNodes) {
                layout[n.id] = n.position;
            }
            onChange({
                nodes: graphNodes,
                edges: graphEdges,
                layout,
            });
        },
        [onChange],
    );

    const handleNodesChange = useCallback(
        (changes: NodeChange[]) => {
            setNodes((prev) => {
                const next = applyNodeChanges(changes, prev);
                emitChange(next, edges);
                return next;
            });
        },
        [edges, emitChange],
    );

    const handleEdgesChange = useCallback(
        (changes: EdgeChange[]) => {
            setEdges((prev) => {
                const next = applyEdgeChanges(changes, prev);
                emitChange(nodes, next);
                return next;
            });
        },
        [nodes, emitChange],
    );

    const handleConnect = useCallback(
        (connection: Connection) => {
            // Simple validation: don't allow trigger→trigger.
            const src = nodes.find((n) => n.id === connection.source);
            const tgt = nodes.find((n) => n.id === connection.target);
            if (src?.type === 'trigger' && tgt?.type === 'trigger') return;
            setEdges((prev) => {
                const next = addEdge(
                    {
                        ...connection,
                        id: `e-${connection.source}-${connection.target}-${Date.now()}`,
                    },
                    prev,
                );
                emitChange(nodes, next);
                return next;
            });
        },
        [nodes, emitChange],
    );

    const handleDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const handleDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();
            const raw = event.dataTransfer.getData('application/reactflow');
            if (!raw) return;
            let payload: { kind: NodeKind; label: string };
            try {
                payload = JSON.parse(raw);
            } catch {
                return;
            }
            const position = reactFlow.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });
            const newNode: Node = {
                id:
                    typeof crypto !== 'undefined' && 'randomUUID' in crypto
                        ? crypto.randomUUID()
                        : `node-${Date.now()}-${Math.random()
                              .toString(36)
                              .slice(2, 8)}`,
                type: payload.kind,
                position,
                data: { label: payload.label, config: {} },
            };
            setNodes((prev) => {
                const next = [...prev, newNode];
                emitChange(next, edges);
                return next;
            });
        },
        [reactFlow, edges, emitChange],
    );

    const handleSelectionChange = useCallback(
        ({ nodes: selected }: { nodes: Node[] }) => {
            if (!onSelectNode) return;
            onSelectNode(selected.length > 0 ? selected[0].id : null);
        },
        [onSelectNode],
    );

    if (initial.isEmpty && nodes.length === 0) {
        return (
            <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                style={{ width: '100%', height: '100%' }}
                className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50"
                data-testid="editor-empty-state"
            >
                <div className="text-center">
                    <p className="text-sm font-medium text-slate-700">
                        Drag a Trigger from the palette to start.
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                        Build your workflow by connecting nodes left-to-right.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div
            style={{ width: '100%', height: '100%' }}
            className="h-full rounded-2xl border border-slate-200 bg-white"
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            data-testid="editor-canvas"
        >
            <ReactFlow
                nodes={nodesWithBadges}
                edges={edges}
                nodeTypes={NODE_TYPES}
                nodesDraggable
                nodesConnectable
                elementsSelectable
                onNodesChange={handleNodesChange}
                onEdgesChange={handleEdgesChange}
                onConnect={handleConnect}
                onSelectionChange={handleSelectionChange}
                fitView
                attributionPosition="bottom-left"
            >
                <Background />
                <Controls />
            </ReactFlow>
        </div>
    );
}

export default NodeCanvas;

// ---------------------------------------------------------------------------
// Fallback projection — mirrors the SQL helpers in 109-01 (project_steps_to_*
// + flatten_phases_to_steps adapter) in TypeScript. After 109-01's eager
// migration runs in prod, every row has graph_nodes != null and this branch
// is dead code. Kept for safety so a single bad row does not crash the page.
// ---------------------------------------------------------------------------

interface NormalizedStep {
    name: string;
    tool: string | undefined;
}

function projectTemplateToGraph(template: WorkflowTemplate): {
    nodes: Node[];
    edges: Edge[];
} {
    const steps = flattenTemplateToSteps(template);
    if (steps.length === 0) {
        return { nodes: [], edges: [] };
    }

    const COL_WIDTH = 200;
    const triggerNode: Node = {
        id: 'trigger',
        type: 'trigger',
        position: { x: 0, y: 0 },
        data: { label: 'Start' },
    };
    const stepNodes: Node[] = steps.map((s, i) => ({
        id: `step-${i}`,
        type: 'agent-action',
        position: { x: COL_WIDTH * (i + 1), y: 0 },
        data: { label: s.name, tool_name: s.tool },
    }));
    const outputNode: Node = {
        id: 'output',
        type: 'output',
        position: { x: COL_WIDTH * (steps.length + 1), y: 0 },
        data: { label: 'Done' },
    };

    const edges: Edge[] = [];
    edges.push({ id: 'e-trigger-step-0', source: 'trigger', target: 'step-0' });
    for (let i = 0; i < steps.length - 1; i++) {
        edges.push({
            id: `e-step-${i}-step-${i + 1}`,
            source: `step-${i}`,
            target: `step-${i + 1}`,
        });
    }
    edges.push({
        id: `e-step-${steps.length - 1}-output`,
        source: `step-${steps.length - 1}`,
        target: 'output',
    });

    return {
        nodes: [triggerNode, ...stepNodes, outputNode],
        edges,
    };
}

/**
 * Flattens a workflow template's `steps` array OR its nested `phases.*.steps`
 * into a single ordered list of {name, tool} pairs. Mirrors the Postgres
 * `pikar.flatten_phases_to_steps` adapter shipped in Plan 109-01 so both code
 * paths produce identical projections for the same template.
 */
function flattenTemplateToSteps(template: WorkflowTemplate): NormalizedStep[] {
    const bag = template as unknown as Record<string, unknown>;

    const flatSteps = bag.steps;
    if (Array.isArray(flatSteps) && flatSteps.length > 0) {
        return normalizeSteps(flatSteps as LegacyStep[]);
    }

    const phases = bag.phases;
    if (Array.isArray(phases)) {
        const out: NormalizedStep[] = [];
        for (const phase of phases as LegacyPhase[]) {
            if (
                phase &&
                typeof phase === 'object' &&
                Array.isArray(phase.steps)
            ) {
                out.push(...normalizeSteps(phase.steps as LegacyStep[]));
            }
        }
        return out;
    }

    return [];
}

function normalizeSteps(raw: LegacyStep[]): NormalizedStep[] {
    return raw.map((s, i) => ({
        name: typeof s?.name === 'string' && s.name.trim() ? s.name : `Step ${i + 1}`,
        tool: typeof s?.tool === 'string' ? s.tool : undefined,
    }));
}
