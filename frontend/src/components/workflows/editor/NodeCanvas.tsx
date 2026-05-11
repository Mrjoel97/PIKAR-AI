'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview React Flow wrapper component for the workflow node editor.
 *
 * Phase 1 of Spec B (read-only viewer). Maps WorkflowTemplate.graph_nodes
 * onto React Flow Node[] and graph_edges onto Edge[]; uses graph_layout
 * for pixel positions. Renders three custom node types (trigger,
 * agent-action, output) and falls back to React Flow's default node for
 * Phase 3+ kinds (condition/parallel/merge/human-approval).
 *
 * All editing affordances are disabled: nodesDraggable=false,
 * nodesConnectable=false, elementsSelectable=false. Pan and zoom work
 * via the built-in <Controls> component.
 *
 * The fallback `projectStepsToGraph` codepath should be dead after Plan
 * 109-01's eager migration populates graph_nodes for every row, but is
 * kept as a safety net for any template whose projection failed (rows
 * land in workflow_template_migration_errors with NULL graph_nodes).
 */

import React, { useMemo } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    type Node,
    type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import type {
    WorkflowTemplate,
    GraphNode,
    GraphEdge,
    NodePosition,
} from '@/services/workflows';
import { TriggerNode } from './nodes/TriggerNode';
import { AgentActionNode } from './nodes/AgentActionNode';
import { OutputNode } from './nodes/OutputNode';

// nodeTypes must be defined at module scope (not inline) so React Flow does
// not warn about "It looks like you have created a new nodeTypes object" on
// every render. Phase 3+ kinds (condition/parallel/merge/human-approval) are
// intentionally absent — React Flow falls back to its default node renderer.
const NODE_TYPES = {
    trigger: TriggerNode,
    'agent-action': AgentActionNode,
    output: OutputNode,
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

interface NodeCanvasProps {
    template: WorkflowTemplate;
}

export function NodeCanvas({ template }: NodeCanvasProps) {
    const { nodes, edges, isEmpty } = useMemo(() => {
        // Phase 1 happy path: graph_nodes + graph_edges populated by the
        // 109-01 migration, graph_layout produced by pikar.compute_dagre_layout.
        if (template.graph_nodes && template.graph_edges) {
            const layout = (template.graph_layout ?? {}) as Record<string, NodePosition>;
            const rfNodes: Node[] = template.graph_nodes.map((gn: GraphNode) => ({
                id: gn.id,
                type: gn.kind,
                position: layout[gn.id] ?? { x: 0, y: 0 },
                data: {
                    label: gn.label,
                    tool_name:
                        gn.config && typeof gn.config === 'object'
                            ? ((gn.config as Record<string, unknown>).tool_name as string | undefined)
                            : undefined,
                },
            }));
            const rfEdges: Edge[] = template.graph_edges.map((ge: GraphEdge) => ({
                id: ge.id,
                source: ge.source,
                target: ge.target,
                label: ge.label ?? undefined,
            }));
            return {
                nodes: rfNodes,
                edges: rfEdges,
                isEmpty: rfNodes.length === 0,
            };
        }

        // Fallback path: graph fields are missing (legacy/un-migrated row, or
        // the per-row projection raised an exception). Project on the client
        // from the template's steps/phases. Post-109-01 deploy this branch is
        // dead code but it's the safety net per plan §interfaces.
        const projected = projectTemplateToGraph(template);
        return {
            nodes: projected.nodes,
            edges: projected.edges,
            isEmpty: projected.nodes.length === 0,
        };
    }, [template]);

    if (isEmpty) {
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
                        Phase 2 of the workflow node editor will let you add nodes here.
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
                nodes={nodes}
                edges={edges}
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
    // The WorkflowTemplateResponse Pydantic model does not currently expose
    // `steps` or `phases` as named fields, but Supabase select("*") returns
    // them and the legacy editor reads them. Cast through Record<string,
    // unknown> for a type-safe escape hatch.
    const bag = template as unknown as Record<string, unknown>;

    const flatSteps = bag.steps;
    if (Array.isArray(flatSteps) && flatSteps.length > 0) {
        return normalizeSteps(flatSteps as LegacyStep[]);
    }

    const phases = bag.phases;
    if (Array.isArray(phases)) {
        const out: NormalizedStep[] = [];
        for (const phase of phases as LegacyPhase[]) {
            if (phase && typeof phase === 'object' && Array.isArray(phase.steps)) {
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
